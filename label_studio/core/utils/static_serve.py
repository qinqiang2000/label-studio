"""
Views and functions for serving static files. These are only to be used
during development, and SHOULD NOT be used in a production setting.
"""

import gzip
import mimetypes
import posixpath
import re
from collections import OrderedDict
from pathlib import Path
from threading import Lock

from core.utils.manifest_assets import get_manifest_asset
from django.http import (
    Http404,
    HttpResponse,
    HttpResponseNotModified,
)
from django.utils._os import safe_join
from django.utils.http import http_date
from django.utils.translation import gettext as _
from django.views.static import was_modified_since
from ranged_fileresponse import RangedFileResponse

# Content types that benefit from gzip and don't already self-compress.
_GZIPPABLE_TYPES = frozenset(
    {
        'text/css',
        'text/html',
        'text/plain',
        'text/javascript',
        'application/javascript',
        'application/json',
        'application/manifest+json',
        'application/wasm',
        'image/svg+xml',
        'image/x-icon',
    }
)

# In-memory cache of gzip-compressed payloads keyed by (path, mtime_ns, size).
# Bounded by total compressed bytes to avoid unbounded memory growth.
_GZIP_CACHE: 'OrderedDict[tuple, bytes]' = OrderedDict()
_GZIP_CACHE_LOCK = Lock()
_GZIP_CACHE_MAX_BYTES = 64 * 1024 * 1024  # 64 MiB
_GZIP_CACHE_BYTES = 0
_GZIP_MIN_BYTES = 1024
_GZIP_MAX_FILE_BYTES = 10 * 1024 * 1024  # don't try to compress >10 MiB files in memory

_VERSION_QUERY_RE = re.compile(r'(?:^|&)v=')


def _client_accepts_gzip(request):
    accept = request.META.get('HTTP_ACCEPT_ENCODING', '')
    return 'gzip' in accept.lower()


def _gzip_cache_get(key):
    with _GZIP_CACHE_LOCK:
        if key in _GZIP_CACHE:
            _GZIP_CACHE.move_to_end(key)
            return _GZIP_CACHE[key]
    return None


def _gzip_cache_put(key, payload):
    global _GZIP_CACHE_BYTES
    size = len(payload)
    with _GZIP_CACHE_LOCK:
        if key in _GZIP_CACHE:
            return
        _GZIP_CACHE[key] = payload
        _GZIP_CACHE_BYTES += size
        while _GZIP_CACHE_BYTES > _GZIP_CACHE_MAX_BYTES and _GZIP_CACHE:
            _, old = _GZIP_CACHE.popitem(last=False)
            _GZIP_CACHE_BYTES -= len(old)


def _build_gzip_response(fullpath: Path, statobj, content_type: str) -> HttpResponse:
    key = (str(fullpath), statobj.st_mtime_ns, statobj.st_size)
    payload = _gzip_cache_get(key)
    if payload is None:
        with fullpath.open('rb') as f:
            raw = f.read()
        payload = gzip.compress(raw, compresslevel=6, mtime=0)
        _gzip_cache_put(key, payload)
    response = HttpResponse(payload, content_type=content_type)
    response['Content-Encoding'] = 'gzip'
    response['Content-Length'] = str(len(payload))
    return response


def serve(request, path, document_root=None, show_indexes=False, manifest_asset_prefix=None):
    """
    Serve static files below a given point in the directory structure.

    To use, put a URL pattern such as::

        from django.views.static import serve

        path('<path:path>', serve, {'document_root': '/path/to/my/files/'})

    in your URLconf. You must provide the ``document_root`` param. You may
    also set ``show_indexes`` to ``True`` if you'd like to serve a basic index
    of the directory.  This index view will use the template hardcoded below,
    but if you'd like to override it, you can create a template called
    ``static/directory_index.html``.

    If manifest_asset_prefix is provided, we will try to serve the file from the manifest.json
    if the file is not found in the document_root.

    Example:
        path = "main.js"
        document_root = "/dist/apps/labelstudio/"
        manifest_asset_prefix = "react-app"
        manifest_json = {"main.js": "/react-app/main.123456.js"}
        fullpath = Path(safe_join(document_root, "main.123456.js"))
    """
    path = posixpath.normpath(path).lstrip('/')
    fullpath = Path(safe_join(document_root, path))
    if fullpath.is_dir():
        raise Http404(_('Directory indexes are not allowed here.'))
    if manifest_asset_prefix and not fullpath.exists():
        possible_asset = get_manifest_asset(path)
        manifest_asset_prefix = (
            f'/{manifest_asset_prefix}' if not manifest_asset_prefix.startswith('/') else manifest_asset_prefix
        )
        if possible_asset.startswith(manifest_asset_prefix):
            possible_asset = possible_asset[len(manifest_asset_prefix) :]
        fullpath = Path(safe_join(document_root, possible_asset))
    if not fullpath.exists():
        raise Http404(_('“%(path)s” does not exist') % {'path': fullpath})
    # Respect the If-Modified-Since header.
    statobj = fullpath.stat()
    if not was_modified_since(request.META.get('HTTP_IF_MODIFIED_SINCE'), statobj.st_mtime):
        return HttpResponseNotModified()
    content_type, encoding = mimetypes.guess_type(str(fullpath))
    content_type = content_type or 'application/octet-stream'

    # Cache headers: immutable for hashed/versioned assets (e.g. ?v=abc123 or
    # bundle filenames embedding a content hash); short revalidation otherwise.
    is_versioned = bool(_VERSION_QUERY_RE.search(request.META.get('QUERY_STRING', ''))) or bool(
        re.search(r'\.[0-9a-f]{8,}\.', fullpath.name)
    )
    cache_control = 'public, max-age=31536000, immutable' if is_versioned else 'public, max-age=300'

    # Fast path: gzip-compressed in-memory response for compressible text assets.
    # Skip when the client sends a Range header (Range over Content-Encoding is
    # underspecified and breaks media seeking; fall back to the ranged path).
    has_range = bool(request.META.get('HTTP_RANGE'))
    if (
        not has_range
        and _client_accepts_gzip(request)
        and content_type in _GZIPPABLE_TYPES
        and _GZIP_MIN_BYTES <= statobj.st_size <= _GZIP_MAX_FILE_BYTES
        and not encoding  # don't double-encode pre-compressed files
    ):
        response = _build_gzip_response(fullpath, statobj, content_type)
        response['Last-Modified'] = http_date(statobj.st_mtime)
        response['Vary'] = 'Accept-Encoding'
        response['Cache-Control'] = cache_control
        return response

    response = RangedFileResponse(request, fullpath.open('rb'), content_type=content_type)
    response['Last-Modified'] = http_date(statobj.st_mtime)
    # RangedFileResponse wraps the file in an iterator without `.read()`, so
    # FileResponse.set_headers() never runs and Content-Length is missing
    # except for actual Range requests. Set it from the stat we already have
    # so HTTP/1.1 keep-alive proxies (e.g. Clash) can frame the response.
    response['Content-Length'] = str(statobj.st_size)
    response['Cache-Control'] = cache_control
    if encoding:
        response['Content-Encoding'] = encoding
    return response

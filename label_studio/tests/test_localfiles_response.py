import pytest
from io_storages.localfiles.models import LocalFilesImportStorage
from tests.utils import make_project


@pytest.mark.django_db
def test_local_files_pdf_response_has_length_for_plain_get(business_client, settings, tmp_path):
    settings.LOCAL_FILES_SERVING_ENABLED = True
    settings.LOCAL_FILES_DOCUMENT_ROOT = str(tmp_path)

    pdf = tmp_path / 'sample.pdf'
    pdf.write_bytes(b'%PDF-1.3\n%test\n')

    project = make_project({}, business_client.user, use_ml_backend=False)
    LocalFilesImportStorage.objects.create(project=project, path=str(tmp_path))

    response = business_client.get('/data/local-files/?d=sample.pdf')

    assert response.status_code == 200
    assert response['Content-Type'] == 'application/pdf'
    assert response['Accept-Ranges'] == 'bytes'
    assert response['Content-Length'] == str(pdf.stat().st_size)

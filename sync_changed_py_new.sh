#!/bin/bash
set -euo pipefail

# Usage:
#   ./sync_changed_py_new.sh        # sync backend + frontend, then restart
#   ./sync_changed_py_new.sh b      # sync backend only, then restart
#   ./sync_changed_py_new.sh f      # sync frontend only, then restart
#   ./sync_changed_py_new.sh src    # sync full source mirror to /root/label_studio/src only
#   ./sync_changed_py_new.sh restart

SYNC_MODE="${1:-all}"

PEM=~/tools/pem/ty_sg01.pem
REMOTE=root@43.166.182.9
REMOTE_BASE=/root/miniconda3/envs/ls-env/lib/python3.10/site-packages
REMOTE_SRC=/root/label_studio/src
LAST_SYNC_COMMIT_FILE=".last_synced_commit_new"

ssh_remote() {
  ssh -i "$PEM" -o StrictHostKeyChecking=no "$REMOTE" "$@"
}

sync_backend() {
  local last_sync_commit current_head changed_files

  if [ -f "$LAST_SYNC_COMMIT_FILE" ]; then
    last_sync_commit=$(cat "$LAST_SYNC_COMMIT_FILE")
  else
    last_sync_commit=$(git rev-parse HEAD^)
    echo "No $LAST_SYNC_COMMIT_FILE found. Syncing from HEAD^ ($last_sync_commit)."
  fi

  current_head=$(git rev-parse HEAD)
  changed_files=$(git diff --name-only "$last_sync_commit".."$current_head" -- 'label_studio/*' || true)

  echo "Backend sync: $last_sync_commit -> $current_head"
  if [ -z "$changed_files" ]; then
    echo "No backend files changed."
  else
    echo "$changed_files"
    while IFS= read -r file; do
      [ -n "$file" ] || continue
      remote_dir=$(dirname "$REMOTE_BASE/$file")
      ssh_remote "mkdir -p '$remote_dir'"
      scp -i "$PEM" -o StrictHostKeyChecking=no "$file" "$REMOTE:$REMOTE_BASE/$file"
    done <<< "$changed_files"
  fi

  echo "$current_head" > "$LAST_SYNC_COMMIT_FILE"
  echo "Updated $LAST_SYNC_COMMIT_FILE with $current_head"
}

sync_frontend() {
  if [ ! -d ./web/dist/apps/labelstudio ]; then
    echo "Frontend dist not found: ./web/dist/apps/labelstudio"
    echo "Build frontend first, then rerun frontend sync."
    exit 1
  fi

  echo "Frontend sync start."
  ssh_remote "mkdir -p '$REMOTE_BASE/web/dist/apps/labelstudio'"
  rsync -az --delete -e "ssh -i $PEM -o StrictHostKeyChecking=no" \
    ./web/dist/apps/labelstudio/ \
    "$REMOTE:$REMOTE_BASE/web/dist/apps/labelstudio/"
  echo "Frontend sync done."
}

sync_source_mirror() {
  echo "Source mirror sync start: $REMOTE_SRC"
  ssh_remote "mkdir -p '$REMOTE_SRC'"
  rsync -az --delete \
    --exclude .git \
    --exclude node_modules \
    --exclude .venv \
    --exclude venv \
    --exclude __pycache__ \
    -e "ssh -i $PEM -o StrictHostKeyChecking=no" \
    ./ "$REMOTE:$REMOTE_SRC/"
  echo "Source mirror sync done."
}

restart_service() {
  echo "Restarting label-studio.service on $REMOTE"
  ssh_remote "systemctl restart label-studio && sleep 5 && systemctl is-active label-studio && curl -I --max-time 10 http://127.0.0.1/ | sed -n '1,12p'"
}

case "$SYNC_MODE" in
  b|backend)
    sync_backend
    restart_service
    ;;
  f|frontend)
    sync_frontend
    restart_service
    ;;
  src)
    sync_source_mirror
    ;;
  restart)
    restart_service
    ;;
  all)
    sync_backend
    sync_frontend
    restart_service
    ;;
  *)
    echo "Unknown mode: $SYNC_MODE"
    exit 1
    ;;
esac

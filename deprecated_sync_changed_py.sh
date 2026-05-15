#!/bin/bash

# 参数处理
SYNC_MODE="all"
if [ "$1" = "b" ]; then
    SYNC_MODE="backend"
elif [ "$1" = "f" ]; then
    SYNC_MODE="frontend"
fi

# 远程服务器信息
PEM=~/tools/pem/ecs_label_studio_1.pem
REMOTE=root@120.77.56.227
REMOTE_BASE=/root/miniconda3/envs/ls-env/lib/python3.10/site-packages

# 后端同步函数
sync_backend() {
    LAST_SYNC_COMMIT_FILE=".last_synced_commit"
    LAST_SYNC_COMMIT=""

    if [ -f "$LAST_SYNC_COMMIT_FILE" ]; then
        LAST_SYNC_COMMIT=$(cat "$LAST_SYNC_COMMIT_FILE")
    else
        # If no previous sync commit, default to the commit before HEAD (last commit)
        # Or, the user might want to specify a base commit for the very first run.
        LAST_SYNC_COMMIT=$(git rev-parse HEAD^)
        echo "No previous sync commit found. Syncing from HEAD^ ($LAST_SYNC_COMMIT) to HEAD."
    fi

    CURRENT_HEAD=$(git rev-parse HEAD)

    echo "Syncing from $LAST_SYNC_COMMIT to $CURRENT_HEAD"

    # 1. 找出所有改动且以 label_studio/ 开头的文件
    changed_files=$(git diff --name-only "$LAST_SYNC_COMMIT".."$CURRENT_HEAD" | grep '^label_studio/')

    echo "后端同步开始！要同步的文件如下："
    echo "$changed_files"

    # 2. 逐个 scp 同步
    for file in $changed_files; do
      remote_dir=$(dirname "$REMOTE_BASE/$file")
      echo "ssh -i $PEM $REMOTE 'mkdir -p $remote_dir'"
      ssh -i $PEM $REMOTE "mkdir -p $remote_dir"
      echo "scp -i $PEM $file $REMOTE:$REMOTE_BASE/$file"
      scp -i $PEM $file $REMOTE:$REMOTE_BASE/$file
    done

    echo "后端全部同步完成！"

    # Update last synced commit
    echo "$CURRENT_HEAD" > "$LAST_SYNC_COMMIT_FILE"
    echo "Updated $LAST_SYNC_COMMIT_FILE with $CURRENT_HEAD"
}

# 前端同步函数
sync_frontend() {
    echo "前端同步开始！"
    scp -i $PEM ./web/dist/apps/labelstudio/* $REMOTE:$REMOTE_BASE/web/dist/apps/labelstudio
    echo "前端全部同步完成！"
}

# 根据参数执行相应的同步操作
if [ "$SYNC_MODE" = "backend" ]; then
    sync_backend
elif [ "$SYNC_MODE" = "frontend" ]; then
    sync_frontend
else
    sync_backend
    sync_frontend
fi
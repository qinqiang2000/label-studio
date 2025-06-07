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
    # 1. 找出所有改动且以 label_studio/ 开头的文件
    changed_files=$(git diff --name-only c6d9011..company-custom | grep '^label_studio/')
    # changed_files=$(git diff --name-only HEAD^ HEAD | grep '^label_studio/')

    echo "后端同步开始！要同步的文件如下："
    echo "$changed_files"

    # 2. 逐个 scp 同步
    for file in $changed_files; do
      echo "scp -i $PEM $file $REMOTE:$REMOTE_BASE/$file"
      scp -i $PEM $file $REMOTE:$REMOTE_BASE/$file
    done

    echo "后端全部同步完成！"
}

# 前端同步函数
sync_frontend() {
    echo "前端同步开始！"
    scp -i $PEM /Users/qinqiang02/colab/codespace/ai/label-studio/web/dist/apps/labelstudio/* $REMOTE:$REMOTE_BASE/web/dist/apps/labelstudio
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
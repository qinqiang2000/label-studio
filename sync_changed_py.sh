#!/bin/bash

# 1. 找出所有改动且以 label_studio/ 开头的文件
changed_files=$(git diff --name-only c6d9011..company-custom | grep '^label_studio/')

# 2. 远程服务器信息
PEM=~/tools/pem/ecs_label_studio_1.pem
REMOTE=root@120.77.56.227
REMOTE_BASE=/root/miniconda3/envs/ls-env/lib/python3.10/site-packages

# 3. 逐个 scp 同步
for file in $changed_files; do
  echo "scp -i $PEM $file $REMOTE:$REMOTE_BASE/$file"
  scp -i $PEM $file $REMOTE:$REMOTE_BASE/$file
done

echo "全部同步完成！"
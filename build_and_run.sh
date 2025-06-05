#!/bin/bash

set -e
#export LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true
#export LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=/Users/qinqiang02/job/test/发票测试数据/海外形式发票/日本/海信日本生产20250522

echo "进入 web 目录..."
cd web

echo "开始前端构建..."
yarn build

echo "前端构建完成，返回项目根目录..."
cd ..

echo "收集静态文件到 Django..."
poetry run python label_studio/manage.py collectstatic --noinput

echo "重启 Django 开发服务..."
# 先杀掉旧的 runserver（如果有）
pkill -f "manage.py runserver" || true

# 启动新的 runserver（前台运行，Ctrl+C 可停止）
poetry run python label_studio/manage.py runserver

# 如果你想后台运行，可以这样（不推荐生产环境用）：
# poetry run python label_studio/manage.py runserver &

echo "全部完成！"

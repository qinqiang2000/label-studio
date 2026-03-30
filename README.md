# Label Studio 本地开发指南

## 环境要求

- Python >= 3.10
- [Poetry](https://python-poetry.org/) >= 2.0.0
- Node.js (推荐 v22+)
- Yarn 1.x

## 后端安装

```bash
# 安装 Poetry（如未安装）
pip install poetry

# 安装 Python 依赖
poetry install

# 数据库迁移（SQLite）
make migrate-dev

# 收集静态文件
DJANGO_DB=sqlite LOG_DIR=tmp DEBUG=true LOG_LEVEL=DEBUG \
  DJANGO_SETTINGS_MODULE=core.settings.label_studio \
  poetry run python label_studio/manage.py collectstatic
```

## 前端安装

```bash
cd web
yarn install --frozen-lockfile
```

## 启动服务

每个终端启动前需要先加载环境变量：

```bash
source .env
```

### Terminal 1 — 后端 (端口 8000)

```bash
make run-dev
```

等价于：

```bash
DJANGO_DB=sqlite LOG_DIR=tmp DEBUG=true LOG_LEVEL=DEBUG \
  DJANGO_SETTINGS_MODULE=core.settings.label_studio \
  poetry run python label_studio/manage.py runserver
```

### Terminal 2 — 前端 HMR (端口 8010)

```bash
cd web && yarn dev
```

### Terminal 3 — ML Backend (端口 9090)

ML 后端服务需要单独启动，监听 `http://127.0.0.1:9090`。

## .env 配置

项目根目录下的 `.env` 文件包含运行时配置，**已有内容请勿随意覆盖**。主要配置项：

| 变量 | 说明 |
|------|------|
| `FRONTEND_HMR` | 前端热更新开关 |
| `TZ` | 时区（Asia/Shanghai） |
| `LABEL_STUDIO_API_KEY` | API 访问密钥 |
| `LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED` | 启用本地文件服务 |
| `LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT` | 本地文件根目录 |
| `LABEL_STUDIO_ML_BACKEND_URL` | ML 后端地址 |
| `ML_TIMEOUT_*` 系列 | ML 各操作超时配置（秒） |

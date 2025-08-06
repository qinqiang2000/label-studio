默认是plan模式，即：先输出思路和方案，由我同意后，才自动生成和修改代码
如果发现本rule的命令有不对的地方，请直接修改

## 虚拟环境
所有Python命令都需要加上 `poetry run` 前缀

## 常用命令

### Django 开发命令
```bash
# 加载环境变量
source .env

# 运行开发服务器
poetry run python label_studio/manage.py runserver

# 数据库迁移
poetry run python label_studio/manage.py makemigrations
poetry run python label_studio/manage.py migrate

# 创建超级用户
poetry run python label_studio/manage.py createsuperuser

# Django shell
poetry run python label_studio/manage.py shell

# 初始化权限数据
poetry run python label_studio/manage.py init_permissions
```

### 前端命令 (在 web/ 目录下)
**重要：所有前端命令都需要在 web/ 目录下执行**

```bash
# 开发
yarn dev                   # 开发服务器
yarn watch                 # 监听模式构建
yarn build                 # 生产构建

# Label Studio 特定命令
yarn ls:dev                # Label Studio 开发服务器
yarn ls:watch              # Label Studio 监听构建
yarn ls:build              # Label Studio 生产构建

# 编辑器相关命令
yarn lsf:watch             # 编辑器监听构建
yarn lsf:serve             # 编辑器独立服务

# 测试
yarn test:unit             # 单元测试
yarn test:e2e              # E2E 测试
yarn test:integration      # 集成测试

# 代码检查和格式化
yarn lint                     # 运行 Biome 代码检查和格式化 (等同于: biome check --apply .)
yarn biome check --write <file>     # 检查并修复单个文件（安全修复）
yarn biome check --fix --unsafe <file>  # 应用不安全的修复建议
```

## 项目架构

### 后端结构 (Django)
- `label_studio/` - Django 应用根目录
  - `core/` - 核心设置和工具
  - `projects/` - 项目管理
  - `tasks/` - 任务管理
  - `users/` - 用户管理
  - `organizations/` - 组织管理
  - `data_manager/` - 数据管理和操作
  - `data_import/` - 数据导入
  - `data_export/` - 数据导出
  - `io_storages/` - 存储集成 (S3, GCS, Azure等)
  - `ml/` - 机器学习后端集成
  - `webhooks/` - Webhook 支持
  - `workspaces/` - 工作空间功能
  - `evaluation_configs/` - 评估配置管理

### 前端结构 (React + MobX)
- `web/` - 前端代码根目录
  - `apps/labelstudio/` - 主应用
  - `libs/editor/` - 标注编辑器库
  - `libs/datamanager/` - 数据管理器库
  - Nx monorepo 结构，使用 React 18 和 MobX 状态管理

### 权限系统
- 基于角色的动态权限管理系统
- 通过 Django Admin 界面管理权限，无需修改代码
- 实时权限刷新 API
- 权限管理中心: `/admin/permission-management/`

## 测试用户
- 标注员: qinqiang2000@qq.com / 11111111
- 管理员: qinqiang2000@foxmail.com / 11111111
- 管理员API Token：-H 'Authorization: Token a0534aa47e4be8c03450d3090f475c5eacf68964' 
- 标注员API Token：-H 'Authorization: Token 4f36015cbf62b6af1e37ac91778e5412bec989f9' 

## 开发配置
### 数据库配置
支持多种数据库:
- SQLite (开发推荐)
- PostgreSQL (生产推荐)
- MySQL

### 前端开发
- 使用 Nx 管理 monorepo
- 支持 Hot Module Replacement (HMR)
- Biome 用于代码格式化和检查
- 支持 Storybook 组件开发

### 代码质量工具
- Ruff: Python 代码检查和格式化
- Blue: Python 代码格式化
- Biome: JavaScript/TypeScript 代码检查和格式化
- Pre-commit hooks 用于代码质量检查
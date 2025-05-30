# 公司定制化 Label Studio 开发指南

## 分支管理策略

### 主要分支
- `company-custom`: 公司主分支，包含所有定制化功能
- `develop` (upstream): 跟踪原始 Label Studio 的开发分支
- `feature/*`: 功能开发分支
- `hotfix/*`: 紧急修复分支

## 开发工作流

### 新功能开发
```bash
# 从公司主分支创建功能分支
git checkout company-custom
git pull origin company-custom
git checkout -b feature/your-feature-name

# 开发完成后
git add .
git commit -m "feat: 添加新功能描述"
git push origin feature/your-feature-name

# 创建 Pull Request 到 company-custom 分支
```

### 紧急修复
```bash
# 从公司主分支创建修复分支
git checkout company-custom
git checkout -b hotfix/issue-description

# 修复完成后
git commit -m "fix: 修复问题描述"
git push origin hotfix/issue-description
```

### 与上游同步（可选）
```bash
# 获取上游更新
git fetch upstream
git checkout develop
git merge upstream/develop

# 合并到公司分支（需要谨慎处理冲突）
git checkout company-custom
git merge develop
```

## 构建和部署

### 开发环境
```bash
# 使用提供的构建脚本
./build_and_run.sh
```

### 生产环境
```bash
# 使用 Docker 构建
docker build -t company-label-studio .
docker run -p 8080:8080 company-label-studio
```

## 代码规范

- 所有公司定制化代码应包含注释说明
- 提交信息使用规范格式：feat/fix/docs/style/refactor/test/chore
- 重要配置更改需要更新此文档

## 文件说明

### 已修改的核心文件
- `label_studio/core/utils/common.py`: 核心工具函数修改
- `web/libs/editor/src/tags/control/TextArea/TextArea.jsx`: 文本区域组件定制
- `web/libs/editor/src/tags/control/TextArea/TextArea.scss`: 样式定制
- `web/libs/datamanager/src/sdk/lsf-sdk.js`: SDK 接口修改

### 新增文件
- `build_and_run.sh`: 开发环境构建脚本
- `package.json`: 前端依赖管理
- `yarn.lock`: 依赖版本锁定 
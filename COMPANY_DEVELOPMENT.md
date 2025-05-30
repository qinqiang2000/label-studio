# 公司定制化 Label Studio 开发指南

## 仓库架构

### 远程仓库设置
- `origin`: https://github.com/qinqiang2000/label-studio.git (您的 Fork)
- `upstream`: https://github.com/HumanSignal/label-studio.git (官方原仓库)

### 分支管理策略
- `company-custom`: 公司主分支，包含所有定制化功能
- `develop` (upstream): 跟踪原始 Label Studio 的开发分支
- `feature/*`: 功能开发分支
- `hotfix/*`: 紧急修复分支

## 开发工作流

### 初始设置（已完成）
```bash
# 1. Fork 仓库到 GitHub（已完成）
# 2. 更改远程仓库指向
git remote set-url origin https://github.com/qinqiang2000/label-studio.git

# 3. 添加上游仓库
git remote add upstream https://github.com/HumanSignal/label-studio.git

# 4. 推送公司分支
git push -u origin company-custom
```

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

# 在 GitHub 上创建 Pull Request 到 company-custom 分支
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

### 与上游同步（保持最新）
```bash
# 获取上游更新
git fetch upstream

# 同步 develop 分支
git checkout develop
git merge upstream/develop
git push origin develop

# 合并到公司分支（需要谨慎处理冲突）
git checkout company-custom
git merge develop
# 解决冲突后
git push origin company-custom
```

### 团队协作流程
1. **代码审查**: 所有更改通过 Pull Request 进行
2. **分支保护**: 在 GitHub 设置 `company-custom` 分支保护规则
3. **CI/CD**: 配置自动化测试和部署流程

## GitHub 仓库管理

### 分支保护设置
在 GitHub 仓库设置中启用：
- Require pull request reviews before merging
- Require status checks to pass before merging
- Restrict pushes that create files larger than 100MB

### 标签管理
```bash
# 创建版本标签
git tag -a v1.0.0-company -m "公司定制版本 1.0.0"
git push origin v1.0.0-company
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
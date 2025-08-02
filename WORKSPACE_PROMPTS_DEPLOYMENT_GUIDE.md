# Workspace Prompts 生产发布实施指引

## 概述

本指引提供了 Workspace Prompts 功能在生产环境发布后的完整实施方案。该功能已完全实现并可投入生产使用。

## 功能特性

### ✅ 已实现的核心功能
- **工作区隔离**: Prompts 可按工作区进行隔离访问
- **组织级共享**: 未分配工作区的 Prompts 在组织内全局可见
- **访问控制**: 基于工作区成员身份的权限管理
- **完整的 CRUD 操作**: 创建、读取、更新、删除 Prompts
- **高级配置**: 支持 Temperature 参数和 JSON Schema 配置
- **现代化UI**: 响应式设计，支持全屏编辑和 JSON 折叠

## 生产发布前准备

### 1. 数据库迁移检查

```bash
# 确认以下迁移已正确应用
python manage.py showmigrations prompts workspaces

# 关键迁移文件:
# - prompts.0005_prompt_workspace.py (添加 workspace 外键)
# - workspaces.0001_initial.py (工作区基础架构)
```

### 2. API 端点验证

```bash
# 验证 API 端点可用性
curl -H "Authorization: Token <your-token>" \
     http://your-domain/api/prompts/

curl -H "Authorization: Token <your-token>" \
     http://your-domain/api/workspaces/1/prompts/
```

### 3. 前端构建验证

```bash
cd web/
yarn build
# 确认构建成功且包含以下文件：
# - Prompts.jsx
# - WorkspaceCard.tsx
# - WorkspaceSelector 组件
```

## 发布后实施步骤

### 第一阶段：管理员准备 (发布当天)

#### 1. 创建工作区
```bash
# 作为超级管理员登录系统
# 导航到 /workspaces
# 点击 "Create Workspace"
```

**推荐的初始工作区设置：**
- **开发团队** (Development Team) - 颜色: #1976d2
- **产品团队** (Product Team) - 颜色: #388e3c  
- **数据科学团队** (Data Science Team) - 颜色: #f57c00
- **公共资源** (Shared Resources) - 颜色: #7b1fa2

#### 2. 配置工作区成员
```bash
# 为每个工作区添加相应成员
# 在工作区卡片中点击 "..." -> "Manage Members"
# 添加用户并设置角色
```

### 第二阶段：现有 Prompts 迁移 (发布后 1-2 天)

#### 1. 审计现有 Prompts
```python
# 在 Django shell 中执行
from prompts.models import Prompt

# 查看所有现有 prompts
existing_prompts = Prompt.objects.filter(workspace__isnull=True)
print(f"待迁移的 Prompts 数量: {existing_prompts.count()}")

for prompt in existing_prompts:
    print(f"- {prompt.name} (创建者: {prompt.created_by.email})")
```

#### 2. 批量分配工作区
```python
# 示例：根据创建者邮箱域名自动分配
from workspaces.models import Workspace

# 获取工作区
dev_workspace = Workspace.objects.get(name="Development Team")
product_workspace = Workspace.objects.get(name="Product Team")

# 自动分配逻辑
for prompt in existing_prompts:
    if 'dev' in prompt.created_by.email or 'eng' in prompt.created_by.email:
        prompt.workspace = dev_workspace
    elif 'product' in prompt.created_by.email or 'pm' in prompt.created_by.email:
        prompt.workspace = product_workspace
    # 其他保持为组织级别 (workspace=None)
    prompt.save()
```

### 第三阶段：用户培训和推广 (发布后 1 周)

#### 1. 用户操作指南

**创建新 Prompt：**
1. 导航到 `/prompts`
2. 点击 "Create Prompt"
3. 填写基本信息（名称、内容）
4. **重要**: 选择适当的工作区或保持"组织级别"
5. 配置高级选项（Temperature、Response Schema）

**查看工作区 Prompts：**
1. 导航到 `/workspaces`
2. 在工作区卡片中点击 "Show Prompts"
3. 查看该工作区的所有 Prompts

#### 2. 最佳实践建议

**Prompt 命名规范：**
```
[团队]-[用途]-[版本]
例如：DEV-CodeReview-v1, PROD-UserStory-v2
```

**工作区使用策略：**
- **私有 Prompts**: 分配给特定工作区
- **通用模板**: 保持组织级别，所有人可见
- **实验性 Prompts**: 分配给开发工作区

### 第四阶段：监控和优化 (发布后 2-4 周)

#### 1. 使用情况监控
```python
# 定期检查使用统计
from django.db.models import Count
from prompts.models import Prompt
from workspaces.models import Workspace

# 各工作区 Prompt 统计
stats = Workspace.objects.annotate(
    prompt_count=Count('prompt')
).values('name', 'prompt_count')

for stat in stats:
    print(f"{stat['name']}: {stat['prompt_count']} prompts")
```

#### 2. 权限审计
```python
# 检查无工作区的孤立 prompts
orphaned_prompts = Prompt.objects.filter(
    workspace__isnull=True
).count()
print(f"组织级别 Prompts: {orphaned_prompts}")

# 检查用户访问权限
from django.contrib.auth import get_user_model
User = get_user_model()

for user in User.objects.all():
    accessible_workspaces = user.workspace_set.count()
    print(f"{user.email}: 可访问 {accessible_workspaces} 个工作区")
```

## 故障排除

### 常见问题

#### 1. 用户看不到 Prompts
**症状**: 用户反馈看不到某些 Prompts
**排查步骤**:
```python
# 检查用户工作区成员身份
user = User.objects.get(email='user@example.com')
user_workspaces = user.workspace_set.all()
print(f"用户工作区: {[w.name for w in user_workspaces]}")

# 检查 Prompt 的工作区分配
prompt = Prompt.objects.get(name='问题Prompt名称')
print(f"Prompt 工作区: {prompt.workspace.name if prompt.workspace else '组织级别'}")
```

#### 2. 工作区 Prompts 不显示
**症状**: 工作区卡片中 "Show Prompts" 无内容
**排查步骤**:
```bash
# 检查 API 响应
curl -H "Authorization: Token <token>" \
     http://your-domain/api/workspaces/1/prompts/
```

#### 3. 权限错误
**症状**: 用户无法创建或编辑 Prompts
**解决方案**:
- 确认用户是相关工作区成员
- 检查用户组织权限
- 验证 API 权限设置

### 回滚方案

如果需要回滚 Workspace Prompts 功能：

```python
# 将所有 prompts 设置为组织级别
Prompt.objects.update(workspace=None)
```

**注意**: 这不会删除工作区，只是取消 prompts 的工作区关联。

## 性能监控

### 关键指标

1. **API 响应时间**
   - `/api/prompts/` 列表查询
   - `/api/workspaces/{id}/prompts/` 工作区查询

2. **数据库查询优化**
   - 监控 workspace 相关的 JOIN 查询
   - 确保适当的索引使用

3. **用户体验指标**
   - Prompts 页面加载时间
   - 工作区切换响应时间

## 后续扩展建议

### 短期 (1-3 个月)
- 添加 Prompt 使用统计
- 实现 Prompt 版本控制
- 增加 Prompt 模板功能

### 中期 (3-6 个月)
- 跨工作区 Prompt 共享机制
- Prompt 导入/导出功能
- 高级搜索和过滤

### 长期 (6+ 个月)
- Prompt 效果分析和 A/B 测试
- 智能 Prompt 推荐
- 与 AI 模型的深度集成

## 支持和文档

- **技术文档**: `/docs/prompts/`
- **API 文档**: `/api/docs/`
- **用户手册**: 内置帮助系统
- **问题反馈**: GitHub Issues

---

**发布负责人签名**: _______________  
**发布日期**: _______________  
**版本**: v1.0
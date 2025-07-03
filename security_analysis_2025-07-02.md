# Label Studio Workspace 功能安全分析报告
**分析日期：2025年7月2日**

## 📋 执行概述

本报告对基于 Label Studio 开源项目增加的 workspace 功能进行了深度安全检查。分析重点关注组织间数据隔离和访问控制机制，以确保其他组织用户无法访问不属于他们的 workspace 项目。通过对代码架构、权限控制、数据库查询和API端点的全面审查，识别出多个关键安全漏洞。

## 🏗️ Workspace 架构分析

### 数据模型关系
```
Organization (组织)
    ├── Workspaces (工作空间) - 多个
    │   ├── Projects (项目) - 多个，可选分配到workspace
    │   ├── Members (成员) - 多个用户
    │   └── Tasks/Annotations (任务/标注) - 通过项目间接关联
    └── Users (用户) - 多个，属于组织成员
```

### 关键模型定义

**Workspace Model** (`label_studio/workspaces/models.py`):
```python
class Workspace(models.Model):
    name = models.CharField(max_length=256)
    organization = models.ForeignKey('organizations.Organization', on_delete=models.CASCADE)
    members = models.ManyToManyField(settings.AUTH_USER_MODEL, through='WorkspaceMember')
    is_archived = models.BooleanField(default=False)
    
    class Meta:
        unique_together = ['name', 'organization']
```

**Project-Workspace关系** (`label_studio/projects/migrations/0030_project_workspace.py`):
```python
workspace = models.ForeignKey(
    'workspaces.Workspace',
    on_delete=models.SET_NULL,
    related_name='projects',
    null=True, blank=True
)
```

## ⚠️ 发现的关键安全问题

### 1. **缺乏 Workspace 级别的任务访问控制** - 🔥 **高风险**

**问题描述：** 任务和标注的访问控制仅在组织级别进行过滤，**未实施 workspace 成员验证**。

**影响范围：**
- `tasks/api.py:176` - TaskListAPI 只检查 `project__organization=user.active_organization`
- `tasks/models.py:362-366` - Task.has_permission() 仅验证项目权限，未检查 workspace 成员身份
- `data_manager/managers.py` - TaskManager.for_user() 只过滤组织

**安全风险：** 同一组织内的用户可以访问他们不是成员的 workspace 中的项目任务和标注数据。

**存在问题的代码：**
```python
# label_studio/tasks/api.py:176
def filter_queryset(self, queryset):
    queryset = super().filter_queryset(queryset)
    return queryset.filter(project__organization=self.request.user.active_organization)
    # ❌ 缺少: workspace 成员检查
```

**对比正确实现（projects/api.py）：**
```python
# ✅ 项目 API 有正确的 workspace 过滤
if not user.is_superuser:
    queryset = queryset.filter(
        Q(workspace__isnull=True) |
        Q(workspace__members=user)
    )
```

### 2. **直接任务 API 访问漏洞** - 🔶 **中风险**

**问题描述：** TaskAPI.get_queryset() 通过任务 ID 直接查找，可能绕过 workspace 检查。

**代码位置：** `tasks/api.py:310-326`
```python
def get_queryset(self):
    task_id = self.request.parser_context['kwargs'].get('pk')
    task = generics.get_object_or_404(Task, pk=task_id)  # 直接查找，无workspace检查
    # ... 其余方法
```

**风险：** 如果用户知道任务ID，可能直接访问而无需适当的 workspace 授权检查。

### 3. **注释访问控制问题** - 🔶 **中风险**

**代码位置：** `tasks/api.py:526`
```python
def get_queryset(self):
    task = generics.get_object_or_404(Task.objects.for_user(self.request.user), pk=self.kwargs.get('pk', 0))
    return Annotation.objects.filter(Q(task=task) & Q(was_cancelled=False)).order_by('pk')
```

虽然使用了 `Task.objects.for_user()`，但这仍然只检查组织成员身份，不检查 workspace 成员身份。

### 4. **批量操作安全隐患** - 🔶 **中风险**

**问题描述：** 数据管理器的批量操作系统除了基本的组织过滤外，似乎没有额外的 workspace 级别安全检查。

**潜在漏洞：**
- 批量删除操作可能影响跨 workspace 边界的任务
- 批量标注操作可能在 workspace 间泄露数据  
- 数据导出操作可能包含未授权 workspace 的任务

**代码位置：** `data_manager/actions/basic.py`

### 5. **项目-任务关系验证不足** - 🔷 **低-中风险**

**代码位置：** `tasks/api.py:185-191`
```python
def perform_create(self, serializer):
    project_id = self.request.data.get('project')
    project = generics.get_object_or_404(Project, pk=project_id)  # 无workspace检查
    instance = serializer.save(project=project)
```

创建任务时，没有验证用户是否有权访问指定项目的 workspace。

### 6. **管理权限过度集中** - 🔷 **低风险**

**问题描述：** 所有 workspace 管理操作都需要超级用户权限，限制了管理灵活性。

**影响功能：** (`workspaces/api.py`)
```python
def check_admin_permission(self):
    """Check if user has admin permissions (superuser)"""
    if not self.request.user.is_superuser:
        raise PermissionDenied("Only administrators can perform this action")
```

- 创建/编辑/删除 workspace
- 添加/移除成员
- 归档/取消归档

## ✅ 安全优势

### 1. **强大的组织级别隔离**
- 所有数据访问都严格限制在用户的 `active_organization` 内
- 跨组织数据泄露风险极低
- 一致的组织边界执行

### 2. **项目级别的正确访问控制**
工作空间系统确实在项目级别有适当的访问控制：

```python
# workspaces/api.py:48-49
if not user.is_superuser:
    queryset = queryset.filter(members=user)
```

### 3. **数据库完整性保护**
- Workspace 删除时项目引用设置为 NULL (`on_delete=models.SET_NULL`)
- 唯一约束防止同组织内重名 workspace (`unique_together = ['name', 'organization']`)

### 4. **安全的成员管理**
- 添加成员时验证用户属于同一组织
- 通过中间模型 `WorkspaceMember` 管理成员关系

## 🛡️ 安全修复建议

### 1. **实现 Workspace 感知的任务过滤** - 🔥 **紧急**

**修复位置：** `tasks/api.py`
```python
def filter_queryset(self, queryset):
    queryset = super().filter_queryset(queryset)
    user = self.request.user
    
    # 组织级别过滤（现有）
    queryset = queryset.filter(project__organization=user.active_organization)
    
    # 新增：Workspace 级别过滤
    if not user.is_superuser:
        queryset = queryset.filter(
            Q(project__workspace__isnull=True) |  # 无workspace的项目
            Q(project__workspace__members=user)   # 用户所属workspace的项目
        )
    
    return queryset
```

### 2. **增强任务权限检查**

**修复位置：** `tasks/models.py`
```python
def has_permission(self, user: 'User') -> bool:
    # 现有检查
    mixin_has_permission = cast(bool, super().has_permission(user))
    project_has_permission = self.project.has_permission(user)
    
    # 新增：Workspace 权限检查
    workspace_has_permission = True
    if self.project.workspace:
        workspace_has_permission = (
            self.project.workspace.has_member(user) or user.is_superuser
        )
    
    user.project = self.project
    return (mixin_has_permission and 
            project_has_permission and 
            workspace_has_permission)
```

### 3. **修复直接任务访问**

**修复位置：** `tasks/api.py`
```python
def get_object(self):
    task_id = self.kwargs.get('pk')
    user = self.request.user
    
    # 应用workspace过滤的查询集
    queryset = Task.objects.filter(project__organization=user.active_organization)
    if not user.is_superuser:
        queryset = queryset.filter(
            Q(project__workspace__isnull=True) |
            Q(project__workspace__members=user)
        )
    
    return generics.get_object_or_404(queryset, pk=task_id)
```

### 4. **审计批量操作**

需要审查 `data_manager/actions/` 中所有批量操作，确保遵守 workspace 边界：

```python
# 在批量操作中添加workspace检查
def get_queryset_for_action(user, project_ids):
    queryset = Task.objects.filter(
        project__organization=user.active_organization,
        project__in=project_ids
    )
    
    if not user.is_superuser:
        queryset = queryset.filter(
            Q(project__workspace__isnull=True) |
            Q(project__workspace__members=user)
        )
    
    return queryset
```

### 5. **项目创建验证**

**修复位置：** `tasks/api.py`
```python
def perform_create(self, serializer):
    project_id = self.request.data.get('project')
    user = self.request.user
    
    # 验证用户对项目的访问权限
    project_queryset = Project.objects.filter(organization=user.active_organization)
    if not user.is_superuser:
        project_queryset = project_queryset.filter(
            Q(workspace__isnull=True) |
            Q(workspace__members=user)
        )
    
    project = generics.get_object_or_404(project_queryset, pk=project_id)
    instance = serializer.save(project=project)
```

### 6. **实施统一访问控制中间件**

创建 workspace 访问控制装饰器，在所有相关 API 端点统一应用：

```python
# 新文件: core/workspace_permissions.py
def workspace_permission_required(view_func):
    """确保用户对workspace有适当访问权限的装饰器"""
    def wrapper(self, *args, **kwargs):
        # 实施workspace权限检查逻辑
        return view_func(self, *args, **kwargs)
    return wrapper
```

## 🧪 建议的安全测试

### 1. **跨 Workspace 访问测试**
```python
# 测试场景
def test_cross_workspace_access():
    # 创建同组织内不同 workspace 的用户
    user_a = create_user_in_workspace(workspace_a)
    user_b = create_user_in_workspace(workspace_b)
    
    # 验证用户A无法访问workspace B的任务
    task_in_b = create_task_in_workspace(workspace_b)
    
    # 这应该返回404或权限错误
    response = api_client.get(f'/api/tasks/{task_in_b.id}/', user=user_a)
    assert response.status_code in [403, 404]
```

### 2. **任务ID枚举测试**
```python
def test_task_id_enumeration():
    # 验证用户无法通过猜测任务ID访问其他workspace的数据
    for task_id in range(1, 1000):
        response = api_client.get(f'/api/tasks/{task_id}/', user=unauthorized_user)
        assert response.status_code in [403, 404]
```

### 3. **批量操作测试**
```python
def test_bulk_operations_workspace_isolation():
    # 验证批量操作不会影响未授权的workspace
    bulk_action_data = {
        'action': 'delete_tasks',
        'selected_items': {'all': True, 'included': [task_ids_from_other_workspace]}
    }
    
    response = api_client.post('/api/dm/actions/', data=bulk_action_data)
    # 应该只影响用户有权限的任务
```

### 4. **数据导出安全测试**
```python
def test_export_data_isolation():
    # 确认数据导出不会泄露跨workspace数据
    response = api_client.get('/api/projects/1/export/', user=limited_user)
    exported_data = response.json()
    
    # 验证导出的数据只包含授权的workspace任务
    for task in exported_data:
        assert user_has_workspace_access(limited_user, task['project'])
```

## 📊 风险评估总结

| 风险等级 | 问题数量 | 主要影响 | 紧急程度 |
|---------|---------|---------|----------|
| 🔥 高风险 | 1 | 跨 workspace 数据访问 | 立即修复 |
| 🔶 中风险 | 3 | 权限绕过、批量操作、直接访问 | 1-2周内修复 |
| 🔷 低风险 | 2 | 管理灵活性限制、创建验证 | 1个月内修复 |

## 🎯 修复优先级建议

### 立即修复 (0-3天)
1. **实现任务级别的 workspace 成员检查** - 修复核心访问控制漏洞
2. **修复直接任务API访问** - 防止权限绕过

### 短期内修复 (1-2周)
3. **审计和修复批量操作安全问题** - 防止大规模数据泄露
4. **增强注释访问控制** - 确保标注数据安全

### 中期修复 (2-4周)
5. **实施统一的 workspace 访问控制中间件** - 标准化权限检查
6. **增强项目创建验证** - 防止未授权项目操作

### 长期改进 (1-3个月)
7. **考虑实现更细粒度的角色权限系统** - 提升管理灵活性
8. **添加审计日志功能** - 跟踪跨workspace访问尝试

## 📈 安全监控建议

### 1. **实施访问日志记录**
```python
# 记录所有workspace访问尝试
logger.warning(f"User {user.id} attempted to access workspace {workspace.id} without permission")
```

### 2. **设置安全警报**
- 监控跨workspace访问尝试
- 检测异常的批量操作模式
- 跟踪任务ID枚举尝试

### 3. **定期安全审计**
- 每季度审查workspace成员身份
- 验证孤立项目的访问权限
- 检查超级用户权限使用

## 🔒 结论

虽然 Label Studio 的 workspace 功能在项目级别具有良好的组织隔离和适当的访问控制，但在任务和标注级别存在**重大安全漏洞**。核心问题是任务访问控制仅在组织级别实施，未验证 workspace 成员身份，这在多租户环境中创造了显著的数据泄露风险。

**关键发现：**
- ✅ 组织级别隔离执行良好
- ✅ 项目访问控制正确实施
- ❌ **任务/标注级别缺少workspace权限检查**
- ❌ 批量操作可能绕过workspace边界
- ❌ 直接API访问可能导致权限升级

**修复后的安全状态：** 实施建议的修复措施后，系统将提供强大的多层安全保护，确保组织内不同workspace间的完全数据隔离，满足企业级多租户安全要求。

---

**报告生成时间：** 2025年7月2日  
**分析工具：** Claude Code by Anthropic  
**代码版本：** company-custom 分支 (commit: 8f05082)
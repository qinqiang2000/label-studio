# Label Studio 权限系统操作指引

## 📖 概述

本指引基于当前权限系统的实现状态，详细说明如何添加菜单权限、角色和权限配置。权限系统目前主要控制**前端菜单的显示/隐藏**，后续将逐步扩展到API权限和操作权限控制。

## 🎯 当前权限系统能力

### ✅ 已实现功能
- **菜单权限控制**: 主菜单和项目设置菜单的显示/隐藏
- **角色管理**: 动态角色系统（superuser、annotator、workspace_admin）
- **权限管理**: 可通过Django管理后台管理权限分配
- **用户权限**: 自动权限获取和检查

### ❌ 当前局限性
- **API权限**: 后端API尚未集成权限验证
- **操作权限**: 页面内按钮和操作权限控制待实现
- **数据权限**: 细粒度数据访问控制待开发

## 🏗️ 系统架构

### 数据模型关系
```
User (用户)
├── role (外键) → Role (角色)
└── is_superuser (布尔值)

Role (角色)
├── name (英文标识符，如: annotator)
├── display_name (中文名称，如: 标注员)
└── permissions (多对多) → RolePermission → Permission

Permission (权限)
├── name (英文标识符，如: view_home)
├── display_name (中文名称，如: Home菜单查看)
└── category (分类: menu/action/admin)
```

### 权限检查流程
```
用户访问页面
    ↓
前端调用 usePermissions() Hook
    ↓
检查用户权限列表 (从API获取)
    ↓
根据权限控制菜单显示/隐藏
```

## 📝 操作指引

### 1. 添加新菜单权限

#### 场景：为系统添加"数据统计"菜单

#### 步骤一：后端添加权限定义

**1.1 在权限常量中添加新权限**

编辑文件：`label_studio/users/utils/permissions.py`

```python
# 菜单权限常量
MENU_PERMISSIONS = {
    'HOME': 'view_home',
    'PROJECTS': 'view_projects',
    'WORKSPACES': 'view_workspaces',
    'PROMPTS': 'view_prompts',
    'ORGANIZATION': 'view_organization',
    
    # 新增：数据统计菜单权限
    'DATA_ANALYTICS': 'view_data_analytics',
    
    # ... 其他权限
}
```

**1.2 更新角色权限配置**

在同一文件中，更新 `DEFAULT_ROLE_PERMISSIONS`：

```python
DEFAULT_ROLE_PERMISSIONS = {
    'superuser': {
        'permissions': [
            # 所有现有权限 +
            'view_data_analytics',  # 超级管理员拥有数据统计权限
            # ...
        ],
    },
    
    'annotator': {
        'permissions': [
            # 现有权限（不包含数据统计权限）
            # ...
        ],
    },
    
    'workspace_admin': {
        'permissions': [
            # 现有权限 +
            'view_data_analytics',  # 工作空间管理员拥有数据统计权限
            # ...
        ],
    },
}
```

**1.3 创建数据库权限记录**

运行管理命令重新初始化权限：

```bash
cd label_studio
python manage.py init_role_permissions --reset
```

#### 步骤二：前端添加权限定义

**2.1 添加前端权限常量**

编辑文件：`web/apps/labelstudio/src/utils/permissions.js`

```javascript
// 菜单权限常量
export const MENU_PERMISSIONS = {
  HOME: 'view_home',
  PROJECTS: 'view_projects',
  WORKSPACES: 'view_workspaces',
  PROMPTS: 'view_prompts',
  ORGANIZATION: 'view_organization',
  
  // 新增：数据统计菜单权限
  DATA_ANALYTICS: 'view_data_analytics',
  
  // ... 其他权限
};
```

**2.2 添加权限检查方法**

编辑文件：`web/apps/labelstudio/src/hooks/usePermissions.js`

```javascript
// 菜单权限检查
const menuPermissions = useMemo(() => ({
  // 现有权限检查方法
  canViewHome: () => permissionChecker.hasPermission(MENU_PERMISSIONS.HOME),
  canViewProjects: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECTS),
  // ...
  
  // 新增：数据统计权限检查
  canViewDataAnalytics: () => permissionChecker.hasPermission(MENU_PERMISSIONS.DATA_ANALYTICS),
  
}), [permissionChecker]);
```

#### 步骤三：前端菜单集成

**3.1 主菜单添加权限检查**

编辑文件：`web/apps/labelstudio/src/components/Menubar/Menubar.jsx`

```jsx
// 在合适的位置添加菜单项
{permissions.menu.canViewDataAnalytics() && (
  <Menu.Item 
    label="数据统计" 
    to="/data-analytics" 
    icon={<IconChart />} 
    exact 
  />
)}
```

### 2. 添加新角色

#### 方法一：通过Django管理后台

1. 访问 `/admin/users/role/`
2. 点击"Add Role"
3. 填写信息：
   - **Name**: 英文标识符（如：`data_analyst`）
   - **Display name**: 中文名称（如：`数据分析师`）
   - **Description**: 角色描述
   - **Is active**: 勾选
4. 保存后，转到 `/admin/users/rolepermission/` 为新角色分配权限

#### 方法二：通过管理命令

**2.1 创建角色定义脚本**

创建文件：`label_studio/users/management/commands/create_data_analyst_role.py`

```python
from django.core.management.base import BaseCommand
from users.models import Role, Permission, RolePermission

class Command(BaseCommand):
    help = '创建数据分析师角色'

    def handle(self, *args, **options):
        # 创建角色
        role, created = Role.objects.get_or_create(
            name='data_analyst',
            defaults={
                'display_name': '数据分析师',
                'description': '拥有数据查看和分析权限',
                'is_active': True
            }
        )
        
        if created:
            self.stdout.write(f'✓ 创建角色: {role.display_name}')
        else:
            self.stdout.write(f'✓ 角色已存在: {role.display_name}')
        
        # 分配权限
        permission_names = [
            'view_home',
            'view_projects', 
            'view_data_analytics',
            'view_account_settings'
        ]
        
        for perm_name in permission_names:
            try:
                permission = Permission.objects.get(name=perm_name)
                role_perm, created = RolePermission.objects.get_or_create(
                    role=role,
                    permission=permission,
                    defaults={'granted': True}
                )
                if created:
                    self.stdout.write(f'  ✓ 分配权限: {perm_name}')
            except Permission.DoesNotExist:
                self.stdout.write(f'  ❌ 权限不存在: {perm_name}')
```

**2.2 执行命令**

```bash
cd label_studio
python manage.py create_data_analyst_role
```

### 3. 添加新权限

#### 3.1 权限命名规范

| 权限类型 | 命名格式 | 示例 |
|---------|---------|------|
| 菜单权限 | `view_[菜单名]` | `view_reports`, `view_settings` |
| 操作权限 | `[动作]_[对象]` | `create_project`, `delete_task` |
| 管理权限 | `manage_[对象]` | `manage_users`, `manage_roles` |

#### 3.2 权限分类

- **menu**: 菜单访问权限
- **action**: 操作执行权限  
- **admin**: 管理功能权限
- **data**: 数据访问权限

#### 3.3 添加步骤

1. **更新后端权限常量**（`users/utils/permissions.py`）
2. **运行初始化命令**创建数据库记录
3. **更新前端权限常量**（`src/utils/permissions.js`）
4. **添加权限检查方法**（`src/hooks/usePermissions.js`）
5. **在组件中使用权限检查**

### 4. 用户角色管理

#### 4.1 为用户分配角色

**通过管理后台：**
1. 访问 `/admin/users/user/`
2. 编辑用户，选择对应的Role
3. 保存

**通过管理命令：**
```bash
# 为特定用户分配角色
cd label_studio
python manage.py shell -c "
from users.models import User, Role
user = User.objects.get(email='user@example.com')
role = Role.objects.get(name='data_analyst')
user.role = role
user.save()
print(f'✓ 为用户 {user.email} 分配角色 {role.display_name}')
"
```

#### 4.2 批量角色分配

使用现有的 `assign_default_roles` 命令可以为没有角色的用户批量分配默认角色。

## 🔧 完整示例：添加"报表管理"菜单

### 后端代码修改

**1. 更新权限常量** (`users/utils/permissions.py`)

```python
MENU_PERMISSIONS = {
    # ... 现有权限
    'REPORTS': 'view_reports',
}

DEFAULT_ROLE_PERMISSIONS = {
    'superuser': {
        'permissions': [
            # ... 现有权限
            'view_reports',
        ],
    },
    'workspace_admin': {
        'permissions': [
            # ... 现有权限  
            'view_reports',
        ],
    },
    # annotator 不包含此权限
}
```

**2. 初始化权限数据**

```bash
cd label_studio
python manage.py init_role_permissions --reset
```

### 前端代码修改

**1. 添加权限常量** (`src/utils/permissions.js`)

```javascript
export const MENU_PERMISSIONS = {
  // ... 现有权限
  REPORTS: 'view_reports',
};
```

**2. 添加权限检查** (`src/hooks/usePermissions.js`)

```javascript
const menuPermissions = useMemo(() => ({
  // ... 现有方法
  canViewReports: () => permissionChecker.hasPermission(MENU_PERMISSIONS.REPORTS),
}), [permissionChecker]);
```

**3. 菜单集成** (`src/components/Menubar/Menubar.jsx`)

```jsx
{permissions.menu.canViewReports() && (
  <Menu.Item 
    label="报表管理" 
    to="/reports" 
    icon={<IconReport />} 
    exact 
  />
)}
```

### 验证结果

1. **超级管理员**：能看到"报表管理"菜单
2. **工作空间管理员**：能看到"报表管理"菜单  
3. **标注员**：看不到"报表管理"菜单

## ⚠️ 注意事项

### 开发注意事项

1. **权限名称一致性**：确保后端和前端的权限标识符完全一致
2. **权限粒度**：建议菜单权限和操作权限分开定义
3. **默认权限**：新权限需要明确哪些角色默认拥有
4. **测试验证**：每次添加权限后都要测试不同角色的访问效果

### 当前系统局限性

1. **仅控制菜单显示**：目前只能控制前端菜单的显示/隐藏
2. **无API权限验证**：后端API尚未集成权限检查
3. **无操作权限控制**：页面内的按钮、表单等操作权限待实现
4. **无数据级权限**：细粒度的数据访问控制待开发

### 最佳实践

1. **权限命名**：使用清晰、一致的命名规范
2. **权限分类**：合理使用权限分类，便于管理
3. **渐进式扩展**：先实现菜单权限，再逐步扩展到操作权限
4. **文档更新**：每次修改权限系统都要更新此指引

## 🚀 未来规划

随着权限系统的逐步完善，本指引将扩展包含：

- **API权限验证**：后端接口权限装饰器使用指引
- **操作权限控制**：按钮、表单字段权限控制方法
- **数据级权限**：基于用户角色的数据过滤机制
- **权限测试**：自动化权限测试用例编写指南

---

**文档版本**：v1.0  
**更新时间**：2025-08-02  
**适用系统**：Label Studio权限系统 v0.1  
**维护者**：开发团队
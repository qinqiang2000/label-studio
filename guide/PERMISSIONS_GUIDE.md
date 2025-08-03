# Label Studio 权限系统操作指引 v3.0

## 📖 概述

本指引详细说明Label Studio优化后的权限管理系统。新系统采用**配置驱动**的方式，通过权限组和继承机制，大大简化了权限管理的复杂度，并提供了可视化的权限管理界面。

## 🎯 权限系统能力

### ✅ 已实现功能
- **配置驱动权限管理**: 单一配置文件管理所有权限
- **权限组和继承**: 支持权限组批量管理和角色继承
- **自动生成常量和方法**: 基于配置自动生成前端权限检查代码
- **智能权限组件**: 支持按钮、字段、页面操作的权限控制
- **菜单权限控制**: 主菜单和项目设置菜单的显示/隐藏
- **页面操作权限**: 按钮和操作的显示/隐藏/禁用控制
- **角色管理**: 动态角色系统，支持继承和权限组
- **可视化权限管理**: Django Admin集成的权限管理中心
- **实时权限刷新**: 支持无需重启的权限配置更新
- **权限包管理**: 支持权限包的批量添加和移除

### 🚀 系统优势
- **维护简单**: 新增权限只需修改1-2个配置文件
- **自动生成**: 权限常量和检查方法完全自动生成
- **灵活配置**: 支持权限组、继承、自定义权限组合
- **智能组件**: 提供开箱即用的权限控制组件
- **可视化管理**: 通过Django Admin界面进行权限管理
- **即时生效**: 权限变更无需重启服务器即可生效

## 🏗️ 系统架构

### 配置文件结构
```
web/apps/labelstudio/src/config/permissions.js
└── 权限配置中心
    ├── PERMISSION_DEFINITIONS (权限定义)
    ├── PERMISSION_GROUPS (权限组)
    └── ROLE_PERMISSION_CONFIG (角色配置)

label_studio/users/utils/permissions.py
└── 后端权限配置
    ├── PERMISSION_GROUPS (权限组)
    └── ROLE_PERMISSION_CONFIG (角色配置)
```

### 权限组架构
```
basic_user (基础用户)
├── view_home
├── view_projects  
├── view_workspaces
└── view_account_settings

annotation_operations (标注操作)
├── create_annotation
├── edit_annotation
└── delete_annotation

project_management (项目管理)
├── create_project
├── edit_project
├── delete_project
├── export_project_data
└── import_project_data

workspace_management (工作空间管理)
├── manage_workspaces
├── create_workspace
├── edit_workspace
├── delete_workspace
└── manage_workspace_members
```

### 角色继承关系
```
annotator (标注员)
├── basic_user
├── annotation_operations  
└── project_basic_settings

workspace_admin (工作空间管理员)
├── 继承 annotator 的所有权限
├── project_management
├── workspace_management
├── project_advanced_settings
└── page_operations

superuser (超级管理员)
└── 所有权限组 (groups: 'all')
```

## 🎛️ 权限管理中心

### 访问权限管理中心

1. **通过Django Admin访问**:
   - 访问 `http://your-domain/admin/`
   - 登录管理员账户
   - 在首页顶部点击「🔐 权限管理中心」

2. **直接访问**:
   - 直接访问 `http://your-domain/admin/permission-management/`

### 权限管理中心功能

- **统计信息**: 查看系统总角色数、权限数、用户数等统计
- **角色权限矩阵**: 可视化展示所有角色及其权限配置
- **权限包管理**: 支持快速添加/移除权限包（如项目创建、工作空间管理等）
- **实时权限开关**: 支持单个权限的开启/关闭，即时生效
- **权限搜索**: 支持按权限名称快速搜索和过滤

## 📝 开发人员操作指引

### 快速参考

#### 添加新菜单权限（最常用）
1. **配置权限**：在 `web/apps/labelstudio/src/config/permissions.js` 和 `label_studio/users/utils/permissions.py` 中添加权限定义
2. **更新管理命令**：在 `init_role_permissions.py` 中添加权限数据
3. **应用配置**：运行 `python manage.py init_role_permissions`
4. **前端使用**：通过 `usePermissions().menu.canViewXxx()` 检查权限

#### 添加新操作权限
1. **配置权限**：同上，category设为'action'
2. **前端使用**：通过 `SmartButton` 组件或 `useButtonPermissions()` Hook

#### 快速权限配置示例
```javascript
// 1. 权限定义
'view_my_feature': {
  'display_name': '我的功能菜单',
  'category': 'menu',
  'hookMethod': 'canViewMyFeature'
},

// 2. 权限组
'my_feature_group': ['view_my_feature', 'create_my_feature'],

// 3. 角色配置  
'workspace_admin': {
  'groups': [..., 'my_feature_group']
}
```

### 1. 添加新权限（详细步骤）

#### 场景：添加"数据分析"相关权限

**步骤一：前端配置**

编辑 `web/apps/labelstudio/src/config/permissions.js`：

```javascript
// 1. 添加权限定义
export const PERMISSION_DEFINITIONS = {
  // ... 现有权限定义
  
  // 新增数据分析权限
  'view_data_analytics': {
    'display_name': '数据分析菜单',
    'description': '查看数据分析菜单的权限',
    'category': 'menu',
    'hookMethod': 'canViewDataAnalytics'
  },
  'export_analytics_report': {
    'display_name': '导出分析报告',
    'description': '导出数据分析报告的权限',
    'category': 'action', 
    'hookMethod': 'canExportAnalyticsReport'
  },
  'show_analytics_export_button': {
    'display_name': '显示导出分析按钮',
    'description': '控制分析报告导出按钮的显示',
    'category': 'page_operation',
    'hookMethod': 'canShowAnalyticsExportButton'
  }
};

// 2. 创建或更新权限组
export const PERMISSION_GROUPS = {
  // ... 现有权限组
  
  // 新增数据分析权限组
  'data_analytics': [
    'view_data_analytics',
    'export_analytics_report', 
    'show_analytics_export_button'
  ]
};

// 3. 更新角色配置
export const ROLE_PERMISSION_CONFIG = {
  'annotator': {
    'groups': ['basic_user', 'annotation_operations', 'project_basic_settings'],
    // annotator 不包含数据分析权限
  },
  
  'workspace_admin': {
    'inherit_from': 'annotator',
    'groups': [
      'project_management', 
      'workspace_management', 
      'project_advanced_settings',
      'page_operations',
      'data_analytics'  // 新增数据分析权限组
    ],
  },
  
  'superuser': {
    'groups': 'all',  // 自动包含所有权限
  }
};
```

**步骤二：后端配置**

编辑 `label_studio/users/utils/permissions.py`：

```python
# 1. 添加权限组
PERMISSION_GROUPS = {
    # ... 现有权限组
    
    # 新增数据分析权限组
    'data_analytics': [
        'view_data_analytics',
        'export_analytics_report',
        'show_analytics_export_button',
    ],
}

# 2. 更新角色配置（与前端保持一致）
ROLE_PERMISSION_CONFIG = {
    'annotator': {
        'groups': ['basic_user', 'annotation_operations', 'project_basic_settings'],
    },
    
    'workspace_admin': {
        'inherit_from': 'annotator',
        'groups': [
            'project_management', 
            'workspace_management', 
            'project_advanced_settings',
            'page_operations',
            'data_analytics'  # 新增数据分析权限组
        ],
    },
    
    'superuser': {
        'groups': 'all',
    }
}
```

**步骤三：更新管理命令**

编辑 `label_studio/users/management/commands/init_role_permissions.py`，在 `permissions_data` 列表中添加新权限：

```python
permissions_data = [
    # ... 现有权限定义
    
    # 新增数据分析权限
    ('view_data_analytics', '数据分析菜单', '查看数据分析菜单的权限', 'menu'),
    ('export_analytics_report', '导出分析报告', '导出数据分析报告的权限', 'action'),
    ('show_analytics_export_button', '显示导出分析按钮', '控制分析报告导出按钮的显示', 'page_operation'),
]
```

**步骤四：应用配置**

```bash
# 重新生成权限数据
source /Users/qinqiang02/Library/Caches/pypoetry/virtualenvs/label-studio-ofHy_tK8-py3.12/bin/activate
cd label_studio
python manage.py init_role_permissions --reset
```

**步骤五：前端使用**

```jsx
// 1. 菜单中使用
import { usePermissions } from '../../hooks/usePermissions';

const { menu } = usePermissions();

// 菜单项
{menu.canViewDataAnalytics() && (
  <Menu.Item 
    label="数据分析" 
    to="/data-analytics" 
    icon={<IconChart />} 
  />
)}

// 2. 按钮中使用  
import { SmartButton } from '../../components/SmartPermission/SmartButton';

<SmartButton
  permission="show_analytics_export_button"
  onClick={handleExportReport}
  look="primary"
  fallback="disable"
  tooltipText="您没有导出报告的权限"
>
  导出报告
</SmartButton>

// 3. 操作权限检查
import { useButtonPermissions } from '../../hooks/useButtonPermissions';

const { canExportAnalyticsReport } = useButtonPermissions();

if (canExportAnalyticsReport) {
  // 执行导出操作
}
```

### 2. 添加新角色

#### 场景：添加"数据分析师"角色

**步骤一：配置定义**

编辑前后端配置文件，添加新角色：

```javascript
// 前端: web/apps/labelstudio/src/config/permissions.js
export const ROLE_PERMISSION_CONFIG = {
  // ... 现有角色
  
  'data_analyst': {
    'inherit_from': 'annotator',  // 继承标注员权限
    'groups': ['data_analytics'],  // 额外拥有数据分析权限组
    'additional_permissions': ['view_organization'], // 额外单个权限
    'description': '数据分析师，拥有数据分析和基础标注权限',
  }
};
```

```python
# 后端: label_studio/users/utils/permissions.py
ROLE_PERMISSION_CONFIG = {
    # ... 现有角色
    
    'data_analyst': {
        'inherit_from': 'annotator',
        'groups': ['data_analytics'],
        'additional_permissions': ['view_organization'],
        'description': '数据分析师，拥有数据分析和基础标注权限',
    }
}
```

**步骤二：更新管理命令**

编辑 `label_studio/users/management/commands/init_role_permissions.py`：

```python
def create_roles(self):
    roles_data = [
        ('superuser', '超级管理员', '系统超级管理员，拥有所有权限'),
        ('annotator', '标注员', '标注员，拥有基础的标注和项目访问权限'),
        ('workspace_admin', '工作空间管理员', '工作空间管理员，可以管理所属工作空间的项目和成员'),
        # 新增角色
        ('data_analyst', '数据分析师', '数据分析师，拥有数据分析和基础标注权限'),
    ]
```

**步骤三：应用配置**

```bash
# 重新生成角色和权限
cd label_studio  
python manage.py init_role_permissions --reset
```

### 3. 创建权限组

#### 场景：创建"报表管理"权限组

**步骤一：定义权限组**

```javascript
// 前端配置
export const PERMISSION_GROUPS = {
  // ... 现有权限组
  
  'report_management': [
    'view_reports',
    'create_report',
    'edit_report', 
    'delete_report',
    'export_report',
    'show_create_report_button',
    'show_delete_report_button'
  ]
};
```

**步骤二：分配给角色**

```javascript
export const ROLE_PERMISSION_CONFIG = {
  'workspace_admin': {
    'inherit_from': 'annotator',
    'groups': [
      'project_management',
      'workspace_management', 
      'project_advanced_settings',
      'page_operations',
      'report_management'  // 新增权限组
    ],
  },
};
```

### 4. 使用智能权限组件

#### SmartButton - 智能按钮

```jsx
import { SmartButton } from '../../components/SmartPermission/SmartButton';

// 隐藏模式：无权限时隐藏按钮
<SmartButton
  permission="show_create_project_button"
  onClick={handleCreateProject}
  look="primary"
  fallback="hide"
>
  创建项目
</SmartButton>

// 禁用模式：无权限时禁用按钮
<SmartButton
  permission="show_delete_project_button"
  onClick={handleDeleteProject}
  look="destructive"
  fallback="disable"
>
  删除项目
</SmartButton>

// 提示模式：无权限时显示tooltip
<SmartButton
  permission="show_export_project_button"
  onClick={handleExportProject}
  look="primary"
  fallback="tooltip"
  tooltipText="您没有导出项目的权限"
>
  导出项目
</SmartButton>
```

#### PermissionGuard - 权限守卫

```jsx
import { PermissionGuard } from '../../components/SmartPermission/PermissionGuard';

// 简单权限检查
<PermissionGuard permission="view_organization">
  <OrganizationSettings />
</PermissionGuard>

// 多权限检查（AND逻辑）
<PermissionGuard permissions={['edit_project', 'manage_project_settings']}>
  <ProjectSettingsPanel />
</PermissionGuard>

// 多权限检查（OR逻辑）
<PermissionGuard 
  permissions={['manage_users', 'manage_roles']} 
  requireAll={false}
>
  <UserManagementPanel />
</PermissionGuard>

// 自定义fallback
<PermissionGuard 
  permission="view_advanced_settings"
  fallback={<div>您没有访问高级设置的权限</div>}
>
  <AdvancedSettings />
</PermissionGuard>
```

#### SmartField - 智能表单字段

```jsx
import { SmartField } from '../../components/SmartPermission/SmartField';

// 只读模式
<SmartField
  fieldPermission="edit_project_danger_zone_fields"
  fallback="readonly"
>
  <Input 
    label="项目删除设置"
    value={dangerZoneSettings}
    onChange={handleDangerZoneChange}
  />
</SmartField>

// 隐藏模式
<SmartField
  fieldPermission="edit_organization_settings"
  fallback="hide"
>
  <OrganizationConfigPanel />
</SmartField>
```

### 5. 权限Hook使用

```jsx
import { usePermissions } from '../../hooks/usePermissions';
import { useButtonPermissions } from '../../hooks/useButtonPermissions';
import { useFieldPermissions } from '../../hooks/useFieldPermissions';

const MyComponent = () => {
  // 基础权限检查
  const permissions = usePermissions();
  
  // 按钮权限（便捷方法）
  const buttonPermissions = useButtonPermissions();
  
  // 字段权限（便捷方法）
  const fieldPermissions = useFieldPermissions();
  
  return (
    <div>
      {/* 菜单权限 */}
      {permissions.menu.canViewOrganization() && (
        <Link to="/organization">组织管理</Link>
      )}
      
      {/* 操作权限 */}
      {permissions.action.canCreateProject() && (
        <Button onClick={createProject}>创建项目</Button>
      )}
      
      {/* 按钮权限（便捷方法）*/}
      {buttonPermissions.createProject && (
        <Button onClick={createProject}>创建项目</Button>
      )}
      
      {/* 字段权限 */}
      <Input 
        disabled={!fieldPermissions.canEditProjectDangerZoneFields}
        value={settings}
        onChange={handleChange}
      />
      
      {/* 权限组合检查 */}
      {permissions.hasAnyPermission(['create_project', 'edit_project']) && (
        <ProjectManagementPanel />
      )}
      
      {/* 分类权限检查 */}
      {permissions.hasAnyPermissionInCategory('admin') && (
        <AdminPanel />
      )}
    </div>
  );
};
```

## 🔧 完整示例：添加"工作流管理"功能

### 1. 权限定义

```javascript
// web/apps/labelstudio/src/config/permissions.js
export const PERMISSION_DEFINITIONS = {
  // ... 现有定义
  
  // 工作流相关权限
  'view_workflows': {
    'display_name': '工作流菜单',
    'description': '查看工作流管理菜单',
    'category': 'menu',
    'hookMethod': 'canViewWorkflows'
  },
  'create_workflow': {
    'display_name': '创建工作流',
    'description': '创建新工作流的权限',
    'category': 'action',
    'hookMethod': 'canCreateWorkflow'
  },
  'edit_workflow': {
    'display_name': '编辑工作流',
    'description': '编辑工作流配置的权限',
    'category': 'action',
    'hookMethod': 'canEditWorkflow'
  },
  'delete_workflow': {
    'display_name': '删除工作流',
    'description': '删除工作流的权限',
    'category': 'action',
    'hookMethod': 'canDeleteWorkflow'
  },
  'show_create_workflow_button': {
    'display_name': '显示创建工作流按钮',
    'description': '控制创建工作流按钮的显示',
    'category': 'page_operation',
    'hookMethod': 'canShowCreateWorkflowButton'
  }
};

export const PERMISSION_GROUPS = {
  // ... 现有权限组
  
  'workflow_management': [
    'view_workflows',
    'create_workflow',
    'edit_workflow', 
    'delete_workflow',
    'show_create_workflow_button'
  ]
};

export const ROLE_PERMISSION_CONFIG = {
  'workspace_admin': {
    'inherit_from': 'annotator',
    'groups': [
      'project_management',
      'workspace_management',
      'project_advanced_settings', 
      'page_operations',
      'workflow_management'  // 新增
    ],
  }
};
```

### 2. 后端配置

```python
# label_studio/users/utils/permissions.py
PERMISSION_GROUPS = {
    # ... 现有权限组
    
    'workflow_management': [
        'view_workflows',
        'create_workflow',
        'edit_workflow',
        'delete_workflow', 
        'show_create_workflow_button',
    ],
}
```

### 3. 菜单集成

```jsx
// src/components/Menubar/Menubar.jsx
import { usePermissions } from '../../hooks/usePermissions';

const { menu } = usePermissions();

{menu.canViewWorkflows() && (
  <Menu.Item 
    label="工作流管理" 
    to="/workflows" 
    icon={<IconWorkflow />} 
    exact 
  />
)}
```

### 4. 页面实现

```jsx
// src/pages/Workflows/WorkflowsPage.jsx
import React from 'react';
import { SmartButton } from '../../components/SmartPermission/SmartButton';
import { useButtonPermissions } from '../../hooks/useButtonPermissions';

export const WorkflowsPage = () => {
  const buttonPermissions = useButtonPermissions();
  
  return (
    <div>
      <h1>工作流管理</h1>
      
      {/* 创建按钮 */}
      <SmartButton
        permission="show_create_workflow_button"
        onClick={handleCreateWorkflow}
        look="primary"
        fallback="hide"
      >
        创建工作流
      </SmartButton>
      
      {/* 工作流列表 */}
      {workflows.map(workflow => (
        <WorkflowCard 
          key={workflow.id}
          workflow={workflow}
          canEdit={buttonPermissions.canEditWorkflow}
          canDelete={buttonPermissions.canDeleteWorkflow}
        />
      ))}
    </div>
  );
};
```

### 5. 应用配置

```bash
# 应用新权限配置
cd label_studio
python manage.py init_role_permissions --reset
```

## ⚠️ 最佳实践

### 权限设计原则

1. **最小权限原则**: 角色只拥有必需的最小权限集合
2. **权限组织**: 使用权限组对相关权限进行批量管理
3. **继承优先**: 优先使用角色继承，减少重复配置
4. **命名规范**: 使用一致的权限命名规范

### 开发注意事项

1. **配置同步**: 前后端权限配置必须保持同步
2. **权限粒度**: 合理控制权限粒度，避免过细或过粗
3. **测试验证**: 每次权限变更都要充分测试各角色的访问效果
4. **文档更新**: 及时更新权限文档和注释

### 性能优化

1. **权限缓存**: 系统自动缓存用户权限，避免重复查询
2. **批量检查**: 使用 `hasAnyPermission` 进行批量权限检查
3. **组件优化**: SmartButton等组件已优化，避免不必要的重渲染

## 🔧 运维人员部署指引

### 新环境部署权限系统

#### 1. 环境要求
- Python 3.8+
- Django 3.2+
- PostgreSQL/MySQL数据库
- Redis（可选，用于缓存）

#### 2. 部署步骤

**步骤一：代码部署**
```bash
# 1. 部署代码到目标环境
git clone <repository-url>
cd label-studio

# 2. 安装依赖
pip install -r requirements.txt
# 或使用poetry
poetry install

# 3. 配置环境变量
cp .env.example .env
# 编辑.env文件，配置数据库连接等
```

**步骤二：数据库初始化**
```bash
# 1. 运行数据库迁移
python manage.py migrate

# 2. 初始化权限系统（重要！）
python manage.py init_role_permissions

# 3. 创建超级管理员账户
python manage.py createsuperuser
```

**步骤三：权限系统验证**
```bash
# 1. 启动服务
python manage.py runserver 0.0.0.0:8080

# 2. 访问管理界面验证
# 浏览器访问: http://your-domain:8080/admin/
# 确认能看到「🔐 权限管理中心」链接

# 3. 验证权限管理功能
# 访问: http://your-domain:8080/admin/permission-management/
# 确认页面正常加载，显示角色和权限信息
```

### 权限系统更新部署

#### 场景一：更新权限配置（无代码变更）

**通过权限管理中心更新**：
1. 访问 `http://your-domain/admin/permission-management/`
2. 使用权限开关和权限包功能进行调整
3. 变更即时生效，无需重启

**通过Django Admin更新**：
1. 访问 `http://your-domain/admin/users/role/`
2. 编辑角色权限配置
3. 访问 `http://your-domain/admin/users/permission/`
4. 管理权限定义

#### 场景二：代码更新后的权限同步

```bash
# 1. 更新代码
git pull origin main

# 2. 运行数据库迁移（如有新迁移）
python manage.py migrate

# 3. 同步权限配置（重要！）
python manage.py init_role_permissions

# 4. 重启服务
sudo systemctl restart label-studio
# 或使用其他进程管理工具
```

#### 场景三：权限系统故障恢复

```bash
# 1. 重置权限系统（谨慎使用）
python manage.py init_role_permissions --reset

# 2. 检查权限数据完整性
python manage.py shell
>>> from users.models import Role, Permission, RolePermission
>>> print(f"角色数: {Role.objects.count()}")
>>> print(f"权限数: {Permission.objects.count()}")
>>> print(f"角色权限关系数: {RolePermission.objects.count()}")

# 3. 验证特定角色权限
>>> role = Role.objects.get(name='workspace_admin')
>>> permissions = role.get_granted_permissions()
>>> print(f"workspace_admin 拥有 {len(permissions)} 个权限")
```

### 生产环境配置建议

#### 1. 安全配置
```python
# settings.py 或环境变量
SECRET_KEY = 'your-production-secret-key'
DEBUG = False
ALLOWED_HOSTS = ['your-domain.com']

# 数据库配置
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': 'labelstudio_prod',
        'USER': 'labelstudio',
        'PASSWORD': 'secure-password',
        'HOST': 'localhost',
        'PORT': '5432',
    }
}
```

#### 2. 权限系统监控
```bash
# 创建权限系统健康检查脚本
cat > check_permissions.py << 'EOF'
#!/usr/bin/env python
import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'label_studio.settings')
django.setup()

from users.models import Role, Permission, RolePermission

def check_permissions_health():
    """检查权限系统健康状态"""
    try:
        # 检查基础角色
        required_roles = ['superuser', 'annotator', 'workspace_admin']
        for role_name in required_roles:
            role = Role.objects.get(name=role_name)
            permission_count = role.get_granted_permissions().count()
            print(f"✓ 角色 {role_name}: {permission_count} 个权限")
        
        # 检查权限总数
        total_permissions = Permission.objects.filter(is_active=True).count()
        print(f"✓ 活跃权限总数: {total_permissions}")
        
        print("权限系统健康检查通过!")
        return True
    except Exception as e:
        print(f"❌ 权限系统检查失败: {e}")
        return False

if __name__ == '__main__':
    check_permissions_health()
EOF

python check_permissions.py
```

#### 3. 备份与恢复
```bash
# 备份权限配置
python manage.py dumpdata users.Role users.Permission users.RolePermission > permissions_backup.json

# 恢复权限配置
python manage.py loaddata permissions_backup.json
```

### 故障排除

#### 常见问题及解决方案

**问题1：权限管理中心无法访问**
```bash
# 检查URL配置
python manage.py shell
>>> from django.urls import reverse
>>> reverse('admin:index')  # 应该返回 '/admin/'

# 检查模板文件
ls label_studio/users/templates/admin/
# 应该存在 index.html 和 permission_management.html
```

**问题2：权限检查不生效**
```bash
# 清理权限缓存
python manage.py shell
>>> from django.core.cache import cache
>>> cache.clear()

# 重新初始化权限
python manage.py init_role_permissions
```

**问题3：角色权限丢失**
```bash
# 检查数据库连接
python manage.py dbshell

# 重新生成权限数据
python manage.py init_role_permissions --reset
```

## 🚀 系统优势总结

### 维护效率提升

- **添加权限**: 从原来的6个文件修改减少到2个配置文件
- **权限组织**: 通过权限组实现批量管理
- **自动生成**: Hook方法和常量完全自动生成
- **可视化管理**: 通过Web界面进行权限配置

### 开发体验改善

- **智能组件**: 提供开箱即用的权限控制组件
- **类型安全**: TypeScript支持，提供完整的类型检查  
- **便捷Hook**: 提供多种便捷的权限检查Hook
- **即时生效**: 权限变更无需重启即可生效

### 系统扩展性

- **配置驱动**: 通过配置而非代码管理权限
- **继承机制**: 支持角色权限继承，便于扩展
- **灵活组合**: 支持权限组、继承、自定义权限的灵活组合
- **多环境部署**: 支持开发、测试、生产环境的灵活部署

---

**文档版本**：v3.0  
**更新时间**：2025-08-03  
**适用系统**：Label Studio权限系统 v3.0（完整版）  
**维护者**：开发团队
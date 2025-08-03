# SmartPermission 组件库

权限控制组件库，提供从简单到复杂的多层级权限控制方案。

## 组件概览

| 组件 | 适用场景 | 配置复杂度 | 性能 |
|------|----------|------------|------|
| `Button` | 普通功能 | 无 | 最佳 |
| `SimpleButton` | 角色控制 | 低 | 良好 |
| `SmartButton` | 复杂权限 | 高 | 一般 |

## Button (推荐)

普通按钮，无权限控制，适用于大部分场景。

```jsx
import { Button } from '@humansignal/ui';

<Button onClick={handleAction}>
  查看数据
</Button>
```

**使用场景**：
- 查看功能
- 个人设置编辑
- 数据导出
- 非敏感操作

## SimpleButton

基于角色的简化权限控制按钮。

### Props

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `requireRole` | `'admin_ui' \| 'super_ui'` | - | 所需角色级别 |
| `dangerLevel` | `'high'` | - | 危险级别，high时需要超级管理员权限 |
| `fallback` | `'hide' \| 'disable' \| 'tooltip'` | `'hide'` | 无权限时的处理方式 |
| `tooltipText` | `string` | - | 无权限时的提示文本 |
| `...buttonProps` | `ButtonProps` | - | 所有Button组件的props |

### 使用示例

```jsx
import { SimpleButton } from '../components/SmartPermission/SimpleButton';

// 管理员功能
<SimpleButton
  requireRole="admin_ui"
  onClick={handleAdminAction}
  fallback="tooltip"
  tooltipText="需要管理员权限"
>
  用户管理
</SimpleButton>

// 超级管理员功能
<SimpleButton
  requireRole="super_ui"
  onClick={handleSuperAction}
>
  系统设置
</SimpleButton>

// 高危险操作
<SimpleButton
  dangerLevel="high"
  onClick={handleDangerousAction}
  fallback="tooltip"
  tooltipText="需要超级管理员权限"
>
  重置系统
</SimpleButton>
```

### 角色说明

- `admin_ui`: 需要管理员权限（workspace_admin 或 superuser）
- `super_ui`: 需要超级管理员权限（仅 superuser）

## SmartButton

完整的权限控制按钮，支持复杂权限逻辑。

### Props

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `permission` | `string` | - | 具体权限名称 |
| `permissions` | `string[]` | - | 权限列表（需要全部满足） |
| `condition` | `(permissions) => boolean` | - | 自定义权限检查函数 |
| `requireRole` | `'admin_ui' \| 'super_ui'` | - | 所需角色级别（宽松模式） |
| `dangerLevel` | `'high'` | - | 危险级别（宽松模式） |
| `fallback` | `'hide' \| 'disable' \| 'tooltip'` | `'hide'` | 无权限时的处理方式 |
| `tooltipText` | `string` | - | 无权限时的提示文本 |
| `...buttonProps` | `ButtonProps` | - | 所有Button组件的props |

### 使用示例

```jsx
import { SmartButton } from '../components/SmartPermission/SmartButton';

// 具体权限控制
<SmartButton
  permission="delete_project"
  onClick={handleDeleteProject}
  fallback="tooltip"
  tooltipText="您没有删除项目的权限"
>
  删除项目
</SmartButton>

// 多权限控制
<SmartButton
  permissions={['edit_project', 'manage_project_settings']}
  onClick={handleAdvancedEdit}
>
  高级编辑
</SmartButton>

// 自定义权限逻辑
<SmartButton
  condition={(perms) => perms.isAdmin() && perms.hasPermission('special_access')}
  onClick={handleSpecialAction}
>
  特殊操作
</SmartButton>
```

## PermissionGuard

权限保护组件，用于条件渲染。

### Props

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `permission` | `string` | - | 单个权限 |
| `permissions` | `string[]` | - | 权限列表 |
| `requireAll` | `boolean` | `true` | 是否需要所有权限（false为OR逻辑） |
| `fallback` | `ReactNode` | `null` | 无权限时的替代内容 |
| `children` | `ReactNode` | - | 有权限时显示的内容 |

### 使用示例

```jsx
import { PermissionGuard } from '../components/SmartPermission/PermissionGuard';

// 单权限保护
<PermissionGuard permission="view_organization">
  <OrganizationSettings />
</PermissionGuard>

// 多权限保护（AND逻辑）
<PermissionGuard permissions={['edit_project', 'manage_project_settings']}>
  <ProjectSettingsPanel />
</PermissionGuard>

// 多权限保护（OR逻辑）
<PermissionGuard 
  permissions={['manage_users', 'manage_roles']} 
  requireAll={false}
>
  <UserManagementPanel />
</PermissionGuard>

// 自定义fallback
<PermissionGuard 
  permission="view_advanced_settings"
  fallback={<div>您没有访问权限</div>}
>
  <AdvancedSettings />
</PermissionGuard>
```

## SmartField

智能表单字段，支持权限控制的表单元素。

### Props

| 属性 | 类型 | 默认值 | 描述 |
|------|------|--------|------|
| `fieldPermission` | `string` | - | 字段编辑权限 |
| `fallback` | `'readonly' \| 'hide'` | `'readonly'` | 无权限时的处理方式 |
| `children` | `ReactNode` | - | 表单字段内容 |

### 使用示例

```jsx
import { SmartField } from '../components/SmartPermission/SmartField';

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

## Hooks

### usePermissions

权限检查的主要Hook。

```jsx
import { usePermissions } from '../hooks/usePermissions';

const MyComponent = () => {
  const permissions = usePermissions();
  
  return (
    <div>
      {/* 基础权限检查 */}
      {permissions.hasPermission('create_project') && (
        <Button>创建项目</Button>
      )}
      
      {/* 角色检查 */}
      {permissions.isSuperuser() && (
        <Button>系统设置</Button>
      )}
      
      {/* 菜单权限 */}
      {permissions.menu.canViewOrganization() && (
        <Link to="/organization">组织管理</Link>
      )}
      
      {/* 操作权限 */}
      {permissions.action.canCreateProject() && (
        <Button>创建项目</Button>
      )}
    </div>
  );
};
```

### useRoleAccess

简化的角色访问控制Hook。

```jsx
import { useRoleAccess } from '../hooks/useRoleAccess';

const MyComponent = () => {
  const role = useRoleAccess();
  
  return (
    <div>
      {/* 角色检查 */}
      {role.isAdmin() && <Button>管理功能</Button>}
      {role.isSuperUser() && <Button>系统功能</Button>}
      
      {/* UI区域访问检查 */}
      {role.hasUIAccess('admin_ui') && (
        <AdminPanel />
      )}
    </div>
  );
};
```

### useButtonPermissions

便捷的按钮权限Hook。

```jsx
import { useButtonPermissions } from '../hooks/useButtonPermissions';

const MyComponent = () => {
  const buttonPerms = useButtonPermissions();
  
  return (
    <div>
      {buttonPerms.canCreateProject && (
        <Button>创建项目</Button>
      )}
      
      {buttonPerms.canDeleteProject && (
        <Button>删除项目</Button>
      )}
    </div>
  );
};
```

## 权限模式配置

系统支持两种模式：

### 严格模式 (strict)

```javascript
PERMISSION_SYSTEM_CONFIG.mode = 'strict';
```

- 所有UI元素都需要显式权限配置
- 未配置权限的元素不显示
- 适合高安全要求的场景

### 宽松模式 (loose) - 推荐

```javascript
PERMISSION_SYSTEM_CONFIG.mode = 'loose';
```

- 普通元素默认显示
- 只对危险操作进行权限控制
- 支持角色级别控制
- 提高开发效率

## 最佳实践

### 1. 选择合适的组件

```jsx
// ✅ 普通功能 - 使用 Button
<Button onClick={handleView}>查看</Button>

// ✅ 角色控制 - 使用 SimpleButton  
<SimpleButton requireRole="admin_ui">管理</SimpleButton>

// ✅ 严格权限 - 使用 SmartButton
<SmartButton permission="delete_project">删除</SmartButton>
```

### 2. 合理的fallback策略

```jsx
// ✅ 普通功能隐藏即可
<SimpleButton fallback="hide">

// ✅ 重要功能提供提示
<SimpleButton fallback="tooltip" tooltipText="需要管理员权限">

// ✅ 危险操作禁用并提示
<SmartButton fallback="tooltip" tooltipText="您没有此权限">
```

### 3. 性能优化

```jsx
// ✅ 避免不必要的权限检查
const MyComponent = React.memo(() => {
  // 只在需要时进行权限检查
});

// ✅ 使用角色检查替代复杂权限检查
const role = useRoleAccess();
return role.isAdmin() ? <AdminButton /> : null;
```

## 调试工具

开发环境下可以使用浏览器控制台工具：

```javascript
// 查看权限分析报告
PermissionDevTools.printAnalysisReport();

// 切换权限模式
PermissionDevTools.toggleMode();

// 查看当前用户权限
window.currentUserPermissions = usePermissions().debug;
```
# 简化权限管理系统 - 开发指引

## 📖 概述

新的权限管理系统提供三种使用方式，从简单到复杂，让开发者可以根据实际需求选择合适的权限控制级别。

## 🚀 快速开始

### 1. 最简单的方式 - 普通按钮（推荐）

对于大部分功能，直接使用普通按钮，无需任何权限配置：

```jsx
import { Button } from '@humansignal/ui';

// ✅ 推荐：普通功能直接使用普通按钮
<Button onClick={() => window.open('/admin/some-page', '_blank')}>
  管理设置
</Button>
```

**适用场景**：
- 查看类功能
- 编辑个人设置
- 导出数据
- 大部分管理功能

### 2. 角色控制方式 - SimpleButton

需要区分用户角色时，使用 SimpleButton：

```jsx
import { SimpleButton } from '../../../components/SmartPermission/SimpleButton';

// ✅ 管理员功能：只有管理员和超级管理员能看到
<SimpleButton
  requireRole="admin_ui"
  onClick={handleAdminAction}
>
  用户管理
</SimpleButton>

// ✅ 超级管理员功能：只有超级管理员能看到
<SimpleButton
  requireRole="super_ui"
  onClick={handleSuperAction}
>
  系统设置
</SimpleButton>
```

**可用角色**：
- `basic_ui` - 所有用户（annotator、workspace_admin、superuser）
- `admin_ui` - 管理员（workspace_admin、superuser）
- `super_ui` - 超级管理员（superuser）

### 3. 严格权限控制 - SmartButton

只对真正危险的操作使用严格权限控制：

```jsx
import { SmartButton } from '../../../components/SmartPermission/SmartButton';

// ⚠️ 危险操作：需要具体权限
<SmartButton
  permission="delete_project"
  dangerLevel="high"
  onClick={handleDeleteProject}
  fallback="tooltip"
  tooltipText="您没有删除项目的权限"
>
  删除项目
</SmartButton>
```

## 📋 决策流程图

```
需要添加一个按钮/菜单？
│
├── 是普通功能（查看、编辑、导出等）？
│   └── ✅ 使用普通 Button，无需权限配置
│
├── 需要区分用户角色？
│   ├── 只有管理员能用？
│   │   └── ✅ 使用 SimpleButton + requireRole="admin_ui"
│   └── 只有超级管理员能用？
│       └── ✅ 使用 SimpleButton + requireRole="super_ui"
│
└── 是危险操作（删除、系统配置等）？
    └── ⚠️ 使用 SmartButton + 具体权限
```

## 🛠️ 开发示例

### 示例1：项目管理页面

```jsx
// src/pages/Projects/ProjectsPage.jsx
import React from 'react';
import { Button } from '@humansignal/ui';
import { SimpleButton } from '../../components/SmartPermission/SimpleButton';
import { SmartButton } from '../../components/SmartPermission/SmartButton';

export const ProjectsPage = () => {
  return (
    <div>
      {/* 普通功能：所有用户都能使用 */}
      <Button onClick={handleViewProject}>
        查看项目
      </Button>
      
      <Button onClick={handleExportData}>
        导出数据
      </Button>
      
      {/* 管理功能：只有管理员能使用 */}
      <SimpleButton
        requireRole="admin_ui"
        onClick={handleCreateProject}
      >
        创建项目
      </SimpleButton>
      
      <SimpleButton
        requireRole="admin_ui" 
        onClick={handleManageMembers}
      >
        管理成员
      </SimpleButton>
      
      {/* 危险操作：需要具体权限 */}
      <SmartButton
        permission="delete_project"
        dangerLevel="high"
        onClick={handleDeleteProject}
        fallback="tooltip"
        tooltipText="您没有删除项目的权限"
      >
        删除项目
      </SmartButton>
    </div>
  );
};
```

### 示例2：用户管理页面

```jsx
// src/pages/Organization/UsersPage.jsx
import React from 'react';
import { SimpleButton } from '../../components/SmartPermission/SimpleButton';

export const UsersPage = () => {
  return (
    <div>
      {/* 基础管理功能 */}
      <SimpleButton
        requireRole="admin_ui"
        onClick={handleInviteUser}
      >
        邀请用户
      </SimpleButton>
      
      <SimpleButton
        requireRole="admin_ui"
        onClick={handleEditUser}
      >
        编辑用户
      </SimpleButton>
      
      {/* 系统级功能 */}
      <SimpleButton
        requireRole="super_ui"
        onClick={handleManageRoles}
      >
        角色管理
      </SimpleButton>
      
      <SimpleButton
        requireRole="super_ui"
        onClick={handleSystemSettings}
      >
        系统设置
      </SimpleButton>
    </div>
  );
};
```

## 🎯 最佳实践

### ✅ 推荐做法

1. **默认使用普通按钮**
   ```jsx
   // ✅ 大部分情况下，直接使用普通按钮
   <Button onClick={handleAction}>功能按钮</Button>
   ```

2. **按功能层级选择组件**
   ```jsx
   // ✅ 查看功能 - 普通按钮
   <Button onClick={handleView}>查看详情</Button>
   
   // ✅ 管理功能 - 角色控制
   <SimpleButton requireRole="admin_ui" onClick={handleManage}>
     管理设置
   </SimpleButton>
   
   // ✅ 危险操作 - 权限控制
   <SmartButton permission="delete_data" dangerLevel="high">
     删除数据
   </SmartButton>
   ```

3. **合理的fallback策略**
   ```jsx
   // ✅ 普通功能隐藏即可
   <SimpleButton requireRole="admin_ui" fallback="hide">
   
   // ✅ 重要功能提供提示
   <SimpleButton 
     requireRole="admin_ui" 
     fallback="tooltip"
     tooltipText="需要管理员权限"
   >
   ```

### ❌ 避免的做法

1. **不要过度使用权限控制**
   ```jsx
   // ❌ 查看功能不需要权限控制
   <SmartButton permission="view_data" onClick={handleView}>
     查看数据
   </SmartButton>
   
   // ✅ 直接使用普通按钮
   <Button onClick={handleView}>查看数据</Button>
   ```

2. **不要为简单功能配置复杂权限**
   ```jsx
   // ❌ 简单的编辑功能不需要复杂配置
   <SmartButton 
     permission="edit_profile_settings_basic_info"
     onClick={handleEditProfile}
   >
   
   // ✅ 个人设置直接允许
   <Button onClick={handleEditProfile}>编辑个人信息</Button>
   ```

## 🔧 开发者工具

### 浏览器控制台工具

在开发环境下，打开浏览器控制台，可以使用以下工具：

```javascript
// 查看权限分析报告
PermissionDevTools.printAnalysisReport();

// 查看当前权限模式
PermissionDevTools.getCurrentMode(); // 返回 'loose' 或 'strict'

// 切换权限模式（开发环境）
PermissionDevTools.toggleMode();
```

### 权限配置检查

```javascript
// 检查组件权限配置是否合理
import { PermissionGenerator } from '../utils/permissionTools';

// 为现有权限生成简化建议
const suggestions = PermissionGenerator.generateSimplificationSuggestions([
  'show_create_project_button',
  'show_delete_project_button'
]);

console.log('简化建议:', suggestions);
```

## 📝 迁移指南

### 从旧权限系统迁移

1. **识别功能类型**
   ```jsx
   // 原来的配置
   <SmartButton permission="show_export_button">
     导出数据
   </SmartButton>
   
   // 评估：这是普通功能，可以简化
   <Button onClick={handleExport}>
     导出数据
   </Button>
   ```

2. **批量迁移策略**
   - 保留危险操作的严格权限控制
   - 将管理功能改为角色控制
   - 将普通功能改为无权限控制

3. **渐进式迁移**
   - 新功能使用简化方式
   - 现有功能逐步迁移
   - 保持系统稳定性

## 🚨 注意事项

### 安全注意事项

1. **危险操作必须权限控制**
   - 删除操作
   - 系统配置
   - 用户权限管理
   - 敏感数据访问

2. **合理设置角色要求**
   - 不要让普通用户执行管理操作
   - 系统级功能限制为超级管理员

### 性能注意事项

1. **避免过度的权限检查**
   - 简单查看功能不需要权限检查
   - 使用角色控制而非细粒度权限检查

2. **合理使用组件类型**
   - 普通Button性能最好
   - SimpleButton次之
   - SmartButton开销最大

## 🆘 常见问题

### Q1: 什么时候使用普通Button vs SimpleButton？

**A**: 
- 普通功能（查看、编辑个人数据、导出等）→ 普通Button
- 需要区分角色的功能（用户管理、系统设置等）→ SimpleButton

### Q2: 如何判断是否需要严格权限控制？

**A**: 只有真正危险的操作才需要：
- ✅ 删除项目、删除用户 → 需要
- ✅ 系统配置、权限管理 → 需要  
- ❌ 查看数据、编辑设置 → 不需要
- ❌ 导出数据、创建项目 → 不需要

### Q3: 如何处理复杂的权限逻辑？

**A**: 使用条件渲染：
```jsx
import { useRoleAccess } from '../hooks/useRoleAccess';

const role = useRoleAccess();

return (
  <div>
    {role.isAdmin() && someCondition && (
      <Button onClick={handleComplexAction}>
        复杂操作
      </Button>
    )}
  </div>
);
```

### Q4: 现有项目如何迁移？

**A**: 分阶段迁移：
1. 新功能使用简化方式
2. 非关键功能逐步简化
3. 保留核心安全功能的严格控制

## 📚 更多资源

- [完整改进方案](./PERMISSION_SYSTEM_IMPROVEMENT.md)
- [原有权限系统文档](./PERMISSIONS_GUIDE.md)
- [组件API文档](../web/apps/labelstudio/src/components/SmartPermission/README.md)

---

**记住**：简单优于复杂，安全第一，开发效率第二！
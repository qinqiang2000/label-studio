# 权限管理快速参考

## 🎯 30秒决策指南

### 我要添加一个按钮，用哪种方式？

```
普通功能（查看、编辑、导出） → Button
     ↓
管理功能（需要区分角色） → SimpleButton + requireRole
     ↓  
危险操作（删除、系统设置） → SmartButton + permission
```

## 📋 组件选择速查表

| 功能类型 | 推荐组件 | 示例代码 |
|----------|----------|----------|
| **查看数据** | `Button` | `<Button onClick={view}>查看</Button>` |
| **编辑设置** | `Button` | `<Button onClick={edit}>编辑</Button>` |
| **导出数据** | `Button` | `<Button onClick={export}>导出</Button>` |
| **用户管理** | `SimpleButton` | `<SimpleButton requireRole="admin_ui">用户管理</SimpleButton>` |
| **系统设置** | `SimpleButton` | `<SimpleButton requireRole="super_ui">系统设置</SimpleButton>` |
| **删除项目** | `SmartButton` | `<SmartButton permission="delete_project">删除</SmartButton>` |
| **权限管理** | `SmartButton` | `<SmartButton permission="manage_permissions">权限管理</SmartButton>` |

## 🔧 常用代码片段

### 1. 普通按钮（90%的情况）
```jsx
<Button onClick={() => handleAction()}>
  功能名称
</Button>
```

### 2. 管理员按钮
```jsx
<SimpleButton
  requireRole="admin_ui"
  onClick={() => handleAdminAction()}
>
  管理功能
</SimpleButton>
```

### 3. 超级管理员按钮
```jsx
<SimpleButton
  requireRole="super_ui"
  onClick={() => handleSuperAction()}
>
  系统功能
</SimpleButton>
```

### 4. 危险操作按钮
```jsx
<SmartButton
  permission="delete_something"
  onClick={() => handleDelete()}
  fallback="tooltip"
  tooltipText="您没有删除权限"
>
  删除
</SmartButton>
```

## 🚨 常见错误

### ❌ 过度使用权限控制
```jsx
// 错误：查看功能不需要权限控制
<SmartButton permission="view_data">查看数据</SmartButton>

// 正确：直接使用普通按钮
<Button>查看数据</Button>
```

### ❌ 为简单功能配置复杂权限
```jsx
// 错误：个人设置不需要权限
<SmartButton permission="edit_own_profile">编辑个人信息</SmartButton>

// 正确：个人功能直接允许
<Button>编辑个人信息</Button>
```

### ❌ 混淆角色和权限
```jsx
// 错误：用权限控制角色功能
<SmartButton permission="admin_user_management">用户管理</SmartButton>

// 正确：用角色控制
<SimpleButton requireRole="admin_ui">用户管理</SimpleButton>
```

## 📱 移动端/响应式

所有组件都支持响应式设计：

```jsx
<SimpleButton
  requireRole="admin_ui"
  size="small"  // mobile
  size="medium" // desktop
>
  管理功能
</SimpleButton>
```

## 🎨 样式定制

```jsx
<SimpleButton
  requireRole="admin_ui"
  variant="primary"    // 主要按钮
  variant="secondary"  // 次要按钮
  variant="danger"     // 危险按钮
  look="outline"       // 边框样式
>
  功能按钮
</SimpleButton>
```

## 🔍 调试技巧

### 检查用户权限
```javascript
// 在浏览器控制台中
PermissionDevTools.printAnalysisReport();
```

### 查看当前用户角色
```javascript
// 在浏览器控制台中  
const role = useRoleAccess();
console.log('当前用户角色:', role.getCurrentRole());
console.log('是否管理员:', role.isAdmin());
```

### 切换权限模式（开发环境）
```javascript
// 在浏览器控制台中
PermissionDevTools.toggleMode(); // 切换 strict/loose 模式
```

## 📚 更多资源

- [完整开发指引](./SIMPLIFIED_PERMISSION_GUIDE.md)
- [组件API文档](../web/apps/labelstudio/src/components/SmartPermission/README.md)
- [系统改进方案](./PERMISSION_SYSTEM_IMPROVEMENT.md)

---

**记住**：简单优于复杂！大部分功能都可以使用普通Button。
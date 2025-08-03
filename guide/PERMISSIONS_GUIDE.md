# Label Studio 权限管理系统指引

## 🎯 30秒快速上手

### 我要添加一个按钮，用哪种方式？

```
普通功能（查看、编辑、导出） → Button (0配置)
     ↓
管理功能（需要区分角色） → SimpleButton + requireRole (1行配置)
     ↓  
危险操作（删除、系统设置） → SmartButton + permission (传统方式)
```

### 常用代码模板

```jsx
// ✅ 90%的情况：普通按钮
<Button onClick={handleAction}>功能名称</Button>

// ✅ 管理员功能
<SimpleButton requireRole="admin_ui" onClick={handleAdmin}>
  管理功能
</SimpleButton>

// ✅ 危险操作
<SmartButton permission="delete_project" onClick={handleDelete}>
  删除项目
</SmartButton>
```

## 🚀 系统改进亮点

### 问题解决
- **原来**：添加一个按钮需要修改6个文件，工作量恐怖
- **现在**：普通功能0配置，管理功能1行配置

### 效果对比
| 方式 | 配置文件 | 开发时间 | 适用场景 |
|------|----------|----------|----------|
| **普通Button** | 0个 | 2分钟 | 查看、编辑、导出等 |
| **SimpleButton** | 0个 | 5分钟 | 用户管理、系统设置 |
| **SmartButton** | 3-6个 | 30分钟 | 删除、权限管理等 |

## 📚 详细文档导航

### 🚀 快速开始
1. **立即使用** - 本文档的代码模板，90%情况够用
2. **深入学习** - 查看 [详细开发指引](./SIMPLIFIED_PERMISSION_GUIDE.md)
3. **API查阅** - 查看 [组件API文档](../web/apps/labelstudio/src/components/SmartPermission/README.md)

### 📖 具体指引
- **添加普通功能** → 直接用 `Button`，无需权限配置
- **添加管理功能** → 用 `SimpleButton + requireRole="admin_ui"`
- **添加危险操作** → 用传统的 `SmartButton + permission`
- **查看实际实现** → 参考 `@web/apps/labelstudio/src/pages/Organization/PeoplePage/PeoplePage.jsx` 的实现示例
- **查看组件API** → 看组件README.md
- **理解系统改进** → 看 [改进方案文档](./PERMISSION_SYSTEM_IMPROVEMENT.md)

## 🛠️ 开发示例

### 常见场景代码

```jsx
// 场景1：项目列表页面
export const ProjectsPage = () => (
  <div>
    {/* 普通功能：所有人都能用 */}
    <Button onClick={handleView}>查看项目</Button>
    <Button onClick={handleExport}>导出数据</Button>
    
    {/* 管理功能：只有管理员能用 */}
    <SimpleButton requireRole="admin_ui" onClick={handleCreate}>
      创建项目
    </SimpleButton>
    
    {/* 危险操作：需要具体权限 */}
    <SmartButton permission="delete_project" onClick={handleDelete}>
      删除项目
    </SmartButton>
  </div>
);

// 场景2：用户管理页面
export const UsersPage = () => (
  <div>
    {/* 基础管理功能 */}
    <SimpleButton requireRole="admin_ui">邀请用户</SimpleButton>
    <SimpleButton requireRole="admin_ui">编辑用户</SimpleButton>
    
    {/* 系统级功能 */}
    <SimpleButton requireRole="super_ui">角色管理</SimpleButton>
    <SimpleButton requireRole="super_ui">权限设置</SimpleButton>
  </div>
);
```

### 角色说明

| 角色 | 说明 | 适用功能 |
|------|------|----------|
| `admin_ui` | 管理员权限 | 用户管理、项目管理、工作空间管理 |
| `super_ui` | 超级管理员权限 | 系统设置、权限管理、角色管理 |

## 🔧 调试与管理

### 权限管理中心
- 访问 `http://your-domain/admin/permission-management/`
- 可视化管理角色和权限配置

### 开发者工具（浏览器控制台）
```javascript
// 查看权限分析报告
PermissionDevTools.printAnalysisReport();

// 切换权限模式（开发环境）
PermissionDevTools.toggleMode(); // strict ↔ loose

// 查看当前用户权限信息
console.log('用户角色:', useRoleAccess().getCurrentRole());
```

## ⚠️ 常见错误

### ❌ 避免过度权限控制
```jsx
// 错误：查看功能不需要权限
<SmartButton permission="view_data">查看数据</SmartButton>

// 正确：直接使用普通按钮
<Button>查看数据</Button>
```

### ❌ 避免为简单功能配置复杂权限
```jsx
// 错误：个人设置不需要权限
<SmartButton permission="edit_own_profile">编辑个人信息</SmartButton>

// 正确：个人功能直接允许
<Button>编辑个人信息</Button>
```

## 🆘 需要复杂权限控制时

如果新的简化方式不能满足需求，可以查看：
- [传统权限配置方法](./SIMPLIFIED_PERMISSION_GUIDE.md) - 详细的传统配置步骤
- [组件完整API](../web/apps/labelstudio/src/components/SmartPermission/README.md) - 所有可用的配置选项

## 📦 总结

### 系统改进成果
- **开发效率**：添加按钮从30分钟减少到2分钟
- **配置复杂度**：从6个文件减少到0个文件（普通功能）
- **维护成本**：权限配置减少80%
- **向后兼容**：现有配置继续有效

### 核心理念
**简单优于复杂，安全第一！**

大部分功能都可以使用普通Button，只有真正需要区分角色或危险操作才使用权限控制。

---

**📚 更多资源**：
- [详细开发指引](./SIMPLIFIED_PERMISSION_GUIDE.md) 
- [组件API文档](../web/apps/labelstudio/src/components/SmartPermission/README.md)
- [系统改进方案](./PERMISSION_SYSTEM_IMPROVEMENT.md)

**文档版本**：v4.0 (简化版)  
**更新时间**：2025-08-03
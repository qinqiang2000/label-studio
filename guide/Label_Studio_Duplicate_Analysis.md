# Label Studio Duplicate功能分析

## 概述

Label Studio中的"Duplicate"功能允许用户复制当前tab页面的视图配置，创建一个具有相同过滤器、排序规则和列设置的新tab页面。

## 功能实现机制

### 1. 前端实现

#### Tab菜单配置
**文件：** `web/libs/datamanager/src/components/Common/Tabs/TabsMenu.jsx`

```javascript
{
  key: "duplicate",
  title: "Duplicate", 
  enabled: !virtual && clonable,
  action: () => onClick("duplicate"),
  willLeave: true,
}
```

#### 事件处理
**文件：** `web/libs/datamanager/src/components/Common/Tabs/Tabs.jsx`

```javascript
case "duplicate":
  return onDuplicate?.();
```

#### 调用逻辑
**文件：** `web/libs/datamanager/src/components/DataManager/DataManager.jsx`

```javascript
<TabsItem
  onDuplicate={() => views.duplicateView(tab)}
  // ... 其他props
/>
```

### 2. 状态管理

#### 核心复制逻辑
**文件：** `web/libs/datamanager/src/stores/Tabs/store.js`

```javascript
duplicateView: flow(function* (view) {
  const sn = getSnapshot(view);

  self.views.push({
    ...sn,
    id: Number.MAX_SAFE_INTEGER,
    saved: false,
    key: guidGenerator(),
    title: createNameCopy(sn.title),
  });

  const newView = self.views[self.views.length - 1];

  yield newView.save();
  self.selected = self.views[self.views.length - 1];
  self.selected.reload();
}),
```

#### 名称生成规则
```javascript
const createNameCopy = (name) => {
  let newName = name;
  const matcher = /Copy(\s\(([\d]+)\))?/;
  const copyNum = newName.match(matcher);

  if (copyNum) {
    newName = newName.replace(matcher, (...match) => {
      const num = match[2];
      if (num) return `Copy (${Number(num) + 1})`;
      return "Copy (2)";
    });
  } else {
    newName += " Copy";
  }

  return newName;
};
```

### 3. 后端API

#### API端点
**文件：** `web/libs/datamanager/src/sdk/api-config.js`

```javascript
/** Creates a new tab */
createTab: {
  path: "/views",
  method: "post",
},

/** Update particular tab (PATCH) */
updateTab: {
  path: "/views/:tabID", 
  method: "patch",
},
```

#### 后端处理
**文件：** `label_studio/data_manager/api.py`

```python
class ViewAPI(viewsets.ModelViewSet):
    serializer_class = ViewSerializer
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)
```

## Duplicate功能执行流程

1. **用户操作**：右键点击tab页面，选择"Duplicate"选项
2. **获取快照**：使用`getSnapshot(view)`获取当前视图的完整配置
3. **创建副本**：
   - 分配新的临时ID (`Number.MAX_SAFE_INTEGER`)
   - 生成新的唯一key (`guidGenerator()`)
   - 创建新的标题（添加"Copy"后缀）
   - 标记为未保存状态
4. **保存到后端**：调用`newView.save()`将新视图保存到数据库
5. **切换视图**：自动切换到新创建的tab页面并重新加载数据

## 数据共享问题分析

### 问题现象
当用户复制tab页面后，在新tab页面中删除prediction等操作会影响到原始tab页面，显示数据不独立。

### 根本原因

#### 1. 视图配置 vs 数据源
- **复制的内容**：视图配置（过滤器、排序、列设置）
- **未复制的内容**：底层数据源（tasks、annotations、predictions）

#### 2. 共享数据结构
两个tab页面实际上访问的是同一个项目数据：
- 相同的tasks数据集
- 相同的annotations
- 相同的predictions
- 相同的数据库记录

#### 3. 视图本质
Tab页面本质上是对同一数据集的不同"视图"（View），而不是数据的副本：
- 每个tab定义了如何显示数据（过滤、排序、分页）
- 但所有tab操作的都是同一个底层数据源
- 数据的增删改操作会立即反映到所有视图中

### 设计意图
这种设计是有意的，因为：
1. **内存效率**：避免复制大量数据
2. **数据一致性**：确保所有视图看到的是最新数据
3. **协作友好**：多个用户的不同视图能看到实时更新

## 解决方案建议

如果需要真正的数据隔离，可以考虑：

1. **项目级别的复制**：创建新项目并导入数据副本
2. **快照功能**：在特定时间点创建数据快照
3. **分支功能**：类似Git的分支概念，允许并行的数据修改

## 相关文件位置

- 前端Tab组件：`web/libs/datamanager/src/components/Common/Tabs/`
- 状态管理：`web/libs/datamanager/src/stores/Tabs/store.js`
- API配置：`web/libs/datamanager/src/sdk/api-config.js`
- 后端API：`label_studio/data_manager/api.py`
- 数据模型：`label_studio/data_manager/models.py`

## 总结

Label Studio的Duplicate功能是一个**视图复制**功能，而不是**数据复制**功能。它允许用户快速创建具有不同配置的新视图来查看同一数据集，这是一个合理且高效的设计选择。数据的"共享"行为是预期的功能特性，而不是bug。
# Prompts模块部署指南

## 概述
Prompts模块是一个为Label Studio添加的自定义功能，允许用户创建、编辑、删除和管理提示词(prompts)。

## 新环境部署步骤

### 1. 后端部署

#### 1.1 复制文件
将以下文件复制到新的Label Studio环境：

```bash
# 复制prompts应用目录
cp -r label_studio/prompts/ <new_env>/label_studio/

# 包含的文件：
# - label_studio/prompts/models.py         # 数据模型
# - label_studio/prompts/serializers.py   # API序列化器
# - label_studio/prompts/api.py           # API视图
# - label_studio/prompts/views.py         # 页面视图
# - label_studio/prompts/urls.py          # URL配置
# - label_studio/prompts/migrations/      # 数据库迁移文件
# - label_studio/prompts/management/      # 管理命令
```

#### 1.2 修改Django设置
在 `label_studio/core/settings/base.py` 中添加应用：

```python
INSTALLED_APPS = [
    # ... 现有应用 ...
    'prompts',  # 添加这一行
]
```

#### 1.3 添加URL路由
在 `label_studio/core/urls.py` 中添加prompts的URL配置：

```python
urlpatterns = [
    # ... 现有URL配置 ...
    re_path(r'^', include('prompts.urls')),  # 添加这一行
]
```

#### 1.4 运行数据库迁移
```bash
cd <new_env>/label_studio
python manage.py makemigrations prompts
python manage.py migrate
```

### 2. 前端部署

#### 2.1 复制前端文件
```bash
# 复制页面组件
cp -r web/apps/labelstudio/src/pages/Prompts/ <new_env>/web/apps/labelstudio/src/pages/

# 包含的文件：
# - Prompts.jsx    # 主页面组件
# - Prompts.scss   # 样式文件
# - index.js       # 导出文件
```

#### 2.2 更新页面注册
在 `web/apps/labelstudio/src/pages/index.js` 中添加：

```javascript
import { PromptsPage } from "./Prompts";

export const Pages = [
  // ... 现有页面 ...
  PromptsPage,  // 添加这一行
].filter(Boolean);
```

#### 2.3 添加菜单项
在 `web/apps/labelstudio/src/components/Menubar/Menubar.jsx` 中：

1. 添加图标导入：
```javascript
import {
  // ... 现有图标 ...
  IconSparks,  // 添加这一行
} from "@humansignal/icons";
```

2. 添加菜单项：
```javascript
<Menu>
  {/* ... 现有菜单项 ... */}
  <Menu.Item label="Prompts" to="/prompts" icon={<IconSparks />} data-external exact />
  {/* ... 其他菜单项 ... */}
</Menu>
```

#### 2.4 添加API配置
在 `web/apps/labelstudio/src/config/ApiConfig.js` 中添加：

```javascript
export const API_CONFIG = {
  gateway: "/api/",
  endpoints: {
    // ... 现有端点 ...
    
    // Prompts
    getPrompts: "GET:/prompts",
    createPrompt: "POST:/prompts",
    updatePrompt: "PATCH:/prompts/:id",
    deletePrompt: "DELETE:/prompts/:id",
  },
};
```

### 3. 验证部署

#### 3.1 后端验证
```bash
# 启动开发服务器
python manage.py runserver

# 测试API端点
curl http://localhost:8000/api/prompts/
```

#### 3.2 前端验证
1. 访问 `http://localhost:8000/prompts`
2. 检查左侧菜单是否显示"Prompts"项
3. 测试创建、编辑、删除功能

### 4. 生产环境注意事项

#### 4.1 静态文件
确保运行静态文件收集：
```bash
python manage.py collectstatic
```

#### 4.2 前端构建
如果使用生产构建：
```bash
cd web/
npm run build
# 或
yarn build
```

#### 4.3 数据库备份
在运行迁移前备份数据库：
```bash
python manage.py dumpdata > backup_before_prompts.json
```

## 功能特性

### 数据模型
- `name`: 提示词名称（唯一）
- `content`: 提示词内容
- `created_at`: 创建时间
- `updated_at`: 更新时间
- `created_by`: 创建用户

### API端点
- `GET /api/prompts/` - 获取提示词列表
- `POST /api/prompts/` - 创建新提示词
- `PATCH /api/prompts/{id}/` - 更新提示词
- `DELETE /api/prompts/{id}/` - 删除提示词

### 前端功能
- 网格布局显示提示词卡片
- 点击卡片或Edit按钮编辑
- 大尺寸模态框编辑器
- Name字段唯一性验证
- 创建、编辑、删除功能

## 故障排除

### 常见问题

1. **模块导入错误**
   - 确保 `prompts` 已添加到 `INSTALLED_APPS`
   - 检查文件路径是否正确

2. **迁移失败**
   - 检查数据库连接
   - 确保有正确的数据库权限

3. **前端菜单不显示**
   - 确保图标正确导入
   - 检查菜单项语法

4. **API调用失败**
   - 检查URL配置
   - 验证用户认证状态

### 日志检查
```bash
# Django日志
tail -f <log_path>/django.log

# 浏览器控制台
# F12 -> Console 检查前端错误
```

## 版本兼容性

- **Label Studio版本**: 1.x.x及以上
- **Django版本**: 3.x及以上
- **React版本**: 16.x及以上
- **Python版本**: 3.8及以上

## 支持

如有问题，请检查：
1. 文件是否完整复制
2. 配置是否正确添加
3. 迁移是否成功运行
4. 前端构建是否无错误 
# Claude 工作环境配置

## 虚拟环境
```bash
source /Users/qinqiang02/Library/Caches/pypoetry/virtualenvs/label-studio-ofHy_tK8-py3.12/bin/activate
```

## 常用命令
```bash
# 运行开发服务器
python label_studio/manage.py runserver

# 数据库迁移
python label_studio/manage.py makemigrations
python label_studio/manage.py migrate

# 创建超级用户
python label_studio/manage.py createsuperuser

# Django shell
python label_studio/manage.py shell

# 初始化权限数据
python label_studio/manage.py init_permissions
```

## 项目结构
- `label_studio/` - Django 后端代码
- `web/` - 前端代码
- `guide/` - 项目文档

## 测试用户
- 标注员: qinqiang2000@qq.com / 11111111
- 管理员: qinqiang2000@foxmail.com / 11111111

## 权限管理系统
已实现基于角色的动态权限管理系统，支持：
- 通过Django Admin界面管理权限，无需修改代码
- 实时权限刷新API
- 权限管理中心页面: `/admin/permission-management/`
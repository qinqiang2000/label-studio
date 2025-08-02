# 评估配置系统部署指南

## 概述

新的评估配置系统使用JSON配置文件和自动加载机制，替代了原来的硬编码管理命令。

## 部署步骤

### 1. 代码部署
```bash
# 拉取最新代码
git pull origin company-custom

# 确认配置文件存在
ls -la label_studio/evaluation_configs/config/
# 应该看到: bank_receipt.json, invoice.json, receipt.json, custom.json
```

### 2. 数据库迁移
```bash
# 运行迁移（如果有新的）
python manage.py migrate evaluation_configs

# 迁移完成后会自动触发配置加载
```

### 3. 手动加载配置（如果需要）
```bash
# 如果自动加载失败，可以手动加载
python manage.py reload_configs

# 或者清除并重新加载
python manage.py reload_configs --clear
```

### 4. 验证配置
```bash
# 检查数据库中的配置
python manage.py shell -c "
from evaluation_configs.models import EvaluationFieldConfig
configs = EvaluationFieldConfig.objects.all()
print(f'配置数量: {configs.count()}')
for config in configs:
    print(f'- {config.key}: {len(config.required_fields)} 个必需字段')
    if config.key == 'bank_receipt':
        print(f'  银行回单: {config.required_fields}')
"
```

### 5. 测试API
```bash
# 测试配置API
curl http://your-server/api/frontend/evaluation-configs/presets/
```

### 6. 重启服务器
```bash
# 重启Django服务器
systemctl restart your-django-service
# 或根据你的部署方式重启
```

## 新的配置字段

银行回单现在包含完整的12个字段：
- tradeId ✨ 新增
- recieptNum
- logNum ✨ 新增
- tradeDate
- amount
- paymentName
- paymentBank
- paymentAccount
- payeeName
- payeeBank
- payeeAccount
- currency

## 故障排除

### 问题1: API返回空配置
**原因**: 数据库中没有配置数据
**解决**: 运行 `python manage.py reload_configs --clear`

### 问题2: 前端显示旧字段
**原因**: 前端缓存或代码未更新
**解决**: 
1. 重新构建前端代码
2. 清除浏览器缓存
3. 重启服务器

### 问题3: Django启动警告
**原因**: 在应用初始化时访问数据库
**解决**: 已通过信号处理器解决，配置在迁移后自动加载

## 维护

### 添加新的文档类型
1. 在 `evaluation_configs/config/` 目录下创建新的JSON文件
2. 运行 `python manage.py reload_configs` 加载新配置

### 修改现有配置
1. 编辑对应的JSON文件
2. 运行 `python manage.py reload_configs` 重新加载

### 备份配置
配置数据存储在数据库中，随数据库备份一起备份。
JSON文件作为配置源，应当纳入版本控制。
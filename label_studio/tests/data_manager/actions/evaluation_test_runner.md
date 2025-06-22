# 评估功能测试执行指南

## 概述
本文档提供了如何执行 `document_evaluation_test_cases.md` 中定义的测试用例的具体指导。

## 前置条件

### 环境准备
1. 确保Label Studio服务运行在 http://127.0.0.1:8080
2. 确保有管理员权限的用户账号
3. 准备测试项目和数据

### 测试数据准备脚本
```bash
# 在label_studio目录下执行
python manage.py shell -c "
from projects.models import Project
from evaluation_configs.models import EvaluationFieldConfig, ProjectEvaluationConfig

# 确保项目1使用Invoice配置
project1 = Project.objects.get(id=1)
invoice_config = EvaluationFieldConfig.objects.get(key='invoice')
project_config, created = ProjectEvaluationConfig.objects.get_or_create(
    project=project1,
    defaults={'evaluation_config': invoice_config}
)
if not created:
    project_config.evaluation_config = invoice_config
    project_config.save()
print('项目1配置为Invoice配置')

# 检查项目27是否使用Custom配置
try:
    project27 = Project.objects.get(id=27)
    custom_config = EvaluationFieldConfig.objects.get(key='custom')
    project27_config, created = ProjectEvaluationConfig.objects.get_or_create(
        project=project27,
        defaults={'evaluation_config': custom_config}
    )
    if not created:
        project27_config.evaluation_config = custom_config
        project27_config.save()
    print('项目27配置为Custom配置')
except Project.DoesNotExist:
    print('项目27不存在')
"
```

## 核心测试用例执行

### 1. 基础功能测试 (1.1, 1.2)

**使用Playwright执行**:
```markdown
测试步骤:
1. 打开浏览器并导航到项目1数据页面
2. 选择任务11
3. 点击"1 Task"按钮
4. 点击"Evaluate Document Extraction"
5. 验证对话框内容
6. 点击OK执行评估
7. 验证结果页面

预期验证点:
- 对话框显示简化文本
- 没有配置选择下拉框
- 总字段数 > 0
- 显示准确率数据
```

**执行命令示例**:
```bash
# 使用Playwright MCP工具
# 1. 导航到页面
mcp_playwright_browser_navigate("http://127.0.0.1:8080/projects/1/data?tab=9")

# 2. 等待页面加载
mcp_playwright_browser_wait_for(time=5)

# 3. 选择任务
mcp_playwright_browser_click(element="Task 11 checkbox", ref="...")

# 4. 点击任务按钮
mcp_playwright_browser_click(element="1 Task button", ref="...")

# 5. 点击评估选项
mcp_playwright_browser_click(element="Evaluate Document Extraction", ref="...")

# 6. 验证对话框并点击OK
mcp_playwright_browser_click(element="OK button", ref="...")
```

### 2. 配置匹配测试 (2.1, 2.2)

**项目1 Invoice配置测试**:
```bash
# 验证项目1配置
python manage.py shell -c "
from projects.models import Project
from data_manager.actions.document_evaluation import get_project_evaluation_config

project = Project.objects.get(id=1)
config = get_project_evaluation_config(project)
print('项目1配置:', config.evaluation_config.name)
print('允许的文档类型:', config.effective_validation_rules['docType']['allowed_values'])
print('预期字段数:', len(config.effective_required_fields))
"

# 然后通过Playwright执行评估测试
```

**项目27 Custom配置测试**:
```bash
# 验证项目27配置
python manage.py shell -c "
from projects.models import Project
from data_manager.actions.document_evaluation import get_project_evaluation_config

try:
    project = Project.objects.get(id=27)
    config = get_project_evaluation_config(project)
    print('项目27配置:', config.evaluation_config.name)
    print('允许的文档类型:', config.effective_validation_rules['docType']['allowed_values'])
    print('预期字段数:', len(config.effective_required_fields))
except Project.DoesNotExist:
    print('项目27不存在')
"
```

### 3. 异常情况测试 (3.1)

**文档类型不匹配测试**:
```bash
# 创建测试场景：Bank Receipt配置 + Invoice数据
python manage.py shell -c "
from projects.models import Project
from evaluation_configs.models import EvaluationFieldConfig, ProjectEvaluationConfig

# 临时将项目1设置为Bank Receipt配置
project1 = Project.objects.get(id=1)
bank_receipt_config = EvaluationFieldConfig.objects.get(key='bank_receipt')
project_config = ProjectEvaluationConfig.objects.get(project=project1)
project_config.evaluation_config = bank_receipt_config
project_config.save()
print('项目1临时设置为Bank Receipt配置')
"

# 执行评估测试，预期总字段数为0
# 然后恢复配置
python manage.py shell -c "
from projects.models import Project
from evaluation_configs.models import EvaluationFieldConfig, ProjectEvaluationConfig

project1 = Project.objects.get(id=1)
invoice_config = EvaluationFieldConfig.objects.get(key='invoice')
project_config = ProjectEvaluationConfig.objects.get(project=project1)
project_config.evaluation_config = invoice_config
project_config.save()
print('项目1恢复为Invoice配置')
"
```

### 4. 边界条件测试 (4.1, 4.2)

**单任务测试**:
```markdown
1. 选择项目1的单个任务
2. 执行评估
3. 验证总文档数=1，总字段数>0
```

**大数据量测试**:
```markdown
1. 选择项目1的所有11个任务
2. 执行评估
3. 监控响应时间
4. 验证总文档数=11，总字段数>0
```

### 5. 用户界面测试 (5.1)

**对话框交互测试**:
```markdown
测试序列:
1. 打开评估对话框
2. 点击Cancel，验证操作取消
3. 重新打开对话框
4. 按ESC键，验证对话框关闭
5. 重新打开并点击OK，验证评估执行
```

## 回归测试执行

### 历史问题验证

**1. 界面卡死问题**:
```markdown
验证步骤:
1. 打开评估对话框
2. 等待5秒，验证界面响应正常
3. 点击OK后，验证页面不卡死
4. 评估完成后，验证界面可正常操作
```

**2. project参数None错误**:
```markdown
验证方法:
1. 打开浏览器开发者工具
2. 监控网络请求
3. 执行评估操作
4. 检查API请求中project参数不为None
```

**3. 总字段数为0问题**:
```markdown
验证步骤:
1. 确保项目配置正确匹配数据类型
2. 执行评估
3. 验证总字段数 > 0
4. 验证字段级别准确率显示
```

## 性能测试执行

### 响应时间测试
```bash
# 使用time命令测量评估耗时
echo "开始性能测试..."

# 单任务测试
echo "单任务测试开始: $(date)"
# 执行单任务评估
echo "单任务测试结束: $(date)"

# 多任务测试
echo "多任务测试开始: $(date)"
# 执行多任务评估
echo "多任务测试结束: $(date)"
```

### 内存使用监控
```bash
# 监控Python进程内存使用
ps aux | grep "python.*manage.py runserver" | grep -v grep

# 或使用htop监控系统资源
htop
```

## 自动化测试脚本示例

### 基础功能自动化测试
```markdown
自动化测试流程:
1. 启动浏览器
2. 登录系统
3. 导航到项目1
4. 执行评估流程
5. 验证结果
6. 截图保存
7. 清理环境
```

### 批量项目测试
```bash
# 测试多个项目的评估功能
for project_id in 1 27; do
    echo "测试项目 $project_id"
    # 执行项目特定的评估测试
    # 记录结果
    echo "项目 $project_id 测试完成"
done
```

## 测试结果记录

### 测试报告模板
```markdown
## 评估功能测试报告

### 测试环境
- 测试时间: [日期时间]
- 系统版本: [版本号]
- 浏览器: [浏览器版本]

### 测试结果汇总
- 基础功能测试: ✅/❌
- 配置匹配测试: ✅/❌
- 异常情况测试: ✅/❌
- 边界条件测试: ✅/❌
- 用户界面测试: ✅/❌
- 性能测试: ✅/❌

### 详细测试结果
[具体测试用例的执行结果]

### 发现的问题
[问题描述和严重程度]

### 建议
[改进建议]
```

## 故障排除

### 常见问题及解决方案

**1. 评估对话框不显示**:
```bash
# 检查用户权限
python manage.py shell -c "
from django.contrib.auth.models import User
user = User.objects.get(username='your_username')
print('用户权限:', user.is_superuser, user.is_staff)
"
```

**2. 总字段数显示为0**:
```bash
# 检查项目配置和数据匹配
python manage.py shell -c "
from projects.models import Project
from data_manager.actions.document_evaluation import get_project_evaluation_config

project = Project.objects.get(id=1)
config = get_project_evaluation_config(project)
print('配置允许的文档类型:', config.effective_validation_rules['docType']['allowed_values'])

# 检查实际数据的文档类型
from tasks.models import Task
tasks = Task.objects.filter(project=project)[:5]
for task in tasks:
    if task.data:
        print('任务文档类型:', task.data.get('docType'))
"
```

**3. API调用失败**:
```bash
# 检查API端点和参数
curl -X POST http://127.0.0.1:8080/api/dm/actions/document_evaluation/ \
  -H "Content-Type: application/json" \
  -H "Authorization: Token your_token" \
  -d '{"project": 1, "selectedItems": {"all": false, "included": [task_id]}}'
```

## 测试维护

### 定期检查项目
- 每周执行基础功能测试
- 每月执行完整测试套件
- 新功能发布前执行回归测试

### 测试数据维护
- 定期更新测试数据
- 清理过期的测试结果
- 备份重要的测试配置

### 文档更新
- 新增测试用例时更新文档
- 修复问题后更新测试步骤
- 记录新发现的边界情况 
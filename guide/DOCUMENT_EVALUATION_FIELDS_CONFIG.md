# 单据评估字段动态配置功能

## 功能概述

本功能实现了从前端到后端的统一单据评估字段配置系统，支持不同单据类型（发票、银行回单等）的动态字段配置，极大提升了评估功能的灵活性和可维护性。

## 主要改进

1. **字段配置从硬编码改为动态配置**：不再写死评估字段，支持根据单据类型动态配置
2. **支持多种单据类型**：预定义了发票、银行回单等常见单据类型的字段配置
3. **用户界面友好**：提供直观的前端配置界面，支持自定义字段
4. **改动最少原则**：在现有架构基础上扩展，最小化代码改动

## 技术架构

### 1. 数据存储层

#### 项目模型扩展
- 在 `Project` 模型中添加 `evaluation_field_config` 字段
- 类型：`JSONField`，存储评估字段配置信息
- 配置格式：
```json
{
  "document_type": "invoice|bank_receipt|custom",
  "default_fields": ["field1", "field2", ...],
  "last_updated": "2025-06-20T09:00:00Z"
}
```

### 2. 后端业务逻辑

#### 预定义字段配置
```python
DEFAULT_FIELD_CONFIGS = {
    'invoice': ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "totalTaxAmount"],
    'bank_receipt': ["recieptNum", "logNum", "tradeDate", "amount", "paymentName", "paymentBank", "paymentAccount", "payeeName", "payeeBank", "payeeAccount", "currency"],
    'custom': []  # 用户自定义
}
```

#### 核心函数

1. **`get_evaluation_fields_for_project(project)`**
   - 获取项目的评估字段配置
   - 支持多级回退：用户配置 → 项目默认 → 系统默认

2. **`get_evaluation_fields_by_doc_type(project, doc_type)`**
   - 根据单据类型获取评估字段
   - 支持动态字段配置

3. **`create_evaluation_form(user, project)`**
   - 生成评估动作的表单配置
   - 支持单据类型选择和自定义字段输入

### 3. 前端用户界面

#### 项目设置页面
- 在 `GeneralSettings` 中集成 `EvaluationFieldsConfig` 组件
- 用户可以配置不同单据类型的评估字段

#### 评估动作表单
- 在执行评估时，用户可以选择单据类型
- 支持临时自定义字段配置
- 表单数据会保存到项目配置中

## 使用方式

### 1. 项目设置配置

1. 进入项目设置页面
2. 找到"评估字段配置"section
3. 选择单据类型：
   - **发票 (Invoice)**: 适用于发票和收据
   - **银行回单 (Bank Receipt)**: 适用于银行回单
   - **自定义 (Custom)**: 用户自定义字段
4. 保存配置

### 2. 执行评估

1. 在数据管理器中选择任务
2. 点击"Evaluate Document Extraction"
3. 在弹出的对话框中：
   - 选择单据类型
   - 如选择自定义，输入字段列表（逗号分隔）
4. 确认执行评估

## 支持的单据类型

### 发票 (Invoice)
**适用场景**: 发票、收据等财务单据
**评估字段**: 
- `totalAmount`: 总金额
- `invoiceDate`: 发票日期
- `docType`: 单据类型
- `currency`: 币种
- `billToName`: 收票方名称
- `totalTaxAmount`: 总税额

### 银行回单 (Bank Receipt)
**适用场景**: 银行转账回单、支付凭证等
**评估字段**:
- `recieptNum`: 回单号
- `logNum`: 流水号
- `tradeDate`: 交易日期
- `amount`: 金额
- `paymentName`: 付款方名称
- `paymentBank`: 付款银行
- `paymentAccount`: 付款账号
- `payeeName`: 收款方名称
- `payeeBank`: 收款银行
- `payeeAccount`: 收款账号
- `currency`: 币种

### 自定义 (Custom)
**适用场景**: 其他类型单据或特殊需求
**配置方式**: 用户输入字段列表，用逗号分隔

## 代码变更

### 后端变更

1. **models.py**: 添加 `evaluation_field_config` 字段
2. **serializers.py**: 序列化器中包含新字段
3. **invoice_evaluation.py**: 
   - 添加字段配置函数
   - 修改评估入口函数支持动态字段
   - 添加表单生成函数

### 前端变更

1. **EvaluationFieldsConfig.jsx**: 新增评估字段配置组件
2. **EvaluationFieldsConfig.scss**: 组件样式
3. **GeneralSettings.jsx**: 集成配置组件

### 数据库变更

1. **Migration**: `0031_add_evaluation_field_config.py`

## 扩展性

该方案具有良好的扩展性：

1. **新增单据类型**: 只需在 `DEFAULT_FIELD_CONFIGS` 中添加配置
2. **字段级配置**: 可扩展支持字段级别的权重、验证规则等
3. **多语言支持**: 可扩展支持多语言字段名称
4. **API接口**: 可提供API接口供外部系统配置

## 兼容性

- **向后兼容**: 现有项目会使用默认的发票字段配置
- **平滑升级**: 数据库迁移自动添加新字段，不影响现有数据
- **功能渐进**: 用户可以选择继续使用默认配置或逐步自定义

## 测试建议

1. **单元测试**: 测试字段配置获取函数
2. **集成测试**: 测试完整的评估流程
3. **UI测试**: 测试前端配置界面
4. **兼容性测试**: 测试现有项目的兼容性

## 总结

这个方案通过最少的代码改动，实现了评估字段的动态配置功能，支持多种单据类型，提供了友好的用户界面，同时保持了良好的向后兼容性和扩展性。用户可以根据实际业务需求，灵活配置不同单据类型的评估字段，大大提升了系统的实用性和适应性。 
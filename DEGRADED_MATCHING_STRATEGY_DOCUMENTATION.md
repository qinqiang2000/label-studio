# 降级匹配策略设计文档

## 🎯 背景和问题

### 原始问题
用户反馈在多字段评估时发现严重bug：当配置多个字段一起评估时，如果其中一个字段不匹配，会错误地将所有字段都标记为不匹配。

**具体表现：**
- 配置评估字段 `recieptNum, logNum` 时，100%相等，正常
- 配置评估字段 `recieptNum, logNum, tradeDate` 时，由于6个tradeDate不相等，把对应的recieptNum, logNum都错误判别为不等

### 根本原因
原来的主键字段确定逻辑过于严格，优先选择 `amount` 和 `tradeDate` 作为主键。当 `tradeDate` 不匹配时，整个票据被错误归类，导致字段比较结果错误。

## 🔧 解决方案：降级匹配策略

### 设计理念
1. **简化配置**：用户只需指定字段列表，系统自动处理降级
2. **智能降级**：从完整字段组合逐步降级到单个字段
3. **统一处理**：位置匹配也纳入降级体系
4. **灵活适配**：不同文档类型自动适配字段

### 降级逻辑
```
完整匹配: ["docType", "invoiceDate", "totalAmount"]
     ↓ (如果没找到匹配)
降级1:   ["invoiceDate", "totalAmount"] 
     ↓ (如果没找到匹配)
降级2:   ["totalAmount"]
     ↓ (如果没找到匹配)
位置匹配: ["_position"]
```

## 🏗️ 架构设计

### 核心类：DegradedMatchingStrategy

```python
class DegradedMatchingStrategy:
    """
    降级匹配策略
    核心思想：从完整字段组合逐步降级到单个字段，最后回退到位置匹配
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.verbose = self.config.get('verbose', False)
        self.mode = MatchingMode(self.config.get('mode', 'field_based'))
```

### 匹配模式枚举

```python
class MatchingMode(Enum):
    FIELD_BASED = "field_based"      # 基于字段匹配（支持降级）
    POSITION_BASED = "position_based"  # 基于位置匹配
    AUTO = "auto"                    # 自动选择最佳模式
```

## 📋 配置系统

### 1. 文档类型默认配置

#### 发票 (Invoice)
```python
{
    'mode': 'field_based',
    'primary_fields': [],  # 自动识别
    'include_date': False,
    'max_primary_fields': 3,
    'receipt_keywords': ['invoice', 'number', 'id'],
    'amount_keywords': ['amount', 'total', 'tax'],
    'verbose': True
}
```

#### 银行回单 (Bank Receipt)
```python
{
    'mode': 'field_based',  # 可以配置为position_based
    'primary_fields': [],  # 自动识别
    'include_date': True,
    'receipt_keywords': ['receipt', 'num', 'number'],
    'amount_keywords': ['amount', 'money'],
    'verbose': True
}
```

#### 自定义 (Custom)
```python
{
    'mode': 'field_based',
    'primary_fields': [],  # 用户可以指定
    'include_date': False,
    'max_primary_fields': 3,
    'receipt_keywords': ['num', 'number', 'id', 'code'],
    'amount_keywords': ['amount', 'total', 'money'],
    'verbose': True
}
```

### 2. 用户自定义配置

#### 指定主键字段
```python
strategy_config = {
    'primary_fields': ['recieptNum', 'logNum', 'amount'],
    'verbose': True
}
```

#### 位置匹配模式
```python
strategy_config = {
    'mode': 'position_based',
    'position_tolerance': 0,
    'verbose': True
}
```

## 🔍 智能字段识别

### 字段重要性排序
1. **票据号码类字段**（最重要）：num, number, id, code, receipt, invoice
2. **金额字段**：amount, total, tax, sum, money, price
3. **文档类型字段**：type
4. **日期字段**（可选）：date, time, day

### 自动识别逻辑
```python
def _identify_important_fields(self, all_fields: List[str]) -> List[str]:
    important_fields = []
    
    # 1. 票据号码类字段（最重要）
    receipt_keywords = self.config.get('receipt_keywords', 
                                     ['num', 'number', 'id', 'code', 'receipt', 'invoice'])
    for field in all_fields:
        if any(keyword in field.lower() for keyword in receipt_keywords):
            important_fields.append(field)
            break
    
    # 2. 金额字段
    # 3. 文档类型字段  
    # 4. 日期字段（根据配置决定是否包含）
    # 5. 如果识别的字段不足，补充其他字段
```

## 🚀 使用方法

### 1. API调用方式

```python
from label_studio.data_manager.actions.invoice_evaluation import compare_invoices_with_comparer

# 配置降级匹配策略
config = MockEvaluationConfig({
    'evaluation_settings': {
        'matching_strategy': {
            'type': 'degraded_field_based',
            'mode': 'field_based',
            'primary_fields': ['recieptNum', 'logNum', 'amount'],  # 用户指定
            'verbose': True
        }
    }
})

result = compare_invoices_with_comparer(
    annotation_text, 
    prediction_text, 
    compare_fields,
    document_type='bank_receipt',
    evaluation_config=config
)
```

### 2. 界面配置方式

在项目设置 -> 评估字段配置中：
1. 选择文档类型: 自定义 (Custom)
2. 配置评估字段: docType, invoiceDate, totalAmount
3. 选择匹配策略: 智能字段匹配

### 3. 数据库配置方式

```python
# 在评估配置初始化命令中
'evaluation_settings': {
    'matching_strategy': {
        'type': 'degraded_field_based',
        'mode': 'field_based',
        'primary_fields': [],  # 自动识别或用户指定
        'include_date': False,
        'max_primary_fields': 3,
        'receipt_keywords': ['invoice', 'number', 'id'],
        'amount_keywords': ['amount', 'total', 'tax'],
        'verbose': True
    }
}
```

## 📊 测试结果

### 真实场景测试 - 银行回单数据

**配置：** 指定 recieptNum, logNum, amount 作为主键字段

**测试数据：**
- 标准数据: 3条银行回单
- 预测数据: 3条银行回单（其中2条tradeDate错误）
- 比较字段: ['recieptNum', 'amount', 'tradeDate', 'logNum']

**测试结果：**
- 票据级准确率: 33.33%
- 字段级准确率: 83.33%
- 完全匹配: 1
- 部分匹配: 2

**降级过程：**
```
🔍 处理标准票据 2:
[DegradedMatching] 🎯 使用用户指定的主键字段: ['recieptNum', 'logNum', 'amount']
[DegradedMatching] 🔄 生成降级组合 1: ['recieptNum', 'logNum', 'amount']
[DegradedMatching] 🔄 生成降级组合 2: ['logNum', 'amount']
[DegradedMatching] 🔄 生成降级组合 3: ['amount']
[DegradedMatching] 🔄 添加位置匹配作为最终回退

[DegradedMatching] 🔄 尝试降级级别 1: ['recieptNum', 'logNum', 'amount']
[DegradedMatching]   🔑 主键 recieptNum: '202401002' vs '202401002' = True
[DegradedMatching]   🔑 主键 logNum: 'LOG002' vs 'LOG002' = True
[DegradedMatching]   🔑 主键 amount: '2000.0' vs '2000.0' = True
[DegradedMatching]   ✅ 主键匹配成功，差异字段: ['tradeDate']
[DegradedMatching] ✅ 字段匹配成功，级别 1
```

## 🎯 解决的核心问题

### 修复前
- `recieptNum` 50%, `amount` 50%, `tradeDate` 50%
- 一个字段不匹配导致所有字段都被错误标记

### 修复后
- `recieptNum` 100%, `amount` 100%, `tradeDate` 50% ✅
- 各字段独立正确比较，不再互相影响

## 🔧 调试功能

### 详细调试信息
```
🎯 使用用户指定的主键字段: ['docType', 'invoiceDate', 'totalAmount']
📋 可用字段列表: ['docType', 'invoiceDate', 'totalAmount', 'billToName', 'currency']
🔍 开始字段匹配，标准票据: {'docType': 'invoice', 'invoiceDate': '2024-01-01', 'totalAmount': 100.0}
🔑 主键字段 docType: 标准='invoice', 预测='invoice', 匹配=True
🔑 主键字段 invoiceDate: 标准='2024-01-01', 预测='2024-01-01', 匹配=True
🔑 主键字段 totalAmount: 标准='100.0', 预测='100.0', 匹配=True
🎯 主键匹配结果: True
✅ 找到完全匹配的票据 (索引 0)
```

### 开启调试模式
```python
strategy_config = {
    'verbose': True  # 开启详细调试信息
}
```

## 🌟 优势特性

### 1. 灵活性
- 支持多种文档类型和匹配策略
- 用户可以自定义主键字段
- 自动识别重要字段

### 2. 可扩展性
- 新增匹配策略只需实现基类接口
- 支持不同文档类型的个性化配置
- 模块化设计便于维护

### 3. 向后兼容性
- 现有功能完全保持兼容
- 可以选择使用传统策略或新策略
- 渐进式升级

### 4. 调试友好
- 详细的调试信息便于问题排查
- 清晰的降级过程展示
- 匹配策略使用情况记录

## 📝 配置示例

### 示例1：银行回单自定义主键
```python
{
    "evaluation_field_config": {
        "document_type": "bank_receipt",
        "default_fields": ["recieptNum", "amount", "tradeDate", "logNum"],
        "matching_strategy": {
            "type": "degraded_field_based",
            "mode": "field_based",
            "primary_fields": ["recieptNum", "logNum", "amount"],
            "verbose": True
        }
    }
}
```

### 示例2：发票自动识别
```python
{
    "evaluation_field_config": {
        "document_type": "invoice",
        "default_fields": ["docType", "invoiceDate", "totalAmount", "billToName"],
        "matching_strategy": {
            "type": "degraded_field_based",
            "mode": "field_based",
            "primary_fields": [],  # 自动识别
            "include_date": False,
            "verbose": true
        }
    }
}
```

### 示例3：位置匹配模式
```python
{
    "evaluation_field_config": {
        "document_type": "bank_receipt",
        "default_fields": ["amount", "date", "name"],
        "matching_strategy": {
            "type": "degraded_position_based",
            "mode": "position_based",
            "position_tolerance": 0,
            "verbose": true
        }
    }
}
```

## 🚀 未来扩展

### 1. 更多匹配策略
- 基于相似度的匹配
- 基于机器学习的智能匹配
- 混合策略

### 2. 更智能的字段识别
- 基于字段内容的识别
- 学习用户偏好
- 动态调整权重

### 3. 性能优化
- 并行匹配处理
- 缓存机制
- 批量处理优化

## 📞 使用支持

如果在使用过程中遇到问题，可以：

1. 开启 `verbose: true` 查看详细调试信息
2. 检查配置的 `primary_fields` 是否在实际字段中存在
3. 尝试不同的匹配模式 (`field_based` vs `position_based`)
4. 查看日志中的错误信息和匹配过程

**注意事项：**
- 指定的主键字段必须在实际数据中存在
- 位置匹配适用于数据顺序一致的场景
- 降级匹配会按优先级逐步尝试，直到找到匹配或全部失败 
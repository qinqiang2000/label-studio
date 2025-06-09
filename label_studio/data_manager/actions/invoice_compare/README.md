# 票据比较工具

支持灵活配置比较字段的票据对比工具，可以计算票据级和字段级准确率。

## 功能特性

- ✅ 支持多种数据输入格式（JSON字符串、文件路径、Python列表）
- ✅ **可配置化的比较字段** - 根据需求自定义要比较的字段
- ✅ 智能数据标准化（金额、日期、字符串格式）
- ✅ 详细的比较结果分析
- ✅ 命令行工具和Python API两种使用方式
- ✅ 配置文件支持

## 比较字段配置

### 默认字段
```python
DEFAULT_CORE_FIELDS = [
    'totalAmount',      # 总金额
    'invoiceDate',      # 开票日期  
    'docType',          # 文档类型
    'currency',         # 货币类型
    'billToName',       # 收票方名称
    'totalTaxAmount'    # 总税额
]
```

### 配置方式

#### 1. 编程接口配置
```python
from invoice_compare_utils import InvoiceComparer

# 使用默认字段
comparer = InvoiceComparer(verbose=True)

# 自定义字段
custom_fields = ['totalAmount', 'invoiceDate', 'docType']
comparer = InvoiceComparer(core_fields=custom_fields, verbose=True)

# 从配置文件创建
comparer = InvoiceComparer.from_config_file('config.json', verbose=True)
```

#### 2. 命令行参数配置
```bash
# 使用默认字段
python invoice_compare_utils.py -s standard.json -p prediction.json

# 自定义字段
python invoice_compare_utils.py -s standard.json -p prediction.json -f totalAmount invoiceDate docType

# 使用配置文件
python invoice_compare_utils.py -s standard.json -p prediction.json -c config.json
```

#### 3. 配置文件格式
```json
{
  "core_fields": [
    "totalAmount",
    "invoiceDate", 
    "docType",
    "currency"
  ],
  "description": "自定义比较字段配置"
}
```

## 使用方法

### 生成默认配置文件
```bash
python invoice_compare_utils.py --generate-config default_config.json
```

### 命令行使用
```bash
# 基本使用
python invoice_compare_utils.py -s standard.json -p prediction.json -v

# 自定义字段
python invoice_compare_utils.py -s standard.json -p prediction.json -f totalAmount invoiceDate -v

# 使用配置文件
python invoice_compare_utils.py -s standard.json -p prediction.json -c config.json -v

# 保存结果
python invoice_compare_utils.py -s standard.json -p prediction.json -o result.json
```

### Python API使用
```python
from invoice_compare_utils import InvoiceComparer

# 创建比较器
comparer = InvoiceComparer(
    core_fields=['totalAmount', 'invoiceDate', 'docType'],
    verbose=True
)

# 比较数据
result = comparer.compare_invoices(
    standard_data='standard.json',
    prediction_data='prediction.json'
)

# 查看结果
print(f"票据级准确率: {result['invoice_accuracy']:.2%}")
print(f"字段级准确率: {result['field_accuracy']:.2%}")

# 动态修改字段
comparer.set_core_fields(['totalAmount', 'currency'])
new_result = comparer.compare_invoices(standard_data, prediction_data)
```

## 比较结果说明

结果包含以下信息：
- `matched_count`: 完全匹配的票据数量
- `unmatched_count`: 部分匹配的票据数量
- `only_in_standard_count`: 仅在标准数据中的票据数量
- `only_in_prediction_count`: 仅在预测数据中的票据数量
- `invoice_accuracy`: 票据级准确率
- `field_accuracy`: 字段级准确率
- `unmatched`: 部分匹配的详细信息
- `only_in_standard`: 仅在标准数据中的票据
- `only_in_prediction`: 仅在预测数据中的票据

## 命令行参数

| 参数 | 简写 | 描述 |
|------|------|------|
| `--standard` | `-s` | 标准票据数据文件路径或JSON字符串 |
| `--prediction` | `-p` | 预测票据数据文件路径或JSON字符串 |
| `--output` | `-o` | 输出结果文件路径 |
| `--fields` | `-f` | 自定义要比较的字段列表 |
| `--config` | `-c` | 配置文件路径 |
| `--generate-config` | `-g` | 生成默认配置文件 |
| `--verbose` | `-v` | 显示详细日志 |

## 示例

### 示例1：基础比较
```bash
python invoice_compare_utils.py \
  -s '[{"totalAmount": 100, "docType": "invoice"}]' \
  -p '[{"totalAmount": "100", "docType": "invoice"}]' \
  -v
```

### 示例2：自定义字段比较
```bash
python invoice_compare_utils.py \
  -s standard.json \
  -p prediction.json \
  -f totalAmount docType \
  -o result.json \
  -v
```

### 示例3：配置文件比较
```bash
# 先生成配置文件
python invoice_compare_utils.py -g my_config.json

# 编辑配置文件，然后使用
python invoice_compare_utils.py -s standard.json -p prediction.json -c my_config.json -v
```

## 数据格式要求

输入数据应为JSON数组格式：
```json
[
  {
    "totalAmount": 183700,
    "invoiceDate": "2025-04-06",
    "docType": "invoice",
    "currency": "JPY",
    "billToName": "公司名称",
    "totalTaxAmount": 16700
  }
]
``` 
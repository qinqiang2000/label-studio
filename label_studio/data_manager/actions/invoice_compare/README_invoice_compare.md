# 票据对比工具

一个专业的票据对比和API结果生成工具，支持语义相等判断和准确率计算。

## 功能特性

### 核心功能
- 比较标准票据和预测票据的指定字段
- 支持语义相等判断（金额类型、日期格式、大小写等）
- 生成详细的比较报告和准确率统计
- 支持多种输入格式（JSON字符串、文件、Python对象）

### 比较字段
只比较以下6个核心字段，其他字段完全忽略：
- `totalAmount` - 总金额
- `invoiceDate` - 票据日期  
- `docType` - 文档类型
- `currency` - 币种
- `billToName` - 账单方名称
- `totalTaxAmount` - 总税额

### 语义相等规则
- **金额字段**: 支持int/float/string类型互换
- **日期字段**: 支持多种日期格式（YYYY-MM-DD、YYYY/MM/DD等）
- **字符串字段**: 忽略大小写、首尾空格
- **币种类型**: 忽略大小写

## 安装依赖

```bash
pip install -r requirements.txt
```

依赖的包：
- Python 3.7+
- json（标准库）
- re（标准库）
- datetime（标准库）
- pathlib（标准库）
- typing（标准库）
- dataclasses（标准库）

## 使用方法

### 1. 作为Python库使用

```python
from invoice_compare_utils import InvoiceComparer

# 创建比较器
comparer = InvoiceComparer(verbose=True)

# 标准票据数据
standard_data = [
    {
        "docType": "invoice",
        "invoiceDate": "2025-04-06",
        "totalAmount": 183700,
        "totalTaxAmount": 16700,
        "currency": "JPY",
        "billToName": "ハイセンスジャパン 株式会社"
    }
]

# 预测票据数据
prediction_data = [
    {
        "docType": "invoice",
        "invoiceDate": "2025-04-06",
        "totalAmount": "183700",  # 字符串格式
        "totalTaxAmount": "16700",
        "currency": "JPY",
        "billToName": "ハイセンスジャパン 株式会社"
    }
]

# 进行比较
result = comparer.compare_invoices(standard_data, prediction_data)
print(f"票据级准确率: {result['invoice_accuracy']:.2%}")
print(f"字段级准确率: {result['field_accuracy']:.2%}")
```

### 2. 命令行使用

```bash
# 从文件比较
python invoice_compare_utils.py -s standard.json -p prediction.json -o result.json

# 使用JSON字符串
python invoice_compare_utils.py -s '[{"docType":"invoice",...}]' -p '[{"docType":"invoice",...}]'

# 显示详细日志
python invoice_compare_utils.py -s standard.json -p prediction.json -v
```

### 3. 运行演示

```bash
# 运行完整演示
python demo_invoice_compare.py

# 运行简单示例
python invoice_compare_utils.py
```

## 输出格式

比较结果为JSON格式，包含以下字段：

```json
{
  "matched_count": 1,                    // 完全匹配的票据数
  "unmatched_count": 0,                  // 部分匹配的票据数
  "only_in_standard_count": 0,           // 仅在标准中的票据数
  "only_in_prediction_count": 0,         // 仅在预测中的票据数
  "total_standard": 1,                   // 标准票据总数
  "total_prediction": 1,                 // 预测票据总数
  "correct_field_count": 6,              // 正确字段数
  "total_field_count": 6,                // 标准票据总字段数
  "invoice_accuracy": 1.0,               // 票据级准确率
  "field_accuracy": 1.0,                 // 字段级准确率
  "unmatched": [],                       // 不匹配的详细信息
  "only_in_standard": [],                // 仅在标准中的票据
  "only_in_prediction": []               // 仅在预测中的票据
}
```

### 详细字段说明

- **matched_count**: 所有6个字段都匹配的票据数量
- **unmatched_count**: 通过主键匹配但有字段差异的票据数量
- **only_in_standard_count**: 在标准中存在但预测中找不到的票据数量
- **only_in_prediction_count**: 在预测中存在但标准中找不到的票据数量
- **correct_field_count**: 所有正确字段的总数
- **total_field_count**: 标准票据的总字段数（标准票据数 × 6）
- **invoice_accuracy**: 票据级准确率 = matched_count / total_standard
- **field_accuracy**: 字段级准确率 = correct_field_count / total_field_count

## 匹配逻辑

### 联合唯一匹配
票据通过所有6个核心字段的组合进行匹配，允许语义相等：

1. **完全匹配**: 所有字段都语义相等 → 归入`matched_count`
2. **部分匹配**: 主键字段匹配但其他字段不同 → 归入`unmatched`
3. **无匹配**: 在对方中找不到对应票据 → 归入`only_in_*`

### 主键字段
用于识别同一张票据的关键字段：
- `totalAmount` - 总金额
- `invoiceDate` - 票据日期
- `docType` - 文档类型

## 示例场景

### 完全匹配示例
```python
# 语义相等，被判定为完全匹配
standard = {"totalAmount": 100, "currency": "JPY"}
prediction = {"totalAmount": "100", "currency": "jpy"}
# 结果: matched_count = 1
```

### 部分匹配示例
```python
# 主键匹配但其他字段不同
standard = {"totalAmount": 100, "billToName": "公司A"}
prediction = {"totalAmount": 100, "billToName": "公司B"}
# 结果: unmatched_count = 1, diff_fields = ["billToName"]
```

### 无匹配示例
```python
# 完全找不到对应票据
standard = [{"totalAmount": 100}]
prediction = [{"totalAmount": 200}]
# 结果: only_in_standard_count = 1, only_in_prediction_count = 1
```

## 文件示例

查看以下示例文件：
- `invoice_compare.py` - 基础版本
- `invoice_compare_utils.py` - 完整功能版本
- `demo_invoice_compare.py` - 演示脚本

## 注意事项

1. **字段限制**: 只比较指定的6个核心字段，其他字段会被忽略
2. **语义相等**: 数据类型和格式的细微差异不影响匹配结果
3. **性能**: 大数据量时建议启用verbose=False以提高性能
4. **编码**: 支持UTF-8编码，可处理中文、日文等多语言内容

## 错误处理

工具会处理以下常见错误：
- JSON格式错误
- 文件不存在
- 数据类型不匹配
- 空数据输入

## 许可证

此工具基于MIT许可证开源。 
# 数据导出模块 - 用户故事

本目录包含数据导出相关的用户故事文档。

## 用户故事列表

| 编号 | 用户故事标题 | 状态 | 优先级 | 相关需求文档 | 负责人 | 备注 |
|------|-------------|------|--------|-------------|--------|------|
| US-001 | 生成符合模板格式的Statistics报表 | 待实现 | 高 | evaluation_report_v1.0.md | - | - |
| US-002 | 增强Statistics报表的整体情况统计 | 待实现 | 高 | evaluation_report_v1.0.md | - | - |
| US-003 | 增强Statistics报表的整体指标分析 | 待实现 | 中 | evaluation_report_v1.0.md | - | - |
| US-004 | 保持现有导出功能的一致性 | 待实现 | 高 | evaluation_report_v1.0.md | - | - |

## 详细用户故事文档

- [US-001到004_评估报告生成优化.md](./US-001到004_评估报告生成优化.md) - 评估报告生成优化相关的4个用户故事

## 功能范围

本模块涵盖以下数据导出相关功能：
- Excel报告生成
- 数据统计分析
- 模板格式化
- 数据一致性保证

## 相关技术组件

- `label_studio/data_export/` - 数据导出核心模块
- `label_studio/data_manager/actions/` - 数据管理操作
- Excel模板处理相关组件 
- 测试数据集
注意：假设服务器已经启动，且有热更新
    - 测试数据1

curl -X POST 'http://127.0.0.1:8080/api/dm/actions?id=evaluate_document_extraction_task&tabID=77&project=72' \
-H 'Authorization: Token 4f36015cbf62b6af1e37ac91778e5412bec989f9' \
-H 'Content-Type: application/json' \
-d '{"ordering":[],"selectedItems":{"all":false,"included":[1389,1390,1391]},"filters":{"conjunction":"and","items":[{"filter":"filter:tasks:total_annotations","operator":"greater_or_equal","value":1,"type":"Number"}]},"project":"72"}'

response：
{
    "processed_items": 3,
    "detail": "3 tasks evaluated using Invoice configuration",
    "evaluation_type": "document_extraction",
    "evaluation_results": {
        "project_id": 72,
        "evaluated_at": "2025-06-26T03:10:33.150575",
        "task_count": 3,
        "evaluation_type": "document_extraction",
        "evaluation_config": {
            "name": "Invoice",
            "key": "invoice",
            "fields": [
                "docType",
                "invoiceDate",
                "totalAmount",
                "currency",
                "billToName",
                "totalTaxAmount"
            ]
        },
        "excel_path": "/var/folders/sn/shdg2z_d4ds1b5l83wjxpbvr0000gn/T/tmp27oegh8l.xlsx",
        "statistics": {
            "field_accuracy": {
                "billToName": 100.0,
                "currency": 100.0,
                "docType": 100.0,
                "invoiceDate": 100.0,
                "totalAmount": 80.0,
                "totalTaxAmount": 80.0
            },
            "invoice_accuracy": 80.0,
            "document_accuracy": 66.67,
            "total_invoices": 5,
            "total_documents": 3,
            "correct_invoices": 4,
            "correct_documents": 2,
            "overall_field_accuracy": 93.33,
            "model_version": "gemini-2.5-flash-preview-04-17"
        }
    }
}
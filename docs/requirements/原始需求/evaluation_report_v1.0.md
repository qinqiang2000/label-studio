## 1. 项目背景
项目已经有了一版excel评估报告，但格式和内容需要继续完善

## 2. 需求概述
1、需要根据模版进行生成：label_studio/data_manager/actions/invoice_compare/statisitcs_template_v1.0.xlsx
2、分了四个sheets：Statistics、Document_Details、Predictions、Annotations
3、Document_Details维持现状不变
4、Predictions、Annotations 和label_studio/data_export/ext_export_converter.py导出内容一模一样
5、Statistics参考原来的整体情况、整体指标、核心字段指标。增加：数据分析小结（利用大模型）部分  
6、Statistics的整体情况，增加：
    总文件数（纯other类型文件）	文件下只有other类型的文件总数
    总文件数（含票据文件）	文件下含有票据recept或invoice类型的文件数总数
    总票据数	Receipt或Invoice类型的票据总数
    Invoice数	票据下票件类型是Invoice
    Receipt数	票据下票件类型是Receipt
    模型版本	本次进行识别的Prompts版本
7、Statistics的整体指标，增加：
    可识别率	可以识别为票据的文件占比，总文件数（含票据文件）/总文件数
8、Statistics的数据分析小结（大模型），需求待定

注意：sheet：Statistics需要按照Excel的模版进行生成，包括格式和字体
# ML Backend Analyze API 规范

## Endpoint: /analyze

### 请求方法
POST

### 请求体
```json
{
  "excel_content": "string",        // Excel文件的base64编码内容
  "excel_filename": "string",       // Excel文件名（用于识别和日志）
  "project": "string",              // 项目UID (格式: project_id.timestamp)
  "label_config": "string",         // 项目的标注配置
  "params": {
    "context": "object",            // 可选，上下文信息
    "analysis_type": "string",      // 可选，分析类型，默认为"evaluation"
    "extra_params": "object"        // 可选，额外参数
  }
}
```

### 响应体
```json
{
  "status": "success|error",
  "analysis_result": "string",      // Markdown格式的分析结果
  "metadata": {
    "model_version": "string"       // 分析模型版本
  },
  "error": "string"                 // 错误信息（仅在status为error时返回）
}
```

### 分析结果格式要求
- 返回的 `analysis_result` 必须是有效的 Markdown 格式
- 应包含以下部分（建议）：
  - ## 评估概览
  - ## 核心指标分析
  - ## 问题诊断
  - ## 改进建议
  - ## 详细统计

### 错误处理
- base64解码失败：返回 400 状态码
- 文件格式不支持：返回 400 状态码
- Excel文件损坏：返回 400 状态码
- 内部分析错误：返回 500 状态码

### 示例响应
```json
{
  "status": "success",
  "analysis_result": "## 评估概览\n\n本次评估共分析了15个文档...\n\n## 核心指标分析\n\n### 整体准确率：85.2%\n- 文档识别准确率：92.1%\n- 字段提取准确率：78.3%\n\n## 问题诊断\n\n发现以下主要问题：\n1. 发票日期字段识别准确率偏低(65.4%)\n2. 总金额提取存在格式问题\n\n## 改进建议\n\n1. 优化日期格式识别算法\n2. 增强数字格式处理能力",
  "metadata": {
    "analyzed_at": "2024-01-15T10:30:00Z",
    "excel_file_size": 45632,
    "excel_filename": "evaluation_report.xlsx",
    "analysis_duration": 2.5,
    "model_version": "v1.2.3"
  }
}
``` 
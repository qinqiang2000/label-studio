# ML Backend 错误处理功能

## 概述

本功能扩展了 Label Studio 的 "Retrieve Predictions" 功能，使其能够获取、处理和展示来自 ML backend 的异常信息。当 ML backend 在处理预测请求时遇到超时、地区限制、认证失败等问题时，这些错误信息会被传递给前端并友好地展示给用户。

## 功能特性

### 1. 支持的错误类型

- **timeout_error**: 请求超时
- **region_not_supported**: 地区不支持
- **authentication_error**: 认证失败
- **network_error**: 网络连接问题
- **empty_prediction**: 模型返回空预测
- **processing_error**: 其他处理错误
- **critical_error**: 严重错误

### 2. 错误信息传递流程

```
ML Backend → Label Studio Backend → Frontend → User
```

1. **ML Backend**: 返回包含 `errors` 字段的响应
2. **Label Studio Backend**: 解析错误信息并存储
3. **Frontend**: 接收错误信息并展示给用户
4. **User**: 看到友好的错误提示和详细信息

### 3. 响应格式

#### ML Backend 新格式响应
```json
{
  "results": {
    "model_version": "gemini-2.5-flash-preview-04-17",
    "predictions": [
      {
        "result": [...],
        "score": 0.9,
        "model_version": "..."
      }
    ],
    "errors": [
      {
        "task_index": 1,
        "task_id": "task-456",
        "error_type": "timeout_error",
        "error_message": "Request timed out after 30 seconds"
      }
    ]
  }
}
```

#### Label Studio API 响应
```json
{
  "processed_items": 5,
  "detail": "Retrieved 5 predictions (with 2 errors from ML backend)",
  "ml_errors": [
    {
      "task_index": 1,
      "task_id": "task-456",
      "error_type": "timeout_error",
      "error_message": "Request timed out after 30 seconds"
    }
  ],
  "error_summary": {
    "timeout_error": 1,
    "region_not_supported": 1
  }
}
```

## 实现细节

### 后端修改

#### 1. ML Backend 响应处理 (`label_studio/ml/models.py`)

```python
def _get_predictions_from_ml_backend(self, serialized_tasks, prompt_name=None):
    # 检查是否是新格式（包含 predictions 和 errors）
    if isinstance(results_data, dict) and 'predictions' in results_data:
        predictions = results_data.get('predictions', [])
        errors = results_data.get('errors', [])
        
        # 记录错误信息
        if errors:
            logger.warning(f"ML backend返回了 {len(errors)} 个错误")
        
        # 将错误信息存储到实例中
        self._last_prediction_errors = errors
        responses = predictions
    else:
        # 兼容旧格式
        self._last_prediction_errors = []
        responses = results_data
```

#### 2. 预测任务处理 (`label_studio/ml/models.py`)

```python
def predict_tasks(self, tasks, prompt_name=None):
    # ... 现有逻辑 ...
    
    # 获取错误信息
    errors = getattr(self, '_last_prediction_errors', [])
    
    # 返回包含错误信息的结果
    result = {
        'model_version': model_version,
        'predictions_count': len(instances),
        'errors': errors,
        'instances': instances
    }
    
    return result
```

#### 3. Action 处理 (`label_studio/data_manager/actions/basic.py`)

```python
def retrieve_tasks_predictions(queryset, **kwargs):
    # ... 现有逻辑 ...
    
    # 检查是否有ML错误
    ml_errors = getattr(project, '_last_ml_errors', [])
    
    response = {
        'processed_items': queryset.count(),
        'detail': f'Retrieved {queryset.count()} predictions'
    }
    
    # 如果有错误，添加到响应中
    if ml_errors:
        response['ml_errors'] = ml_errors
        response['detail'] += f' (with {len(ml_errors)} errors from ML backend)'
        
        # 构建错误摘要
        error_summary = {}
        for error in ml_errors:
            error_type = error.get('error_type', 'unknown')
            error_summary[error_type] = error_summary.get(error_type, 0) + 1
        
        response['error_summary'] = error_summary
    
    return response
```

### 前端修改

#### 错误显示逻辑 (`web/libs/datamanager/src/components/DataManager/Toolbar/ActionsButton.jsx`)

```javascript
// 检查是否有ML错误并显示
if (result && result.ml_errors && result.ml_errors.length > 0) {
  console.warn("检测到ML backend错误:", result.ml_errors);
  
  // 构建错误消息
  const errorMessages = result.ml_errors.map(error => {
    return `${error.error_type}: ${error.error_message}`;
  });
  
  // 显示错误摘要
  const errorSummary = result.error_summary || {};
  const summaryText = Object.entries(errorSummary)
    .map(([type, count]) => `${type}: ${count}`)
    .join(', ');
  
  // 使用 Toast 显示错误信息
  store.SDK.invoke("toast", { 
    message: `预测完成但有错误: ${summaryText}`, 
    type: "warning",
    duration: 8000
  });
}
```

## 向后兼容性

本功能完全向后兼容：

1. **旧格式ML Backend**: 继续正常工作，不会显示错误信息
2. **现有API调用**: 无需修改，`errors` 字段为可选
3. **前端代码**: 自动检测是否有错误信息，无错误时正常显示

## 用户体验

### 1. 成功场景
- 正常显示预测结果
- 无额外提示

### 2. 部分失败场景
- 显示成功处理的任务数量
- Toast 提示：`预测完成但有错误: timeout_error: 2, region_not_supported: 1`
- 控制台显示详细错误信息

### 3. 全部失败场景
- 显示处理的任务数量为0
- Toast 提示具体错误类型和数量
- 用户可以根据错误类型采取相应措施

## 调试和监控

### 日志输出

```
🎯 [ML ERRORS] ML backend返回了 2 个错误:
🎯 [ML ERRORS] 任务 1 (ID: task-456): [timeout_error] Request timed out after 30 seconds
🎯 [ML ERRORS] 任务 2 (ID: task-789): [region_not_supported] API access not available in your region
🎯 [ML ERRORS] predict_tasks完成，成功: 3, 失败: 2
```

### 前端控制台

```javascript
[ML ERRORS] 检测到ML backend错误: [
  {
    task_index: 1,
    task_id: "task-456", 
    error_type: "timeout_error",
    error_message: "Request timed out after 30 seconds"
  }
]
```

## 配置和部署

### 无需额外配置

本功能无需额外配置，自动检测ML backend的响应格式：

- 如果ML backend返回新格式（包含errors），则处理和显示错误
- 如果ML backend返回旧格式，则正常工作，不显示错误信息

### 部署注意事项

1. **数据库迁移**: 无需额外迁移
2. **ML Backend升级**: 可选，升级后可享受错误处理功能
3. **前端更新**: 自动生效，无需用户操作

## 故障排除

### 常见问题

1. **错误信息不显示**
   - 检查ML backend是否返回新格式响应
   - 查看后端日志确认错误信息是否被正确解析

2. **Toast消息不显示**
   - 检查浏览器控制台是否有JavaScript错误
   - 确认 `store.SDK.invoke("toast")` 方法可用

3. **错误分类不准确**
   - ML backend负责错误分类，检查其错误分类逻辑

### 调试步骤

1. 检查后端日志中的 `🎯 [ML ERRORS]` 标记
2. 检查前端控制台中的 `[ML ERRORS]` 日志
3. 验证API响应中是否包含 `ml_errors` 字段
4. 确认Toast组件正常工作

## 总结

ML Backend错误处理功能为Label Studio提供了更好的错误可见性和用户体验。用户现在可以：

- 了解哪些任务的预测失败了
- 知道失败的具体原因（超时、地区限制等）
- 根据错误类型采取相应的解决措施
- 在批量处理时获得详细的成功/失败统计

该功能完全向后兼容，可以安全地部署到现有环境中。 
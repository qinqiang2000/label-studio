# Label Studio 评估功能

## 概述

本功能为 Label Studio 的 Data Manager 添加了两个新的评估操作，用于分析标注质量和预测准确性。

## 功能特性

### 1. 预测与标注对比评估 (Evaluate Predictions vs Annotations)

- **功能**: 比较机器学习模型的预测结果与人工标注的准确性
- **用途**: 评估模型性能，识别预测错误的任务
- **输出指标**:
  - 准确率 (Accuracy)
  - 精确率 (Precision) 
  - 召回率 (Recall)
  - F1分数 (F1-Score)
  - 处理的任务数量

### 2. 标注者间一致性评估 (Calculate Inter-Annotator Agreement)

- **功能**: 计算不同标注者之间的一致性程度
- **用途**: 评估标注质量，识别有争议的任务
- **输出指标**:
  - 一致性百分比
  - Kappa系数
  - 有争议的任务数量
  - 处理的任务数量

## 使用方法

1. 在 Label Studio 中打开项目
2. 进入 Data Manager 页面
3. 选择要评估的任务
4. 点击 "Actions" 按钮
5. 选择相应的评估操作:
   - "Evaluate Predictions vs Annotations" - 预测与标注对比
   - "Calculate Inter-Annotator Agreement" - 标注者间一致性
6. 确认操作后查看评估结果

## 技术实现

### 文件结构

```
label_studio/
├── data_manager/
│   └── actions/
│       └── evaluation.py         # 评估功能实现
├── core/
│   └── settings/
│       └── base.py               # Django设置配置
└── tests/
    └── data_manager/
        └── actions/
            └── test_evaluation.py # 功能测试脚本
```

### 核心组件

- **evaluation.py**: 包含评估逻辑和操作定义
- **base.py**: 在 `DATA_MANAGER_ACTIONS` 中注册评估操作
- **test_evaluation.py**: 验证功能正常工作的测试脚本（位于tests目录）

## 权限要求

- 用户需要具有 `projects.view_project` 权限才能执行评估操作
- 评估操作只对有权限访问的项目可见

## 注意事项

1. 评估功能目前使用模拟数据进行演示
2. 实际部署时需要根据具体的标注格式调整评估逻辑
3. 大量任务的评估可能需要较长时间，建议分批处理
4. 评估结果会显示在操作完成后的通知中

## 扩展开发

如需添加新的评估指标或功能：

1. 在 `evaluation.py` 中添加新的评估函数
2. 在 `base.py` 的 `DATA_MANAGER_ACTIONS` 中注册新操作
3. 更新测试脚本验证新功能
4. 更新本文档说明新功能的使用方法
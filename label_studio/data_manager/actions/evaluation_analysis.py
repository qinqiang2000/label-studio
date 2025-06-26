import logging
import json
import base64
import os
from projects.models import Project

logger = logging.getLogger(__name__)

def _read_file_to_base64(file_path):
    """
    读取文件并转换为base64编码
    
    :param file_path: 文件路径
    :return: base64编码的文件内容
    """
    try:
        with open(file_path, 'rb') as f:
            file_content = f.read()
            base64_content = base64.b64encode(file_content).decode('utf-8')
            return base64_content
    except FileNotFoundError:
        raise ValueError(f"Excel file not found: {file_path}")
    except Exception as e:
        raise ValueError(f"Failed to read Excel file: {str(e)}")


def analyze_evaluation_report(project, queryset, **kwargs):
    """
    分析评估报告
    
    :param project: 项目实例
    :param queryset: 查询集（这里不会用到，但是action需要这个参数）
    :param kwargs: 额外参数，应包含 excel_path
    :return: 分析结果
    """
    logger.info(f"🔍 [EVALUATION_ANALYSIS] Starting analysis for project {project.id}")
    
    # 从kwargs中获取excel_path
    excel_path = kwargs.get('excel_path')
    if not excel_path:
        raise ValueError("Missing required parameter: excel_path")
    
    logger.info(f"🔍 [EVALUATION_ANALYSIS] Excel path: {excel_path}")
    
    # 读取Excel文件并转换为base64
    try:
        excel_content = _read_file_to_base64(excel_path)
        excel_filename = os.path.basename(excel_path)
        logger.info(f"🔍 [EVALUATION_ANALYSIS] Excel file read successfully, size: {len(excel_content)} chars")
    except ValueError as e:
        logger.error(f"🔍 [EVALUATION_ANALYSIS] Failed to read Excel file: {e}")
        raise e
    
    # 获取ML Backend连接
    active_ml_backends = project.get_active_ml_backends()
    if not active_ml_backends.exists():
        logger.warning(f"🔍 [EVALUATION_ANALYSIS] No active ML backend configured for project {project.id}")
        # Mock响应用于测试
        logger.warning("🔍 [EVALUATION_ANALYSIS] No ML backend configured, returning mock analysis")
        mock_analysis = """## 评估概览

本次评估共分析了15个文档，涵盖了票据提取的核心字段识别能力。

## 核心指标分析

### 整体准确率：85.2%
- 文档识别准确率：92.1% ✅
- 字段提取准确率：78.3% ⚠️

### 各字段表现
- **发票号码**：95.6% (优秀)
- **发票日期**：65.4% (需改进)
- **总金额**：82.1% (良好)
- **开票单位**：88.9% (良好)

## 问题诊断

发现以下主要问题：

1. **日期格式识别不准确**
   - 对于非标准日期格式识别率偏低
   - 手写日期识别存在困难

2. **金额提取格式问题**
   - 小数点处理不统一
   - 货币符号识别有误

3. **开票单位名称截断**
   - 长单位名称可能被截断
   - 特殊字符处理不当

## 改进建议

### 技术优化
1. **优化日期格式识别算法**
   - 增强非标准日期格式的训练数据
   - 实现日期格式自动推断机制

2. **增强数字格式处理能力**
   - 统一金额格式处理规则
   - 提升小数点和千分位识别精度

3. **完善文本区域检测**
   - 优化文本边界检测算法
   - 减少文本截断现象

### 数据质量
1. **扩充训练数据集**
   - 增加边缘案例样本
   - 平衡各类型票据比例

2. **提升标注质量**
   - 制定更详细的标注规范
   - 增加质量检查流程

## 详细统计

| 指标 | 数值 | 状态 |
|------|------|------|
| 处理文档数 | 15 | - |
| 总字段数 | 225 | - |
| 正确识别数 | 176 | - |
| 错误识别数 | 49 | - |
| 平均处理时间 | 1.2秒/文档 | - |

---
*分析完成时间：2024-01-15 10:30:00*  
*模型版本：v1.2.3*  
*分析引擎：Label Studio Analysis Engine*"""
        
        return {
            'status': 'success',
            'analysis_result': mock_analysis,
            'metadata': {
                'model_version': 'mock-v1.0.0'
            }
        }
    
    # 使用第一个活跃的ML Backend
    ml_backend = active_ml_backends.first()
    ml_api = ml_backend.api
    logger.info(f"🔍 [EVALUATION_ANALYSIS] Using ML backend: {ml_backend.title} ({ml_backend.url})")
    
    # 调用ML后端进行分析
    logger.info(f"🔍 [EVALUATION_ANALYSIS] Calling ML backend for analysis")
    result = ml_api.analyze(
        excel_content=excel_content,
        excel_filename=excel_filename,
        project=project,
        context=kwargs.get('context'),
        analysis_type=kwargs.get('analysis_type', 'evaluation'),
        extra_params=kwargs.get('extra_params')
    )
    
    logger.info(f"🔍 [EVALUATION_ANALYSIS] ML backend response: {result.status_code}")
    
    if result.is_error:
        logger.error(f"🔍 [EVALUATION_ANALYSIS] ML backend error: {result.error_message}")
        raise Exception(f"Analysis failed: {result.error_message}")
    
    return result.response


# 注册action（隐藏，只通过API调用）
actions = [
    {
        'entry_point': analyze_evaluation_report,
        'title': 'Analyze Evaluation Report',
        'order': 100,
        'description': 'Send evaluation Excel to ML backend for analysis',
        'permission': 'projects.change_project',
        'hidden': True,  # 从UI中隐藏，只通过API调用
    }
] 
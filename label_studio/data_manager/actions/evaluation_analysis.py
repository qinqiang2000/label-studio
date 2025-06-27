import logging
import json
import base64
import os
from projects.models import Project
from datetime import datetime

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


def analyze_evaluation_report(user_id, project_id, queryset=None, **params):
    """
    分析评估报告，调用ML Backend的analyze方法
    """
    logger.info(f"Starting analysis for project {project_id}")
    
    try:
        project = Project.objects.get(pk=project_id)
        
        # 从参数中获取Excel文件路径
        excel_path = params.get('excel_path')
        if not excel_path:
            raise ValueError("Missing excel_path parameter")
        
        # 检查文件是否存在
        if not os.path.exists(excel_path):
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        # 读取Excel文件并转换为base64
        try:
            with open(excel_path, 'rb') as f:
                excel_binary = f.read()
            excel_content = base64.b64encode(excel_binary).decode('utf-8')
            excel_filename = os.path.basename(excel_path)
            logger.info(f"Excel file read successfully, size: {len(excel_content)} chars")
        except Exception as e:
            raise ValueError(f"Failed to read Excel file: {e}")
        
        # 准备ML Backend连接
        ml_backends = project.ml_backends.filter(state='CO')
        if not ml_backends.exists():
            raise ValueError("No ML Backend available for this project")
        
        ml_backend = ml_backends.first()
        logger.info(f"Using ML Backend: {ml_backend.url}")
        
        # 提取prompt参数
        prompt_content = None
        if 'prompt' in params:
            prompt_content = params['prompt']
        elif 'params' in params and 'prompt' in params['params']:
            prompt_content = params['params']['prompt']
        
        # 准备ML Backend analyze请求的参数
        context = {
            'evaluation_type': 'document_extraction',
            'description': '评估结果分析'
        }
        
        # 构建extra_params，包含prompt
        extra_params = {}
        if prompt_content:
            extra_params['prompt'] = prompt_content
            logger.info("Custom prompt provided for analysis")
        else:
            logger.info("Using default ML Backend prompt")
        
        # 调用ML Backend的analyze方法
        try:
            result = ml_backend.api.analyze(
                excel_content=excel_content,
                excel_filename=excel_filename,
                project=project,
                context=context,
                analysis_type='evaluation',
                extra_params=extra_params
            )
            
            # 如果result是MLApiResult对象，提取响应数据
            if hasattr(result, 'response'):
                if result.is_error:
                    logger.error(f"ML Backend error: {result.error_message}")
                    raise ValueError(f"ML Backend analysis failed: {result.error_message}")
                else:
                    logger.info("Analysis completed successfully")
                    return result.response
            else:
                logger.info("Analysis completed successfully")
                return result
            
        except Exception as e:
            logger.error(f"ML Backend call failed: {e}")
            raise
        
    except Exception as e:
        logger.error(f"Analysis failed: {str(e)}")
        raise


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
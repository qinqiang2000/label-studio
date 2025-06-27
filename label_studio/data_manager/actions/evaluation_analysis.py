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
    print(f"🔍 [后端调试] analyze_evaluation_report被调用")
    print(f"🔍 [后端调试] user_id: {user_id}")
    print(f"🔍 [后端调试] project_id: {project_id}")
    print(f"🔍 [后端调试] queryset: {queryset}")
    print(f"🔍 [后端调试] params: {json.dumps(params, indent=2, ensure_ascii=False)}")
    
    # 检查params中是否包含prompt
    prompt_param = params.get('prompt')
    print(f"🔍 [后端调试] 提取的prompt参数: {prompt_param}")
    
    # 检查嵌套结构中的prompt
    if 'params' in params:
        nested_params = params.get('params', {})
        nested_prompt = nested_params.get('prompt')
        print(f"🔍 [后端调试] 嵌套params中的prompt: {nested_prompt}")
    
    try:
        project = Project.objects.get(pk=project_id)
        
        # 从参数中获取Excel文件路径
        excel_path = params.get('excel_path')
        if not excel_path:
            print(f"❌ [后端调试] 缺少excel_path参数")
            raise ValueError("Missing excel_path parameter")
        
        print(f"📁 [后端调试] Excel文件路径: {excel_path}")
        
        # 检查文件是否存在
        if not os.path.exists(excel_path):
            print(f"❌ [后端调试] Excel文件不存在: {excel_path}")
            raise FileNotFoundError(f"Excel file not found: {excel_path}")
        
        # 读取Excel文件并转换为base64
        try:
            with open(excel_path, 'rb') as f:
                excel_binary = f.read()
            excel_content = base64.b64encode(excel_binary).decode('utf-8')
            excel_filename = os.path.basename(excel_path)
            print(f"✅ [后端调试] Excel文件已读取并转换为base64")
            print(f"📄 [后端调试] 文件名: {excel_filename}")
            print(f"📊 [后端调试] Base64内容大小: {len(excel_content)} 字符")
        except Exception as e:
            print(f"❌ [后端调试] 读取Excel文件失败: {e}")
            raise ValueError(f"Failed to read Excel file: {e}")
        
        # 准备ML Backend连接
        ml_backends = project.ml_backends.filter(state='CO')  # 只要求连接状态为Connected
        if not ml_backends.exists():
            print(f"❌ [后端调试] 项目没有可用的ML Backend")
            raise ValueError("No ML Backend available for this project")
        
        ml_backend = ml_backends.first()
        print(f"✅ [后端调试] 找到ML Backend: {ml_backend.url}")
        
        # 提取prompt参数
        prompt_content = None
        if 'prompt' in params:
            prompt_content = params['prompt']
            print(f"✅ [后端调试] 从根级别提取prompt参数: {prompt_content[:100] if prompt_content else None}...")
        elif 'params' in params and 'prompt' in params['params']:
            prompt_content = params['params']['prompt']
            print(f"✅ [后端调试] 从嵌套params提取prompt参数: {prompt_content[:100] if prompt_content else None}...")
        
        # 准备ML Backend analyze请求的参数
        context = {
            'evaluation_type': 'document_extraction',
            'description': '评估结果分析'
        }
        
        # 构建extra_params，包含prompt
        extra_params = {}
        if prompt_content:
            extra_params['prompt'] = prompt_content
            print(f"✅ [后端调试] 添加prompt到extra_params")
        else:
            print(f"⚠️ [后端调试] 未提供prompt，使用ML Backend默认prompt")
        
        print(f"📤 [后端调试] 发送给ML Backend的参数:")
        print(f"  - excel_filename: {excel_filename}")
        print(f"  - excel_content大小: {len(excel_content)} 字符")
        print(f"  - context: {json.dumps(context, indent=2, ensure_ascii=False)}")
        print(f"  - extra_params: {json.dumps({k: v[:100] + '...' if k == 'prompt' and len(str(v)) > 100 else v for k, v in extra_params.items()}, indent=2, ensure_ascii=False)}")
        
        # 调用ML Backend的analyze方法 - 使用正确的参数格式
        try:
            result = ml_backend.api.analyze(
                excel_content=excel_content,
                excel_filename=excel_filename,
                project=project,
                context=context,
                analysis_type='evaluation',
                extra_params=extra_params
            )
            print(f"📥 [后端调试] ML Backend返回结果: {type(result)}")
            
            # 如果result是MLApiResult对象，提取响应数据
            if hasattr(result, 'response'):
                if result.is_error:
                    print(f"❌ [后端调试] ML Backend返回错误: {result.error_message}")
                    raise ValueError(f"ML Backend analysis failed: {result.error_message}")
                else:
                    print(f"✅ [后端调试] ML Backend分析成功")
                    return result.response
            else:
                print(f"✅ [后端调试] ML Backend分析成功（直接返回响应）")
                return result
            
        except Exception as e:
            print(f"❌ [后端调试] ML Backend调用失败: {e}")
            print(f"❌ [后端调试] 错误类型: {type(e)}")
            import traceback
            print(f"❌ [后端调试] 错误堆栈:\n{traceback.format_exc()}")
            raise
        
    except Exception as e:
        print(f"❌ [后端调试] analyze_evaluation_report整体失败: {str(e)}")
        print(f"❌ [后端调试] 错误类型: {type(e)}")
        import traceback
        print(f"❌ [后端调试] 错误堆栈:\n{traceback.format_exc()}")
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
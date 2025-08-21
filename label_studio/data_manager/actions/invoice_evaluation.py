"""
Legacy Invoice Evaluation Module

This module provides backward compatibility for invoice evaluation.
All new functionality should use document_evaluation.py instead.

This module acts as an adapter to the new generic document evaluation system.
"""

import logging
from datetime import datetime
from core.permissions import AllPermissions

logger = logging.getLogger(__name__)
all_permissions = AllPermissions()

# Import the new evaluation system
from .document_evaluation import (
    evaluate_documents as evaluate_document_extraction_task,
    actions as document_actions,
    get_project_evaluation_config
)

# Default field configurations for backward compatibility
DEFAULT_FIELD_CONFIGS = {
    'invoice': ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "totalTaxAmount"],
    'receipt': ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "totalTaxAmount"],
    'bank_receipt': ["recieptNum", "tradeDate", "amount", "paymentName", "paymentBank", "paymentAccount", "payeeName", "payeeBank", "payeeAccount", "currency"],
    'other': ["docType", "totalAmount", "currency"]
}

def get_evaluation_fields_for_project(project):
    """
    获取项目的评估字段配置 - 向后兼容性函数
    
    :param project: 项目实例
    :return: 字段列表
    """
    # 使用新的评估配置系统
    try:
        evaluation_config = get_project_evaluation_config(project)
        if evaluation_config and hasattr(evaluation_config.evaluation_config, 'fields'):
            return evaluation_config.evaluation_config.fields
    except Exception as e:
        logger.warning(f"Failed to get evaluation config from new system: {e}")
    
    # 兜底使用旧的配置方式
    config = getattr(project, 'evaluation_field_config', None) or {}
    
    if not config:
        return DEFAULT_FIELD_CONFIGS['invoice']
    
    # 优先使用专门的evaluation_fields配置（不影响标注模块）
    if 'evaluation_fields' in config:
        return config['evaluation_fields']
    
    if 'default_fields' in config:
        return config['default_fields']
    
    if 'document_types' in config:
        all_fields = set(['docType'])
        for doc_type, fields in config['document_types'].items():
            all_fields.update(fields)
        return sorted(list(all_fields))
    
    return DEFAULT_FIELD_CONFIGS['invoice']

def evaluate_invoice_extraction_task(project, queryset, **kwargs):
    """
    票据提取任务评估入口函数 - 向后兼容性函数
    实际调用新的通用文档评估系统
    """
    logger.info(f"Using legacy invoice evaluation interface for project {project.id}")
    logger.info("This interface is deprecated. Please use document_evaluation.py directly.")
    
    # 调用新的文档评估系统
    return evaluate_document_extraction_task(project, queryset, **kwargs)

def evaluate_invoices(queryset, project, **kwargs):
    """
    Legacy function for invoice evaluation
    This function provides backward compatibility by calling the new generic document evaluation system
    """
    return evaluate_invoice_extraction_task(project, queryset, **kwargs)

def create_evaluation_form(user, project):
    """
    为评估动作创建表单 - 向后兼容性函数
    """
    # 直接使用新系统的表单创建功能
    from .document_evaluation import create_evaluation_form as new_create_form
    return new_create_form(user, project)

# 注册票据提取评估动作 - 使用新系统的actions
invoice_actions = document_actions
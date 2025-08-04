"""
Utility functions for prompts management
"""
import logging
from django.db.models import Q

logger = logging.getLogger(__name__)


def get_user_accessible_prompts(user, limit=None):
    """
    获取用户可访问的prompts（按workspace过滤）
    
    :param user: User instance
    :param limit: Optional limit for number of prompts to return
    :return: QuerySet of accessible prompts
    """
    from .models import Prompt
    
    if not user or not user.is_authenticated:
        return Prompt.objects.none()
    
    # 基础查询：同一组织的prompts
    prompts_query = Prompt.objects.filter(created_by__active_organization=user.active_organization)
    
    # 如果不是超级用户，则按workspace过滤
    if not user.is_superuser:
        prompts_query = prompts_query.filter(
            Q(workspaces__isnull=True) |  # 组织级别的prompts（没有关联workspace的）
            Q(workspaces__members=user)   # 用户所属workspace的prompts
        ).distinct()
    
    # 按更新时间排序
    prompts_query = prompts_query.order_by('-updated_at')
    
    # 应用限制
    if limit and limit > 0:
        prompts_query = prompts_query[:limit]
    
    return prompts_query


def get_user_accessible_prompts_list(user, limit=None):
    """
    获取用户可访问的prompts列表（用于API返回）
    
    :param user: User instance
    :param limit: Optional limit for number of prompts to return
    :return: List of prompt dictionaries
    """
    prompts = get_user_accessible_prompts(user, limit)
    
    return [
        {
            'id': prompt.id,
            'name': prompt.name,
            'content': prompt.content,
            'temperature': prompt.temperature,
            'response_schema': prompt.response_schema,
            'created_at': prompt.created_at.isoformat() if prompt.created_at else None,
            'updated_at': prompt.updated_at.isoformat() if prompt.updated_at else None,
        }
        for prompt in prompts
    ]


def get_user_accessible_prompt_options(user, limit=None):
    """
    获取用户可访问的prompts选项（用于表单下拉列表）
    
    :param user: User instance
    :param limit: Optional limit for number of prompts to return
    :return: List of option dictionaries with label and value
    """
    prompts = get_user_accessible_prompts(user, limit)
    
    options = [{"label": "None", "value": ""}]  # 默认"无"选项
    
    for prompt in prompts:
        options.append({
            "label": prompt.name,
            "value": prompt.name
        })
    
    return options
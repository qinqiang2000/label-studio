"""Utility functions for prompts management."""
import logging

logger = logging.getLogger(__name__)


def get_user_accessible_prompts(user, limit=None):
    """获取用户可访问的 prompts（按 workspace 隔离，超管可见全部）。"""
    from .models import Prompt

    if not user or not user.is_authenticated:
        return Prompt.objects.none()

    qs = Prompt.objects.select_related('workspace', 'created_by')
    if not user.is_superuser:
        qs = qs.filter(workspace__members=user).distinct()

    qs = qs.order_by('-updated_at')

    if limit and limit > 0:
        qs = qs[:limit]

    return qs


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
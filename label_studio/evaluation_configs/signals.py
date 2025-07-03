"""
Django信号处理器
用于在合适的时机自动加载配置，避免在应用初始化时访问数据库
"""

import logging
from django.db.models.signals import post_migrate
from django.dispatch import receiver
from django.apps import apps

logger = logging.getLogger(__name__)


@receiver(post_migrate)
def load_evaluation_configs_after_migrate(sender, **kwargs):
    """
    在数据库迁移完成后自动加载评估配置
    这是Django推荐的在迁移后执行数据初始化的方式
    """
    # 只在evaluation_configs应用的迁移完成后执行
    if sender.name == 'evaluation_configs':
        try:
            from .config_loader import auto_load_evaluation_configs
            from .models import EvaluationFieldConfig
            
            # 检查是否已有配置
            existing_count = EvaluationFieldConfig.objects.count()
            
            if existing_count == 0:
                # 只在没有配置时加载
                stats = auto_load_evaluation_configs()
                logger.info(f"Auto-loaded evaluation configs after migration: {stats}")
            else:
                logger.info(f"Evaluation configs already exist ({existing_count} configs), skipping auto-load")
                
        except Exception as e:
            logger.error(f"Failed to auto-load evaluation configs after migration: {e}")
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class EvaluationConfigsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evaluation_configs'
    verbose_name = 'Evaluation Configurations'
    
    def ready(self):
        """在Django应用启动时自动加载评估配置"""
        try:
            from .config_loader import auto_load_evaluation_configs
            stats = auto_load_evaluation_configs()
            logger.info(f"Auto-loaded evaluation configs: {stats}")
        except Exception as e:
            logger.error(f"Failed to auto-load evaluation configs: {e}") 
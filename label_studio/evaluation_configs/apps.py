import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class EvaluationConfigsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evaluation_configs'
    verbose_name = 'Evaluation Configurations'
    
    def ready(self):
        """
        Django应用就绪时的初始化
        导入信号处理器，在迁移完成后自动加载配置
        """
        # 导入信号处理器，这样它们会被注册
        from . import signals
        logger.info("EvaluationConfigs app is ready. Signals registered for post-migration config loading.") 
import logging
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class EvaluationConfigsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'evaluation_configs'
    verbose_name = 'Evaluation Configurations'
    
    def ready(self):
        """
        Django应用就绪时注册信号处理器
        避免在应用初始化时直接访问数据库
        """
        # 只在非迁移命令时加载配置
        import sys
        if 'migrate' not in sys.argv and 'makemigrations' not in sys.argv:
            try:
                # 延迟导入，避免循环导入
                from django.db import connection
                from django.db.utils import OperationalError
                
                # 检查数据库是否可用
                try:
                    connection.ensure_connection()
                    if connection.is_usable():
                        from .config_loader import auto_load_evaluation_configs
                        stats = auto_load_evaluation_configs()
                        logger.info(f"Auto-loaded evaluation configs: {stats}")
                except OperationalError:
                    logger.warning("Database not ready, skipping config auto-load")
            except Exception as e:
                logger.error(f"Failed to auto-load evaluation configs: {e}") 
from django.apps import AppConfig


class ProjectsConfig(AppConfig):
    name = 'projects'
    default_auto_field = 'django.db.models.BigAutoField'
    
    def ready(self):
        # 导入信号处理器
        import projects.auto_storage
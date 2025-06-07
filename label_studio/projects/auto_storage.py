import os
import logging
import yaml
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from pathlib import Path

from projects.models import Project
from io_storages.localfiles.models import LocalFilesImportStorage

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Project)
def auto_create_local_storage(sender, instance, created, **kwargs):
    """
    自动为新创建的项目添加本地文件存储并设置label_config
    
    功能：
    1. 自动设置项目的label_config为document-ai模板（总是执行）
    2. 当环境变量LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED为true时：
       - 在LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT目录下创建项目ID子目录
       - 自动添加本地文件存储，title为create_by_code，路径为新建的目录
    """
    if not created:
        # 只处理新创建的项目
        return
    
    # 首先自动设置label_config（不依赖环境变量）
    # BASE_DIR指向label_studio/core，需要回到上级目录找annotation_templates
    logger.info(f"首先自动设置label_config（不依赖环境变量）")
    config_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'annotation_templates', 'document-ai', 'config.yml')
    if os.path.exists(config_path):
        logger.info(f"为项目 {instance.id} 设置{config_path}")
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
                if 'config' in config_data:
                    instance.label_config = config_data['config']
                    instance.save()
                    logger.info(f"为项目 {instance.id} 自动设置label_config")
        except Exception as config_e:
            logger.error(f"为项目 {instance.id} 设置label_config时发生错误: {str(config_e)}")
    else:
        logger.warning(f"配置文件不存在: {config_path}")
    
    # 检查环境变量，决定是否创建本地存储
    serving_enabled = os.environ.get('LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED', 'false').lower() == 'true'
    if not serving_enabled:
        logger.debug(f"项目 {instance.id} 创建完成，但LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED未启用，跳过自动创建本地存储")
        return
    
    document_root = os.environ.get('LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT')
    if not document_root:
        logger.warning(f"项目 {instance.id} 创建完成，但LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT未设置，跳过自动创建本地存储")
        return
    
    try:
        # 创建项目专用目录
        project_dir = os.path.join(document_root, str(instance.id))
        os.makedirs(project_dir, exist_ok=True)
        logger.info(f"为项目 {instance.id} 创建目录: {project_dir}")
        
        # 检查是否已存在同名的本地存储
        existing_storage = LocalFilesImportStorage.objects.filter(
            project=instance,
            title='create_by_code'
        ).first()
        
        if existing_storage:
            logger.info(f"项目 {instance.id} 已存在名为 'create_by_code' 的本地存储，跳过创建")
            return
        
        # 创建本地文件存储
        storage = LocalFilesImportStorage.objects.create(
            project=instance,
            title='create_by_code',
            path=project_dir,
            regex_filter='',
            use_blob_urls=False
        )
        
        logger.info(f"为项目 {instance.id} 自动创建本地文件存储: {storage.id}, 路径: {project_dir}")
        
    except Exception as e:
        logger.error(f"为项目 {instance.id} 自动创建本地存储时发生错误: {str(e)}")
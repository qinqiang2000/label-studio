import os
import logging
import yaml
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from pathlib import Path

from projects.models import Project
from io_storages.localfiles.models import LocalFilesImportStorage
from ml.models import MLBackend, MLBackendAuth

logger = logging.getLogger(__name__)

# 配置常量 - 基于project_config_template.yml
CONFIG_DEFAULTS = {
    'label_config_template': 'document-ai',
    'show_instruction': False,
    'expert_instruction': '',
    'show_collab_predictions': False,
    'ml_backend': {
        'enabled': True,
        'enabled_env_var': 'LABEL_STUDIO_ML_BACKEND_ENABLED',
        'title_env_var': 'LABEL_STUDIO_ML_BACKEND_TITLE',
        'url_env_var': 'LABEL_STUDIO_ML_BACKEND_URL',
        'auth_method_env_var': 'LABEL_STUDIO_ML_BACKEND_AUTH_METHOD',
        'title': 'test',
        'url': 'http://127.0.0.1:9090',
        'auth_method': 'NONE',
        'is_interactive': False,
        'auto_set_as_default': False
    },
    'local_storage': {
        'enabled_env_var': 'LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED',
        'document_root_env_var': 'LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT',
        'title': 'create_by_code',
        'regex_filter': '',
        'use_blob_urls': False,
        'create_project_directory': True
    }
}

def get_env_bool(env_var, default=False):
    """获取环境变量布尔值，支持调试日志"""
    value = os.environ.get(env_var, str(default)).lower()
    result = value in ('true', '1', 'yes', 'on')
    logger.debug(f"环境变量 {env_var}={os.environ.get(env_var, 'NOT_SET')} -> 解析为: {result}")
    return result

def get_env_string(env_var, default=None):
    """获取环境变量字符串值，支持调试日志"""
    value = os.environ.get(env_var, default)
    logger.debug(f"环境变量 {env_var}={value if value else 'NOT_SET'}")
    return value


@receiver(post_save, sender=Project)
def auto_create_local_storage(sender, instance, created, **kwargs):
    """
    自动为新创建的项目配置默认设置
    
    基于project_config_template.yml的配置，功能包括：
    1. 自动设置项目的label_config（总是执行）
    2. 设置项目显示配置（总是执行）
    3. 创建ML后端配置（总是执行）
    4. 当环境变量启用时创建本地文件存储（条件执行）
    """
    if not created:
        logger.debug(f"项目 {instance.id} 不是新创建的项目，跳过自动配置")
        return
    
    logger.info(f"开始为新项目 {instance.id} (名称: {instance.title}) 应用自动配置")
    
    # 1. 自动设置label_config（总是执行）
    _apply_label_config(instance)
    
    # 2. 设置项目显示配置（总是执行）
    _apply_project_display_config(instance)
    
    # 3. 创建ML后端配置（总是执行）
    _apply_ml_backend_config(instance)
    
    # 4. 条件创建本地文件存储（依赖环境变量）
    _apply_local_storage_config(instance)

def _apply_label_config(instance):
    """应用标签配置模板"""
    template_name = CONFIG_DEFAULTS['label_config_template']
    logger.debug(f"为项目 {instance.id} 应用标签配置模板: {template_name}")
    
    # BASE_DIR指向label_studio/core，需要回到上级目录找annotation_templates
    config_path = os.path.join(os.path.dirname(settings.BASE_DIR), 'annotation_templates', template_name, 'config.yml')
    logger.debug(f"标签配置文件路径: {config_path}")
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r', encoding='utf-8') as f:
                config_data = yaml.safe_load(f)
            if config_data and 'config' in config_data:
                instance.label_config = config_data['config']
                instance.save(update_fields=['label_config'])
                logger.info(f'为项目 {instance.id} 成功设置标签配置模板: {template_name}')
            else:
                logger.warning(f'标签配置文件 {config_path} 格式不正确，缺少config字段')
        except Exception as e:
            logger.error(f'读取标签配置文件 {config_path} 失败: {e}')
    else:
        logger.warning(f'标签配置文件不存在: {config_path}')

def _apply_project_display_config(instance):
    """应用项目显示配置"""
    config = CONFIG_DEFAULTS
    logger.debug(f"为项目 {instance.id} 应用显示配置")
    
    # 应用配置
    instance.show_instruction = config['show_instruction']
    instance.expert_instruction = config['expert_instruction']
    instance.show_collab_predictions = config['show_collab_predictions']
    
    instance.save(update_fields=['show_instruction', 'expert_instruction', 'show_collab_predictions'])
    
    logger.info(f'为项目 {instance.id} 成功设置显示配置: '
               f'show_instruction={config["show_instruction"]}, '
               f'expert_instruction="{config["expert_instruction"]}", '
               f'show_collab_predictions={config["show_collab_predictions"]}')

def _apply_ml_backend_config(instance):
    """应用ML后端配置"""
    ml_config = CONFIG_DEFAULTS['ml_backend']
    
    # 检查ML后端是否启用（支持环境变量覆盖）
    ml_enabled = get_env_bool(ml_config.get('enabled_env_var'), ml_config['enabled'])
    if not ml_enabled:
        logger.debug(f"项目 {instance.id} ML后端配置已禁用，跳过创建")
        return
    
    logger.debug(f"为项目 {instance.id} 创建ML后端配置")
    
    try:
        # 检查是否已存在ML后端，避免重复创建
        existing_backends = instance.ml_backends.all()
        if existing_backends.exists():
            logger.debug(f"项目 {instance.id} 已存在 {existing_backends.count()} 个ML后端，跳过创建")
            return
        
        # 从环境变量获取配置，如果没有则使用默认值
        ml_title = get_env_string(ml_config.get('title_env_var'), ml_config['title'])
        ml_url = get_env_string(ml_config.get('url_env_var'), ml_config['url'])
        ml_auth_method_str = get_env_string(ml_config.get('auth_method_env_var'), ml_config['auth_method'])
        
        # 获取认证方法
        auth_method = getattr(MLBackendAuth, ml_auth_method_str, MLBackendAuth.NONE)
        
        logger.debug(f"ML后端配置 - 标题: {ml_title}, URL: {ml_url}, 认证方法: {ml_auth_method_str}")
        
        ml_backend = MLBackend.objects.create(
            project=instance,
            title=ml_title,
            url=ml_url,
            auth_method=auth_method,
            extra_params=ml_config.get('extra_params', {}),
            is_interactive=ml_config['is_interactive']
        )
        
        logger.debug(f"ML后端创建成功，ID: {ml_backend.id}，开始更新状态")
        
        # 更新ML后端状态
        ml_backend.update_state()
        
        # 设置为默认模型版本（仅当配置允许且条件满足时）
        if (ml_config['auto_set_as_default'] and 
            instance.show_collab_predictions and 
            not instance.model_version):
            instance.model_version = ml_backend.title
            instance.save(update_fields=['model_version'])
            logger.debug(f"为项目 {instance.id} 设置默认模型版本: {ml_backend.title}")
        
        logger.info(f'为项目 {instance.id} 成功创建ML后端: {ml_backend.title} (ID: {ml_backend.id}, URL: {ml_url})')
        
    except Exception as e:
        logger.error(f'为项目 {instance.id} 创建ML后端失败: {e}', exc_info=True)

def _apply_local_storage_config(instance):
    """应用本地存储配置（条件执行）"""
    storage_config = CONFIG_DEFAULTS['local_storage']
    
    # 检查环境变量，决定是否创建本地存储
    serving_enabled = get_env_bool(storage_config['enabled_env_var'])
    if not serving_enabled:
        logger.debug(f"项目 {instance.id} 本地存储功能未启用 ({storage_config['enabled_env_var']}=false)，跳过创建")
        return
    
    document_root = get_env_string(storage_config['document_root_env_var'])
    if not document_root:
        logger.warning(f"项目 {instance.id} 本地存储根目录未设置 ({storage_config['document_root_env_var']})，跳过创建")
        return
    
    logger.debug(f"为项目 {instance.id} 创建本地存储，根目录: {document_root}")
    
    try:
        # 创建项目专用目录（如果配置启用）
        project_dir = document_root
        if storage_config['create_project_directory']:
            project_dir = os.path.join(document_root, str(instance.id))
            logger.debug(f"为项目 {instance.id} 创建专用目录: {project_dir}")
            os.makedirs(project_dir, exist_ok=True)
            logger.info(f"项目 {instance.id} 专用目录创建成功: {project_dir}")
        else:
            logger.debug(f"项目 {instance.id} 使用共享目录: {project_dir}")
        
        # 检查是否已存在同名的本地存储
        storage_title = storage_config['title']
        existing_storage = LocalFilesImportStorage.objects.filter(
            project=instance,
            title=storage_title
        ).first()
        
        if existing_storage:
            logger.info(f"项目 {instance.id} 已存在名为 '{storage_title}' 的本地存储 (ID: {existing_storage.id})，跳过创建")
            return
        
        # 创建本地文件存储
        storage = LocalFilesImportStorage.objects.create(
            project=instance,
            title=storage_title,
            path=project_dir,
            regex_filter=storage_config['regex_filter'],
            use_blob_urls=storage_config['use_blob_urls']
        )
        
        logger.info(f"为项目 {instance.id} 成功创建本地文件存储: {storage.id} (标题: {storage_title}, 路径: {project_dir})")
        
    except Exception as e:
        logger.error(f"为项目 {instance.id} 创建本地存储时发生错误: {str(e)}", exc_info=True)
"""
自动配置加载器 - 在Django启动时自动加载和同步评估字段配置

功能:
1. 从JSON配置文件加载配置
2. 自动同步到数据库
3. 检测配置变更并更新
4. 支持配置版本管理
"""

import json
import os
import logging
from pathlib import Path
from typing import Dict, List, Optional
from django.conf import settings
from django.db import transaction

logger = logging.getLogger(__name__)

class EvaluationConfigLoader:
    """评估配置自动加载器"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent / 'config'
        self.supported_formats = ['.json']
    
    def load_config_files(self) -> Dict[str, dict]:
        """加载所有配置文件"""
        configs = {}
        
        if not self.config_dir.exists():
            logger.warning(f"Config directory not found: {self.config_dir}")
            return configs
        
        for config_file in self.config_dir.glob('*.json'):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    config_data = json.load(f)
                    
                if 'key' not in config_data:
                    logger.warning(f"Config file {config_file.name} missing 'key' field")
                    continue
                    
                configs[config_data['key']] = config_data
                logger.info(f"Loaded config: {config_data['key']} from {config_file.name}")
                
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON in config file {config_file.name}: {e}")
            except Exception as e:
                logger.error(f"Error loading config file {config_file.name}: {e}")
        
        return configs
    
    def sync_to_database(self, configs: Dict[str, dict]) -> Dict[str, int]:
        """同步配置到数据库"""
        from .models import EvaluationFieldConfig
        
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        with transaction.atomic():
            for key, config_data in configs.items():
                try:
                    config, created = EvaluationFieldConfig.objects.get_or_create(
                        key=key,
                        defaults={
                            **config_data,
                            'is_system_default': True,
                            'is_active': True
                        }
                    )
                    
                    if created:
                        stats['created'] += 1
                        logger.info(f"Created new config: {config.name}")
                    else:
                        # 检查是否需要更新
                        needs_update = False
                        for field, value in config_data.items():
                            if field != 'key' and getattr(config, field, None) != value:
                                needs_update = True
                                break
                        
                        if needs_update:
                            for field, value in config_data.items():
                                if field != 'key':
                                    setattr(config, field, value)
                            config.save()
                            stats['updated'] += 1
                            logger.info(f"Updated config: {config.name}")
                
                except Exception as e:
                    stats['errors'] += 1
                    logger.error(f"Error syncing config {key}: {e}")
        
        return stats
    
    def load_and_sync(self) -> Dict[str, int]:
        """加载配置文件并同步到数据库"""
        logger.info("Starting evaluation config auto-loading...")
        
        # 加载配置文件
        configs = self.load_config_files()
        
        if not configs:
            logger.warning("No valid config files found")
            return {'created': 0, 'updated': 0, 'errors': 0}
        
        # 同步到数据库
        stats = self.sync_to_database(configs)
        
        logger.info(
            f"Config loading complete. Created: {stats['created']}, "
            f"Updated: {stats['updated']}, Errors: {stats['errors']}"
        )
        
        return stats

# 全局加载器实例
config_loader = EvaluationConfigLoader()

def auto_load_evaluation_configs():
    """自动加载评估配置的入口函数"""
    try:
        return config_loader.load_and_sync()
    except Exception as e:
        logger.error(f"Failed to auto-load evaluation configs: {e}")
        return {'created': 0, 'updated': 0, 'errors': 1}
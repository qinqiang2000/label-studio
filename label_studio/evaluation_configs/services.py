"""
评估配置管理核心服务
提供字段和文档类型管理的核心业务逻辑，可被命令行工具和Web界面复用
"""
import json
import os
import re
from pathlib import Path
from typing import Dict, List, Optional, Union
import logging

from django.conf import settings
from .models import EvaluationFieldConfig
from .config_loader import auto_load_evaluation_configs

logger = logging.getLogger(__name__)


class ConfigServiceError(Exception):
    """配置服务异常"""
    pass


class ConfigService:
    """评估配置管理核心服务"""
    
    def __init__(self):
        self.config_dir = Path(__file__).parent / 'config'
        self.frontend_config_path = Path(settings.BASE_DIR).parent / 'web' / 'apps' / 'labelstudio' / 'src' / 'components' / 'EvaluationFieldsConfig' / 'EvaluationFieldsConfig.jsx'
    
    def add_field_to_document_type(self, doc_type: str, field_config: Dict) -> str:
        """
        向指定文档类型添加字段
        
        Args:
            doc_type: 文档类型 (invoice, bank_receipt, receipt, custom)
            field_config: 字段配置
                {
                    'name': 'fieldName',
                    'label': 'Field Display Label', 
                    'type': 'string|number|date|boolean',
                    'required': True|False,
                    'validation_rules': {...} (optional)
                }
        
        Returns:
            str: 操作结果描述
        """
        try:
            # 1. 验证参数
            self._validate_field_config(field_config)
            self._validate_document_type(doc_type)
            
            field_name = field_config['name']
            
            # 2. 更新JSON配置文件
            self._update_json_config(doc_type, field_name, field_config)
            
            # 3. 更新前端兜底配置
            self._update_frontend_fallback_config(doc_type, field_name, 'add')
            
            # 4. 重新加载数据库配置
            self._reload_database_configs()
            
            # 5. 验证配置生效
            self._verify_field_added(doc_type, field_name)
            
            return f"成功添加字段 '{field_name}' 到文档类型 '{doc_type}'"
            
        except Exception as e:
            logger.error(f"添加字段失败: {e}")
            raise ConfigServiceError(f"添加字段失败: {e}")
    
    def remove_field_from_document_type(self, doc_type: str, field_name: str) -> str:
        """
        从指定文档类型删除字段
        
        Args:
            doc_type: 文档类型
            field_name: 字段名称
        
        Returns:
            str: 操作结果描述
        """
        try:
            # 1. 验证参数
            self._validate_document_type(doc_type)
            
            # 2. 检查字段是否存在
            if not self._field_exists_in_config(doc_type, field_name):
                raise ConfigServiceError(f"字段 '{field_name}' 在文档类型 '{doc_type}' 中不存在")
            
            # 3. 更新JSON配置文件
            self._remove_field_from_json_config(doc_type, field_name)
            
            # 4. 更新前端兜底配置
            self._update_frontend_fallback_config(doc_type, field_name, 'remove')
            
            # 5. 重新加载数据库配置
            self._reload_database_configs()
            
            return f"成功从文档类型 '{doc_type}' 删除字段 '{field_name}'"
            
        except Exception as e:
            logger.error(f"删除字段失败: {e}")
            raise ConfigServiceError(f"删除字段失败: {e}")
    
    def create_document_type(self, type_config: Dict) -> str:
        """
        创建新的文档类型
        
        Args:
            type_config: 文档类型配置
                {
                    'key': 'document_key',
                    'name': 'Document Name',
                    'description': 'Description',
                    'required_fields': [...],
                    'optional_fields': [...],
                    'field_labels': {...},
                    'field_types': {...}
                }
        
        Returns:
            str: 操作结果描述
        """
        try:
            # 1. 验证参数
            self._validate_document_type_config(type_config)
            
            doc_key = type_config['key']
            
            # 2. 检查文档类型是否已存在
            if self._document_type_exists(doc_key):
                raise ConfigServiceError(f"文档类型 '{doc_key}' 已存在")
            
            # 3. 创建JSON配置文件
            self._create_json_config_file(type_config)
            
            # 4. 更新前端兜底配置
            self._add_document_type_to_frontend(type_config)
            
            # 5. 重新加载数据库配置
            self._reload_database_configs()
            
            return f"成功创建文档类型 '{doc_key}' ({type_config['name']})"
            
        except Exception as e:
            logger.error(f"创建文档类型失败: {e}")
            raise ConfigServiceError(f"创建文档类型失败: {e}")
    
    def list_document_types(self) -> List[Dict]:
        """列出所有文档类型"""
        try:
            configs = EvaluationFieldConfig.objects.filter(is_active=True)
            return [
                {
                    'key': config.key,
                    'name': config.name, 
                    'description': config.description,
                    'field_count': len(config.all_fields),
                    'required_fields': config.required_fields,
                    'optional_fields': config.optional_fields
                }
                for config in configs
            ]
        except Exception as e:
            logger.error(f"列出文档类型失败: {e}")
            raise ConfigServiceError(f"列出文档类型失败: {e}")
    
    def get_document_type_info(self, doc_type: str) -> Dict:
        """获取指定文档类型的详细信息"""
        try:
            config = EvaluationFieldConfig.objects.get(key=doc_type, is_active=True)
            return {
                'key': config.key,
                'name': config.name,
                'description': config.description,
                'required_fields': config.required_fields,
                'optional_fields': config.optional_fields,
                'all_fields': config.all_fields,
                'field_labels': config.field_labels,
                'field_types': config.field_types,
                'validation_rules': config.field_validation_rules
            }
        except EvaluationFieldConfig.DoesNotExist:
            raise ConfigServiceError(f"文档类型 '{doc_type}' 不存在")
        except Exception as e:
            logger.error(f"获取文档类型信息失败: {e}")
            raise ConfigServiceError(f"获取文档类型信息失败: {e}")
    
    # 私有方法
    def _validate_field_config(self, field_config: Dict):
        """验证字段配置"""
        required_keys = ['name', 'label', 'type']
        for key in required_keys:
            if key not in field_config:
                raise ConfigServiceError(f"字段配置缺少必需的参数: {key}")
        
        # 验证字段名称格式
        field_name = field_config['name']
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_]*$', field_name):
            raise ConfigServiceError(f"字段名称格式无效: {field_name}. 必须以字母开头，只能包含字母、数字和下划线")
        
        # 验证字段类型
        valid_types = ['string', 'number', 'date', 'boolean', 'array']
        if field_config['type'] not in valid_types:
            raise ConfigServiceError(f"无效的字段类型: {field_config['type']}. 支持的类型: {valid_types}")
    
    def _validate_document_type(self, doc_type: str):
        """验证文档类型是否存在"""
        if not EvaluationFieldConfig.objects.filter(key=doc_type, is_active=True).exists():
            available_types = list(EvaluationFieldConfig.objects.filter(is_active=True).values_list('key', flat=True))
            raise ConfigServiceError(f"文档类型 '{doc_type}' 不存在. 可用类型: {available_types}")
    
    def _validate_document_type_config(self, type_config: Dict):
        """验证文档类型配置"""
        required_keys = ['key', 'name']
        for key in required_keys:
            if key not in type_config:
                raise ConfigServiceError(f"文档类型配置缺少必需的参数: {key}")
        
        # 验证文档类型key格式
        doc_key = type_config['key']
        if not re.match(r'^[a-z][a-z0-9_]*$', doc_key):
            raise ConfigServiceError(f"文档类型key格式无效: {doc_key}. 必须以小写字母开头，只能包含小写字母、数字和下划线")
    
    def _update_json_config(self, doc_type: str, field_name: str, field_config: Dict):
        """更新JSON配置文件"""
        config_file = self.config_dir / f"{doc_type}.json"
        
        if not config_file.exists():
            raise ConfigServiceError(f"配置文件不存在: {config_file}")
        
        # 读取现有配置
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 添加字段到适当的数组
        if field_config.get('required', False):
            if field_name not in config.get('required_fields', []):
                config.setdefault('required_fields', []).append(field_name)
            # 从optional_fields中移除（如果存在）
            if field_name in config.get('optional_fields', []):
                config['optional_fields'].remove(field_name)
        else:
            if field_name not in config.get('optional_fields', []):
                config.setdefault('optional_fields', []).append(field_name)
            # 从required_fields中移除（如果存在）
            if field_name in config.get('required_fields', []):
                config['required_fields'].remove(field_name)
        
        # 添加显示属性
        config.setdefault('field_display_properties', {})
        config['field_display_properties'].setdefault('labels', {})[field_name] = field_config['label']
        config['field_display_properties'].setdefault('types', {})[field_name] = field_config['type']
        
        # 添加验证规则（如果提供）
        if 'validation_rules' in field_config:
            config.setdefault('field_validation_rules', {})[field_name] = field_config['validation_rules']
        
        # 写回文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"已更新JSON配置文件: {config_file}")
    
    def _remove_field_from_json_config(self, doc_type: str, field_name: str):
        """从JSON配置文件中删除字段"""
        config_file = self.config_dir / f"{doc_type}.json"
        
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        # 从字段数组中移除
        if field_name in config.get('required_fields', []):
            config['required_fields'].remove(field_name)
        if field_name in config.get('optional_fields', []):
            config['optional_fields'].remove(field_name)
        
        # 从显示属性中移除
        if 'field_display_properties' in config:
            config['field_display_properties'].get('labels', {}).pop(field_name, None)
            config['field_display_properties'].get('types', {}).pop(field_name, None)
        
        # 从验证规则中移除
        config.get('field_validation_rules', {}).pop(field_name, None)
        
        # 写回文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"已从JSON配置文件删除字段: {config_file}")
    
    def _update_frontend_fallback_config(self, doc_type: str, field_name: str, action: str):
        """更新前端兜底配置"""
        if not self.frontend_config_path.exists():
            logger.warning(f"前端配置文件不存在: {self.frontend_config_path}")
            return
        
        # 读取前端配置文件
        with open(self.frontend_config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 查找并更新配置中的字段数组
        # 匹配模式: fields: ["field1", "field2", ...]
        pattern = rf'({doc_type}.*?fields:\s*\[)([^\]]*?)(\])'
        
        def update_fields_array(match):
            prefix = match.group(1)
            fields_str = match.group(2)
            suffix = match.group(3)
            
            # 解析现有字段
            fields = []
            for field in re.findall(r'"([^"]*)"', fields_str):
                fields.append(field)
            
            if action == 'add' and field_name not in fields:
                fields.append(field_name)
            elif action == 'remove' and field_name in fields:
                fields.remove(field_name)
            
            # 重新构建字段数组字符串
            new_fields_str = ', '.join(f'"{field}"' for field in fields)
            return f"{prefix}{new_fields_str}{suffix}"
        
        # 更新所有匹配的字段数组
        updated_content = re.sub(pattern, update_fields_array, content, flags=re.DOTALL)
        
        # 写回文件
        with open(self.frontend_config_path, 'w', encoding='utf-8') as f:
            f.write(updated_content)
        
        logger.info(f"已更新前端兜底配置: {action} {field_name} to {doc_type}")
    
    def _reload_database_configs(self):
        """重新加载数据库配置"""
        try:
            stats = auto_load_evaluation_configs()
            logger.info(f"数据库配置重新加载完成: {stats}")
        except Exception as e:
            logger.error(f"重新加载数据库配置失败: {e}")
            raise ConfigServiceError(f"重新加载数据库配置失败: {e}")
    
    def _verify_field_added(self, doc_type: str, field_name: str):
        """验证字段是否成功添加"""
        try:
            config = EvaluationFieldConfig.objects.get(key=doc_type, is_active=True)
            if field_name not in config.all_fields:
                raise ConfigServiceError(f"验证失败: 字段 '{field_name}' 未在数据库配置中找到")
        except EvaluationFieldConfig.DoesNotExist:
            raise ConfigServiceError(f"验证失败: 文档类型 '{doc_type}' 未在数据库中找到")
    
    def _field_exists_in_config(self, doc_type: str, field_name: str) -> bool:
        """检查字段是否在配置中存在"""
        try:
            config = EvaluationFieldConfig.objects.get(key=doc_type, is_active=True)
            return field_name in config.all_fields
        except EvaluationFieldConfig.DoesNotExist:
            return False
    
    def _document_type_exists(self, doc_key: str) -> bool:
        """检查文档类型是否已存在"""
        return EvaluationFieldConfig.objects.filter(key=doc_key).exists()
    
    def _create_json_config_file(self, type_config: Dict):
        """创建新的JSON配置文件"""
        config_file = self.config_dir / f"{type_config['key']}.json"
        
        if config_file.exists():
            raise ConfigServiceError(f"配置文件已存在: {config_file}")
        
        # 构建JSON配置
        json_config = {
            "name": type_config['name'],
            "key": type_config['key'],
            "description": type_config.get('description', ''),
            "required_fields": type_config.get('required_fields', []),
            "optional_fields": type_config.get('optional_fields', []),
            "field_display_properties": {
                "labels": type_config.get('field_labels', {}),
                "types": type_config.get('field_types', {})
            },
            "field_validation_rules": type_config.get('validation_rules', {}),
            "evaluation_settings": {
                "comparison_method": "field_by_field",
                "matching_strategy": {
                    "type": "field_based",
                    "primary_fields": type_config.get('primary_fields', [])
                }
            }
        }
        
        # 写入文件
        with open(config_file, 'w', encoding='utf-8') as f:
            json.dump(json_config, f, indent=2, ensure_ascii=False)
        
        logger.info(f"已创建JSON配置文件: {config_file}")
    
    def _add_document_type_to_frontend(self, type_config: Dict):
        """在前端兜底配置中添加新文档类型"""
        if not self.frontend_config_path.exists():
            logger.warning(f"前端配置文件不存在: {self.frontend_config_path}")
            return
        
        # 读取前端配置文件
        with open(self.frontend_config_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        doc_key = type_config['key']
        doc_name = type_config['name']
        fields = type_config.get('required_fields', []) + type_config.get('optional_fields', [])
        fields_str = ', '.join(f'"{field}"' for field in fields)
        
        # 构建新的文档类型配置
        new_config = f'''  {doc_key}: {{
    label: "{doc_name}",
    fields: [{fields_str}],
    description: "{type_config.get('description', '')}"
  }},'''
        
        # 在现有配置后添加新配置（查找模式并插入）
        # 这里简化处理，在实际实现中可能需要更复杂的模式匹配
        # 当前只记录日志，具体实现可能需要根据前端文件结构调整
        logger.info(f"需要在前端配置中添加文档类型: {doc_key}")
        logger.info(f"建议添加的配置: {new_config}")
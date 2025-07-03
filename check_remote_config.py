#!/usr/bin/env python3
"""
远程服务器配置诊断脚本
用于检查远程服务器上的evaluation_configs配置状态
"""

import os
import sys
import django
from pathlib import Path

# 设置Django环境
sys.path.insert(0, '/path/to/your/remote/label-studio')  # 请替换为实际的远程路径
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.label_studio')

try:
    django.setup()
    
    from evaluation_configs.models import EvaluationFieldConfig
    from evaluation_configs.config_loader import auto_load_evaluation_configs
    from evaluation_configs.frontend_api import get_preset_configurations
    import json
    
    print("=== 远程服务器配置诊断 ===\n")
    
    # 1. 检查配置文件是否存在
    print("1. 检查配置文件:")
    config_dir = Path("evaluation_configs/config")
    if config_dir.exists():
        config_files = list(config_dir.glob("*.json"))
        print(f"   配置目录存在: {config_dir.absolute()}")
        print(f"   配置文件数量: {len(config_files)}")
        for file in config_files:
            print(f"   - {file.name}")
    else:
        print(f"   ❌ 配置目录不存在: {config_dir.absolute()}")
    
    # 2. 检查数据库中的配置
    print("\n2. 检查数据库配置:")
    configs = EvaluationFieldConfig.objects.all()
    print(f"   数据库中的配置数量: {configs.count()}")
    for config in configs:
        print(f"   - {config.document_type}: {len(config.required_fields)} 个必需字段")
    
    # 3. 尝试手动加载配置
    print("\n3. 尝试手动加载配置:")
    try:
        stats = auto_load_evaluation_configs()
        print(f"   ✅ 配置加载成功: {stats}")
    except Exception as e:
        print(f"   ❌ 配置加载失败: {e}")
    
    # 4. 检查API返回
    print("\n4. 检查API返回:")
    try:
        from django.test import RequestFactory
        from evaluation_configs.frontend_api import get_preset_configurations as api_view
        
        factory = RequestFactory()
        request = factory.get('/api/frontend/evaluation-configs/presets/')
        response = api_view(request)
        
        if hasattr(response, 'data'):
            data = response.data
        else:
            import json
            data = json.loads(response.content.decode('utf-8'))
            
        print(f"   API返回的配置数量: {len(data) if isinstance(data, dict) else 0}")
        if isinstance(data, dict):
            for key in data.keys():
                print(f"   - {key}")
        else:
            print(f"   返回数据: {data}")
            
    except Exception as e:
        print(f"   ❌ API调用失败: {e}")
    
    # 5. 检查Django应用配置
    print("\n5. 检查Django应用配置:")
    from django.conf import settings
    if 'evaluation_configs' in settings.INSTALLED_APPS:
        print("   ✅ evaluation_configs应用已在INSTALLED_APPS中")
    else:
        print("   ❌ evaluation_configs应用未在INSTALLED_APPS中")
    
    print("\n=== 诊断完成 ===")
    
except Exception as e:
    print(f"❌ Django环境设置失败: {e}")
    print("请确保:")
    print("1. 在远程服务器上运行此脚本")
    print("2. 修改脚本中的路径为正确的远程路径")
    print("3. 激活正确的Python虚拟环境")
#!/usr/bin/env python3
"""
调试配置加载问题

排查步骤：
1. 检查配置文件是否存在
2. 检查配置文件内容
3. 检查Django应用加载状态
4. 检查数据库配置
"""

import os
import json
import django
from pathlib import Path

# 设置Django环境
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.label_studio')
django.setup()

from evaluation_configs.models import EvaluationFieldConfig
from evaluation_configs.config_loader import config_loader

def debug_config_loading():
    print("=== 调试配置加载问题 ===\n")
    
    # 1. 检查配置文件
    print("1. 检查配置文件...")
    config_dir = Path(__file__).parent / 'config'
    print(f"配置目录: {config_dir}")
    print(f"目录存在: {config_dir.exists()}")
    
    if config_dir.exists():
        config_files = list(config_dir.glob('*.json'))
        print(f"配置文件数量: {len(config_files)}")
        for f in config_files:
            print(f"  - {f.name}")
    
    # 2. 检查bank_receipt.json内容
    print("\n2. 检查bank_receipt.json内容...")
    bank_file = config_dir / 'bank_receipt.json'
    if bank_file.exists():
        with open(bank_file, 'r', encoding='utf-8') as f:
            bank_config = json.load(f)
        print(f"必填字段数量: {len(bank_config.get('required_fields', []))}")
        print(f"必填字段: {bank_config.get('required_fields', [])}")
    else:
        print("❌ bank_receipt.json 不存在")
    
    # 3. 检查数据库配置
    print("\n3. 检查数据库配置...")
    try:
        bank_config_db = EvaluationFieldConfig.objects.get(key='bank_receipt')
        print(f"数据库中的必填字段: {bank_config_db.required_fields}")
        print(f"数据库配置最后更新时间: {bank_config_db.updated_at}")
    except EvaluationFieldConfig.DoesNotExist:
        print("❌ 数据库中没有bank_receipt配置")
    
    # 4. 手动触发配置加载
    print("\n4. 手动触发配置加载...")
    try:
        stats = config_loader.load_and_sync()
        print(f"加载结果: {stats}")
    except Exception as e:
        print(f"❌ 加载失败: {e}")
    
    # 5. 再次检查数据库
    print("\n5. 再次检查数据库...")
    try:
        bank_config_db = EvaluationFieldConfig.objects.get(key='bank_receipt')
        print(f"更新后的必填字段: {bank_config_db.required_fields}")
        
        # 检查关键字段
        required_fields = ['tradeId', 'recieptNum', 'logNum', 'tradeDate', 'amount']
        missing = [f for f in required_fields if f not in bank_config_db.required_fields]
        if missing:
            print(f"❌ 缺失字段: {missing}")
        else:
            print("✅ 所有关键字段都存在")
            
    except Exception as e:
        print(f"❌ 检查失败: {e}")

if __name__ == "__main__":
    debug_config_loading()
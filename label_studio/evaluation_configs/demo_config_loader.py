#!/usr/bin/env python3
"""
演示新的配置加载系统

这个脚本演示了新的配置系统如何工作：
1. 从JSON文件加载配置
2. 显示银行回单配置包含的所有字段
3. 验证所需字段是否存在
"""

import json
import os
from pathlib import Path

def demo_config_loader():
    """演示配置加载器功能"""
    print("=== 演示新的评估配置加载系统 ===\n")
    
    # 配置文件目录
    config_dir = Path(__file__).parent / 'config'
    
    # 加载银行回单配置
    bank_receipt_file = config_dir / 'bank_receipt.json'
    
    if not bank_receipt_file.exists():
        print(f"❌ 配置文件不存在: {bank_receipt_file}")
        return
    
    try:
        with open(bank_receipt_file, 'r', encoding='utf-8') as f:
            bank_config = json.load(f)
        
        print("✅ 成功加载银行回单配置")
        print(f"配置名称: {bank_config['name']}")
        print(f"配置键: {bank_config['key']}")
        
        # 显示必填字段
        print(f"\n必填字段 ({len(bank_config['required_fields'])} 个):")
        for field in bank_config['required_fields']:
            print(f"  - {field}")
        
        # 显示可选字段
        print(f"\n可选字段 ({len(bank_config['optional_fields'])} 个):")
        for field in bank_config['optional_fields']:
            print(f"  - {field}")
        
        # 验证客户需求的字段
        print(f"\n=== 验证客户需求的字段 ===")
        required_fields = ['tradeId', 'recieptNum', 'logNum', 'tradeDate', 'amount', 
                          'paymentName', 'paymentBank', 'paymentAccount', 
                          'payeeName', 'payeeBank', 'payeeAccount', 'currency']
        
        missing_fields = []
        for field in required_fields:
            if field in bank_config['required_fields']:
                print(f"✅ {field} - 已包含")
            else:
                print(f"❌ {field} - 缺失")
                missing_fields.append(field)
        
        if missing_fields:
            print(f"\n❌ 缺失字段: {missing_fields}")
        else:
            print(f"\n✅ 所有需要的字段都已包含!")
        
        # 显示字段标签
        print(f"\n=== 字段标签映射 ===")
        labels = bank_config['field_display_properties']['labels']
        for field in required_fields:
            if field in labels:
                print(f"  {field}: {labels[field]}")
        
        # 显示字段类型
        print(f"\n=== 字段类型映射 ===")
        types = bank_config['field_display_properties']['types']
        for field in required_fields:
            if field in types:
                print(f"  {field}: {types[field]}")
        
    except Exception as e:
        print(f"❌ 加载配置失败: {e}")

def demo_all_configs():
    """演示所有配置文件"""
    print("\n=== 所有配置文件 ===")
    
    config_dir = Path(__file__).parent / 'config'
    
    for config_file in config_dir.glob('*.json'):
        try:
            with open(config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            print(f"\n📄 {config_file.name}")
            print(f"  名称: {config['name']}")
            print(f"  键: {config['key']}")
            print(f"  必填字段: {len(config['required_fields'])} 个")
            print(f"  可选字段: {len(config['optional_fields'])} 个")
            
        except Exception as e:
            print(f"❌ 加载 {config_file.name} 失败: {e}")

if __name__ == "__main__":
    demo_config_loader()
    demo_all_configs()
    
    print(f"\n=== 系统架构说明 ===")
    print("1. 配置文件存储在 evaluation_configs/config/ 目录")
    print("2. Django启动时自动加载配置文件到数据库")
    print("3. 修改JSON文件后重启应用即可生效")
    print("4. 支持自动检测配置变更并更新数据库")
    print("5. 不再需要手动运行 init_evaluation_configs 命令")
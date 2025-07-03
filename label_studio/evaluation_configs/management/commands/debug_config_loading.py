"""
调试配置加载问题的Django命令

使用方法:
    python manage.py debug_config_loading
"""

import json
from pathlib import Path
from django.core.management.base import BaseCommand
from evaluation_configs.models import EvaluationFieldConfig
from evaluation_configs.config_loader import config_loader


class Command(BaseCommand):
    help = 'Debug configuration loading issues'

    def handle(self, *args, **options):
        self.stdout.write('=== 调试配置加载问题 ===\n')
        
        # 1. 检查配置文件
        self.stdout.write('1. 检查配置文件...')
        config_dir = Path(__file__).parent.parent.parent / 'config'
        self.stdout.write(f'配置目录: {config_dir}')
        self.stdout.write(f'目录存在: {config_dir.exists()}')
        
        if config_dir.exists():
            config_files = list(config_dir.glob('*.json'))
            self.stdout.write(f'配置文件数量: {len(config_files)}')
            for f in config_files:
                self.stdout.write(f'  - {f.name}')
        
        # 2. 检查bank_receipt.json内容
        self.stdout.write('\n2. 检查bank_receipt.json内容...')
        bank_file = config_dir / 'bank_receipt.json'
        if bank_file.exists():
            with open(bank_file, 'r', encoding='utf-8') as f:
                bank_config = json.load(f)
            self.stdout.write(f'必填字段数量: {len(bank_config.get("required_fields", []))}')
            self.stdout.write(f'必填字段: {bank_config.get("required_fields", [])}')
        else:
            self.stdout.write(self.style.ERROR('❌ bank_receipt.json 不存在'))
        
        # 3. 检查数据库配置
        self.stdout.write('\n3. 检查数据库配置...')
        try:
            bank_config_db = EvaluationFieldConfig.objects.get(key='bank_receipt')
            self.stdout.write(f'数据库中的必填字段: {bank_config_db.required_fields}')
            self.stdout.write(f'数据库配置最后更新时间: {bank_config_db.updated_at}')
        except EvaluationFieldConfig.DoesNotExist:
            self.stdout.write(self.style.ERROR('❌ 数据库中没有bank_receipt配置'))
        
        # 4. 手动触发配置加载
        self.stdout.write('\n4. 手动触发配置加载...')
        try:
            stats = config_loader.load_and_sync()
            self.stdout.write(f'加载结果: {stats}')
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 加载失败: {e}'))
        
        # 5. 再次检查数据库
        self.stdout.write('\n5. 再次检查数据库...')
        try:
            bank_config_db = EvaluationFieldConfig.objects.get(key='bank_receipt')
            self.stdout.write(f'更新后的必填字段: {bank_config_db.required_fields}')
            
            # 检查关键字段
            required_fields = ['tradeId', 'recieptNum', 'logNum', 'tradeDate', 'amount']
            missing = [f for f in required_fields if f not in bank_config_db.required_fields]
            if missing:
                self.stdout.write(self.style.ERROR(f'❌ 缺失字段: {missing}'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ 所有关键字段都存在'))
                
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'❌ 检查失败: {e}'))
        
        # 6. 显示所有配置
        self.stdout.write('\n6. 显示所有配置...')
        configs = EvaluationFieldConfig.objects.all()
        for config in configs:
            self.stdout.write(f'- {config.key}: {config.name} (字段数: {len(config.required_fields)})')
        
        self.stdout.write('\n=== 调试完成 ===')
        self.stdout.write('\n建议检查远端服务器上的：')
        self.stdout.write('1. 配置文件是否正确部署')
        self.stdout.write('2. Django应用是否正确重启')
        self.stdout.write('3. 数据库迁移是否完成')
        self.stdout.write('4. 日志中是否有错误信息')
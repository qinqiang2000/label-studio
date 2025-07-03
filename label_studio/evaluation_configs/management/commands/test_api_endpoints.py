"""
测试前端API端点，排查配置显示问题

使用方法:
    python manage.py test_api_endpoints
"""

import json
from django.core.management.base import BaseCommand
from django.test import RequestFactory
from django.contrib.auth.models import User
from evaluation_configs.frontend_api import (
    get_available_configs, 
    get_preset_configurations,
    get_config_by_key
)


class Command(BaseCommand):
    help = 'Test frontend API endpoints for evaluation configurations'

    def handle(self, *args, **options):
        self.stdout.write('=== 测试前端API端点 ===\n')
        
        # 创建测试请求
        factory = RequestFactory()
        
        # 获取一个用户用于测试
        user = User.objects.first()
        if not user:
            self.stdout.write(self.style.ERROR('❌ 没有找到用户，无法测试API'))
            return
        
        # 1. 测试 get_available_configs (用于下拉列表)
        self.stdout.write('1. 测试 /api/frontend/evaluation-configs/active/')
        request = factory.get('/api/frontend/evaluation-configs/active/')
        request.user = user
        
        response = get_available_configs(request)
        if response.status_code == 200:
            configs = response.data
            self.stdout.write(f'✅ 返回 {len(configs)} 个配置')
            for config in configs:
                self.stdout.write(f'  - {config["key"]}: {config["name"]} (字段数: {len(config["required_fields"])})')
        else:
            self.stdout.write(self.style.ERROR(f'❌ API调用失败: {response.status_code}'))
        
        # 2. 测试 get_preset_configurations (用于字段显示)
        self.stdout.write('\n2. 测试 /api/frontend/evaluation-configs/presets/')
        request = factory.get('/api/frontend/evaluation-configs/presets/')
        request.user = user
        
        response = get_preset_configurations(request)
        if response.status_code == 200:
            presets = response.data
            self.stdout.write(f'✅ 返回 {len(presets)} 个预设配置')
            for key, config in presets.items():
                self.stdout.write(f'  - {key}: {config["name"]} (必填字段: {len(config["required_fields"])})')
                if key == 'bank_receipt':
                    self.stdout.write(f'    银行回单必填字段: {config["required_fields"]}')
        else:
            self.stdout.write(self.style.ERROR(f'❌ API调用失败: {response.status_code}'))
        
        # 3. 测试具体的 bank_receipt 配置
        self.stdout.write('\n3. 测试 /api/frontend/evaluation-configs/key/bank_receipt/')
        request = factory.get('/api/frontend/evaluation-configs/key/bank_receipt/')
        request.user = user
        
        response = get_config_by_key(request, 'bank_receipt')
        if response.status_code == 200:
            bank_config = response.data
            self.stdout.write(f'✅ 银行回单配置')
            self.stdout.write(f'  名称: {bank_config["name"]}')
            self.stdout.write(f'  必填字段: {bank_config["required_fields"]}')
            self.stdout.write(f'  可选字段: {bank_config["optional_fields"]}')
            
            # 检查关键字段
            required_fields = ['tradeId', 'recieptNum', 'logNum', 'tradeDate', 'amount']
            missing = [f for f in required_fields if f not in bank_config["required_fields"]]
            if missing:
                self.stdout.write(self.style.ERROR(f'❌ 缺失字段: {missing}'))
            else:
                self.stdout.write(self.style.SUCCESS('✅ 所有关键字段都存在'))
        else:
            self.stdout.write(self.style.ERROR(f'❌ API调用失败: {response.status_code}'))
        
        # 4. 测试发票配置作为对比
        self.stdout.write('\n4. 测试 /api/frontend/evaluation-configs/key/invoice/')
        request = factory.get('/api/frontend/evaluation-configs/key/invoice/')
        request.user = user
        
        response = get_config_by_key(request, 'invoice')
        if response.status_code == 200:
            invoice_config = response.data
            self.stdout.write(f'✅ 发票配置')
            self.stdout.write(f'  名称: {invoice_config["name"]}')
            self.stdout.write(f'  必填字段: {invoice_config["required_fields"]}')
        else:
            self.stdout.write(self.style.ERROR(f'❌ API调用失败: {response.status_code}'))
        
        self.stdout.write('\n=== 测试完成 ===')
        self.stdout.write('\n如果API返回的bank_receipt配置是正确的，')
        self.stdout.write('但前端显示的是invoice字段，那么问题在于：')
        self.stdout.write('1. 前端JavaScript缓存')
        self.stdout.write('2. 前端组件状态没有正确更新')
        self.stdout.write('3. 前端选择逻辑有问题')
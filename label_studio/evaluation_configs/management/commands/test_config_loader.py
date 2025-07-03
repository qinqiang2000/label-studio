"""
测试新的配置加载系统

使用方法:
    poetry run python manage.py test_config_loader
"""

from django.core.management.base import BaseCommand
from evaluation_configs.config_loader import auto_load_evaluation_configs
from evaluation_configs.models import EvaluationFieldConfig


class Command(BaseCommand):
    help = 'Test the new automatic config loading system'

    def handle(self, *args, **options):
        self.stdout.write('Testing automatic config loading system...')
        
        # 显示当前数据库中的配置
        self.stdout.write('\n=== Current configs in database ===')
        configs = EvaluationFieldConfig.objects.all()
        for config in configs:
            self.stdout.write(f"- {config.key}: {config.name}")
        
        # 测试自动加载
        self.stdout.write('\n=== Testing auto-load ===')
        stats = auto_load_evaluation_configs()
        
        self.stdout.write(
            self.style.SUCCESS(
                f"Auto-load completed! Created: {stats['created']}, "
                f"Updated: {stats['updated']}, Errors: {stats['errors']}"
            )
        )
        
        # 显示银行回单配置的字段
        self.stdout.write('\n=== Bank Receipt Config Fields ===')
        try:
            bank_config = EvaluationFieldConfig.objects.get(key='bank_receipt')
            self.stdout.write(f"Required fields: {bank_config.required_fields}")
            
            # 检查是否包含新增的字段
            missing_fields = []
            required_fields = ['tradeId', 'recieptNum', 'logNum', 'tradeDate', 'amount', 
                             'paymentName', 'paymentBank', 'paymentAccount', 
                             'payeeName', 'payeeBank', 'payeeAccount', 'currency']
            
            for field in required_fields:
                if field not in bank_config.required_fields:
                    missing_fields.append(field)
            
            if missing_fields:
                self.stdout.write(
                    self.style.ERROR(f"Missing fields: {missing_fields}")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS("All required fields are present!")
                )
                
        except EvaluationFieldConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR("Bank receipt config not found!")
            )
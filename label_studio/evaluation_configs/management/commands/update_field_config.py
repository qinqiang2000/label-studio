from django.core.management.base import BaseCommand
from evaluation_configs.models import EvaluationFieldConfig


class Command(BaseCommand):
    help = '更新评估字段配置'
    
    def add_arguments(self, parser):
        parser.add_argument('--doc-type', help='文档类型 (receipt, invoice, etc.)')
        parser.add_argument('--required-fields', help='必填字段，用逗号分隔')
        parser.add_argument('--optional-fields', help='可选字段，用逗号分隔')
        parser.add_argument('--list', action='store_true', help='列出所有可用的配置')
        parser.add_argument('--show', help='显示特定配置的详细信息')
    
    def handle(self, *args, **options):
        if options['list']:
            self.list_configs()
            return
            
        if options['show']:
            self.show_config(options['show'])
            return
            
        doc_type = options.get('doc_type')
        if not doc_type:
            self.stdout.write(
                self.style.ERROR('--doc-type is required when not using --list or --show')
            )
            return
        
        try:
            config = EvaluationFieldConfig.objects.get(key=doc_type)
            
            changes_made = False
            
            if options['required_fields']:
                old_required = config.required_fields.copy()
                config.required_fields = [f.strip() for f in options['required_fields'].split(',')]
                changes_made = True
                self.stdout.write(f"必填字段: {old_required} -> {config.required_fields}")
                
            if options['optional_fields']:
                old_optional = config.optional_fields.copy()
                config.optional_fields = [f.strip() for f in options['optional_fields'].split(',')]
                changes_made = True
                self.stdout.write(f"可选字段: {old_optional} -> {config.optional_fields}")
                
            if changes_made:
                config.save()
                self.stdout.write(
                    self.style.SUCCESS(f'Successfully updated {doc_type} configuration')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('No changes specified. Use --required-fields or --optional-fields')
                )
                
        except EvaluationFieldConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Configuration for {doc_type} does not exist')
            )
            self.stdout.write('Available configurations:')
            self.list_configs()
    
    def list_configs(self):
        """列出所有可用的配置"""
        configs = EvaluationFieldConfig.objects.filter(is_active=True).order_by('name')
        
        self.stdout.write('\n可用的评估配置:')
        self.stdout.write('-' * 50)
        for config in configs:
            status = '系统默认' if config.is_system_default else '自定义'
            self.stdout.write(f'{config.key:15} | {config.name:20} | {status}')
    
    def show_config(self, doc_type):
        """显示特定配置的详细信息"""
        try:
            config = EvaluationFieldConfig.objects.get(key=doc_type)
            
            self.stdout.write(f'\n配置详情: {config.name} ({config.key})')
            self.stdout.write('=' * 50)
            self.stdout.write(f'描述: {config.description}')
            self.stdout.write(f'状态: {"激活" if config.is_active else "非激活"}')
            self.stdout.write(f'类型: {"系统默认" if config.is_system_default else "自定义"}')
            self.stdout.write(f'创建时间: {config.created_at}')
            self.stdout.write(f'更新时间: {config.updated_at}')
            
            self.stdout.write('\n必填字段:')
            for field in config.required_fields:
                self.stdout.write(f'  - {field}')
                
            self.stdout.write('\n可选字段:')
            for field in config.optional_fields:
                self.stdout.write(f'  - {field}')
                
            if config.field_validation_rules:
                self.stdout.write('\n验证规则:')
                for field, rules in config.field_validation_rules.items():
                    self.stdout.write(f'  {field}: {rules}')
                    
        except EvaluationFieldConfig.DoesNotExist:
            self.stdout.write(
                self.style.ERROR(f'Configuration for {doc_type} does not exist')
            )
            self.list_configs() 
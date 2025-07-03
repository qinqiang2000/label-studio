from django.core.management.base import BaseCommand
from evaluation_configs.config_loader import auto_load_evaluation_configs
from evaluation_configs.models import EvaluationFieldConfig


class Command(BaseCommand):
    help = 'Manually reload evaluation field configurations from JSON files'

    def add_arguments(self, parser):
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force reload even if configurations already exist',
        )
        parser.add_argument(
            '--clear',
            action='store_true',
            help='Clear existing configurations before reloading',
        )

    def handle(self, *args, **options):
        self.stdout.write("=== 手动重新加载评估字段配置 ===\n")
        
        # 如果指定了清除选项，先清除现有配置
        if options['clear']:
            self.stdout.write("清除现有配置...")
            deleted_count = EvaluationFieldConfig.objects.all().delete()[0]
            self.stdout.write(f"已删除 {deleted_count} 个现有配置")
        
        # 显示加载前的状态
        before_count = EvaluationFieldConfig.objects.count()
        self.stdout.write(f"加载前数据库中的配置数量: {before_count}")
        
        try:
            # 执行配置加载
            stats = auto_load_evaluation_configs()
            
            # 显示加载结果
            after_count = EvaluationFieldConfig.objects.count()
            self.stdout.write(f"加载后数据库中的配置数量: {after_count}")
            self.stdout.write(f"加载统计: {stats}")
            
            # 显示具体配置
            self.stdout.write("\n当前数据库中的配置:")
            configs = EvaluationFieldConfig.objects.all()
            for config in configs:
                self.stdout.write(f"  - {config.document_type}: {len(config.required_fields)} 个必需字段")
                self.stdout.write(f"    必需字段: {config.required_fields}")
            
            self.stdout.write(
                self.style.SUCCESS("\n✅ 配置重新加载成功！")
            )
            
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f"\n❌ 配置加载失败: {e}")
            )
            import traceback
            self.stdout.write(traceback.format_exc())
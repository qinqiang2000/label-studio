"""
字段管理命令
用于管理评估配置中的字段（添加、删除、修改）
"""
from django.core.management.base import BaseCommand, CommandError
from evaluation_configs.services import ConfigService, ConfigServiceError


class Command(BaseCommand):
    help = '管理评估配置中的字段'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['add', 'remove', 'list', 'info'],
            help='操作类型: add(添加字段), remove(删除字段), list(列出字段), info(字段信息)'
        )
        
        parser.add_argument(
            'document_type',
            help='文档类型 (invoice, bank_receipt, receipt, custom)'
        )
        
        parser.add_argument(
            'field_name',
            nargs='?',
            help='字段名称 (add/remove/info操作时必需)'
        )
        
        # 添加字段时的选项
        parser.add_argument(
            '--label',
            help='字段显示标签 (add操作时必需)'
        )
        
        parser.add_argument(
            '--type',
            choices=['string', 'number', 'date', 'boolean', 'array'],
            default='string',
            help='字段类型 (默认: string)'
        )
        
        parser.add_argument(
            '--required',
            action='store_true',
            help='设置为必需字段'
        )
        
        parser.add_argument(
            '--optional',
            action='store_true', 
            help='设置为可选字段 (默认)'
        )
        
        parser.add_argument(
            '--validation',
            help='验证规则 (JSON格式字符串)'
        )
        
        parser.add_argument(
            '--update-frontend',
            action='store_true',
            default=True,
            help='同时更新前端兜底配置 (默认启用)'
        )

    def handle(self, *args, **options):
        try:
            service = ConfigService()
            action = options['action']
            doc_type = options['document_type']
            
            if action == 'add':
                self._handle_add_field(service, options)
            elif action == 'remove':
                self._handle_remove_field(service, options)
            elif action == 'list':
                self._handle_list_fields(service, options)
            elif action == 'info':
                self._handle_field_info(service, options)
                
        except ConfigServiceError as e:
            raise CommandError(f"❌ {e}")
        except Exception as e:
            raise CommandError(f"❌ 未知错误: {e}")

    def _handle_add_field(self, service, options):
        """处理添加字段操作"""
        doc_type = options['document_type']
        field_name = options['field_name']
        
        if not field_name:
            raise CommandError("添加字段时必须指定字段名称")
        
        if not options['label']:
            raise CommandError("添加字段时必须指定 --label 参数")
        
        # 检查required和optional冲突
        if options['required'] and options['optional']:
            raise CommandError("--required 和 --optional 不能同时指定")
        
        # 构建字段配置
        field_config = {
            'name': field_name,
            'label': options['label'],
            'type': options['type'],
            'required': options['required'] or not options['optional']  # 默认为必需字段
        }
        
        # 添加验证规则（如果提供）
        if options['validation']:
            import json
            try:
                field_config['validation_rules'] = json.loads(options['validation'])
            except json.JSONDecodeError:
                raise CommandError("验证规则必须是有效的JSON格式")
        
        # 执行添加操作
        result = service.add_field_to_document_type(doc_type, field_config)
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ {result}")
        )
        
        # 显示操作详情
        self._show_operation_details('添加', doc_type, field_name, field_config)

    def _handle_remove_field(self, service, options):
        """处理删除字段操作"""
        doc_type = options['document_type']
        field_name = options['field_name']
        
        if not field_name:
            raise CommandError("删除字段时必须指定字段名称")
        
        # 确认删除操作
        self.stdout.write(
            self.style.WARNING(f"⚠️  即将删除字段 '{field_name}' 从文档类型 '{doc_type}'")
        )
        
        if not self._confirm_deletion():
            self.stdout.write("❌ 操作已取消")
            return
        
        # 执行删除操作
        result = service.remove_field_from_document_type(doc_type, field_name)
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ {result}")
        )

    def _handle_list_fields(self, service, options):
        """处理列出字段操作"""
        doc_type = options['document_type']
        
        try:
            doc_info = service.get_document_type_info(doc_type)
            
            self.stdout.write(
                self.style.SUCCESS(f"\n📋 文档类型: {doc_info['name']} ({doc_info['key']})")
            )
            
            if doc_info['description']:
                self.stdout.write(f"📝 描述: {doc_info['description']}")
            
            self.stdout.write(f"\n🔸 必需字段 ({len(doc_info['required_fields'])} 个):")
            for field in doc_info['required_fields']:
                label = doc_info['field_labels'].get(field, field)
                field_type = doc_info['field_types'].get(field, 'unknown')
                self.stdout.write(f"  • {field} ({field_type}) - {label}")
            
            self.stdout.write(f"\n🔹 可选字段 ({len(doc_info['optional_fields'])} 个):")
            for field in doc_info['optional_fields']:
                label = doc_info['field_labels'].get(field, field)
                field_type = doc_info['field_types'].get(field, 'unknown')
                self.stdout.write(f"  • {field} ({field_type}) - {label}")
            
            self.stdout.write(f"\n📊 总计: {len(doc_info['all_fields'])} 个字段")
            
        except ConfigServiceError as e:
            raise CommandError(f"❌ {e}")

    def _handle_field_info(self, service, options):
        """处理字段信息查询"""
        doc_type = options['document_type']
        field_name = options['field_name']
        
        if not field_name:
            raise CommandError("查询字段信息时必须指定字段名称")
        
        try:
            doc_info = service.get_document_type_info(doc_type)
            
            if field_name not in doc_info['all_fields']:
                raise CommandError(f"字段 '{field_name}' 在文档类型 '{doc_type}' 中不存在")
            
            # 显示字段详细信息
            label = doc_info['field_labels'].get(field_name, field_name)
            field_type = doc_info['field_types'].get(field_name, 'unknown')
            is_required = field_name in doc_info['required_fields']
            validation_rules = doc_info['validation_rules'].get(field_name, {})
            
            self.stdout.write(
                self.style.SUCCESS(f"\n🔍 字段信息: {field_name}")
            )
            self.stdout.write(f"📝 显示标签: {label}")
            self.stdout.write(f"🏷️  字段类型: {field_type}")
            self.stdout.write(f"📌 是否必需: {'是' if is_required else '否'}")
            
            if validation_rules:
                self.stdout.write(f"✅ 验证规则: {validation_rules}")
            else:
                self.stdout.write("✅ 验证规则: 无")
                
        except ConfigServiceError as e:
            raise CommandError(f"❌ {e}")

    def _confirm_deletion(self) -> bool:
        """确认删除操作"""
        try:
            response = input("确认删除? (yes/no): ").lower().strip()
            return response in ['yes', 'y', '是']
        except (EOFError, KeyboardInterrupt):
            return False

    def _show_operation_details(self, operation, doc_type, field_name, field_config):
        """显示操作详情"""
        self.stdout.write(f"\n📋 操作详情:")
        self.stdout.write(f"  🔧 操作类型: {operation}")
        self.stdout.write(f"  📄 文档类型: {doc_type}")
        self.stdout.write(f"  🏷️  字段名称: {field_name}")
        self.stdout.write(f"  📝 显示标签: {field_config['label']}")
        self.stdout.write(f"  🏷️  字段类型: {field_config['type']}")
        self.stdout.write(f"  📌 是否必需: {'是' if field_config['required'] else '否'}")
        
        if 'validation_rules' in field_config:
            self.stdout.write(f"  ✅ 验证规则: {field_config['validation_rules']}")
        
        self.stdout.write(f"\n🔄 已更新的文件:")
        self.stdout.write(f"  • JSON配置: evaluation_configs/config/{doc_type}.json")
        self.stdout.write(f"  • 前端配置: EvaluationFieldsConfig.jsx")
        self.stdout.write(f"  • 数据库配置: 已重新加载")
        
        self.stdout.write(f"\n🎯 使用建议:")
        self.stdout.write(f"  • 运行测试: poetry run python manage.py test evaluation_configs")
        self.stdout.write(f"  • 验证API: curl -H 'Authorization: Token YOUR_TOKEN' \\")
        self.stdout.write(f"           'http://127.0.0.1:8080/api/frontend/evaluation-configs/presets/'")
        self.stdout.write(f"  • 检查前端: 刷新项目设置页面查看新字段")
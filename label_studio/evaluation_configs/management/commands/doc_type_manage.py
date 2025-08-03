"""
文档类型管理命令
用于管理评估配置中的文档类型（创建、删除、列出、查看）
"""
from django.core.management.base import BaseCommand, CommandError
from evaluation_configs.services import ConfigService, ConfigServiceError
import json


class Command(BaseCommand):
    help = '管理评估配置中的文档类型'

    def add_arguments(self, parser):
        parser.add_argument(
            'action',
            choices=['create', 'delete', 'list', 'info'],
            help='操作类型: create(创建), delete(删除), list(列出所有), info(查看详情)'
        )
        
        parser.add_argument(
            'document_key',
            nargs='?',
            help='文档类型key (create/delete/info操作时必需)'
        )
        
        # 创建文档类型时的选项
        parser.add_argument(
            '--name',
            help='文档类型显示名称 (create操作时必需)'
        )
        
        parser.add_argument(
            '--description',
            default='',
            help='文档类型描述'
        )
        
        parser.add_argument(
            '--required',
            help='必需字段列表 (逗号分隔)'
        )
        
        parser.add_argument(
            '--optional',
            help='可选字段列表 (逗号分隔)'
        )
        
        parser.add_argument(
            '--labels',
            help='字段标签映射 (格式: field1:Label1,field2:Label2)'
        )
        
        parser.add_argument(
            '--types',
            help='字段类型映射 (格式: field1:string,field2:number)'
        )
        
        parser.add_argument(
            '--primary-fields',
            help='主要字段列表，用于匹配策略 (逗号分隔)'
        )
        
        parser.add_argument(
            '--template',
            choices=['basic', 'invoice', 'receipt', 'contract'],
            help='使用预定义模板快速创建'
        )
        
        parser.add_argument(
            '--config-file',
            help='从YAML/JSON配置文件导入 (暂未实现)'
        )

    def handle(self, *args, **options):
        try:
            service = ConfigService()
            action = options['action']
            
            if action == 'create':
                self._handle_create_document_type(service, options)
            elif action == 'delete':
                self._handle_delete_document_type(service, options)
            elif action == 'list':
                self._handle_list_document_types(service, options)
            elif action == 'info':
                self._handle_document_type_info(service, options)
                
        except ConfigServiceError as e:
            raise CommandError(f"❌ {e}")
        except Exception as e:
            raise CommandError(f"❌ 未知错误: {e}")

    def _handle_create_document_type(self, service, options):
        """处理创建文档类型操作"""
        doc_key = options['document_key']
        
        if not doc_key:
            raise CommandError("创建文档类型时必须指定document_key")
        
        if not options['name']:
            raise CommandError("创建文档类型时必须指定 --name 参数")
        
        # 使用模板
        if options['template']:
            type_config = self._get_template_config(options['template'], doc_key, options['name'])
        else:
            # 手动配置
            type_config = self._build_type_config_from_options(options)
        
        # 显示即将创建的配置
        self._show_create_preview(type_config)
        
        if not self._confirm_creation():
            self.stdout.write("❌ 操作已取消")
            return
        
        # 执行创建操作
        result = service.create_document_type(type_config)
        
        self.stdout.write(
            self.style.SUCCESS(f"✅ {result}")
        )
        
        # 显示操作详情和后续建议
        self._show_creation_details(type_config)

    def _handle_delete_document_type(self, service, options):
        """处理删除文档类型操作"""
        doc_key = options['document_key']
        
        if not doc_key:
            raise CommandError("删除文档类型时必须指定document_key")
        
        # 显示要删除的文档类型信息
        try:
            doc_info = service.get_document_type_info(doc_key)
            self.stdout.write(
                self.style.WARNING(f"⚠️  即将删除文档类型:")
            )
            self.stdout.write(f"  📄 名称: {doc_info['name']}")
            self.stdout.write(f"  🔑 Key: {doc_info['key']}")
            self.stdout.write(f"  📊 字段数: {len(doc_info['all_fields'])}")
            
        except ConfigServiceError:
            self.stdout.write(
                self.style.WARNING(f"⚠️  即将删除文档类型: {doc_key}")
            )
        
        if not self._confirm_deletion():
            self.stdout.write("❌ 操作已取消")
            return
        
        # 注意：当前ConfigService没有实现删除功能，这里给出提示
        self.stdout.write(
            self.style.ERROR("❌ 删除功能暂未实现")
        )
        self.stdout.write("💡 如需删除文档类型，请手动:")
        self.stdout.write(f"  1. 删除文件: evaluation_configs/config/{doc_key}.json")
        self.stdout.write(f"  2. 从前端配置中移除相关代码")
        self.stdout.write(f"  3. 运行: poetry run python manage.py reload_configs --force")

    def _handle_list_document_types(self, service, options):
        """处理列出文档类型操作"""
        doc_types = service.list_document_types()
        
        if not doc_types:
            self.stdout.write("📝 当前没有配置的文档类型")
            return
        
        self.stdout.write(
            self.style.SUCCESS(f"\n📋 当前文档类型列表 ({len(doc_types)} 个):")
        )
        
        # 表格头
        self.stdout.write(f"{'Key':<15} {'Name':<20} {'Fields':<8} {'Description'}")
        self.stdout.write("-" * 70)
        
        # 表格内容
        for doc_type in doc_types:
            key = doc_type['key'][:14]
            name = doc_type['name'][:19]
            field_count = str(doc_type['field_count'])
            description = doc_type['description'][:30] + ('...' if len(doc_type['description']) > 30 else '')
            
            self.stdout.write(f"{key:<15} {name:<20} {field_count:<8} {description}")
        
        # 使用建议
        self.stdout.write(f"\n💡 使用建议:")
        self.stdout.write(f"  • 查看详情: poetry run python manage.py doc_type_manage info <document_key>")
        self.stdout.write(f"  • 管理字段: poetry run python manage.py field_manage list <document_key>")

    def _handle_document_type_info(self, service, options):
        """处理查看文档类型详情"""
        doc_key = options['document_key']
        
        if not doc_key:
            raise CommandError("查看文档类型详情时必须指定document_key")
        
        doc_info = service.get_document_type_info(doc_key)
        
        # 显示基本信息
        self.stdout.write(
            self.style.SUCCESS(f"\n📄 文档类型详情: {doc_info['name']}")
        )
        self.stdout.write(f"🔑 Key: {doc_info['key']}")
        
        if doc_info['description']:
            self.stdout.write(f"📝 描述: {doc_info['description']}")
        
        # 显示字段信息
        self.stdout.write(f"\n🔸 必需字段 ({len(doc_info['required_fields'])} 个):")
        for field in doc_info['required_fields']:
            label = doc_info['field_labels'].get(field, field)
            field_type = doc_info['field_types'].get(field, 'unknown')
            self.stdout.write(f"  • {field:<20} ({field_type:<8}) - {label}")
        
        self.stdout.write(f"\n🔹 可选字段 ({len(doc_info['optional_fields'])} 个):")
        for field in doc_info['optional_fields']:
            label = doc_info['field_labels'].get(field, field)
            field_type = doc_info['field_types'].get(field, 'unknown')
            self.stdout.write(f"  • {field:<20} ({field_type:<8}) - {label}")
        
        # 显示验证规则
        if doc_info['validation_rules']:
            self.stdout.write(f"\n✅ 字段验证规则:")
            for field, rules in doc_info['validation_rules'].items():
                self.stdout.write(f"  • {field}: {rules}")
        
        # 统计信息
        self.stdout.write(f"\n📊 统计信息:")
        self.stdout.write(f"  • 总字段数: {len(doc_info['all_fields'])}")
        self.stdout.write(f"  • 必需字段: {len(doc_info['required_fields'])}")
        self.stdout.write(f"  • 可选字段: {len(doc_info['optional_fields'])}")

    def _get_template_config(self, template, doc_key, doc_name):
        """获取预定义模板配置"""
        templates = {
            'basic': {
                'key': doc_key,
                'name': doc_name,
                'description': '基础文档类型',
                'required_fields': ['docType'],
                'optional_fields': [],
                'field_labels': {'docType': 'Document Type'},
                'field_types': {'docType': 'string'},
                'primary_fields': []
            },
            'invoice': {
                'key': doc_key,
                'name': doc_name, 
                'description': '发票类型文档',
                'required_fields': ['docType', 'invoiceDate', 'totalAmount', 'currency'],
                'optional_fields': ['invoiceNumber', 'billToName', 'billFromName'],
                'field_labels': {
                    'docType': 'Document Type',
                    'invoiceDate': 'Invoice Date',
                    'totalAmount': 'Total Amount',
                    'currency': 'Currency',
                    'invoiceNumber': 'Invoice Number',
                    'billToName': 'Bill To Name',
                    'billFromName': 'Bill From Name'
                },
                'field_types': {
                    'docType': 'string',
                    'invoiceDate': 'date',
                    'totalAmount': 'number',
                    'currency': 'string',
                    'invoiceNumber': 'string',
                    'billToName': 'string',
                    'billFromName': 'string'
                },
                'primary_fields': ['invoiceNumber', 'invoiceDate', 'totalAmount']
            },
            'receipt': {
                'key': doc_key,
                'name': doc_name,
                'description': '收据类型文档',
                'required_fields': ['docType', 'totalAmount', 'receiptDate'],
                'optional_fields': ['receiptNumber', 'storeName', 'items'],
                'field_labels': {
                    'docType': 'Document Type',
                    'totalAmount': 'Total Amount', 
                    'receiptDate': 'Receipt Date',
                    'receiptNumber': 'Receipt Number',
                    'storeName': 'Store Name',
                    'items': 'Items'
                },
                'field_types': {
                    'docType': 'string',
                    'totalAmount': 'number',
                    'receiptDate': 'date',
                    'receiptNumber': 'string',
                    'storeName': 'string',
                    'items': 'array'
                },
                'primary_fields': ['receiptNumber', 'receiptDate']
            },
            'contract': {
                'key': doc_key,
                'name': doc_name,
                'description': '合同类型文档',
                'required_fields': ['docType', 'contractNumber', 'contractDate', 'partyA', 'partyB'],
                'optional_fields': ['contractAmount', 'signDate', 'effectiveDate'],
                'field_labels': {
                    'docType': 'Document Type',
                    'contractNumber': 'Contract Number',
                    'contractDate': 'Contract Date',
                    'partyA': 'Party A',
                    'partyB': 'Party B',
                    'contractAmount': 'Contract Amount',
                    'signDate': 'Sign Date',
                    'effectiveDate': 'Effective Date'
                },
                'field_types': {
                    'docType': 'string',
                    'contractNumber': 'string',
                    'contractDate': 'date',
                    'partyA': 'string',
                    'partyB': 'string',
                    'contractAmount': 'number',
                    'signDate': 'date',
                    'effectiveDate': 'date'
                },
                'primary_fields': ['contractNumber', 'contractDate']
            }
        }
        
        if template not in templates:
            raise CommandError(f"未知模板: {template}")
        
        return templates[template]

    def _build_type_config_from_options(self, options):
        """从命令行选项构建文档类型配置"""
        doc_key = options['document_key']
        
        type_config = {
            'key': doc_key,
            'name': options['name'],
            'description': options['description'],
            'required_fields': [],
            'optional_fields': [],
            'field_labels': {},
            'field_types': {},
            'primary_fields': []
        }
        
        # 解析字段列表
        if options['required']:
            type_config['required_fields'] = [f.strip() for f in options['required'].split(',')]
        
        if options['optional']:
            type_config['optional_fields'] = [f.strip() for f in options['optional'].split(',')]
        
        # 解析字段标签
        if options['labels']:
            for mapping in options['labels'].split(','):
                if ':' in mapping:
                    field, label = mapping.split(':', 1)
                    type_config['field_labels'][field.strip()] = label.strip()
        
        # 解析字段类型
        if options['types']:
            for mapping in options['types'].split(','):
                if ':' in mapping:
                    field, field_type = mapping.split(':', 1)
                    type_config['field_types'][field.strip()] = field_type.strip()
        
        # 解析主要字段
        if options['primary_fields']:
            type_config['primary_fields'] = [f.strip() for f in options['primary_fields'].split(',')]
        
        # 设置默认字段类型和标签
        all_fields = type_config['required_fields'] + type_config['optional_fields']
        for field in all_fields:
            if field not in type_config['field_labels']:
                type_config['field_labels'][field] = field.replace('_', ' ').title()
            if field not in type_config['field_types']:
                type_config['field_types'][field] = 'string'
        
        return type_config

    def _show_create_preview(self, type_config):
        """显示创建预览"""
        self.stdout.write(
            self.style.WARNING(f"\n📋 即将创建文档类型:")
        )
        self.stdout.write(f"  🔑 Key: {type_config['key']}")
        self.stdout.write(f"  📄 名称: {type_config['name']}")
        self.stdout.write(f"  📝 描述: {type_config['description']}")
        
        if type_config['required_fields']:
            self.stdout.write(f"  🔸 必需字段: {', '.join(type_config['required_fields'])}")
        
        if type_config['optional_fields']:
            self.stdout.write(f"  🔹 可选字段: {', '.join(type_config['optional_fields'])}")
        
        if type_config['primary_fields']:
            self.stdout.write(f"  📌 主要字段: {', '.join(type_config['primary_fields'])}")

    def _show_creation_details(self, type_config):
        """显示创建操作详情"""
        self.stdout.write(f"\n📋 创建详情:")
        self.stdout.write(f"  📄 文档类型: {type_config['name']} ({type_config['key']})")
        self.stdout.write(f"  📊 字段总数: {len(type_config['required_fields']) + len(type_config['optional_fields'])}")
        
        self.stdout.write(f"\n🔄 已创建的文件:")
        self.stdout.write(f"  • JSON配置: evaluation_configs/config/{type_config['key']}.json")
        self.stdout.write(f"  • 数据库配置: 已加载")
        
        self.stdout.write(f"\n📝 手动更新项目 (需要手动操作):")
        self.stdout.write(f"  • 前端配置: 在 EvaluationFieldsConfig.jsx 中添加新文档类型")
        self.stdout.write(f"  • UI选项: 在相关下拉框中添加新类型选项")
        
        self.stdout.write(f"\n🎯 后续操作建议:")
        self.stdout.write(f"  • 查看创建结果: poetry run python manage.py doc_type_manage info {type_config['key']}")
        self.stdout.write(f"  • 管理字段: poetry run python manage.py field_manage list {type_config['key']}")
        self.stdout.write(f"  • 添加字段: poetry run python manage.py field_manage add {type_config['key']} new_field --label='新字段'")

    def _confirm_creation(self) -> bool:
        """确认创建操作"""
        try:
            response = input("确认创建? (yes/no): ").lower().strip()
            return response in ['yes', 'y', '是']
        except (EOFError, KeyboardInterrupt):
            return False

    def _confirm_deletion(self) -> bool:
        """确认删除操作"""
        try:
            response = input("确认删除? 此操作不可逆! (yes/no): ").lower().strip()
            return response in ['yes', 'y', '是']
        except (EOFError, KeyboardInterrupt):
            return False
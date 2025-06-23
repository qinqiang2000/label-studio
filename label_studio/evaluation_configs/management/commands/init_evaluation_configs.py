"""
初始化评估字段配置的命令

使用方法:
    poetry run python manage.py init_evaluation_configs

功能:
    1. 创建默认的评估字段配置预设
    2. 支持发票、银行回单、收据、自定义等文档类型
    3. 为每种文档类型定义必填字段、可选字段、字段显示属性和验证规则
    4. 配置评估设置，包括比较方法和匹配策略

预设配置包括:
    - invoice: 发票类型，包含发票号、日期、金额等字段
    - bank_receipt: 银行回单类型，包含回单号、交易日期、金额等字段  
    - receipt: 收据类型，包含日期、总金额等字段
    - custom: 自定义类型，支持用户自定义字段

注意事项:
    - 运行前确保数据库已迁移
    - 重复运行会更新现有配置
    - 配置变更会影响前端的评估字段选择
"""


from django.core.management.base import BaseCommand
from evaluation_configs.models import EvaluationFieldConfig


class Command(BaseCommand):
    help = 'Initialize default evaluation field configurations'

    def handle(self, *args, **options):
        self.stdout.write('Initializing default evaluation field configurations...')
        
        # Define default configurations
        default_configs = [
            {
                'name': 'Invoice',
                'key': 'invoice',
                'description': '',
                'required_fields': [
                    'docType',  'invoiceDate', 'totalAmount', 'currency','billToName', 'totalTaxAmount'
                ],
                'optional_fields': [
                    'invoiceNumber', 'buyerName', 
                    'sellerName', 'taxRate', 'subtotal', 'description'
                ],
                'field_display_properties': {
                    'labels': {
                        'docType': 'Document Type',
                        'totalAmount': 'Total Amount',
                        'invoiceDate': 'Invoice Date',
                        'currency': 'Currency',
                        'billToName': 'Bill To Name',
                        'totalTaxAmount': 'Total Tax Amount',
                        'invoiceNumber': 'Invoice Number',
                        'buyerName': 'Buyer Name',
                        'sellerName': 'Seller Name',
                        'taxRate': 'Tax Rate',
                        'subtotal': 'Subtotal',
                        'description': 'Description',
                        '序号': 'Serial Number'
                    },
                    'types': {
                        'docType': 'string',
                        'totalAmount': 'number',
                        'invoiceDate': 'date',
                        'currency': 'string',
                        'billToName': 'string',
                        'totalTaxAmount': 'number',
                        'invoiceNumber': 'string',
                        'buyerName': 'string',
                        'sellerName': 'string',
                        'taxRate': 'number',
                        'subtotal': 'number',
                        'description': 'string',
                        '序号': 'number'
                    }
                },
                'field_validation_rules': {
                    'docType': {
                        'required': True,
                        'allowed_values': ['invoice', 'receipt']
                    },
                    'totalAmount': {
                        'required': True,
                        'type': 'number',
                        'min_value': 0
                    },
                    'currency': {
                        'required': True,
                        'type': 'string'
                    }
                },
                'evaluation_settings': {
                    'comparison_method': 'field_by_field',
                    'tolerance': {
                        'totalAmount': 0.01,
                        'totalTaxAmount': 0.01
                    },
                    'matching_strategy': {
                        'type': 'degraded_field_based',
                        'mode': 'field_based',
                        'primary_fields': ['invoiceNumber', 'invoiceDate', 'totalAmount'],  # 发票预设主键
                        'verbose': True
                    }
                }
            },
            {
                'name': 'Bank Receipt',
                'key': 'bank_receipt',
                'description': '',
                'required_fields': [
                     'recieptNum', 'tradeDate', 'amount', 
                    'paymentName', 'paymentBank', 'paymentAccount',
                    'payeeName', 'payeeBank', 'payeeAccount', 'currency'
                ],
                'optional_fields': [
                    'tradePurpose', 'feeAmount', 'balance', '序号'
                ],
                'field_display_properties': {
                    'labels': {
                        'docType': 'Document Type',
                        'recieptNum': 'Receipt Number',
                        'tradeDate': 'Trade Date',
                        'amount': 'Amount',
                        'paymentName': 'Payment Name',
                        'paymentBank': 'Payment Bank',
                        'paymentAccount': 'Payment Account',
                        'payeeName': 'Payee Name',
                        'payeeBank': 'Payee Bank',
                        'payeeAccount': 'Payee Account',
                        'currency': 'Currency',
                        'tradePurpose': 'Trade Purpose',
                        'feeAmount': 'Fee Amount',
                        'balance': 'Balance',
                        '序号': 'Serial Number'
                    },
                    'types': {
                        'docType': 'string',
                        'recieptNum': 'string',
                        'tradeDate': 'date',
                        'amount': 'number',
                        'paymentName': 'string',
                        'paymentBank': 'string',
                        'paymentAccount': 'string',
                        'payeeName': 'string',
                        'payeeBank': 'string',
                        'payeeAccount': 'string',
                        'currency': 'string',
                        'tradePurpose': 'string',
                        'feeAmount': 'number',
                        'balance': 'number',
                        '序号': 'number'
                    }
                },
                'field_validation_rules': {
                    'docType': {
                        'required': True,
                        'allowed_values': ['bank_receipt']
                    },
                    'amount': {
                        'required': True,
                        'type': 'number',
                        'min_value': 0
                    },
                    'currency': {
                        'required': True,
                        'type': 'string'
                    }
                },
                'evaluation_settings': {
                    'comparison_method': 'field_by_field',
                    'tolerance': {
                        'amount': 0.01,
                        'feeAmount': 0.01,
                        'balance': 0.01
                    },
                    'matching_strategy': {
                        'type': 'degraded_field_based',
                        'mode': 'field_based', 
                        'primary_fields': ['recieptNum', 'amount'],  # 银行回单预设主键：回单号+金额
                        'verbose': True
                    }
                }
            },
            {
                'name': 'Receipt',
                'key': 'receipt',
                'description': '',
                'required_fields': [
                    'docType', 'totalAmount', 'invoiceDate', 'currency'
                ],
                'optional_fields': [
                    'receiptNumber', 'storeName', 'storeAddress', 
                    'items', 'paymentMethod', '序号'
                ],
                'field_display_properties': {
                    'labels': {
                        'docType': 'Document Type',
                        'totalAmount': 'Total Amount',
                        'invoiceDate': 'Date',
                        'currency': 'Currency',
                        'receiptNumber': 'Receipt Number',
                        'storeName': 'Store Name',
                        'storeAddress': 'Store Address',
                        'items': 'Items',
                        'paymentMethod': 'Payment Method',
                        '序号': 'Serial Number'
                    },
                    'types': {
                        'docType': 'string',
                        'totalAmount': 'number',
                        'invoiceDate': 'date',
                        'currency': 'string',
                        'receiptNumber': 'string',
                        'storeName': 'string',
                        'storeAddress': 'string',
                        'items': 'array',
                        'paymentMethod': 'string',
                        '序号': 'number'
                    }
                },
                'field_validation_rules': {
                    'docType': {
                        'required': True,
                        'allowed_values': ['receipt']
                    },
                    'totalAmount': {
                        'required': True,
                        'type': 'number',
                        'min_value': 0
                    },
                    'currency': {
                        'required': True,
                        'type': 'string'
                    }
                },
                'evaluation_settings': {
                    'comparison_method': 'field_by_field',
                    'tolerance': {
                        'totalAmount': 0.01
                    },
                    'matching_strategy': {
                        'type': 'degraded_field_based',
                        'mode': 'field_based',
                        'primary_fields': ['invoiceDate', 'totalAmount'],  # 收据预设主键
                        'verbose': True
                    }
                }
            },
            {
                'name': 'Custom',
                'key': 'custom',
                'description': 'Custom document type with user-defined fields and matching strategy',
                'required_fields': [
                    'docType'
                ],
                'optional_fields': [
                    'amount', 'totalAmount', 'invoiceDate', 'tradeDate', 
                    'recieptNum', 'invoiceNumber', 'logNum', 'billToName',
                    'currency', '序号'
                ],
                'field_display_properties': {
                    'labels': {
                        'docType': 'Document Type',
                        'amount': 'Amount',
                        'totalAmount': 'Total Amount',
                        'invoiceDate': 'Invoice Date',
                        'tradeDate': 'Trade Date',
                        'recieptNum': 'Receipt Number',
                        'invoiceNumber': 'Invoice Number',
                        'logNum': 'Log Number',
                        'billToName': 'Bill To Name',
                        'currency': 'Currency',
                        '序号': 'Serial Number'
                    },
                    'types': {
                        'docType': 'string',
                        'amount': 'number',
                        'totalAmount': 'number',
                        'invoiceDate': 'date',
                        'tradeDate': 'date',
                        'recieptNum': 'string',
                        'invoiceNumber': 'string',
                        'logNum': 'string',
                        'billToName': 'string',
                        'currency': 'string',
                        '序号': 'number'
                    }
                },
                'field_validation_rules': {
                    'docType': {
                        'required': True
                    },
                    'amount': {
                        'type': 'number',
                        'min_value': 0
                    },
                    'totalAmount': {
                        'type': 'number',
                        'min_value': 0
                    }
                },
                'evaluation_settings': {
                    'comparison_method': 'field_by_field',
                    'tolerance': {
                        'amount': 0.01,
                        'totalAmount': 0.01
                    },
                    'matching_strategy': {
                        'type': 'degraded_field_based',
                        'mode': 'field_based',
                        'primary_fields': [],  # 自定义类型默认空配置，将使用位置匹配
                        'verbose': True
                    }
                }
            }
        ]
        
        created_count = 0
        updated_count = 0
        
        for config_data in default_configs:
            config, created = EvaluationFieldConfig.objects.get_or_create(
                key=config_data['key'],
                defaults={
                    **config_data,
                    'is_system_default': True,
                    'is_active': True
                }
            )
            
            if created:
                created_count += 1
                self.stdout.write(
                    self.style.SUCCESS(f'Created configuration: {config.name}')
                )
            else:
                # Update existing configuration
                for field, value in config_data.items():
                    if field != 'key':  # Don't update the key
                        setattr(config, field, value)
                config.save()
                updated_count += 1
                self.stdout.write(
                    self.style.WARNING(f'Updated configuration: {config.name}')
                )
        
        self.stdout.write(
            self.style.SUCCESS(
                f'Initialization complete! Created: {created_count}, Updated: {updated_count}'
            )
        ) 
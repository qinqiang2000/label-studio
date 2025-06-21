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
                    'docType', 'totalAmount', 'invoiceDate', 'currency', 
                    'billToName', 'totalTaxAmount'
                ],
                'optional_fields': [
                    'invoiceNumber', 'buyerName', 'sellerName', 'taxRate',
                    'subtotal', 'description', '序号'
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
                        'allowed_values': ['CNY', 'USD', 'EUR', 'GBP']
                    }
                },
                'evaluation_settings': {
                    'comparison_method': 'field_by_field',
                    'tolerance': {
                        'totalAmount': 0.01,
                        'totalTaxAmount': 0.01
                    }
                }
            },
            {
                'name': 'Bank Receipt',
                'key': 'bank_receipt',
                'description': '',
                'required_fields': [
                    'docType', 'recieptNum', 'tradeDate', 'amount', 
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
                        'allowed_values': ['CNY', 'USD', 'EUR', 'GBP']
                    }
                },
                'evaluation_settings': {
                    'comparison_method': 'field_by_field',
                    'tolerance': {
                        'amount': 0.01,
                        'feeAmount': 0.01,
                        'balance': 0.01
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
                        'allowed_values': ['CNY', 'USD', 'EUR', 'GBP']
                    }
                },
                'evaluation_settings': {
                    'comparison_method': 'field_by_field',
                    'tolerance': {
                        'totalAmount': 0.01
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
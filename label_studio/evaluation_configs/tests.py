from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from organizations.models import Organization
from projects.models import Project
from .models import EvaluationFieldConfig, ProjectEvaluationConfig
import json

User = get_user_model()


class EvaluationFieldConfigModelTest(TestCase):
    """Test EvaluationFieldConfig model functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.org = Organization.objects.create(
            title='Test Organization'
        )
        
    def test_create_evaluation_config(self):
        """Test creating an evaluation configuration"""
        config = EvaluationFieldConfig.objects.create(
            name='Test Invoice',
            key='test_invoice',
            description='Test invoice configuration',
            required_fields=['invoice_number', 'total_amount'],
            optional_fields=['vendor_name', 'date'],
            field_validation_rules={
                'total_amount': {'type': 'number', 'min': 0}
            },
            field_display_properties={
                'labels': {'invoice_number': 'Invoice Number', 'total_amount': 'Total Amount'}
            },
            evaluation_settings={
                'tolerance': 0.01
            },
            created_by=self.user,
            organization=self.org
        )
        
        self.assertEqual(config.name, 'Test Invoice')
        self.assertEqual(config.key, 'test_invoice')
        self.assertEqual(len(config.required_fields), 2)
        self.assertEqual(len(config.optional_fields), 2)
        self.assertEqual(len(config.all_fields), 4)
        self.assertTrue(config.is_field_required('invoice_number'))
        self.assertFalse(config.is_field_required('vendor_name'))
        
    def test_field_properties(self):
        """Test field property methods"""
        config = EvaluationFieldConfig.objects.create(
            name='Test Config',
            key='test_config',
            required_fields=['field1'],
            optional_fields=['field2'],
            field_display_properties={
                'labels': {'field1': 'Field One'},
                'types': {'field1': 'number'}
            }
        )
        
        self.assertEqual(config.get_field_label('field1'), 'Field One')
        self.assertEqual(config.get_field_label('field2'), 'field2')  # fallback
        self.assertEqual(config.get_field_type('field1'), 'number')
        self.assertEqual(config.get_field_type('field2'), 'string')  # default


class EvaluationConfigAPITest(APITestCase):
    """Test Evaluation Config API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test config
        self.config = EvaluationFieldConfig.objects.create(
            name='Test Invoice',
            key='test_invoice',
            required_fields=['invoice_number', 'total_amount'],
            optional_fields=['vendor_name'],
            is_active=True
        )
        
    def test_list_evaluation_configs(self):
        """Test listing evaluation configurations"""
        url = reverse('evaluation_configs:evaluation-configs-list')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertGreater(len(response.data), 0)
        
    def test_get_evaluation_config(self):
        """Test getting a specific evaluation configuration"""
        url = reverse('evaluation_configs:evaluation-configs-detail', kwargs={'pk': self.config.pk})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Invoice')
        self.assertEqual(response.data['key'], 'test_invoice')
        
    def test_create_evaluation_config(self):
        """Test creating evaluation configuration via API"""
        url = reverse('evaluation_configs:evaluation-configs-list')
        data = {
            'name': 'New Receipt',
            'key': 'new_receipt',
            'description': 'New receipt configuration',
            'required_fields': ['receipt_number', 'amount'],
            'optional_fields': ['date'],
            'field_validation_rules': {},
            'field_display_properties': {},
            'evaluation_settings': {}
        }
        
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['name'], 'New Receipt')
        
    def test_update_evaluation_config(self):
        """Test updating evaluation configuration"""
        url = reverse('evaluation_configs:evaluation-configs-detail', kwargs={'pk': self.config.pk})
        data = {
            'name': 'Updated Invoice',
            'key': 'test_invoice',
            'required_fields': ['invoice_number', 'total_amount', 'date'],
            'optional_fields': ['vendor_name']
        }
        
        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Updated Invoice')
        self.assertEqual(len(response.data['required_fields']), 3)


class FrontendAPITest(APITestCase):
    """Test Frontend API endpoints"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.client.force_authenticate(user=self.user)
        
        # Create test configs
        self.config1 = EvaluationFieldConfig.objects.create(
            name='Invoice',
            key='invoice',
            required_fields=['invoice_number', 'total_amount'],
            is_active=True
        )
        self.config2 = EvaluationFieldConfig.objects.create(
            name='Receipt',
            key='receipt',
            required_fields=['receipt_number', 'amount'],
            is_active=True
        )
        
    def test_list_active_configs(self):
        """Test listing active evaluation configurations for frontend"""
        url = reverse('evaluation_configs:frontend-get-available-configs')
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data), 2)
        
        # Check that response contains necessary fields
        config_data = response.data[0]
        required_fields = ['id', 'name', 'key', 'required_fields', 'optional_fields']
        for field in required_fields:
            self.assertIn(field, config_data)
            
    def test_get_config_by_key(self):
        """Test getting configuration by key"""
        url = reverse('evaluation_configs:frontend-get-config-by-key', kwargs={'config_key': self.config1.key})
        response = self.client.get(url)
        
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Invoice')
        self.assertEqual(response.data['key'], 'invoice')


class ProjectEvaluationConfigTest(TestCase):
    """Test Project-EvaluationConfig relationship"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.org = Organization.objects.create(title='Test Org')
        
        self.project = Project.objects.create(
            title='Test Project',
            created_by=self.user,
            organization=self.org
        )
        
        self.config = EvaluationFieldConfig.objects.create(
            name='Invoice',
            key='invoice',
            required_fields=['invoice_number', 'total_amount'],
            optional_fields=['vendor_name'],
            organization=self.org
        )
        
    def test_project_evaluation_config_creation(self):
        """Test creating project evaluation configuration"""
        project_config = ProjectEvaluationConfig.objects.create(
            project=self.project,
            evaluation_config=self.config,
            custom_required_fields=['invoice_number', 'total_amount', 'date']
        )
        
        self.assertEqual(project_config.project, self.project)
        self.assertEqual(project_config.evaluation_config, self.config)
        self.assertEqual(len(project_config.effective_required_fields), 3)
        self.assertIn('date', project_config.effective_required_fields)
        
    def test_effective_fields(self):
        """Test effective fields calculation"""
        project_config = ProjectEvaluationConfig.objects.create(
            project=self.project,
            evaluation_config=self.config
        )
        
        # Without custom fields, should use config defaults
        self.assertEqual(
            project_config.effective_required_fields,
            self.config.required_fields
        )
        
        # With custom fields, should use custom
        project_config.custom_required_fields = ['custom_field']
        project_config.save()
        self.assertEqual(
            project_config.effective_required_fields,
            ['custom_field']
        )


class DocumentEvaluationTest(TestCase):
    """Test document evaluation functionality"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.org = Organization.objects.create(title='Test Org')
        
        self.config = EvaluationFieldConfig.objects.create(
            name='Invoice',
            key='invoice',
            required_fields=['invoice_number', 'total_amount', 'vendor_name'],
            field_validation_rules={
                'total_amount': {'type': 'number', 'min': 0}
            },
            evaluation_settings={
                'tolerance': 0.01,
                'comparison_rules': {
                    'total_amount': {'tolerance': 0.05}
                }
            }
        )
        
    def test_document_evaluation_import(self):
        """Test that document evaluation module can be imported"""
        try:
            from data_manager.actions.document_evaluation import evaluate_documents
            self.assertTrue(callable(evaluate_documents))
        except ImportError as e:
            self.fail(f"Could not import document_evaluation: {e}")
            
    def test_invoice_evaluation_compatibility(self):
        """Test that invoice evaluation still works with new system"""
        try:
            from data_manager.actions.invoice_evaluation import evaluate_invoices
            self.assertTrue(callable(evaluate_invoices))
        except ImportError as e:
            self.fail(f"Could not import invoice_evaluation: {e}")


class IntegrationTest(APITestCase):
    """Integration tests for the complete system"""
    
    def setUp(self):
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass123'
        )
        self.org = Organization.objects.create(title='Test Org')
        self.client.force_authenticate(user=self.user)
        
    def test_complete_workflow(self):
        """Test complete workflow from config creation to project usage"""
        
        # 1. Create evaluation config
        config_data = {
            'name': 'Test Invoice',
            'key': 'test_invoice_workflow',
            'description': 'Test workflow configuration',
            'required_fields': ['invoice_number', 'total_amount'],
            'optional_fields': ['vendor_name'],
            'field_validation_rules': {
                'total_amount': {'type': 'number', 'min': 0}
            },
            'field_display_properties': {
                'labels': {
                    'invoice_number': 'Invoice Number',
                    'total_amount': 'Total Amount'
                }
            },
            'evaluation_settings': {
                'tolerance': 0.01
            }
        }
        
        url = reverse('evaluation_configs:evaluation-configs-list')
        response = self.client.post(url, config_data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        config_id = response.data['id']
        
        # 2. Get active configs for frontend
        url = reverse('evaluation_configs:frontend-get-available-configs')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertTrue(any(config['key'] == 'test_invoice_workflow' for config in response.data))
        
        # 3. Get config by key
        url = reverse('evaluation_configs:frontend-get-config-by-key', kwargs={'config_key': 'test_invoice_workflow'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Test Invoice')
        
        # 4. Verify all required fields are present in response
        required_response_fields = [
            'id', 'name', 'key', 'required_fields', 'optional_fields',
            'field_labels', 'field_types', 'evaluation_settings'
        ]
        for field in required_response_fields:
            self.assertIn(field, response.data) 
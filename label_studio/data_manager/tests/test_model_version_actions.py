"""
Unit tests for model version functionality in data manager actions
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
import json
from django.test import TestCase, RequestFactory
from django.contrib.auth.models import User

# Import modules to test
from data_manager.actions.basic import retrieve_tasks_predictions_form, retrieve_tasks_predictions
from data_manager.functions import evaluate_predictions
from projects.models import Project
from ml.models import MLBackend


class TestModelVersionForm(TestCase):
    """Test model version form generation"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        
        # Create a mock project
        self.project = Mock()
        self.project.ml_backend = None
        self.project.get_model_versions.return_value = ['gemini-1.5-pro', 'gemini-2.5-flash']
    
    def test_form_without_ml_backend(self):
        """Test form generation when no ML backend is configured"""
        form_data = retrieve_tasks_predictions_form(self.user, self.project)
        
        # Should have 2 columns (prompt and model version)
        self.assertEqual(len(form_data), 1)
        self.assertEqual(form_data[0]['columnCount'], 2)
        
        # Should have both prompt_name and model_version fields
        fields = form_data[0]['fields']
        field_names = [field['name'] for field in fields]
        self.assertIn('prompt_name', field_names)
        self.assertIn('model_version', field_names)
        
        # Model version should only have default option and historical versions
        model_version_field = next(field for field in fields if field['name'] == 'model_version')
        self.assertGreater(len(model_version_field['options']), 1)  # At least default + historical
        
        # First option should be "Use Default"
        self.assertEqual(model_version_field['options'][0]['label'], 'Use Default')
        self.assertEqual(model_version_field['options'][0]['value'], '')
    
    @patch('data_manager.actions.basic.logger')
    def test_form_with_ml_backend_success(self, mock_logger):
        """Test form generation with successful ML backend version retrieval"""
        # Mock ML backend with successful get_versions
        mock_ml_backend = Mock()
        mock_response = Mock()
        mock_response.is_error = False
        mock_response.response = {
            'versions': [
                {
                    'processor_type': 'gemini',
                    'model_name': 'gemini-2.5-flash',
                    'description': 'Gemini 2.5 Flash (Latest)',
                    'version_string': 'gemini|gemini-2.5-flash'
                },
                {
                    'processor_type': 'gemini',
                    'model_name': 'gemini-1.5-pro',
                    'description': 'Gemini 1.5 Pro (High Performance)',
                    'version_string': 'gemini|gemini-1.5-pro'
                }
            ]
        }
        mock_ml_backend.get_versions.return_value = mock_response
        self.project.ml_backend = mock_ml_backend
        
        form_data = retrieve_tasks_predictions_form(self.user, self.project)
        
        # Find model version field
        fields = form_data[0]['fields']
        model_version_field = next(field for field in fields if field['name'] == 'model_version')
        
        # Should have default + ML backend versions + historical versions
        self.assertGreater(len(model_version_field['options']), 3)
        
        # Check ML backend versions are included
        option_labels = [opt['label'] for opt in model_version_field['options']]
        self.assertIn('Gemini 2.5 Flash (Latest)', option_labels)
        self.assertIn('Gemini 1.5 Pro (High Performance)', option_labels)
    
    @patch('data_manager.actions.basic.logger')
    def test_form_with_ml_backend_error(self, mock_logger):
        """Test form generation when ML backend get_versions fails"""
        # Mock ML backend with failed get_versions
        mock_ml_backend = Mock()
        mock_response = Mock()
        mock_response.is_error = True
        mock_response.error_message = "Backend unavailable"
        mock_ml_backend.get_versions.return_value = mock_response
        self.project.ml_backend = mock_ml_backend
        
        form_data = retrieve_tasks_predictions_form(self.user, self.project)
        
        # Should still work with default and historical options
        fields = form_data[0]['fields']
        model_version_field = next(field for field in fields if field['name'] == 'model_version')
        
        # Should have at least default option
        self.assertGreaterEqual(len(model_version_field['options']), 1)
        self.assertEqual(model_version_field['options'][0]['label'], 'Use Default')
    
    @patch('data_manager.actions.basic.UserPreference')
    def test_form_with_user_preferences(self, mock_user_preference):
        """Test form generation respects user preferences"""
        # Mock user preferences
        mock_prompt_pref = Mock()
        mock_prompt_pref.preference_value = 'my_favorite_prompt'
        
        mock_version_pref = Mock()
        mock_version_pref.preference_value = 'gemini|gemini-1.5-pro'
        
        # Setup mock to return different preferences for different keys
        def mock_filter(**kwargs):
            mock_queryset = Mock()
            if kwargs.get('preference_key') == 'last_selected_prompt':
                mock_queryset.first.return_value = mock_prompt_pref
            elif kwargs.get('preference_key') == 'last_selected_model_version':
                mock_queryset.first.return_value = mock_version_pref
            else:
                mock_queryset.first.return_value = None
            return mock_queryset
        
        mock_user_preference.objects.filter.side_effect = mock_filter
        
        # Mock available prompts
        with patch('data_manager.actions.basic.Prompt') as mock_prompt_model:
            mock_prompt = Mock()
            mock_prompt.name = 'my_favorite_prompt'
            mock_prompts = Mock()
            mock_prompts.exists.return_value = True
            mock_prompts.first.return_value = mock_prompt
            mock_prompt_model.objects.all.return_value = mock_prompts
            
            form_data = retrieve_tasks_predictions_form(self.user, self.project)
        
        # Check that preferences are used as defaults
        fields = form_data[0]['fields']
        prompt_field = next(field for field in fields if field['name'] == 'prompt_name')
        model_version_field = next(field for field in fields if field['name'] == 'model_version')
        
        self.assertEqual(prompt_field['value'], 'my_favorite_prompt')
        self.assertEqual(model_version_field['value'], 'gemini|gemini-1.5-pro')


class TestModelVersionRetrieval(TestCase):
    """Test model version functionality in retrieve_tasks_predictions"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.factory = RequestFactory()
        self.user = User.objects.create_user(
            username='testuser',
            email='test@example.com',
            password='testpass'
        )
        
        # Mock project and queryset
        self.project = Mock()
        self.project.has_ml_backend.return_value = True
        self.project.ml_backend = Mock()
        self.project.ml_backend.state = 'CO'  # Connected
        self.project.title = 'Test Project'
        self.project.id = 1
        
        self.queryset = Mock()
        self.queryset.count.return_value = 5
    
    def test_retrieve_with_model_version(self):
        """Test retrieve_tasks_predictions with model_version parameter"""
        # Create request with model_version
        request = self.factory.post('/api/actions/', {
            'prompt_name': 'test_prompt',
            'model_version': 'gemini|gemini-2.5-flash'
        })
        request.user = self.user
        
        # Mock evaluate_predictions
        with patch('data_manager.actions.basic.evaluate_predictions') as mock_evaluate:
            mock_evaluate.return_value = {'processed_items': 5}
            
            result = retrieve_tasks_predictions(
                project=self.project,
                queryset=self.queryset,
                request=request
            )
        
        # Verify evaluate_predictions was called with both parameters
        mock_evaluate.assert_called_once()
        call_args = mock_evaluate.call_args
        self.assertEqual(call_args[1]['prompt_name'], 'test_prompt')
        self.assertEqual(call_args[1]['model_version'], 'gemini|gemini-2.5-flash')
        self.assertEqual(call_args[1]['project'], self.project)
    
    def test_retrieve_without_model_version(self):
        """Test retrieve_tasks_predictions without model_version parameter"""
        # Create request without model_version
        request = self.factory.post('/api/actions/', {
            'prompt_name': 'test_prompt'
        })
        request.user = self.user
        
        # Mock evaluate_predictions
        with patch('data_manager.actions.basic.evaluate_predictions') as mock_evaluate:
            mock_evaluate.return_value = {'processed_items': 5}
            
            result = retrieve_tasks_predictions(
                project=self.project,
                queryset=self.queryset,
                request=request
            )
        
        # Verify evaluate_predictions was called with None model_version
        mock_evaluate.assert_called_once()
        call_args = mock_evaluate.call_args
        self.assertEqual(call_args[1]['prompt_name'], 'test_prompt')
        self.assertIsNone(call_args[1]['model_version'])
    
    @patch('data_manager.actions.basic.UserPreference')
    def test_user_preference_saving(self, mock_user_preference):
        """Test that user preferences are saved correctly"""
        # Mock UserPreference.objects.get_or_create
        mock_get_or_create = Mock()
        mock_user_preference.objects.get_or_create = mock_get_or_create
        
        # Create request with both parameters
        request = self.factory.post('/api/actions/', {
            'prompt_name': 'test_prompt',
            'model_version': 'gemini|gemini-2.5-flash'
        })
        request.user = self.user
        
        # Mock evaluate_predictions
        with patch('data_manager.actions.basic.evaluate_predictions') as mock_evaluate:
            mock_evaluate.return_value = {'processed_items': 5}
            
            result = retrieve_tasks_predictions(
                project=self.project,
                queryset=self.queryset,
                request=request
            )
        
        # Verify user preferences were saved
        self.assertEqual(mock_get_or_create.call_count, 2)  # One for prompt, one for model_version
        
        # Check the calls
        calls = mock_get_or_create.call_args_list
        
        # Find prompt preference call
        prompt_call = next(call for call in calls if call[1]['preference_key'] == 'last_selected_prompt')
        self.assertEqual(prompt_call[1]['defaults']['preference_value'], 'test_prompt')
        
        # Find model version preference call
        version_call = next(call for call in calls if call[1]['preference_key'] == 'last_selected_model_version')
        self.assertEqual(version_call[1]['defaults']['preference_value'], 'gemini|gemini-2.5-flash')


class TestEvaluatePredictionsWithModelVersion(TestCase):
    """Test evaluate_predictions function with model version support"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock tasks
        self.task1 = Mock()
        self.task1.id = 1
        self.task2 = Mock()
        self.task2.id = 2
        self.tasks = [self.task1, self.task2]
        
        # Mock project
        self.project = Mock()
        self.project.title = 'Test Project'
        self.project.id = 1
        
        # Mock ML backend
        self.ml_backend = Mock()
        self.project.ml_backend = self.ml_backend
    
    def test_evaluate_predictions_with_model_version(self):
        """Test that evaluate_predictions passes model_version to ML backend"""
        with patch('data_manager.functions.logger'):
            evaluate_predictions(
                tasks=self.tasks,
                prompt_name='test_prompt',
                model_version='gemini|gemini-2.5-flash',
                project=self.project
            )
        
        # Verify ML backend was called with both parameters
        self.ml_backend.predict_tasks.assert_called_once_with(
            tasks=self.tasks,
            prompt_name='test_prompt',
            model_version='gemini|gemini-2.5-flash'
        )
    
    def test_evaluate_predictions_without_model_version(self):
        """Test that evaluate_predictions works without model_version"""
        with patch('data_manager.functions.logger'):
            evaluate_predictions(
                tasks=self.tasks,
                prompt_name='test_prompt',
                project=self.project
            )
        
        # Verify ML backend was called with None model_version
        self.ml_backend.predict_tasks.assert_called_once_with(
            tasks=self.tasks,
            prompt_name='test_prompt',
            model_version=None
        )
    
    def test_evaluate_predictions_project_inference(self):
        """Test that project is correctly inferred from tasks when not provided"""
        # Set up task with project
        self.task1.project = self.project
        
        with patch('data_manager.functions.logger'):
            evaluate_predictions(
                tasks=self.tasks,
                prompt_name='test_prompt',
                model_version='gemini|gemini-2.5-flash'
            )
        
        # Verify ML backend was called (project was inferred)
        self.ml_backend.predict_tasks.assert_called_once()


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
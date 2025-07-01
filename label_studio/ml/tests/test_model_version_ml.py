"""
Unit tests for model version functionality in ML models
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from django.test import TestCase

# Import modules to test
from ml.models import MLBackend
from ml.api_connector import MLApi
from projects.models import Project


class TestMLBackendModelVersion(TestCase):
    """Test MLBackend model version functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock project
        self.project = Mock()
        self.project.id = 1
        self.project.title = 'Test Project'
        
        # Create MLBackend instance
        self.ml_backend = MLBackend(
            url='http://localhost:9090',
            title='Test Backend',
            project=self.project
        )
        
        # Mock tasks
        self.task1 = Mock()
        self.task1.id = 1
        self.task2 = Mock()
        self.task2.id = 2
        self.tasks = [self.task1, self.task2]
    
    @patch('ml.models.TaskSimpleSerializer')
    def test_predict_tasks_with_model_version(self, mock_serializer):
        """Test predict_tasks method with model_version parameter"""
        # Mock serializer
        mock_serializer.return_value.data = [
            {'id': 1, 'data': 'task1'},
            {'id': 2, 'data': 'task2'}
        ]
        
        # Mock _get_predictions_from_ml_backend
        with patch.object(self.ml_backend, '_get_predictions_from_ml_backend') as mock_get_predictions:
            mock_get_predictions.return_value = [
                {'task': 1, 'result': 'prediction1'},
                {'task': 2, 'result': 'prediction2'}
            ]
            
            # Mock update_state
            with patch.object(self.ml_backend, 'update_state') as mock_update_state:
                mock_update_state.return_value = 'default-model-version'
                
                # Mock not_ready property
                with patch.object(self.ml_backend, 'not_ready', False):
                    # Mock tasks queryset methods
                    mock_queryset = Mock()
                    mock_queryset.annotate.return_value = mock_queryset
                    mock_queryset.exclude.return_value = mock_queryset
                    mock_queryset.exists.return_value = True
                    
                    with patch('ml.models.TaskSimpleSerializer', return_value=mock_queryset):
                        result = self.ml_backend.predict_tasks(
                            tasks=self.tasks,
                            prompt_name='test_prompt',
                            model_version='gemini|gemini-2.5-flash'
                        )
        
        # Verify _get_predictions_from_ml_backend was called with model_version
        mock_get_predictions.assert_called_once()
        call_args = mock_get_predictions.call_args
        self.assertIn('model_version', call_args[1])
        self.assertEqual(call_args[1]['model_version'], 'gemini|gemini-2.5-flash')
    
    def test_get_predictions_from_ml_backend_with_model_version(self):
        """Test _get_predictions_from_ml_backend with model_version parameter"""
        # Mock API
        mock_api = Mock()
        mock_response = Mock()
        mock_response.is_error = False
        mock_response.response = {
            'results': [
                {'result': 'prediction1', 'score': 0.9},
                {'result': 'prediction2', 'score': 0.8}
            ]
        }
        mock_api.make_predictions.return_value = mock_response
        
        with patch.object(self.ml_backend, 'api', mock_api):
            serialized_tasks = [
                {'id': 1, 'project': 1, 'data': 'task1'},
                {'id': 2, 'project': 1, 'data': 'task2'}
            ]
            
            predictions = self.ml_backend._get_predictions_from_ml_backend(
                serialized_tasks,
                prompt_name='test_prompt',
                model_version='gemini|gemini-2.5-flash'
            )
        
        # Verify API was called with model_version
        mock_api.make_predictions.assert_called_once()
        call_args = mock_api.make_predictions.call_args
        self.assertIn('model_version', call_args[1])
        self.assertEqual(call_args[1]['model_version'], 'gemini|gemini-2.5-flash')
    
    def test_get_predictions_one_by_one_with_model_version(self):
        """Test _get_predictions_from_ml_backend_one_by_one with model_version"""
        serialized_tasks = [
            {'id': 1, 'project': 1, 'data': 'task1'},
            {'id': 2, 'project': 1, 'data': 'task2'}
        ]
        current_responses = [{'result': 'single_response'}]  # Single response triggers one-by-one
        
        # Mock the recursive call to _get_predictions_from_ml_backend
        with patch.object(self.ml_backend, '_get_predictions_from_ml_backend') as mock_get_predictions:
            mock_get_predictions.return_value = [{'prediction': 'test'}]
            
            result = self.ml_backend._get_predictions_from_ml_backend_one_by_one(
                serialized_tasks,
                current_responses,
                prompt_name='test_prompt',
                model_version='gemini|gemini-2.5-flash'
            )
        
        # Verify that each call included model_version
        self.assertEqual(mock_get_predictions.call_count, 2)  # One for each task
        for call in mock_get_predictions.call_args_list:
            self.assertIn('model_version', call[1])
            self.assertEqual(call[1]['model_version'], 'gemini|gemini-2.5-flash')


class TestMLApiModelVersion(TestCase):
    """Test MLApi model version functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.api = MLApi(url='http://localhost:9090')
        
        # Mock project
        self.project = Mock()
        self.project.id = 1
        self.project.title = 'Test Project'
        self.project.label_config = '<View></View>'
        self.project.task_data_login = None
        self.project.task_data_password = None
    
    def test_prep_prediction_req_with_model_version(self):
        """Test _prep_prediction_req includes model_version in params"""
        tasks = [{'id': 1, 'data': 'task1'}]
        
        # Mock _create_project_uid
        with patch.object(self.api, '_create_project_uid') as mock_create_uid:
            mock_create_uid.return_value = 'project_uid'
            
            request = self.api._prep_prediction_req(
                tasks=tasks,
                project=self.project,
                context=None,
                prompt_name='test_prompt',
                model_version='gemini|gemini-2.5-flash'
            )
        
        # Verify model_version is in params
        self.assertIn('params', request)
        self.assertIn('model_version', request['params'])
        self.assertEqual(request['params']['model_version'], 'gemini|gemini-2.5-flash')
    
    def test_prep_prediction_req_without_model_version(self):
        """Test _prep_prediction_req without model_version"""
        tasks = [{'id': 1, 'data': 'task1'}]
        
        # Mock _create_project_uid
        with patch.object(self.api, '_create_project_uid') as mock_create_uid:
            mock_create_uid.return_value = 'project_uid'
            
            request = self.api._prep_prediction_req(
                tasks=tasks,
                project=self.project,
                context=None,
                prompt_name='test_prompt'
            )
        
        # Verify model_version is not in params when not provided
        self.assertIn('params', request)
        self.assertNotIn('model_version', request['params'])
    
    @patch('ml.api_connector.Prompt')
    def test_prep_prediction_req_with_prompt_and_model_version(self, mock_prompt_model):
        """Test _prep_prediction_req with both prompt and model_version"""
        # Mock prompt
        mock_prompt = Mock()
        mock_prompt.content = 'Test prompt content'
        mock_prompt.get_runtime_config.return_value = {
            'temperature': 0.7,
            'response_mime_type': 'application/json'
        }
        mock_prompt_model.objects.get.return_value = mock_prompt
        
        tasks = [{'id': 1, 'data': 'task1'}]
        
        # Mock _create_project_uid
        with patch.object(self.api, '_create_project_uid') as mock_create_uid:
            mock_create_uid.return_value = 'project_uid'
            
            request = self.api._prep_prediction_req(
                tasks=tasks,
                project=self.project,
                context=None,
                prompt_name='test_prompt',
                model_version='gemini|gemini-2.5-flash'
            )
        
        # Verify both prompt and model_version are included
        params = request['params']
        self.assertIn('prompt', params)
        self.assertIn('prompt_name', params)
        self.assertIn('model_version', params)
        self.assertIn('runtime_config', params)
        
        # Verify model_version is added to runtime_config
        runtime_config = params['runtime_config']
        self.assertIn('model_version', runtime_config)
        self.assertEqual(runtime_config['model_version'], 'gemini|gemini-2.5-flash')
    
    def test_make_predictions_with_model_version(self):
        """Test make_predictions method includes model_version"""
        tasks = [{'id': 1, 'data': 'task1'}]
        
        # Mock _prep_prediction_req
        with patch.object(self.api, '_prep_prediction_req') as mock_prep:
            mock_prep.return_value = {'test': 'request'}
            
            # Mock _request
            with patch.object(self.api, '_request') as mock_request:
                mock_request.return_value = Mock()
                
                self.api.make_predictions(
                    tasks=tasks,
                    project=self.project,
                    context=None,
                    prompt_name='test_prompt',
                    model_version='gemini|gemini-2.5-flash'
                )
        
        # Verify _prep_prediction_req was called with model_version
        mock_prep.assert_called_once()
        call_args = mock_prep.call_args
        self.assertIn('model_version', call_args[1])
        self.assertEqual(call_args[1]['model_version'], 'gemini|gemini-2.5-flash')


class TestModelVersionIntegration(TestCase):
    """Integration tests for model version functionality"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock project
        self.project = Mock()
        self.project.id = 1
        self.project.title = 'Test Project'
        
        # Mock MLBackend
        self.ml_backend = MLBackend(
            url='http://localhost:9090',
            title='Test Backend',
            project=self.project
        )
    
    @patch('ml.models.TaskSimpleSerializer')
    @patch('ml.api_connector.MLApiResult')
    def test_end_to_end_model_version_flow(self, mock_api_result, mock_serializer):
        """Test complete flow from predict_tasks to ML API with model_version"""
        # Mock serializer
        mock_serializer.return_value.data = [{'id': 1, 'data': 'task1'}]
        
        # Mock API response
        mock_response = Mock()
        mock_response.is_error = False
        mock_response.response = {
            'results': [{'result': 'prediction', 'score': 0.9}]
        }
        
        # Mock the API request
        with patch.object(self.ml_backend, 'api') as mock_api:
            mock_api.make_predictions.return_value = mock_response
            
            # Mock update_state and other prerequisites
            with patch.object(self.ml_backend, 'update_state') as mock_update_state:
                mock_update_state.return_value = 'default-model'
                
                with patch.object(self.ml_backend, 'not_ready', False):
                    # Mock tasks queryset
                    mock_tasks = Mock()
                    mock_tasks.annotate.return_value = mock_tasks
                    mock_tasks.exclude.return_value = mock_tasks
                    mock_tasks.exists.return_value = True
                    
                    with patch('ml.models.TaskSimpleSerializer', return_value=mock_tasks):
                        result = self.ml_backend.predict_tasks(
                            tasks=[Mock()],
                            prompt_name='test_prompt',
                            model_version='gemini|gemini-2.5-flash'
                        )
        
        # Verify the complete chain included model_version
        mock_api.make_predictions.assert_called_once()
        call_args = mock_api.make_predictions.call_args
        self.assertIn('model_version', call_args[1])
        self.assertEqual(call_args[1]['model_version'], 'gemini|gemini-2.5-flash')


if __name__ == '__main__':
    # Run tests
    unittest.main(verbosity=2)
import pytest
import random
from django.contrib.auth import get_user_model
from projects.models import Project
from tasks.models import Task, Annotation, Prediction
from organizations.models import Organization
from data_manager.actions.evaluation import (
    evaluate_annotations_vs_predictions,
    evaluate_inter_annotator_agreement,
    mock_calculate_metrics
)

User = get_user_model()


# Mock data for testing
MOCK_LABEL_CONFIG = '''
<View>
  <Text name="text" value="$text"/>
  <Choices name="sentiment" toName="text">
    <Choice value="positive"/>
    <Choice value="negative"/>
    <Choice value="neutral"/>
  </Choices>
</View>
'''

@pytest.fixture
@pytest.mark.django_db
def setup_evaluation_test_data():
    """Set up test environment with users, organization, and project"""
    # Create user
    user = User.objects.create_user(
        username='test_evaluator',
        email='test@example.com',
        password='testpass123'
    )
    
    # Create organization
    organization = Organization.objects.create(
        title='Test Evaluation Org',
        created_by=user
    )
    
    # Create project
    project = Project.objects.create(
        title='Evaluation Test Project',
        description='Project for testing evaluation functionality',
        label_config=MOCK_LABEL_CONFIG,
        organization=organization,
        created_by=user
    )
    
    # Create sample tasks
    tasks = []
    sample_texts = [
        'This is a great product!',
        'I hate this service.',
        'The weather is okay today.',
        'Amazing experience, highly recommend!',
        'Could be better, not satisfied.'
    ]
    
    for i, text in enumerate(sample_texts):
        task = Task.objects.create(
            project=project,
            data={'text': text}
        )
        tasks.append(task)
    
    return {
        'user': user,
        'organization': organization,
        'project': project,
        'tasks': tasks
    }


def create_annotations(tasks, user):
    """Create sample annotations for tasks"""
    annotations = []
    sentiments = ['positive', 'negative', 'neutral']
    
    for task in tasks:
        # Create annotation with random sentiment
        sentiment = random.choice(sentiments)
        annotation_data = {
            'result': [{
                'value': {'choices': [sentiment]},
                'from_name': 'sentiment',
                'to_name': 'text',
                'type': 'choices'
            }]
        }
        
        annotation = Annotation.objects.create(
            task=task,
            completed_by=user,
            result=annotation_data['result'],
            was_cancelled=False
        )
        annotations.append(annotation)
    
    return annotations


def create_predictions(tasks, user):
    """Create sample predictions for tasks"""
    predictions = []
    sentiments = ['positive', 'negative', 'neutral']
    
    for task in tasks:
        # Create prediction with random sentiment and confidence
        sentiment = random.choice(sentiments)
        confidence = random.uniform(0.6, 0.95)
        
        prediction_data = {
            'result': [{
                'value': {'choices': [sentiment]},
                'from_name': 'sentiment',
                'to_name': 'text',
                'type': 'choices',
                'score': confidence
            }]
        }
        
        prediction = Prediction.objects.create(
            task=task,
            result=prediction_data['result'],
            score=confidence
        )
        predictions.append(prediction)
    
    return predictions


def create_multiple_annotations_for_agreement(tasks, user):
    """Create multiple annotations per task for agreement testing"""
    annotations = []
    sentiments = ['positive', 'negative', 'neutral']
    
    for task in tasks:
        # Create 2-3 annotations per task from different perspectives
        num_annotations = random.randint(2, 3)
        
        for i in range(num_annotations):
            sentiment = random.choice(sentiments)
            annotation_data = {
                'result': [{
                    'value': {'choices': [sentiment]},
                    'from_name': 'sentiment',
                    'to_name': 'text',
                    'type': 'choices'
                }]
            }
            
            annotation = Annotation.objects.create(
                task=task,
                completed_by=user,
                result=annotation_data['result'],
                was_cancelled=False
            )
            annotations.append(annotation)
    
    return annotations


# Test functions

@pytest.mark.django_db
def test_complete_evaluation_workflow_simple(setup_evaluation_test_data):
    """Test basic evaluation workflow"""
    data = setup_evaluation_test_data
    
    # Create annotations and predictions
    annotations = create_annotations(data['tasks'], data['user'])
    predictions = create_predictions(data['tasks'], data['user'])
    
    # Test evaluation function
    task_ids = [task.id for task in data['tasks']]
    result = evaluate_annotations_vs_predictions(
        data['project'],
        queryset=Task.objects.filter(id__in=task_ids)
    )
    
    # Basic assertions
    assert result is not None
    
    # Verify response structure
    assert 'processed_items' in result
    assert 'detail' in result
    assert 'evaluation_results' in result
    
    # Check evaluation results
    eval_results = result['evaluation_results']
    assert 'metrics' in eval_results
    assert 'accuracy' in eval_results['metrics']
    assert 'precision' in eval_results['metrics']
    assert 'recall' in eval_results['metrics']
    assert 'f1_score' in eval_results['metrics']


@pytest.mark.django_db
def test_inter_annotator_agreement_simple(setup_evaluation_test_data):
    """Test inter-annotator agreement calculation"""
    data = setup_evaluation_test_data
    
    # Create annotations from first annotator
    first_annotations = create_annotations(data['tasks'], data['user'])
    
    # Create annotations from second annotator
    second_annotations = create_multiple_annotations_for_agreement(data['tasks'], data['user'])
    
    # Test agreement function
    task_ids = [task.id for task in data['tasks']]
    result = evaluate_inter_annotator_agreement(
        data['project'],
        queryset=Task.objects.filter(id__in=task_ids)
    )
    
    # Basic assertions
    assert result is not None
    
    # Verify response structure
    assert 'processed_items' in result
    assert 'detail' in result
    assert 'agreement_score' in result


def test_mock_calculate_metrics():
    """Test the mock calculate metrics function directly"""
    # Test with empty data
    empty_result = mock_calculate_metrics([], [])
    assert empty_result['accuracy'] == 0.0
    assert empty_result['total_tasks'] == 0
    
    # Test with sample data
    sample_annotations = [{'result': [{'value': {'choices': ['positive']}}]}]
    sample_predictions = [{'result': [{'value': {'choices': ['positive']}}]}]
    
    result = mock_calculate_metrics(sample_annotations, sample_predictions)
    
    # Check required metrics exist
    required_metrics = ['accuracy', 'precision', 'recall', 'f1_score', 'total_tasks', 'evaluated_tasks']
    for metric in required_metrics:
        assert metric in result
    
    # Check values are reasonable
    assert 0.0 <= result['accuracy'] <= 1.0
    assert result['total_tasks'] == 1
    assert result['evaluated_tasks'] == 1


@pytest.mark.django_db
def test_evaluation_with_no_data(setup_evaluation_test_data):
    """Test evaluation when there are no annotations or predictions"""
    data = setup_evaluation_test_data
    
    # Test evaluation without creating any annotations or predictions
    task_ids = [task.id for task in data['tasks']]
    result = evaluate_annotations_vs_predictions(
        data['project'], 
        queryset=Task.objects.filter(id__in=task_ids)
    )
    
    # Should handle gracefully
    assert result is not None
    
    # Verify response structure
    assert 'processed_items' in result
    assert 'detail' in result
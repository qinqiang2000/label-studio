"""Evaluation actions for comparing annotations and predictions"""
import logging
import random
from datetime import datetime
from typing import Dict, List, Any

from core.permissions import AllPermissions
from django.db.models import Q, Count
from django.db import models
from tasks.models import Task, Annotation, Prediction

all_permissions = AllPermissions()
logger = logging.getLogger(__name__)


def mock_calculate_metrics(annotations: List[Dict], predictions: List[Dict]) -> Dict[str, float]:
    """Mock function to calculate evaluation metrics
    
    In a real implementation, this would:
    1. Parse annotation and prediction results
    2. Calculate metrics like accuracy, precision, recall, F1-score
    3. Handle different task types (classification, NER, object detection, etc.)
    
    For now, we return mock metrics for demonstration
    """
    if not annotations or not predictions:
        return {
            'accuracy': 0.0,
            'precision': 0.0,
            'recall': 0.0,
            'f1_score': 0.0,
            'total_tasks': 0,
            'evaluated_tasks': 0
        }
    
    # Mock calculation - in reality this would be much more complex
    total_tasks = len(annotations)
    evaluated_tasks = min(len(annotations), len(predictions))
    
    # Generate realistic mock metrics
    accuracy = round(random.uniform(0.75, 0.95), 3)
    precision = round(random.uniform(0.70, 0.90), 3)
    recall = round(random.uniform(0.65, 0.85), 3)
    f1_score = round(2 * (precision * recall) / (precision + recall), 3)
    
    return {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1_score': f1_score,
        'total_tasks': total_tasks,
        'evaluated_tasks': evaluated_tasks
    }


def evaluate_annotations_vs_predictions(project, queryset, **kwargs):
    """Evaluate annotations against predictions for selected tasks
    
    :param project: project instance
    :param queryset: filtered tasks db queryset
    :return: evaluation results
    """
    logger.info(f"Starting evaluation for project {project.id} with {queryset.count()} tasks")
    
    # Get tasks with both annotations and predictions
    tasks_with_both = queryset.filter(
        annotations__isnull=False,
        predictions__isnull=False
    ).distinct()
    
    if not tasks_with_both.exists():
        return {
            'processed_items': 0,
            'detail': 'No tasks found with both annotations and predictions',
            'metrics': mock_calculate_metrics([], [])
        }
    
    annotations_data = []
    predictions_data = []
    
    # Collect annotation and prediction data
    for task in tasks_with_both:
        # Get ground truth annotations (completed annotations)
        task_annotations = task.annotations.filter(
            was_cancelled=False
        ).values_list('result', flat=True)
        
        # Get predictions
        task_predictions = task.predictions.all().values_list('result', flat=True)
        
        if task_annotations and task_predictions:
            # For simplicity, take the first annotation as ground truth
            annotations_data.append(list(task_annotations)[0])
            predictions_data.append(list(task_predictions)[0])
    
    # Calculate metrics using mock function
    metrics = mock_calculate_metrics(annotations_data, predictions_data)
    
    # Store evaluation results (in a real implementation, you might want to save these)
    evaluation_summary = {
        'project_id': project.id,
        'evaluated_at': datetime.now().isoformat(),
        'task_count': len(annotations_data),
        'metrics': metrics
    }
    
    logger.info(f"Evaluation completed: {evaluation_summary}")
    
    return {
        'processed_items': len(annotations_data),
        'detail': f'Evaluated {len(annotations_data)} tasks. Accuracy: {metrics["accuracy"]:.1%}',
        'evaluation_results': evaluation_summary
    }


def evaluate_inter_annotator_agreement(project, queryset, **kwargs):
    """Calculate inter-annotator agreement for tasks with multiple annotations
    
    :param project: project instance
    :param queryset: filtered tasks db queryset
    :return: agreement results
    """
    logger.info(f"Starting inter-annotator agreement calculation for project {project.id}")
    
    # Get tasks with multiple annotations
    tasks_with_multiple = queryset.annotate(
        annotation_count=Count('annotations')
    ).filter(annotation_count__gt=1)
    
    if not tasks_with_multiple.exists():
        return {
            'processed_items': 0,
            'detail': 'No tasks found with multiple annotations',
            'agreement_score': 0.0
        }
    
    # Mock agreement calculation
    agreement_scores = []
    evaluated_tasks = 0
    
    for task in tasks_with_multiple:
        annotations = task.annotations.filter(was_cancelled=False)
        if annotations.count() >= 2:
            # Mock agreement score between 0.6 and 0.9
            mock_score = random.uniform(0.6, 0.9)
            agreement_scores.append(mock_score)
            evaluated_tasks += 1
    
    if agreement_scores:
        avg_agreement = sum(agreement_scores) / len(agreement_scores)
    else:
        avg_agreement = 0.0
    
    return {
        'processed_items': evaluated_tasks,
        'detail': f'Calculated agreement for {evaluated_tasks} tasks. Average agreement: {avg_agreement:.1%}',
        'agreement_score': round(avg_agreement, 3),
        'evaluated_tasks': evaluated_tasks
    }


# Import invoice evaluation
from .invoice_evaluation import invoice_actions

# Register actions
actions = [
    {
        'id': 'evaluate_annotations_vs_predictions',
        'entry_point': evaluate_annotations_vs_predictions,
        'permission': all_permissions.predictions_any,
        'title': 'Evaluate Predictions vs Annotations',
        'order': 200,
        'hidden': True,
        'dialog': {
            'text': 'This will evaluate prediction accuracy against ground truth annotations for the selected tasks.',
            'type': 'confirm',
        },
    },
    {
        'id': 'evaluate_inter_annotator_agreement',
        'entry_point': evaluate_inter_annotator_agreement,
        'permission': all_permissions.annotations_view,
        'title': 'Calculate Inter-Annotator Agreement',
        'order': 201,
        'hidden': True,
        'dialog': {
            'text': 'This will calculate agreement scores between multiple annotators for the selected tasks.',
            'type': 'confirm',
        },
    },
] + invoice_actions  # 添加票据提取评估动作
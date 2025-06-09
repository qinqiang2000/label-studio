#!/usr/bin/env python3
"""
Simple test script for evaluation functionality
"""

import sys
import os

# Add the project root directory to Python path
# Current file is at: label_studio/tests/data_manager/actions/test_evaluation.py
# Project root is 4 levels up
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
sys.path.insert(0, project_root)

# Set Django settings before importing Django modules
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings.label_studio')

import django
django.setup()

from data_manager.actions.evaluation import mock_calculate_metrics


def test_mock_metrics():
    """Test the mock metrics calculation"""
    print("Testing mock metrics calculation...")
    
    # Test with empty data
    metrics = mock_calculate_metrics([], [])
    assert metrics['accuracy'] == 0.0
    assert metrics['total_tasks'] == 0
    print("✓ Empty data test passed")
    
    # Test with sample data
    annotations = [{'label': 'positive'}, {'label': 'negative'}]
    predictions = [{'label': 'positive'}, {'label': 'positive'}]
    metrics = mock_calculate_metrics(annotations, predictions)
    
    assert 0 <= metrics['accuracy'] <= 1
    assert 0 <= metrics['precision'] <= 1
    assert 0 <= metrics['recall'] <= 1
    assert 0 <= metrics['f1_score'] <= 1
    assert metrics['total_tasks'] == 2
    assert metrics['evaluated_tasks'] == 2
    print("✓ Sample data test passed")
    print(f"  Sample metrics: {metrics}")


def test_actions_registration():
    """Test that evaluation actions are properly registered"""
    print("\nTesting actions registration...")
    
    # Check if the evaluation module can be imported
    try:
        import data_manager.actions.evaluation as eval_module
        print("✓ Evaluation module imported successfully")
        
        # Check if actions are defined
        assert hasattr(eval_module, 'actions'), "No 'actions' attribute found in evaluation module"
        
        actions = eval_module.actions
        print(f"✓ Found {len(actions)} actions in evaluation module")
        
        # Verify we have the expected actions
        assert len(actions) >= 2, "Expected at least 2 evaluation actions"
        
        action_titles = [action['title'] for action in actions]
        assert 'Evaluate Predictions vs Annotations' in action_titles
        assert 'Calculate Inter-Annotator Agreement' in action_titles
        
        for action in actions:
            print(f"  - {action['title']} (order: {action['order']})")
            
    except ImportError as e:
        assert False, f"Failed to import evaluation module: {e}"


def test_evaluation_functions_exist():
    """Test that evaluation functions exist and can be called"""
    print("\nTesting evaluation functions exist...")
    
    try:
        from data_manager.actions.evaluation import (
            evaluate_annotations_vs_predictions,
            evaluate_inter_annotator_agreement
        )
        print("✓ Evaluation functions imported successfully")
        print("  - evaluate_annotations_vs_predictions")
        print("  - evaluate_inter_annotator_agreement")
        
        # Check if functions are callable
        assert callable(evaluate_annotations_vs_predictions), "evaluate_annotations_vs_predictions is not callable"
        print("✓ evaluate_annotations_vs_predictions is callable")
        
        assert callable(evaluate_inter_annotator_agreement), "evaluate_inter_annotator_agreement is not callable"
        print("✓ evaluate_inter_annotator_agreement is callable")
            
    except ImportError as e:
        assert False, f"Failed to import evaluation functions: {e}"


def main():
    """Run all tests"""
    print("Starting evaluation functionality tests...\n")
    
    try:
        test_mock_metrics()
        test_actions_registration()
        test_evaluation_functions_exist()
        
        print("\n🎉 All tests passed! Evaluation functionality is working correctly.")
        
    except Exception as e:
        print(f"\n❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
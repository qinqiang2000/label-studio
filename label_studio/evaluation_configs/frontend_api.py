"""
Frontend-specific API endpoints for evaluation configurations
Used by frontend components like TextArea.jsx and CreateProject.jsx
"""
import logging
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from projects.models import Project
from .models import EvaluationFieldConfig, ProjectEvaluationConfig

logger = logging.getLogger(__name__)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_configs(request):
    """
    Get all available evaluation configurations for frontend dropdowns
    """
    try:
        configs = EvaluationFieldConfig.objects.filter(
            is_active=True
        ).order_by('name')
        
        # Convert to frontend-friendly format
        config_list = []
        for config in configs:
            config_list.append({
                'id': config.id,
                'key': config.key,
                'name': config.name,
                'value': config.key,  # for dropdown compatibility
                'label': config.name,  # for dropdown compatibility
                'description': config.description,
                'fields': config.all_fields,
                'required_fields': config.required_fields,
                'optional_fields': config.optional_fields,
                'field_labels': config.field_labels,
                'field_types': config.field_types,
                'validation_rules': config.field_validation_rules
            })
        
        return Response(config_list)
        
    except Exception as e:
        logger.error(f"Error getting evaluation configs: {e}")
        return Response(
            {'error': 'Failed to retrieve evaluation configurations'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_project_config(request, project_id):
    """
    Get evaluation configuration for a specific project
    """
    try:
        project = get_object_or_404(Project, id=project_id)
        
        try:
            project_config = ProjectEvaluationConfig.objects.get(project=project)
            config = project_config.evaluation_config
            
            return Response({
                'project_id': project.id,
                'config_key': config.key,
                'config_name': config.name,
                'description': config.description,
                'required_fields': project_config.effective_required_fields,
                'optional_fields': project_config.effective_optional_fields,
                'all_fields': project_config.effective_all_fields,
                'field_labels': config.field_labels,
                'field_types': config.field_types,
                'validation_rules': project_config.effective_validation_rules,
                'is_custom': bool(project_config.custom_required_fields or project_config.custom_optional_fields)
            })
            
        except ProjectEvaluationConfig.DoesNotExist:
            # Check if project has evaluation_field_config configured
            if hasattr(project, 'evaluation_field_config') and project.evaluation_field_config:
                project_eval_config = project.evaluation_field_config
                document_type = project_eval_config.get('document_type')
                
                if document_type:
                    try:
                        # Find configuration by document_type key
                        config = EvaluationFieldConfig.objects.get(
                            key=document_type, 
                            is_active=True
                        )
                        
                        # Use configured fields from project if available, otherwise use config defaults
                        default_fields = project_eval_config.get('default_fields', config.required_fields)
                        
                        return Response({
                            'project_id': project.id,
                            'config_key': config.key,
                            'config_name': config.name,
                            'description': config.description,
                            'required_fields': default_fields,
                            'optional_fields': config.optional_fields,
                            'all_fields': config.all_fields,
                            'field_labels': config.field_labels,
                            'field_types': config.field_types,
                            'validation_rules': config.field_validation_rules,
                            'is_default': False,
                            'is_custom': False
                        })
                        
                    except EvaluationFieldConfig.DoesNotExist:
                        logger.warning(f"Configuration '{document_type}' not found for project {project_id}")
            
            # Return default configuration as last resort
            default_config = EvaluationFieldConfig.objects.filter(
                is_system_default=True,
                is_active=True
            ).first()
            
            if default_config:
                return Response({
                    'project_id': project.id,
                    'config_key': default_config.key,
                    'config_name': default_config.name,
                    'description': default_config.description,
                    'required_fields': default_config.required_fields,
                    'optional_fields': default_config.optional_fields,
                    'all_fields': default_config.all_fields,
                    'field_labels': default_config.field_labels,
                    'field_types': default_config.field_types,
                    'validation_rules': default_config.field_validation_rules,
                    'is_default': True,
                    'is_custom': False
                })
            else:
                return Response(
                    {'error': 'No evaluation configuration found'},
                    status=status.HTTP_404_NOT_FOUND
                )
                
    except Exception as e:
        logger.error(f"Error getting project evaluation config: {e}")
        return Response(
            {'error': 'Failed to retrieve project evaluation configuration'},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_config_by_key(request, config_key):
    """
    Get evaluation configuration by key (for CreateProject component)
    """
    try:
        config = get_object_or_404(EvaluationFieldConfig, key=config_key, is_active=True)
        
        return Response({
            'id': config.id,
            'key': config.key,
            'name': config.name,
            'description': config.description,
            'required_fields': config.required_fields,
            'optional_fields': config.optional_fields,
            'all_fields': config.all_fields,
            'field_labels': config.field_labels,
            'field_types': config.field_types,
            'validation_rules': config.field_validation_rules,
            'evaluation_settings': config.evaluation_settings
        })
        
    except Exception as e:
        logger.error(f"Error getting config by key {config_key}: {e}")
        return Response(
            {'error': f'Configuration "{config_key}" not found'},
            status=status.HTTP_404_NOT_FOUND
        ) 
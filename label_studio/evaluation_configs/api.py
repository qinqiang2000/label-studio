from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.db import models
from core.permissions import all_permissions
from projects.models import Project
from .models import EvaluationFieldConfig, ProjectEvaluationConfig
import logging

logger = logging.getLogger(__name__)


class EvaluationFieldConfigViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing evaluation field configurations
    """
    queryset = EvaluationFieldConfig.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        """Filter by organization if user has one"""
        queryset = super().get_queryset()
        
        # For testing and development, be more permissive
        # In production, you may want to add more strict filtering
        queryset = queryset.filter(is_active=True).order_by('name')
        
        return queryset
    
    def list(self, request, *args, **kwargs):
        """List all available evaluation configurations"""
        queryset = self.get_queryset()
        data = [config.to_dict() for config in queryset]
        return Response(data)
    
    def retrieve(self, request, pk=None):
        """Get a specific evaluation configuration"""
        config = get_object_or_404(self.get_queryset(), pk=pk)
        return Response(config.to_dict())
    
    def create(self, request):
        """Create a new evaluation configuration"""
        data = request.data
        
        try:
            with transaction.atomic():
                config = EvaluationFieldConfig.objects.create(
                    name=data.get('name'),
                    key=data.get('key'),
                    description=data.get('description', ''),
                    required_fields=data.get('required_fields', []),
                    optional_fields=data.get('optional_fields', []),
                    field_validation_rules=data.get('field_validation_rules', {}),
                    field_display_properties=data.get('field_display_properties', {}),
                    evaluation_settings=data.get('evaluation_settings', {}),
                    created_by=request.user,
                    organization=getattr(request.user, 'active_organization', None)
                )
                
                return Response(config.to_dict(), status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"Error creating evaluation config: {e}")
            return Response(
                {'error': f'Failed to create configuration: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def update(self, request, pk=None, partial=False):
        """Update an evaluation configuration"""
        config = get_object_or_404(self.get_queryset(), pk=pk)
        data = request.data
        
        try:
            with transaction.atomic():
                # Only update fields that are provided in partial updates
                if 'name' in data:
                    config.name = data['name']
                if 'description' in data:
                    config.description = data['description']
                if 'required_fields' in data:
                    config.required_fields = data['required_fields']
                if 'optional_fields' in data:
                    config.optional_fields = data['optional_fields']
                if 'field_validation_rules' in data:
                    config.field_validation_rules = data['field_validation_rules']
                if 'field_display_properties' in data:
                    config.field_display_properties = data['field_display_properties']
                if 'evaluation_settings' in data:
                    config.evaluation_settings = data['evaluation_settings']
                
                config.save()
                
                return Response(config.to_dict())
                
        except Exception as e:
            logger.error(f"Error updating evaluation config: {e}")
            return Response(
                {'error': f'Failed to update configuration: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    def destroy(self, request, pk=None):
        """Delete an evaluation configuration"""
        config = get_object_or_404(self.get_queryset(), pk=pk)
        
        # Check if it's used by any projects
        if config.project_usages.exists():
            return Response(
                {'error': 'Cannot delete configuration that is in use by projects'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Don't allow deletion of system defaults
        if config.is_system_default:
            return Response(
                {'error': 'Cannot delete system default configurations'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        config.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
    
    @action(detail=False, methods=['get'])
    def system_defaults(self, request):
        """Get system default configurations"""
        configs = EvaluationFieldConfig.objects.filter(
            is_system_default=True, 
            is_active=True
        ).order_by('name')
        
        data = [config.to_dict() for config in configs]
        return Response(data)


class ProjectEvaluationConfigViewSet(viewsets.ViewSet):
    """
    ViewSet for managing project-specific evaluation configurations
    """
    permission_classes = [IsAuthenticated]
    
    def get_project(self, project_id):
        """Get project with permission check"""
        project = get_object_or_404(Project, id=project_id)
        # Add permission check here if needed
        return project
    
    @action(detail=False, methods=['get'], url_path='project/(?P<project_id>[^/.]+)')
    def get_project_config(self, request, project_id=None):
        """Get evaluation configuration for a specific project"""
        project = self.get_project(project_id)
        
        try:
            project_config = ProjectEvaluationConfig.objects.get(project=project)
            return Response(project_config.to_dict())
        except ProjectEvaluationConfig.DoesNotExist:
            # Return default configuration if no specific config exists
            default_config = EvaluationFieldConfig.objects.filter(
                is_system_default=True,
                is_active=True
            ).first()
            
            if default_config:
                return Response({
                    'project_id': project.id,
                    'evaluation_config': default_config.to_dict(),
                    'effective_required_fields': default_config.required_fields,
                    'effective_optional_fields': default_config.optional_fields,
                    'effective_all_fields': default_config.all_fields,
                    'effective_validation_rules': default_config.field_validation_rules,
                    'is_default': True
                })
            else:
                return Response(
                    {'error': 'No evaluation configuration found for this project'}, 
                    status=status.HTTP_404_NOT_FOUND
                )
    
    @action(detail=False, methods=['post'], url_path='project/(?P<project_id>[^/.]+)/set')
    def set_project_config(self, request, project_id=None):
        """Set evaluation configuration for a specific project"""
        project = self.get_project(project_id)
        data = request.data
        
        try:
            with transaction.atomic():
                eval_config = get_object_or_404(
                    EvaluationFieldConfig, 
                    id=data.get('evaluation_config_id')
                )
                
                # Create or update project configuration
                project_config, created = ProjectEvaluationConfig.objects.get_or_create(
                    project=project,
                    defaults={'evaluation_config': eval_config}
                )
                
                if not created:
                    project_config.evaluation_config = eval_config
                
                # Update custom fields if provided
                if 'custom_required_fields' in data:
                    project_config.custom_required_fields = data['custom_required_fields']
                if 'custom_optional_fields' in data:
                    project_config.custom_optional_fields = data['custom_optional_fields']
                if 'custom_field_validation_rules' in data:
                    project_config.custom_field_validation_rules = data['custom_field_validation_rules']
                
                project_config.save()
                
                return Response(project_config.to_dict())
                
        except Exception as e:
            logger.error(f"Error setting project evaluation config: {e}")
            return Response(
                {'error': f'Failed to set project configuration: {str(e)}'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=False, methods=['delete'], url_path='project/(?P<project_id>[^/.]+)')
    def remove_project_config(self, request, project_id=None):
        """Remove evaluation configuration from a project (reset to default)"""
        project = self.get_project(project_id)
        
        try:
            project_config = ProjectEvaluationConfig.objects.get(project=project)
            project_config.delete()
            return Response({'message': 'Project configuration removed successfully'})
        except ProjectEvaluationConfig.DoesNotExist:
            return Response(
                {'error': 'No configuration found for this project'}, 
                status=status.HTTP_404_NOT_FOUND
            ) 
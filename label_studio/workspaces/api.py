import logging
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from django.contrib.auth import get_user_model
from django.core.exceptions import PermissionDenied

from .models import Workspace, WorkspaceMember
from .serializers import (
    WorkspaceSerializer,
    WorkspaceCreateSerializer,
    WorkspaceUpdateSerializer,
    WorkspaceMemberSerializer
)
from users.serializers import BaseUserSerializer
from projects.serializers import ProjectSerializer
from prompts.serializers import PromptSerializer

logger = logging.getLogger(__name__)
User = get_user_model()


class WorkspaceViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing workspaces
    """
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return WorkspaceCreateSerializer
        elif self.action in ['update', 'partial_update']:
            return WorkspaceUpdateSerializer
        return WorkspaceSerializer
    
    def get_queryset(self):
        user = self.request.user
        organization = user.active_organization
        
        if not organization:
            return Workspace.objects.none()
        
        queryset = Workspace.objects.filter(organization=organization)
        
        # If not superuser, only show workspaces where user is a member
        if not user.is_superuser:
            queryset = queryset.filter(members=user)
        
        # Filter archived workspaces unless specifically requested or for archive action
        show_archived = self.request.query_params.get('archived', 'false').lower() == 'true'
        if not show_archived and self.action != 'archive':
            queryset = queryset.filter(is_archived=False)
            
        return queryset.prefetch_related('members', 'projects', 'created_by').distinct()
    
    def check_admin_permission(self):
        """Check if user has admin permissions (superuser)"""
        if not self.request.user.is_superuser:
            raise PermissionDenied("Only administrators can perform this action")
    
    def perform_create(self, serializer):
        # Only superusers can create workspaces
        self.check_admin_permission()
        workspace = serializer.save()
        # Add creator as a member
        workspace.add_member(self.request.user)
        
    def create(self, request, *args, **kwargs):
        self.check_admin_permission()
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        # Return the full workspace data using the default serializer
        instance = serializer.instance
        response_serializer = WorkspaceSerializer(instance, context={'request': request})
        headers = self.get_success_headers(serializer.data)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        self.check_admin_permission()
        return super().update(request, *args, **kwargs)
    
    def partial_update(self, request, *args, **kwargs):
        self.check_admin_permission()
        return super().partial_update(request, *args, **kwargs)
    
    def destroy(self, request, *args, **kwargs):
        self.check_admin_permission()
        workspace = self.get_object()
        
        # Check if workspace has projects
        project_count = workspace.projects.count()
        if project_count > 0:
            return Response(
                {
                    'error': f'Cannot delete workspace with {project_count} project(s). Please delete or move all projects to another workspace first.'
                }, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['get'])
    def projects(self, request, pk=None):
        """Get projects in this workspace"""
        workspace = self.get_object()
        projects = workspace.projects.all()
        serializer = ProjectSerializer(projects, many=True, context={'request': request})
        return Response(serializer.data)
    
    @action(detail=True, methods=['get'])
    def prompts(self, request, pk=None):
        """Get prompts in this workspace"""
        workspace = self.get_object()
        prompts = workspace.prompts.all()
        # Create a lightweight response with essential info only
        prompts_data = []
        for prompt in prompts:
            # Truncate content for preview (first 100 characters)
            content_preview = prompt.content[:100] + "..." if len(prompt.content) > 100 else prompt.content
            prompts_data.append({
                'id': prompt.id,
                'name': prompt.name,
                'content_preview': content_preview,
                'temperature': prompt.temperature,
                'created_at': prompt.created_at,
                'updated_at': prompt.updated_at,
            })
        return Response(prompts_data)
    
    @action(detail=True, methods=['get'])
    def members(self, request, pk=None):
        """Get workspace members"""
        workspace = self.get_object()
        members = WorkspaceMember.objects.filter(workspace=workspace)
        serializer = WorkspaceMemberSerializer(members, many=True)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def add_member(self, request, pk=None):
        """Add a member to workspace - admin only"""
        self.check_admin_permission()
        workspace = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(pk=user_id)
            # Check if user belongs to the same organization
            if user.active_organization != workspace.organization:
                return Response(
                    {'error': 'User must belong to the same organization'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            workspace.add_member(user)
            return Response({'message': 'Member added successfully'})
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def remove_member(self, request, pk=None):
        """Remove a member from workspace - admin only"""
        self.check_admin_permission()
        workspace = self.get_object()
        user_id = request.data.get('user_id')
        
        if not user_id:
            return Response(
                {'error': 'user_id is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            user = User.objects.get(pk=user_id)
            workspace.remove_member(user)
            return Response({'message': 'Member removed successfully'})
            
        except User.DoesNotExist:
            return Response(
                {'error': 'User not found'}, 
                status=status.HTTP_404_NOT_FOUND
            )
    
    @action(detail=True, methods=['post'])
    def archive(self, request, pk=None):
        """Archive/unarchive workspace - admin only"""
        self.check_admin_permission()
        workspace = self.get_object()
        workspace.is_archived = not workspace.is_archived
        workspace.save()
        
        action_name = 'archived' if workspace.is_archived else 'unarchived'
        return Response({'message': f'Workspace {action_name} successfully'})
    
    @action(detail=False, methods=['get'])
    def archived(self, request):
        """Get archived workspaces"""
        user = request.user
        organization = user.active_organization
        
        if not organization:
            return Response([])
        
        queryset = Workspace.objects.filter(
            organization=organization,
            is_archived=True
        )
        
        # If not superuser, only show workspaces where user is a member
        if not user.is_superuser:
            queryset = queryset.filter(members=user)
        
        workspaces = queryset.prefetch_related('members', 'projects', 'created_by').distinct()
        
        serializer = self.get_serializer(workspaces, many=True)
        return Response(serializer.data) 
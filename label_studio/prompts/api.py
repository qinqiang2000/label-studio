from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Prompt
from .serializers import PromptSerializer
from .permissions import PromptsAccessPermission


class PromptListAPI(generics.ListCreateAPIView):
    """List all prompts or create a new prompt"""
    
    serializer_class = PromptSerializer
    permission_classes = [permissions.IsAuthenticated, PromptsAccessPermission]
    
    def get_queryset(self):
        """Filter prompts based on workspace membership"""
        prompts = Prompt.objects.filter(created_by__active_organization=self.request.user.active_organization)
        
        # Filter prompts based on workspace membership (unless user is superuser)
        if not self.request.user.is_superuser:
            prompts = prompts.filter(
                Q(workspaces__isnull=True) |  # Prompts without any workspaces (organization-wide)
                Q(workspaces__members=self.request.user)  # Prompts in workspaces where user is a member
            ).distinct()  # Use distinct() to avoid duplicates from multiple workspace matches
        
        # Prefetch related data for better performance
        return prompts.prefetch_related('workspaces').select_related('workspace', 'created_by')


class PromptDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a prompt"""
    
    serializer_class = PromptSerializer
    permission_classes = [permissions.IsAuthenticated, PromptsAccessPermission]
    
    def get_queryset(self):
        """Filter prompts based on workspace membership"""
        prompts = Prompt.objects.filter(created_by__active_organization=self.request.user.active_organization)
        
        # Filter prompts based on workspace membership (unless user is superuser)
        if not self.request.user.is_superuser:
            prompts = prompts.filter(
                Q(workspaces__isnull=True) |  # Prompts without any workspaces (organization-wide)
                Q(workspaces__members=self.request.user)  # Prompts in workspaces where user is a member
            ).distinct()  # Use distinct() to avoid duplicates from multiple workspace matches
        
        # Prefetch related data for better performance
        return prompts.prefetch_related('workspaces').select_related('workspace', 'created_by') 
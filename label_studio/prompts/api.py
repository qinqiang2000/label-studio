from rest_framework import generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .models import Prompt
from .serializers import PromptSerializer


class PromptListAPI(generics.ListCreateAPIView):
    """List all prompts or create a new prompt"""
    
    serializer_class = PromptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Return all prompts - they should be available to all users
        # since they are meant to be shared resources
        return Prompt.objects.all()


class PromptDetailAPI(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update or delete a prompt"""
    
    serializer_class = PromptSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Return all prompts for consistency with list view
        return Prompt.objects.all() 
from rest_framework import serializers
from .models import Prompt, PromptWorkspace
from workspaces.models import Workspace
import json


class WorkspaceSerializer(serializers.ModelSerializer):
    """Nested serializer for workspace information"""
    
    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'color']


class PromptWorkspaceSerializer(serializers.ModelSerializer):
    """Serializer for PromptWorkspace through model"""
    workspace = WorkspaceSerializer(read_only=True)
    
    class Meta:
        model = PromptWorkspace
        fields = ['id', 'workspace', 'created_at']


class PromptSerializer(serializers.ModelSerializer):
    """Serializer for Prompt model"""
    # Legacy field for backward compatibility
    workspace = WorkspaceSerializer(read_only=True)
    workspace_id = serializers.PrimaryKeyRelatedField(
        queryset=Workspace.objects.all(),
        source='workspace',
        write_only=True,
        required=False,
        allow_null=True
    )
    
    # New multi-workspace fields
    workspaces = WorkspaceSerializer(many=True, read_only=True)
    workspace_ids = serializers.PrimaryKeyRelatedField(
        queryset=Workspace.objects.all(),
        source='workspaces',
        many=True,
        write_only=True,
        required=False
    )
    
    class Meta:
        model = Prompt
        fields = [
            'id', 'name', 'content', 'temperature', 'response_schema', 
            'created_at', 'updated_at', 'created_by', 
            'workspace', 'workspace_id',  # Legacy fields
            'workspaces', 'workspace_ids'  # New multi-workspace fields
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
        
    def create(self, validated_data):
        # Extract workspaces data before creating the prompt
        workspaces_data = validated_data.pop('workspaces', [])
        
        # Set the created_by field to the current user
        validated_data['created_by'] = self.context['request'].user
        
        # Create the prompt instance
        prompt = super().create(validated_data)
        
        # Add workspaces if provided
        if workspaces_data:
            prompt.workspaces.set(workspaces_data)
        
        return prompt
    
    def update(self, instance, validated_data):
        # Extract workspaces data before updating the prompt
        workspaces_data = validated_data.pop('workspaces', None)
        
        # Update the prompt instance
        prompt = super().update(instance, validated_data)
        
        # Update workspaces if provided
        if workspaces_data is not None:
            prompt.workspaces.set(workspaces_data)
        
        return prompt
        
    def validate_name(self, value):
        """Validate that the name is unique"""
        queryset = Prompt.objects.filter(name=value)
        if self.instance:
            # For updates, exclude the current instance
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A prompt with this name already exists.")
        return value
    
    def validate_temperature(self, value):
        """Validate temperature is within valid range"""
        if value is not None:
            if value < 0.0 or value > 2.0:
                raise serializers.ValidationError("Temperature must be between 0.0 and 2.0")
        return value
    
    def validate_response_schema(self, value):
        """Validate response_schema is valid JSON"""
        if value is not None:
            try:
                # If it's a string, try to parse it as JSON
                if isinstance(value, str):
                    json.loads(value)
                # If it's already a dict, that's fine too
                elif not isinstance(value, dict):
                    raise serializers.ValidationError("Response schema must be valid JSON")
            except json.JSONDecodeError:
                raise serializers.ValidationError("Response schema must be valid JSON")
        return value
    
    def validate_workspace_id(self, value):
        """Validate that user has access to the specified workspace (legacy field)"""
        if value is not None:
            user = self.context['request'].user
            # Superusers can set any workspace
            if user.is_superuser:
                return value
            # Regular users can only set workspaces they are members of
            if not value.has_member(user):
                raise serializers.ValidationError("You don't have permission to use this workspace.")
            # Ensure workspace belongs to user's organization
            if value.organization != user.active_organization:
                raise serializers.ValidationError("Workspace must belong to your organization.")
        return value
    
    def validate_workspace_ids(self, value):
        """Validate that user has access to all specified workspaces"""
        if value:
            user = self.context['request'].user
            # Superusers can set any workspace
            if user.is_superuser:
                return value
            
            # Regular users can only set workspaces they are members of
            for workspace in value:
                if not workspace.has_member(user):
                    raise serializers.ValidationError(
                        f"You don't have permission to use workspace '{workspace.name}'."
                    )
                # Ensure workspace belongs to user's organization
                if workspace.organization != user.active_organization:
                    raise serializers.ValidationError(
                        f"Workspace '{workspace.name}' must belong to your organization."
                    )
        return value 
from rest_framework import serializers
from .models import Workspace, WorkspaceMember
from users.serializers import BaseUserSerializer


class WorkspaceMemberSerializer(serializers.ModelSerializer):
    user = BaseUserSerializer(read_only=True)
    
    class Meta:
        model = WorkspaceMember
        fields = ['id', 'user', 'created_at']


class WorkspaceSerializer(serializers.ModelSerializer):
    member_count = serializers.SerializerMethodField()
    project_count = serializers.SerializerMethodField()
    prompt_count = serializers.SerializerMethodField()
    created_by = BaseUserSerializer(read_only=True)
    members = WorkspaceMemberSerializer(source='workspace_members', many=True, read_only=True)
    
    class Meta:
        model = Workspace
        fields = [
            'id', 'name', 'description', 'color', 'organization', 
            'created_by', 'is_archived', 'created_at', 'updated_at',
            'member_count', 'project_count', 'prompt_count', 'members'
        ]
        read_only_fields = ['organization', 'created_by', 'created_at', 'updated_at']
    
    def get_member_count(self, obj):
        return obj.members.count()
    
    def get_project_count(self, obj):
        return obj.projects.count()
    
    def get_prompt_count(self, obj):
        return obj.prompts.count()


class WorkspaceCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ['name', 'description', 'color']
        
    def create(self, validated_data):
        request = self.context.get('request')
        validated_data['organization'] = request.user.active_organization
        validated_data['created_by'] = request.user
        return super().create(validated_data)


class WorkspaceUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Workspace
        fields = ['name', 'description', 'color', 'is_archived'] 
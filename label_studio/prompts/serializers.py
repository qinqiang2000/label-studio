from rest_framework import serializers
from .models import Prompt
from workspaces.models import Workspace
import json


class WorkspaceSerializer(serializers.ModelSerializer):
    """Nested serializer for workspace information"""

    class Meta:
        model = Workspace
        fields = ['id', 'name', 'description', 'color']


class PromptSerializer(serializers.ModelSerializer):
    """Serializer for Prompt model. Each prompt belongs to exactly one workspace."""

    workspace = WorkspaceSerializer(read_only=True)
    workspace_id = serializers.PrimaryKeyRelatedField(
        queryset=Workspace.objects.all(),
        source='workspace',
        write_only=True,
        required=False,
        allow_null=False,
    )

    # Backward-compat: emit a single-element list so existing UI keeps rendering.
    workspaces = serializers.SerializerMethodField()

    class Meta:
        model = Prompt
        fields = [
            'id', 'name', 'content', 'temperature', 'thinking_budget', 'response_schema',
            'created_at', 'updated_at', 'created_by',
            'workspace', 'workspace_id', 'workspaces',
        ]
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']

    def get_workspaces(self, obj):
        if obj.workspace_id is None:
            return []
        return [WorkspaceSerializer(obj.workspace).data]

    def _user_workspaces(self, user):
        from workspaces.models import WorkspaceMember
        return list(
            Workspace.objects.filter(
                id__in=WorkspaceMember.objects.filter(user=user).values('workspace_id')
            )
        )

    def create(self, validated_data):
        user = self.context['request'].user
        validated_data['created_by'] = user

        if 'workspace' not in validated_data or validated_data['workspace'] is None:
            if user.is_superuser:
                raise serializers.ValidationError(
                    {'workspace_id': '超级管理员创建 Prompt 时必须显式指定 workspace_id。'}
                )
            user_ws = self._user_workspaces(user)
            if len(user_ws) == 0:
                raise serializers.ValidationError(
                    {'workspace_id': '当前账号未绑定任何 Workspace，无法创建 Prompt。'}
                )
            if len(user_ws) > 1:
                raise serializers.ValidationError(
                    {'workspace_id': f'当前账号属于 {len(user_ws)} 个 Workspace，请显式指定 workspace_id。'}
                )
            validated_data['workspace'] = user_ws[0]

        return super().create(validated_data)

    def validate_name(self, value):
        queryset = Prompt.objects.filter(name=value)
        if self.instance:
            queryset = queryset.exclude(pk=self.instance.pk)

        if queryset.exists():
            raise serializers.ValidationError("A prompt with this name already exists.")
        return value

    def validate_temperature(self, value):
        if value is not None and (value < 0.0 or value > 2.0):
            raise serializers.ValidationError("Temperature must be between 0.0 and 2.0")
        return value

    def validate_thinking_budget(self, value):
        if value is not None and value < 0:
            raise serializers.ValidationError("Thinking budget must be 0 or a positive integer")
        return value

    def validate_response_schema(self, value):
        if value is not None:
            try:
                if isinstance(value, str):
                    json.loads(value)
                elif not isinstance(value, dict):
                    raise serializers.ValidationError("Response schema must be valid JSON")
            except json.JSONDecodeError:
                raise serializers.ValidationError("Response schema must be valid JSON")
        return value

    def validate_workspace_id(self, value):
        if value is None:
            return value
        user = self.context['request'].user
        if user.is_superuser:
            return value
        if not value.has_member(user):
            raise serializers.ValidationError("You don't have permission to use this workspace.")
        return value

from rest_framework import serializers
from .models import Prompt


class PromptSerializer(serializers.ModelSerializer):
    """Serializer for Prompt model"""
    
    class Meta:
        model = Prompt
        fields = ['id', 'name', 'content', 'created_at', 'updated_at', 'created_by']
        read_only_fields = ['id', 'created_at', 'updated_at', 'created_by']
        
    def create(self, validated_data):
        # Set the created_by field to the current user
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)
        
    def validate_name(self, value):
        """Validate that the name is unique"""
        queryset = Prompt.objects.filter(name=value)
        if self.instance:
            # For updates, exclude the current instance
            queryset = queryset.exclude(pk=self.instance.pk)
        
        if queryset.exists():
            raise serializers.ValidationError("A prompt with this name already exists.")
        return value 
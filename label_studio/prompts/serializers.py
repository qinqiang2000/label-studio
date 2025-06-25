from rest_framework import serializers
from .models import Prompt
import json


class PromptSerializer(serializers.ModelSerializer):
    """Serializer for Prompt model"""
    
    class Meta:
        model = Prompt
        fields = ['id', 'name', 'content', 'temperature', 'response_schema', 'created_at', 'updated_at', 'created_by']
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
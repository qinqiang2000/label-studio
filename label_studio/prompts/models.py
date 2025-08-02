from django.db import models
from django.conf import settings
import json


class Prompt(models.Model):
    """Model for storing prompts"""
    
    name = models.CharField(max_length=255, unique=True, help_text="Name of the prompt")
    content = models.TextField(help_text="The actual prompt content")
    temperature = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Temperature for AI model response (0.0-2.0). Controls randomness: lower is more deterministic."
    )
    response_schema = models.JSONField(
        null=True, 
        blank=True, 
        help_text="JSON schema for structured AI model response format"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prompts',
        help_text="User who created this prompt"
    )
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.SET_NULL,
        related_name='prompts',
        null=True,
        blank=True,
        help_text='Workspace this prompt belongs to'
    )
    
    class Meta:
        ordering = ['-updated_at']
        
    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError
        
        # Validate temperature range
        if self.temperature is not None:
            if self.temperature < 0.0 or self.temperature > 2.0:
                raise ValidationError("Temperature must be between 0.0 and 2.0")
        
        # Validate response_schema is valid JSON
        if self.response_schema is not None:
            try:
                if isinstance(self.response_schema, str):
                    json.loads(self.response_schema)
            except (json.JSONDecodeError, TypeError):
                raise ValidationError("Response schema must be valid JSON")

    def get_runtime_config(self):
        """Get runtime config for ML backend"""
        runtime_config = {}
        
        if self.temperature is not None:
            runtime_config['temperature'] = self.temperature
            
        if self.response_schema is not None:
            runtime_config['response_schema'] = self.response_schema
            
        return runtime_config if runtime_config else None

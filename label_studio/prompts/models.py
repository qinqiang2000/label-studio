from django.db import models
from django.conf import settings
import json


class Prompt(models.Model):
    """Prompt 资产。每条 Prompt 归属一个 Workspace（租户隔离边界）。"""

    name = models.CharField(max_length=255, unique=True, help_text="Name of the prompt")
    content = models.TextField(help_text="The actual prompt content")
    temperature = models.FloatField(
        null=True,
        blank=True,
        help_text="Temperature for AI model response (0.0-2.0). Controls randomness: lower is more deterministic.",
    )
    thinking_budget = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        help_text="Thinking budget for AI model (0 or positive integer). Controls deep thinking computation.",
    )
    response_schema = models.JSONField(
        null=True,
        blank=True,
        help_text="JSON schema for structured AI model response format",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prompts',
        help_text='User who created this prompt',
    )
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.PROTECT,
        related_name='prompts',
        help_text='Workspace that owns this prompt (tenant boundary)',
    )

    class Meta:
        ordering = ['-updated_at']

    def __str__(self):
        return self.name

    def clean(self):
        from django.core.exceptions import ValidationError

        if self.temperature is not None and (self.temperature < 0.0 or self.temperature > 2.0):
            raise ValidationError("Temperature must be between 0.0 and 2.0")

        if self.thinking_budget is not None and self.thinking_budget < 0:
            raise ValidationError("Thinking budget must be 0 or a positive integer")

        if self.response_schema is not None and isinstance(self.response_schema, str):
            try:
                json.loads(self.response_schema)
            except (json.JSONDecodeError, TypeError):
                raise ValidationError("Response schema must be valid JSON")

    def get_runtime_config(self):
        """Get runtime config for ML backend"""
        runtime_config = {}

        if self.temperature is not None:
            runtime_config['temperature'] = self.temperature

        if self.thinking_budget is not None and self.thinking_budget > 0:
            runtime_config['thinking_budget'] = self.thinking_budget

        if self.response_schema is not None:
            runtime_config['response_schema'] = self.response_schema

        return runtime_config or None

from django.db import models
from django.conf import settings
import json


class PromptWorkspace(models.Model):
    """Through model for prompt-workspace many-to-many relationship"""
    
    prompt = models.ForeignKey(
        'Prompt',
        on_delete=models.CASCADE,
        related_name='prompt_workspaces',
        help_text='Prompt'
    )
    
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.CASCADE,
        related_name='workspace_prompts',
        help_text='Workspace'
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        db_table = 'prompt_workspace'
        unique_together = ['prompt', 'workspace']
        
    def __str__(self):
        return f"{self.prompt.name} - {self.workspace.name}"


class Prompt(models.Model):
    """Model for storing prompts"""
    
    name = models.CharField(max_length=255, unique=True, help_text="Name of the prompt")
    content = models.TextField(help_text="The actual prompt content")
    temperature = models.FloatField(
        null=True, 
        blank=True, 
        help_text="Temperature for AI model response (0.0-2.0). Controls randomness: lower is more deterministic."
    )
    thinking_budget = models.IntegerField(
        null=True,
        blank=True,
        default=0,
        help_text="Thinking budget for AI model (0 or positive integer). Controls deep thinking computation."
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
    # Legacy field - kept for migration compatibility, will be removed after migration
    workspace = models.ForeignKey(
        'workspaces.Workspace',
        on_delete=models.SET_NULL,
        related_name='legacy_prompts',
        null=True,
        blank=True,
        help_text='Legacy single workspace field - use workspaces instead'
    )
    
    workspaces = models.ManyToManyField(
        'workspaces.Workspace',
        through='PromptWorkspace',
        related_name='prompts',
        blank=True,
        help_text='Workspaces this prompt belongs to'
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
        
        # Validate thinking_budget range
        if self.thinking_budget is not None:
            if self.thinking_budget < 0:
                raise ValidationError("Thinking budget must be 0 or a positive integer")
        
        # Validate response_schema is valid JSON
        if self.response_schema is not None:
            try:
                if isinstance(self.response_schema, str):
                    json.loads(self.response_schema)
            except (json.JSONDecodeError, TypeError):
                raise ValidationError("Response schema must be valid JSON")

    def has_workspace(self, workspace):
        """Check if prompt belongs to the specified workspace"""
        return self.workspaces.filter(pk=workspace.pk).exists()
    
    def add_workspace(self, workspace):
        """Add workspace to this prompt"""
        if not self.has_workspace(workspace):
            PromptWorkspace.objects.create(
                prompt=self,
                workspace=workspace
            )
    
    def remove_workspace(self, workspace):
        """Remove workspace from this prompt"""
        PromptWorkspace.objects.filter(
            prompt=self,
            workspace=workspace
        ).delete()
    
    def get_workspace_ids(self):
        """Get list of workspace IDs this prompt belongs to"""
        return list(self.workspaces.values_list('pk', flat=True))

    def get_runtime_config(self):
        """Get runtime config for ML backend"""
        runtime_config = {}
        
        if self.temperature is not None:
            runtime_config['temperature'] = self.temperature
            
        if self.thinking_budget is not None and self.thinking_budget > 0:
            # Send thinking_budget as integer value - ML backend will create ThinkingConfig
            runtime_config['thinking_budget'] = self.thinking_budget
            
        if self.response_schema is not None:
            runtime_config['response_schema'] = self.response_schema
            
        return runtime_config if runtime_config else None

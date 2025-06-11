from django.db import models
from django.conf import settings


class Prompt(models.Model):
    """Model for storing prompts"""
    
    name = models.CharField(max_length=255, unique=True, help_text="Name of the prompt")
    content = models.TextField(help_text="The actual prompt content")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='prompts',
        help_text="User who created this prompt"
    )
    
    class Meta:
        ordering = ['-updated_at']
        
    def __str__(self):
        return self.name

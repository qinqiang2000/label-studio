from django.db import models
from django.conf import settings
from organizations.models import Organization
import json


class EvaluationFieldConfig(models.Model):
    """
    Evaluation Field Configuration model for storing document type evaluation configurations
    """
    name = models.CharField(max_length=255, help_text="Configuration name (e.g., 'Invoice', 'Bank Receipt')")
    key = models.CharField(max_length=100, unique=True, help_text="Unique key for this configuration (e.g., 'invoice', 'bank_receipt')")
    description = models.TextField(blank=True, help_text="Description of what this configuration is used for")
    
    # Field configuration
    required_fields = models.JSONField(default=list, help_text="List of required fields for this document type")
    optional_fields = models.JSONField(default=list, help_text="List of optional fields for this document type")
    
    # Field validation rules
    field_validation_rules = models.JSONField(default=dict, help_text="Validation rules for specific fields")
    
    # Field display properties
    field_display_properties = models.JSONField(default=dict, help_text="Display properties for fields (e.g., labels, types)")
    
    # Evaluation settings
    evaluation_settings = models.JSONField(default=dict, help_text="Settings for evaluation logic")
    
    # Metadata
    is_active = models.BooleanField(default=True, help_text="Whether this configuration is active")
    is_system_default = models.BooleanField(default=False, help_text="Whether this is a system default configuration")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_eval_configs')
    
    # Organization scope (optional - for multi-tenant support)
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, null=True, blank=True, related_name='evaluation_configs')
    
    class Meta:
        db_table = 'evaluation_field_configs'
        ordering = ['name']
        indexes = [
            models.Index(fields=['key']),
            models.Index(fields=['is_active']),
            models.Index(fields=['organization']),
        ]
    
    def __str__(self):
        return f"{self.name} ({self.key})"
    
    @property
    def all_fields(self):
        """Get all fields (required + optional)"""
        return list(set(self.required_fields + self.optional_fields))
    
    @property
    def field_labels(self):
        """Get field labels from display properties"""
        return self.field_display_properties.get('labels', {})
    
    @property
    def field_types(self):
        """Get field types from display properties"""
        return self.field_display_properties.get('types', {})
    
    def get_field_label(self, field_name):
        """Get display label for a specific field"""
        return self.field_labels.get(field_name, field_name)
    
    def get_field_type(self, field_name):
        """Get field type for a specific field"""
        return self.field_types.get(field_name, 'string')
    
    def is_field_required(self, field_name):
        """Check if a field is required"""
        return field_name in self.required_fields
    
    def get_validation_rule(self, field_name):
        """Get validation rule for a specific field"""
        return self.field_validation_rules.get(field_name, {})
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'name': self.name,
            'key': self.key,
            'description': self.description,
            'required_fields': self.required_fields,
            'optional_fields': self.optional_fields,
            'all_fields': self.all_fields,
            'field_labels': self.field_labels,
            'field_types': self.field_types,
            'field_validation_rules': self.field_validation_rules,
            'evaluation_settings': self.evaluation_settings,
            'is_active': self.is_active,
            'is_system_default': self.is_system_default,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        }


class ProjectEvaluationConfig(models.Model):
    """
    Link between projects and evaluation field configurations
    """
    project = models.OneToOneField(
        'projects.Project', 
        on_delete=models.CASCADE, 
        related_name='evaluation_field_configuration'
    )
    evaluation_config = models.ForeignKey(
        EvaluationFieldConfig, 
        on_delete=models.CASCADE,
        related_name='project_usages'
    )
    
    # Project-specific overrides
    custom_required_fields = models.JSONField(default=list, blank=True, help_text="Project-specific required fields override")
    custom_optional_fields = models.JSONField(default=list, blank=True, help_text="Project-specific optional fields override")
    custom_field_validation_rules = models.JSONField(default=dict, blank=True, help_text="Project-specific validation rules override")
    
    # Audit fields
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'project_evaluation_configs'
        indexes = [
            models.Index(fields=['project']),
            models.Index(fields=['evaluation_config']),
        ]
    
    def __str__(self):
        return f"Project {self.project.title} -> {self.evaluation_config.name}"
    
    @property
    def effective_required_fields(self):
        """Get effective required fields (custom or default)"""
        return self.custom_required_fields if self.custom_required_fields else self.evaluation_config.required_fields
    
    @property
    def effective_optional_fields(self):
        """Get effective optional fields (custom or default)"""
        return self.custom_optional_fields if self.custom_optional_fields else self.evaluation_config.optional_fields
    
    @property
    def effective_all_fields(self):
        """Get all effective fields"""
        return list(set(self.effective_required_fields + self.effective_optional_fields))
    
    @property
    def effective_validation_rules(self):
        """Get effective validation rules (merged custom and default)"""
        rules = self.evaluation_config.field_validation_rules.copy()
        rules.update(self.custom_field_validation_rules)
        return rules
    
    def to_dict(self):
        """Convert to dictionary for API responses"""
        return {
            'id': self.id,
            'project_id': self.project.id,
            'evaluation_config': self.evaluation_config.to_dict(),
            'effective_required_fields': self.effective_required_fields,
            'effective_optional_fields': self.effective_optional_fields,
            'effective_all_fields': self.effective_all_fields,
            'effective_validation_rules': self.effective_validation_rules,
            'custom_required_fields': self.custom_required_fields,
            'custom_optional_fields': self.custom_optional_fields,
            'custom_field_validation_rules': self.custom_field_validation_rules,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
        } 
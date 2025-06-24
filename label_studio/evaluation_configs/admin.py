from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import EvaluationFieldConfig, ProjectEvaluationConfig
import json


@admin.register(EvaluationFieldConfig)
class EvaluationFieldConfigAdmin(admin.ModelAdmin):
    list_display = ('name', 'key', 'required_fields_display', 'optional_fields_display', 'is_active', 'is_system_default', 'created_at')
    list_filter = ('is_active', 'is_system_default', 'created_at')
    search_fields = ('name', 'key', 'description')
    readonly_fields = ('created_at', 'updated_at', 'created_by')
    
    fieldsets = (
        ('基本信息', {
            'fields': ('name', 'key', 'description', 'is_active', 'is_system_default')
        }),
        ('字段配置', {
            'fields': ('required_fields', 'optional_fields'),
            'description': '必填字段：验证时必须存在的字段；可选字段：验证时可有可无的字段'
        }),
        ('验证规则', {
            'fields': ('field_validation_rules',),
            'classes': ('collapse',),
            'description': '为特定字段定义验证规则（JSON格式）'
        }),
        ('显示属性', {
            'fields': ('field_display_properties',),
            'classes': ('collapse',),
            'description': '字段的显示属性，如标签和类型（JSON格式）'
        }),
        ('评估设置', {
            'fields': ('evaluation_settings',),
            'classes': ('collapse',),
            'description': '评估相关的设置（JSON格式）'
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at', 'created_by'),
            'classes': ('collapse',)
        })
    )
    
    def required_fields_display(self, obj):
        """显示必填字段"""
        if obj.required_fields:
            fields_html = ', '.join([f'<span style="background: #e8f4fd; padding: 2px 6px; border-radius: 3px; font-family: monospace;">{field}</span>' for field in obj.required_fields])
            return mark_safe(fields_html)
        return '-'
    required_fields_display.short_description = '必填字段'
    
    def optional_fields_display(self, obj):
        """显示可选字段"""
        if obj.optional_fields:
            fields_html = ', '.join([f'<span style="background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-family: monospace;">{field}</span>' for field in obj.optional_fields])
            return mark_safe(fields_html)
        return '-'
    optional_fields_display.short_description = '可选字段'
    
    def save_model(self, request, obj, form, change):
        if not change:  # 新建时
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

    class Meta:
        verbose_name = '评估字段配置'
        verbose_name_plural = '评估字段配置'


@admin.register(ProjectEvaluationConfig)
class ProjectEvaluationConfigAdmin(admin.ModelAdmin):
    list_display = ('project', 'evaluation_config', 'effective_required_fields_display', 'created_at')
    list_filter = ('evaluation_config', 'created_at')
    search_fields = ('project__title', 'evaluation_config__name')
    readonly_fields = ('created_at', 'updated_at')
    
    fieldsets = (
        ('项目关联', {
            'fields': ('project', 'evaluation_config')
        }),
        ('自定义字段配置', {
            'fields': ('custom_required_fields', 'custom_optional_fields'),
            'description': '可以覆盖基础配置的字段设置。如果留空，将使用基础配置的字段设置。'
        }),
        ('自定义验证规则', {
            'fields': ('custom_field_validation_rules',),
            'classes': ('collapse',),
            'description': '项目特定的验证规则覆盖（JSON格式）'
        }),
        ('元数据', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        })
    )
    
    def effective_required_fields_display(self, obj):
        """显示有效的必填字段"""
        fields = obj.effective_required_fields
        if fields:
            fields_html = ', '.join([f'<span style="background: #e8f4fd; padding: 2px 6px; border-radius: 3px; font-family: monospace;">{field}</span>' for field in fields])
            return mark_safe(fields_html)
        return '-'
    effective_required_fields_display.short_description = '有效必填字段'
    
    class Meta:
        verbose_name = '项目评估配置'
        verbose_name_plural = '项目评估配置' 
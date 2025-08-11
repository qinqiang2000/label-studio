from django.contrib import admin
from core.admin import superuser_admin_site

from .models import ModelInterface, ModelRun, ThirdPartyModelVersion


class ModelInterfaceAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'skill_name',
        'organization',
        'created_by',
        'created_at',
        'updated_at',
    )
    list_filter = ('skill_name', 'organization')
    search_fields = ('title', 'description')
    readonly_fields = ('created_at', 'updated_at')
    filter_horizontal = ('associated_projects',)
    fieldsets = (
        ('Model Details', {'fields': ('title', 'description', 'skill_name')}),
        ('Organization', {'fields': ('organization', 'created_by')}),
        (
            'Configuration',
            {'fields': ('input_fields', 'output_classes', 'associated_projects')},
        ),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


class ThirdPartyModelVersionAdmin(admin.ModelAdmin):
    list_display = (
        'title',
        'parent_model',
        'provider',
        'provider_model_id',
        'organization',
        'created_at',
    )
    list_filter = ('provider', 'organization')
    search_fields = ('title', 'provider_model_id', 'prompt')
    readonly_fields = ('created_at', 'updated_at')
    fieldsets = (
        ('Version Details', {'fields': ('title', 'parent_model', 'prompt')}),
        (
            'Provider Details',
            {'fields': ('provider', 'provider_model_id', 'model_provider_connection')},
        ),
        ('Organization', {'fields': ('organization', 'created_by')}),
        ('Timestamps', {'fields': ('created_at', 'updated_at')}),
    )


class ModelRunAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'model_version',
        'project',
        'status',
        'created_by',
        'created_at',
        'completed_at',
    )
    list_filter = ('status', 'project_subset')
    search_fields = ('job_id',)
    readonly_fields = (
        'created_at',
        'triggered_at',
        'predictions_updated_at',
        'completed_at',
        'total_predictions',
        'total_correct_predictions',
        'total_tasks',
    )
    fieldsets = (
        (
            'Run Details',
            {
                'fields': (
                    'model_version',
                    'project',
                    'project_subset',
                    'status',
                    'job_id',
                )
            },
        ),
        ('Organization', {'fields': ('organization', 'created_by')}),
        (
            'Statistics',
            {
                'fields': (
                    'total_predictions',
                    'total_correct_predictions',
                    'total_tasks',
                )
            },
        ),
        (
            'Timestamps',
            {
                'fields': (
                    'created_at',
                    'triggered_at',
                    'predictions_updated_at',
                    'completed_at',
                )
            },
        ),
    )

    actions = ['delete_model_run_predictions']

    def delete_model_run_predictions(self, request, queryset):
        for model_run in queryset:
            model_run.delete_predictions()
        self.message_user(request, f'Deleted predictions for {queryset.count()} model runs.')

    delete_model_run_predictions.short_description = 'Delete predictions for selected model runs'


# 注册到自定义的超级用户专用 admin site
superuser_admin_site.register(ModelInterface, ModelInterfaceAdmin)
superuser_admin_site.register(ThirdPartyModelVersion, ThirdPartyModelVersionAdmin)
superuser_admin_site.register(ModelRun, ModelRunAdmin)

# 保留默认 admin.site 的注册（以防其他地方有依赖）
admin.site.register(ModelInterface, ModelInterfaceAdmin)
admin.site.register(ThirdPartyModelVersion, ThirdPartyModelVersionAdmin)
admin.site.register(ModelRun, ModelRunAdmin)

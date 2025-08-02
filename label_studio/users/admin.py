"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
from core.models import AsyncMigrationStatus
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from ml.models import MLBackend, MLBackendTrainJob
from organizations.models import Organization, OrganizationMember
from projects.models import Project
from tasks.models import Annotation, Prediction, Task
from users.models import User, Role, Permission, RolePermission


class UserAdminShort(UserAdmin):

    add_fieldsets = ((None, {'fields': ('email', 'password1', 'password2')}),)

    def __init__(self, *args, **kwargs):
        super(UserAdminShort, self).__init__(*args, **kwargs)

        self.list_display = (
            'email',
            'username',
            'role',
            'active_organization',
            'organization',
            'is_staff',
            'is_superuser',
        )
        self.list_filter = ('is_staff', 'is_superuser', 'is_active', 'role')
        self.search_fields = (
            'username',
            'first_name',
            'last_name',
            'email',
            'organization__title',
            'active_organization__title',
        )
        self.ordering = ('email',)

        self.fieldsets = (
            (None, {'fields': ('password',)}),
            ('Personal info', {'fields': ('email', 'username', 'first_name', 'last_name')}),
            (
                'Permissions',
                {
                    'fields': (
                        'is_active',
                        'is_staff',
                        'is_superuser',
                        'role',
                    )
                },
            ),
            ('Important dates', {'fields': ('last_login', 'date_joined')}),
        )


class AsyncMigrationStatusAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super(AsyncMigrationStatusAdmin, self).__init__(*args, **kwargs)

        self.list_display = ('id', 'name', 'project', 'status', 'created_at', 'updated_at', 'meta')
        self.list_filter = ('name', 'status')
        self.search_fields = ('name', 'project__id')
        self.ordering = ('id',)


class OrganizationMemberAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super(OrganizationMemberAdmin, self).__init__(*args, **kwargs)

        self.list_display = ('id', 'user', 'organization', 'created_at', 'updated_at')
        self.search_fields = ('user__email', 'organization__title')
        self.ordering = ('id',)


class RoleAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super(RoleAdmin, self).__init__(*args, **kwargs)

        self.list_display = ('id', 'name', 'display_name', 'description', 'is_active', 'created_at')
        self.list_filter = ('is_active',)
        self.search_fields = ('name', 'display_name')
        self.ordering = ('name',)


class PermissionAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super(PermissionAdmin, self).__init__(*args, **kwargs)

        self.list_display = ('id', 'name', 'display_name', 'category', 'is_active', 'created_at')
        self.list_filter = ('category', 'is_active')
        self.search_fields = ('name', 'display_name')
        self.ordering = ('category', 'name')
        
    def get_form(self, request, obj=None, **kwargs):
        """自定义表单，显示更友好的帮助信息"""
        form = super().get_form(request, obj, **kwargs)
        if 'name' in form.base_fields:
            form.base_fields['name'].help_text = '权限的英文标识符，如: view_home, create_project'
        if 'display_name' in form.base_fields:
            form.base_fields['display_name'].help_text = '权限的中文显示名称，如: Home菜单查看'
        return form


class RolePermissionAdmin(admin.ModelAdmin):
    def __init__(self, *args, **kwargs):
        super(RolePermissionAdmin, self).__init__(*args, **kwargs)

        self.list_display = ('id', 'role', 'permission_detail', 'granted', 'created_at')
        self.list_filter = ('granted', 'role', 'permission__category')
        self.search_fields = ('role__name', 'permission__name', 'permission__display_name')
        self.ordering = ('role', 'permission')
    
    def permission_detail(self, obj):
        """显示权限的详细信息：英文名 + 中文名"""
        return f"{obj.permission.name} ({obj.permission.display_name})"
    permission_detail.short_description = '权限详情'


admin.site.register(User, UserAdminShort)
admin.site.register(Role, RoleAdmin)
admin.site.register(Permission, PermissionAdmin)
admin.site.register(RolePermission, RolePermissionAdmin)
admin.site.register(Project)
admin.site.register(MLBackend)
admin.site.register(MLBackendTrainJob)
admin.site.register(Task)
admin.site.register(Annotation)
admin.site.register(Prediction)
admin.site.register(Organization)
admin.site.register(OrganizationMember, OrganizationMemberAdmin)
admin.site.register(AsyncMigrationStatus, AsyncMigrationStatusAdmin)

# remove unused django groups
admin.site.unregister(Group)

"""This file and its contents are licensed under the Apache License 2.0. Please see the included NOTICE for copyright information and LICENSE for a copy of the license.
"""
from core.models import AsyncMigrationStatus
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import Group
from django.urls import path
from django.http import HttpResponseRedirect
from django.shortcuts import render
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

        self.list_display = ('id', 'name', 'display_name', 'permission_count', 'user_count', 'is_active', 'created_at')
        self.list_filter = ('is_active',)
        self.search_fields = ('name', 'display_name')
        self.ordering = ('name',)
        self.actions = [
            'add_project_creation_permissions', 
            'add_workspace_management_permissions',
            'add_annotation_permissions',
            'add_admin_full_permissions',
            'clone_role_permissions'
        ]
    
    def permission_count(self, obj):
        """显示角色拥有的权限数量"""
        return obj.rolepermission_set.filter(granted=True).count()
    permission_count.short_description = '权限数量'
    
    def user_count(self, obj):
        """显示拥有此角色的用户数量"""
        return obj.users.count()
    user_count.short_description = '用户数量'
    
    def _add_permission_group(self, request, queryset, permissions, group_name):
        """为角色添加权限组的通用方法"""
        from .models import Permission, RolePermission
        
        added_count = 0
        for role in queryset:
            for perm_name in permissions:
                try:
                    permission = Permission.objects.get(name=perm_name)
                    role_perm, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                        defaults={'granted': True}
                    )
                    if created or not role_perm.granted:
                        role_perm.granted = True
                        role_perm.save()
                        added_count += 1
                except Permission.DoesNotExist:
                    continue
        
        self.message_user(request, f'成功为 {queryset.count()} 个角色添加 {added_count} 个{group_name}权限')
    
    def add_project_creation_permissions(self, request, queryset):
        """为选中角色添加项目创建权限"""
        project_permissions = [
            'create_project',
            'show_create_project_button'
        ]
        self._add_permission_group(request, queryset, project_permissions, '项目创建')
    add_project_creation_permissions.short_description = '添加项目创建权限'
    
    def add_workspace_management_permissions(self, request, queryset):
        """为选中角色添加工作空间管理权限"""
        workspace_permissions = [
            'create_workspace',
            'edit_workspace', 
            'delete_workspace',
            'show_create_workspace_button',
            'show_edit_workspace_button',
            'show_delete_workspace_button'
        ]
        self._add_permission_group(request, queryset, workspace_permissions, '工作空间管理')
    add_workspace_management_permissions.short_description = '添加工作空间管理权限'
    
    def add_annotation_permissions(self, request, queryset):
        """为选中角色添加标注权限"""
        annotation_permissions = [
            'view_annotations',
            'create_annotation',
            'edit_annotation',
            'delete_annotation',
            'submit_annotation',
            'skip_annotation'
        ]
        self._add_permission_group(request, queryset, annotation_permissions, '标注')
    add_annotation_permissions.short_description = '添加标注权限'
    
    def add_admin_full_permissions(self, request, queryset):
        """为选中角色添加管理员完整权限"""
        from .models import Permission
        
        # 获取所有活跃权限
        all_permissions = Permission.objects.filter(is_active=True).values_list('name', flat=True)
        self._add_permission_group(request, queryset, list(all_permissions), '管理员完整')
    add_admin_full_permissions.short_description = '添加管理员完整权限'
    
    def clone_role_permissions(self, request, queryset):
        """克隆角色权限到其他角色"""
        if queryset.count() < 2:
            self.message_user(request, '需要选择至少2个角色才能进行权限克隆', level='warning')
            return
        
        from .models import Permission, RolePermission
        
        # 使用第一个角色作为源角色
        source_role = queryset.first()
        target_roles = queryset.exclude(id=source_role.id)
        
        # 获取源角色的所有权限
        source_permissions = RolePermission.objects.filter(
            role=source_role, 
            granted=True
        ).values_list('permission__name', flat=True)
        
        added_count = 0
        for target_role in target_roles:
            for perm_name in source_permissions:
                try:
                    permission = Permission.objects.get(name=perm_name)
                    role_perm, created = RolePermission.objects.get_or_create(
                        role=target_role,
                        permission=permission,
                        defaults={'granted': True}
                    )
                    if created or not role_perm.granted:
                        role_perm.granted = True
                        role_perm.save()
                        added_count += 1
                except Permission.DoesNotExist:
                    continue
        
        self.message_user(
            request, 
            f'成功将角色 "{source_role.display_name}" 的权限克隆到 {target_roles.count()} 个其他角色，共添加 {added_count} 个权限'
        )
    clone_role_permissions.short_description = '克隆权限（以第一个选中角色为源）'


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
        self.actions = [
            'grant_permission', 
            'revoke_permission', 
            'bulk_add_menu_permissions',
            'bulk_add_action_permissions',
            'bulk_add_admin_permissions',
            'bulk_add_page_operation_permissions'
        ]
    
    def permission_detail(self, obj):
        """显示权限的详细信息：英文名 + 中文名"""
        return f"{obj.permission.name} ({obj.permission.display_name})"
    permission_detail.short_description = '权限详情'
    
    def grant_permission(self, request, queryset):
        """批量授予权限"""
        updated = queryset.update(granted=True)
        self.message_user(request, f'成功授予 {updated} 个权限')
    grant_permission.short_description = '授予选中的权限'
    
    def revoke_permission(self, request, queryset):
        """批量撤销权限"""
        updated = queryset.update(granted=False)
        self.message_user(request, f'成功撤销 {updated} 个权限')
    revoke_permission.short_description = '撤销选中的权限'
    
    def _bulk_add_permissions_by_category(self, request, queryset, category, category_name):
        """按类别批量添加权限的通用方法"""
        from .models import Role, Permission, RolePermission
        
        # 获取该类别的所有权限
        permissions = Permission.objects.filter(category=category, is_active=True)
        permission_names = list(permissions.values_list('name', flat=True))
        
        if not permission_names:
            self.message_user(request, f'没有找到 {category_name} 类别的权限')
            return
        
        # 获取涉及的角色
        roles = Role.objects.filter(
            rolepermission__in=queryset
        ).distinct()
        
        added_count = 0
        for role in roles:
            for perm_name in permission_names:
                try:
                    permission = Permission.objects.get(name=perm_name)
                    role_perm, created = RolePermission.objects.get_or_create(
                        role=role,
                        permission=permission,
                        defaults={'granted': True}
                    )
                    if created or not role_perm.granted:
                        role_perm.granted = True
                        role_perm.save()
                        added_count += 1
                except Permission.DoesNotExist:
                    continue
        
        self.message_user(request, f'成功为 {roles.count()} 个角色添加 {added_count} 个{category_name}权限')
    
    def bulk_add_menu_permissions(self, request, queryset):
        """为角色批量添加菜单权限"""
        self._bulk_add_permissions_by_category(request, queryset, 'menu', '菜单')
    bulk_add_menu_permissions.short_description = '添加菜单权限包'
    
    def bulk_add_action_permissions(self, request, queryset):
        """为角色批量添加操作权限"""
        self._bulk_add_permissions_by_category(request, queryset, 'action', '操作')
    bulk_add_action_permissions.short_description = '添加操作权限包'
    
    def bulk_add_admin_permissions(self, request, queryset):
        """为角色批量添加管理权限"""
        self._bulk_add_permissions_by_category(request, queryset, 'admin', '管理')
    bulk_add_admin_permissions.short_description = '添加管理权限包'
    
    def bulk_add_page_operation_permissions(self, request, queryset):
        """为角色批量添加页面操作权限"""
        self._bulk_add_permissions_by_category(request, queryset, 'page_operation', '页面操作')
    bulk_add_page_operation_permissions.short_description = '添加页面操作权限包'


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

# 自定义admin站点设置
admin.site.site_header = 'Label Studio 管理后台'
admin.site.site_title = 'Label Studio Admin'
admin.site.index_title = '欢迎使用 Label Studio 管理后台'

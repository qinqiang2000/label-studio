from rest_framework import permissions


class PromptsAccessPermission(permissions.BasePermission):
    """模块级访问权限：用户是否能进入 prompts 模块。"""

    def has_permission(self, request, view):
        if request.user.is_superuser:
            return True

        # 走自定义 RBAC（htx_role_permission），而非 Django 的 has_perm（后者只读 auth_permission/rules）
        for permission_name in ('view_prompts_module', 'view_prompts'):
            if request.user.has_permission(permission_name):
                return True

        return False


class IsPromptOwnerOrSuperuserForWrite(permissions.BasePermission):
    """对象级写权限：仅创建者或超管可改/删 prompt（核心资产保护）。

    GET/HEAD/OPTIONS 由队列层（PromptDetailAPI.get_queryset）按 workspace 隔离过滤，
    本类只在写操作时起作用。
    """

    message = '只有创建者或超级管理员可以修改/删除该 Prompt。'

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        user = request.user
        return user.is_superuser or obj.created_by_id == user.id

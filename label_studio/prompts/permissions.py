from rest_framework import permissions


class PromptsAccessPermission(permissions.BasePermission):
    """
    Prompts模块访问权限检查
    检查用户是否具有访问prompts模块的权限
    """
    
    def has_permission(self, request, view):
        # 超级用户始终有权限
        if request.user.is_superuser:
            return True
        
        # 检查用户是否具有prompts相关权限
        permission_names = [
            'view_prompts_module',
            'view_prompts',
        ]
        
        for permission_name in permission_names:
            if request.user.has_perm(permission_name):
                return True
        
        return False
"""
自定义 Django Admin 配置
只允许超级用户登录 admin 界面
"""
from django.contrib import admin


class SuperuserOnlyAdminSite(admin.AdminSite):
    """
    自定义 AdminSite，只允许超级用户访问
    要求用户必须同时满足：is_staff=True, is_active=True, is_superuser=True
    """
    site_header = "Label Studio 管理后台 (超级用户专用)"
    site_title = "Label Studio Admin"
    index_title = "管理后台"

    def has_permission(self, request):
        """
        重写权限检查方法，要求用户必须是激活的超级用户
        """
        return (
            request.user.is_active and
            request.user.is_staff and
            request.user.is_superuser
        )


# 创建自定义 admin site 实例
superuser_admin_site = SuperuserOnlyAdminSite(name='superuser_admin')
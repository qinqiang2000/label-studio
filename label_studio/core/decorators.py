from functools import wraps
from django.core.exceptions import PermissionDenied


def permission_required(*permissions, fn=None):
    def decorator(view):
        def wrapped_view(self, request, *args, **kwargs):

            if callable(fn):
                obj = fn(request, *args, **kwargs)
            else:
                obj = fn

            missing_permissions = [perm for perm in permissions if not request.user.has_perm(perm, obj)]
            if any(missing_permissions):
                # raises a permission denied exception causing a 403 response
                self.permission_denied(
                    request, message=('Permission denied: {}'.format(', '.join(missing_permissions)))
                )

            return view(self, request, *args, **kwargs)

        return wrapped_view

    return decorator


def override_report_only_csp(view_func):
    """
    Decorator to switch report-only CSP to regular CSP. For use with core.middleware.HumanSignalCspMiddleware.
    """

    @wraps(view_func)
    def wrapper(*args, **kwargs):
        response = view_func(*args, **kwargs)
        setattr(response, '_override_report_only_csp', True)
        return response

    return wrapper


def module_permission_required(module_name):
    """
    通用模块权限检查装饰器
    自动根据模块名检查对应的 view_{module}_module 权限
    
    Args:
        module_name (str): 模块名称，如 'prompts', 'projects' 等
        
    Usage:
        @module_permission_required('prompts')
        def prompts_list(request):
            return render(request, 'base.html')
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            # 构造权限名称：view_{module}_module 或 view_{module}
            permission_names = [
                f'view_{module_name}_module',
                f'view_{module_name}',
            ]
            
            # 检查用户是否具有任一权限
            has_permission = False
            for permission_name in permission_names:
                if request.user.has_perm(permission_name):
                    has_permission = True
                    break
            
            if not has_permission:
                raise PermissionDenied(f'访问 {module_name} 模块需要相应权限')
            
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator

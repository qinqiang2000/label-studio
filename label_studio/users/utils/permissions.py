"""
权限相关的工具函数和常量定义
"""

# 权限分类
PERMISSION_CATEGORIES = {
    'MENU': 'menu',
    'ACTION': 'action',
    'DATA': 'data',
    'ADMIN': 'admin',
}

# 菜单权限常量
MENU_PERMISSIONS = {
    'HOME': 'view_home',
    'PROJECTS': 'view_projects',
    'WORKSPACES': 'view_workspaces',
    'PROMPTS': 'view_prompts',
    'ORGANIZATION': 'view_organization',
    
    # 项目设置菜单权限
    'PROJECT_GENERAL_SETTINGS': 'view_project_general_settings',
    'PROJECT_LABELING_SETTINGS': 'view_project_labeling_settings',
    'PROJECT_ANNOTATION_SETTINGS': 'view_project_annotation_settings',
    'PROJECT_MACHINE_LEARNING': 'view_project_machine_learning',
    'PROJECT_PREDICTIONS': 'view_project_predictions',
    'PROJECT_CLOUD_STORAGE': 'view_project_cloud_storage',
    'PROJECT_WEBHOOKS': 'view_project_webhooks',
    'PROJECT_DANGER_ZONE': 'view_project_danger_zone',
    
    # 账户设置权限
    'ACCOUNT_SETTINGS': 'view_account_settings',
}

# 操作权限常量
ACTION_PERMISSIONS = {
    # 项目操作权限
    'CREATE_PROJECT': 'create_project',
    'EDIT_PROJECT': 'edit_project',
    'DELETE_PROJECT': 'delete_project',
    'EXPORT_PROJECT_DATA': 'export_project_data',
    
    # 标注操作权限
    'CREATE_ANNOTATION': 'create_annotation',
    'EDIT_ANNOTATION': 'edit_annotation',
    'DELETE_ANNOTATION': 'delete_annotation',
    'REVIEW_ANNOTATION': 'review_annotation',
    
    # 用户管理权限
    'MANAGE_USERS': 'manage_users',
    'MANAGE_ROLES': 'manage_roles',
    'MANAGE_PERMISSIONS': 'manage_permissions',
    
    # 组织管理权限
    'MANAGE_ORGANIZATION': 'manage_organization',
    'MANAGE_WORKSPACES': 'manage_workspaces',
}

# 预定义角色的默认权限配置
DEFAULT_ROLE_PERMISSIONS = {
    'superuser': {
        # 超级管理员拥有所有权限
        'permissions': [
            # 所有菜单权限
            'view_home',
            'view_projects',
            'view_workspaces',
            'view_prompts',
            'view_organization',
            'view_project_general_settings',
            'view_project_labeling_settings',
            'view_project_annotation_settings',
            'view_project_machine_learning',
            'view_project_predictions',
            'view_project_cloud_storage',
            'view_project_webhooks',
            'view_project_danger_zone',
            'view_account_settings',
            
            # 所有操作权限
            'create_project',
            'edit_project',
            'delete_project',
            'export_project_data',
            'create_annotation',
            'edit_annotation',
            'delete_annotation',
            'review_annotation',
            'manage_users',
            'manage_roles',
            'manage_permissions',
            'manage_organization',
            'manage_workspaces',
        ],
        'description': '超级管理员，拥有系统所有权限',
    },
    
    'annotator': {
        # 标注员的基础权限 - 排除管理类功能
        'permissions': [
            # 基础菜单权限
            'view_home',
            'view_projects',
            'view_workspaces',
            
            # 项目设置中的部分权限（排除管理类功能）
            'view_project_general_settings',
            'view_project_labeling_settings',
            'view_project_annotation_settings',
            # 注意：排除了机器学习、云存储、Webhooks、危险操作等管理功能
            
            # 基础操作权限
            'create_annotation',
            'edit_annotation',
            'delete_annotation',
            
            # 账户设置
            'view_account_settings',
        ],
        'description': '标注员，拥有基础的标注和项目访问权限，不能访问Organization等管理功能',
    },
    
    'workspace_admin': {
        # 工作空间管理员权限（为未来扩展预留）
        'permissions': [
            # 继承标注员权限
            'view_home',
            'view_projects',
            'view_workspaces',
            'view_project_general_settings',
            'view_project_labeling_settings',
            'view_project_annotation_settings',
            'create_annotation',
            'edit_annotation',
            'delete_annotation',
            'view_account_settings',
            
            # 额外的工作空间管理权限
            'manage_workspaces',
            'create_project',
            'edit_project',
            'export_project_data',
            
            # 项目设置的更多权限
            'view_project_predictions',
            'view_project_webhooks',
        ],
        'description': '工作空间管理员，可以管理所属工作空间的项目和成员',
    },
}


def get_all_permissions():
    """获取所有可用权限"""
    return list(set(
        list(MENU_PERMISSIONS.values()) + 
        list(ACTION_PERMISSIONS.values())
    ))


def validate_permissions(permissions):
    """验证权限列表是否有效"""
    all_valid_permissions = get_all_permissions()
    return [p for p in permissions if p in all_valid_permissions]


def get_role_permissions(role_name):
    """获取指定角色的权限列表"""
    return DEFAULT_ROLE_PERMISSIONS.get(role_name, {}).get('permissions', [])


def check_user_permission(user, permission_name):
    """检查用户是否具有指定权限"""
    # 超级管理员拥有所有权限
    if user.is_superuser:
        return True
    
    # 如果没有角色，返回False
    if not user.role:
        return False
    
    # 检查角色是否具有该权限
    from users.models import RolePermission
    return RolePermission.objects.filter(
        role=user.role,
        permission__name=permission_name,
        permission__is_active=True,
        granted=True
    ).exists()


def get_user_permissions(user):
    """获取用户的所有权限列表"""
    from users.models import Permission
    
    if user.is_superuser:
        # 超级管理员拥有所有权限
        return list(Permission.objects.filter(is_active=True).values_list('name', flat=True))
    
    if not user.role:
        return []
    
    return list(Permission.objects.filter(
        roles__role=user.role,
        roles__granted=True,
        is_active=True
    ).values_list('name', flat=True))
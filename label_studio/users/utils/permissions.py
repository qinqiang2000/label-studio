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
    
    # 权限管理权限
    'PERMISSION_MANAGEMENT': 'view_permission_management',
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

# 权限组定义 - 用于批量管理相关权限
PERMISSION_GROUPS = {
    'basic_user': [
        'view_home',
        'view_projects', 
        'view_workspaces',
        'view_account_settings',
    ],
    
    'annotation_operations': [
        'create_annotation',
        'edit_annotation', 
        'delete_annotation',
    ],
    
    'project_basic_settings': [
        'view_project_general_settings',
        'view_project_labeling_settings',
        'view_project_annotation_settings',
    ],
    
    'project_management': [
        'create_project',
        'edit_project',
        'delete_project',
        'export_project_data',
        'import_project_data',
    ],
    
    'project_advanced_settings': [
        'view_project_machine_learning',
        'view_project_predictions', 
        'view_project_cloud_storage',
        'view_project_webhooks',
        'view_project_danger_zone',
    ],
    
    'workspace_management': [
        'manage_workspaces',
        'create_workspace',
        'edit_workspace',
        'delete_workspace',
        'manage_workspace_members',
    ],
    
    'organization_management': [
        'view_organization',
        'manage_organization',
        'manage_users',
        'manage_roles',
        'view_prompts',
        'view_permission_management',
    ],
    
    'page_operations': [
        'show_create_project_button',
        'show_import_project_button', 
        'show_export_project_button',
        'show_delete_project_button',
        'show_create_workspace_button',
        'show_edit_workspace_button',
        'show_delete_workspace_button',
        'show_invite_users_button',
        'show_manage_user_roles',
        'show_permission_management_button',
    ],
    
    'form_field_permissions': [
        'edit_project_danger_zone_fields',
        'edit_project_ml_settings',
        'edit_project_webhook_settings',
        'edit_user_role_assignment',
        'edit_organization_settings',
    ]
}

# 角色权限配置 - 使用权限组简化配置
ROLE_PERMISSION_CONFIG = {
    'annotator': {
        'groups': ['basic_user', 'annotation_operations', 'project_basic_settings'],
        'additional_permissions': [],
        'description': '标注员，拥有基础的标注和项目访问权限',
    },
    
    'workspace_admin': {
        'inherit_from': 'annotator',  # 继承annotator的所有权限
        'groups': [
            'project_management', 
            'workspace_management', 
            'project_advanced_settings',
            'page_operations'
        ],
        'additional_permissions': [],
        'description': '工作空间管理员，可以管理所属工作空间的项目和成员',
    },
    
    'superuser': {
        'groups': 'all',  # 拥有所有权限
        'description': '超级管理员，拥有系统所有权限',
    }
}

# 工具函数：获取角色的所有权限
def get_role_permissions_by_config(role_name):
    """基于配置获取指定角色的所有权限列表"""
    role_config = ROLE_PERMISSION_CONFIG.get(role_name)
    if not role_config:
        return []
    
    permissions = []
    
    # 处理权限继承
    if 'inherit_from' in role_config:
        permissions.extend(get_role_permissions_by_config(role_config['inherit_from']))
    
    # 处理权限组
    if role_config.get('groups') == 'all':
        # 拥有所有权限
        all_permissions = []
        for group_permissions in PERMISSION_GROUPS.values():
            all_permissions.extend(group_permissions)
        permissions.extend(all_permissions)
    elif isinstance(role_config.get('groups'), list):
        # 基于权限组获取权限
        for group_name in role_config['groups']:
            group_permissions = PERMISSION_GROUPS.get(group_name, [])
            permissions.extend(group_permissions)
    
    # 添加额外的单个权限
    if role_config.get('additional_permissions'):
        permissions.extend(role_config['additional_permissions'])
    
    # 去重并返回
    return list(set(permissions))

# 基于新配置生成默认权限配置
DEFAULT_ROLE_PERMISSIONS = {
    role_name: {
        'permissions': get_role_permissions_by_config(role_name),
        'description': config['description'],
    }
    for role_name, config in ROLE_PERMISSION_CONFIG.items()
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
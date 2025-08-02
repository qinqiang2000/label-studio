/**
 * 权限常量定义
 * 定义系统中所有可用的权限
 */

// 菜单权限常量
export const MENU_PERMISSIONS = {
  // 主菜单权限
  HOME: 'view_home',
  PROJECTS: 'view_projects',
  WORKSPACES: 'view_workspaces',
  PROMPTS: 'view_prompts',
  ORGANIZATION: 'view_organization',

  // 项目设置菜单权限
  PROJECT_GENERAL_SETTINGS: 'view_project_general_settings',
  PROJECT_LABELING_SETTINGS: 'view_project_labeling_settings',
  PROJECT_ANNOTATION_SETTINGS: 'view_project_annotation_settings',
  PROJECT_MACHINE_LEARNING: 'view_project_machine_learning',
  PROJECT_PREDICTIONS: 'view_project_predictions',
  PROJECT_CLOUD_STORAGE: 'view_project_cloud_storage',
  PROJECT_WEBHOOKS: 'view_project_webhooks',
  PROJECT_DANGER_ZONE: 'view_project_danger_zone',

  // 账户设置权限
  ACCOUNT_SETTINGS: 'view_account_settings',
};

// 操作权限常量
export const ACTION_PERMISSIONS = {
  // 项目操作权限
  CREATE_PROJECT: 'create_project',
  EDIT_PROJECT: 'edit_project',
  DELETE_PROJECT: 'delete_project',
  EXPORT_PROJECT_DATA: 'export_project_data',

  // 标注操作权限
  CREATE_ANNOTATION: 'create_annotation',
  EDIT_ANNOTATION: 'edit_annotation',
  DELETE_ANNOTATION: 'delete_annotation',
  REVIEW_ANNOTATION: 'review_annotation',

  // 用户管理权限
  MANAGE_USERS: 'manage_users',
  MANAGE_ROLES: 'manage_roles',
  MANAGE_PERMISSIONS: 'manage_permissions',

  // 组织管理权限
  MANAGE_ORGANIZATION: 'manage_organization',
  MANAGE_WORKSPACES: 'manage_workspaces',
};

// 权限分类
export const PERMISSION_CATEGORIES = {
  MENU: 'menu',
  ACTION: 'action',
  DATA: 'data',
  ADMIN: 'admin',
};

// 预定义角色的默认权限配置
export const DEFAULT_ROLE_PERMISSIONS = {
  superuser: {
    // 超级管理员拥有所有权限
    permissions: [
      ...Object.values(MENU_PERMISSIONS),
      ...Object.values(ACTION_PERMISSIONS),
    ],
    description: '超级管理员，拥有系统所有权限',
  },
  
  annotator: {
    // 标注员的基础权限
    permissions: [
      // 基础菜单权限
      MENU_PERMISSIONS.HOME,
      MENU_PERMISSIONS.PROJECTS,
      MENU_PERMISSIONS.WORKSPACES,
      
      // 项目设置中的部分权限（排除管理类功能）
      MENU_PERMISSIONS.PROJECT_GENERAL_SETTINGS,
      MENU_PERMISSIONS.PROJECT_LABELING_SETTINGS,
      MENU_PERMISSIONS.PROJECT_ANNOTATION_SETTINGS,
      
      // 基础操作权限
      ACTION_PERMISSIONS.CREATE_ANNOTATION,
      ACTION_PERMISSIONS.EDIT_ANNOTATION,
      ACTION_PERMISSIONS.DELETE_ANNOTATION,
      
      // 账户设置
      MENU_PERMISSIONS.ACCOUNT_SETTINGS,
    ],
    description: '标注员，拥有基础的标注和项目访问权限',
  },
  
  workspace_admin: {
    // 工作空间管理员权限（为未来扩展预留）
    permissions: [
      // 基础菜单权限（继承自标注员）
      MENU_PERMISSIONS.HOME,
      MENU_PERMISSIONS.PROJECTS,
      MENU_PERMISSIONS.WORKSPACES,
      MENU_PERMISSIONS.PROJECT_GENERAL_SETTINGS,
      MENU_PERMISSIONS.PROJECT_LABELING_SETTINGS,
      MENU_PERMISSIONS.PROJECT_ANNOTATION_SETTINGS,
      MENU_PERMISSIONS.ACCOUNT_SETTINGS,
      
      // 基础操作权限（继承自标注员）
      ACTION_PERMISSIONS.CREATE_ANNOTATION,
      ACTION_PERMISSIONS.EDIT_ANNOTATION,
      ACTION_PERMISSIONS.DELETE_ANNOTATION,
      
      // 额外的工作空间管理权限
      ACTION_PERMISSIONS.MANAGE_WORKSPACES,
      ACTION_PERMISSIONS.CREATE_PROJECT,
      ACTION_PERMISSIONS.EDIT_PROJECT,
      ACTION_PERMISSIONS.EXPORT_PROJECT_DATA,
      
      // 项目设置的更多权限
      MENU_PERMISSIONS.PROJECT_PREDICTIONS,
      MENU_PERMISSIONS.PROJECT_WEBHOOKS,
    ],
    description: '工作空间管理员，可以管理所属工作空间的项目和成员',
  },
};

// 权限检查辅助函数
export const createPermissionChecker = (userPermissions = []) => {
  const permissionSet = new Set(userPermissions);
  
  return {
    // 检查单个权限
    hasPermission: (permission) => permissionSet.has(permission),
    
    // 检查多个权限（AND逻辑）
    hasAllPermissions: (permissions) => 
      permissions.every(permission => permissionSet.has(permission)),
    
    // 检查多个权限（OR逻辑）
    hasAnyPermission: (permissions) => 
      permissions.some(permission => permissionSet.has(permission)),
    
    // 检查菜单权限
    hasMenuPermission: (menuKey) => 
      permissionSet.has(MENU_PERMISSIONS[menuKey]),
    
    // 检查操作权限
    hasActionPermission: (actionKey) => 
      permissionSet.has(ACTION_PERMISSIONS[actionKey]),
    
    // 获取用户所有权限
    getPermissions: () => Array.from(permissionSet),
  };
};

// 权限配置验证函数
export const validatePermissions = (permissions) => {
  const allValidPermissions = [
    ...Object.values(MENU_PERMISSIONS),
    ...Object.values(ACTION_PERMISSIONS),
  ];
  
  return permissions.filter(permission => 
    allValidPermissions.includes(permission)
  );
};
import { useMemo } from 'react';
import { useCurrentUser } from '../providers/CurrentUser';
import { createPermissionChecker, MENU_PERMISSIONS, ACTION_PERMISSIONS } from '../utils/permissions';

/**
 * 权限管理 Hook
 * 提供统一的权限检查接口
 */
export const usePermissions = () => {
  const { user } = useCurrentUser();
  
  // 创建权限检查器
  const permissionChecker = useMemo(() => {
    const userPermissions = user?.permissions || [];
    return createPermissionChecker(userPermissions);
  }, [user?.permissions]);
  
  // 角色检查
  const roleCheckers = useMemo(() => {
    const userRole = user?.role_info?.name || 'annotator';
    
    return {
      isSuperuser: () => user?.is_superuser || userRole === 'superuser',
      isAnnotator: () => userRole === 'annotator',
      isWorkspaceAdmin: () => userRole === 'workspace_admin',
      getCurrentRole: () => userRole,
      getRoleDisplayName: () => user?.role_info?.display_name || 'Annotator',
    };
  }, [user?.is_superuser, user?.role_info]);
  
  // 菜单权限检查
  const menuPermissions = useMemo(() => ({
    // 主菜单权限
    canViewHome: () => permissionChecker.hasPermission(MENU_PERMISSIONS.HOME),
    canViewProjects: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECTS),
    canViewWorkspaces: () => permissionChecker.hasPermission(MENU_PERMISSIONS.WORKSPACES),
    canViewPrompts: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROMPTS),
    canViewOrganization: () => permissionChecker.hasPermission(MENU_PERMISSIONS.ORGANIZATION),
    
    // 项目设置菜单权限
    canViewProjectGeneralSettings: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECT_GENERAL_SETTINGS),
    canViewProjectLabelingSettings: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECT_LABELING_SETTINGS),
    canViewProjectAnnotationSettings: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECT_ANNOTATION_SETTINGS),
    canViewProjectMachineLearning: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECT_MACHINE_LEARNING),
    canViewProjectPredictions: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECT_PREDICTIONS),
    canViewProjectCloudStorage: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECT_CLOUD_STORAGE),
    canViewProjectWebhooks: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECT_WEBHOOKS),
    canViewProjectDangerZone: () => permissionChecker.hasPermission(MENU_PERMISSIONS.PROJECT_DANGER_ZONE),
    
    // 账户设置权限
    canViewAccountSettings: () => permissionChecker.hasPermission(MENU_PERMISSIONS.ACCOUNT_SETTINGS),
  }), [permissionChecker]);
  
  // 操作权限检查
  const actionPermissions = useMemo(() => ({
    // 项目操作权限
    canCreateProject: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.CREATE_PROJECT),
    canEditProject: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.EDIT_PROJECT),
    canDeleteProject: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.DELETE_PROJECT),
    canExportProjectData: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.EXPORT_PROJECT_DATA),
    
    // 标注操作权限
    canCreateAnnotation: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.CREATE_ANNOTATION),
    canEditAnnotation: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.EDIT_ANNOTATION),
    canDeleteAnnotation: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.DELETE_ANNOTATION),
    canReviewAnnotation: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.REVIEW_ANNOTATION),
    
    // 用户管理权限
    canManageUsers: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.MANAGE_USERS),
    canManageRoles: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.MANAGE_ROLES),
    canManagePermissions: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.MANAGE_PERMISSIONS),
    
    // 组织管理权限
    canManageOrganization: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.MANAGE_ORGANIZATION),
    canManageWorkspaces: () => permissionChecker.hasPermission(ACTION_PERMISSIONS.MANAGE_WORKSPACES),
  }), [permissionChecker]);
  
  return {
    // 基础权限检查器
    ...permissionChecker,
    
    // 角色检查器
    ...roleCheckers,
    
    // 菜单权限检查器
    menu: menuPermissions,
    
    // 操作权限检查器
    action: actionPermissions,
    
    // 便捷方法
    isLoading: !user,
    hasUser: !!user,
    
    // 调试信息
    debug: {
      user: user,
      permissions: user?.permissions || [],
      role: user?.role_info || null,
    },
  };
};

/**
 * 权限组件包装器 Hook
 * 用于条件渲染组件
 */
export const usePermissionGuard = () => {
  const permissions = usePermissions();
  
  /**
   * 根据权限条件渲染组件
   * @param {string|string[]|function} condition - 权限条件
   * @param {React.Component} component - 要渲染的组件
   * @param {React.Component} fallback - 无权限时的替代组件
   * @returns {React.Component|null}
   */
  const renderWithPermission = (condition, component, fallback = null) => {
    let hasPermission = false;
    
    if (typeof condition === 'string') {
      // 单个权限检查
      hasPermission = permissions.hasPermission(condition);
    } else if (Array.isArray(condition)) {
      // 多个权限检查（AND逻辑）
      hasPermission = permissions.hasAllPermissions(condition);
    } else if (typeof condition === 'function') {
      // 自定义条件函数
      hasPermission = condition(permissions);
    }
    
    return hasPermission ? component : fallback;
  };
  
  /**
   * 权限HOC组件
   */
  const PermissionGuard = ({ 
    permission, 
    permissions: permissionList, 
    condition, 
    children, 
    fallback = null,
    mode = 'all' // 'all' | 'any'
  }) => {
    let hasPermission = false;
    
    if (permission) {
      hasPermission = permissions.hasPermission(permission);
    } else if (permissionList) {
      hasPermission = mode === 'any' 
        ? permissions.hasAnyPermission(permissionList)
        : permissions.hasAllPermissions(permissionList);
    } else if (condition) {
      hasPermission = condition(permissions);
    }
    
    return hasPermission ? children : fallback;
  };
  
  return {
    renderWithPermission,
    PermissionGuard,
  };
};

export default usePermissions;
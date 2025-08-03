import { useMemo } from 'react';
import { useCurrentUser } from '../providers/CurrentUser';
import { PERMISSION_SYSTEM_CONFIG } from '../config/permissions';

/**
 * 简化的角色访问控制 Hook
 * 用于替代复杂的权限检查，基于用户角色进行UI访问控制
 */
export const useRoleAccess = () => {
  const { user } = useCurrentUser();
  
  // 获取用户角色
  const userRole = useMemo(() => {
    if (user?.is_superuser) return 'superuser';
    return user?.role_info?.name || 'annotator';
  }, [user?.is_superuser, user?.role_info?.name]);
  
  // 角色级别判断
  const roleCheckers = useMemo(() => ({
    // 基础用户检查
    isBasicUser: () => ['annotator', 'workspace_admin', 'superuser'].includes(userRole),
    
    // 管理员检查
    isAdmin: () => ['workspace_admin', 'superuser'].includes(userRole),
    
    // 超级管理员检查
    isSuperUser: () => userRole === 'superuser',
    
    // 获取当前角色
    getCurrentRole: () => userRole,
    
    // 检查是否有UI区域访问权限
    hasUIAccess: (uiArea) => {
      const allowedRoles = PERMISSION_SYSTEM_CONFIG.looseMode.roleBasedUI[uiArea] || [];
      return allowedRoles.includes(userRole);
    },
    
    // 检查是否可以执行危险操作
    canPerformDangerousOperation: () => userRole === 'superuser'
  }), [userRole]);
  
  return {
    userRole,
    ...roleCheckers,
    
    // 调试信息
    debug: {
      user: user,
      userRole: userRole,
      roleInfo: user?.role_info || null,
    },
  };
};

/**
 * 角色保护组件
 * 基于角色控制组件渲染
 */
export const useRoleGuard = () => {
  const roleAccess = useRoleAccess();
  
  /**
   * 根据角色要求渲染组件
   * @param {string} requiredRole - 需要的角色：'basic_ui' | 'admin_ui' | 'super_ui'
   * @param {React.Component} component - 要渲染的组件
   * @param {React.Component} fallback - 无权限时的替代组件
   * @returns {React.Component|null}
   */
  const renderWithRole = (requiredRole, component, fallback = null) => {
    const hasAccess = roleAccess.hasUIAccess(requiredRole);
    return hasAccess ? component : fallback;
  };
  
  /**
   * 角色保护HOC组件
   */
  const RoleGuard = ({ 
    requireRole, 
    children, 
    fallback = null 
  }) => {
    const hasAccess = roleAccess.hasUIAccess(requireRole);
    return hasAccess ? children : fallback;
  };
  
  return {
    renderWithRole,
    RoleGuard,
  };
};

export default useRoleAccess;
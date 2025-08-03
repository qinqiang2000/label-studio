import React from 'react';
import { Button, Tooltip } from '@humansignal/ui';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSION_SYSTEM_CONFIG } from '../../config/permissions';

/**
 * 智能权限按钮组件
 * 基于权限自动控制按钮的显示、禁用状态和提示
 */
export const SmartButton = ({ 
  permission,
  permissions: permissionList,
  condition,
  requireRole, // 新增：角色要求 'admin_ui' | 'super_ui'
  dangerLevel, // 新增：危险级别 'low' | 'medium' | 'high'
  fallback = 'hide', // 'hide' | 'disable' | 'tooltip'
  tooltipText,
  disabled = false,
  children,
  className,
  variant,
  size,
  onClick,
  ...props 
}) => {
  const permissionHook = usePermissions();
  
  // 计算是否有权限
  const hasPermission = React.useMemo(() => {
    const isLooseMode = PERMISSION_SYSTEM_CONFIG.mode === 'loose';
    
    // 宽松模式下的权限检查逻辑
    if (isLooseMode) {
      // 1. 优先检查角色要求
      if (requireRole) {
        const userRole = permissionHook.getCurrentRole();
        const allowedRoles = PERMISSION_SYSTEM_CONFIG.looseMode.roleBasedUI[requireRole] || [];
        return allowedRoles.includes(userRole);
      }
      
      // 2. 检查危险级别（高危险操作需要权限控制）
      if (dangerLevel === 'high') {
        if (permission) {
          return permissionHook.hasPermission(permission);
        }
        // 高危险操作但没有指定权限，默认只允许超级用户
        return permissionHook.isSuperuser();
      }
      
      // 3. 检查是否在危险操作列表中
      if (permission && PERMISSION_SYSTEM_CONFIG.looseMode.dangerousOperations.includes(permission)) {
        return permissionHook.hasPermission(permission);
      }
      
      // 4. 宽松模式下，普通操作默认允许
      if (!permission && !permissionList && !condition) {
        return true;
      }
    }
    
    // 严格模式下的原有逻辑，或显式指定了权限检查的情况
    if (condition && typeof condition === 'function') {
      return condition(permissionHook);
    }
    
    if (permission && typeof permission === 'string') {
      return permissionHook.hasPermission(permission);
    }
    
    if (permissionList && Array.isArray(permissionList)) {
      return permissionHook.hasAllPermissions(permissionList);
    }
    
    // 严格模式下，没有指定权限条件默认无权限
    // 宽松模式下，没有指定权限条件默认有权限
    return isLooseMode;
  }, [permission, permissionList, condition, requireRole, dangerLevel, permissionHook]);
  
  // 无权限时的处理
  if (!hasPermission) {
    switch (fallback) {
      case 'hide':
        return null;
        
      case 'disable':
        return (
          <Button 
            disabled={true}
            className={className}
            variant={variant}
            size={size}
            {...props}
          >
            {children}
          </Button>
        );
        
      case 'tooltip':
        const defaultTooltipText = tooltipText || '您没有此操作权限';
        return (
          <Tooltip title={defaultTooltipText}>
            <Button 
              disabled={true}
              className={className}
              variant={variant}
              size={size}
              {...props}
            >
              {children}
            </Button>
          </Tooltip>
        );
        
      default:
        return null;
    }
  }
  
  // 有权限时正常渲染
  return (
    <Button 
      disabled={disabled}
      className={className}
      variant={variant}
      size={size}
      onClick={onClick}
      {...props}
    >
      {children}
    </Button>
  );
};

export default SmartButton;
import React from 'react';
import { Button, Tooltip } from '@humansignal/ui';
import { usePermissions } from '../../hooks/usePermissions';
import { PERMISSION_SYSTEM_CONFIG } from '../../config/permissions';

/**
 * 简化的智能按钮组件 - 演示宽松模式的理念
 * 
 * 使用方式：
 * 1. 普通按钮：直接显示，无需权限配置
 * 2. 管理员按钮：只需要指定 requireRole="admin_ui"
 * 3. 危险操作：指定 dangerLevel="high"
 */
export const SimpleButton = ({ 
  requireRole, // 'admin_ui' | 'super_ui' - 角色要求
  dangerLevel, // 'high' - 危险级别
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
  const permissions = usePermissions();
  
  // 简化的权限检查逻辑
  const hasAccess = React.useMemo(() => {
    // 1. 角色要求检查
    if (requireRole) {
      const userRole = permissions.getCurrentRole();
      const allowedRoles = PERMISSION_SYSTEM_CONFIG.looseMode.roleBasedUI[requireRole] || [];
      return allowedRoles.includes(userRole);
    }
    
    // 2. 危险操作检查
    if (dangerLevel === 'high') {
      return permissions.isSuperuser();
    }
    
    // 3. 默认允许访问
    return true;
  }, [requireRole, dangerLevel, permissions]);
  
  // 无权限时的处理
  if (!hasAccess) {
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

export default SimpleButton;
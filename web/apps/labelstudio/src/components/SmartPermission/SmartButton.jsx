import React from 'react';
import { Button, Tooltip } from '@humansignal/ui';
import { usePermissions } from '../../hooks/usePermissions';

/**
 * 智能权限按钮组件
 * 基于权限自动控制按钮的显示、禁用状态和提示
 */
export const SmartButton = ({ 
  permission,
  permissions: permissionList,
  condition,
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
    if (condition && typeof condition === 'function') {
      return condition(permissionHook);
    }
    
    if (permission && typeof permission === 'string') {
      return permissionHook.hasPermission(permission);
    }
    
    if (permissionList && Array.isArray(permissionList)) {
      return permissionHook.hasAllPermissions(permissionList);
    }
    
    // 如果没有指定权限条件，默认有权限
    return true;
  }, [permission, permissionList, condition, permissionHook]);
  
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
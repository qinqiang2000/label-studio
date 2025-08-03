import React from 'react';
import { Tooltip } from '@humansignal/ui';
import { usePermissions } from '../../hooks/usePermissions';

/**
 * 智能权限表单字段组件
 * 基于权限自动控制表单字段的编辑、禁用和显示状态
 */
export const SmartField = ({ 
  permission,
  permissions: permissionList,
  condition,
  mode = 'edit', // 'edit' | 'readonly' | 'hide' - 无权限时的处理方式
  readOnlyTooltip = '您没有编辑此字段的权限',
  children,
  fallback = null,
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
    switch (mode) {
      case 'hide':
        return fallback;
        
      case 'readonly':
        // 将子组件设置为只读模式
        if (React.isValidElement(children)) {
          const readOnlyChild = React.cloneElement(children, {
            ...props,
            readOnly: true,
            disabled: true,
          });
          
          return readOnlyTooltip ? (
            <Tooltip title={readOnlyTooltip}>
              <div style={{ cursor: 'not-allowed' }}>
                {readOnlyChild}
              </div>
            </Tooltip>
          ) : readOnlyChild;
        }
        return children;
        
      case 'edit':
      default:
        // 默认行为：显示但禁用
        if (React.isValidElement(children)) {
          return React.cloneElement(children, {
            ...props,
            disabled: true,
          });
        }
        return children;
    }
  }
  
  // 有权限时正常渲染
  if (React.isValidElement(children)) {
    return React.cloneElement(children, props);
  }
  
  return children;
};

export default SmartField;
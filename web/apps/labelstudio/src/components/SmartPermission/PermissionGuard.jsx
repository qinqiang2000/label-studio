import React from "react";
import { usePermissions } from "../../hooks/usePermissions";

/**
 * 权限守卫组件
 * 根据权限条件控制子组件的渲染
 */
export const PermissionGuard = ({
  permission,
  permissions: permissionList,
  condition,
  mode = "all", // 'all' | 'any' - 仅在使用permissionList时生效
  children,
  fallback = null,
  inverse = false, // 是否反向检查（即没有权限时才显示）
}) => {
  const permissionHook = usePermissions();

  // 计算是否有权限
  const hasPermission = React.useMemo(() => {
    if (condition && typeof condition === "function") {
      return condition(permissionHook);
    }

    if (permission && typeof permission === "string") {
      return permissionHook.hasPermission(permission);
    }

    if (permissionList && Array.isArray(permissionList)) {
      return mode === "any"
        ? permissionHook.hasAnyPermission(permissionList)
        : permissionHook.hasAllPermissions(permissionList);
    }

    // 如果没有指定权限条件，默认有权限
    return true;
  }, [permission, permissionList, condition, mode, permissionHook]);

  // 根据inverse参数决定最终的显示逻辑
  const shouldRender = inverse ? !hasPermission : hasPermission;

  return shouldRender ? children : fallback;
};

/**
 * 权限守卫高阶组件
 * 用于包装现有组件添加权限控制
 */
export const withPermission = (permissionConfig) => (WrappedComponent) => {
  const PermissionWrappedComponent = (props) => {
    return (
      <PermissionGuard {...permissionConfig}>
        <WrappedComponent {...props} />
      </PermissionGuard>
    );
  };

  PermissionWrappedComponent.displayName = `withPermission(${WrappedComponent.displayName || WrappedComponent.name})`;

  return PermissionWrappedComponent;
};

export default PermissionGuard;

import { useMemo } from "react";
import { useCurrentUser } from "../providers/CurrentUser";
import { createPermissionChecker } from "../utils/permissions";
import { PERMISSION_DEFINITIONS } from "../config/permissions";

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
    const userRole = user?.role_info?.name || "annotator";

    return {
      isSuperuser: () => user?.is_superuser || userRole === "superuser",
      isAnnotator: () => userRole === "annotator",
      isWorkspaceAdmin: () => userRole === "workspace_admin",
      getCurrentRole: () => userRole,
      getRoleDisplayName: () => user?.role_info?.display_name || "Annotator",
    };
  }, [user?.is_superuser, user?.role_info]);

  // 基于配置文件自动生成菜单权限检查方法
  const menuPermissions = useMemo(() => {
    const methods = {};

    Object.entries(PERMISSION_DEFINITIONS)
      .filter(([_, config]) => config.category === "menu")
      .forEach(([permission, config]) => {
        methods[config.hookMethod] = () => permissionChecker.hasPermission(permission);
      });

    return methods;
  }, [permissionChecker]);

  // 基于配置文件自动生成操作权限检查方法
  const actionPermissions = useMemo(() => {
    const methods = {};

    Object.entries(PERMISSION_DEFINITIONS)
      .filter(([_, config]) => config.category === "action")
      .forEach(([permission, config]) => {
        methods[config.hookMethod] = () => permissionChecker.hasPermission(permission);
      });

    return methods;
  }, [permissionChecker]);

  // 基于配置文件自动生成管理权限检查方法
  const adminPermissions = useMemo(() => {
    const methods = {};

    Object.entries(PERMISSION_DEFINITIONS)
      .filter(([_, config]) => config.category === "admin")
      .forEach(([permission, config]) => {
        methods[config.hookMethod] = () => permissionChecker.hasPermission(permission);
      });

    return methods;
  }, [permissionChecker]);

  // 基于配置文件自动生成页面操作权限检查方法
  const pageOperationPermissions = useMemo(() => {
    const methods = {};

    Object.entries(PERMISSION_DEFINITIONS)
      .filter(([_, config]) => config.category === "page_operation")
      .forEach(([permission, config]) => {
        methods[config.hookMethod] = () => permissionChecker.hasPermission(permission);
      });

    return methods;
  }, [permissionChecker]);

  // 基于配置文件自动生成表单字段权限检查方法
  const fieldPermissions = useMemo(() => {
    const methods = {};

    Object.entries(PERMISSION_DEFINITIONS)
      .filter(([_, config]) => config.category === "field_permission")
      .forEach(([permission, config]) => {
        methods[config.hookMethod] = () => permissionChecker.hasPermission(permission);
      });

    return methods;
  }, [permissionChecker]);

  return {
    // 基础权限检查器
    ...permissionChecker,

    // 角色检查器
    ...roleCheckers,

    // 菜单权限检查器
    menu: menuPermissions,

    // 操作权限检查器
    action: actionPermissions,

    // 管理权限检查器
    admin: adminPermissions,

    // 页面操作权限检查器
    page: pageOperationPermissions,

    // 表单字段权限检查器
    field: fieldPermissions,

    // 便捷方法
    isLoading: !user,
    hasUser: !!user,

    // 调试信息
    debug: {
      user: user,
      permissions: user?.permissions || [],
      role: user?.role_info || null,
      permissionCount: user?.permissions?.length || 0,
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

    if (typeof condition === "string") {
      // 单个权限检查
      hasPermission = permissions.hasPermission(condition);
    } else if (Array.isArray(condition)) {
      // 多个权限检查（AND逻辑）
      hasPermission = permissions.hasAllPermissions(condition);
    } else if (typeof condition === "function") {
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
    mode = "all", // 'all' | 'any'
  }) => {
    let hasPermission = false;

    if (permission) {
      hasPermission = permissions.hasPermission(permission);
    } else if (permissionList) {
      hasPermission =
        mode === "any" ? permissions.hasAnyPermission(permissionList) : permissions.hasAllPermissions(permissionList);
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

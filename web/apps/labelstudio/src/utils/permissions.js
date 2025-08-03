/**
 * 权限常量定义
 * 基于配置文件自动生成所有权限常量
 */

import { 
  PERMISSION_DEFINITIONS, 
  getPermissionsByCategory,
  ROLE_PERMISSION_CONFIG,
  getRolePermissions 
} from '../config/permissions.js';

// 自动生成菜单权限常量
export const MENU_PERMISSIONS = getPermissionsByCategory('menu');

// 自动生成操作权限常量  
export const ACTION_PERMISSIONS = getPermissionsByCategory('action');

// 自动生成管理权限常量
export const ADMIN_PERMISSIONS = getPermissionsByCategory('admin');

// 自动生成页面操作权限常量
export const PAGE_OPERATION_PERMISSIONS = getPermissionsByCategory('page_operation');

// 自动生成表单字段权限常量
export const FIELD_PERMISSION_PERMISSIONS = getPermissionsByCategory('field_permission');

// 权限分类常量
export const PERMISSION_CATEGORIES = {
  MENU: 'menu',
  ACTION: 'action',
  ADMIN: 'admin',
  PAGE_OPERATION: 'page_operation',
  FIELD_PERMISSION: 'field_permission',
};

// 基于配置文件自动生成角色权限配置
export const DEFAULT_ROLE_PERMISSIONS = Object.fromEntries(
  Object.entries(ROLE_PERMISSION_CONFIG).map(([roleName, config]) => [
    roleName,
    {
      permissions: getRolePermissions(roleName),
      description: config.description,
      displayName: config.displayName,
    }
  ])
);

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
    
    // 检查管理权限
    hasAdminPermission: (adminKey) => 
      permissionSet.has(ADMIN_PERMISSIONS[adminKey]),
    
    // 检查页面操作权限
    hasPageOperationPermission: (operationKey) => 
      permissionSet.has(PAGE_OPERATION_PERMISSIONS[operationKey]),
    
    // 检查表单字段权限
    hasFieldPermission: (fieldKey) => 
      permissionSet.has(FIELD_PERMISSION_PERMISSIONS[fieldKey]),
    
    // 获取用户所有权限
    getPermissions: () => Array.from(permissionSet),
    
    // 获取用户权限总数
    getPermissionCount: () => permissionSet.size,
    
    // 检查用户是否有指定分类的任意权限
    hasAnyPermissionInCategory: (category) => {
      const categoryPermissions = getPermissionsByCategory(category);
      return Object.values(categoryPermissions).some(permission => 
        permissionSet.has(permission)
      );
    },
  };
};

// 权限配置验证函数
export const validatePermissions = (permissions) => {
  const allValidPermissions = Object.keys(PERMISSION_DEFINITIONS);
  
  return permissions.filter(permission => 
    allValidPermissions.includes(permission)
  );
};

// 获取所有有效权限列表
export const getAllValidPermissions = () => {
  return Object.keys(PERMISSION_DEFINITIONS);
};

// 根据权限名获取权限详细信息
export const getPermissionInfo = (permissionName) => {
  return PERMISSION_DEFINITIONS[permissionName] || null;
};

// 获取所有权限分类及其权限列表
export const getAllPermissionsByCategory = () => {
  return {
    menu: Object.values(MENU_PERMISSIONS),
    action: Object.values(ACTION_PERMISSIONS), 
    admin: Object.values(ADMIN_PERMISSIONS),
    page_operation: Object.values(PAGE_OPERATION_PERMISSIONS),
    field_permission: Object.values(FIELD_PERMISSION_PERMISSIONS),
  };
};
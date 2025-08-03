/**
 * 智能权限组件库
 * 提供基于权限的智能UI组件
 */

export { SmartButton } from './SmartButton';
export { PermissionGuard, withPermission } from './PermissionGuard';
export { SmartField } from './SmartField';

// 便捷的权限检查Hook
export { usePermissions, usePermissionGuard } from '../../hooks/usePermissions';

// 重新导出权限常量，方便使用
export {
  MENU_PERMISSIONS,
  ACTION_PERMISSIONS,
  ADMIN_PERMISSIONS,
  PAGE_OPERATION_PERMISSIONS,
  FIELD_PERMISSION_PERMISSIONS,
  PERMISSION_CATEGORIES
} from '../../utils/permissions';

// 重新导出权限配置，用于调试和扩展
export {
  PERMISSION_DEFINITIONS,
  PERMISSION_GROUPS,
  ROLE_PERMISSION_CONFIG
} from '../../config/permissions';
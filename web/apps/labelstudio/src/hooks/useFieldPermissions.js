import { usePermissions } from "./usePermissions";

/**
 * 表单字段权限专用Hook
 * 提供常用表单字段权限的快捷检查方法
 */
export const useFieldPermissions = () => {
  const permissions = usePermissions();

  return {
    // 项目设置表单字段权限
    canEditProjectDangerZoneFields: permissions.field?.canEditProjectDangerZoneFields?.() || false,
    canEditProjectMLSettings: permissions.field?.canEditProjectMLSettings?.() || false,
    canEditProjectWebhookSettings: permissions.field?.canEditProjectWebhookSettings?.() || false,

    // 用户管理表单字段权限
    canEditUserRoleAssignment: permissions.field?.canEditUserRoleAssignment?.() || false,
    canEditOrganizationSettings: permissions.field?.canEditOrganizationSettings?.() || false,

    // 便捷方法：检查是否可以编辑任何项目高级设置
    canEditAnyProjectAdvancedSettings: () => {
      const advancedFieldPermissions = [
        "edit_project_danger_zone_fields",
        "edit_project_ml_settings",
        "edit_project_webhook_settings",
      ];
      return permissions.hasAnyPermission?.(advancedFieldPermissions) || false;
    },

    // 便捷方法：检查是否可以编辑任何用户管理字段
    canEditAnyUserManagementFields: () => {
      const userManagementPermissions = ["edit_user_role_assignment", "edit_organization_settings"];
      return permissions.hasAnyPermission?.(userManagementPermissions) || false;
    },

    // 便捷方法：根据字段名动态检查权限
    canEditField: (fieldName) => {
      const fieldPermissionMap = {
        projectDangerZone: "edit_project_danger_zone_fields",
        projectMLSettings: "edit_project_ml_settings",
        projectWebhookSettings: "edit_project_webhook_settings",
        userRoleAssignment: "edit_user_role_assignment",
        organizationSettings: "edit_organization_settings",
      };

      const permissionName = fieldPermissionMap[fieldName];
      return permissionName ? permissions.hasPermission?.(permissionName) || false : false;
    },

    // 获取字段权限状态（用于复杂的表单处理）
    getFieldPermissionStatus: (fieldName) => {
      const canEdit = permissions.field?.[`canEdit${fieldName}`]?.() || false;

      return {
        canEdit,
        canView: true, // 暂时假设所有字段都可以查看
        mode: canEdit ? "edit" : "readonly",
        tooltip: canEdit ? null : "您没有编辑此字段的权限",
      };
    },
  };
};

export default useFieldPermissions;

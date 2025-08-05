import { usePermissions } from "./usePermissions";

/**
 * 按钮权限专用Hook
 * 提供常用按钮权限的快捷检查方法
 */
export const useButtonPermissions = () => {
  const permissions = usePermissions();

  return {
    // 项目相关按钮权限
    createProject: permissions.page?.canShowCreateProjectButton?.() || false,
    importProject: permissions.page?.canShowImportProjectButton?.() || false,
    exportProject: permissions.page?.canShowExportProjectButton?.() || false,
    deleteProject: permissions.page?.canShowDeleteProjectButton?.() || false,

    // 工作空间相关按钮权限
    createWorkspace: permissions.page?.canShowCreateWorkspaceButton?.() || false,
    editWorkspace: permissions.page?.canShowEditWorkspaceButton?.() || false,
    deleteWorkspace: permissions.page?.canShowDeleteWorkspaceButton?.() || false,

    // 用户管理相关按钮权限
    inviteUsers: permissions.page?.canShowInviteUsersButton?.() || false,
    manageUserRoles: permissions.page?.canShowManageUserRoles?.() || false,

    // 基础操作权限（直接来自action权限）
    canCreateProject: permissions.action?.canCreateProject?.() || false,
    canEditProject: permissions.action?.canEditProject?.() || false,
    canDeleteProject: permissions.action?.canDeleteProject?.() || false,
    canExportProjectData: permissions.action?.canExportProjectData?.() || false,
    canImportProjectData: permissions.action?.canImportProjectData?.() || false,

    canCreateWorkspace: permissions.action?.canCreateWorkspace?.() || false,
    canEditWorkspace: permissions.action?.canEditWorkspace?.() || false,
    canDeleteWorkspace: permissions.action?.canDeleteWorkspace?.() || false,
    canManageWorkspaces: permissions.action?.canManageWorkspaces?.() || false,

    // 标注操作权限
    canCreateAnnotation: permissions.action?.canCreateAnnotation?.() || false,
    canEditAnnotation: permissions.action?.canEditAnnotation?.() || false,
    canDeleteAnnotation: permissions.action?.canDeleteAnnotation?.() || false,
    canReviewAnnotation: permissions.action?.canReviewAnnotation?.() || false,

    // 管理权限
    canManageUsers: permissions.admin?.canManageUsers?.() || false,
    canManageRoles: permissions.admin?.canManageRoles?.() || false,
    canManageOrganization: permissions.admin?.canManageOrganization?.() || false,

    // 便捷方法：检查用户是否有任何管理权限
    hasAnyAdminPermission: () => {
      return permissions.hasAnyPermissionInCategory?.("admin") || false;
    },

    // 便捷方法：检查用户是否有任何项目管理权限
    hasAnyProjectManagementPermission: () => {
      const projectPermissions = [
        "create_project",
        "edit_project",
        "delete_project",
        "export_project_data",
        "import_project_data",
      ];
      return permissions.hasAnyPermission?.(projectPermissions) || false;
    },

    // 便捷方法：检查用户是否有任何工作空间管理权限
    hasAnyWorkspaceManagementPermission: () => {
      const workspacePermissions = [
        "create_workspace",
        "edit_workspace",
        "delete_workspace",
        "manage_workspaces",
        "manage_workspace_members",
      ];
      return permissions.hasAnyPermission?.(workspacePermissions) || false;
    },
  };
};

export default useButtonPermissions;

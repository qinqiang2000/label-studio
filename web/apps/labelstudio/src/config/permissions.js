/**
 * 权限系统配置文件 - 所有权限的统一定义
 *
 * 这个文件是权限系统的核心配置，所有权限都在这里定义。
 * 修改这个文件后，权限常量和Hook方法会自动生成。
 */

// ====== 权限系统模式配置 ======
export const PERMISSION_SYSTEM_CONFIG = {
  // 权限模式：'strict' 严格模式 | 'loose' 宽松模式
  mode: "loose",

  // 严格模式：所有UI元素都需要显式权限配置，未配置的元素不显示
  // 宽松模式：只有显式配置为需要权限的元素才检查权限，其他元素默认显示

  // 在宽松模式下生效的默认策略
  looseMode: {
    // 默认所有用户都能看到的UI区域
    defaultVisible: true,

    // 需要最低角色要求的UI区域
    roleBasedUI: {
      basic_ui: ["annotator", "workspace_admin", "superuser"],
      admin_ui: ["workspace_admin", "superuser"],
      super_ui: ["superuser"],
    },

    // 真正需要权限控制的危险操作
    dangerousOperations: [
      "delete_project",
      "delete_workspace",
      "manage_users",
      "manage_permissions",
      "system_settings",
    ],

    // 页面级权限简化映射
    // 将细粒度的按钮权限映射到页面级权限
    pagePermissionMapping: {
      // 项目管理页面
      project_management: ["show_create_project_button", "show_import_project_button", "show_export_project_button"],

      // 工作空间管理页面
      workspace_management: [
        "show_create_workspace_button",
        "show_edit_workspace_button",
        "show_delete_workspace_button",
      ],

      // 用户管理页面
      user_management: ["show_invite_users_button", "show_manage_user_roles", "show_permission_management_button"],
    },
  },
};

// 权限组定义 - 用于批量管理相关权限
export const PERMISSION_GROUPS = {
  // 基础用户权限组
  basic_user: {
    displayName: "基础用户权限",
    permissions: ["view_home", "view_projects", "view_workspaces", "view_account_settings"],
  },

  // 标注操作权限组
  annotation_operations: {
    displayName: "标注操作权限",
    permissions: ["create_annotation", "edit_annotation", "delete_annotation"],
  },

  // 项目基础设置权限组
  project_basic_settings: {
    displayName: "项目基础设置",
    permissions: [
      "view_project_general_settings",
      "view_project_labeling_settings",
      "view_project_annotation_settings",
    ],
  },

  // 项目管理权限组
  project_management: {
    displayName: "项目管理权限",
    permissions: ["create_project", "edit_project", "delete_project", "export_project_data", "import_project_data"],
  },

  // 项目删除权限组 - 包含删除项目所需的完整权限
  project_deletion: {
    displayName: "项目删除权限",
    permissions: ["view_project_danger_zone", "edit_project_danger_zone_fields", "delete_project"],
  },

  // 项目高级设置权限组
  project_advanced_settings: {
    displayName: "项目高级设置",
    permissions: [
      "view_project_machine_learning",
      "view_project_predictions",
      "view_project_cloud_storage",
      "view_project_webhooks",
      "view_project_danger_zone",
    ],
  },

  // 工作空间管理权限组
  workspace_management: {
    displayName: "工作空间管理",
    permissions: [
      "manage_workspaces",
      "create_workspace",
      "edit_workspace",
      "delete_workspace",
      "manage_workspace_members",
    ],
  },

  // 组织管理权限组
  organization_management: {
    displayName: "组织管理权限",
    permissions: [
      "view_organization",
      "manage_organization",
      "manage_users",
      "manage_roles",
      "view_prompts",
      "view_permission_management",
    ],
  },

  // 页面操作权限组
  page_operations: {
    displayName: "页面操作权限",
    permissions: [
      "show_create_project_button",
      "show_import_project_button",
      "show_export_project_button",
      // 'show_delete_project_button', // 已弃用：项目删除在危险区域中
      "show_create_workspace_button",
      "show_edit_workspace_button",
      "show_delete_workspace_button",
      "show_invite_users_button",
      "show_manage_user_roles",
      "show_permission_management_button",
    ],
  },

  // 表单字段权限组
  form_field_permissions: {
    displayName: "表单字段权限",
    permissions: [
      "edit_project_danger_zone_fields",
      "edit_project_ml_settings",
      "edit_project_webhook_settings",
      "edit_user_role_assignment",
      "edit_organization_settings",
    ],
  },
};

// ====== 简化权限定义 ======
// 这些是合并后的简化权限，用于解决管理员容易漏配权限的问题
export const SIMPLIFIED_PERMISSIONS = {
  // 项目管理简化权限
  project_create_full: {
    category: "simplified",
    displayName: "创建项目",
    description: "创建项目的完整权限，包含按钮显示和创建操作",
    hookMethod: "canCreateProjectFull",
    includes: ["view_projects", "create_project", "show_create_project_button"],
    group: "simplified_project",
  },

  project_delete_full: {
    category: "simplified",
    displayName: "删除项目",
    description: "删除项目的完整权限，包含访问危险区域和删除操作",
    hookMethod: "canDeleteProjectFull",
    includes: ["view_project_danger_zone", "edit_project_danger_zone_fields", "delete_project"],
    group: "simplified_project",
  },

  project_export_full: {
    category: "simplified",
    displayName: "导出项目",
    description: "导出项目的完整权限，包含按钮显示和导出操作",
    hookMethod: "canExportProjectFull",
    includes: ["export_project_data", "show_export_project_button"],
    group: "simplified_project",
  },

  project_import_full: {
    category: "simplified",
    displayName: "导入项目",
    description: "导入项目的完整权限，包含按钮显示和导入操作",
    hookMethod: "canImportProjectFull",
    includes: ["import_project_data", "show_import_project_button"],
    group: "simplified_project",
  },

  // 工作空间管理简化权限
  workspace_create_full: {
    category: "simplified",
    displayName: "创建工作空间",
    description: "创建工作空间的完整权限，包含按钮显示和创建操作",
    hookMethod: "canCreateWorkspaceFull",
    includes: ["view_workspaces", "create_workspace", "show_create_workspace_button"],
    group: "simplified_workspace",
  },

  workspace_manage_full: {
    category: "simplified",
    displayName: "管理工作空间",
    description: "管理工作空间的完整权限，包含编辑、删除和成员管理",
    hookMethod: "canManageWorkspaceFull",
    includes: [
      "manage_workspaces",
      "edit_workspace",
      "delete_workspace",
      "manage_workspace_members",
      "show_edit_workspace_button",
      "show_delete_workspace_button",
    ],
    group: "simplified_workspace",
  },

  // 标注操作简化权限
  annotation_full: {
    category: "simplified",
    displayName: "标注操作",
    description: "标注的完整操作权限，包含创建、编辑、删除和审核",
    hookMethod: "canAnnotationFull",
    includes: ["create_annotation", "edit_annotation", "delete_annotation", "review_annotation"],
    group: "simplified_annotation",
  },

  // 用户管理简化权限
  user_manage_full: {
    category: "simplified",
    displayName: "用户管理",
    description: "用户管理的完整权限，包含用户和角色管理",
    hookMethod: "canManageUsersFull",
    includes: [
      "manage_users",
      "manage_roles",
      "edit_user_role_assignment",
      "show_invite_users_button",
      "show_manage_user_roles",
    ],
    group: "simplified_admin",
  },

  // 组织管理简化权限
  organization_manage_full: {
    category: "simplified",
    displayName: "组织管理",
    description: "组织管理的完整权限，包含组织设置和权限管理",
    hookMethod: "canManageOrganizationFull",
    includes: ["view_organization", "manage_organization", "manage_permissions", "edit_organization_settings"],
    group: "simplified_admin",
  },

  // 项目设置访问简化权限
  project_settings_basic: {
    category: "simplified",
    displayName: "项目基础设置",
    description: "访问项目基础设置的权限",
    hookMethod: "canAccessProjectSettingsBasic",
    includes: ["view_project_general_settings", "view_project_labeling_settings", "view_project_annotation_settings"],
    group: "simplified_project",
  },

  project_settings_advanced: {
    category: "simplified",
    displayName: "项目高级设置",
    description: "访问项目高级设置的权限，包含ML、预测、存储等",
    hookMethod: "canAccessProjectSettingsAdvanced",
    includes: [
      "view_project_machine_learning",
      "view_project_predictions",
      "view_project_cloud_storage",
      "view_project_webhooks",
      "edit_project_ml_settings",
      "edit_project_webhook_settings",
    ],
    group: "simplified_project",
  },
};

// 简化权限组定义
export const SIMPLIFIED_PERMISSION_GROUPS = {
  // 基础用户权限组
  basic_user_simplified: {
    displayName: "基础用户",
    permissions: ["view_home", "view_projects", "view_workspaces", "view_account_settings"],
  },

  // 项目用户权限组
  project_user_simplified: {
    displayName: "项目用户",
    permissions: ["project_settings_basic", "annotation_full"],
  },

  // 项目管理员权限组
  project_admin_simplified: {
    displayName: "项目管理员",
    permissions: [
      "project_create_full",
      "project_delete_full",
      "project_export_full",
      "project_import_full",
      "project_settings_advanced",
    ],
  },

  // 工作空间管理员权限组
  workspace_admin_simplified: {
    displayName: "工作空间管理员",
    permissions: ["workspace_create_full", "workspace_manage_full"],
  },

  // 系统管理员权限组
  system_admin_simplified: {
    displayName: "系统管理员",
    permissions: ["user_manage_full", "organization_manage_full"],
  },
};

// 完整的权限定义配置（原有的详细权限，标记为高级选项）
export const PERMISSION_DEFINITIONS = {
  // ====== 菜单权限 ======
  view_home: {
    category: "menu",
    displayName: "Home菜单查看",
    description: "查看首页菜单",
    hookMethod: "canViewHome",
    group: "basic_user",
  },

  view_projects: {
    category: "menu",
    displayName: "Projects菜单查看",
    description: "查看项目列表菜单",
    hookMethod: "canViewProjects",
    group: "basic_user",
  },

  view_workspaces: {
    category: "menu",
    displayName: "Workspaces菜单查看",
    description: "查看工作空间菜单",
    hookMethod: "canViewWorkspaces",
    group: "basic_user",
  },

  view_prompts: {
    category: "menu",
    displayName: "Prompts菜单查看",
    description: "查看提示词菜单",
    hookMethod: "canViewPrompts",
    group: "organization_management",
  },

  view_organization: {
    category: "menu",
    displayName: "Organization菜单查看",
    description: "查看组织管理菜单",
    hookMethod: "canViewOrganization",
    group: "organization_management",
  },

  // 项目设置菜单权限
  view_project_general_settings: {
    category: "menu",
    displayName: "项目基本设置",
    description: "查看项目基本设置页面",
    hookMethod: "canViewProjectGeneralSettings",
    group: "project_basic_settings",
  },

  view_project_labeling_settings: {
    category: "menu",
    displayName: "项目标注设置",
    description: "查看项目标注设置页面",
    hookMethod: "canViewProjectLabelingSettings",
    group: "project_basic_settings",
  },

  view_project_annotation_settings: {
    category: "menu",
    displayName: "项目注释设置",
    description: "查看项目注释设置页面",
    hookMethod: "canViewProjectAnnotationSettings",
    group: "project_basic_settings",
  },

  view_project_machine_learning: {
    category: "menu",
    displayName: "项目机器学习设置",
    description: "查看项目机器学习设置页面",
    hookMethod: "canViewProjectMachineLearning",
    group: "project_advanced_settings",
  },

  view_project_predictions: {
    category: "menu",
    displayName: "项目预测设置",
    description: "查看项目预测设置页面",
    hookMethod: "canViewProjectPredictions",
    group: "project_advanced_settings",
  },

  view_project_cloud_storage: {
    category: "menu",
    displayName: "项目云存储设置",
    description: "查看项目云存储设置页面",
    hookMethod: "canViewProjectCloudStorage",
    group: "project_advanced_settings",
  },

  view_project_webhooks: {
    category: "menu",
    displayName: "项目Webhook设置",
    description: "查看项目Webhook设置页面",
    hookMethod: "canViewProjectWebhooks",
    group: "project_advanced_settings",
  },

  view_project_danger_zone: {
    category: "menu",
    displayName: "项目危险区域设置",
    description: "查看项目危险区域设置页面",
    hookMethod: "canViewProjectDangerZone",
    group: "project_advanced_settings",
  },

  view_account_settings: {
    category: "menu",
    displayName: "账户设置",
    description: "查看账户设置页面",
    hookMethod: "canViewAccountSettings",
    group: "basic_user",
  },

  view_permission_management: {
    category: "menu",
    displayName: "权限管理中心",
    description: "查看权限管理中心页面",
    hookMethod: "canViewPermissionManagement",
    group: "organization_management",
  },

  // ====== 操作权限 ======

  // 项目操作权限
  create_project: {
    category: "action",
    displayName: "创建项目",
    description: "创建新项目的权限",
    hookMethod: "canCreateProject",
    group: "project_management",
  },

  edit_project: {
    category: "action",
    displayName: "编辑项目",
    description: "编辑项目信息的权限",
    hookMethod: "canEditProject",
    group: "project_management",
  },

  delete_project: {
    category: "action",
    displayName: "删除项目",
    description: "删除项目的权限",
    hookMethod: "canDeleteProject",
    group: "project_management",
  },

  export_project_data: {
    category: "action",
    displayName: "导出项目数据",
    description: "导出项目数据的权限",
    hookMethod: "canExportProjectData",
    group: "project_management",
  },

  import_project_data: {
    category: "action",
    displayName: "导入项目数据",
    description: "导入项目数据的权限",
    hookMethod: "canImportProjectData",
    group: "project_management",
  },

  // 标注操作权限
  create_annotation: {
    category: "action",
    displayName: "创建标注",
    description: "创建新标注的权限",
    hookMethod: "canCreateAnnotation",
    group: "annotation_operations",
  },

  edit_annotation: {
    category: "action",
    displayName: "编辑标注",
    description: "编辑现有标注的权限",
    hookMethod: "canEditAnnotation",
    group: "annotation_operations",
  },

  delete_annotation: {
    category: "action",
    displayName: "删除标注",
    description: "删除标注的权限",
    hookMethod: "canDeleteAnnotation",
    group: "annotation_operations",
  },

  review_annotation: {
    category: "action",
    displayName: "审核标注",
    description: "审核标注质量的权限",
    hookMethod: "canReviewAnnotation",
    group: "annotation_operations",
  },

  // 工作空间操作权限
  manage_workspaces: {
    category: "action",
    displayName: "管理工作空间",
    description: "管理工作空间的权限",
    hookMethod: "canManageWorkspaces",
    group: "workspace_management",
  },

  create_workspace: {
    category: "action",
    displayName: "创建工作空间",
    description: "创建新工作空间的权限",
    hookMethod: "canCreateWorkspace",
    group: "workspace_management",
  },

  edit_workspace: {
    category: "action",
    displayName: "编辑工作空间",
    description: "编辑工作空间信息的权限",
    hookMethod: "canEditWorkspace",
    group: "workspace_management",
  },

  delete_workspace: {
    category: "action",
    displayName: "删除工作空间",
    description: "删除工作空间的权限",
    hookMethod: "canDeleteWorkspace",
    group: "workspace_management",
  },

  manage_workspace_members: {
    category: "action",
    displayName: "管理工作空间成员",
    description: "管理工作空间成员的权限",
    hookMethod: "canManageWorkspaceMembers",
    group: "workspace_management",
  },

  // 用户管理权限
  manage_users: {
    category: "admin",
    displayName: "管理用户",
    description: "管理系统用户的权限",
    hookMethod: "canManageUsers",
    group: "organization_management",
  },

  manage_roles: {
    category: "admin",
    displayName: "管理角色",
    description: "管理用户角色的权限",
    hookMethod: "canManageRoles",
    group: "organization_management",
  },

  manage_permissions: {
    category: "admin",
    displayName: "管理权限",
    description: "管理系统权限的权限",
    hookMethod: "canManagePermissions",
    group: "organization_management",
  },

  // 组织管理权限
  manage_organization: {
    category: "admin",
    displayName: "管理组织",
    description: "管理组织设置的权限",
    hookMethod: "canManageOrganization",
    group: "organization_management",
  },

  // ====== 页面操作权限 ======

  // 项目页面操作权限
  show_create_project_button: {
    category: "page_operation",
    displayName: "显示创建项目按钮",
    description: "控制创建项目按钮的显示",
    hookMethod: "canShowCreateProjectButton",
    group: "page_operations",
  },

  show_import_project_button: {
    category: "page_operation",
    displayName: "显示导入项目按钮",
    description: "控制导入项目按钮的显示",
    hookMethod: "canShowImportProjectButton",
    group: "page_operations",
  },

  show_export_project_button: {
    category: "page_operation",
    displayName: "显示导出项目按钮",
    description: "控制导出项目按钮的显示",
    hookMethod: "canShowExportProjectButton",
    group: "page_operations",
  },

  // 注意：项目删除功能在项目设置的危险区域中，不是独立按钮
  // 此权限已弃用，请使用 view_project_danger_zone + edit_project_danger_zone_fields + delete_project 组合
  show_delete_project_button: {
    category: "deprecated",
    displayName: "[已弃用] 显示删除项目按钮",
    description: "此权限已弃用。项目删除在危险区域中，请使用相关权限组合",
    hookMethod: "canShowDeleteProjectButton",
    group: "page_operations",
    deprecated: true,
  },

  // 工作空间页面操作权限
  show_create_workspace_button: {
    category: "page_operation",
    displayName: "显示创建工作空间按钮",
    description: "控制创建工作空间按钮的显示",
    hookMethod: "canShowCreateWorkspaceButton",
    group: "page_operations",
  },

  show_edit_workspace_button: {
    category: "page_operation",
    displayName: "显示编辑工作空间按钮",
    description: "控制编辑工作空间按钮的显示",
    hookMethod: "canShowEditWorkspaceButton",
    group: "page_operations",
  },

  show_delete_workspace_button: {
    category: "page_operation",
    displayName: "显示删除工作空间按钮",
    description: "控制删除工作空间按钮的显示",
    hookMethod: "canShowDeleteWorkspaceButton",
    group: "page_operations",
  },

  // 用户管理页面操作权限
  show_invite_users_button: {
    category: "page_operation",
    displayName: "显示邀请用户按钮",
    description: "控制邀请用户按钮的显示",
    hookMethod: "canShowInviteUsersButton",
    group: "page_operations",
  },

  show_manage_user_roles: {
    category: "page_operation",
    displayName: "显示管理用户角色",
    description: "控制用户角色管理功能的显示",
    hookMethod: "canShowManageUserRoles",
    group: "page_operations",
  },

  show_permission_management_button: {
    category: "page_operation",
    displayName: "显示权限管理按钮",
    description: "控制权限管理按钮的显示",
    hookMethod: "canShowPermissionManagementButton",
    group: "page_operations",
  },

  // ====== 表单字段权限 ======

  // 项目设置表单字段权限
  edit_project_danger_zone_fields: {
    category: "field_permission",
    displayName: "编辑项目危险区域字段",
    description: "控制项目危险区域字段的编辑权限",
    hookMethod: "canEditProjectDangerZoneFields",
    group: "form_field_permissions",
  },

  edit_project_ml_settings: {
    category: "field_permission",
    displayName: "编辑项目机器学习设置",
    description: "控制项目机器学习设置字段的编辑权限",
    hookMethod: "canEditProjectMLSettings",
    group: "form_field_permissions",
  },

  edit_project_webhook_settings: {
    category: "field_permission",
    displayName: "编辑项目Webhook设置",
    description: "控制项目Webhook设置字段的编辑权限",
    hookMethod: "canEditProjectWebhookSettings",
    group: "form_field_permissions",
  },

  // 用户管理表单字段权限
  edit_user_role_assignment: {
    category: "field_permission",
    displayName: "编辑用户角色分配",
    description: "控制用户角色分配字段的编辑权限",
    hookMethod: "canEditUserRoleAssignment",
    group: "form_field_permissions",
  },

  edit_organization_settings: {
    category: "field_permission",
    displayName: "编辑组织设置",
    description: "控制组织设置字段的编辑权限",
    hookMethod: "canEditOrganizationSettings",
    group: "form_field_permissions",
  },
};

// 角色权限配置 - 使用权限组简化配置
export const ROLE_PERMISSION_CONFIG = {
  annotator: {
    displayName: "标注员",
    description: "标注员，拥有基础的标注和项目访问权限",
    groups: ["basic_user", "annotation_operations", "project_basic_settings"],
    additionalPermissions: [], // 额外的单个权限
  },

  workspace_admin: {
    displayName: "工作空间管理员",
    description: "工作空间管理员，可以管理所属工作空间的项目和成员",
    inheritFrom: "annotator", // 继承annotator的所有权限
    groups: ["project_management", "workspace_management", "project_advanced_settings", "page_operations"],
    additionalPermissions: [], // 额外的单个权限
  },

  superuser: {
    displayName: "超级管理员",
    description: "超级管理员，拥有系统所有权限",
    groups: "all", // 拥有所有权限
  },
};

// 工具函数：获取角色的所有权限
export const getRolePermissions = (roleName) => {
  const roleConfig = ROLE_PERMISSION_CONFIG[roleName];
  if (!roleConfig) return [];

  const permissions = [];

  // 处理权限继承
  if (roleConfig.inheritFrom) {
    permissions.push(...getRolePermissions(roleConfig.inheritFrom));
  }

  // 处理权限组
  if (roleConfig.groups === "all") {
    // 拥有所有权限
    permissions.push(...Object.keys(PERMISSION_DEFINITIONS));
  } else if (Array.isArray(roleConfig.groups)) {
    // 基于权限组获取权限
    roleConfig.groups.forEach((groupName) => {
      const group = PERMISSION_GROUPS[groupName];
      if (group) {
        permissions.push(...group.permissions);
      }
    });
  }

  // 添加额外的单个权限
  if (roleConfig.additionalPermissions) {
    permissions.push(...roleConfig.additionalPermissions);
  }

  // 去重并返回
  return [...new Set(permissions)];
};

// 工具函数：获取所有权限分类
export const getPermissionsByCategory = (category) => {
  return Object.fromEntries(
    Object.entries(PERMISSION_DEFINITIONS)
      .filter(([_, config]) => config.category === category)
      .map(([key, _]) => [key.toUpperCase(), key]),
  );
};

// 工具函数：验证权限定义的完整性
export const validatePermissionDefinitions = () => {
  const errors = [];

  // 检查hookMethod的唯一性
  const hookMethods = new Set();
  Object.entries(PERMISSION_DEFINITIONS).forEach(([permission, config]) => {
    if (hookMethods.has(config.hookMethod)) {
      errors.push(`重复的hookMethod: ${config.hookMethod} (权限: ${permission})`);
    }
    hookMethods.add(config.hookMethod);
  });

  // 检查权限组中的权限是否都存在
  Object.entries(PERMISSION_GROUPS).forEach(([groupName, group]) => {
    group.permissions.forEach((permission) => {
      if (!PERMISSION_DEFINITIONS[permission]) {
        errors.push(`权限组 ${groupName} 中的权限 ${permission} 不存在`);
      }
    });
  });

  return errors;
};

// ====== 简化权限工具函数 ======

/**
 * 检查用户是否拥有简化权限
 * @param {string} simplifiedPermission - 简化权限名称
 * @param {Object} userPermissions - 用户当前权限对象
 * @returns {boolean} 是否拥有完整权限
 */
export const hasSimplifiedPermission = (simplifiedPermission, userPermissions) => {
  const permissionDef = SIMPLIFIED_PERMISSIONS[simplifiedPermission];
  if (!permissionDef || !permissionDef.includes) {
    return false;
  }

  // 检查是否拥有所有包含的权限
  return permissionDef.includes.every((permission) => userPermissions[permission]);
};

/**
 * 获取简化权限所包含的所有详细权限
 * @param {string} simplifiedPermission - 简化权限名称
 * @returns {string[]} 包含的详细权限列表
 */
export const getIncludedPermissions = (simplifiedPermission) => {
  const permissionDef = SIMPLIFIED_PERMISSIONS[simplifiedPermission];
  return permissionDef ? permissionDef.includes || [] : [];
};

/**
 * 从用户的详细权限中推导出拥有的简化权限
 * @param {Object} userPermissions - 用户当前权限对象
 * @returns {Object} 用户拥有的简化权限对象
 */
export const deriveSimplifiedPermissions = (userPermissions) => {
  const simplifiedPermissions = {};

  for (const [simplifiedPerm, permDef] of Object.entries(SIMPLIFIED_PERMISSIONS)) {
    simplifiedPermissions[simplifiedPerm] = hasSimplifiedPermission(simplifiedPerm, userPermissions);
  }

  return simplifiedPermissions;
};

/**
 * 将简化权限转换为详细权限列表
 * @param {string[]} simplifiedPermissions - 简化权限列表
 * @returns {string[]} 详细权限列表（去重）
 */
export const expandSimplifiedPermissions = (simplifiedPermissions) => {
  const detailedPermissions = new Set();

  for (const simplifiedPerm of simplifiedPermissions) {
    const included = getIncludedPermissions(simplifiedPerm);
    included.forEach((perm) => detailedPermissions.add(perm));
  }

  return Array.from(detailedPermissions);
};

/**
 * 获取简化的角色权限配置
 * @param {string} roleName - 角色名称
 * @returns {Object} 简化后的角色权限配置
 */
export const getSimplifiedRolePermissions = (roleName) => {
  const simplifiedRoleConfigs = {
    annotator: {
      displayName: "标注员",
      description: "标注员，拥有基础的标注和项目访问权限",
      simplifiedPermissions: [
        "view_home",
        "view_projects",
        "view_workspaces",
        "view_account_settings",
        "project_settings_basic",
        "annotation_full",
      ],
    },

    workspace_admin: {
      displayName: "工作空间管理员",
      description: "工作空间管理员，可以管理所属工作空间的项目和成员",
      simplifiedPermissions: [
        "view_home",
        "view_projects",
        "view_workspaces",
        "view_account_settings",
        "project_settings_basic",
        "annotation_full",
        "project_create_full",
        "project_delete_full",
        "project_export_full",
        "project_import_full",
        "project_settings_advanced",
        "workspace_create_full",
        "workspace_manage_full",
      ],
    },

    superuser: {
      displayName: "超级管理员",
      description: "超级管理员，拥有系统所有权限",
      simplifiedPermissions: "all", // 拥有所有简化权限
    },
  };

  const roleConfig = simplifiedRoleConfigs[roleName];
  if (!roleConfig) return { simplifiedPermissions: [] };

  if (roleConfig.simplifiedPermissions === "all") {
    // 拥有所有简化权限
    roleConfig.simplifiedPermissions = Object.keys(SIMPLIFIED_PERMISSIONS);
  }

  return roleConfig;
};

/**
 * 验证简化权限配置的完整性
 * @returns {string[]} 错误信息列表
 */
export const validateSimplifiedPermissions = () => {
  const errors = [];

  // 检查简化权限中包含的详细权限是否都存在
  for (const [simplifiedPerm, permDef] of Object.entries(SIMPLIFIED_PERMISSIONS)) {
    if (permDef.includes) {
      for (const includedPerm of permDef.includes) {
        if (!PERMISSION_DEFINITIONS[includedPerm]) {
          errors.push(`简化权限 ${simplifiedPerm} 包含的权限 ${includedPerm} 不存在`);
        }
      }
    }
  }

  return errors;
};

// 导出验证结果（开发时使用）
if (process.env.NODE_ENV === "development") {
  const errors = validatePermissionDefinitions();
  const simplifiedErrors = validateSimplifiedPermissions();

  if (errors.length > 0 || simplifiedErrors.length > 0) {
    console.warn("权限配置验证失败:", [...errors, ...simplifiedErrors]);
  } else {
    console.log("✅ 权限配置验证通过");
  }
}

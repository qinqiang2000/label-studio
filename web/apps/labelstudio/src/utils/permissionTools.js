/**
 * 权限配置工具集
 * 用于简化权限管理和配置
 */

import { PERMISSION_SYSTEM_CONFIG, PERMISSION_DEFINITIONS } from "../config/permissions";

/**
 * 权限配置分析工具
 */
export class PermissionAnalyzer {
  constructor() {
    this.config = PERMISSION_SYSTEM_CONFIG;
    this.definitions = PERMISSION_DEFINITIONS;
  }

  /**
   * 分析当前权限配置的复杂度
   */
  analyzeComplexity() {
    const totalPermissions = Object.keys(this.definitions).length;
    const buttonPermissions = Object.entries(this.definitions).filter(
      ([_, config]) => config.category === "page_operation",
    ).length;

    const complexity = {
      totalPermissions,
      buttonPermissions,
      complexityRatio: buttonPermissions / totalPermissions,
      recommendation: this.getComplexityRecommendation(buttonPermissions / totalPermissions),
    };

    return complexity;
  }

  /**
   * 根据复杂度比例给出建议
   */
  getComplexityRecommendation(ratio) {
    if (ratio > 0.3) {
      return "权限配置过于复杂，建议启用宽松模式或简化按钮权限";
    } else if (ratio > 0.2) {
      return "权限配置较为复杂，可以考虑部分简化";
    } else {
      return "权限配置合理";
    }
  }

  /**
   * 查找未使用的权限
   */
  findUnusedPermissions() {
    // 这里可以扩展为扫描代码文件，查找实际使用的权限
    const definedPermissions = Object.keys(this.definitions);
    const dangerousOperations = this.config.looseMode.dangerousOperations;

    return definedPermissions.filter(
      (permission) =>
        !dangerousOperations.includes(permission) && this.definitions[permission].category === "page_operation",
    );
  }

  /**
   * 生成权限迁移建议
   */
  generateMigrationSuggestions() {
    const suggestions = [];

    // 检查可以简化的按钮权限
    const buttonPermissions = this.findUnusedPermissions();
    if (buttonPermissions.length > 0) {
      suggestions.push({
        type: "simplify_buttons",
        message: `可以简化 ${buttonPermissions.length} 个按钮权限，改为角色级控制`,
        permissions: buttonPermissions.slice(0, 5), // 只显示前5个
        action: "use_role_based_ui",
      });
    }

    // 检查是否适合启用宽松模式
    const complexity = this.analyzeComplexity();
    if (complexity.complexityRatio > 0.2) {
      suggestions.push({
        type: "enable_loose_mode",
        message: "当前权限配置较复杂，建议启用宽松模式",
        action: "set_mode_to_loose",
      });
    }

    return suggestions;
  }
}

/**
 * 权限配置生成器
 */
export class PermissionGenerator {
  /**
   * 生成简化的按钮配置
   */
  static generateSimpleButton(options = {}) {
    const { requireRole = null, dangerLevel = null, fallback = "hide" } = options;

    const props = { fallback };

    if (requireRole) props.requireRole = requireRole;
    if (dangerLevel) props.dangerLevel = dangerLevel;

    return props;
  }

  /**
   * 生成页面级权限配置
   */
  static generatePagePermission(pageName, requiredRole = "admin_ui") {
    return {
      [pageName]: {
        type: "page",
        requireRole: requiredRole,
        description: `${pageName} 页面访问权限`,
      },
    };
  }

  /**
   * 为现有权限生成简化建议
   */
  static generateSimplificationSuggestions(permissions) {
    return permissions
      .map((permission) => {
        const config = PERMISSION_DEFINITIONS[permission];
        if (!config) return null;

        const suggestion = {
          old: `permission="${permission}"`,
          new: null,
          reason: "",
        };

        // 根据权限类型生成建议
        if (config.category === "page_operation") {
          if (permission.includes("admin") || permission.includes("manage")) {
            suggestion.new = 'requireRole="admin_ui"';
            suggestion.reason = "管理功能建议使用角色控制";
          } else {
            suggestion.new = "无需权限配置";
            suggestion.reason = "普通操作建议直接显示";
          }
        }

        return suggestion;
      })
      .filter(Boolean);
  }
}

/**
 * 权限配置验证器
 */
export class PermissionValidator {
  /**
   * 验证权限配置的一致性
   */
  static validateConsistency() {
    const errors = [];
    const warnings = [];

    // 检查模式配置
    if (!["strict", "loose"].includes(PERMISSION_SYSTEM_CONFIG.mode)) {
      errors.push("无效的权限模式配置");
    }

    // 检查角色配置
    const roleBasedUI = PERMISSION_SYSTEM_CONFIG.looseMode.roleBasedUI;
    for (const [uiArea, roles] of Object.entries(roleBasedUI)) {
      if (!Array.isArray(roles)) {
        errors.push(`UI区域 ${uiArea} 的角色配置应该是数组`);
      }
    }

    // 检查危险操作配置
    const dangerousOps = PERMISSION_SYSTEM_CONFIG.looseMode.dangerousOperations;
    for (const operation of dangerousOps) {
      if (!PERMISSION_DEFINITIONS[operation]) {
        warnings.push(`危险操作 ${operation} 在权限定义中不存在`);
      }
    }

    return { errors, warnings };
  }

  /**
   * 检查权限使用情况
   */
  static checkPermissionUsage() {
    // 这里可以扩展为实际的代码扫描
    const definedPermissions = Object.keys(PERMISSION_DEFINITIONS);
    const usageStats = {
      total: definedPermissions.length,
      used: 0,
      unused: 0,
      categories: {},
    };

    // 统计各类别的权限数量
    for (const [permission, config] of Object.entries(PERMISSION_DEFINITIONS)) {
      const category = config.category;
      if (!usageStats.categories[category]) {
        usageStats.categories[category] = 0;
      }
      usageStats.categories[category]++;
    }

    return usageStats;
  }
}

/**
 * 开发者工具
 */
export const PermissionDevTools = {
  /**
   * 在控制台输出权限分析报告
   */
  printAnalysisReport() {
    const analyzer = new PermissionAnalyzer();
    const complexity = analyzer.analyzeComplexity();
    const suggestions = analyzer.generateMigrationSuggestions();
    const validation = PermissionValidator.validateConsistency();

    console.group("🔐 权限系统分析报告");
    console.log("复杂度分析:", complexity);
    console.log("迁移建议:", suggestions);
    console.log("配置验证:", validation);
    console.groupEnd();
  },

  /**
   * 获取当前权限模式
   */
  getCurrentMode() {
    return PERMISSION_SYSTEM_CONFIG.mode;
  },

  /**
   * 切换权限模式（仅开发环境）
   */
  toggleMode() {
    if (process.env.NODE_ENV === "development") {
      const currentMode = PERMISSION_SYSTEM_CONFIG.mode;
      PERMISSION_SYSTEM_CONFIG.mode = currentMode === "strict" ? "loose" : "strict";
      console.log(`权限模式已切换为: ${PERMISSION_SYSTEM_CONFIG.mode}`);
      return PERMISSION_SYSTEM_CONFIG.mode;
    } else {
      console.warn("权限模式切换仅在开发环境可用");
    }
  },
};

// 开发环境下自动添加到全局变量
if (process.env.NODE_ENV === "development") {
  window.PermissionDevTools = PermissionDevTools;

  // 自动分析并输出报告
  setTimeout(() => {
    PermissionDevTools.printAnalysisReport();
  }, 1000);
}

import { SidebarMenu } from "../../components/SidebarMenu/SidebarMenu";
import { WebhookPage } from "../WebhookPage/WebhookPage";
import { DangerZone } from "./DangerZone";
import { GeneralSettings } from "./GeneralSettings";
import { AnnotationSettings } from "./AnnotationSettings";
import { LabelingSettings } from "./LabelingSettings";
import { MachineLearningSettings } from "./MachineLearningSettings/MachineLearningSettings";
import { PredictionsSettings } from "./PredictionsSettings/PredictionsSettings";
import { StorageSettings } from "./StorageSettings/StorageSettings";
import { isInLicense, LF_CLOUD_STORAGE_FOR_MANAGERS } from "../../utils/license-flags";
import { usePermissions } from "../../hooks/usePermissions";

const isAllowCloudStorage = !isInLicense(LF_CLOUD_STORAGE_FOR_MANAGERS);

export const MenuLayout = ({ children, ...routeProps }) => {
  const permissions = usePermissions();

  // 根据权限过滤菜单项
  const getFilteredMenuItems = () => {
    const menuItems = [];

    // General Settings - 所有用户都可以访问
    if (permissions.menu.canViewProjectGeneralSettings()) {
      menuItems.push(GeneralSettings);
    }

    // Labeling Settings - 标注相关设置
    if (permissions.menu.canViewProjectLabelingSettings()) {
      menuItems.push(LabelingSettings);
    }

    // Annotation Settings - 标注设置
    if (permissions.menu.canViewProjectAnnotationSettings()) {
      menuItems.push(AnnotationSettings);
    }

    // Machine Learning - 仅管理员可访问
    if (permissions.menu.canViewProjectMachineLearning()) {
      menuItems.push(MachineLearningSettings);
    }

    // Predictions - 预测设置
    if (permissions.menu.canViewProjectPredictions()) {
      menuItems.push(PredictionsSettings);
    }

    // Cloud Storage - 需要许可证和权限
    if (isAllowCloudStorage && permissions.menu.canViewProjectCloudStorage()) {
      menuItems.push(StorageSettings);
    }

    // Webhooks - 仅管理员可访问
    if (permissions.menu.canViewProjectWebhooks()) {
      menuItems.push(WebhookPage);
    }

    // Danger Zone - 仅管理员可访问
    if (permissions.menu.canViewProjectDangerZone()) {
      menuItems.push(DangerZone);
    }

    return menuItems;
  };

  return <SidebarMenu menuItems={getFilteredMenuItems()} path={routeProps.match.url} children={children} />;
};

const pages = {
  AnnotationSettings,
  LabelingSettings,
  MachineLearningSettings,
  PredictionsSettings,
  WebhookPage,
  DangerZone,
};

isAllowCloudStorage && (pages.StorageSettings = StorageSettings);

export const SettingsPage = {
  title: "Settings",
  path: "/settings",
  exact: true,
  layout: MenuLayout,
  component: GeneralSettings,
  pages,
};

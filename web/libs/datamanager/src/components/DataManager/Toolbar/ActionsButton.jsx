import { inject, observer } from "mobx-react";
import { useCallback, useRef, useState } from "react";
import { IconChevronRight, IconChevronDown, IconTrash } from "@humansignal/icons";
import { Block, Elem } from "../../../utils/bem";
import { FF_LOPS_E_3, isFF } from "../../../utils/feature-flags";
import { Button } from "../../Common/Button/Button";
import { Dropdown } from "../../Common/Dropdown/DropdownComponent";
import Form from "../../Common/Form/Form";
import { Menu } from "../../Common/Menu/Menu";
import { Modal } from "../../Common/Modal/ModalPopup";
import { EvaluationResultModal } from "../EvaluationResultModal";
import "./ActionsButton.scss";

const isFFLOPSE3 = isFF(FF_LOPS_E_3);
const injector = inject(({ store }) => ({
  store,
  hasSelected: store.currentView?.selected?.hasSelected ?? false,
}));

const buildDialogContent = (text, form, formRef) => {
  return (
    <Block name="dialog-content">
      <Elem name="text">{text}</Elem>
      {form && (
        <Elem name="form" style={{ paddingTop: 16 }}>
          <Form.Builder ref={formRef} fields={form.toJSON()} autosubmit={false} withActions={false} />
        </Elem>
      )}
    </Block>
  );
};

export const ActionsButton = injector(
  observer(({ store, size, hasSelected, ...rest }) => {
    const formRef = useRef();
    const [batchProgress, setBatchProgress] = useState(null);
    const [evaluationResult, setEvaluationResult] = useState(null);
    const [showEvaluationModal, setShowEvaluationModal] = useState(false);
    const selectedCount = store.currentView.selectedCount;
    const actions = store.availableActions.filter((a) => !a.hidden).sort((a, b) => a.order - b.order);

    // 获取所有任务ID的方法（仅用于retrieve_tasks_predictions）
    const getAllTaskIds = async () => {
      try {
        const view = store.currentView ?? {};
        const params = {
          page_size: 500, // 使用较大的数值获取更多任务
        };

        // 添加视图相关参数
        if (view.query) {
          params.query = view.query;
        } else if (view.id) {
          params.view = view.id;
        }

        console.log("[DEBUG] 获取所有任务ID，参数:", params);
        const response = await store.apiCall("tasks", params);
        const taskIds = response.tasks?.map((task) => task.id) || [];
        console.log("[DEBUG] 成功获取所有任务ID，数量:", taskIds.length);
        return taskIds;
      } catch (error) {
        console.error("[DEBUG] 获取所有任务ID失败:", error);
        return [];
      }
    };

    const handleBatchPredictions = async (action, params) => {
      console.log("[DEBUG] handleBatchPredictions 开始执行", { action: action.id, params });

      // 处理两种不同的参数格式：直接调用模式和对话框模式
      const body = params?.body || params;
      let selectedItems = body?.selectedItems;
      console.log("[DEBUG] 处理后的body:", body);
      console.log("[DEBUG] 原始selectedItems:", selectedItems);

      // 确保selectedItems有正确的格式
      if (!selectedItems) {
        console.log("[DEBUG] selectedItems为空，使用默认值");
        selectedItems = { all: false, included: [] };
      }

      // 如果selectedItems不是期望的对象格式，尝试修正
      if (Array.isArray(selectedItems)) {
        console.log("[DEBUG] selectedItems是数组，转换为对象格式");
        selectedItems = { all: false, included: selectedItems };
      }

      console.log("[DEBUG] 处理后的selectedItems:", selectedItems);

      // 更新body中的selectedItems
      if (body) {
        body.selectedItems = selectedItems;
      }

      // 检查是否为单个任务或无选择：
      // 1. 没有选中项
      // 2. 只选中1个任务且不是全选状态
      const isNoSelection =
        !selectedItems ||
        (!selectedItems.all && (!selectedItems.included?.length || selectedItems.included.length === 0));
      const isSingleTask = !selectedItems.all && selectedItems.included?.length === 1;

      if (isNoSelection || isSingleTask) {
        console.log("[DEBUG] 单个任务或无选择，使用原有逻辑");
        console.log("[DEBUG] 选择状态 - all:", selectedItems?.all, "included length:", selectedItems?.included?.length);

        try {
          // 对于retrieve_tasks_predictions，我们需要特殊处理以避免全局错误弹窗
          let result;
          if (action.id === "retrieve_tasks_predictions") {
            // 使用suppressError来避免全局错误处理
            result = await store.invokeAction(action.id, {
              ...params,
              suppressError: true, // 阻止全局错误处理
            });
          } else {
            result = await store.invokeAction(action.id, params?.body ? params : { body: params });
          }

          // 检查是否有ML后端配置相关的错误
          if (result && result.error) {
            const errorMessage = result.error_message || result.detail || result.error;

            if (result.error === "no_ml_backend") {
              store.SDK.invoke("toast", {
                message: errorMessage,
                type: "error",
                duration: 8000,
              });
              return result;
            } else if (result.error === "ml_backend_disconnected") {
              store.SDK.invoke("toast", {
                message: errorMessage,
                type: "error",
                duration: 8000,
              });
              return result;
            } else if (result.error === "ml_backend_error") {
              store.SDK.invoke("toast", {
                message: errorMessage,
                type: "error",
                duration: 8000,
              });
              return result;
            } else if (result.error === "ml_backend_not_ready") {
              store.SDK.invoke("toast", {
                message: errorMessage,
                type: "warning",
                duration: 8000,
              });
              return result;
            }
          }

          // 检查是否有ML错误
          if (result && result.ml_errors && result.ml_errors.length > 0) {
            console.warn("[ML ERRORS] 单个任务处理有ML错误:", result.ml_errors);

            // 构建错误摘要
            const errorSummary = result.error_summary || {};
            const summaryText = Object.entries(errorSummary)
              .map(([type, count]) => `${type}: ${count}`)
              .join(", ");

            // 显示详细错误信息
            const errorMessages = result.ml_errors.map((error) => {
              const taskInfo = error.task_id ? ` (Task: ${error.task_id})` : "";
              return `${error.error_type}: ${error.error_message}${taskInfo}`;
            });

            store.SDK.invoke("toast", {
              message: `预测完成但有错误: ${summaryText}`,
              type: "warning",
              duration: 8000,
            });

            // 在控制台显示详细错误
            console.error("[ML ERRORS] 详细错误信息:", errorMessages);
          }

          return result;
        } catch (error) {
          console.error("[DEBUG] 单个任务处理失败:", error);

          // 检查是否是store.invokeAction返回的错误信息
          if (error && typeof error === "object") {
            const errorMessage = error.error_message || error.detail || error.message || error.error || "任务处理失败";

            store.SDK.invoke("toast", {
              message: errorMessage,
              type: "error",
              duration: 8000,
            });
          } else {
            store.SDK.invoke("toast", {
              message: error?.message || "任务处理失败",
              type: "error",
              duration: 8000,
            });
          }

          throw error;
        }
      }

      // 获取要处理的任务ID列表
      let taskIds;
      if (selectedItems.all) {
        // 全选状态：从后端获取所有任务ID（仅用于retrieve_tasks_predictions）
        console.log("[DEBUG] 全选模式：从后端获取所有任务ID");
        taskIds = await getAllTaskIds();

        if (taskIds.length === 0) {
          store.SDK.invoke("toast", {
            message: "无法获取任务列表，请重试",
            type: "error",
          });
          return;
        }
      } else {
        // 部分选择：使用included数组
        taskIds = selectedItems.included || [];
        console.log("[DEBUG] 部分选择模式：使用included数组");
      }

      console.log("[DEBUG] 开始批量处理，任务数量:", taskIds.length, "任务IDs:", taskIds);

      setBatchProgress({ current: 0, total: taskIds.length });

      // 用于收集批量处理过程中的错误信息
      const batchErrors = [];
      let successCount = 0;
      let failureCount = 0;

      try {
        store.SDK.invoke("toast", {
          message: `开始处理 ${taskIds.length} 个任务的预测... (1/${taskIds.length})`,
          type: "info",
          duration: -1,
        });

        for (let i = 0; i < taskIds.length; i++) {
          const taskId = taskIds[i];
          console.log(`[DEBUG] 处理第 ${i + 1}/${taskIds.length} 个任务，ID: ${taskId}`);

          // 构造单个任务的payload
          const singleTaskBody = {
            ...body,
            selectedItems: {
              all: false,
              included: [taskId],
            },
          };

          console.log("[DEBUG] 单个任务请求体:", singleTaskBody);

          try {
            console.log(`[DEBUG] 开始调用 store.invokeAction，任务ID: ${taskId}`);
            const result = await store.invokeAction(action.id, { body: singleTaskBody });
            console.log(`[DEBUG] 任务 ${taskId} 处理成功，结果:`, result);

            // 检查是否有ML错误
            if (result && result.ml_errors && result.ml_errors.length > 0) {
              console.warn(`[ML ERRORS] 任务 ${taskId} 有ML错误:`, result.ml_errors);

              // 收集错误信息到批量错误数组中
              result.ml_errors.forEach((error) => {
                batchErrors.push({
                  taskId: taskId,
                  error_type: error.error_type,
                  error_message: error.error_message,
                });
              });

              failureCount++;
            } else {
              successCount++;
            }

            setBatchProgress({ current: i + 1, total: taskIds.length });

            // 更新toast进度
            store.SDK.invoke("toast", {
              message: `处理中... (${i + 2}/${taskIds.length})`,
              type: "info",
              duration: -1,
            });

            // 添加小延迟避免过于频繁的请求
            if (i < taskIds.length - 1) {
              console.log("[DEBUG] 等待100ms后处理下一个任务");
              await new Promise((resolve) => setTimeout(resolve, 100));
            }
          } catch (error) {
            console.error(`[DEBUG] 任务 ${taskId} 处理失败:`, error);

            // 收集处理失败的错误信息
            batchErrors.push({
              taskId: taskId,
              error_type: "ProcessingError",
              error_message: error.message || "任务处理失败",
            });

            failureCount++;
          }
        }

        console.log("[DEBUG] 所有任务处理完成");

        // 根据处理结果显示不同的消息
        if (batchErrors.length === 0) {
          // 全部成功
          store.SDK.invoke("toast", {
            message: `成功处理完成 ${taskIds.length} 个任务的预测！`,
            type: "success",
          });
        } else if (successCount > 0) {
          // 部分成功，部分有错误
          const errorSummary = {};
          batchErrors.forEach((error) => {
            errorSummary[error.error_type] = (errorSummary[error.error_type] || 0) + 1;
          });

          const summaryText = Object.entries(errorSummary)
            .map(([type, count]) => `${type}: ${count}`)
            .join(", ");

          store.SDK.invoke("toast", {
            message: `批量预测完成: ${successCount} 个成功，${failureCount} 个有错误 (${summaryText})`,
            type: "warning",
            duration: 10000,
          });

          // 在控制台显示详细错误信息
          console.error("[ML ERRORS] 批量处理详细错误信息:", batchErrors);
        } else {
          // 全部失败
          store.SDK.invoke("toast", {
            message: `批量预测失败: ${failureCount} 个任务处理失败`,
            type: "error",
            duration: 8000,
          });
        }
      } catch (error) {
        console.error("[DEBUG] 批量处理失败:", error);
        store.SDK.invoke("toast", {
          message: "批量处理过程中发生错误",
          type: "error",
        });
      } finally {
        console.log("[DEBUG] 清理批量处理状态");
        setBatchProgress(null);
      }
    };

    const invokeAction = (action, destructive) => {
      if (action.dialog) {
        const { type: dialogType, text, form, title } = action.dialog;
        const dialog = Modal[dialogType] ?? Modal.confirm;

        dialog({
          title: title ? title : destructive ? "Destructive action" : "Confirm action",
          body: buildDialogContent(text, form, formRef),
          buttonLook: destructive ? "destructive" : "primary",
          onOk() {
            let body = formRef.current?.assembleFormData({ asJSON: true });

            // 对于retrieve_tasks_predictions，需要确保包含selectedItems信息
            if (action.id === "retrieve_tasks_predictions") {
              const view = store.currentView ?? {};
              const { selected } = view;

              // 如果没有表单数据，创建空对象
              if (!body) {
                body = {};
              }

              // 确保包含selectedItems信息
              if (!body.selectedItems) {
                body.selectedItems = selected?.snapshot || { all: false, included: [] };
              }

              console.log("[DEBUG] 对话框模式：补充选中任务信息后的body:", body);
            }

            store.SDK.invoke("actionDialogOk", action.id, { body });

            // 为retrieve_tasks_predictions使用批量处理
            if (action.id === "retrieve_tasks_predictions") {
              console.log("[DEBUG] 检测到 retrieve_tasks_predictions 动作，路由到批量处理函数");
              console.log("[DEBUG] 对话框模式传递的body参数:", body);
              return handleBatchPredictions(action, { body });
            } else if (
              action.id === "evaluate_annotations_vs_predictions" ||
              action.id === "evaluate_invoice_extraction_task" ||
              action.id === "evaluate_document_extraction_task"
            ) {
              console.log("[DEBUG] 检测到评估动作:", action.id);
              store
                .invokeAction(action.id, { body })
                .then((result) => {
                  if (result && result.evaluation_results) {
                    console.log("[DEBUG] 收到evaluation结果:", result);
                    setEvaluationResult(result);
                    setShowEvaluationModal(true);
                  }
                })
                .catch((error) => {
                  console.error("[DEBUG] Evaluation动作执行失败:", error);
                });
            } else {
              console.log("[DEBUG] 使用标准 invokeAction 处理动作:", action.id);
              store.invokeAction(action.id, { body });
            }
          },
          closeOnClickOutside: false,
        });
      } else {
        // 为retrieve_tasks_predictions使用批量处理
        if (action.id === "retrieve_tasks_predictions") {
          console.log("[DEBUG] 直接调用模式：检测到 retrieve_tasks_predictions 动作");
          const view = store.currentView ?? {};
          const { selected } = view;
          console.log("[DEBUG] 当前视图选择状态:", selected?.snapshot);
          const actionParams = {
            ordering: view.ordering,
            selectedItems: selected?.snapshot ?? { all: false, included: [] },
            filters: {
              conjunction: view.conjunction ?? "and",
              items: view.serializedFilters ?? [],
            },
          };
          console.log("[DEBUG] 构造的动作参数:", actionParams);
          handleBatchPredictions(action, actionParams);
        } else if (
          action.id === "evaluate_annotations_vs_predictions" ||
          action.id === "evaluate_invoice_extraction_task" ||
          action.id === "evaluate_document_extraction_task"
        ) {
          console.log("[DEBUG] 直接调用模式：检测到评估动作:", action.id);
          store
            .invokeAction(action.id)
            .then((result) => {
              if (result && result.evaluation_results) {
                console.log("[DEBUG] 收到evaluation结果:", result);
                setEvaluationResult(result);
                setShowEvaluationModal(true);
              }
            })
            .catch((error) => {
              console.error("[DEBUG] Evaluation动作执行失败:", error);
            });
        } else {
          console.log("[DEBUG] 直接调用模式：使用标准 invokeAction 处理动作:", action.id);
          store.invokeAction(action.id);
        }
      }
    };

    const ActionButton = (action, parentRef) => {
      const isDeleteAction = action.id.includes("delete");
      const hasChildren = !!action.children?.length;
      const submenuRef = useRef();
      const onClick = useCallback(
        (e) => {
          e.preventDefault();
          if (action.disabled) return;
          action?.callback
            ? action?.callback(store.currentView?.selected?.snapshot, action)
            : invokeAction(action, isDeleteAction);
          parentRef?.current?.close?.();
        },
        [store.currentView?.selected],
      );
      const titleContainer = (
        <Block
          key={action.id}
          tag={Menu.Item}
          size={size}
          onClick={onClick}
          mod={{
            hasSeperator: isDeleteAction,
            hasSubMenu: action.children?.length > 0,
            isSeparator: action.isSeparator,
            isTitle: action.isTitle,
            danger: isDeleteAction,
            disabled: action.disabled,
          }}
          name="actionButton"
        >
          <Elem name="titleContainer" {...(action.disabled ? { title: action.disabledReason } : {})}>
            <Elem name="title">{action.title}</Elem>
            {hasChildren ? <Elem name="icon" tag={IconChevronRight} /> : null}
          </Elem>
        </Block>
      );

      return hasChildren ? (
        <Dropdown.Trigger
          key={action.id}
          align="top-right-outside"
          toggle={false}
          ref={submenuRef}
          content={
            <Block name="actionButton-submenu" tag="ul">
              {action.children.map(ActionButton, parentRef)}
            </Block>
          }
        >
          {titleContainer}
        </Dropdown.Trigger>
      ) : (
        <Menu.Item
          size={size}
          key={action.id}
          danger={isDeleteAction}
          onClick={onClick}
          className={`actionButton${action.isSeparator ? "_isSeparator" : action.isTitle ? "_isTitle" : ""} ${
            action.disabled ? "actionButton_disabled" : ""
          }`}
          icon={isDeleteAction && <IconTrash />}
          title={action.disabled ? action.disabledReason : null}
        >
          {action.title}
        </Menu.Item>
      );
    };

    const actionButtons = actions.map(ActionButton);
    const recordTypeLabel = isFFLOPSE3 && store.SDK.type === "DE" ? "Record" : "Task";

    return (
      <>
        <Dropdown.Trigger
          content={<Menu size="compact">{actionButtons}</Menu>}
          openUpwardForShortViewport={false}
          disabled={!hasSelected || batchProgress !== null}
        >
          <Button size={size} disabled={!hasSelected || batchProgress !== null} {...rest}>
            {batchProgress
              ? `处理中... ${batchProgress.current + 1}/${batchProgress.total}`
              : selectedCount > 0
                ? `${selectedCount} ${recordTypeLabel}${selectedCount > 1 ? "s" : ""}`
                : "Actions"}
            <IconChevronDown style={{ marginLeft: 4, marginRight: -7 }} />
          </Button>
        </Dropdown.Trigger>

        {/* Evaluation Result Modal */}
        {showEvaluationModal && evaluationResult && (
          <EvaluationResultModal
            result={evaluationResult}
            onClose={() => {
              setShowEvaluationModal(false);
              setEvaluationResult(null);
            }}
          />
        )}
      </>
    );
  }),
);

export default ActionsButton;

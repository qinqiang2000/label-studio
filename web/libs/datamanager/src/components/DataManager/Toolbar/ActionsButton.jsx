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
import { Space } from "../../Common/Space/Space";
import { Tooltip } from "@humansignal/ui";
import { isDefined } from "../../../utils/utils";
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
          page_size: 500,  // 使用较大的数值获取更多任务
        };
        
        // 添加视图相关参数
        if (view.query) {
          params.query = view.query;
        } else if (view.id) {
          params.view = view.id;
        }
        
        console.log('[DEBUG] 获取所有任务ID，参数:', params);
        const response = await store.apiCall('tasks', params);
        const taskIds = response.tasks?.map(task => task.id) || [];
        console.log('[DEBUG] 成功获取所有任务ID，数量:', taskIds.length);
        return taskIds;
      } catch (error) {
        console.error('[DEBUG] 获取所有任务ID失败:', error);
        return [];
      }
    };

    const handleBatchPredictions = async (action, params) => {
      console.log('[DEBUG] handleBatchPredictions 开始执行', { action: action.id, params });
      
      // 处理两种不同的参数格式：直接调用模式和对话框模式
      const body = params?.body || params;
      const selectedItems = body?.selectedItems;
      console.log('[DEBUG] 处理后的body:', body);
      console.log('[DEBUG] selectedItems:', selectedItems);
      
      // 检查是否为单个任务或无选择：
      // 1. 没有选中项
      // 2. 只选中1个任务且不是全选状态
      const isNoSelection = !selectedItems || (!selectedItems.all && (!selectedItems.included?.length || selectedItems.included.length === 0));
      const isSingleTask = !selectedItems.all && selectedItems.included?.length === 1;
      
      if (isNoSelection || isSingleTask) {
        console.log('[DEBUG] 单个任务或无选择，使用原有逻辑');
        console.log('[DEBUG] 选择状态 - all:', selectedItems?.all, 'included length:', selectedItems?.included?.length);
        return store.invokeAction(action.id, params?.body ? params : { body: params });
      }
  
      // 获取要处理的任务ID列表
      let taskIds;
      if (selectedItems.all) {
        // 全选状态：从后端获取所有任务ID（仅用于retrieve_tasks_predictions）
        console.log('[DEBUG] 全选模式：从后端获取所有任务ID');
        taskIds = await getAllTaskIds();
        
        if (taskIds.length === 0) {
          store.SDK.invoke("toast", { 
            message: "无法获取任务列表，请重试", 
            type: "error" 
          });
          return;
        }
      } else {
        // 部分选择：使用included数组
        taskIds = selectedItems.included || [];
        console.log('[DEBUG] 部分选择模式：使用included数组');
      }
      
      console.log('[DEBUG] 开始批量处理，任务数量:', taskIds.length, '任务IDs:', taskIds);
      
      setBatchProgress({ current: 0, total: taskIds.length });
      
      try {
        store.SDK.invoke("toast", { 
          message: `开始处理 ${taskIds.length} 个任务的预测... (1/${taskIds.length})`, 
          type: "info",
          duration: -1
        });

        for (let i = 0; i < taskIds.length; i++) {
          const taskId = taskIds[i];
          console.log(`[DEBUG] 处理第 ${i + 1}/${taskIds.length} 个任务，ID: ${taskId}`);
          
          // 构造单个任务的payload
          const singleTaskBody = {
            ...body,
            selectedItems: {
              all: false,
              included: [taskId]
            }
          };
          
          console.log('[DEBUG] 单个任务请求体:', singleTaskBody);
          
          try {
            console.log(`[DEBUG] 开始调用 store.invokeAction，任务ID: ${taskId}`);
            await store.invokeAction(action.id, { body: singleTaskBody });
            console.log(`[DEBUG] 任务 ${taskId} 处理成功`);
            
            setBatchProgress({ current: i + 1, total: taskIds.length });
            
            // 更新toast进度
            store.SDK.invoke("toast", { 
              message: `处理中... (${i + 2}/${taskIds.length})`, 
              type: "info",
              duration: -1
            });
            
            // 添加小延迟避免过于频繁的请求
            if (i < taskIds.length - 1) {
              console.log('[DEBUG] 等待100ms后处理下一个任务');
              await new Promise(resolve => setTimeout(resolve, 100));
            }
          } catch (error) {
            console.error(`[DEBUG] 任务 ${taskId} 处理失败:`, error);
            store.SDK.invoke("toast", { 
              message: `任务 ${taskId} 处理失败，继续处理其他任务...`, 
              type: "warning" 
            });
          }
        }
        
        console.log('[DEBUG] 所有任务处理完成');
        store.SDK.invoke("toast", { 
          message: `成功处理完成 ${taskIds.length} 个任务的预测！`, 
          type: "success" 
        });
      } catch (error) {
        console.error('[DEBUG] 批量处理失败:', error);
        store.SDK.invoke("toast", { 
          message: "批量处理过程中发生错误", 
          type: "error" 
        });
      } finally {
        console.log('[DEBUG] 清理批量处理状态');
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
            
            // 如果没有表单数据，为retrieve_tasks_predictions构造选中任务的body
            if (!body && action.id === 'retrieve_tasks_predictions') {
              const view = store.currentView ?? {};
              const { selected } = view;
              body = {
                selectedItems: selected?.snapshot || []
              };
              console.log('[DEBUG] 对话框模式：没有表单，构造选中任务body:', body);
            }

            store.SDK.invoke("actionDialogOk", action.id, { body });
            
            // 为retrieve_tasks_predictions使用批量处理
             if (action.id === 'retrieve_tasks_predictions') {
               console.log('[DEBUG] 检测到 retrieve_tasks_predictions 动作，路由到批量处理函数');
               console.log('[DEBUG] 对话框模式传递的body参数:', body);
               return handleBatchPredictions(action, { body });
             } else if (action.id === 'evaluate_annotations_vs_predictions' || action.id === 'evaluate_invoice_extraction_task') {
               console.log('[DEBUG] 检测到评估动作:', action.id);
               store.invokeAction(action.id, { body }).then((result) => {
                 if (result && result.evaluation_results) {
                   console.log('[DEBUG] 收到evaluation结果:', result);
                   setEvaluationResult(result);
                   setShowEvaluationModal(true);
                 }
               }).catch((error) => {
                 console.error('[DEBUG] Evaluation动作执行失败:', error);
               });
             } else {
               console.log('[DEBUG] 使用标准 invokeAction 处理动作:', action.id);
               store.invokeAction(action.id, { body });
             }
          },
          closeOnClickOutside: false,
        });
      } else {
        // 为retrieve_tasks_predictions使用批量处理
        if (action.id === 'retrieve_tasks_predictions') {
          console.log('[DEBUG] 直接调用模式：检测到 retrieve_tasks_predictions 动作');
          const view = store.currentView ?? {};
          const { selected } = view;
          console.log('[DEBUG] 当前视图选择状态:', selected?.snapshot);
          const actionParams = {
            ordering: view.ordering,
            selectedItems: selected?.snapshot ?? { all: false, included: [] },
            filters: {
              conjunction: view.conjunction ?? "and",
              items: view.serializedFilters ?? [],
            },
          };
          console.log('[DEBUG] 构造的动作参数:', actionParams);
          handleBatchPredictions(action, actionParams);
        } else if (action.id === 'evaluate_annotations_vs_predictions' || action.id === 'evaluate_invoice_extraction_task') {
          console.log('[DEBUG] 直接调用模式：检测到评估动作:', action.id);
          store.invokeAction(action.id).then((result) => {
            if (result && result.evaluation_results) {
              console.log('[DEBUG] 收到evaluation结果:', result);
              setEvaluationResult(result);
              setShowEvaluationModal(true);
            }
          }).catch((error) => {
            console.error('[DEBUG] Evaluation动作执行失败:', error);
          });
        } else {
          console.log('[DEBUG] 直接调用模式：使用标准 invokeAction 处理动作:', action.id);
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
            {batchProgress ? (
              `处理中... ${batchProgress.current + 1}/${batchProgress.total}`
            ) : (
              selectedCount > 0 ? `${selectedCount} ${recordTypeLabel}${selectedCount > 1 ? "s" : ""}` : "Actions"
            )}
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

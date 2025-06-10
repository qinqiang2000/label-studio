# 票据评估功能架构图与点击流程

## 架构图

```mermaid
flowchart TD
    subgraph 前端
      A[用户点击"Evaluate Invoice Extraction"按钮]
      B[前端通过API调用 /api/dm/actions POST]
    end
    subgraph 后端
      C[ProjectActionsAPI.post]
      D[perform_action]
      E[settings.DATA_MANAGER_ACTIONS 查找 action]
      F[evaluate_invoice_extraction_task]
      G[评估逻辑: 数据比对/统计/生成Excel]
      H[返回评估结果和Excel路径]
    end
    A-->|触发|B
    B-->|POST id=evaluate_invoice_extraction_task<br>project=项目ID|C
    C-->|参数校验/查找项目/权限|D
    D-->|查找 action_id 并校验权限|E
    E-->|找到 entry_point: evaluate_invoice_extraction_task|F
    F-->|执行评估流程|G
    G-->|返回结果|H
    H-->|响应|B
    B-->|展示评估结果|A
```

## 点击流程说明

1. 用户在前端界面点击"Evaluate Invoice Extraction"按钮。
2. 前端通过 POST /api/dm/actions 接口，传递 action id（如 evaluate_invoice_extraction_task）和项目ID等参数。
3. 后端 ProjectActionsAPI 接收到请求，校验参数和权限。
4. perform_action 根据 action_id 查找对应的 action，并校验用户权限。
5. 找到 entry_point（evaluate_invoice_extraction_task），执行评估逻辑，包括数据比对、统计、生成Excel报告等。
6. 评估结果和Excel路径通过API返回给前端。
7. 前端展示评估结果，用户可下载Excel报告。 
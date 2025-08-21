import { useState, useCallback, useEffect } from "react";
import { Select, Button } from "@humansignal/ui";
import { Block, Elem } from "../../utils/bem";
import { TextArea } from "../Form";
import { EvaluationMatchingStrategyConfig } from "./EvaluationMatchingStrategyConfig";
import "./EvaluationFieldsConfig.scss";

export const EvaluationFieldsConfig = ({ project, onUpdate }) => {
  const [documentType, setDocumentType] = useState("invoice");
  const [customFields, setCustomFields] = useState("");
  const [isEditing, setIsEditing] = useState(false);
  const [matchingStrategy, setMatchingStrategy] = useState(null);
  const [activeTab, setActiveTab] = useState("fields");
  const [documentTypeConfigs, setDocumentTypeConfigs] = useState({});
  const [isLoadingConfigs, setIsLoadingConfigs] = useState(true);

  // 新增状态：项目级评估字段自定义
  const [customEvaluationFields, setCustomEvaluationFields] = useState([]);
  const [isFieldCustomizationMode, setIsFieldCustomizationMode] = useState(false);
  
  // 添加状态来存储从API获取的字段配置（与TextArea.jsx保持一致）
  const [apiEvaluationConfig, setApiEvaluationConfig] = useState(null);

  // 从后端API获取文档类型配置
  useEffect(() => {
    const fetchDocumentTypeConfigs = async () => {
      try {
        setIsLoadingConfigs(true);
        const response = await fetch("/api/frontend/evaluation-configs/presets/", {
          headers: {
            "Content-Type": "application/json",
          },
        });

        if (response.ok) {
          const presets = await response.json();

          // 转换为组件需要的格式
          const configs = {};
          Object.keys(presets).forEach((key) => {
            const config = presets[key];
            configs[key] = {
              label: config.name,
              fields: config.required_fields || config.fields || [],
              description: config.description || `适用于${config.name}的评估`,
            };
          });

          // 如果后端返回空配置，使用兜底配置
          if (Object.keys(configs).length === 0) {
            console.warn("[EvaluationFieldsConfig] Backend returned empty configurations, using fallback");
            setDocumentTypeConfigs({
              invoice: {
                label: "发票 (Invoice)",
                fields: [
                  "totalAmount",
                  "invoiceDate",
                  "docType",
                  "currency",
                  "billToName",
                  "billFromName",
                  "totalTaxAmount",
                ],
                description: "适用于发票和收据的评估",
              },
              bank_receipt: {
                label: "银行回单 (Bank Receipt)",
                fields: [
                  "tradeId",
                  "recieptNum",
                  "logNum",
                  "tradeDate",
                  "amount",
                  "paymentName",
                  "paymentBank",
                  "paymentAccount",
                  "payeeName",
                  "payeeBank",
                  "payeeAccount",
                  "currency",
                ],
                description: "适用于银行回单的评估",
              },
              custom: {
                label: "自定义 (Custom)",
                fields: [],
                description: "自定义评估字段",
              },
            });
          } else {
            setDocumentTypeConfigs(configs);
          }
          console.log("[EvaluationFieldsConfig] Loaded document type configurations from backend:", configs);
        } else {
          console.warn("[EvaluationFieldsConfig] Failed to load document type configurations, using fallback");
          // 兜底配置
          setDocumentTypeConfigs({
            invoice: {
              label: "发票 (Invoice)",
              fields: [
                "totalAmount",
                "invoiceDate",
                "docType",
                "currency",
                "billToName",
                "billFromName",
                "totalTaxAmount",
              ],
              description: "适用于发票和收据的评估",
            },
            bank_receipt: {
              label: "银行回单 (Bank Receipt)",
              fields: [
                "tradeId",
                "recieptNum",
                "logNum",
                "tradeDate",
                "amount",
                "paymentName",
                "paymentBank",
                "paymentAccount",
                "payeeName",
                "payeeBank",
                "payeeAccount",
                "currency",
              ],
              description: "适用于银行回单的评估",
            },
            custom: {
              label: "自定义 (Custom)",
              fields: [],
              description: "自定义评估字段",
            },
          });
        }
      } catch (error) {
        console.error("[EvaluationFieldsConfig] Error fetching document type configurations:", error);
        // 兜底配置
        setDocumentTypeConfigs({
          invoice: {
            label: "发票 (Invoice)",
            fields: [
              "totalAmount",
              "invoiceDate",
              "docType",
              "currency",
              "billToName",
              "billFromName",
              "totalTaxAmount",
            ],
            description: "适用于发票和收据的评估",
          },
          bank_receipt: {
            label: "银行回单 (Bank Receipt)",
            fields: [
              "tradeId",
              "recieptNum",
              "logNum",
              "tradeDate",
              "amount",
              "paymentName",
              "paymentBank",
              "paymentAccount",
              "payeeName",
              "payeeBank",
              "payeeAccount",
              "currency",
            ],
            description: "适用于银行回单的评估",
          },
          custom: {
            label: "自定义 (Custom)",
            fields: [],
            description: "自定义评估字段",
          },
        });
      } finally {
        setIsLoadingConfigs(false);
      }
    };

    fetchDocumentTypeConfigs();
  }, []);

  // 获取API字段配置的预设数据
  useEffect(() => {
    const loadApiPresets = async () => {
      try {
        // 使用预设配置API，这与你提供的数据结构一致
        const response = await fetch(`/api/frontend/evaluation-configs/presets/`);
        if (response.ok) {
          const presets = await response.json();
          setApiEvaluationConfig(presets);
        }
      } catch (error) {
        console.warn('Failed to load API presets:', error);
      }
    };

    loadApiPresets();
  }, []);

  // 从项目配置中加载当前设置
  useEffect(() => {
    if (isLoadingConfigs) return; // 等待配置加载完成

    const config = project?.evaluation_field_config || {};
    if (config.document_type) {
      setDocumentType(config.document_type);
    }
    if (config.document_type === "custom" && config.default_fields) {
      setCustomFields(config.default_fields.join(", "));
    }
    if (config.matching_strategy) {
      setMatchingStrategy(config.matching_strategy);
    }

    // 加载项目级评估字段配置
    if (config.evaluation_fields) {
      setCustomEvaluationFields(config.evaluation_fields);
      setIsFieldCustomizationMode(true);
    }
  }, [project, isLoadingConfigs]);

  // 当文档类型变化时的处理逻辑
  useEffect(() => {
    if (documentType !== "custom") {
      setCustomFields("");
      // 重置字段自定义模式
      setIsFieldCustomizationMode(false);
      setCustomEvaluationFields([]);
    }
  }, [documentType]);

  // 获取当前配置的字段列表
  const getCurrentFields = useCallback(() => {
    if (documentType === "custom") {
      return customFields
        .split(",")
        .map((f) => f.trim())
        .filter(Boolean);
    }

    // 如果是字段自定义模式，返回自定义评估字段
    if (isFieldCustomizationMode) {
      return customEvaluationFields;
    }

    return documentTypeConfigs[documentType]?.fields || [];
  }, [documentType, customFields, documentTypeConfigs, isFieldCustomizationMode, customEvaluationFields]);

  // 评估字段管理函数
  const initializeCustomFields = useCallback(() => {
    const templateFields = (documentTypeConfigs[documentType] && documentTypeConfigs[documentType].fields) ? documentTypeConfigs[documentType].fields : [];
    // 将模板字段作为评估字段初始化
    setCustomEvaluationFields([...templateFields]);
    setIsFieldCustomizationMode(true);
  }, [documentType, documentTypeConfigs]);

  const addEvaluationField = useCallback(
    (fieldName) => {
      if (!fieldName.trim()) return;

      const trimmedField = fieldName.trim();
      if (!customEvaluationFields.includes(trimmedField)) {
        setCustomEvaluationFields((prev) => [...prev, trimmedField]);
      }
    },
    [customEvaluationFields],
  );

  const removeEvaluationField = useCallback((fieldName) => {
    setCustomEvaluationFields((prev) => prev.filter((f) => f !== fieldName));
  }, []);

  const resetToTemplate = useCallback(() => {
    setIsFieldCustomizationMode(false);
    setCustomEvaluationFields([]);
  }, []);

  // 获取可用字段选项（排除已添加的字段）
  const getAvailableFieldOptions = useCallback(() => {
    // 根据当前选择的文档类型获取对应的字段
    let availableFields = [];

    // 1. 优先从 API 预设配置中获取当前文档类型的字段
    if (apiEvaluationConfig && apiEvaluationConfig[documentType]) {
      const presetConfig = apiEvaluationConfig[documentType];
      availableFields = presetConfig.fields || [];
    }
    // 2. 如果 API 没有数据，则从本地 documentTypeConfigs 获取
    else if (documentTypeConfigs[documentType]?.fields) {
      availableFields = [...documentTypeConfigs[documentType].fields];
    }

    // 3. 确保序号字段始终可用
    if (!availableFields.includes("序号")) {
      availableFields = ["序号", ...availableFields];
    }

    // 过滤掉已经在 customEvaluationFields 中存在的字段
    const filteredFields = availableFields.filter((field) => !customEvaluationFields.includes(field));

    // 返回适合 Select 组件的格式
    return filteredFields.map((field) => ({
      value: field,
      label: field,
    }));
  }, [documentType, documentTypeConfigs, customEvaluationFields, apiEvaluationConfig]);

  // 保存配置
  const handleSave = useCallback(async () => {
    const fields = getCurrentFields();

    try {
      // 仅使用项目PATCH接口，不修改全局EvaluationFieldConfig
      const config = {
        document_type: documentType,
        default_fields: fields, // 兼容现有逻辑
        evaluation_fields: fields, // 新增：专用于评估模块的字段
        matching_strategy: matchingStrategy,
        last_updated: new Date().toISOString(),
      };

      const response = await fetch(`/api/projects/${project.id}/`, {
        method: "PATCH",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          evaluation_field_config: config,
        }),
      });

      if (response.ok) {
        onUpdate && onUpdate();
        setIsEditing(false);
      }
    } catch (error) {
      console.error("Failed to save evaluation config:", error);
    }
  }, [project.id, documentType, customFields, getCurrentFields, onUpdate, matchingStrategy]);

  const currentConfig = project?.evaluation_field_config || {};
  const currentFields = getCurrentFields();

  // 显示加载状态
  if (isLoadingConfigs) {
    return (
      <Block name="evaluation-fields-config">
        <Elem name="header">
          <Elem name="title">评估字段配置</Elem>
          <Elem name="description">正在加载配置...</Elem>
        </Elem>
      </Block>
    );
  }

  return (
    <Block name="evaluation-fields-config">
      <Elem name="header">
        <Elem name="title">评估字段配置</Elem>
        <Elem name="description">配置不同文档类型的评估字段，用于自动化评估功能</Elem>
      </Elem>

      {!isEditing ? (
        <Elem name="display">
          <Elem name="current-config">
            <Elem name="item">
              <Elem name="label">文档类型:</Elem>
              <Elem name="value">
                {documentTypeConfigs[currentConfig.document_type || "invoice"]?.label || "发票 (Invoice)"}
              </Elem>
            </Elem>
            <Elem name="description-text">
              {documentTypeConfigs[currentConfig.document_type || "invoice"]?.description || "适用于发票的评估"}
            </Elem>

            {currentConfig.document_type &&
              documentTypeConfigs[currentConfig.document_type] &&
              documentTypeConfigs[currentConfig.document_type].fields && (
                <Elem name="predefined-fields">
                  <Elem name="fields-label">预定义字段:</Elem>
                  <Elem name="fields-list">
                    {documentTypeConfigs[currentConfig.document_type].fields.map((field) => (
                      <Elem key={field} name="field-tag">
                        {field}
                      </Elem>
                    ))}
                  </Elem>
                </Elem>
              )}

            <Elem name="item">
              <Elem name="label">当前配置字段:</Elem>
              <Elem name="current-fields">
                {(() => {
                  // 优先显示自定义评估字段
                  if (currentConfig.evaluation_fields) {
                    return currentConfig.evaluation_fields.join(", ") || "无";
                  }

                  // 否则显示模板字段
                  return (
                    (
                      documentTypeConfigs[currentConfig.document_type || "invoice"]?.fields ||
                      documentTypeConfigs.invoice?.fields ||
                      []
                    ).join(", ") || "无"
                  );
                })()}
              </Elem>
            </Elem>

            {/* 显示自定义评估字段 */}
            {currentConfig.evaluation_fields && (
              <Elem name="item">
                <Elem name="label">自定义评估字段:</Elem>
                <Elem name="value">{currentConfig.evaluation_fields.join(", ")}</Elem>
              </Elem>
            )}
          </Elem>
          <Elem name="edit-button">
            <Button look="primary" onClick={() => setIsEditing(true)}>
              编辑配置
            </Button>
          </Elem>
        </Elem>
      ) : (
        <Elem name="editor">
          <Elem name="form-container">
            <Elem name="form-row">
              {/* <Elem name="form-group"> */}
              <label htmlFor="document-type-select">文档类型</label>
              <Select
                id="document-type-select"
                value={documentType}
                onChange={setDocumentType}
                options={Object.entries(documentTypeConfigs).map(([key, config]) => ({
                  value: key,
                  label: config.label,
                }))}
                placeholder="选择文档类型"
                className="evaluation-config-select"
              />
              {/* </Elem> */}
            </Elem>

            <Elem name="description-section">{documentTypeConfigs[documentType]?.description}</Elem>

            {documentType === "custom" ? (
              <Elem name="form-row">
                <Elem name="form-group">
                  <label htmlFor="custom-fields-textarea">自定义字段 (用逗号分隔)</label>
                  <TextArea
                    id="custom-fields-textarea"
                    value={customFields}
                    onChange={(e) => setCustomFields(e.target.value)}
                    placeholder="例如: totalAmount, invoiceDate, docType, currency"
                    rows={4}
                    style={{ minHeight: 100 }}
                    className="custom-fields-textarea"
                  />
                </Elem>
              </Elem>
            ) : (
              <Elem name="template-fields-section">
                {/* 模板字段自定义选项 */}
                <Elem name="customization-options">
                  {!isFieldCustomizationMode ? (
                    <Elem name="template-mode">
                      <Elem name="predefined-fields">
                        <Elem name="fields-label">预定义字段:</Elem>
                        <Elem name="fields-list">
                          {documentTypeConfigs[documentType] && documentTypeConfigs[documentType].fields && documentTypeConfigs[documentType].fields.map((field, index) => (
                            <Elem key={field} name="field-tag">
                              {field}
                            </Elem>
                          )) || <span>无预定义字段</span>}
                        </Elem>
                      </Elem>
                      <Button 
                        look="secondary" 
                        onClick={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          // 使用 setTimeout 确保在不同浏览器中的兼容性
                          setTimeout(() => {
                            initializeCustomFields();
                          }, 0);
                        }} 
                        style={{ marginTop: "10px" }}
                      >
                        自定义此模板的字段
                      </Button>
                    </Elem>
                  ) : (
                    <Elem name="custom-mode">
                      <Elem name="customization-header">
                        <Elem name="title">基于 {documentTypeConfigs[documentType]?.label} 模板自定义评估字段</Elem>
                      </Elem>

                      {/* 评估字段编辑 */}
                      <Elem name="field-group">
                        <Elem name="field-group-header">
                          <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                            <Select
                              placeholder="选择要添加的字段"
                              options={getAvailableFieldOptions()}
                              onChange={(selectedField) => {
                                if (selectedField) addEvaluationField(selectedField);
                              }}
                              value={null}
                              className="add-field-select"
                              style={{ width: 180 }}
                              disabled={getAvailableFieldOptions().length === 0}
                            />
                            <Button
                              look="secondary"
                              size="small"
                              onClick={() => {
                                const fieldName = prompt("请输入自定义字段名:");
                                if (fieldName) addEvaluationField(fieldName);
                              }}
                            >
                              自定义字段
                            </Button>
                            {getAvailableFieldOptions().length === 0 && (
                              <span style={{ color: "#999", fontSize: "12px" }}>所有预定义字段已添加</span>
                            )}
                          </div>
                          <Button look="secondary" size="small" onClick={resetToTemplate}>
                            重置为模板
                          </Button>
                        </Elem>
                        <Elem name="fields-list editable">
                          {customEvaluationFields.map((field) => (
                            <Elem key={field} name="field-tag editable">
                              <span>{field}</span>
                              <button onClick={() => removeEvaluationField(field)} className="remove-field">
                                ×
                              </button>
                            </Elem>
                          ))}
                        </Elem>
                      </Elem>
                    </Elem>
                  )}
                </Elem>
              </Elem>
            )}

            <Elem name="preview">
              <Elem name="preview-label">当前配置字段:</Elem>
              <Elem name="preview-fields">{currentFields.join(", ") || "无"}</Elem>
            </Elem>

            {/* 匹配策略配置 */}
            <Elem name="strategy-section">
              <EvaluationMatchingStrategyConfig
                value={matchingStrategy}
                onChange={setMatchingStrategy}
                documentType={documentType}
                evaluationFields={currentFields}
                disabled={false}
              />
            </Elem>

            <Elem name="actions">
              <Button look="primary" onClick={handleSave} style={{ marginRight: "9px" }}>
                保存配置
              </Button>
              <Button
                look="default"
                onClick={() => {
                  setIsEditing(false);
                  // 重置到当前配置
                  const config = project?.evaluation_field_config || {};
                  setDocumentType(config.document_type || "invoice");
                  if (config.document_type === "custom" && config.default_fields) {
                    setCustomFields(config.default_fields.join(", "));
                  } else {
                    setCustomFields("");
                  }

                  // 重置评估字段自定义状态
                  if (config.evaluation_fields) {
                    setCustomEvaluationFields(config.evaluation_fields);
                    setIsFieldCustomizationMode(true);
                  } else {
                    setCustomEvaluationFields([]);
                    setIsFieldCustomizationMode(false);
                  }
                }}
              >
                取消
              </Button>
            </Elem>
          </Elem>
        </Elem>
      )}
    </Block>
  );
};

import React, { useState, useCallback, useEffect } from "react";
import { Select, Button, Tabs } from "@humansignal/ui";
import { Block, Elem } from "../../utils/bem";
import { Form, Input, TextArea } from "../Form";
import { EvaluationMatchingStrategyConfig } from "./EvaluationMatchingStrategyConfig";
import "./EvaluationFieldsConfig.scss";

export const EvaluationFieldsConfig = ({ project, onUpdate }) => {
  const [documentType, setDocumentType] = useState('invoice');
  const [customFields, setCustomFields] = useState('');
  const [isEditing, setIsEditing] = useState(false);
  const [matchingStrategy, setMatchingStrategy] = useState(null);
  const [activeTab, setActiveTab] = useState('fields');
  const [documentTypeConfigs, setDocumentTypeConfigs] = useState({});
  const [isLoadingConfigs, setIsLoadingConfigs] = useState(true);

  // 从后端API获取文档类型配置
  useEffect(() => {
    const fetchDocumentTypeConfigs = async () => {
      try {
        setIsLoadingConfigs(true);
        const response = await fetch('/api/frontend/evaluation-configs/presets/', {
          headers: {
            'Content-Type': 'application/json',
          },
        });
        
        if (response.ok) {
          const presets = await response.json();
          
          // 转换为组件需要的格式
          const configs = {};
          Object.keys(presets).forEach(key => {
            const config = presets[key];
            configs[key] = {
              label: config.name,
              fields: config.required_fields || config.fields || [],
              description: config.description || `适用于${config.name}的评估`
            };
          });
          
          setDocumentTypeConfigs(configs);
          console.log('[EvaluationFieldsConfig] Loaded document type configurations from backend:', configs);
        } else {
          console.warn('[EvaluationFieldsConfig] Failed to load document type configurations, using fallback');
          // 兜底配置
          setDocumentTypeConfigs({
            invoice: {
              label: "发票 (Invoice)",
              fields: ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "totalTaxAmount"],
              description: "适用于发票和收据的评估"
            },
            bank_receipt: {
              label: "银行回单 (Bank Receipt)",
              fields: ["recieptNum", "tradeDate", "amount", "paymentName", "paymentBank", "paymentAccount", "payeeName", "payeeBank", "payeeAccount", "currency"],
              description: "适用于银行回单的评估"
            },
            custom: {
              label: "自定义 (Custom)",
              fields: [],
              description: "自定义评估字段"
            }
          });
        }
      } catch (error) {
        console.error('[EvaluationFieldsConfig] Error fetching document type configurations:', error);
        // 兜底配置
        setDocumentTypeConfigs({
          invoice: {
            label: "发票 (Invoice)",
            fields: ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "totalTaxAmount"],
            description: "适用于发票和收据的评估"
          },
          bank_receipt: {
            label: "银行回单 (Bank Receipt)",
            fields: ["recieptNum", "tradeDate", "amount", "paymentName", "paymentBank", "paymentAccount", "payeeName", "payeeBank", "payeeAccount", "currency"],
            description: "适用于银行回单的评估"
          },
          custom: {
            label: "自定义 (Custom)",
            fields: [],
            description: "自定义评估字段"
          }
        });
      } finally {
        setIsLoadingConfigs(false);
      }
    };

    fetchDocumentTypeConfigs();
  }, []);

  // 从项目配置中加载当前设置
  useEffect(() => {
    if (isLoadingConfigs) return; // 等待配置加载完成
    
    const config = project?.evaluation_field_config || {};
    if (config.document_type) {
      setDocumentType(config.document_type);
    }
    if (config.document_type === 'custom' && config.default_fields) {
      setCustomFields(config.default_fields.join(', '));
    }
    if (config.matching_strategy) {
      setMatchingStrategy(config.matching_strategy);
    }
  }, [project, isLoadingConfigs]);

  // 当文档类型变化时，如果不是自定义类型，清空自定义字段
  useEffect(() => {
    if (documentType !== 'custom') {
      setCustomFields('');
    }
  }, [documentType]);

  // 获取当前配置的字段列表
  const getCurrentFields = useCallback(() => {
    if (documentType === 'custom') {
      return customFields.split(',').map(f => f.trim()).filter(Boolean);
    }
    return documentTypeConfigs[documentType]?.fields || [];
  }, [documentType, customFields, documentTypeConfigs]);

  // 保存配置
  const handleSave = useCallback(async () => {
    const fields = getCurrentFields();
    const config = {
      document_type: documentType,
      default_fields: fields,
      matching_strategy: matchingStrategy,
      last_updated: new Date().toISOString()
    };

    try {
      // 调用API保存配置
      const response = await fetch(`/api/projects/${project.id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          evaluation_field_config: config
        })
      });

      if (response.ok) {
        onUpdate && onUpdate();
        setIsEditing(false);
      }
    } catch (error) {
      console.error('Failed to save evaluation config:', error);
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
        <Elem name="description">
          配置不同文档类型的评估字段，用于自动化评估功能
        </Elem>
      </Elem>

      {!isEditing ? (
        <Elem name="display">
          <Elem name="current-config">
            <Elem name="item">
              <Elem name="label">文档类型:</Elem>
              <Elem name="value">
                {documentTypeConfigs[currentConfig.document_type || 'invoice']?.label || '发票 (Invoice)'}
              </Elem>
            </Elem>
            <Elem name="description-text">
              {documentTypeConfigs[currentConfig.document_type || 'invoice']?.description || '适用于发票的评估'}
            </Elem>
            
            {currentConfig.document_type && documentTypeConfigs[currentConfig.document_type] && (
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
                {(documentTypeConfigs[currentConfig.document_type || 'invoice']?.fields || documentTypeConfigs.invoice.fields).join(', ')}
              </Elem>
            </Elem>
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
                    label: config.label
                  }))}
                  placeholder="选择文档类型"
                  className="evaluation-config-select"
                />
              {/* </Elem> */}
            </Elem>

            <Elem name="description-section">
              {documentTypeConfigs[documentType]?.description}
            </Elem>

            {documentType === 'custom' ? (
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
              <Elem name="predefined-fields">
                <Elem name="fields-label">预定义字段:</Elem>
                <Elem name="fields-list">
                  {documentTypeConfigs[documentType]?.fields.map((field, index) => (
                    <Elem key={field} name="field-tag">
                      {field}
                    </Elem>
                  ))}
                </Elem>
              </Elem>
            )}

            <Elem name="preview">
              <Elem name="preview-label">当前配置字段:</Elem>
              <Elem name="preview-fields">
                {currentFields.join(', ') || '无'}
              </Elem>
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
              <Button look="primary" onClick={handleSave} style={{ marginRight: '9px' }}>
                保存配置
              </Button>
              <Button 
                look="default" 
                onClick={() => {
                  setIsEditing(false);
                  // 重置到当前配置
                  const config = project?.evaluation_field_config || {};
                  setDocumentType(config.document_type || 'invoice');
                  if (config.document_type === 'custom' && config.default_fields) {
                    setCustomFields(config.default_fields.join(', '));
                  } else {
                    setCustomFields('');
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
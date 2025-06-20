import React, { useState, useCallback, useEffect } from "react";
import { Select, Button } from "@humansignal/ui";
import { Block, Elem } from "../../utils/bem";
import { Form, Input, TextArea } from "../Form";
import "./EvaluationFieldsConfig.scss";

// 预定义的单据类型配置
const DOCUMENT_TYPE_CONFIGS = {
  invoice: {
    label: "发票 (Invoice)",
    fields: ["totalAmount", "invoiceDate", "docType", "currency", "billToName", "totalTaxAmount"],
    description: "适用于发票和收据的评估"
  },
  bank_receipt: {
    label: "银行回单 (Bank Receipt)",
    fields: ["recieptNum", "logNum", "tradeDate", "amount", "paymentName", "paymentBank", "paymentAccount", "payeeName", "payeeBank", "payeeAccount", "currency"],
    description: "适用于银行回单的评估"
  },
  custom: {
    label: "自定义 (Custom)",
    fields: [],
    description: "自定义评估字段"
  }
};

export const EvaluationFieldsConfig = ({ project, onUpdate }) => {
  const [documentType, setDocumentType] = useState('invoice');
  const [customFields, setCustomFields] = useState('');
  const [isEditing, setIsEditing] = useState(false);

  // 从项目配置中加载当前设置
  useEffect(() => {
    const config = project?.evaluation_field_config || {};
    if (config.document_type) {
      setDocumentType(config.document_type);
    }
    if (config.document_type === 'custom' && config.default_fields) {
      setCustomFields(config.default_fields.join(', '));
    }
  }, [project]);

  // 获取当前配置的字段列表
  const getCurrentFields = useCallback(() => {
    if (documentType === 'custom') {
      return customFields.split(',').map(f => f.trim()).filter(Boolean);
    }
    return DOCUMENT_TYPE_CONFIGS[documentType]?.fields || [];
  }, [documentType, customFields]);

  // 保存配置
  const handleSave = useCallback(async () => {
    const fields = getCurrentFields();
    const config = {
      document_type: documentType,
      default_fields: fields,
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
  }, [project.id, documentType, customFields, getCurrentFields, onUpdate]);

  const currentConfig = project?.evaluation_field_config || {};
  const currentFields = getCurrentFields();

  return (
    <Block name="evaluation-fields-config">
      <Elem name="header">
        <Elem name="title">评估字段配置</Elem>
        <Elem name="description">
          配置不同单据类型的评估字段，用于自动化评估功能
        </Elem>
      </Elem>

      {!isEditing ? (
        <Elem name="display">
          <Elem name="current-config">
            <Elem name="item">
              <Elem name="label">当前单据类型:</Elem>
              <Elem name="value">
                {DOCUMENT_TYPE_CONFIGS[currentConfig.document_type || 'invoice']?.label || '发票'}
              </Elem>
            </Elem>
            <Elem name="item">
              <Elem name="label">评估字段:</Elem>
              <Elem name="value">
                {(currentConfig.default_fields || DOCUMENT_TYPE_CONFIGS.invoice.fields).join(', ')}
              </Elem>
            </Elem>
          </Elem>
          <Button look="primary" onClick={() => setIsEditing(true)}>
            编辑配置
          </Button>
        </Elem>
      ) : (
        <Elem name="editor">
          <Form.Row>
            <Select
              label="单据类型"
              value={documentType}
              onChange={setDocumentType}
              options={Object.entries(DOCUMENT_TYPE_CONFIGS).map(([key, config]) => ({
                value: key,
                label: config.label
              }))}
            />
          </Form.Row>

          <Elem name="description">
            {DOCUMENT_TYPE_CONFIGS[documentType]?.description}
          </Elem>

          {documentType === 'custom' ? (
            <Form.Row>
              <TextArea
                label="自定义字段 (用逗号分隔)"
                value={customFields}
                onChange={(e) => setCustomFields(e.target.value)}
                placeholder="例如: totalAmount, invoiceDate, docType, currency"
                rows={3}
              />
            </Form.Row>
          ) : (
            <Elem name="predefined-fields">
              <Elem name="fields-label">预定义字段:</Elem>
              <Elem name="fields-list">
                {DOCUMENT_TYPE_CONFIGS[documentType]?.fields.map((field, index) => (
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

          <Elem name="actions">
            <Button look="primary" onClick={handleSave}>
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
      )}
    </Block>
  );
}; 
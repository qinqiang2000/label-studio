import React, { useState, useEffect } from 'react';
import { Select, Button, Input, Checkbox } from "@humansignal/ui";
import { Block, Elem } from "../../utils/bem";

/**
 * 优化的匹配策略配置组件
 * 统一配置源：从后端API获取预设配置，避免硬编码
 * 支持拖拽排序：用户可以通过拖拽调整主键字段顺序
 * 1. 用户只需配置指定字段即可
 * 2. 如果需要顺序匹配，只需要配置空，或["_position"]即可
 * 3. 预设文档类型配置从后端API动态获取
 * 4. 支持拖拽排序调整字段优先级
 */
export const EvaluationMatchingStrategyConfig = ({ 
  value, 
  onChange, 
  documentType = 'custom',
  evaluationFields = [],
  disabled = false 
}) => {
  const [primaryFields, setPrimaryFields] = useState([]);
  const [usePositionMatching, setUsePositionMatching] = useState(false);
  const [showFieldSelector, setShowFieldSelector] = useState(false);
  const [presetConfigurations, setPresetConfigurations] = useState({});
  const [isLoadingPresets, setIsLoadingPresets] = useState(true);
  const [isInitialized, setIsInitialized] = useState(false); // 追踪是否已经初始化
  
  // 拖拽排序相关状态
  const [draggedIndex, setDraggedIndex] = useState(null);
  const [dragOverIndex, setDragOverIndex] = useState(null);

  // 从后端API获取预设配置
  useEffect(() => {
    const fetchPresetConfigurations = async () => {
      try {
        const response = await fetch('/api/frontend/evaluation-configs/presets/');
        if (response.ok) {
          const data = await response.json();
          console.log('[EvaluationMatchingStrategy] Loaded preset configurations from backend:', data);
          setPresetConfigurations(data);
        } else {
          console.error('[EvaluationMatchingStrategy] Failed to load preset configurations:', response.status);
          // 兜底配置，防止API失败
          setPresetConfigurations({
            invoice: { primary_fields: ['invoiceNumber', 'invoiceDate', 'totalAmount'] },
            bank_receipt: { primary_fields: ['recieptNum', 'amount'] },
            receipt: { primary_fields: ['invoiceDate', 'totalAmount'] },
            custom: { primary_fields: [] }
          });
        }
      } catch (error) {
        console.error('[EvaluationMatchingStrategy] Error fetching preset configurations:', error);
        // 兜底配置
        setPresetConfigurations({
          invoice: { primary_fields: ['invoiceNumber', 'invoiceDate', 'totalAmount'] },
          bank_receipt: { primary_fields: ['recieptNum', 'amount'] },
          receipt: { primary_fields: ['invoiceDate', 'totalAmount'] },
          custom: { primary_fields: [] }
        });
      } finally {
        setIsLoadingPresets(false);
      }
    };

    fetchPresetConfigurations();
  }, []);

  // 获取当前文档类型的预设主键字段
  const getPresetPrimaryFields = (docType) => {
    const config = presetConfigurations[docType];
    return config?.primary_fields || [];
  };

  // 初始化状态 - 只在组件第一次加载和预设配置加载完成时执行
  useEffect(() => {
    if (isLoadingPresets || isInitialized) return; // 等待预设配置加载完成，且避免重复初始化

    // 初始化时根据文档类型和现有配置设置状态
    if (value && value.primary_fields !== undefined) {
      // 编辑现有配置
      const fields = value.primary_fields;
      if (fields.length === 0 || (fields.length === 1 && fields[0] === '_position')) {
        setUsePositionMatching(true);
        setPrimaryFields([]);
      } else {
        setUsePositionMatching(false);
        setPrimaryFields(fields);
      }
    } else {
      // 新建配置，使用从后端获取的预设配置
      const defaultFields = getPresetPrimaryFields(documentType);
      if (defaultFields.length === 0) {
        setUsePositionMatching(true);
        setPrimaryFields([]);
        // 通知父组件使用顺序匹配
        onChange?.({
          type: 'degraded_field_based',
          mode: 'field_based',
          primary_fields: [],
          verbose: true
        });
      } else {
        setUsePositionMatching(false);
        setPrimaryFields(defaultFields);
        // 重要：通知父组件使用预设配置
        onChange?.({
          type: 'degraded_field_based',
          mode: 'field_based',
          primary_fields: defaultFields,
          verbose: true
        });
      }
    }
    
    setIsInitialized(true); // 标记已初始化
  }, [documentType, presetConfigurations, isLoadingPresets, isInitialized]); // 添加isInitialized依赖

  // 当文档类型变化时，重置初始化状态并应用新的预设配置
  useEffect(() => {
    if (isLoadingPresets) return;
    
    // 文档类型变化时，重置初始化状态
    setIsInitialized(false);
  }, [documentType]); // 仅依赖documentType

  const handleMatchingModeChange = (event) => {
    const usePosition = event.target.checked;
    setUsePositionMatching(usePosition);
    
    if (usePosition) {
      // 切换到顺序匹配
      setPrimaryFields([]);
      onChange?.({
        type: 'degraded_field_based',
        mode: 'field_based',
        primary_fields: [],  // 空配置表示使用顺序匹配
        verbose: true
      });
    } else {
      // 切换到字段匹配，加载预设字段
      const defaultFields = getPresetPrimaryFields(documentType);
      setPrimaryFields(defaultFields);
      onChange?.({
        type: 'degraded_field_based',
        mode: 'field_based',
        primary_fields: defaultFields,
        verbose: true
      });
    }
  };

  const handlePrimaryFieldsChange = (newFields) => {
    setPrimaryFields(newFields);
    onChange?.({
      type: 'degraded_field_based',
      mode: 'field_based',
      primary_fields: newFields,
      verbose: true
    });
  };

  const addPrimaryField = (field) => {
    if (field && !primaryFields.includes(field)) {
      const newFields = [...primaryFields, field];
      handlePrimaryFieldsChange(newFields);
    }
  };

  const removePrimaryField = (fieldToRemove) => {
    const newFields = primaryFields.filter(field => field !== fieldToRemove);
    handlePrimaryFieldsChange(newFields);
  };

  // 拖拽开始
  const handleDragStart = (e, index) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = 'move';
    e.dataTransfer.setData('text/html', e.target.outerHTML);
    e.target.style.opacity = '0.5';
  };

  // 拖拽结束
  const handleDragEnd = (e) => {
    e.target.style.opacity = '1';
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  // 拖拽经过
  const handleDragOver = (e, index) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
    setDragOverIndex(index);
  };

  // 拖拽离开
  const handleDragLeave = () => {
    setDragOverIndex(null);
  };

  // 拖拽释放
  const handleDrop = (e, dropIndex) => {
    e.preventDefault();
    
    if (draggedIndex === null || draggedIndex === dropIndex) {
      return;
    }

    const newFields = [...primaryFields];
    const draggedField = newFields[draggedIndex];
    
    // 移除拖拽的元素
    newFields.splice(draggedIndex, 1);
    // 在新位置插入
    newFields.splice(dropIndex, 0, draggedField);
    
    handlePrimaryFieldsChange(newFields);
    setDraggedIndex(null);
    setDragOverIndex(null);
  };

  // 获取当前文档类型的预设字段说明
  const getPresetDescription = (docType) => {
    const config = presetConfigurations[docType];
    if (!config) return { fields: [], name: '自定义' };
    
    const typeNames = {
      invoice: '发票',
      bank_receipt: '银行回单',
      receipt: '收据',
      custom: '自定义'
    };
    
    return {
      fields: config.primary_fields || [],
      name: typeNames[docType] || config.name || '自定义'
    };
  };

  const presetInfo = getPresetDescription(documentType);

  // 显示加载状态
  if (isLoadingPresets) {
    return (
      <Block name="matching-strategy-config">
        <Elem name="header">
          <Elem name="title">票据匹配策略</Elem>
          <Elem name="description">正在加载配置...</Elem>
        </Elem>
      </Block>
    );
  }

  return (
    <Block name="matching-strategy-config">
      <Elem name="header">
        <Elem name="title">票据匹配策略</Elem>
        <Elem name="description">
          配置如何将标准票据与预测票据进行配对比较
        </Elem>
      </Elem>

      {/* 主要匹配模式选择 */}
      <Elem name="matching-mode">
        <label>
          <Checkbox
            checked={usePositionMatching}
            onChange={handleMatchingModeChange}
            disabled={disabled}
          />
          <span>使用顺序匹配（按位置一对一配对）</span>
        </label>
        
        {usePositionMatching ? (
          <Elem name="position-info">
            <Elem name="info-box">
              📍 <strong>顺序匹配</strong>：第1张标准票据对应第1张预测票据，第2张对应第2张，以此类推
              <br/>
              {/* <strong>适用：</strong>银行流水、批量扫描等顺序一致的票据 */}
            </Elem>
          </Elem>
        ) : (
          <Elem name="field-matching-section">
            {/* 主键字段配置 */}
            <Elem name="primary-fields-config">
              <Elem name="section-title">主键字段配置</Elem>
              
              <Elem name="current-fields">
                <label>当前主键字段：</label>
                <Elem name="fields-list-draggable">
                  {primaryFields.length > 0 ? (
                    primaryFields.map((field, index) => (
                      <Elem 
                        key={`${field}-${index}`}
                        name="field-tag-draggable"
                        mod={{
                          dragging: draggedIndex === index,
                          dragover: dragOverIndex === index
                        }}
                        draggable={!disabled}
                        onDragStart={(e) => handleDragStart(e, index)}
                        onDragEnd={handleDragEnd}
                        onDragOver={(e) => handleDragOver(e, index)}
                        onDragLeave={handleDragLeave}
                        onDrop={(e) => handleDrop(e, index)}
                      >
                        <Elem name="drag-handle" title="拖拽调整顺序">
                          ⋮⋮
                        </Elem>
                        <Elem name="field-name">{field}</Elem>
                        <Button
                          size="small"
                          onClick={() => removePrimaryField(field)}
                          disabled={disabled}
                          className="remove-field-btn"
                          title="删除字段"
                        >
                          ×
                        </Button>
                      </Elem>
                    ))
                  ) : (
                    <Elem name="no-fields">
                      未配置（将使用位置匹配）
                    </Elem>
                  )}
                </Elem>
              </Elem>

              {/* 添加字段按钮 */}
              <Elem name="add-field-section">
                <Button
                  onClick={() => setShowFieldSelector(!showFieldSelector)}
                  disabled={disabled}
                  size="small"
                >
                  {showFieldSelector ? "隐藏字段" : "添加字段"}
                </Button>
                
                {showFieldSelector && (
                  <Elem name="field-selector">
                    <Elem name="selector-title">可选字段：</Elem>
                    <Elem name="available-fields">
                      {evaluationFields
                        .filter(field => !primaryFields.includes(field))
                        .map((field, index) => (
                          <Button
                            key={index}
                            size="small"
                            onClick={() => addPrimaryField(field)}
                            disabled={disabled}
                            className="add-field-btn"
                          >
                            + {field}
                          </Button>
                        ))}
                    </Elem>
                  </Elem>
                )}
              </Elem>

              {/* 排序提示 */}
              {primaryFields.length > 1 && (
                <Elem name="sorting-tips">
                  <strong>💡 排序提示：</strong>
                                      <ul>
                      <li>字段的顺序影响匹配结果，请将<strong>重要性高的字段放在前面</strong></li>
                      <li>系统会对未匹配数据尝试降级匹配，如：[{primaryFields.join(', ')}] → [{primaryFields.slice(1).join(', ')}] → [{primaryFields[primaryFields.length - 1]}]</li>
                      <li><strong>拖拽字段</strong>可调整顺序，重要字段在前可确保优先匹配</li>
                    </ul>
                </Elem>
              )}
            </Elem>
          </Elem>
        )}
      </Elem>

      {/* 配置预览 */}
      <Elem name="config-preview">
        <Elem name="preview-label">配置预览：</Elem>
        <Elem name="preview-content">
          {usePositionMatching 
            ? "顺序匹配：按位置一对一配对"
            : `字段匹配: [${primaryFields.join(', ')}]`
          }
        </Elem>
      </Elem>
    </Block>
  );
}; 
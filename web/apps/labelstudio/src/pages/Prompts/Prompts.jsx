import React, { useState, useEffect, useCallback, useRef } from "react";
import { Button } from "../../components";
import { Spinner } from "../../components/Spinner/Spinner";
import { modal } from "../../components/Modal/Modal";
import { cn } from "../../utils/bem";
import { useAPI } from "../../providers/ApiProvider";
import { useCurrentUser } from "../../providers/CurrentUser";
import WorkspaceSelector from "../CreateProject/WorkspaceSelector";
import "./Prompts.scss";

const Block = cn("prompts-page");

// 可折叠JSON编辑器组件
const CollapsibleJsonEditor = ({ value, onChange, placeholder, disabled, error }) => {
  const [isCollapsed, setIsCollapsed] = useState(false); // 默认展开
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [jsonError, setJsonError] = useState(null);
  const [cursorPosition, setCursorPosition] = useState(0);

  // 验证JSON并设置错误信息
  const validateJson = useCallback((jsonString) => {
    if (!jsonString.trim()) {
      setJsonError(null);
      return true;
    }

    try {
      JSON.parse(jsonString);
      setJsonError(null);
      return true;
    } catch (e) {
      const match = e.message.match(/at position (\d+)/);
      const position = match ? parseInt(match[1]) : 0;
      
      // 计算行列位置
      const lines = jsonString.substring(0, position).split('\n');
      const line = lines.length;
      const column = lines[lines.length - 1].length + 1;
      
      setJsonError({
        message: e.message,
        line,
        column,
        position
      });
      return false;
    }
  }, []);

  // 处理输入变化
  const handleChange = useCallback((e) => {
    const newValue = e.target.value;
    setCursorPosition(e.target.selectionStart);
    validateJson(newValue);
    onChange(e);
  }, [onChange, validateJson]);

  // JSON对象/数组折叠功能
  const [collapsedRanges, setCollapsedRanges] = useState(new Set());
  const textareaRef = useRef(null);

  // 查找JSON中的可折叠区域
  const findCollapsibleRanges = useCallback((text) => {
    const ranges = [];
    const stack = [];
    let inString = false;
    let escapeNext = false;
    
    for (let i = 0; i < text.length; i++) {
      const char = text[i];
      
      if (escapeNext) {
        escapeNext = false;
        continue;
      }
      
      if (char === '\\') {
        escapeNext = true;
        continue;
      }
      
      if (char === '"') {
        inString = !inString;
        continue;
      }
      
      if (inString) continue;
      
      if (char === '{' || char === '[') {
        stack.push({ type: char, start: i });
      } else if (char === '}' || char === ']') {
        const expected = char === '}' ? '{' : '[';
        if (stack.length > 0 && stack[stack.length - 1].type === expected) {
          const start = stack.pop();
          // 只有多行的对象/数组才可折叠
          const content = text.substring(start.start, i + 1);
          if (content.includes('\n')) {
            ranges.push({
              start: start.start,
              end: i + 1,
              type: start.type,
              id: `${start.start}-${i}`
            });
          }
        }
      }
    }
    
    return ranges;
  }, []);

  // 切换折叠状态
  const toggleCollapse = useCallback((rangeId) => {
    setCollapsedRanges(prev => {
      const newSet = new Set(prev);
      if (newSet.has(rangeId)) {
        newSet.delete(rangeId);
      } else {
        newSet.add(rangeId);
      }
      return newSet;
    });
  }, []);

  // 渲染带折叠功能的JSON
  const renderCollapsibleJson = useCallback((text) => {
    if (!text || jsonError) return text;
    
    try {
      // 验证JSON
      JSON.parse(text);
      const ranges = findCollapsibleRanges(text);
      
      if (ranges.length === 0) return text;
      
      let result = text;
      let offset = 0;
      
      // 从后往前处理，避免位置偏移问题
      for (let i = ranges.length - 1; i >= 0; i--) {
        const range = ranges[i];
        if (collapsedRanges.has(range.id)) {
          const beforeRange = result.substring(0, range.start);
          const afterRange = result.substring(range.end);
          const symbol = range.type === '{' ? '{}' : '[]';
          result = beforeRange + symbol + afterRange;
        }
      }
      
      return result;
    } catch (e) {
      return text;
    }
  }, [findCollapsibleRanges, collapsedRanges, jsonError]);

  // 获取折叠按钮位置
  const getCollapsibleButtons = useCallback((text) => {
    if (!text || jsonError) return [];
    
    try {
      JSON.parse(text);
      const ranges = findCollapsibleRanges(text);
      const lines = text.split('\n');
      let lineOffset = 0;
      
      return ranges.map(range => {
        // 找到开始位置所在的行
        let line = 0;
        let pos = 0;
        for (let i = 0; i < lines.length; i++) {
          if (pos + lines[i].length >= range.start) {
            line = i;
            break;
          }
          pos += lines[i].length + 1; // +1 for newline
        }
        
        return {
          ...range,
          line: line + 1,
          isCollapsed: collapsedRanges.has(range.id)
        };
      });
    } catch (e) {
      return [];
    }
  }, [findCollapsibleRanges, collapsedRanges, jsonError]);

  useEffect(() => {
    validateJson(value);
  }, [value, validateJson]);

  return (
    <div className={Block.elem("json-editor-container")}>
      <details 
        open={!isCollapsed} 
        onToggle={(e) => setIsCollapsed(!e.target.open)}
        className={Block.elem("json-editor-details")}
      >
        <summary className={Block.elem("json-editor-summary")}>
          <span className={Block.elem("json-editor-title")}>
            Response Schema
            <small style={{ color: '#666', fontWeight: 'normal', marginLeft: '8px' }}>
              (Optional JSON schema for structured output)
            </small>
          </span>
          <div className={Block.elem("json-editor-indicators")}>
            <button
              type="button"
              onClick={() => setIsFullscreen(!isFullscreen)}
              style={{
                padding: '4px 8px',
                fontSize: '11px',
                border: '1px solid #d1d5db',
                borderRadius: '4px',
                backgroundColor: 'white',
                cursor: 'pointer',
                marginRight: '8px'
              }}
              title={isFullscreen ? '退出全屏' : '全屏编辑'}
            >
              {isFullscreen ? '退出全屏' : '全屏编辑'}
            </button>
            {value.trim() && (
              <span className={Block.elem("json-editor-badge")} style={{
                backgroundColor: jsonError ? '#fee2e2' : '#d1fae5',
                color: jsonError ? '#dc2626' : '#059669',
                padding: '2px 6px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: '500'
              }}>
                {jsonError ? '语法错误' : 'JSON有效'}
              </span>
            )}
            <span className={Block.elem("json-editor-toggle")} style={{
              color: '#6b7280',
              fontSize: '12px',
              marginLeft: '8px'
            }}>
              {isCollapsed ? '展开 ▼' : '收起 ▲'}
            </span>
          </div>
        </summary>
        
        <div className={Block.elem("json-editor-content")} style={{
          position: isFullscreen ? 'fixed' : 'relative',
          top: isFullscreen ? '0' : 'auto',
          left: isFullscreen ? '0' : 'auto',
          width: isFullscreen ? '100vw' : 'auto',
          height: isFullscreen ? '100vh' : 'auto',
          zIndex: isFullscreen ? 9999 : 'auto',
          backgroundColor: isFullscreen ? 'white' : 'transparent',
          padding: isFullscreen ? '20px' : '0'
        }}>

          {/* 全屏模式下的顶部工具栏 */}
          {isFullscreen && (
            <div style={{
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
              marginBottom: '20px',
              padding: '10px 0',
              borderBottom: '1px solid #e5e7eb'
            }}>
              <h3 style={{ margin: 0, fontSize: '18px', fontWeight: 'bold' }}>
                Response Schema - 全屏编辑
              </h3>
              <button
                type="button"
                onClick={() => setIsFullscreen(false)}
                style={{
                  padding: '8px 16px',
                  fontSize: '14px',
                  border: '1px solid #d1d5db',
                  borderRadius: '4px',
                  backgroundColor: 'white',
                  cursor: 'pointer'
                }}
              >
                退出全屏
              </button>
            </div>
          )}
          
          {/* JSON编辑器 */}
          <div className={Block.elem("json-editor-wrapper")} style={{ 
            position: 'relative',
            height: isFullscreen ? 'calc(100vh - 120px)' : 'auto'
          }}>
            <div style={{ position: 'relative' }}>
              <textarea
                ref={textareaRef}
                id="response_schema"
                value={value}
                onChange={handleChange}
                rows="20"
                disabled={disabled}
                placeholder={placeholder}
                style={{
                  fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                  fontSize: '13px',
                  lineHeight: '1.4',
                  width: '100%',
                  padding: '12px 12px 12px 40px', // 左边留空间给折叠按钮
                  border: `1px solid ${jsonError ? '#fca5a5' : '#d1d5db'}`,
                  borderRadius: '4px',
                  backgroundColor: disabled ? '#f9fafb' : 'white',
                  resize: 'vertical',
                  minHeight: isFullscreen ? 'calc(100vh - 120px)' : '400px',
                  maxHeight: isFullscreen ? 'calc(100vh - 120px)' : '600px',
                  height: isFullscreen ? 'calc(100vh - 120px)' : 'auto'
                }}
              />
              
              {/* 折叠按钮层 */}
              {!disabled && value.trim() && !jsonError && (
                <div style={{
                  position: 'absolute',
                  left: '12px',
                  top: '12px',
                  pointerEvents: 'none',
                  fontFamily: 'Monaco, Menlo, "Ubuntu Mono", monospace',
                  fontSize: '13px',
                  lineHeight: '1.4',
                  color: 'transparent'
                }}>
                  {getCollapsibleButtons(value).map(button => (
                    <div
                      key={button.id}
                      style={{
                        position: 'absolute',
                        top: `${(button.line - 1) * 1.4}em`,
                        left: '0',
                        width: '20px',
                        height: '1.4em',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        pointerEvents: 'auto'
                      }}
                    >
                      <button
                        type="button"
                        onClick={() => toggleCollapse(button.id)}
                        style={{
                          width: '16px',
                          height: '16px',
                          border: '1px solid #d1d5db',
                          borderRadius: '2px',
                          backgroundColor: 'white',
                          color: '#666',
                          fontSize: '10px',
                          lineHeight: '1',
                          cursor: 'pointer',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          padding: '0'
                        }}
                        title={button.isCollapsed ? '展开' : '折叠'}
                      >
                        {button.isCollapsed ? '+' : '−'}
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
            
            {/* 错误信息 */}
            {jsonError && (
              <div className={Block.elem("json-error")} style={{
                marginTop: '8px',
                padding: '8px 12px',
                backgroundColor: '#fee2e2',
                border: '1px solid #fca5a5',
                borderRadius: '4px',
                fontSize: '12px'
              }}>
                <div style={{ fontWeight: 'bold', color: '#dc2626', marginBottom: '4px' }}>
                  JSON语法错误
                </div>
                <div style={{ color: '#991b1b' }}>
                  {jsonError.message}
                </div>
                <div style={{ color: '#7f1d1d', marginTop: '2px' }}>
                  位置：第 {jsonError.line} 行，第 {jsonError.column} 列
                </div>
              </div>
            )}
            
            {/* 帮助信息 */}
            {!value.trim() && !isCollapsed && (
              <div className={Block.elem("json-help")} style={{
                marginTop: '8px',
                padding: '8px 12px',
                backgroundColor: '#eff6ff',
                border: '1px solid #bfdbfe',
                borderRadius: '4px',
                fontSize: '12px',
                color: '#1e40af'
              }}>
                {/* <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>
                  JSON Schema 帮助
                </div>*/
                <div>
                  定义AI模型返回结果的结构格式。支持标准的JSON Schema语法。
                </div> }
              </div>
            )}
          </div>
        </div>
      </details>
    </div>
  );
};

const PromptForm = ({ prompt, onSave, onCancel, isLoading }) => {
  const [formData, setFormData] = useState({
    name: prompt?.name || "",
    content: prompt?.content || "",
    temperature: prompt?.temperature || "",
    response_schema: prompt?.response_schema ? JSON.stringify(prompt.response_schema, null, 2) : "",
    workspace: prompt?.workspace || "",
  });

  const [errors, setErrors] = useState({});

  const validateForm = () => {
    const newErrors = {};

    // Validate temperature
    if (formData.temperature !== "") {
      const temp = parseFloat(formData.temperature);
      if (isNaN(temp) || temp < 0.0 || temp > 2.0) {
        newErrors.temperature = "Temperature must be a number between 0.0 and 2.0";
      }
    }

    // Validate response_schema JSON
    if (formData.response_schema.trim() !== "") {
      try {
        JSON.parse(formData.response_schema);
      } catch (e) {
        newErrors.response_schema = "Response schema must be valid JSON";
      }
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = (e) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    console.log("=== FORM SUBMIT DEBUG ===");
    
    // Prepare form data
    const submitData = {
      name: formData.name,
      content: formData.content,
    };

    // Add temperature if provided
    if (formData.temperature !== "") {
      submitData.temperature = parseFloat(formData.temperature);
    }

    // Add response_schema if provided
    if (formData.response_schema.trim() !== "") {
      try {
        submitData.response_schema = JSON.parse(formData.response_schema);
      } catch (e) {
        // This shouldn't happen due to validation, but just in case
        console.error("JSON parse error:", e);
        return;
      }
    }

    // Add workspace if provided
    if (formData.workspace !== "") {
      submitData.workspace = formData.workspace;
    }

    console.log("Form data being submitted:", submitData);
    console.log("onSave function:", onSave);
    onSave(submitData);
  };

  const handleChange = (field) => (e) => {
    setFormData(prev => ({
      ...prev,
      [field]: e.target.value
    }));
    
    // Clear error when user starts typing
    if (errors[field]) {
      setErrors(prev => {
        const newErrors = { ...prev };
        delete newErrors[field];
        return newErrors;
      });
    }
  };

  const handleCancel = (e) => {
    e.preventDefault();
    if (onCancel && typeof onCancel === 'function') {
      onCancel();
    }
  };

  return (
    <form onSubmit={handleSubmit} className={Block.elem("form")}>
      <div className={Block.elem("form-field")}>
        <label htmlFor="name">Name</label>
        <input
          id="name"
          type="text"
          value={formData.name}
          onChange={handleChange("name")}
          required
          disabled={isLoading}
          placeholder="Enter prompt name"
        />
      </div>
      
      <div className={Block.elem("form-field")}>
        <label htmlFor="content">Prompt</label>
        <textarea
          id="content"
          value={formData.content}
          onChange={handleChange("content")}
          rows="8"
          required
          disabled={isLoading}
          placeholder="Enter your prompt content here..."
        />
      </div>

      <div className={Block.elem("form-field")}>
        <label htmlFor="temperature">
          Temperature 
          <small style={{ color: '#666', fontWeight: 'normal' }}>
            {' '}(Optional: 0.0-2.0, controls randomness)
          </small>
        </label>
        <input
          id="temperature"
          type="number"
          step="0.1"
          min="0.0"
          max="2.0"
          value={formData.temperature}
          onChange={handleChange("temperature")}
          disabled={isLoading}
          placeholder="e.g., 0.2"
        />
        {errors.temperature && (
          <div className={Block.elem("field-error")} style={{ color: 'red', fontSize: '12px', marginTop: '4px' }}>
            {errors.temperature}
          </div>
        )}
      </div>

      <div className={Block.elem("form-field")}>
        <label htmlFor="workspace">
          Workspace 
          <small style={{ color: '#666', fontWeight: 'normal' }}>
            {' '}(Optional: Select a workspace or leave empty for organization-wide visibility)
          </small>
        </label>
        <WorkspaceSelector
          value={formData.workspace}
          onChange={(value) => setFormData(prev => ({ ...prev, workspace: value }))}
          disabled={isLoading}
          placeholder="Select a workspace (optional)"
          getPopupContainer={() => document.body}
        />
      </div>

      <div className={Block.elem("form-field")}>
        <CollapsibleJsonEditor
          value={formData.response_schema}
          onChange={handleChange("response_schema")}
          disabled={isLoading}
          placeholder={`Example:
{
  "type": "object",
  "properties": {
    "sentiment": {"type": "string"},
    "confidence": {"type": "number"}
  },
  "required": ["sentiment"]
}`}
          error={errors.response_schema}
        />
        {errors.response_schema && (
          <div className={Block.elem("field-error")} style={{ color: 'red', fontSize: '12px', marginTop: '4px' }}>
            {errors.response_schema}
          </div>
        )}
      </div>
      
      <div className={Block.elem("form-actions")}>
        <Button type="button" onClick={handleCancel} disabled={isLoading}>
          Cancel
        </Button>
        <Button type="submit" look="primary" disabled={isLoading}>
          {isLoading ? "Saving..." : "Save"}
        </Button>
      </div>
    </form>
  );
};

const PromptCard = ({ prompt, onEdit, onDelete }) => {
  const formatDate = (dateString) => {
    const date = new Date(dateString);
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hour = String(date.getHours()).padStart(2, '0');
    const minute = String(date.getMinutes()).padStart(2, '0');
    return `${year}-${month}-${day} ${hour}:${minute}`;
  };

  const handleCardClick = (e) => {
    // 如果点击的是按钮，不触发卡片点击事件
    if (e.target.closest('button')) {
      return;
    }
    onEdit(prompt);
  };

  const handleEditClick = (e) => {
    e.stopPropagation();
    onEdit(prompt);
  };

  const handleDeleteClick = (e) => {
    e.stopPropagation();
    onDelete(prompt);
  };

  return (
    <div className={Block.elem("card")} onClick={handleCardClick}>
      <div className={Block.elem("card-header")}>
        <h3 className={Block.elem("card-title")}>{prompt.name}</h3>
        <div className={Block.elem("card-actions")}>
          <Button size="compact" onClick={handleEditClick}>
            Edit
          </Button>
          <Button size="compact" look="destructive" onClick={handleDeleteClick}>
            Delete
          </Button>
        </div>
      </div>
      
      <div className={Block.elem("card-content")}>
        <pre className={Block.elem("card-prompt")}>{prompt.content}</pre>
        
        {/* Display runtime config if available */}
        {(prompt.temperature !== null && prompt.temperature !== undefined) || prompt.response_schema ? (
          <div className={Block.elem("card-config")} style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #eee' }}>
            <h4 style={{ fontSize: '12px', fontWeight: 'bold', margin: '0 0 8px 0', color: '#666' }}>Runtime Config:</h4>
            {prompt.temperature !== null && prompt.temperature !== undefined && (
              <div style={{ fontSize: '12px', marginBottom: '4px' }}>
                <strong>Temperature:</strong> {prompt.temperature}
              </div>
            )}
            {prompt.response_schema && (
              <div style={{ fontSize: '12px' }}>
                <strong>Response Schema:</strong> Configured
              </div>
            )}
          </div>
        ) : null}
        
        {/* Display workspace info */}
        <div className={Block.elem("card-meta")} style={{ marginTop: '12px', paddingTop: '12px', borderTop: '1px solid #eee' }}>
          <div style={{ fontSize: '12px', marginBottom: '4px', color: '#666' }}>
            <strong>Workspace:</strong> {prompt.workspace ? `${prompt.workspace.name || 'Unknown'}` : 'Organization-wide (visible to all users)'}
          </div>
        </div>
      </div>
      
      <div className={Block.elem("card-footer")}>
        <small>Updated: {formatDate(prompt.updated_at)}</small>
      </div>
    </div>
  );
};

export const PromptsPage = () => {
  const api = useAPI();
  const { user } = useCurrentUser();
  const [prompts, setPrompts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentModal, setCurrentModal] = useState(null);
  const [editingPrompt, setEditingPrompt] = useState(null);
  const [saving, setSaving] = useState(false);

  const loadPrompts = useCallback(async () => {
    try {
      setLoading(true);
      const response = await api.callApi("getPrompts");
      // Label Studio API直接返回数据，不是包装在data字段中
      if (Array.isArray(response)) {
        setPrompts(response);
      } else {
        setPrompts([]);
      }
    } catch (error) {
      console.error("Failed to load prompts:", error);
      setPrompts([]);
    } finally {
      setLoading(false);
    }
  }, [api]);

  useEffect(() => {
    loadPrompts();
  }, [loadPrompts]);

  const handleCreatePrompt = () => {
    openModal();
  };

  const handleEditPrompt = (prompt) => {
    openModal(prompt);
  };

  const openModal = (promptToEdit = null) => {
    console.log("=== MODAL DEBUG START ===");
    console.log("promptToEdit:", promptToEdit);
    console.log("Setting editingPrompt to:", promptToEdit);
    
    // 重要：使用useEffect或者setTimeout来确保状态更新后再创建模态框
    setTimeout(() => {
      console.log("Creating modal after state update");
      
      let modalInstance; // 声明在外层作用域
      
      const closeModalHandler = () => {
        console.log("closeModalHandler called");
        if (modalInstance && typeof modalInstance.close === 'function') {
          try {
            console.log("Closing modal instance with close() method");
            modalInstance.close();
          } catch (error) {
            console.warn('Error closing modal:', error);
          }
        } else if (modalInstance && typeof modalInstance.hide === 'function') {
          try {
            console.log("Hiding modal instance with hide() method");
            modalInstance.hide();
          } catch (error) {
            console.warn('Error hiding modal:', error);
          }
        } else {
          console.warn('Modal instance has no close or hide method:', modalInstance);
        }
        console.log("Clearing current modal and editing prompt");
        setCurrentModal(null);
        setEditingPrompt(null);
      };
      
      modalInstance = modal({
        title: promptToEdit ? "Edit Prompt" : "Create Prompt",
        style: {
          width: '90vw',
          maxWidth: '1200px',
          height: '90vh',
          maxHeight: '1000px'
        },
        body: () => (
          <div onClick={(e) => e.stopPropagation()}>
            <PromptForm
              prompt={promptToEdit}
              onSave={(formData) => handleSavePrompt(formData, closeModalHandler, promptToEdit)}
              onCancel={closeModalHandler}
              isLoading={saving}
            />
          </div>
        ),
        onHide: () => {
          setCurrentModal(null);
          setEditingPrompt(null);
        },
      });
      setCurrentModal(modalInstance);
    }, 0);
    
    setEditingPrompt(promptToEdit); // 设置编辑状态
  };

  const closeModal = () => {
    if (currentModal && typeof currentModal.close === 'function') {
      try {
        currentModal.close();
      } catch (error) {
        console.warn('Error closing modal:', error);
      }
    } else if (currentModal && typeof currentModal.hide === 'function') {
      try {
        currentModal.hide();
      } catch (error) {
        console.warn('Error hiding modal:', error);
      }
    }
    setCurrentModal(null);
    setEditingPrompt(null);
  };

  const handleSavePrompt = async (formData, closeHandler, promptToEdit = null) => {
    console.log("=== SAVE DEBUG START ===");
    console.log("formData:", formData);
    console.log("promptToEdit param:", promptToEdit);
    console.log("editingPrompt state:", editingPrompt);
    console.log("closeHandler type:", typeof closeHandler);
    
    // 使用传入的promptToEdit参数而不是状态，因为状态可能还没更新
    const isEditing = promptToEdit !== null;
    
    try {
      setSaving(true);
      console.log("Setting saving to true");
      
      if (isEditing) {
        console.log("UPDATING existing prompt with ID:", promptToEdit.id);
        // Update existing prompt
        const response = await api.callApi("updatePrompt", {
          params: { id: promptToEdit.id },
          body: formData,
        });
        console.log("Prompt updated successfully:", response);
      } else {
        console.log("CREATING new prompt");
        // Create new prompt
        const response = await api.callApi("createPrompt", {
          body: formData,
        });
        console.log("Prompt created successfully:", response);
      }
      
      console.log("About to close modal");
      // 先关闭模态框，再重新加载数据
      if (closeHandler && typeof closeHandler === 'function') {
        console.log("Calling closeHandler");
        closeHandler();
      } else {
        console.log("closeHandler is not a function or is null");
      }
      
      console.log("About to reload prompts");
      // 重新加载prompts
      await loadPrompts();
      console.log("Prompts reloaded");
      
    } catch (error) {
      console.error("Failed to save prompt:", error);
      console.error("Error response:", error.response);
      console.error("Error response data:", error.response?.data);
      
      // 显示错误信息给用户
      let errorMessage = "Failed to save prompt. Please try again.";
      
      if (error.response?.data) {
        const errorData = error.response.data;
        if (errorData.name && Array.isArray(errorData.name)) {
          errorMessage = `Error: ${errorData.name[0]}`;
        } else if (errorData.name) {
          errorMessage = `Error: ${errorData.name}`;
        } else if (typeof errorData === 'string') {
          errorMessage = `Error: ${errorData}`;
        }
      }
      
      alert(errorMessage);
    } finally {
      console.log("Setting saving to false");
      setSaving(false);
      console.log("=== SAVE DEBUG END ===");
    }
  };

  const handleDeletePrompt = async (prompt) => {
    if (window.confirm(`Are you sure you want to delete "${prompt.name}"?`)) {
      try {
        await api.callApi("deletePrompt", {
          params: { id: prompt.id },
        });
        await loadPrompts();
      } catch (error) {
        console.error("Failed to delete prompt:", error);
      }
    }
  };

  if (loading) {
    return (
      <div className={Block}>
        <div className={Block.elem("loading")}>
          <Spinner size={64} />
        </div>
      </div>
    );
  }

  return (
    <div className={Block}>
      <div className={Block.elem("header")}>
        <h1 className={Block.elem("title")}>Prompts</h1>
        <Button onClick={handleCreatePrompt} look="primary">
          Create Prompt
        </Button>
      </div>

      <div className={Block.elem("content")}>
        {prompts.length === 0 ? (
          <div className={Block.elem("empty")}>
            <h2>No prompts yet</h2>
            <p>Create your first prompt to get started.</p>
            <Button onClick={handleCreatePrompt} look="primary">
              Create Prompt
            </Button>
          </div>
        ) : (
          <div 
            className={Block.elem("grid")} 
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(400px, 1fr))',
              gap: '20px'
            }}
          >
            {prompts.map(prompt => (
              <PromptCard
                key={prompt.id}
                prompt={prompt}
                onEdit={handleEditPrompt}
                onDelete={handleDeletePrompt}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

PromptsPage.title = "Prompts";
PromptsPage.path = "/prompts";
PromptsPage.exact = true;
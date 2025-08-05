import { createRef, useCallback, useState, useEffect } from "react";
import Button from "antd/lib/button/index";
import Form from "antd/lib/form/index";
import Input from "antd/lib/input/index";
import Tabs from "antd/lib/tabs";
import Modal from "antd/lib/modal/index";
import Tag from "antd/lib/tag/index";
import { observer } from "mobx-react";
import { destroy, isAlive, types } from "mobx-state-tree";
import ReactSimpleCodeEditor from "react-simple-code-editor";
import Prism from "prismjs";
import "prismjs/components/prism-json";
import "prismjs/themes/prism.css";
import Tooltip from "antd/lib/tooltip";
import { InfoCircleOutlined, EditOutlined, CommentOutlined } from "@ant-design/icons";

import InfoModal from "../../../components/Infomodal/Infomodal";
import Registry from "../../../core/Registry";
import Tree from "../../../core/Tree";
import Types from "../../../core/Types";
import { AnnotationMixin } from "../../../mixins/AnnotationMixin";
import LeadTimeMixin from "../../../mixins/LeadTime";
import PerItemMixin from "../../../mixins/PerItem";
import PerRegionMixin, { PER_REGION_MODES } from "../../../mixins/PerRegion";
import ProcessAttrsMixin from "../../../mixins/ProcessAttrs";
import { ReadOnlyControlMixin } from "../../../mixins/ReadOnlyMixin";
import RequiredMixin from "../../../mixins/Required";
import { HtxTextAreaRegion, TextAreaRegionModel } from "../../../regions/TextAreaRegion";
import { FF_LEAD_TIME, FF_LSDV_4583, isFF } from "../../../utils/feature-flags";
import ControlBase from "../Base";
import ClassificationBase from "../ClassificationBase";
import "./TextAreaRegionView";

import "./TextArea.scss";
import { cn } from "../../../utils/bem";

const { TextArea } = Input;

// Dynamic evaluation configuration - loaded from API
// Fallback configuration for when API is not available
const FALLBACK_REQUIRED_FIELDS = [
  "序号",
  "docType",
  "billToName", 
  "totalAmount", 
  "totalTaxAmount", 
  "invoiceNumber", 
  "invoiceDate", 
  "currency"
];

// 错误类型配置
const ERROR_TYPES = [
  "图像质量问题",
  "文字识别解析错误",
  "规则没转化", 
  "企业特殊要求",
  "系统问题",
  "其他"
];

// Cache for evaluation configurations - per project ID
const evaluationConfigCache = new Map();

// Centralized API utility for evaluation configs
class EvaluationConfigAPI {
  static CACHE_DURATION = 30 * 1000; // 30 seconds for faster testing
  
  static getAuthToken() {
    // Try multiple sources for the auth token
    const sources = [
      () => window.localStorage?.getItem('token'),
      () => window.localStorage?.getItem('auth_token'),
      () => window.localStorage?.getItem('access_token'),
      () => window.sessionStorage?.getItem('token'),
      () => window.sessionStorage?.getItem('auth_token'),
      () => window.sessionStorage?.getItem('access_token'),
      () => window.APP_SETTINGS?.token,
      () => window.LSF?.store?.auth?.token,
    ];
    
    for (const getToken of sources) {
      try {
        const token = getToken();
        if (token) return token;
      } catch (e) {
        // Continue to next source
      }
    }
    
    // Try cookies as last resort
    if (document.cookie) {
      const cookies = document.cookie.split(';');
      for (let cookie of cookies) {
        const [name, value] = cookie.split('=').map(s => s.trim());
        if (['token', 'auth_token', 'access_token'].includes(name)) {
          return value;
        }
      }
    }
    
    return null;
  }
  
  static createHeaders() {
    const headers = {
      'Content-Type': 'application/json'
    };
    
    const token = this.getAuthToken();
    if (token) {
      headers['Authorization'] = `Token ${token}`;
    }
    
    return headers;
  }
  
  static clearCache(projectId = null) {
    if (projectId) {
      const cacheKey = String(projectId);
      evaluationConfigCache.delete(cacheKey);
    } else {
      evaluationConfigCache.clear();
    }
  }
  
  static async fetchProjectConfig(projectId, forceRefresh = false) {
    const now = Date.now();
    const cacheKey = String(projectId);
    
    // Force refresh if requested
    if (forceRefresh) {
      this.clearCache(projectId);
    }
    
    // Return cached data if still valid and not forcing refresh
    const cachedData = evaluationConfigCache.get(cacheKey);
    if (!forceRefresh && cachedData && cachedData.expiry > now) {
      return cachedData.config;
    }
    
    try {
      // Use the unified API endpoint pattern
      const apiUrl = `/api/frontend/evaluation-configs/project/${projectId}/`;
      const headers = this.createHeaders();
      const response = await fetch(apiUrl, {
        headers: headers
      });
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${response.statusText} - ${errorText}`);
      }
      
      const config = await response.json();
      
      const requiredFields = [...(config.required_fields || [])];
      
      // Always include 序号 if not present
      if (!requiredFields.includes('序号')) {
        requiredFields.unshift('序号');
      }
      
      const configData = {
        required_fields: requiredFields,
        optional_fields: config.optional_fields || [],
        all_fields: config.all_fields || [],
        validation_rules: config.validation_rules || {},
        config_key: config.config_key || 'default',
        field_labels: config.field_labels || {},
        project_default_fields: config.project_default_fields || []
      };
      
      // Cache the result
      evaluationConfigCache.set(cacheKey, {
        config: configData,
        expiry: now + this.CACHE_DURATION
      });
      
      return configData;
      
    } catch (error) {
      throw error;
    }
  }
  
  static getFallbackConfig() {
    return {
      required_fields: FALLBACK_REQUIRED_FIELDS,
      optional_fields: [],
      all_fields: FALLBACK_REQUIRED_FIELDS,
      validation_rules: {},
      config_key: 'fallback'
    };
  }
  
  static async fetchAllConfigs() {
    try {
      const apiUrl = '/api/frontend/evaluation-configs/active/';
      
      const headers = this.createHeaders();
      const response = await fetch(apiUrl, { headers });
      
      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }
      
      const configs = await response.json();
      
      // 转换为以key为索引的对象
      const configsByKey = {};
      if (Array.isArray(configs)) {
        configs.forEach(config => {
          // 检查配置是否有效（不需要检查is_active，因为API已经过滤了）
          if (config.key) {
            const requiredFields = [...(config.required_fields || [])];
            if (!requiredFields.includes('序号')) {
              requiredFields.unshift('序号');
            }
            
            configsByKey[config.key] = {
              required_fields: requiredFields,
              optional_fields: config.optional_fields || [],
              all_fields: config.all_fields || [],
              validation_rules: config.validation_rules || config.field_validation_rules || {},
              config_key: config.key,
              field_labels: config.field_labels || {}
            };
          }
        });
      }
      
      return configsByKey;
    } catch (error) {
      return {};
    }
  }

  static async getConfigWithFallback(projectId, forceRefresh = false) {
    try {
      return await this.fetchProjectConfig(projectId, forceRefresh);
    } catch (error) {
      console.warn('Using fallback config, error:', error.message);
      const fallbackConfig = this.getFallbackConfig();
      
      // Cache the fallback too to avoid repeated failed requests (shorter duration)
      const now = Date.now();
      const cacheKey = String(projectId);
      evaluationConfigCache.set(cacheKey, {
        config: fallbackConfig,
        expiry: now + (this.CACHE_DURATION / 2) // Shorter cache for fallback
      });
      
      return fallbackConfig;
    }
  }
}

// Function to get required fields for highlighting
function getRequiredFields(item) {
  const annotation = item?.annotation;
  if (!annotation) {
    return FALLBACK_REQUIRED_FIELDS;
  }
  
  const store = annotation.store;
  if (!store) {
    return FALLBACK_REQUIRED_FIELDS;
  }
  
  // Try multiple ways to get project ID
  let projectId = store.projectId || store.project?.id;
  
  // Try to get from window object if not found
  if (!projectId && window.APP_SETTINGS?.projectId) {
    projectId = window.APP_SETTINGS.projectId;
  }
  
  // Try to get from URL if still not found
  if (!projectId && window.location) {
    const urlMatch = window.location.pathname.match(/\/projects\/(\d+)/);
    if (urlMatch) {
      projectId = parseInt(urlMatch[1]);
    }
  }
  
  // Try to get from history state
  if (!projectId && window.history?.state?.projectId) {
    projectId = window.history.state.projectId;
  }
  
  if (!projectId) {
    return FALLBACK_REQUIRED_FIELDS;
  }
  
  // Check if we have cached config for this project
  const cacheKey = String(projectId);
  const cachedData = evaluationConfigCache.get(cacheKey);
  
  if (cachedData && cachedData.expiry > Date.now()) {
    return cachedData.config.required_fields;
  }
  
  // Async load config (won't block rendering, will update on next render)
  EvaluationConfigAPI.getConfigWithFallback(projectId).then((config) => {
    // This will trigger a re-render with the correct fields
  }).catch((error) => {
    console.error('Failed to load evaluation config:', error);
  });
  
  const fallbackFields = cachedData?.config?.required_fields || FALLBACK_REQUIRED_FIELDS;
  return fallbackFields;
}

// 统一的必填字段获取函数 - 同时用于JSON验证和KV界面高亮
function getRequiredFieldsForDocument(docType, defaultRequiredFields, allConfigs) {
  // 对于docType为"other"或"unknown"的文档，不设置任何必填字段
  if (docType) {
    const docTypeLower = docType.toLowerCase();
    if (docTypeLower === 'other' || docTypeLower === 'unknown') {
      return []; // 不设置任何必填字段
    } else {
      // 如果找到了对应文档类型的配置，使用它
      const docConfig = allConfigs[docType];
      if (docConfig && docConfig.required_fields) {
        return docConfig.required_fields;
      }
    }
  }
  
  // 默认使用项目配置
  return defaultRequiredFields;
}

// 扩展的高亮函数：根据文档类型动态高亮必填字段
function highlightWithDynamicRequiredFields(code, allConfigs = {}, fallbackFields = FALLBACK_REQUIRED_FIELDS) {
  let html = Prism.highlight(code, Prism.languages.json, "json");
  
  try {
    // 先尝试解析JSON来获取文档结构
    const parsed = JSON.parse(code);
    
    if (Array.isArray(parsed)) {
      // 为每个文档根据其docType应用相应的高亮
              parsed.forEach((doc, index) => {
          const docType = doc.docType;
          const requiredFields = allConfigs[docType]?.required_fields || fallbackFields;
          
          // 为每个必填字段应用高亮
          requiredFields.forEach((field) => {
          // 创建更精确的正则表达式，匹配特定文档中的字段
          const fieldRegex = new RegExp(`<span class=\"token property\">(\\"${field}\\")<\/span>`, "g");
          html = html.replace(fieldRegex, `<span class=\"token property required-field required-field-${docType || 'default'}\">$1</span>`);

          // 给必填字段的值也添加对应的class
          const valueRegex = new RegExp(
            `(<span class=\"token property required-field required-field-${docType || 'default'}\">\\"${field}\\"<\/span><span class=\"token operator\">:<\/span>\\s*)(<span class=\"token (?:string|number|boolean|null)\">.*?<\/span>)`,
            "g",
          );
          html = html.replace(valueRegex, `$1<span class=\"token string required-field-value required-field-value-${docType || 'default'}\">$2</span>`);
        });
      });
    } else {
      // 如果不是数组，回退到原来的逻辑
      return highlightWithRequiredFields(code, fallbackFields);
    }
  } catch (e) {
    // JSON解析失败，回退到原来的逻辑
    return highlightWithRequiredFields(code, fallbackFields);
  }
  
  return html;
}

// 保留原来的高亮函数作为回退
function highlightWithRequiredFields(code, requiredFields = FALLBACK_REQUIRED_FIELDS) {
  let html = Prism.highlight(code, Prism.languages.json, "json");
  requiredFields.forEach((field) => {
    // 给必填字段名添加 required-field class
    const fieldRegex = new RegExp(`<span class=\"token property\">(\\"${field}\\")<\/span>`, "g");
    html = html.replace(fieldRegex, `<span class=\"token property required-field\">$1</span>`);

    // 给必填字段的值也添加 required-field class
    const valueRegex = new RegExp(
      `(<span class=\"token property required-field\">\\"${field}\\"<\/span><span class=\"token operator\">:<\/span>\\s*)(<span class=\"token (?:string|number|boolean|null)\">.*?<\/span>)`,
      "g",
    );
    html = html.replace(valueRegex, `$1<span class=\"token string required-field-value\">$2</span>`);
  });
  return html;
}

/**
 * The `TextArea` tag is used to display a text area for user input. Use for transcription, paraphrasing, or captioning tasks.
 *
 * Use with the following data types: audio, image, HTML, paragraphs, text, time series, video.
 *
 * @example
 * <!--Basic labeling configuration to display only a text area -->
 * <View>
 *   <TextArea name="ta"></TextArea>
 * </View>
 * @example
 * <!--You can combine the `TextArea` tag with other tags for OCR or other transcription tasks-->
 * <View>
 *   <Image name="image" value="$ocr"/>
 *   <Labels name="label" toName="image">
 *     <Label value="Product" background="#166a45"/>
 *     <Label value="Price" background="#2a1fc7"/>
 *   </Labels>
 *   <Rectangle name="bbox" toName="image" strokeWidth="3"/>
 *   <TextArea name="transcription" toName="image" editable="true" perRegion="true" required="true" maxSubmissions="1" rows="5" placeholder="Recognized Text" displayMode="region-list"/>
 * </View>
 * @example
 * <!--
 *  You can keep submissions unique.
 * -->
 * <View>
 *   <Audio name="audio" value="$audio"/>
 *   <TextArea name="genre" toName="audio" skipDuplicates="true" />
 * </View>
 * @name TextArea
 * @meta_title Textarea Tag for Text areas
 * @meta_description Customize Label Studio with the TextArea tag to support audio transcription, image captioning, and OCR tasks for machine learning and data science projects.
 * @param {string} name                    - Name of the element
 * @param {string} toName                  - Name of the element that you want to label
 * @param {string} value                   - Pre-filled value
 * @param {string=} [label]                - Label text
 * @param {string=} [placeholder]          - Placeholder text
 * @param {string=} [maxSubmissions]       - Maximum number of submissions
 * @param {boolean=} [editable=false]      - Whether to display an editable textarea
 * @param {boolean} [skipDuplicates=false] - Prevent duplicates in textarea inputs
 * @param {boolean=} [transcription=false] - If false, always show editor
 * @param {tag|region-list} [displayMode=tag] - Display mode for the textarea; region-list shows it for every region in regions list
 * @param {number} [rows]                  - Number of rows in the textarea
 * @param {boolean} [required=false]       - Validate whether content in textarea is required
 * @param {string} [requiredMessage]       - Message to show if validation fails
 * @param {boolean=} [showSubmitButton]    - Whether to show or hide the submit button. By default it shows when there are more than one rows of text, such as in textarea mode.
 * @param {boolean} [perRegion]            - Use this tag to label regions instead of whole objects
 * @param {boolean} [perItem]              - Use this tag to label items inside objects instead of whole objects
 */
const TagAttrs = types.model({
  toname: types.maybeNull(types.string),
  allowsubmit: types.optional(types.boolean, true),
  label: types.optional(types.string, ""),
  value: types.maybeNull(types.string),
  rows: types.optional(types.string, "1"),
  showsubmitbutton: types.maybeNull(types.boolean),
  placeholder: types.maybeNull(types.string),
  maxsubmissions: types.maybeNull(types.string),
  editable: types.optional(types.boolean, false),
  transcription: false,
  skipduplicates: types.optional(types.boolean, false),
});

const Model = types
  .model({
    type: "textarea",
    // @todo rename to textarearegions to avoid confusion, they are not real regions or results
    regions: types.array(TextAreaRegionModel),
    _value: types.optional(types.string, ""),
    children: Types.unionArray(["shortcut"]),
  })
  .volatile(() => {
    return {
      focusable: true,
      textareaRef: createRef(),
    };
  })
  .views((self) => ({
    get isEditable() {
      return self.editable && self.annotation.editable;
    },

    get isDeleteable() {
      return !self.isReadOnly();
    },

    get valueType() {
      return "text";
    },

    get holdsState() {
      return self.regions.length > 0;
    },

    get submissionsNum() {
      return self.regions.length;
    },

    get showSubmit() {
      if (self.maxsubmissions) {
        const num = Number.parseInt(self.maxsubmissions);

        return self.submissionsNum < num;
      }
      return true;
    },

    // @todo not used?
    get serializableValue() {
      if (!self.regions.length) return null;
      return { text: self.selectedValues() };
    },

    // Main and only method to update value in actual result produced by TextArea
    selectedValues() {
      return self.regions.map((r) => r._value);
    },

    hasResult(text) {
      if (!self.result) return false;
      let value = self.result.mainValue;

      if (!Array.isArray(value)) value = [value];
      text = text.toLowerCase();
      return value.some((val) => val.toLowerCase() === text);
    },
  }))
  .actions((self) => (isFF(FF_LEAD_TIME) ? {} : { countTime: () => {} }))
  .actions((self) => {
    let lastActiveElement = null;
    let lastActiveElementModel = null;

    const isAvailableElement = (element, elementModel) => {
      if (!element || !elementModel || !isAlive(elementModel)) return false;
      // Not available if active element is disappeared
      if (self === elementModel && !self.showSubmit) return false;
      if (!element.parentElement) return false;
      return true;
    };

    return {
      // @todo not used?
      getSerializableValue() {
        const texts = self.regions.map((s) => s._value);

        if (texts.length === 0) return;

        return { text: texts };
      },

      needsUpdate() {
        self.updateFromResult(self.result?.mainValue);
      },

      requiredModal() {
        InfoModal.warning(self.requiredmessage || `Input for the textarea "${self.name}" is required.`);
      },

      uniqueModal() {
        InfoModal.warning("There is already an entry with that text. Please enter unique text.");
      },

      setResult(value) {
        const values = Array.isArray(value) ? value : [value];

        values.forEach((v) => self.createRegion(v));
      },

      updateFromResult(value) {
        self.regions = [];
        value && self.setResult(value);
      },

      setValue(value) {
        self._value = value;
      },

      remove(region) {
        const index = self.regions.indexOf(region);

        if (index < 0) return;
        self.regions.splice(index, 1);
        destroy(region);
        self.onChange(region);
      },

      perRegionCleanup() {
        self.regions = [];
      },

      createRegion(text, pid, leadTime) {
        const r = TextAreaRegionModel.create({ pid, leadTime, _value: text });

        self.regions.push(r);
        return r;
      },

      onChange(area) {
        self.updateResult();
        const currentArea = area ?? self.result?.area;

        currentArea?.notifyDrawingFinished();
      },

      validateText(text) {
        if (self.skipduplicates && self.hasResult(text)) {
          self.uniqueModal();
          return false;
        }
        return true;
      },

      addText(text, pid) {
        if (!self.validateText(text)) return;

        self.createRegion(text, pid, self.leadTime);
        // actually creates a new result
        self.onChange();

        // should go after `onChange` because it uses result and area
        self.updateLeadTime();
      },

      /**
       * `lead_time` should be stored inside connected results,
       *   we shouldn't store it in TextAreaRegions,
       *   because TextAreaRegions are not safe, they can be rewritten
       *   on undo/redo, on switching annotations, on switching regions...
       * After adding lead_time to the result, we should reset all lead_time numbers
       */
      updateLeadTime() {
        if (!isFF(FF_LEAD_TIME)) return;

        const result = self.result;

        if (!result) return;

        // add current stored leadTime to the main stored lead_time
        result.setMetaValue("lead_time", (result.meta?.lead_time ?? 0) + self.leadTime / 1000);

        self.leadTime = 0;
        self.resetLeadTimeCounters();
      },

      addTextToResult(text, result) {
        if (!self.validateText(text)) return;

        const newValue = result.mainValue.toJSON();

        newValue.push(text);
        result.setValue(newValue);
      },

      beforeSend() {
        if (self._value && self._value.length) {
          self.addText(self._value);
          self._value = "";
        }
      },

      // add unsubmitted text when user switches region
      submitChanges() {
        self.beforeSend();
      },

      deleteText(text) {
        destroy(text);
      },

      onShortcut(value) {
        if (!isAvailableElement(lastActiveElement, lastActiveElementModel)) {
          // Try to use main textarea element
          const textareaElement =
            self.textareaRef.current?.input || self.textareaRef.current?.resizableTextArea?.textArea;

          if (isAvailableElement(textareaElement, self)) {
            lastActiveElement = textareaElement;
            lastActiveElementModel = self;
          } else {
            return;
          }
        }
        lastActiveElement.setRangeText(value, lastActiveElement.selectionStart, lastActiveElement.selectionEnd, "end");
        lastActiveElementModel.setValue(lastActiveElement.value);
      },

      setLastFocusedElement(element, model = self) {
        lastActiveElement = element;
        lastActiveElementModel = model;
      },

      returnFocus() {
        lastActiveElement?.focus?.();
      },
    };
  });

const TextAreaModel = types.compose(
  "TextAreaModel",
  ControlBase,
  ClassificationBase,
  TagAttrs,
  ...(isFF(FF_LEAD_TIME) ? [LeadTimeMixin] : []),
  ProcessAttrsMixin,
  RequiredMixin,
  PerRegionMixin,
  ...(isFF(FF_LSDV_4583) ? [PerItemMixin] : []),
  AnnotationMixin,
  ReadOnlyControlMixin,
  Model,
);

const HtxTextArea = observer(({ item }) => {
  const rows = Number.parseInt(item.rows);
  const [jsonError, setJsonError] = useState("");
  const [jsonFieldError, setJsonFieldError] = useState("");
  const [pageStats, setPageStats] = useState("");
  const [requiredFields, setRequiredFields] = useState(FALLBACK_REQUIRED_FIELDS);
  const [evaluationConfig, setEvaluationConfig] = useState(null);
  const [allConfigs, setAllConfigs] = useState({}); // 所有评估配置
  const [activeTab, setActiveTab] = useState("kv"); // 添加tab状态
  
  // 字段备注相关状态
  const [fieldAnnotationsModalVisible, setFieldAnnotationsModalVisible] = useState(false);
  const [currentFieldKey, setCurrentFieldKey] = useState(null);
  const [currentFieldAnnotation, setCurrentFieldAnnotation] = useState({ errorTypes: [], reason: "" });
  const [fieldAnnotations, setFieldAnnotations] = useState({}); // 存储所有字段备注
  
  const onFocus = useCallback(
    (ev, model) => {
      item.setLastFocusedElement(ev.target, model);
    },
    [item],
  );

  // 获取当前text数组的索引（最新的一个）
  const getCurrentTextIndex = useCallback(() => {
    if (item.regions && item.regions.length > 0) {
      return item.regions.length - 1;
    }
    return 0;
  }, [item.regions]);

  // 从result中加载字段备注
  const loadFieldAnnotations = useCallback(() => {
    try {
      const result = item.result;
      if (result && result.value && result.value.field_annotations) {
        const textIndex = getCurrentTextIndex();
        const textKey = `text_index_${textIndex}`;
        const annotations = result.value.field_annotations[textKey] || {};
        setFieldAnnotations(annotations);
      }
    } catch (error) {
      console.error('Error loading field annotations:', error);
    }
  }, [item.result, getCurrentTextIndex]);

  // 保存字段备注到result
  const saveFieldAnnotations = useCallback((annotations) => {
    try {
      const result = item.result;
      if (result) {
        const textIndex = getCurrentTextIndex();
        const textKey = `text_index_${textIndex}`;
        
        // 初始化field_annotations结构
        if (!result.value.field_annotations) {
          result.value.field_annotations = {};
        }
        if (!result.value.field_annotations[textKey]) {
          result.value.field_annotations[textKey] = {};
        }
        
        // 保存当前字段的备注
        result.value.field_annotations[textKey] = { ...annotations };
        
        // 触发result更新
        item.updateResult();
      }
    } catch (error) {
      console.error('Error saving field annotations:', error);
    }
  }, [item, getCurrentTextIndex]);

  // 处理字段备注点击
  const handleFieldAnnotationClick = useCallback((arrayIndex, fieldKey) => {
    const annotationKey = `ticket_${arrayIndex}_${fieldKey}`;
    const existingAnnotation = fieldAnnotations[annotationKey] || { errorTypes: [], reason: "" };
    
    setCurrentFieldKey(annotationKey);
    setCurrentFieldAnnotation({ ...existingAnnotation });
    setFieldAnnotationsModalVisible(true);
  }, [fieldAnnotations]);

  // 保存字段备注
  const handleSaveFieldAnnotation = useCallback(() => {
    const updatedAnnotations = {
      ...fieldAnnotations,
      [currentFieldKey]: { ...currentFieldAnnotation }
    };
    
    // 如果备注为空，删除该字段的备注
    if (currentFieldAnnotation.errorTypes.length === 0 && !currentFieldAnnotation.reason.trim()) {
      delete updatedAnnotations[currentFieldKey];
    }
    
    setFieldAnnotations(updatedAnnotations);
    saveFieldAnnotations(updatedAnnotations);
    setFieldAnnotationsModalVisible(false);
    setCurrentFieldKey(null);
    setCurrentFieldAnnotation({ errorTypes: [], reason: "" });
  }, [fieldAnnotations, currentFieldKey, currentFieldAnnotation, saveFieldAnnotations]);

  // 检查字段是否有备注
  const hasFieldAnnotation = useCallback((arrayIndex, fieldKey) => {
    const annotationKey = `ticket_${arrayIndex}_${fieldKey}`;
    const annotation = fieldAnnotations[annotationKey];
    return annotation && (annotation.errorTypes.length > 0 || annotation.reason.trim());
  }, [fieldAnnotations]);


  // Load evaluation configuration on component mount
  useEffect(() => {
    const loadEvaluationConfig = async () => {
      try {
        const annotation = item?.annotation;
        
        if (!annotation) {
          return;
        }
        
        const store = annotation.store;
        
        if (!store) {
          return;
        }
        
        // Try multiple ways to get project ID with enhanced logging
        let projectId = store.projectId || store.project?.id;
        
        // Try to get from window object if not found
        if (!projectId && window.APP_SETTINGS?.projectId) {
          projectId = window.APP_SETTINGS.projectId;
        }
        
        // Try to get from URL if still not found
        if (!projectId && window.location) {
          const urlMatch = window.location.pathname.match(/\/projects\/(\d+)/);
          if (urlMatch) {
            projectId = parseInt(urlMatch[1]);
          }
        }
        
        // Try to get from history state
        if (!projectId && window.history?.state?.projectId) {
          projectId = window.history.state.projectId;
        }
        
        // Try to get from global store if available
        if (!projectId && window.LSF?.store?.projectId) {
          projectId = window.LSF.store.projectId;
        }
        
        if (!projectId) {
          setRequiredFields(FALLBACK_REQUIRED_FIELDS);
          return;
        }
        
        // 并行获取项目配置和所有配置
        const [config, allConfigsData] = await Promise.all([
          EvaluationConfigAPI.getConfigWithFallback(projectId, true),
          EvaluationConfigAPI.fetchAllConfigs()
        ]);
        
        if (config) {
          setRequiredFields(config.required_fields);
          setEvaluationConfig(config);
        } else {
          setRequiredFields(FALLBACK_REQUIRED_FIELDS);
        }
        
        if (allConfigsData && Object.keys(allConfigsData).length > 0) {
          setAllConfigs(allConfigsData);
        } else {
          setAllConfigs({});
        }
      } catch (error) {
        setRequiredFields(FALLBACK_REQUIRED_FIELDS);
      }
    };

    loadEvaluationConfig();
  }, [item?.annotation?.store?.projectId, item?.annotation?.store?.project?.id]);

  // 加载字段备注
  useEffect(() => {
    loadFieldAnnotations();
  }, [loadFieldAnnotations, item.result]);

  // 新增：自动填充按钮逻辑
  const [autoFillLoading, setAutoFillLoading] = useState(false);
  // 仅当当前值为空且 name 包含 json 时显示按钮
  const showAutoFill =
    !item._value &&
    item.displaymode === PER_REGION_MODES.TAG &&
    item.name &&
    item.name.toLowerCase().includes("json");

  // 检查是否应该执行自动更新（不仅是空字段，切换tab时也要更新）
  const shouldAutoUpdate =
    item.displaymode === PER_REGION_MODES.TAG &&
    item.name &&
    item.name.toLowerCase().includes("json");


  // 辅助函数：提取(id: xxx)中的xxx
  const extractName = (str) => {
    if (typeof str !== 'string') return str;
    const match = str.match(/\(id: ([^)]+)\)/);
    return match ? match[1] : str;
  };

  // 自动填充处理
  const handleAutoFill = async () => {
    setAutoFillLoading(true);
    try {
      const store = item.annotation?.store;
      const annotationStore = store?.annotationStore;
      const preds = annotationStore?.predictions?.toJSON ? annotationStore.predictions.toJSON() : annotationStore.predictions;
      let filled = false;

      // 检查当前选中的是否为prediction
      const isPredictionSelected = item.annotation?.type === "prediction";
      
      // 获取当前选中的prediction ID（如果是prediction模式）
      const currentPredictionId = isPredictionSelected ? item.annotation?.id : null;

      if (isPredictionSelected && currentPredictionId) {
        // 当前在查看prediction时，只使用当前选中的prediction数据
        if (Array.isArray(preds)) {
          // 找到当前选中的prediction
          const currentPred = preds.find(pred => pred.id === currentPredictionId);
          if (currentPred) {
            // 只处理当前选中的prediction
            if (currentPred.trackedState && currentPred.trackedState.areas) {
              Array.from(currentPred.trackedState.areas.values()).forEach(area => {
                if (Array.isArray(area.results)) {
                  area.results.forEach(r => {
                    const fromName = extractName(typeof r.from_name === 'string' ? r.from_name : String(r.from_name));
                    const toName = extractName(typeof r.to_name === 'string' ? r.to_name : String(r.to_name));
                    if (
                      fromName === item.name &&
                      toName === item.toname &&
                      r.type === "textarea" &&
                      r.value && r.value.text && r.value.text.length > 0
                    ) {
                      const value = Array.isArray(r.value.text) ? r.value.text[r.value.text.length - 1] : r.value.text;
                      item.setValue(value);
                      validateJsonAndFields(value);
                      filled = true;
                    }
                  });
                }
              });
            }
            if (!filled && currentPred.result) {
              for (const r of currentPred.result) {
                const fromName = extractName(typeof r.from_name === 'string' ? r.from_name : String(r.from_name));
                const toName = extractName(typeof r.to_name === 'string' ? r.to_name : String(r.to_name));
                if (
                  fromName === item.name &&
                  toName === item.toname &&
                  r.type === "textarea" &&
                  r.value && r.value.text && r.value.text.length > 0
                ) {
                  const value = Array.isArray(r.value.text) ? r.value.text[r.value.text.length - 1] : r.value.text;
                  item.setValue(value);
                  validateJsonAndFields(value);
                  filled = true;
                  break; // 找到就退出
                }
              }
            }
          }
        }

        // 如果当前prediction没有数据，不要fallback到annotations，保持一致性
      } else {
        // 当前在查看annotation时，保持原有逻辑：优先使用annotations数据
        // 1. 先用 annotations
        if (annotationStore?.annotations) {
          const anns = annotationStore.annotations.toJSON ? annotationStore.annotations.toJSON() : annotationStore.annotations;
          let lastMatchedValue = null;
          for (const ann of anns) {
            let results = ann.result;
            if (!results && ann.resultSnapshot) results = ann.resultSnapshot;
            if (!results && ann._initialAnnotationObj && ann._initialAnnotationObj.result) results = ann._initialAnnotationObj.result;
            // If still no results, treat _initialAnnotationObj as an array of result items
            if (
              !results &&
              ann._initialAnnotationObj &&
              (Array.isArray(ann._initialAnnotationObj) || typeof ann._initialAnnotationObj === 'object')
            ) {
              // Convert to array if it's an object with numeric keys
              const arr = Array.isArray(ann._initialAnnotationObj)
                ? ann._initialAnnotationObj
                : Object.values(ann._initialAnnotationObj).filter(v => v && typeof v === 'object' && v.type);
              if (arr.length > 0) results = arr;
            }
            if (results && typeof results.toJSON === 'function') {
              results = results.toJSON();
            }
            if (Array.isArray(results)) {
              for (const r of results) {
                const fromName = extractName(typeof r.from_name === 'string' ? r.from_name : String(r.from_name));
                const toName = extractName(typeof r.to_name === 'string' ? r.to_name : String(r.to_name));
                if (
                  fromName === item.name &&
                  toName === item.toname &&
                  r.type === "textarea" &&
                  r.value && r.value.text && r.value.text.length > 0
                ) {
                  const value = Array.isArray(r.value.text) ? r.value.text[r.value.text.length - 1] : r.value.text;
                  lastMatchedValue = value;
                }
              }
            }
          }
          if (lastMatchedValue !== null) {
            item.setValue(lastMatchedValue);
            validateJsonAndFields(lastMatchedValue);
            filled = true;
          }
        }

        // 2. annotations 没命中再用 predictions
        if (!filled && Array.isArray(preds)) {
          for (const pred of preds) {
            if (pred.trackedState && pred.trackedState.areas) {
              Array.from(pred.trackedState.areas.values()).forEach(area => {
                if (Array.isArray(area.results)) {
                  area.results.forEach(r => {
                    const fromName = extractName(typeof r.from_name === 'string' ? r.from_name : String(r.from_name));
                    const toName = extractName(typeof r.to_name === 'string' ? r.to_name : String(r.to_name));
                    if (
                      fromName === item.name &&
                      toName === item.toname &&
                      r.type === "textarea" &&
                      r.value && r.value.text && r.value.text.length > 0
                    ) {
                      const value = Array.isArray(r.value.text) ? r.value.text[r.value.text.length - 1] : r.value.text;
                      item.setValue(value);
                      validateJsonAndFields(value);
                      filled = true;
                    }
                  });
                }
              });
            }
            if (pred.result) {
              for (const r of pred.result) {
                const fromName = extractName(typeof r.from_name === 'string' ? r.from_name : String(r.from_name));
                const toName = extractName(typeof r.to_name === 'string' ? r.to_name : String(r.to_name));
                if (
                  fromName === item.name &&
                  toName === item.toname &&
                  r.type === "textarea" &&
                  r.value && r.value.text && r.value.text.length > 0
                ) {
                  const value = Array.isArray(r.value.text) ? r.value.text[r.value.text.length - 1] : r.value.text;
                  item.setValue(value);
                  validateJsonAndFields(value);
                  filled = true;
                }
              }
            }
          }
        }
      }
      
    } finally {
      setAutoFillLoading(false);
    }
  };

  // 新增：labelstream/Label All Tasks模式下自动触发自动填充
  useEffect(() => {
    // 关键节点日志：自动填充触发
    if (showAutoFill) {
      
    }
    if (showAutoFill) {
      handleAutoFill();
    }
  }, [showAutoFill]);

  // 新增：监听annotation类型变化，当切换tab时自动更新内容
  useEffect(() => {
    if (shouldAutoUpdate) {
      handleAutoFill();
    }
  }, [item.annotation?.type, shouldAutoUpdate]);

  // 校验JSON和必填字段的复用函数
  const validateJsonAndFields = useCallback(
    (value) => {
      if (item.name && item.name.toLowerCase().includes("json")) {
        if (value) {
          try {
            const parsed = JSON.parse(value);
            setJsonError("");
            // 检查是否为数组
            if (Array.isArray(parsed)) {
              // 为每个元素添加序号字段
              let needsUpdate = false;
              const updatedArray = parsed.map((item, index) => {
                const serialNumber = index + 1;
                if (!item.hasOwnProperty("序号") || item["序号"] !== serialNumber) {
                  needsUpdate = true;
                  // 创建新对象，序号在前
                  const newItem = { 序号: serialNumber };
                  // 复制其他属性（排除已存在的序号）
                  Object.keys(item).forEach((key) => {
                    if (key !== "序号") {
                      newItem[key] = item[key];
                    }
                  });
                  return newItem;
                }
                return item;
              });

              // 如果需要更新，更新JSON值
              if (needsUpdate) {
                const updatedJson = JSON.stringify(updatedArray, null, 2);
                item.setValue(updatedJson);
                return; // 退出，等待下次调用来验证更新后的值
              }

              // 统计每页票据数量
              const pageCount = {};
              const multiPageTickets = []; // 存储跨多页的票据信息
              let hasFieldErrors = false;
              let allErrorMessages = []; // 收集所有错误信息

              // 预先获取项目特定配置，避免在循环中重复获取
              const annotation = item?.annotation;
              const store = annotation?.store;
              const projectId = store?.projectId || store?.project?.id;
              
              let currentRequiredFields = requiredFields;
              let currentEvaluationConfig = evaluationConfig;
              let currentAllConfigs = allConfigs;
              
              // 尝试获取项目特定配置
              if (projectId) {
                const cacheKey = String(projectId);
                const cachedData = evaluationConfigCache.get(cacheKey);
                if (cachedData && cachedData.expiry > Date.now()) {
                  currentRequiredFields = cachedData.config.required_fields;
                  currentEvaluationConfig = cachedData.config;
                }
              }

              for (let i = 0; i < parsed.length; i++) {
                const x = parsed[i];
                // 创建原始数据副本用于字段验证
                const originalDoc = { ...x };
                const missing = [];

                // 获取页码，默认为第1页
                const pages = x.page && Array.isArray(x.page) ? x.page : [1];

                // 检查docType字段 - 统计所有除了"other"之外的文档类型
                let isValidDocType = true;
                
                // 如果没有docType字段，但数据包含其他必需字段，则尝试推断类型
                if (!x.docType) {
                  // 尝试根据当前配置类型或数据特征设置默认docType
                  if (x.tradeDate && x.amount && (x.paymentName || x.payeeName)) {
                    x.docType = 'bank_receipt';
                  } else if (x.invoiceNumber && x.totalAmount && (x.billToName || x.buyerName)) {
                    x.docType = 'invoice';
                  } else if (x.totalAmount && !x.invoiceNumber && !x.tradeDate) {
                    x.docType = 'receipt';
                  }
                }
                
                // 票据统计逻辑：统计所有除了"other"之外的文档类型
                if (x.docType) {
                  const docTypeLower = x.docType.toLowerCase();
                  if (docTypeLower === 'other' || docTypeLower === 'unknown') {
                    isValidDocType = false; // 标记为无效，不参与票据统计
                  } else {
                    isValidDocType = true;
                  }
                } else {
                  // 如果仍然没有docType，标记为无效票据类型（不参与统计）
                  isValidDocType = false;
                }
                
                // 票据统计处理（但不影响字段验证）
                let shouldCountForStats = isValidDocType;

                // 只有有效票据类型才进行统计
                if (shouldCountForStats) {
                  // 如果是跨多页的票据，记录范围信息
                  if (pages.length > 1) {
                    const sortedPages = [...pages].sort((a, b) => a - b);
                    // 检查是否为连续页码
                    let isConsecutive = true;
                    for (let j = 1; j < sortedPages.length; j++) {
                      if (sortedPages[j] !== sortedPages[j - 1] + 1) {
                        isConsecutive = false;
                        break;
                      }
                    }
                    if (isConsecutive) {
                      multiPageTickets.push({
                        range: `p${sortedPages[0]}-p${sortedPages[sortedPages.length - 1]}`,
                        pages: sortedPages,
                        startPage: sortedPages[0],
                      });
                    } else {
                      // 非连续页码，按单页处理
                      sortedPages.forEach((page) => {
                        if (!pageCount[page]) {
                          pageCount[page] = 0;
                        }
                        pageCount[page]++;
                      });
                    }
                  } else {
                    // 单页票据
                    const page = pages[0];
                    if (!pageCount[page]) {
                      pageCount[page] = 0;
                    }
                    pageCount[page]++;
                  }
                }

                // 动态字段验证逻辑 - 使用统一的必填字段获取函数
                const docType = x.docType;
                const fieldsToCheck = getRequiredFieldsForDocument(docType, currentRequiredFields, currentAllConfigs);
                const docConfig = currentAllConfigs[docType];
                let docConfigForLabel = docConfig || currentEvaluationConfig;
                
                fieldsToCheck.forEach((field) => {
                  // 对于docType字段，检查原始数据是否包含
                  if (field === 'docType') {
                    if (!originalDoc.hasOwnProperty('docType')) {
                      missing.push(field);
                    }
                  } else {
                    // 其他字段检查当前数据
                    if (!x.hasOwnProperty(field)) {
                      missing.push(field);
                    }
                  }
                });
                
                if (missing.length > 0) {
                  hasFieldErrors = true;
                  // 根据配置获取文档类型显示名
                  const docTypeValidationRules = docConfigForLabel?.validation_rules?.docType;
                  let docTypeText = x.docType || "文档";
                  
                  // 如果有配置的映射，使用友好的显示名
                  if (docTypeValidationRules && docConfigForLabel?.field_labels?.docType) {
                    docTypeText = docConfigForLabel.field_labels.docType[x.docType] || docTypeText;
                  }
                  
                  const errorMsg = `${docTypeText}[${i + 1}]缺: ${missing.map((m) => `"${m}"`).join(", ")}`;
                  allErrorMessages.push(errorMsg);
                }
              }

              // 生成显示结果
              const statsArray = [];

              // 添加单页统计
              const pageNumbers = Object.keys(pageCount)
                .map(Number)
                .sort((a, b) => a - b);
              pageNumbers.forEach((page) => {
                statsArray.push({ text: `p${page}: ${pageCount[page]}票`, sortKey: page });
              });

              // 添加跨多页票据
              multiPageTickets.forEach((ticket) => {
                statsArray.push({ text: `${ticket.range}: 1票`, sortKey: ticket.startPage });
              });

              // 按页码排序
              statsArray.sort((a, b) => a.sortKey - b.sortKey);

              setPageStats(statsArray.length > 0 ? statsArray.map((item) => item.text).join(", ") : "暂无票据");
              
              // 显示所有错误信息，但限制最多显示3个，超过则显示省略号
              if (hasFieldErrors) {
                if (allErrorMessages.length <= 3) {
                  const finalErrorMsg = allErrorMessages.join("\n");
                  setJsonFieldError(finalErrorMsg);
                } else {
                  const finalErrorMsg = `${allErrorMessages.slice(0, 3).join("\n")}\n...等共${allErrorMessages.length}票，缺核心字段`;
                  setJsonFieldError(finalErrorMsg);
                }
              } else {
                setJsonFieldError("");
              }
            } else {
              setJsonFieldError("");
              setPageStats("非数组格式");
            }
          } catch (e) {
            setJsonError(`JSON错: ${e.message}`);
            setJsonFieldError("");
            setPageStats("JSON格式错误");
          }
        } else {
          setJsonError("");
          setJsonFieldError("");
          setPageStats("");
        }
      } else {
        setJsonError("");
        setJsonFieldError("");
        setPageStats("");
      }
    },
    [item.name, evaluationConfig, requiredFields, allConfigs],
  );

  // 监听item._value、item.name和evaluation配置变化，自动校验
  useEffect(() => {
    validateJsonAndFields(item._value);
  }, [item._value, item.name, evaluationConfig, requiredFields, allConfigs, validateJsonAndFields]);

  const props = {
    name: item.name,
    value: item._value,
    rows: item.rows,
    className: "is-search",
    label: item.label,
    placeholder: item.placeholder,
    disabled: item.isReadOnly(),
    readOnly: item.isReadOnly(),
    onChange: (ev) => {
      if (item.annotation.isReadOnly()) return;
      const value = ev;
      item.setValue(value);
      validateJsonAndFields(value);
    },
    onFocus,
    ref: item.textareaRef,
    onKeyPress: item.countTime,
    onKeyDown: item.countTime,
    onKeyUp: item.countTime,
    onMouseDown: item.countTime,
    onMouseUp: item.countTime,
    onMouseMove: (ev) => (ev.button || ev.buttons) && item.countTime(),
  };

  if (rows > 1) {
    // allow to add multiline text with shift+enter
    props.onKeyDown = (e) => {
      if (e.key === "Enter" && e.shiftKey && item.allowsubmit && item._value && !item.annotation.isReadOnly()) {
        e.preventDefault();
        e.stopPropagation();
        item.addText(item._value);
        item.setValue("");
      } else {
        item.countTime();
      }
    };
  }

  const visibleStyle = item.perRegionVisible() ? {} : { display: "none" };

  const showAddButton = !item.isReadOnly() && (item.showsubmitbutton ?? rows !== 1);
  const itemStyle = {};
  const textareaClassName = cn("text-area").toClassName();

  if (showAddButton) itemStyle.marginBottom = 0;

  visibleStyle.marginTop = "4px";

  // Debug helper function
  const handleRefreshConfig = async () => {
    const annotation = item?.annotation;
    if (!annotation?.store) return;
    
    let projectId = annotation.store.projectId || annotation.store.project?.id;
    if (!projectId && window.location) {
      const urlMatch = window.location.pathname.match(/\/projects\/(\d+)/);
      if (urlMatch) {
        projectId = parseInt(urlMatch[1]);
      }
    }
    
    if (projectId) {
      try {
        const config = await EvaluationConfigAPI.fetchProjectConfig(projectId, true);
        setRequiredFields(config.required_fields);
        setEvaluationConfig(config);
      } catch (error) {
        console.error('配置刷新失败:', error);
      }
    }
  };

  // 处理KV模式下的值变更
  const handleKVValueChange = useCallback((arrayIndex, key, value) => {
    try {
      const parsed = JSON.parse(item._value || "[]");
      if (Array.isArray(parsed) && parsed[arrayIndex]) {
        // 创建新的对象来更新值
        const updatedItem = { ...parsed[arrayIndex] };
        updatedItem[key] = value;
        
        // 更新数组
        const updatedArray = [...parsed];
        updatedArray[arrayIndex] = updatedItem;
        
        // 更新JSON值
        const updatedJson = JSON.stringify(updatedArray, null, 2);
        item.setValue(updatedJson);
        validateJsonAndFields(updatedJson);
      }
    } catch (error) {
      console.error('Error updating KV value:', error);
    }
  }, [item, validateJsonAndFields]);

  // 解析JSON数据用于KV显示
  const parseJsonForKV = useCallback(() => {
    try {
      const parsed = JSON.parse(item._value || "[]");
      if (Array.isArray(parsed)) {
        return parsed;
      }
      return [];
    } catch (error) {
      return [];
    }
  }, [item._value]);

  return item.displaymode === PER_REGION_MODES.TAG ? (
    <div className={textareaClassName} style={visibleStyle} ref={item.elementRef}>
      {/* 调试按钮 - 开发环境可见 */}
      {(window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1') && (
        <div style={{ display: "flex", alignItems: "center", marginBottom: 8 }}>
          <Button
            size="small"
            onClick={handleRefreshConfig}
            style={{ 
              fontSize: "12px",
              height: "24px",
              backgroundColor: "#f0f0f0",
              border: "1px solid #d9d9d9"
            }}
          >
            刷新配置 (调试)
          </Button>
          <span style={{ marginLeft: "8px", fontSize: "12px", color: "#666" }}>
            当前配置: {evaluationConfig?.config_key || 'fallback'}
          </span>
        </div>
      )}
      {/* 自动填充按钮 - 设置为不可见 */}
      {showAutoFill && (
        <div style={{ display: "flex", alignItems: "center", marginBottom: 0, height: 0 }}>
          <Button
            size="small"
            icon={<InfoCircleOutlined style={{ display: "none" }} />}
            loading={autoFillLoading}
            onClick={handleAutoFill}
            style={{ 
              opacity: 0, 
              width: 0, 
              height: 0, 
              padding: 0, 
              margin: 0, 
              border: "none", 
              overflow: "hidden", 
              position: "absolute" 
            }}
          >
            自动填充
          </Button>
        </div>
      )}
      {pageStats && <div style={{ color: "blue", marginBottom: 4, fontWeight: "normal" }}>{pageStats}</div>}
      {jsonError && <div style={{ color: "red", marginBottom: 4, fontWeight: "bold" }}>{jsonError}</div>}
      {jsonFieldError && (
        <div style={{ color: "#d4380d", marginBottom: 4, fontWeight: "bold" }}>
          {jsonFieldError.split("\n").map((line, index) => (
            <div key={index}>{line}</div>
          ))}
        </div>
      )}
      {item.showSubmit && (
        <Form
          onFinish={() => {
            if (item.allowsubmit && item._value && !item.annotation.isReadOnly()) {
              item.addText(item._value);
              item.setValue("");
            }

            return false;
          }}
        >
          <Form.Item style={itemStyle}>
            <Tabs
              activeKey={activeTab}
              onChange={setActiveTab}
              size="small"
              items={[
                {
                  key: "kv",
                  label: "KV",
                  children: (
                    <div
                      style={{
                        maxHeight: "610px",
                        overflowY: "auto",
                        border: "1px solid #d9d9d9",
                        borderRadius: 4,
                        padding: 10,
                        background: item.isReadOnly() ? "#f5f5f5" : "white",
                      }}
                    >
                      {(() => {
                        const jsonArray = parseJsonForKV();
                        if (jsonArray.length === 0) {
                          return (
                            <div style={{ color: "#999", textAlign: "center", padding: "20px" }}>
                              暂无数据
                            </div>
                          );
                        }
                        
                        return jsonArray.map((itemData, arrayIndex) => {
                          // 使用统一的必填字段获取函数
                          const docType = itemData.docType;
                          const fieldsToCheck = getRequiredFieldsForDocument(docType, requiredFields, allConfigs);
                          
                          // 创建一个包含所有必填字段的完整对象
                          const completeItemData = { ...itemData };
                          
                          // 确保所有必填字段都存在，如果缺失则添加空值
                          fieldsToCheck.forEach(field => {
                            if (!Object.hasOwn(completeItemData, field)) {
                              completeItemData[field] = "";
                            }
                          });
                          
                          // 创建字段排序：序号在最前，其他必填字段按配置顺序，然后是非必填字段
                          const sortedKeys = [];
                          
                          // 1. 先添加序号字段（如果存在）
                          if (Object.hasOwn(completeItemData, "序号")) {
                            sortedKeys.push("序号");
                          }
                          
                          // 2. 按配置顺序添加其他必填字段
                          fieldsToCheck.forEach(field => {
                            if (field !== "序号" && Object.hasOwn(completeItemData, field)) {
                              sortedKeys.push(field);
                            }
                          });
                          
                          // 3. 添加剩余的非必填字段
                          Object.keys(completeItemData).forEach(key => {
                            if (!sortedKeys.includes(key)) {
                              sortedKeys.push(key);
                            }
                          });
                          
                          return (
                            <div key={arrayIndex}>
                              <div style={{ 
                                marginBottom: arrayIndex === jsonArray.length - 1 ? 0 : 10, 
                                paddingBottom: arrayIndex === jsonArray.length - 1 ? 0 : 10,
                                borderBottom: arrayIndex === jsonArray.length - 1 ? "none" : "1px dashed #d9d9d9"
                              }}>
                                {sortedKeys.map((key) => {
                                
                                const value = completeItemData[key];
                                const displayValue = typeof value === "object" ? JSON.stringify(value) : String(value || "");
                                
                                // 序号字段特殊处理：直接显示为标签
                                if (key === "序号") {
                                  return (
                                    <div key={key} style={{ 
                                      marginBottom: 4,
                                      color: "#1890ff",
                                      fontWeight: "bold",
                                      fontSize: 13
                                    }}>
                                      序号：{displayValue}
                                    </div>
                                  );
                                }
                                
                                // 检查是否为必填字段（使用之前计算的fieldsToCheck）
                                const isRequired = fieldsToCheck.includes(key);
                                // 检查是否为缺失的必填字段
                                const isMissingRequired = isRequired && (!Object.hasOwn(itemData, key) || !itemData[key]);
                                
                                return (
                                  <div key={key} style={{ 
                                    marginBottom: 8, 
                                    display: "grid", 
                                    gridTemplateColumns: "115px 1fr",
                                    gap: "8px",
                                    alignItems: "start"
                                  }}>
                                    <div 
                                      style={{ 
                                        fontWeight: "500", 
                                        color: isMissingRequired ? "#d4380d" : "#666",
                                        paddingTop: 4,
                                        wordBreak: "break-word",
                                        lineHeight: "1.3",
                                        hyphens: "auto",
                                        fontSize: 13,
                                        cursor: "pointer",
                                        position: "relative",
                                        display: "flex",
                                        alignItems: "center",
                                        gap: "4px"
                                      }}
                                      onClick={() => handleFieldAnnotationClick(arrayIndex, key)}
                                    >
                                      <span>{key}:</span>
                                      {hasFieldAnnotation(arrayIndex, key) && (
                                        <CommentOutlined 
                                          style={{ 
                                            color: "#1890ff", 
                                            fontSize: "12px" 
                                          }} 
                                        />
                                      )}
                                    </div>
                                    <div>
                                      <Input.TextArea
                                        value={displayValue}
                                        onChange={(e) => {
                                          if (!item.isReadOnly()) {
                                            let newValue = e.target.value;
                                            // 尝试解析JSON字符串
                                            try {
                                              if (newValue.startsWith("{") || newValue.startsWith("[")) {
                                                newValue = JSON.parse(newValue);
                                              }
                                            } catch (error) {
                                              // 如果不是有效JSON，保持字符串
                                            }
                                            handleKVValueChange(arrayIndex, key, newValue);
                                          }
                                        }}
                                        disabled={item.isReadOnly()}
                                        autoSize={{ minRows: 1, maxRows: 6 }}
                                        style={{ 
                                          fontSize: 12,
                                          ...(isRequired ? { 
                                            backgroundColor: "#fff2e8"
                                          } : {})
                                        }}
                                        placeholder={isMissingRequired ? `Missing field: ${key}` : undefined}
                                      />
                                    </div>
                                  </div>
                                );
                              })}
                              </div>
                            </div>
                          );
                        });
                      })()}
                    </div>
                  ),
                },
                {
                  key: "json",
                  label: "JSON",
                  children: (
                    <div
                      style={{
                        maxHeight: "610px",
                        overflowY: "auto",
                        border: "1px solid #d9d9d9",
                        borderRadius: 4,
                      }}
                    >
                      <ReactSimpleCodeEditor
                        value={item._value}
                        onValueChange={(value) => {
                          if (!item.annotation.isReadOnly()) {
                            item.setValue(value);
                            validateJsonAndFields(value);
                          }
                        }}
                        highlight={(code) => highlightWithDynamicRequiredFields(code, allConfigs, requiredFields)}
                        padding={10}
                        style={{
                          fontFamily: "monospace",
                          fontSize: 14,
                          minHeight: rows > 1 ? rows * 22 : 22,
                          background: item.isReadOnly() ? "#f5f5f5" : "white",
                          outline: "none",
                          width: "100%",
                          border: "none",
                          ...itemStyle,
                        }}
                        readOnly={item.isReadOnly()}
                        aria-label="TextArea Input"
                        placeholder={item.placeholder}
                      />
                    </div>
                  ),
                },
              ]}
            />
            {showAddButton && (
              <Button style={{ marginTop: "10px" }} type="primary" htmlType="submit">
                Add
              </Button>
            )}
          </Form.Item>
        </Form>
      )}

      {Tree.renderChildren(item, item.annotation)}

      {item.regions.length > 0 && (
        <div style={{ marginBottom: "1em" }}>
          {item.regions.map((t) => (
            <HtxTextAreaRegion key={t.id} item={t} onFocus={onFocus} />
          ))}
        </div>
      )}

      {/* 字段备注弹出框 */}
      <Modal
        title="字段备注"
        open={fieldAnnotationsModalVisible}
        onOk={handleSaveFieldAnnotation}
        onCancel={() => {
          setFieldAnnotationsModalVisible(false);
          setCurrentFieldKey(null);
          setCurrentFieldAnnotation({ errorTypes: [], reason: "" });
        }}
        okText="保存"
        cancelText="取消"
        width={600}
      >
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontWeight: "500" }}>错误类型（可多选）：</div>
          <div style={{ display: "flex", flexWrap: "wrap", gap: "8px" }}>
            {ERROR_TYPES.map(type => (
              <Tag.CheckableTag
                key={type}
                checked={currentFieldAnnotation.errorTypes.includes(type)}
                onChange={(checked) => {
                  if (checked) {
                    setCurrentFieldAnnotation(prev => ({
                      ...prev,
                      errorTypes: [...prev.errorTypes, type]
                    }));
                  } else {
                    setCurrentFieldAnnotation(prev => ({
                      ...prev,
                      errorTypes: prev.errorTypes.filter(t => t !== type)
                    }));
                  }
                }}
                style={{
                  borderRadius: "4px",
                  padding: "4px 8px"
                }}
              >
                {type}
              </Tag.CheckableTag>
            ))}
          </div>
        </div>
        
        <div>
          <div style={{ marginBottom: 8, fontWeight: "500" }}>具体原因：</div>
          <Input.TextArea
            value={currentFieldAnnotation.reason}
            onChange={(e) => {
              setCurrentFieldAnnotation(prev => ({
                ...prev,
                reason: e.target.value
              }));
            }}
            placeholder="请输入具体原因..."
            rows={4}
          />
        </div>
      </Modal>
    </div>
  ) : null;
});

Registry.addTag("textarea", TextAreaModel, HtxTextArea);

export { TextAreaModel, HtxTextArea };


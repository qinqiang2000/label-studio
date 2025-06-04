import { createRef, useCallback, useState, useEffect } from "react";
import Button from "antd/lib/button/index";
import Form from "antd/lib/form/index";
import Input from "antd/lib/input/index";
import { observer } from "mobx-react";
import { destroy, isAlive, types } from "mobx-state-tree";
import ReactSimpleCodeEditor from "react-simple-code-editor";
import Prism from "prismjs";
import "prismjs/components/prism-json";
import "prismjs/themes/prism.css";
import Tooltip from "antd/lib/tooltip";
import { InfoCircleOutlined } from "@ant-design/icons";

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

// 票据类型配置
const DOC_TYPES = {
  RECEIPT: "receipt",
  INVOICE: "invoice",
};

const VALID_DOC_TYPES = Object.values(DOC_TYPES);

// 必填字段列表
const REQUIRED_FIELDS = [
  "序号",
  "docType",
  "totalAmount",
  "totalTaxAmount",
  "invoiceNumber",
  "billToName",
  "invoiceDate",
  "currency",
];
// 高亮函数：高亮必填字段
function highlightWithRequiredFields(code) {
  let html = Prism.highlight(code, Prism.languages.json, "json");
  REQUIRED_FIELDS.forEach((field) => {
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
  .actions(() => (isFF(FF_LEAD_TIME) ? {} : { countTime: () => {} }))
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
  const onFocus = useCallback(
    (ev, model) => {
      item.setLastFocusedElement(ev.target, model);
    },
    [item],
  );

  // 新增：自动填充按钮逻辑
  const [autoFillLoading, setAutoFillLoading] = useState(false);
  // 仅当当前值为空且 name 包含 json 时显示按钮
  const showAutoFill =
    !item._value &&
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
      if (filled) {
        console.log('[AutoFill] 自动填充成功');
      }
    } finally {
      setAutoFillLoading(false);
    }
  };

  // 新增：labelstream/Label All Tasks模式下自动触发自动填充
  useEffect(() => {
    // 关键节点日志：自动填充触发
    if (showAutoFill) {
      console.log('[AutoFill] 自动填充触发');
    }
    if (showAutoFill) {
      handleAutoFill();
    }
  }, [showAutoFill]);

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

              for (let i = 0; i < parsed.length; i++) {
                const x = parsed[i];
                const missing = [];

                // 获取页码，默认为第1页
                const pages = x.page && Array.isArray(x.page) ? x.page : [1];

                // 只统计有效的票据类型
                if (!VALID_DOC_TYPES.includes(x.docType?.toLowerCase())) {
                  continue; // 跳过无效票据类型
                }

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

                // 字段验证逻辑保持不变
                if (!x.hasOwnProperty("docType")) {
                  missing.push("docType");
                }
                if (x.docType?.toLowerCase() === DOC_TYPES.INVOICE) {
                  // 'invoice'
                  ["billToName", "totalAmount", "totalTaxAmount", "invoiceNumber", "invoiceDate", "currency"].forEach(
                    (f) => {
                      if (!x.hasOwnProperty(f)) missing.push(f);
                    },
                  );
                } else if (x.docType?.toLowerCase() === DOC_TYPES.RECEIPT) {
                  // 'receipt'
                  ["totalAmount", "invoiceDate", "currency"].forEach((f) => {
                    if (!x.hasOwnProperty(f)) missing.push(f);
                  });
                }
                if (missing.length > 0) {
                  hasFieldErrors = true;
                  const docTypeText = x.docType?.toLowerCase() === DOC_TYPES.INVOICE ? "发票" : 
                                     x.docType?.toLowerCase() === DOC_TYPES.RECEIPT ? "收据" : "";
                  allErrorMessages.push(`${docTypeText}[${i + 1}]缺: ${missing.map((m) => `"${m}"`).join(", ")}`);
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
                  setJsonFieldError(allErrorMessages.join("\n"));
                } else {
                  setJsonFieldError(`${allErrorMessages.slice(0, 3).join("\n")}\n...等共${allErrorMessages.length}票，缺核心字段`);
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
    [item.name],
  );

  // 监听item._value和item.name，自动校验
  useEffect(() => {
    validateJsonAndFields(item._value);
  }, [item._value, item.name, validateJsonAndFields]);

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

  return item.displaymode === PER_REGION_MODES.TAG ? (
    <div className={textareaClassName} style={visibleStyle} ref={item.elementRef}>
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
        <div style={{ color: "green", marginBottom: 4, fontWeight: "normal" }}>
          {jsonFieldError.split("\n").map((line, index) => (
            <div key={index}>{line}</div>
          ))}
        </div>
      )}
      {Tree.renderChildren(item, item.annotation)}

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
                highlight={highlightWithRequiredFields}
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
            {showAddButton && (
              <Button style={{ marginTop: "10px" }} type="primary" htmlType="submit">
                Add
              </Button>
            )}
          </Form.Item>
        </Form>
      )}

      {item.regions.length > 0 && (
        <div style={{ marginBottom: "1em" }}>
          {item.regions.map((t) => (
            <HtxTextAreaRegion key={t.id} item={t} onFocus={onFocus} />
          ))}
        </div>
      )}
    </div>
  ) : null;
});

Registry.addTag("textarea", TextAreaModel, HtxTextArea);

export { TextAreaModel, HtxTextArea };

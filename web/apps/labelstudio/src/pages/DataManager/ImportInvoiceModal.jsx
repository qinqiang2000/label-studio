import { useRef, useState, useEffect } from "react";
import { Modal } from "../../components/Modal/Modal";
import { Button } from "../../components/Button/Button";
import { useAPI } from "../../providers/ApiProvider";

// 前端计算文件hash
async function calculateFileHash(file) {
  try {
    // 尝试使用Web Crypto API
    const arrayBuffer = await file.arrayBuffer();
    const hashBuffer = await crypto.subtle.digest("SHA-256", arrayBuffer);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    const hashHex = hashArray.map((b) => b.toString(16).padStart(2, "0")).join("");
    return hashHex.substring(0, 8); // 取前8位
  } catch (error) {
    console.error("计算文件哈希出错:", error);
    // 备用方法：使用文件名和大小生成简单哈希
    const timestamp = Date.now().toString();
    const fileInfo = `${file.name}-${file.size}-${timestamp}`;
    let hash = 0;
    for (let i = 0; i < fileInfo.length; i++) {
      hash = (hash << 5) - hash + fileInfo.charCodeAt(i);
      hash |= 0; // 转换为32位整数
    }
    return Math.abs(hash % 100000000)
      .toString(16)
      .padStart(8, "0");
  }
}

function getFileTag(projectId, hashFilename) {
  const ext = hashFilename.split(".").pop().toLowerCase();
  const style = "display:block; margin-left:auto; margin-right:0; width:100%; height:811px;";

  // 对hash文件名进行URL编码，处理特殊字符如 #, ?, &, % 等
  const encodedHashFilename = encodeURIComponent(hashFilename);

  if (["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp"].includes(ext)) {
    return `<img src='/data/local-files/?d=${projectId}/${encodedHashFilename}' style='${style}'/>`;
  } else if (["pdf"].includes(ext)) {
    return `<embed src='/data/local-files/?d=${projectId}/${encodedHashFilename}' width='100%' height='811px'/>`;
  }
  return hashFilename;
}

function extractDataFieldFromLabelConfig(labelConfig) {
  const parser = new DOMParser();
  const xml = parser.parseFromString(labelConfig, "application/xml");

  // 查找所有带有value属性的元素（与后端extract_data_types函数逻辑一致）
  const elementsWithValue = xml.querySelectorAll("*[value]");

  const dataTypes = {};

  for (const match of elementsWithValue) {
    if (!match.getAttribute("name")) {
      continue;
    }

    const value = match.getAttribute("value");

    // 检查是否以$开头的简单变量
    if (value && value.length > 1 && value.startsWith("$")) {
      const fieldName = value.substring(1);
      dataTypes[fieldName] = match.tagName;
    } else if (value) {
      // 处理包含$变量的复杂表达式（如正则表达式）
      const pattern = /\$(\w+)/g;
      let regexMatch;
      while ((regexMatch = pattern.exec(value)) !== null) {
        const fieldName = regexMatch[1];
        dataTypes[fieldName] = match.tagName;
      }
    }
  }

  return dataTypes;
}

// 新增函数：解析label config中的textarea配置
function extractTextAreaConfig(labelConfig) {
  const parser = new DOMParser();
  const xml = parser.parseFromString(labelConfig, "application/xml");

  // 查找所有textarea元素
  const textareas = xml.querySelectorAll("TextArea");

  const textareaConfigs = [];

  for (const textarea of textareas) {
    const name = textarea.getAttribute("name");
    const toName = textarea.getAttribute("toName");

    if (name && toName) {
      textareaConfigs.push({
        from_name: name,
        to_name: toName,
        type: "textarea",
      });
    }
  }

  return textareaConfigs;
}

function generateTaskDataWithAllFields(dataTypes, fileUrl, fileName) {
  // 创建包含所有字段的数据对象
  const taskData = {};

  // 为所有检测到的字段设置默认值
  Object.keys(dataTypes).forEach((fieldName) => {
    taskData[fieldName] = ""; // 默认空字符串
  });

  // 查找主要的显示字段（通常是第一个字段，用于显示文件内容）
  const fieldNames = Object.keys(dataTypes);
  const primaryField = fieldNames.length > 0 ? fieldNames[0] : "pdf";

  // 设置文件URL到主要字段
  taskData[primaryField] = fileUrl;

  // 如果有filename字段，设置实际文件名
  if (dataTypes.hasOwnProperty("filename")) {
    taskData.filename = fileName;
  }

  return taskData;
}

export const ImportInvoiceModal = ({ project, onClose, dataManager }) => {
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);
  const [countdown, setCountdown] = useState(5); // 添加倒计时状态
  const [exportingJson, setExportingJson] = useState(false); // 导出JSON状态
  const fileInputRef = useRef();
  const annotationFileInputRef = useRef(); // 标注文件输入引用
  const timeoutRef = useRef(); // 用于清理定时器
  const countdownIntervalRef = useRef(); // 用于清理倒计时
  const isMountedRef = useRef(true); // 跟踪组件挂载状态
  const api = useAPI(); // 添加API钩子

  // 暂停自动点击文件选择按钮功能
  // useEffect(() => {
  //   if (fileInputRef.current) {
  //     setTimeout(() => {
  //       fileInputRef.current.click();
  //     }, 100);
  //   }
  // }, []);

  // 组件卸载时清理
  useEffect(() => {
    return () => {
      isMountedRef.current = false;
      if (timeoutRef.current) {
        clearTimeout(timeoutRef.current);
      }
      if (countdownIntervalRef.current) {
        clearInterval(countdownIntervalRef.current);
      }
    };
  }, []);

  const handleUpload = async (e) => {
    setError(null);
    setSuccess(null);
    setUploading(true);
    try {
      const files = Array.from(e.target.files);

      // 验证文件类型
      const allowedExtensions = ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "pdf"];
      const invalidFiles = files.filter((file) => {
        const ext = file.name.split(".").pop().toLowerCase();
        return !allowedExtensions.includes(ext);
      });

      if (invalidFiles.length > 0) {
        const invalidNames = invalidFiles.map((f) => f.name).join(", ");
        throw new Error(`不支持的文件类型: ${invalidNames}。只支持图片文件（jpg/png/gif/svg/webp等）和PDF文件。`);
      }

      // 计算文件hash并生成hash文件名
      const fileHashData = [];
      for (const file of files) {
        const hash = await calculateFileHash(file);
        const ext = file.name.split(".").pop();
        const hashFilename = `${hash}.${ext}`;
        fileHashData.push({
          originalFile: file,
          originalName: file.name,
          hashFilename: hashFilename,
          hash: hash,
        });
      }

      // 1. 上传到本地API
      const formData = new FormData();
      fileHashData.forEach((data, index) => {
        // 创建新的File对象，使用hash文件名
        const hashFile = new File([data.originalFile], data.hashFilename, {
          type: data.originalFile.type,
        });
        formData.append(`file_${index}`, hashFile);
      });

      const res = await fetch(`/api/projects/${project.id}/local-upload/`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!res.ok) {
        const errorText = await res.text();
        console.error("📤 上传失败:", errorText);
        throw new Error(`Upload failed: ${res.status} ${errorText}`);
      }

      const uploadResult = await res.json();
      const { files: uploadedFiles } = uploadResult;

      // 2. 获取label_config并提取data字段名
      const projectRes = await fetch(`/api/projects/${project.id}`);

      if (!projectRes.ok) {
        throw new Error("获取项目配置失败");
      }

      const projectData = await projectRes.json();

      const labelConfig = projectData.label_config;
      const dataTypes = extractDataFieldFromLabelConfig(labelConfig);
      if (!dataTypes || Object.keys(dataTypes).length === 0) {
        throw new Error("无法自动识别label config中的数据字段");
      }

      // 2.5. 获取导入前的最大任务ID
      const tasksRes = await fetch(`/api/projects/${project.id}/tasks/?page_size=1&ordering=-id`);
      let maxExistingTaskId = 0;

      if (tasksRes.ok) {
        const tasksData = await tasksRes.json();

        // 处理两种可能的返回格式：数组或包含results的对象
        let tasks = [];
        if (Array.isArray(tasksData)) {
          tasks = tasksData;
        } else if (tasksData.results && Array.isArray(tasksData.results)) {
          tasks = tasksData.results;
        }

        if (tasks.length > 0) {
          maxExistingTaskId = tasks[0].id;
        }
      }

      // 3. 生成任务json
      const tasks = fileHashData.map((data) => {
        const fileUrl = getFileTag(project.id, data.hashFilename);
        return {
          data: generateTaskDataWithAllFields(dataTypes, fileUrl, data.originalName),
        };
      });

      // 4. 导入任务
      setImporting(true);

      const importRes = await fetch(`/api/projects/${project.id}/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(tasks),
      });

      if (!importRes.ok) {
        const errorText = await importRes.text();
        console.error("📥 导入失败:", errorText);
        throw new Error(`任务导入失败: ${importRes.status} ${errorText}`);
      }

      const importResult = await importRes.json();

      setImporting(false);
      setUploading(false);

      // 显示成功消息，包含具体任务ID
      const fileCount = tasks.length; // 使用实际生成的任务数量
      const fileWord = fileCount === 1 ? "个文件" : "个文件";

      let successMessage = `上传${fileCount}${fileWord}成功`;

      // 使用推算的任务ID
      if (importResult.task_count && importResult.task_count > 0) {
        const createdTaskCount = importResult.task_count;

        if (maxExistingTaskId > 0) {
          // 推算新创建的任务ID范围
          const startId = maxExistingTaskId + 1;
          const endId = maxExistingTaskId + createdTaskCount;

          if (createdTaskCount === 1) {
            successMessage += `，任务ID：${startId}`;
          } else {
            // 生成ID列表
            const taskIds = [];
            for (let i = startId; i <= endId; i++) {
              taskIds.push(i);
            }
            successMessage += `，任务ID：${taskIds.join(", ")}`;
          }
        } else {
          // 无法获取现有任务ID，使用备选显示
          successMessage += `，共创建${createdTaskCount}个任务`;
        }
      } else {
        // 原有的详细检测逻辑作为备选方案
        if (importResult.task_ids && Array.isArray(importResult.task_ids) && importResult.task_ids.length > 0) {
          const taskIds = importResult.task_ids.join(", ");
          successMessage += `，任务ID：${taskIds}`;
        } else if (importResult.tasks && Array.isArray(importResult.tasks) && importResult.tasks.length > 0) {
          const taskIds = importResult.tasks.map((task) => task.id).join(", ");
          successMessage += `，任务ID：${taskIds}`;
        } else if (importResult.id) {
          successMessage += `，任务ID：${importResult.id}`;
        } else {
          const possibleIdFields = ["task_id", "ids", "created_tasks", "new_tasks"];
          let foundIds = false;

          for (const field of possibleIdFields) {
            if (importResult[field]) {
              if (Array.isArray(importResult[field])) {
                const ids = importResult[field].join(", ");
                successMessage += `，任务ID：${ids}`;
                foundIds = true;
                break;
              } else {
                successMessage += `，任务ID：${importResult[field]}`;
                foundIds = true;
                break;
              }
            }
          }

          if (!foundIds && importResult.task_count) {
            successMessage += `，共创建${importResult.task_count}个任务`;
          }
        }
      }

      setSuccess(successMessage);

      // 启动倒计时
      setCountdown(5);
      countdownIntervalRef.current = setInterval(() => {
        setCountdown((prev) => {
          if (prev <= 1) {
            clearInterval(countdownIntervalRef.current);
            return 0;
          }
          return prev - 1;
        });
      }, 1000);

      // 5秒后自动关闭对话框并刷新
      timeoutRef.current = setTimeout(() => {
        // 检查组件是否还在挂载状态
        if (!isMountedRef.current) {
          return;
        }

        // 调用handleClose来处理关闭逻辑
        handleClose();
      }, 5000);
    } catch (err) {
      console.error("❌ 导入过程出错:", err);
      setError(err.message);
      setUploading(false);
      setImporting(false);
    }
  };

  // 导入标注数据功能
  const handleImportAnnotations = async () => {
    setError(null);
    setExportingJson(true);

    try {
      /* c
      onsole.log('🔄 开始获取项目JSON格式数据...'); 
      // 调用导出API获取JSON格式数据
      const response = await api.callApi("exportRaw", {
        params: {
          pk: project.id,
          exportType: "JSON",
          download_all_tasks: true,
        },
      });
      
      if (response && response.ok) {
        // 获取响应内容
        const jsonData = await response.text();
        console.log('📋 获取到的JSON数据:', jsonData);
        
        // 解析JSON数据
        let parsedData;
        try {
          parsedData = JSON.parse(jsonData);
          console.log('📋 解析后的JSON数据:', parsedData);
        } catch (parseError) {
          console.log('📋 JSON解析失败，原始数据:', jsonData);
          throw new Error('JSON数据解析失败');
        }
        */

      // 临时使用空数据进行调试
      const parsedData = [];
      console.log("📋 使用临时空数据进行调试:", parsedData);

      setExportingJson(false);

      // 创建文件输入元素让用户选择Excel文件
      const fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.accept = ".xlsx,.xls";
      fileInput.onchange = async (event) => {
        const file = event.target.files[0];
        if (file) {
          await processExcelFile(file, parsedData);
        }
      };
      fileInput.click();

      /*
      } else {
        throw new Error('获取项目数据失败');
      }
      */
    } catch (err) {
      console.error("❌ 获取项目数据出错:", err);
      setError(err.message || "获取项目数据失败");
      setExportingJson(false);
    }
  };

  // 处理Excel文件
  const processExcelFile = async (file, projectData) => {
    setImporting(true);
    setError(null);

    try {
      // 动态导入xlsx库
      const XLSX = await import("xlsx");

      // 读取Excel文件
      const arrayBuffer = await file.arrayBuffer();
      const workbook = XLSX.read(arrayBuffer, { type: "array" });

      // 查找Annotations sheet
      const annotationsSheetName = "Annotations";
      if (!workbook.SheetNames.includes(annotationsSheetName)) {
        throw new Error('Excel文件中未找到"Annotations"工作表');
      }

      const worksheet = workbook.Sheets[annotationsSheetName];
      const jsonData = XLSX.utils.sheet_to_json(worksheet);

      // 组装标注数据
      const annotationsByTask = {};

      jsonData.forEach((row) => {
        const taskId = row.id;
        if (!taskId) return;

        // 提取page及以后的字段
        const annotationData = {};
        const fields = [
          "page",
          "docType",
          "invoiceType",
          "nameOfInvoice",
          "invoiceNumber",
          "invoiceCode",
          "originalInvoiceNumber",
          "invoiceDate",
          "originalInvoiceDate",
          "totalNetAmount",
          "totalAmount",
          "totalTaxAmount",
          "currency",
          "billToName",
          "billToComposite",
          "billToCountry",
          "billToTaxIdentificationNumber",
          "shipFromComposite",
          "billFromName",
          "billFromComposite",
          "billFromCountry",
          "billFromTaxIdentificationNumber",
          "purchaseOrderNumber",
          "shipmentNumber",
          "dueDate",
          "paymentDueInDays",
          "detailOfGoodsOrServices",
          "detailOfTaxSummary",
        ];

        fields.forEach((field) => {
          if (row[field] !== undefined && row[field] !== null && row[field] !== "") {
            if (field === "page") {
              // Handle page field specially - convert to array of numbers
              let pageValue = row[field];
              if (typeof pageValue === "string") {
                pageValue = JSON.parse(pageValue);
              }
              annotationData[field] = Array.isArray(pageValue) ? pageValue : [Number(pageValue)];
            } else if (["detailOfGoodsOrServices", "detailOfTaxSummary"].includes(field)) {
              // These fields should always be arrays
              annotationData[field] = Array.isArray(row[field]) ? row[field] : [];
            } else {
              // All other fields stored as-is
              annotationData[field] = row[field];
            }
          }
        });

        if (!annotationsByTask[taskId]) {
          annotationsByTask[taskId] = [];
        }
        annotationsByTask[taskId].push(annotationData);
      });

      // 发送标注数据到后端
      let successCount = 0;
      let errorCount = 0;

      // 获取项目的label config并解析textarea配置
      const labelConfig = project.label_config;
      const textareaConfigs = extractTextAreaConfig(labelConfig);

      // 如果没有找到textarea配置，使用默认值
      const defaultTextareaConfig = {
        from_name: "invoices_json",
        to_name: "pdf",
        type: "textarea",
      };

      // 使用第一个找到的textarea配置，如果没有则使用默认配置
      const textareaConfig = textareaConfigs.length > 0 ? textareaConfigs[0] : defaultTextareaConfig;

      for (const [taskId, annotations] of Object.entries(annotationsByTask)) {
        try {
          // 将标注数据转换为正确的格式，使用动态解析的配置
          const annotationResult = [
            {
              value: {
                text: [JSON.stringify(annotations)],
              },
              from_name: textareaConfig.from_name,
              to_name: textareaConfig.to_name,
              type: textareaConfig.type,
            },
          ];

          // 调用API发送标注数据
          const response = await dataManager.apiCall(
            "submitAnnotation",
            {
              taskID: taskId,
            },
            {
              result: annotationResult,
              was_cancelled: false,
              ground_truth: false,
            },
          );

          if (response && !response.error) {
            successCount++;
          } else {
            errorCount++;
            console.error(`❌ 任务 ${taskId} 标注数据提交失败:`, response?.error);
          }
        } catch (err) {
          errorCount++;
          console.error(`❌ 任务 ${taskId} 标注数据提交出错:`, err);
        }
      }

      setImporting(false);

      if (successCount > 0) {
        setSuccess(`成功导入 ${successCount} 个任务的标注数据${errorCount > 0 ? `，${errorCount} 个失败` : ""}`);
        setCountdown(5);

        // 启动倒计时
        countdownIntervalRef.current = setInterval(() => {
          setCountdown((prev) => {
            if (prev <= 1) {
              clearInterval(countdownIntervalRef.current);
              return 0;
            }
            return prev - 1;
          });
        }, 1000);

        // 5秒后自动关闭对话框并刷新页面
        timeoutRef.current = setTimeout(() => {
          // 使用handleClose函数来确保页面刷新
          if (isMountedRef.current) {
            handleClose();
          }
        }, 5000);
      } else {
        setError("所有标注数据导入失败");
      }
    } catch (err) {
      console.error("❌ 处理Excel文件出错:", err);
      setError(err.message || "Excel文件处理失败");
      setImporting(false);
    }
  };

  // 新增 handleClose，统一关闭逻辑
  const handleClose = () => {
    // 无论是否有success，都刷新页面
    // 使用一个标志来防止重复刷新
    const needsRefresh = success || countdown > 0;

    // 先关闭对话框
    onClose();

    // 如果需要刷新，则在短暂延迟后刷新页面
    if (needsRefresh) {
      setTimeout(() => {
        window.location.reload();
      }, 100);
    }
  };

  return (
    <Modal
      title="Import Invoice Data"
      visible
      onHide={handleClose}
      closeOnClickOutside
      bare
      style={{ minWidth: 500, maxWidth: 600 }}
    >
      <Modal.Header divided>
        <span>Import Invoice Data</span>
        <Button onClick={handleClose}>Close</Button>
      </Modal.Header>
      <div style={{ padding: 24 }}>
        <input
          type="file"
          multiple
          accept=".jpg,.jpeg,.png,.gif,.bmp,.svg,.webp,.pdf,image/*,application/pdf"
          ref={fileInputRef}
          style={{ display: "none" }}
          onChange={handleUpload}
        />

        <input
          type="file"
          accept=".xlsx,.xls,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet,application/vnd.ms-excel"
          ref={annotationFileInputRef}
          style={{ display: "none" }}
          onChange={() => {}} // 暂时空实现
        />

        {success ? (
          <div
            style={{
              padding: 16,
              backgroundColor: "#f0f8ff",
              border: "1px solid #4CAF50",
              borderRadius: 4,
              color: "#4CAF50",
              marginBottom: 16,
              textAlign: "center",
            }}
          >
            <div style={{ fontSize: 16, marginBottom: 8 }}>✅ {success}</div>
            <div style={{ fontSize: 14, color: "#666", marginBottom: 8 }}>
              💡 提示：如需查看最新导入的任务，请按ID倒序排序
            </div>
            <div style={{ fontSize: 14, color: "#999" }}>
              {countdown > 0 ? `${countdown}秒后自动刷新页面` : "正在刷新..."}
            </div>
          </div>
        ) : (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            <Button look="primary" onClick={() => fileInputRef.current.click()} waiting={uploading || importing}>
              导入票据
            </Button>

            <div style={{ fontSize: 12, color: "#888", textAlign: "center" }}>
              支持图片和PDF文件的导入。导入后会自动生成任务。
            </div>

            <Button look="secondary" onClick={handleImportAnnotations} waiting={exportingJson}>
              导入人工标注
            </Button>

            <div style={{ fontSize: 12, color: "#888", textAlign: "center" }}>
              导入已标注的Excel文件。模版可从Export功能获取。
            </div>
          </div>
        )}

        {error && <div style={{ color: "red", marginTop: 8 }}>{error}</div>}
      </div>
    </Modal>
  );
};

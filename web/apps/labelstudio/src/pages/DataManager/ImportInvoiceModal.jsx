import React, { useRef, useState, useEffect } from "react";
import { Modal } from "../../components/Modal/Modal";
import { Button } from "../../components/Button/Button";

// 前端计算文件hash
async function calculateFileHash(file) {
  const arrayBuffer = await file.arrayBuffer();
  const hashBuffer = await crypto.subtle.digest('SHA-256', arrayBuffer);
  const hashArray = Array.from(new Uint8Array(hashBuffer));
  const hashHex = hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  return hashHex.substring(0, 8); // 取前8位
}

function getFileTag(projectId, hashFilename) {
  const ext = hashFilename.split('.').pop().toLowerCase();
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
  console.log('🔍 原始 label config:', labelConfig);
  
  const parser = new DOMParser();
  const xml = parser.parseFromString(labelConfig, "application/xml");
  console.log('🔍 解析后的 XML:', xml);
  
  // 查找所有带有value属性的元素（与后端extract_data_types函数逻辑一致）
  const elementsWithValue = xml.querySelectorAll('*[value]');
  console.log('🔍 找到带有value属性的元素:', elementsWithValue);
  
  const dataTypes = {};
  
  for (let match of elementsWithValue) {
    if (!match.getAttribute('name')) {
      continue;
    }
    
    const value = match.getAttribute('value');
    console.log('🔍 处理元素:', match.tagName, 'value:', value);
    
    // 检查是否以$开头的简单变量
    if (value && value.length > 1 && value.startsWith('$')) {
      const fieldName = value.substring(1);
      dataTypes[fieldName] = match.tagName;
      console.log('🔍 找到数据字段:', fieldName, '类型:', match.tagName);
    } else if (value) {
      // 处理包含$变量的复杂表达式（如正则表达式）
      const pattern = /\$(\w+)/g;
      let regexMatch;
      while ((regexMatch = pattern.exec(value)) !== null) {
        const fieldName = regexMatch[1];
        dataTypes[fieldName] = match.tagName;
        console.log('🔍 从表达式中找到数据字段:', fieldName, '类型:', match.tagName);
      }
    }
  }
  
  console.log('🔍 所有数据字段:', dataTypes);
  return dataTypes;
}

function generateTaskDataWithAllFields(dataTypes, fileUrl, fileName) {
  console.log('📋 生成任务数据，所有字段:', dataTypes);
  
  // 创建包含所有字段的数据对象
  const taskData = {};
  
  // 为所有检测到的字段设置默认值
  Object.keys(dataTypes).forEach(fieldName => {
    taskData[fieldName] = ""; // 默认空字符串
  });
  
  // 查找主要的显示字段（通常是第一个字段，用于显示文件内容）
  const fieldNames = Object.keys(dataTypes);
  const primaryField = fieldNames.length > 0 ? fieldNames[0] : 'pdf';
  
  // 设置文件URL到主要字段
  taskData[primaryField] = fileUrl;
  
  // 如果有filename字段，设置实际文件名
  if (dataTypes.hasOwnProperty('filename')) {
    taskData.filename = fileName;
  }
  
  console.log('📋 生成的任务数据:', taskData);
  return taskData;
}

export const ImportInvoiceModal = ({ project, onClose, dataManager }) => {
  const [uploading, setUploading] = useState(false);
  const [importing, setImporting] = useState(false);
  const [success, setSuccess] = useState(null);
  const [error, setError] = useState(null);
  const [countdown, setCountdown] = useState(5); // 添加倒计时状态
  const fileInputRef = useRef();
  const timeoutRef = useRef(); // 用于清理定时器
  const countdownIntervalRef = useRef(); // 用于清理倒计时
  const isMountedRef = useRef(true); // 跟踪组件挂载状态

  // 自动点击文件选择按钮
  useEffect(() => {
    if (fileInputRef.current) {
      setTimeout(() => {
        fileInputRef.current.click();
      }, 100);
    }
  }, []);

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
      console.log('📤 开始上传文件:', files);
      
      // 验证文件类型
      const allowedExtensions = ["jpg", "jpeg", "png", "gif", "bmp", "svg", "webp", "pdf"];
      const invalidFiles = files.filter(file => {
        const ext = file.name.split('.').pop().toLowerCase();
        return !allowedExtensions.includes(ext);
      });
      
      if (invalidFiles.length > 0) {
        const invalidNames = invalidFiles.map(f => f.name).join(', ');
        throw new Error(`不支持的文件类型: ${invalidNames}。只支持图片文件（jpg/png/gif/svg/webp等）和PDF文件。`);
      }
      
      // 计算文件hash并生成hash文件名
      console.log('🔢 开始计算文件hash...');
      const fileHashData = [];
      for (const file of files) {
        const hash = await calculateFileHash(file);
        const ext = file.name.split('.').pop();
        const hashFilename = `${hash}.${ext}`;
        fileHashData.push({
          originalFile: file,
          originalName: file.name,
          hashFilename: hashFilename,
          hash: hash
        });
        console.log('🔢 文件hash计算完成:', file.name, '->', hashFilename);
      }
      
      // 1. 上传到本地API
      const formData = new FormData();
      fileHashData.forEach((data, index) => {
        // 创建新的File对象，使用hash文件名
        const hashFile = new File([data.originalFile], data.hashFilename, {
          type: data.originalFile.type
        });
        formData.append(`file_${index}`, hashFile);
      });
      
      console.log('📤 发送上传请求到:', `/api/projects/${project.id}/local-upload/`);
      console.log('📤 上传文件数量:', fileHashData.length);
      
      const res = await fetch(`/api/projects/${project.id}/local-upload/`, {
        method: "POST",
        body: formData,
        credentials: "include",
      });
      
      console.log('📤 上传响应状态:', res.status);
      if (!res.ok) {
        const errorText = await res.text();
        console.error('📤 上传失败:', errorText);
        throw new Error(`Upload failed: ${res.status} ${errorText}`);
      }
      
      const uploadResult = await res.json();
      console.log('📤 上传结果:', uploadResult);
      const { files: uploadedFiles } = uploadResult;

      // 2. 获取label_config并提取data字段名
      console.log('🏷️ 获取项目配置...');
      const projectRes = await fetch(`/api/projects/${project.id}`);
      console.log('🏷️ 项目配置响应状态:', projectRes.status);
      
      if (!projectRes.ok) {
        throw new Error("获取项目配置失败");
      }
      
      const projectData = await projectRes.json();
      console.log('🏷️ 项目数据:', projectData);
      
      const labelConfig = projectData.label_config;
      const dataTypes = extractDataFieldFromLabelConfig(labelConfig);
      if (!dataTypes || Object.keys(dataTypes).length === 0) {
        throw new Error("无法自动识别label config中的数据字段");
      }

      // 2.5. 获取导入前的最大任务ID
      console.log('📊 获取当前任务列表...');
      const tasksRes = await fetch(`/api/projects/${project.id}/tasks/?page_size=1&ordering=-id`);
      let maxExistingTaskId = 0;
      
      if (tasksRes.ok) {
        const tasksData = await tasksRes.json();
        console.log('📊 任务数据响应:', tasksData);
        
        // 处理两种可能的返回格式：数组或包含results的对象
        let tasks = [];
        if (Array.isArray(tasksData)) {
          tasks = tasksData;
        } else if (tasksData.results && Array.isArray(tasksData.results)) {
          tasks = tasksData.results;
        }
        
        if (tasks.length > 0) {
          maxExistingTaskId = tasks[0].id;
          console.log('📊 当前最大任务ID:', maxExistingTaskId);
        } else {
          console.log('📊 没有找到任务结果');
        }
      } else {
        console.log('📊 无法获取任务列表，将使用备选方案');
      }

      // 3. 生成任务json
      const tasks = fileHashData.map((data) => {
        const fileUrl = getFileTag(project.id, data.hashFilename);
        return {
          data: generateTaskDataWithAllFields(dataTypes, fileUrl, data.originalName)
        };
      });
      
      console.log('📋 生成的任务:', tasks);

      // 4. 导入任务
      setImporting(true);
      console.log('📥 发送导入请求到:', `/api/projects/${project.id}/import`);
      
      const importRes = await fetch(`/api/projects/${project.id}/import`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify(tasks),
      });
      
      console.log('📥 导入响应状态:', importRes.status);
      if (!importRes.ok) {
        const errorText = await importRes.text();
        console.error('📥 导入失败:', errorText);
        throw new Error(`任务导入失败: ${importRes.status} ${errorText}`);
      }
      
      const importResult = await importRes.json();
      console.log('📥 导入结果:', importResult);
      console.log('📥 导入结果类型:', typeof importResult);
      console.log('📥 导入结果所有字段:', Object.keys(importResult));
      
      setImporting(false);
      setUploading(false);
      
      // 显示成功消息，包含具体任务ID
      const fileCount = tasks.length; // 使用实际生成的任务数量
      const fileWord = fileCount === 1 ? '个文件' : '个文件';
      
      let successMessage = `上传${fileCount}${fileWord}成功`;
      
      // 使用推算的任务ID
      if (importResult.task_count && importResult.task_count > 0) {
        const createdTaskCount = importResult.task_count;
        console.log('📊 准备生成任务ID，maxExistingTaskId:', maxExistingTaskId, 'createdTaskCount:', createdTaskCount);
        
        if (maxExistingTaskId > 0) {
          // 推算新创建的任务ID范围
          const startId = maxExistingTaskId + 1;
          const endId = maxExistingTaskId + createdTaskCount;
          
          console.log('📊 计算任务ID范围: startId =', startId, ', endId =', endId);
          
          if (createdTaskCount === 1) {
            successMessage += `，任务ID：${startId}`;
          } else {
            // 生成ID列表
            const taskIds = [];
            for (let i = startId; i <= endId; i++) {
              taskIds.push(i);
            }
            successMessage += `，任务ID：${taskIds.join(', ')}`;
          }
          
          console.log('📊 推算的新任务ID范围:', startId, '到', endId);
        } else {
          // 无法获取现有任务ID，使用备选显示
          console.log('📊 maxExistingTaskId <= 0，使用备选显示');
          successMessage += `，共创建${createdTaskCount}个任务`;
        }
      } else {
        // 原有的详细检测逻辑作为备选方案
        if (importResult.task_ids && Array.isArray(importResult.task_ids) && importResult.task_ids.length > 0) {
          const taskIds = importResult.task_ids.join(', ');
          successMessage += `，任务ID：${taskIds}`;
        } else if (importResult.tasks && Array.isArray(importResult.tasks) && importResult.tasks.length > 0) {
          const taskIds = importResult.tasks.map(task => task.id).join(', ');
          successMessage += `，任务ID：${taskIds}`;
        } else if (importResult.id) {
          successMessage += `，任务ID：${importResult.id}`;
        } else {
          console.log('📥 尝试从其他字段获取任务ID信息:', importResult);
          
          const possibleIdFields = ['task_id', 'ids', 'created_tasks', 'new_tasks'];
          let foundIds = false;
          
          for (const field of possibleIdFields) {
            if (importResult[field]) {
              if (Array.isArray(importResult[field])) {
                const ids = importResult[field].join(', ');
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
        setCountdown(prev => {
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
          console.log('🔄 组件已卸载，跳过刷新');
          return;
        }
        
        onClose();
        
        // 使用页面刷新避免mobx-state-tree状态错误
        // dm.reload() 会销毁状态树导致错误，所以改用页面刷新
        console.log('🔄 使用页面刷新更新任务列表');
        window.location.reload();
      }, 5000);
    } catch (err) {
      console.error('❌ 导入过程出错:', err);
      setError(err.message);
      setUploading(false);
      setImporting(false);
    }
  };

  // 新增 handleClose，统一关闭逻辑
  const handleClose = () => {
    if (success) {
      window.location.reload();
    } else {
      onClose();
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
        
        {success ? (
          <div style={{ 
            padding: 16, 
            backgroundColor: "#f0f8ff", 
            border: "1px solid #4CAF50",
            borderRadius: 4,
            color: "#4CAF50",
            marginBottom: 16,
            textAlign: "center"
          }}>
            <div style={{ fontSize: 16, marginBottom: 8 }}>
              ✅ {success}
            </div>
            <div style={{ fontSize: 14, color: "#666", marginBottom: 8 }}>
              💡 提示：如需查看最新导入的任务，请按ID倒序排序
            </div>
            <div style={{ fontSize: 14, color: "#999" }}>
              {countdown > 0 ? `${countdown}秒后自动刷新页面` : '正在刷新...'}
            </div>
          </div>
        ) : (
          <Button
            look="primary"
            onClick={() => fileInputRef.current.click()}
            waiting={uploading || importing}
          >
            选择文件上传
          </Button>
        )}
        
        {error && <div style={{ color: "red", marginTop: 8 }}>{error}</div>}
        
        {!success && (
          <div style={{ marginTop: 12, color: "#888" }}>
            支持图片（jpg/png/gif/svg/webp等）和PDF文件，文件将直接存储到本地项目目录并自动生成任务。
          </div>
        )}
      </div>
    </Modal>
  );
}; 
import React, { useCallback, useState, useEffect } from 'react';
import { Modal } from '../../Common/Modal/ModalPopup';
import { Button } from '../../Common/Button/Button';
import { Space } from '../../Common/Space/Space';
import { Block, Elem } from '../../../utils/bem';
import { Icon } from '../../Common/Icon/Icon';
import { IconCopy, IconFileDownload } from '@humansignal/icons';
import { Select } from '../../Common/Form';
import './EvaluationResultModal.scss';

// 智能内容渲染函数，支持Markdown、HTML和纯文本
const renderContent = (content) => {
  // 类型检查和默认值处理
  if (!content) return '';
  
  // 如果是对象，尝试提取文本内容
  if (typeof content === 'object') {
    if (content.analysis_result) {
      content = content.analysis_result;
    } else if (content.content || content.text || content.message) {
      content = content.content || content.text || content.message;
    } else {
      // 如果是其他对象，转为JSON字符串显示
      content = JSON.stringify(content, null, 2);
    }
  }
  
  // 确保是字符串
  if (typeof content !== 'string') {
    content = String(content);
  }
  
  // 检测并移除代码块包围符号
  const trimmedContent = content.trim();
  const codeBlockRegex = /^```(\w+)?\s*\n([\s\S]*?)\n```$/;
  const match = trimmedContent.match(codeBlockRegex);
  
  if (match) {
    const format = match[1]; // html, json, markdown 等
    const actualContent = match[2].trim();
    
    // 根据格式处理内容
    if (format === 'html') {
      return actualContent;
    } else if (format === 'json') {
      try {
        const jsonObj = JSON.parse(actualContent);
        // 如果JSON有特定字段，提取出来
        if (jsonObj.result || jsonObj.analysis_result || jsonObj.message) {
          return renderContent(jsonObj.result || jsonObj.analysis_result || jsonObj.message);
        }
        return `<pre><code>${JSON.stringify(jsonObj, null, 2)}</code></pre>`;
      } catch (e) {
        // JSON解析失败，当作普通文本处理
        content = actualContent;
      }
    } else {
      // 其他格式或无格式标识，移除包围符号后当作markdown处理
      content = actualContent;
    }
  }
  
  // 检测是否已经是HTML格式
  const hasHtmlTags = /<[^>]*>/g.test(content);
  if (hasHtmlTags) {
    // 如果已经包含HTML标签，直接返回
    return content;
  }
  
  // 否则按Markdown格式处理
  let html = content;
  
  try {
    // 处理标题
    html = html.replace(/^### (.*$)/gim, '<h3>$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2>$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1>$1</h1>');
    
    // 处理粗体
    html = html.replace(/\*\*(.*?)\*\*/gim, '<strong>$1</strong>');
    
    // 处理斜体
    html = html.replace(/\*(.*?)\*/gim, '<em>$1</em>');
    
    // 处理代码块
    html = html.replace(/```([\s\S]*?)```/gim, '<pre><code>$1</code></pre>');
    
    // 处理行内代码
    html = html.replace(/`(.*?)`/gim, '<code>$1</code>');
    
    // 处理列表
    html = html.replace(/^\* (.*$)/gim, '<li>$1</li>');
    html = html.replace(/^- (.*$)/gim, '<li>$1</li>');
    html = html.replace(/(\<li\>.*<\/li>)/gims, '<ul>$1</ul>');
    
    // 处理数字列表
    html = html.replace(/^\d+\. (.*$)/gim, '<li>$1</li>');
    
    // 处理换行
    html = html.replace(/\n/gim, '<br/>');
    
    // 清理多余的br标签
    html = html.replace(/<br\/><br\/><ul>/gim, '<ul>');
    html = html.replace(/<\/ul><br\/><br\/>/gim, '</ul>');
    html = html.replace(/<br\/><li>/gim, '<li>');
    html = html.replace(/<\/li><br\/>/gim, '</li>');
  } catch (error) {
    console.warn('Content rendering error:', error);
    // 如果处理失败，返回原始内容并添加换行处理
    html = content.replace(/\n/g, '<br/>');
  }
  
  return html;
};

// 下载分析报告为文档格式
const downloadAnalysisReport = (content, filename = 'analysis_report') => {
  // 创建一个包含完整HTML结构的内容
  const htmlContent = `
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>评估报告分析</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: #fff;
        }
        h1, h2, h3 {
            color: #2c3e50;
            margin-top: 30px;
            margin-bottom: 20px;
        }
        h1 { font-size: 28px; border-bottom: 3px solid #3498db; padding-bottom: 10px; }
        h2 { font-size: 24px; border-bottom: 2px solid #e74c3c; padding-bottom: 8px; }
        h3 { font-size: 20px; border-bottom: 1px solid #95a5a6; padding-bottom: 5px; }
        p { margin-bottom: 15px; }
        ul, ol {
            margin-bottom: 15px;
            padding-left: 30px;
        }
        li { margin-bottom: 8px; }
        strong { color: #2c3e50; }
        em { color: #7f8c8d; }
        code {
            background-color: #f8f9fa;
            padding: 2px 6px;
            border-radius: 3px;
            font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
            color: #e74c3c;
        }
        pre {
            background-color: #f8f9fa;
            padding: 15px;
            border-radius: 5px;
            overflow-x: auto;
            border-left: 4px solid #3498db;
        }
        pre code {
            background: none;
            padding: 0;
            color: #2c3e50;
        }
        .header {
            text-align: center;
            margin-bottom: 40px;
            border-bottom: 2px solid #ecf0f1;
            padding-bottom: 20px;
        }
        .timestamp {
            color: #7f8c8d;
            font-style: italic;
            margin-top: 10px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>Label Studio 评估报告分析</h1>
        <div class="timestamp">生成时间: ${new Date().toLocaleString('zh-CN')}</div>
    </div>
    <div class="content">
        ${renderContent(content)}
    </div>
</body>
</html>`;

  // 创建Blob对象
  const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' });
  
  // 创建下载链接
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `${filename}_${new Date().toISOString().split('T')[0]}.html`;
  
  // 触发下载
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  
  // 清理URL对象
  URL.revokeObjectURL(link.href);
};

const EvaluationResultModal = ({ result, onClose }) => {
  const [isAnalyzing, setIsAnalyzing] = useState(false);
  const [analysisResult, setAnalysisResult] = useState(null);
  const [analysisError, setAnalysisError] = useState(null);
  const [prompts, setPrompts] = useState([]);
  const [selectedPrompt, setSelectedPrompt] = useState('Default');
  
  if (!result || !result.evaluation_results) {
    return null;
  }

  const { evaluation_results, processed_items, detail, evaluation_type } = result;
  const { metrics = {}, task_count, evaluated_at, project_id } = evaluation_results;
  
  // 检查是否为票据提取评估
  const isInvoiceEvaluation = evaluation_type === 'document_extraction' || evaluation_type === 'invoice_extraction';

  // 加载prompts列表
  useEffect(() => {
    const loadPrompts = async () => {
      try {
        // 获取CSRF token
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                         document.querySelector('meta[name=csrf-token]')?.content ||
                         window.localStorage.getItem('token') ||
                         window.sessionStorage.getItem('token') ||
                         '';
        
        const headers = {
          'Content-Type': 'application/json',
        };
        
        // 添加认证头
        if (csrfToken) {
          if (csrfToken.length > 40) {
            headers['Authorization'] = `Token ${csrfToken}`;
          } else {
            headers['X-CSRFToken'] = csrfToken;
          }
        }
        
        const response = await fetch('/api/prompts/', {
          method: 'GET',
          headers,
        });

        if (response.ok) {
          const promptsData = await response.json();
          setPrompts(promptsData || []);
          
          // 恢复用户上次选择的prompt，如果没有则默认选择Default
          const savedPrompt = localStorage.getItem('evaluation_analysis_prompt');
          if (savedPrompt && (savedPrompt === 'Default' || promptsData.find(p => p.name === savedPrompt))) {
            setSelectedPrompt(savedPrompt);
          } else {
            // 如果没有保存的选择，默认选择Default
            setSelectedPrompt('Default');
          }
        } else {
          console.error('Failed to load prompts:', response.statusText);
        }
      } catch (error) {
        console.error('Error loading prompts:', error);
      }
    };

    loadPrompts();
  }, []);

  // 保存用户选择的prompt
  const handlePromptChange = useCallback((promptName) => {
    setSelectedPrompt(promptName);
    localStorage.setItem('evaluation_analysis_prompt', promptName);
  }, []);

  // 阻止Select组件的点击事件冒泡
  const handleSelectClick = useCallback((event) => {
    event.stopPropagation();
  }, []);

  // 下载Excel详情报告
  const downloadExcelReport = useCallback(() => {
    if (evaluation_results?.excel_path) {
      // 创建下载链接
      const link = document.createElement('a');
      link.href = `/api/download-excel?path=${encodeURIComponent(evaluation_results.excel_path)}`;
      link.download = `evaluation_report_${project_id}_${new Date().toISOString().split('T')[0]}.xlsx`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      
      // 显示成功消息
      if (window.LSF && window.LSF.datamanager) {
        window.LSF.datamanager.invoke('toast', { 
          message: '详情报告下载已开始', 
          type: 'info' 
        });
      }
    } else {
      // 显示错误消息
      if (window.LSF && window.LSF.datamanager) {
        window.LSF.datamanager.invoke('toast', { 
          message: '报告文件不可用', 
          type: 'error' 
        });
      }
    }
  }, [evaluation_results, project_id]);

  // 下载分析报告
  const downloadAnalysisReportCallback = useCallback(() => {
    if (!analysisResult) {
      if (window.LSF && window.LSF.datamanager) {
        window.LSF.datamanager.invoke('toast', { 
          message: '请先执行分析生成报告', 
          type: 'warning' 
        });
      }
      return;
    }

    try {
      downloadAnalysisReport(analysisResult, `evaluation_analysis_report_${project_id}`);
      
      if (window.LSF && window.LSF.datamanager) {
        window.LSF.datamanager.invoke('toast', { 
          message: '分析报告下载已开始', 
          type: 'success' 
        });
      }
    } catch (error) {
      console.error('Download analysis report error:', error);
      if (window.LSF && window.LSF.datamanager) {
        window.LSF.datamanager.invoke('toast', { 
          message: '分析报告下载失败', 
          type: 'error' 
        });
      }
    }
  }, [analysisResult, project_id]);

  // 分析评估报告
  const analyzeEvaluationReport = useCallback(async () => {
    if (!evaluation_results?.excel_path) {
      if (window.LSF && window.LSF.datamanager) {
        window.LSF.datamanager.invoke('toast', { 
          message: 'Excel文件路径不可用', 
          type: 'error' 
        });
      }
      return;
    }

    setIsAnalyzing(true);
    setAnalysisError(null); // 清除之前的错误
    try {
      // 获取CSRF token
      const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]')?.value ||
                       document.querySelector('meta[name=csrf-token]')?.content ||
                       window.localStorage.getItem('token') ||
                       window.sessionStorage.getItem('token') ||
                       '';
      
      const headers = {
        'Content-Type': 'application/json',
      };
      
      if (csrfToken) {
        headers['X-CSRFToken'] = csrfToken;
      }
      
      // 构建请求体
      const requestBody = {
        excel_path: evaluation_results.excel_path,
        params: {
          context: {
            evaluation_type: evaluation_type,
            description: '评估结果分析',
          },
          analysis_type: 'evaluation',
        },
      };
      
      // 根据选择的prompt名称找到对应的content并传递
      if (selectedPrompt && selectedPrompt !== 'Default') {
        const selectedPromptObj = prompts.find(p => p.name === selectedPrompt);
        if (selectedPromptObj && selectedPromptObj.content) {
          requestBody.params.prompt = selectedPromptObj.content;
        }
      }

      const response = await fetch(`/api/dm/analysis/?project=${project_id}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(requestBody),
      });

      if (response.ok) {
        const result = await response.json();
        
        if (result.status === 'success') {
          setAnalysisResult(result.analysis_result);
          setAnalysisError(null);
          
          if (window.LSF && window.LSF.datamanager) {
            window.LSF.datamanager.invoke('toast', { 
              message: '分析完成', 
              type: 'success' 
            });
          }
        } else {
          // 处理业务层面的错误
          const errorMsg = result.error || '分析失败';
          setAnalysisError(errorMsg);
          setAnalysisResult(null);
          
          if (window.LSF && window.LSF.datamanager) {
            window.LSF.datamanager.invoke('toast', { 
              message: `分析失败: ${errorMsg}`, 
              type: 'error' 
            });
          }
        }
      } else {
        // 处理HTTP错误
        let errorMsg = '网络请求失败';
        try {
          const errorData = await response.json();
          errorMsg = errorData.error || errorData.message || `HTTP ${response.status}`;
        } catch {
          errorMsg = `HTTP ${response.status} - ${response.statusText}`;
        }
        
        setAnalysisError(errorMsg);
        setAnalysisResult(null);
        
        if (window.LSF && window.LSF.datamanager) {
          window.LSF.datamanager.invoke('toast', { 
            message: `分析失败: ${errorMsg}`, 
            type: 'error' 
          });
        }
      }
    } catch (error) {
      // 处理网络异常或其他异常
      const errorMsg = error.message || '分析过程发生异常';
      setAnalysisError(errorMsg);
      setAnalysisResult(null);
      
      if (window.LSF && window.LSF.datamanager) {
        window.LSF.datamanager.invoke('toast', { 
          message: `分析异常: ${errorMsg}`, 
          type: 'error' 
        });
      }
    } finally {
      setIsAnalyzing(false);
    }
  }, [evaluation_results, evaluation_type, project_id, selectedPrompt, prompts]);

  const formatPercentage = (value) => {
    return (value * 100).toFixed(2) + '%';
  };

  const formatDate = (dateString) => {
    if (!dateString) return '';
    const date = new Date(dateString);
    const pad = n => n.toString().padStart(2, '0');
    return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())} ${pad(date.getHours())}:${pad(date.getMinutes())}`;
  };

  const getMetricColor = (value) => {
    if (value >= 0.8) return 'excellent';
    if (value >= 0.6) return 'good';
    if (value >= 0.4) return 'fair';
    return 'poor';
  };

  const MetricCard = ({ title, value }) => (
    <Block name="metric-card" mod={{ level: getMetricColor(value) }}>
      <Elem name="title">{title}</Elem>
      <Elem name="value">{formatPercentage(value)}</Elem>
      <Elem name="progress">
        <Elem name="progress-bar" style={{ width: formatPercentage(value) }} />
      </Elem>
    </Block>
  );

  const InvoiceMetricCard = ({ title, value, subtitle }) => (
    <Block name="invoice-metric-card" mod={{ level: getMetricColor(value) }}>
      <Elem name="title">{title}</Elem>
      <Elem name="value">{formatPercentage(value)}</Elem>
      {subtitle && <Elem name="subtitle">{subtitle}</Elem>}
      <Elem name="progress">
        <Elem name="progress-bar" style={{ width: formatPercentage(value) }} />
      </Elem>
    </Block>
  );

  const renderInvoiceMetrics = () => {
    if (!isInvoiceEvaluation) return null;
    
    const statistics = evaluation_results?.statistics || {};
    const {
      document_accuracy = 0,
      invoice_accuracy = 0,
      field_accuracy = {}
    } = statistics;

    return (
      <>
        {/* 整体指标 - 横向排列的卡片式布局 */}
        <Elem name="overall-metrics">
          <Elem name="section-title">整体指标</Elem>
          <Elem name="metrics-cards">
            <Elem name="metric-card">
              <Elem name="metric-value" mod={{ level: getMetricColor(document_accuracy / 100) }}>
                {document_accuracy.toFixed(2)}%
              </Elem>
              <Elem name="metric-label">文档准确率</Elem>
            </Elem>
            <Elem name="metric-card">
              <Elem name="metric-value" mod={{ level: getMetricColor(invoice_accuracy / 100) }}>
                {invoice_accuracy.toFixed(2)}%
              </Elem>
              <Elem name="metric-label">票据准确率</Elem>
            </Elem>
            <Elem name="metric-card">
              <Elem name="metric-value" mod={{ level: getMetricColor(Object.values(field_accuracy).reduce((sum, acc) => sum + acc, 0) / Object.keys(field_accuracy).length / 100) }}>
                {Object.keys(field_accuracy).length > 0 ? (Object.values(field_accuracy).reduce((sum, acc) => sum + acc, 0) / Object.keys(field_accuracy).length).toFixed(2) : '0.00'}%
              </Elem>
              <Elem name="metric-label">字段准确率</Elem>
            </Elem>
          </Elem>
        </Elem>
        
        {/* 核心字段指标列表 */}
        {field_accuracy && Object.keys(field_accuracy).length > 0 && (
          <Elem name="field-metrics">
            <Elem name="section-title">核心字段指标</Elem>
            <Elem name="field-list">
              <Elem name="field-header">
                <Elem name="header-item" mod={{ type: 'field' }}>字段名称</Elem>
                <Elem name="header-item" mod={{ type: 'total' }}>总样本数</Elem>
                <Elem name="header-item" mod={{ type: 'correct' }}>正确数</Elem>
                <Elem name="header-item" mod={{ type: 'accuracy' }}>识别正确率</Elem>
              </Elem>
              {Object.entries(field_accuracy).map(([field, accuracy]) => {
                const totalSamples = statistics?.total_invoices || 0;
                const correctSamples = Math.round((accuracy / 100) * totalSamples);
                return (
                  <Elem key={field} name="field-row">
                    <Elem name="field-item" mod={{ type: 'field' }}>{field}</Elem>
                    <Elem name="field-item" mod={{ type: 'total' }}>{totalSamples}</Elem>
                    <Elem name="field-item" mod={{ type: 'correct' }}>{correctSamples}</Elem>
                    <Elem name="field-item" mod={{ type: 'accuracy', level: getMetricColor(accuracy / 100) }}>
                      {accuracy.toFixed(2)}%
                    </Elem>
                  </Elem>
                );
              })}
              {/* 总计行，放在 field-list 内部，确保同宽 */}
              <Elem name="field-row" mod={{ type: 'total-row' }}>
                <Elem name="field-item" mod={{ type: 'field', weight: 'bold' }}>总计</Elem>
                <Elem name="field-item" mod={{ type: 'total', weight: 'bold' }}>
                  {Object.keys(field_accuracy).length * (statistics?.total_invoices || 0)}
                </Elem>
                <Elem name="field-item" mod={{ type: 'correct', weight: 'bold' }}>
                  {Object.entries(field_accuracy).reduce((sum, [field, accuracy]) => {
                    const totalSamples = statistics?.total_invoices || 0;
                    const correctSamples = Math.round((accuracy / 100) * totalSamples);
                    return sum + correctSamples;
                  }, 0)}
                </Elem>
                <Elem name="field-item" mod={{ type: 'accuracy', weight: 'bold' }}>
                  {Object.keys(field_accuracy).length > 0 ? (
                    (Object.values(field_accuracy).reduce((sum, acc) => sum + acc, 0) / Object.keys(field_accuracy).length).toFixed(2)
                  ) : '0.00'}%
                </Elem>
              </Elem>
            </Elem>
          </Elem>
        )}
      </>
    );
  };

  const renderStandardMetrics = () => {
    if (isInvoiceEvaluation) return null;
    
    // 添加安全检查，确保metrics对象存在且有必要的属性
    if (!metrics || typeof metrics !== 'object') {
      return null;
    }
    
    return (
      <Elem name="metrics-section">
        <Elem name="section-title">Performance Metrics</Elem>
        <Elem name="metrics-grid">
          <MetricCard
            title="Accuracy"
            value={metrics.accuracy || 0}
          />
          <MetricCard
            title="Precision"
            value={metrics.precision || 0}
          />
          <MetricCard
            title="Recall"
            value={metrics.recall || 0}
          />
          <MetricCard
            title="F1 Score"
            value={metrics.f1_score || 0}
          />
        </Elem>
      </Elem>
    );
  };

  // 构建prompt选项
  const promptOptions = [
    { label: 'Default', value: 'Default' },
    ...prompts.map(prompt => ({
      label: prompt.name,
      value: prompt.name
    }))
  ];

  return (
    <Modal
      title="Evaluation Results"
      visible={true}
      onHide={onClose}
      size="large"
      style={{ maxHeight: '92vh', height: 'auto', width: '70vw', maxWidth: '70vw', minHeight: 400 }}
    >
      <Block name="evaluation-results" mod={{ scrollable: true }} style={{ maxHeight: 'calc(90vh - 52px)', overflowY: 'auto' }}>
        {/* Summary Section */}
        <Elem name="summary">
          <Elem name="summary-item">
            <span><strong>总文档数:</strong> <span className="summary-number">{evaluation_results?.statistics?.total_documents || task_count}</span></span>
          </Elem>
          <Elem name="summary-item">
            <span><strong>总票据数:</strong> <span className="summary-number">{evaluation_results?.statistics?.total_invoices || processed_items}</span></span>
          </Elem>
          <Elem name="summary-item">
            <span><strong>总字段数:</strong> <span className="summary-number">{evaluation_results?.statistics?.field_accuracy ? 
              Object.keys(evaluation_results.statistics.field_accuracy).length * (evaluation_results?.statistics?.total_invoices || processed_items) : 0}</span></span>
          </Elem>
          <Elem name="summary-item">
            <span><strong>模型:</strong> <span className="summary-number">{evaluation_results?.statistics?.model_version || 'N/A'}</span></span>
          </Elem>
          <Elem name="summary-item">
            <span><strong>时间:</strong> <span className="summary-number">{formatDate(evaluated_at)}</span></span>
          </Elem>
        </Elem>

        {/* Metrics Section */}
        {renderInvoiceMetrics()}
        {renderStandardMetrics()}
        
        {/* Excel Report Download Section */}
        {evaluation_results?.excel_path && (
          <Elem name="details-section">
            <Elem name="section-title">
              详情报告
              <Space direction="horizontal" size="small">
                <Button 
                  type="text" 
                  size="small" 
                  icon={<Icon icon={IconFileDownload} size={14} />}
                  onClick={downloadExcelReport}
                  className="download-button"
                  title="下载详细评估报告"
                >
                  下载Excel
                </Button>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div onClick={handleSelectClick}>
                    <Select
                      value={selectedPrompt}
                      onChange={handlePromptChange}
                      options={promptOptions}
                      size="small"
                      style={{ minWidth: '120px' }}
                      placeholder="选择Prompt"
                      title="选择分析时使用的Prompt"
                    />
                  </div>
                  <Button 
                    type="text" 
                    size="small" 
                    icon={<span style={{fontSize: '14px'}}>🧠</span>}
                    onClick={analyzeEvaluationReport}
                    loading={isAnalyzing || false}
                    className="analyze-button"
                    title={`使用AI分析评估报告${selectedPrompt !== 'Default' ? ` (${selectedPrompt})` : ''}`}
                    disabled={isAnalyzing}
                  >
                    {isAnalyzing ? '分析中...' : '分析'}
                  </Button>
                </div>
              </Space>
            </Elem>
            {/* Analysis Result Section */}
            {analysisResult && (
              <Elem name="analysis-section">
                <Elem name="analysis-header">
                  <Elem name="analysis-title">🎯 分析结果</Elem>
                  <Button 
                    type="text" 
                    size="small" 
                    icon={<Icon icon={IconFileDownload} size={14} />}
                    onClick={downloadAnalysisReportCallback}
                    className="download-analysis-button"
                    title="下载分析报告文档"
                  >
                    下载报告
                  </Button>
                </Elem>
                <Elem name="analysis-content">
                  <div 
                    dangerouslySetInnerHTML={{ 
                      __html: renderContent(analysisResult)
                    }} 
                  />
                </Elem>
              </Elem>
            )}
            
            {/* Analysis Error Section */}
            {analysisError && !analysisResult && (
              <Elem name="analysis-section" mod={{ error: true }}>
                <Elem name="analysis-header">
                  <Elem name="analysis-title">❌ 分析失败</Elem>
                </Elem>
                <Elem name="analysis-content" mod={{ error: true }}>
                  <div className="error-message">
                    <p><strong>错误信息：</strong></p>
                    <p>{analysisError}</p>
                    <div className="error-suggestions">
                      <p><strong>可能的解决方案：</strong></p>
                      <ul>
                        <li>检查网络连接是否正常</li>
                        <li>确认ML Backend服务运行正常</li>
                        <li>检查Excel文件是否完整</li>
                        <li>尝试重新执行分析</li>
                      </ul>
                    </div>
                  </div>
                </Elem>
              </Elem>
            )}
          </Elem>
        )}
      </Block>
    </Modal>
  );
};

export { EvaluationResultModal };
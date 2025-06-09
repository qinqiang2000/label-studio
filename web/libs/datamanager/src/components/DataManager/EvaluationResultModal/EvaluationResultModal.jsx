import React, { useCallback } from 'react';
import { Modal } from '../../Common/Modal/ModalPopup';
import { Button } from '../../Common/Button/Button';
import { Space } from '../../Common/Space/Space';
import { Block, Elem } from '../../../utils/bem';
import { Icon } from '../../Common/Icon/Icon';
import { IconCopy, IconFileDownload } from '@humansignal/icons';
import './EvaluationResultModal.scss';

const EvaluationResultModal = ({ result, onClose }) => {
  if (!result || !result.evaluation_results) {
    return null;
  }

  const { evaluation_results, processed_items, detail, evaluation_type } = result;
  const { metrics, task_count, evaluated_at, project_id } = evaluation_results;
  
  // 检查是否为票据提取评估
  const isInvoiceEvaluation = evaluation_type === 'invoice_extraction';

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

  const formatPercentage = (value) => {
    return (value * 100).toFixed(2) + '%';
  };

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleString();
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
              {/* 总计行 */}
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
    
    return (
      <Elem name="metrics-section">
        <Elem name="section-title">Performance Metrics</Elem>
        <Elem name="metrics-grid">
          <MetricCard
            title="Accuracy"
            value={metrics.accuracy}
          />
          <MetricCard
            title="Precision"
            value={metrics.precision}
          />
          <MetricCard
            title="Recall"
            value={metrics.recall}
          />
          <MetricCard
            title="F1 Score"
            value={metrics.f1_score}
          />
        </Elem>
      </Elem>
    );
  };

  return (
    <Modal
      title="Evaluation Results"
      visible={true}
      onHide={onClose}
      size="large"
      style={{ maxHeight: '90vh', height: 'auto', width: '65vw', maxWidth: '65vw', minHeight: 400 }}
    >
      <Block name="evaluation-results" mod={{ scrollable: true }} style={{ maxHeight: 'calc(90vh - 48px)', overflowY: 'auto' }}>
        {/* Summary Section */}
        <Elem name="summary">
          <Elem name="summary-item">
            <span><strong>总文档数:</strong> {evaluation_results?.statistics?.total_documents || task_count}</span>
          </Elem>
          <Elem name="summary-item">
            <span><strong>总票据数:</strong> {evaluation_results?.statistics?.total_invoices || processed_items}</span>
          </Elem>
          <Elem name="summary-item">
            <span><strong>总字段数:</strong> {evaluation_results?.statistics?.field_accuracy ? Object.keys(evaluation_results.statistics.field_accuracy).length : 0}</span>
          </Elem>
          <Elem name="summary-item">
            <span><strong>评估时间:</strong> {formatDate(evaluated_at)}</span>
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
            </Elem>
            <Elem name="section-description">
              点击上方按钮下载包含详细评估数据的Excel报告，包括每个字段的识别结果和准确率统计
            </Elem>

          </Elem>
        )}
        

        {/* Performance Interpretation */}
        {/* <Elem name="interpretation">
          <Elem name="section-title">Performance Interpretation</Elem>
          <Elem name="interpretation-content">
            <Elem name="interpretation-item">
              <Elem name="color-indicator" mod={{ level: 'excellent' }} />
              <span>Excellent (≥80%): Outstanding performance</span>
            </Elem>
            <Elem name="interpretation-item">
              <Elem name="color-indicator" mod={{ level: 'good' }} />
              <span>Good (60-79%): Satisfactory performance</span>
            </Elem>
            <Elem name="interpretation-item">
              <Elem name="color-indicator" mod={{ level: 'fair' }} />
              <span>Fair (40-59%): Needs improvement</span>
            </Elem>
            <Elem name="interpretation-item">
              <Elem name="color-indicator" mod={{ level: 'poor' }} />
              <span>Poor (&lt;40%): Significant improvement needed</span>
            </Elem>
          </Elem>
        </Elem> */}
      </Block>
    </Modal>
  );
};

export { EvaluationResultModal };
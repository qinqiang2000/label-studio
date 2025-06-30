import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher
import shutil

from core.permissions import AllPermissions
from django.db.models import Q, Count
from tasks.models import Task, Annotation, Prediction
from evaluation_configs.models import EvaluationFieldConfig, ProjectEvaluationConfig
from .invoice_compare.invoice_compare_utils import InvoiceComparer
from .evaluation_export_adapter import add_annotations_predictions_to_excel
import os
import tempfile
import pandas as pd
from openpyxl import load_workbook


all_permissions = AllPermissions()
logger = logging.getLogger(__name__)


def get_available_prediction_options(project, queryset):
    """
    Get available prompt names and model versions from the selected tasks
    
    :param project: Project instance
    :param queryset: QuerySet of selected tasks
    :return: Dictionary with available options
    """
    # Get tasks with both annotations and predictions
    tasks_with_both = queryset.filter(
        annotations__isnull=False,
        predictions__isnull=False
    ).distinct()
    
    # Get all predictions for these tasks
    predictions = Prediction.objects.filter(task__in=tasks_with_both)
    
    # Get unique prompt names (excluding None and empty strings)
    prompt_names = list(predictions.exclude(
        Q(prompt_name__isnull=True) | Q(prompt_name='')
    ).values_list('prompt_name', flat=True).distinct())
    
    # Get unique model versions (excluding None and empty strings)
    model_versions = list(predictions.exclude(
        Q(model_version__isnull=True) | Q(model_version='')
    ).values_list('model_version', flat=True).distinct())
    
    # Get unique combinations
    combinations = list(predictions.exclude(
        Q(prompt_name__isnull=True) | Q(prompt_name='') |
        Q(model_version__isnull=True) | Q(model_version='')
    ).values_list('prompt_name', 'model_version').distinct())
    
    return {
        'prompt_names': sorted(prompt_names),
        'model_versions': sorted(model_versions),
        'combinations': sorted(combinations),
        'total_predictions': predictions.count(),
        'total_tasks': tasks_with_both.count()
    }


def get_project_evaluation_config(project):
    """
    Get the evaluation configuration for a project
    
    :param project: Project instance
    :return: ProjectEvaluationConfig instance or default configuration
    """
    try:
        return ProjectEvaluationConfig.objects.get(project=project)
    except ProjectEvaluationConfig.DoesNotExist:
        # Check if project has evaluation_field_config configured
        if hasattr(project, 'evaluation_field_config') and project.evaluation_field_config:
            project_eval_config = project.evaluation_field_config
            document_type = project_eval_config.get('document_type')
            
            if document_type:
                try:
                    # Find configuration by document_type key
                    config = EvaluationFieldConfig.objects.get(
                        key=document_type, 
                        is_active=True
                    )
                    
                    # Always use config.required_fields for evaluation, not project default_fields
                    # This ensures evaluation only uses the required fields defined in the configuration template
                    
                    # Create a temporary ProjectEvaluationConfig for consistency
                    return type('ProjectEvaluationConfig', (), {
                        'project': project,
                        'evaluation_config': config,
                        'effective_required_fields': config.required_fields,
                        'effective_optional_fields': config.optional_fields,
                        'effective_all_fields': config.all_fields,
                        'effective_validation_rules': config.field_validation_rules,
                    })()
                    
                except EvaluationFieldConfig.DoesNotExist:
                    logger.warning(f"Configuration '{document_type}' not found for project {project.id}")
        
        # Return default configuration if no specific config exists
        default_config = EvaluationFieldConfig.objects.filter(
            is_system_default=True,
            is_active=True
        ).first()
        
        if default_config:
            # Create a temporary ProjectEvaluationConfig for consistency
            return type('ProjectEvaluationConfig', (), {
                'project': project,
                'evaluation_config': default_config,
                'effective_required_fields': default_config.required_fields,
                'effective_optional_fields': default_config.optional_fields,
                'effective_all_fields': default_config.all_fields,
                'effective_validation_rules': default_config.field_validation_rules,
            })()
        else:
            # Fallback to a basic configuration
            return type('ProjectEvaluationConfig', (), {
                'project': project,
                'evaluation_config': type('EvaluationFieldConfig', (), {
                    'name': 'Default',
                    'key': 'default',
                    'evaluation_settings': {}
                })(),
                'effective_required_fields': ['docType'],
                'effective_optional_fields': [],
                'effective_all_fields': ['docType'],
                'effective_validation_rules': {},
            })()


def post_process_documents(documents_data, field_config):
    """
    Post-process document data based on evaluation field configuration
    
    :param documents_data: Document data, can be JSON string or parsed list
    :param field_config: EvaluationFieldConfig instance
    :return: Processed document data (same format as input)
    """
    # Get post-processing rules from evaluation settings
    eval_settings = getattr(field_config, 'evaluation_settings', {})
    post_processing = eval_settings.get('post_processing', {})
    
    # If no post-processing rules, return original data
    if not post_processing:
        return documents_data
    
    # Determine input format
    is_string_input = isinstance(documents_data, str)
    
    try:
        # Parse if string
        if is_string_input:
            data = json.loads(documents_data)
        else:
            data = documents_data
            
        # Ensure data is list
        if not isinstance(data, list):
            logger.warning(f"Document data should be a list, got {type(data)}")
            return documents_data
            
        # Apply post-processing rules
        for document in data:
            if not isinstance(document, dict):
                continue
                
            # Example: Calculate totalTaxAmount from detailOfTaxSummary
            if 'calculate_totals' in post_processing:
                calculate_rules = post_processing['calculate_totals']
                
                for target_field, calc_rule in calculate_rules.items():
                    if target_field in document:
                        continue  # Don't override existing values
                        
                    if calc_rule['method'] == 'sum_from_array':
                        source_array = document.get(calc_rule['source_array'], [])
                        source_field = calc_rule['source_field']
                        total = 0
                        
                        if isinstance(source_array, list):
                            for item in source_array:
                                if isinstance(item, dict) and source_field in item:
                                    value = item[source_field]
                                    if isinstance(value, (int, float)):
                                        total += value
                                    elif isinstance(value, str):
                                        try:
                                            total += float(value)
                                        except ValueError:
                                            logger.warning(f"Invalid {source_field} value: {value}")
                        
                        document[target_field] = total
            
            # Add serial numbers if configured
            if 'add_serial_numbers' in post_processing and post_processing['add_serial_numbers']:
                # This would be handled at array level, not individual document level
                pass
                
        # Handle array-level post-processing
        if 'add_serial_numbers' in post_processing and post_processing['add_serial_numbers']:
            for i, document in enumerate(data):
                if isinstance(document, dict):
                    serial_field = post_processing.get('serial_number_field', '序号')
                    if serial_field not in document:
                        document[serial_field] = i + 1
                        
        # Return in same format as input
        if is_string_input:
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return data
            
    except json.JSONDecodeError as e:
        logger.error(f"Error parsing JSON: {e}")
        return documents_data
    except Exception as e:
        logger.error(f"Error in post_process_documents: {e}")
        return documents_data


def filter_json_by_fields(json_text: str, fields: List[str]) -> str:
    """
    Filter json_text (JSON array string) to keep only specified fields
    Also preserves the 'page' field if it exists for display purposes
    
    :param json_text: JSON array string
    :param fields: List of fields to keep
    :return: Filtered JSON array string
    """
    try:
        data = json.loads(json_text)
        if not isinstance(data, list):
            raise ValueError("Input JSON must be a list of dicts")
        
        # Always include 'page' field if it exists
        fields_to_keep = set(fields)
        fields_to_keep.add('page')  # 始终保留page字段
        
        filtered = [
            {k: v for k, v in item.items() if k in fields_to_keep}
            for item in data if isinstance(item, dict)
        ]
        return json.dumps(filtered, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.error(f"filter_json_by_fields error: {e}")
        return json_text  # fallback to original


def process_comparison_results(filename: str, standard_documents: List[dict], 
                             prediction_documents: List[dict], result: dict, 
                             compare_fields: List[str], comparer, prompt_name: str, 
                             evaluation_config) -> List[dict]:
    """
    Process comparison results and generate Excel row data
    Dynamically handles different document types based on evaluation configuration
    修复：按照标准数据的原始顺序生成明细表
    """
    rows = []
    
    # Only check docType if it's in the compare_fields (predefined fields from project config)
    # This ensures we only validate fields that the project actually cares about
    need_doc_type_check = 'docType' in compare_fields
    
    allowed_doc_types = set()
    if need_doc_type_check:
        # Get validation rules from evaluation config
        validation_rules = getattr(evaluation_config, 'effective_validation_rules', {})
        doc_type_rule = validation_rules.get('docType', {})
        allowed_doc_types = set(doc_type_rule.get('allowed_values', []))
    
    # 新方法：按照标准文档的原始顺序遍历，为每个标准文档找到对应的预测文档
    # 这里需要根据匹配策略决定使用位置匹配还是字段匹配
    
    # 获取匹配策略配置
    eval_settings = getattr(evaluation_config, 'evaluation_settings', {})
    matching_strategy_config = eval_settings.get('matching_strategy', {})
    use_position_matching = (
        matching_strategy_config.get('mode') == 'position_based' or 
        matching_strategy_config.get('primary_fields') == [] or
        matching_strategy_config.get('primary_fields') == ['_position']
    )
    
    remaining_predictions = list(range(len(prediction_documents)))
    
    for std_idx, std_doc in enumerate(standard_documents):
        # Check document type if needed
        if need_doc_type_check:
            std_doc_type = (std_doc.get('docType') or '').lower()
            # Allow empty docType to pass validation (skip validation for empty values)
            # Only validate if docType has a value and it's not in allowed list
            if std_doc_type and std_doc_type not in allowed_doc_types:
                continue
        
        # 寻找匹配的预测文档
        matched_pred_doc = None
        matched_pred_idx = None
        
        if use_position_matching:
            # 位置匹配：严格按位置一一对应
            if std_idx < len(prediction_documents):
                matched_pred_doc = prediction_documents[std_idx]
                # 找到在remaining_predictions中的索引位置
                if std_idx in remaining_predictions:
                    matched_pred_idx = remaining_predictions.index(std_idx)
        else:
            # 字段匹配：使用InvoiceComparer的匹配逻辑
            for i, pred_idx in enumerate(remaining_predictions):
                pred_doc = prediction_documents[pred_idx]
                is_equal, diff_fields = comparer.invoices_equal(std_doc, pred_doc)
                
                # 这里我们接受完全匹配和部分匹配
                if is_equal or (diff_fields and len(diff_fields) < len(compare_fields)):
                    matched_pred_doc = pred_doc
                    matched_pred_idx = i
                    break
        
        # 如果找到匹配的文档，从剩余列表中移除
        if matched_pred_idx is not None:
            remaining_predictions.pop(matched_pred_idx)
        
        # 如果没有找到匹配，尝试找一个最相似的预测文档用于显示
        if matched_pred_doc is None and remaining_predictions:
            # 简单策略：取第一个剩余的预测文档用于显示
            pred_idx = remaining_predictions.pop(0)
            matched_pred_doc = prediction_documents[pred_idx]
        
        # 创建数据行
        row = {'filename': filename, 'prompt_name': prompt_name}
        
        # 添加page字段（如果存在）作为第二列 - 只显示标注数据的page
        if 'page' in std_doc:
            page_value = std_doc['page']
            # 处理数组类型的page字段
            if isinstance(page_value, list):
                row['page'] = ','.join(map(str, page_value)) if page_value else ''
            else:
                row['page'] = str(page_value) if page_value else ''
            
            # 只有当用户配置了page字段用于比较时，才显示预测数据和比较结果
            if 'page' in compare_fields:
                # 预测数据的page字段
                if matched_pred_doc and 'page' in matched_pred_doc:
                    pred_page_value = matched_pred_doc['page']
                    if isinstance(pred_page_value, list):
                        row['pred_page'] = ','.join(map(str, pred_page_value)) if pred_page_value else ''
                    else:
                        row['pred_page'] = str(pred_page_value) if pred_page_value else ''
                else:
                    row['pred_page'] = ''
                
                # 比较page字段
                row['check_page'] = (row['page'] == row['pred_page']) if matched_pred_doc else False
        
        # 添加每个配置字段的标准值、预测值和检查结果
        for field in compare_fields:
            std_value = std_doc.get(field, '')
            pred_value = matched_pred_doc.get(field, '') if matched_pred_doc else ''
            
            # 使用comparer的归一化逻辑来判断字段是否相等
            if matched_pred_doc:
                check_result = comparer.field_values_equal(std_value, pred_value, field)
            else:
                check_result = False  # 没有预测文档时视为不匹配
            
            row[f'std_{field}'] = std_value
            row[f'pred_{field}'] = pred_value
            row[f'check_{field}'] = check_result
        
        rows.append(row)
    
    return rows


def compare_documents_with_comparer(annotation_text_filtered, prediction_text_filtered, compare_fields, evaluation_config):
    """
    Compare documents using InvoiceComparer with evaluation configuration
    
    :param annotation_text_filtered: Filtered annotation data (JSON string)
    :param prediction_text_filtered: Filtered prediction data (JSON string)
    :param compare_fields: List of fields to compare
    :param evaluation_config: Evaluation configuration
    :return: Comparison result
    """
    # Get comparison settings from evaluation config
    eval_settings = getattr(evaluation_config, 'evaluation_settings', {})
    matching_strategy_config = eval_settings.get('matching_strategy', {})
    
    # Create InvoiceComparer with matching strategy configuration
    comparer = InvoiceComparer(
        core_fields=compare_fields, 
        verbose=False,
        name_overlap_threshold=eval_settings.get('name_overlap_threshold', 0.5),
        strategy_config=matching_strategy_config,
        use_degraded_matching=True
    )
    
    try:
        # Perform document comparison
        result = comparer.compare_invoices(annotation_text_filtered, prediction_text_filtered)
        return result
        
    except Exception as e:
        logger.error(f"Document comparison error: {e}")
        return {
            "error": str(e),
            "matched_count": 0,
            "unmatched_count": 0,
            "only_in_standard_count": 0,
            "only_in_prediction_count": 0,
            "invoice_accuracy": 0.0,
            "field_accuracy": 0.0
        }


def generate_excel_report(excel_data, compare_fields, statistics, evaluation_config):
    """
    Generate Excel report for document comparison results
    
    Args:
        excel_data: List containing comparison data
        compare_fields: List of fields to compare
        statistics: Pre-calculated statistics
        evaluation_config: Evaluation configuration
    
    Returns:
        tuple: (excel_output_path, all_rows)
    """
    # Create temporary file
    temp_fd, excel_output_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(temp_fd)

    # 检查是否有page字段数据 - 在处理前先检查
    has_page_data = False
    if excel_data:
        try:
            first_data = excel_data[0]
            standard_documents = json.loads(first_data['annotation_text'])
            if standard_documents and isinstance(standard_documents, list) and len(standard_documents) > 0:
                # 检查第一个文档是否有page字段
                if 'page' in standard_documents[0]:
                    has_page_data = True
        except:
            pass

    # Create column order, 确保page字段出现在第二列（如果存在）
    columns = ['filename', 'prompt_name']
    
    # 如果有page数据，添加page列
    if has_page_data:
        columns.append('page')
        # 只有当page字段配置用于比较时才添加pred_page和check_page列
        if 'page' in compare_fields:
            columns.extend(['pred_page', 'check_page'])
    
    # 添加配置字段的列
    for field in compare_fields:
        columns.extend([f'std_{field}', f'pred_{field}', f'check_{field}'])
    
    all_rows = []
    
    try:
        # Process data
        for data in excel_data:
            filename = data['filename']
            annotation_text = data['annotation_text']
            prediction_text = data['prediction_text']
            result = data['result']
            prompt_name = data['prompt_name']
            
            # Parse JSON data
            try:
                standard_documents = json.loads(annotation_text)
                prediction_documents = json.loads(prediction_text)
            except json.JSONDecodeError as e:
                logger.error(f"JSON parsing failed for {filename}: {e}")
                continue
            
            # Create comparer
            eval_settings = getattr(evaluation_config, 'evaluation_settings', {})
            comparer = InvoiceComparer(
                core_fields=compare_fields, 
                verbose=False,
                name_overlap_threshold=eval_settings.get('name_overlap_threshold', 0.5)
            )
            
            # Process comparison results
            file_rows = process_comparison_results(
                filename, standard_documents, prediction_documents, 
                result, compare_fields, comparer, prompt_name, evaluation_config
            )
            all_rows.extend(file_rows)
        
        # Write Excel
        with pd.ExcelWriter(excel_output_path, engine='openpyxl') as writer:
            # Statistics sheet
            _create_statistics_sheet(writer, statistics, compare_fields, evaluation_config)
            # Details sheet
            _create_details_sheet(writer, all_rows, columns)
            
    except Exception as e:
        logger.error(f"Excel report generation error: {e}")
        # Create basic fallback Excel
        try:
            df = pd.DataFrame(columns=columns)
            with pd.ExcelWriter(excel_output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Document_Details', index=False)
            logger.info(f"Created empty Excel file: {excel_output_path}")
        except Exception as fallback_e:
            logger.error(f"Fallback Excel creation failed: {fallback_e}")

    return excel_output_path, all_rows


def _create_statistics_sheet(writer, statistics, compare_fields, evaluation_config):
    """Create statistics sheet using template and fill in corresponding positions"""
    # Get the template path
    template_path = os.path.join(os.path.dirname(__file__), 'invoice_compare', 'statisitcs_template_v1.0.xlsx')
    
    try:
        # Load the template workbook
        template_wb = load_workbook(template_path)
        template_ws = template_wb['Statistics']
        
        # Copy the template sheet structure to our workbook
        # Create new worksheet in writer
        workbook = writer.book
        worksheet = workbook.create_sheet('Statistics')
        
        # Copy all cells from template with complete formatting
        for row in template_ws.iter_rows():
            for cell in row:
                new_cell = worksheet.cell(row=cell.row, column=cell.column)
                new_cell.value = cell.value
                
                # Copy all formatting attributes
                if cell.has_style:
                    new_cell.font = cell.font.copy() if cell.font else None
                    new_cell.fill = cell.fill.copy() if cell.fill else None
                    new_cell.border = cell.border.copy() if cell.border else None
                    new_cell.alignment = cell.alignment.copy() if cell.alignment else None
                
                # 重要：复制数字格式（包括百分比格式）
                if cell.number_format:
                    new_cell.number_format = cell.number_format
        
        # Copy merged cells
        for merged_range in template_ws.merged_cells.ranges:
            worksheet.merge_cells(str(merged_range))
        
        # Copy column dimensions
        for col_letter, dimension in template_ws.column_dimensions.items():
            worksheet.column_dimensions[col_letter].width = dimension.width
        
        # Copy row dimensions
        for row_num, dimension in template_ws.row_dimensions.items():
            worksheet.row_dimensions[row_num].height = dimension.height
        
        # D3-D8的百分比格式已经从模板复制，统一为无小数点格式以保持一致性
        for row in range(3, 9):
            cell = worksheet[f'D{row}']
            # 统一设置为无小数点的百分比格式
            if cell.number_format and '%' in cell.number_format:
                cell.number_format = '0%'
        
        # Now fill in the data at the correct positions based on the template structure
        config_name = getattr(evaluation_config.evaluation_config, 'name', 'Unknown')
        
        # 整体情况 section (rows 3-11)
        worksheet['C3'] = statistics['total_documents']  # 总文件数
        worksheet['C4'] = statistics.get('only_other_docs', 0)  # 总文件数（纯other类型文件）
        worksheet['C5'] = statistics.get('docs_with_invoices', statistics['total_documents'])  # 总文件数（含票据文件）
        worksheet['C6'] = statistics['total_invoices']  # 总票据数
        worksheet['C7'] = statistics.get('invoice_count', 0)  # Invoice数
        worksheet['C8'] = statistics.get('receipt_count', 0)  # Receipt数
        worksheet['C9'] = statistics['total_invoices'] * len(compare_fields)  # 票据下总字段数
        
        # Use prompt names instead of model version for C10
        prompt_names = statistics.get('prompt_names', set())
        if prompt_names:
            prompt_name_str = ', '.join(sorted(prompt_names))
        else:
            prompt_name_str = statistics.get('model_version', 'N/A')
        worksheet['C10'] = prompt_name_str  # Prompts版本
        
        worksheet['C11'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')  # 评估时间
        
        # 整体指标 section - 使用关键词查找而非硬编码位置，提高robust性
        metrics_mapping = {
            '可识别率': ('recognition_rate', statistics.get('recognition_rate', 0.0)),
            '文件准确率': ('document_accuracy', statistics['document_accuracy']),
            '票据准确率': ('invoice_accuracy', statistics['invoice_accuracy']),
            '字段准确率': ('overall_field_accuracy', statistics['overall_field_accuracy'])
        }
        
        # 在模板中查找关键词并填充相应的C列数据
        for row in range(1, worksheet.max_row + 1):
            cell_a = worksheet.cell(row=row, column=1)  # A列包含指标名称
            if cell_a.value:
                cell_text = str(cell_a.value).strip()
                for keyword, (stat_key, stat_value) in metrics_mapping.items():
                    if keyword in cell_text:
                        # 在同一行的C列填入数据
                        c_cell = worksheet.cell(row=row, column=3)
                        c_cell.value = stat_value / 100
                        # 统一设置为百分比格式以保持一致性
                        c_cell.number_format = '0%'
                        break
        
        # 核心字段指标 section (starting from row 22)
        # Fill in field-specific data
        current_row = 22
        total_correct = 0
        
        # Calculate the total row position based on the number of fields
        total_row = 22 + len(compare_fields)
        
        # If we need more rows than the template provides, insert them
        if len(compare_fields) > 6:  # Template supports 6 fields (rows 22-27)
            rows_to_insert = len(compare_fields) - 6
            # Insert rows before the total row (which was originally at row 28)
            worksheet.insert_rows(28, rows_to_insert)
            # Update total_row position
            total_row = 28 + rows_to_insert
        
        for field in compare_fields:
            field_stats = statistics['field_accuracy'].get(field, 0)
            correct_count = round(statistics['total_invoices'] * field_stats / 100)
            total_correct += correct_count
            
            # 使用原始字段名称，不进行翻译
            # field_labels = getattr(evaluation_config.evaluation_config, 'field_labels', {})
            # field_label = field_labels.get(field, field)
            field_label = field  # 直接使用原始字段名称
            
            # Fill in the data
            worksheet.cell(row=current_row, column=1, value=field_label)  # A列：指标名称
            worksheet.cell(row=current_row, column=2, value=field_label)  # B列：指标定义
            worksheet.cell(row=current_row, column=3, value=statistics['total_invoices'])  # C列：总票据数
            worksheet.cell(row=current_row, column=4, value=correct_count)  # D列：正确识别
            
            # E列：识别正确率 - 使用数值而非字符串，保持模板的百分比格式
            e_cell = worksheet.cell(row=current_row, column=5, value=field_stats / 100)
            # 只有当需要统一为无小数点格式时才覆盖模板格式
            if e_cell.number_format and '%' in e_cell.number_format and '.' in e_cell.number_format:
                e_cell.number_format = '0%'
            
            current_row += 1
        
        # Fill in total row (at the calculated total_row position)
        total_accuracy = round(total_correct / (statistics['total_invoices'] * len(compare_fields)) * 100, 2) if statistics['total_invoices'] > 0 and len(compare_fields) > 0 else 0
        worksheet.cell(row=total_row, column=3, value=statistics['total_invoices'] * len(compare_fields))  # 总票据数
        worksheet.cell(row=total_row, column=4, value=total_correct)  # 正确识别总数
        
        # E总识别正确率 - 使用数值而非字符串，保持模板的百分比格式
        e_total_cell = worksheet.cell(row=total_row, column=5, value=total_accuracy / 100)
        # 只有当需要统一为无小数点格式时才覆盖模板格式
        if e_total_cell.number_format and '%' in e_total_cell.number_format and '.' in e_total_cell.number_format:
            e_total_cell.number_format = '0%'
        
        # Remove the default Sheet if it exists
        if 'Sheet' in workbook.sheetnames:
            workbook.remove(workbook['Sheet'])
        
    except Exception as e:
        logger.error(f"Error creating statistics sheet from template: {e}")
        # Fallback to original method if template loading fails
        _create_statistics_sheet_fallback(writer, statistics, compare_fields, evaluation_config)


def _create_statistics_sheet_fallback(writer, statistics, compare_fields, evaluation_config):
    """Fallback method for creating statistics sheet if template loading fails"""
    config_name = getattr(evaluation_config.evaluation_config, 'name', 'Unknown')
    
    stats_data = []
    # Overview section
    stats_data.extend([
        ['Document Evaluation Report'],
        ['Configuration:', config_name],
        ['Total Documents:', statistics['total_documents']],
        ['Total Items:', statistics['total_invoices']],  # Keep 'invoices' for compatibility
        ['Total Fields:', statistics['total_invoices'] * len(statistics['field_accuracy'])],
        ['Model Version:', statistics.get('model_version', 'N/A')],
        ['Evaluation Time:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['']
    ])
    
    # Metrics section
    stats_data.extend([
        ['Overall Metrics'],
        ['Document Accuracy:', f"{statistics['document_accuracy']}%"],
        ['Item Accuracy:', f"{statistics['invoice_accuracy']}%"],
        ['Field Accuracy:', f"{statistics['overall_field_accuracy']}%"],
        ['']
    ])
    
    # Field details
    stats_data.extend([
        ['Field Details'],
        ['Field Name', 'Total Samples', 'Correct Count', 'Accuracy']
    ])
    
    total_correct = 0
    for field in compare_fields:
        field_stats = statistics['field_accuracy'].get(field, 0)
        correct_count = round(statistics['total_invoices'] * field_stats / 100)
        total_correct += correct_count
        
        # 使用原始字段名称，不进行翻译
        # field_labels = getattr(evaluation_config.evaluation_config, 'field_labels', {})
        # field_label = field_labels.get(field, field)
        field_label = field  # 直接使用原始字段名称
        
        stats_data.append([
            field_label,
            statistics['total_invoices'],
            correct_count,
            f"{field_stats}%"
        ])
    
    # Total row
    total_accuracy = round(total_correct / (statistics['total_invoices'] * len(compare_fields)) * 100, 2)
    stats_data.append([
        'Total',
        statistics['total_invoices'] * len(compare_fields),
        total_correct,
        f"{total_accuracy}%"
    ])
    
    # Create DataFrame and write
    stats_df = pd.DataFrame(stats_data)
    stats_df.to_excel(writer, sheet_name='Statistics', index=False, header=False)
    
    # Adjust column widths
    worksheet = writer.sheets['Statistics']
    for idx, col in enumerate(stats_df.columns):
        max_length = max(
            stats_df[col].astype(str).apply(len).max(),
            len(str(col))
        )
        worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2


def _create_details_sheet(writer, all_rows, columns):
    """Create details sheet with conditional formatting"""
    if all_rows:
        df = pd.DataFrame(all_rows, columns=columns)
    else:
        df = pd.DataFrame(columns=columns)
        logger.info("Excel report generated with empty data sheet")
    
    df.to_excel(writer, sheet_name='Document_Details', index=False)
    
    # Add conditional formatting for check columns
    worksheet = writer.sheets['Document_Details']
    
    from openpyxl.styles import Font
    from openpyxl.formatting.rule import CellIsRule
    
    check_columns = [col for col in columns if col.startswith('check_')]
    
    if check_columns and len(all_rows) > 0:
        for col_name in check_columns:
            col_index = columns.index(col_name) + 1
            col_letter = chr(64 + col_index)
            
            red_font = Font(color="FF0000")
            rule = CellIsRule(operator='equal', formula=[False], font=red_font)
            
            range_string = f"{col_letter}2:{col_letter}{len(all_rows) + 1}"
            try:
                worksheet.conditional_formatting.add(range_string, rule)
            except Exception as format_e:
                logger.warning(f"Conditional formatting failed: {format_e}")


def calculate_evaluation_statistics(all_rows, excel_data=None):
    """Calculate evaluation statistics from comparison results"""
    if not all_rows:
        return {
            'field_accuracy': {},
            'invoice_accuracy': 0.0,
            'document_accuracy': 0.0,
            'total_invoices': 0,
            'total_documents': 0,
            'only_other_docs': 0,
            'invoice_count': 0,
            'receipt_count': 0,
            'docs_with_invoices': 0,
            'recognition_rate': 0.0,
            'prompt_names': set()
        }
    
    # Extract field names
    field_names = set()
    for row in all_rows:
        for key in row.keys():
            if key.startswith('check_'):
                field_name = key[6:]  # Remove 'check_' prefix
                field_names.add(field_name)
    
    field_names = sorted(list(field_names))
    
    # Calculate field accuracy
    field_accuracy = {}
    total_correct_fields = 0
    for field in field_names:
        check_field = f'check_{field}'
        correct_count = sum(1 for row in all_rows if row.get(check_field, False))
        total_count = len(all_rows)
        field_accuracy[field] = round(correct_count / total_count * 100, 2) if total_count > 0 else 0.0
        total_correct_fields += correct_count
    
    # Calculate item-level accuracy
    correct_items = 0
    for row in all_rows:
        item_correct = True
        for field in field_names:
            check_field = f'check_{field}'
            if not row.get(check_field, False):
                item_correct = False
                break
        if item_correct:
            correct_items += 1
    
    item_accuracy = round(correct_items / len(all_rows) * 100, 2) if all_rows else 0.0
    
    # Calculate document-level accuracy
    documents = {}
    for row in all_rows:
        filename = row.get('filename', 'unknown')
        if filename not in documents:
            documents[filename] = []
        documents[filename].append(row)
    
    correct_documents = 0
    for filename, items in documents.items():
        document_correct = True
        for item in items:
            item_correct = True
            for field in field_names:
                check_field = f'check_{field}'
                if not item.get(check_field, False):
                    item_correct = False
                    break
            if not item_correct:
                document_correct = False
                break
        if document_correct:
            correct_documents += 1
    
    document_accuracy = round(correct_documents / len(documents) * 100, 2) if documents else 0.0
    
    # Overall field accuracy
    total_fields_compared = len(all_rows) * len(field_names)
    overall_field_accuracy = round(total_correct_fields / total_fields_compared * 100, 2) if total_fields_compared > 0 else 0.0
    
    # Calculate docType statistics if excel_data is provided
    only_other_docs = 0
    invoice_count = 0
    receipt_count = 0
    docs_with_invoices = 0
    prompt_names = set()
    
    if excel_data:
        for data in excel_data:
            # Collect prompt names
            prompt_names.add(data.get('prompt_name', 'N/A'))
            
            try:
                # Parse annotation data to analyze document types
                annotation_text = data['annotation_text']
                standard_documents = json.loads(annotation_text)
                
                if not isinstance(standard_documents, list):
                    continue
                
                # Analyze this file
                has_invoice_or_receipt = False
                file_invoice_count = 0
                file_receipt_count = 0
                
                for doc in standard_documents:
                    if isinstance(doc, dict):
                        doc_type = str(doc.get('docType', '')).lower().strip()
                        
                        if doc_type == 'invoice':
                            file_invoice_count += 1
                            has_invoice_or_receipt = True
                        elif doc_type == 'receipt':
                            file_receipt_count += 1
                            has_invoice_or_receipt = True
                
                # Update counters
                invoice_count += file_invoice_count
                receipt_count += file_receipt_count
                
                if has_invoice_or_receipt:
                    docs_with_invoices += 1
                else:
                    # Check if all documents are "other" type
                    all_other = True
                    for doc in standard_documents:
                        if isinstance(doc, dict):
                            doc_type = str(doc.get('docType', '')).lower().strip()
                            if doc_type and doc_type not in ['other', '']:
                                all_other = False
                                break
                    if all_other:
                        only_other_docs += 1
                        
            except (json.JSONDecodeError, KeyError, TypeError) as e:
                logger.warning(f"Error analyzing document types for file {data.get('filename', 'unknown')}: {e}")
                continue
    
    # Calculate recognition rate
    total_documents_count = len(documents)
    recognition_rate = round(docs_with_invoices / total_documents_count * 100, 2) if total_documents_count > 0 else 0.0
    
    return {
        'field_accuracy': field_accuracy,
        'invoice_accuracy': item_accuracy,  # Keep 'invoice' for compatibility
        'document_accuracy': document_accuracy,
        'total_invoices': len(all_rows),  # Keep 'invoices' for compatibility
        'total_documents': len(documents),
        'correct_invoices': correct_items,
        'correct_documents': correct_documents,
        'overall_field_accuracy': overall_field_accuracy,
        'only_other_docs': only_other_docs,
        'invoice_count': invoice_count,
        'receipt_count': receipt_count,
        'docs_with_invoices': docs_with_invoices,
        'recognition_rate': recognition_rate,
        'prompt_names': prompt_names
    }


def eval_documents(eval_list, project_config, model_version='N/A'):
    """
    Generic document evaluation function
    
    :param eval_list: Dictionary of filename -> (annotation_text, prediction_text, prompt_name)
    :param project_config: ProjectEvaluationConfig instance
    :param model_version: Model version string
    :return: Tuple of (excel_path, all_rows, statistics)
    """
    logger.info(f"Starting document evaluation, available documents: {len(eval_list)}")
    
    # Get comparison fields from project configuration
    # Always use effective_required_fields for evaluation, not default_fields
    # This ensures evaluation only uses the required fields defined in the configuration
    compare_fields = project_config.effective_required_fields
    logger.info(f"Using effective_required_fields for evaluation: {compare_fields}")
    
    # Log project config for debugging if available
    if hasattr(project_config, 'project'):
        project = project_config.project
    if hasattr(project, 'evaluation_field_config') and project.evaluation_field_config:
        default_fields = project.evaluation_field_config.get('default_fields', [])
        logger.info(f"Project has default_fields: {default_fields}, but using required_fields for evaluation")
    
    if not compare_fields:
        logger.error("No comparison fields available for evaluation")
        return None, [], {}
    
    results = []
    excel_data = []
    
    # Process each document
    for i, (filename, (annotation_text, prediction_text, prompt_name)) in enumerate(eval_list.items(), 1):
        # Post-process prediction data
        prediction_text_processed = post_process_documents(prediction_text, project_config.evaluation_config)
        
        # Filter to keep only comparison fields
        annotation_text_filtered = filter_json_by_fields(annotation_text, compare_fields)
        prediction_text_filtered = filter_json_by_fields(prediction_text_processed, compare_fields)
        
        # Perform comparison
        result = compare_documents_with_comparer(
            annotation_text_filtered,
            prediction_text_filtered,
            compare_fields,
            project_config
        )

        obj = {"id": filename, "result": result}
        results.append(obj)

        excel_data.append({
            'filename': filename,
            'annotation_text': annotation_text_filtered,
            'prediction_text': prediction_text_filtered,
            'result': result,
            'prompt_name': prompt_name
        })

    if not results:
        logger.warning("No results available for evaluation")
        return None, [], {}
    
    # Generate detailed rows for statistics
    all_rows = []
    for data in excel_data:
        filename = data['filename']
        annotation_text = data['annotation_text']
        prediction_text = data['prediction_text']
        result = data['result']
        prompt_name = data['prompt_name']
        
        try:
            standard_documents = json.loads(annotation_text)
            prediction_documents = json.loads(prediction_text)
        except json.JSONDecodeError as e:
            logger.error(f"JSON parsing failed for {filename}: {e}")
            continue
            
        eval_settings = getattr(project_config, 'evaluation_settings', {})
        comparer = InvoiceComparer(
            core_fields=compare_fields, 
            verbose=False,
            name_overlap_threshold=eval_settings.get('name_overlap_threshold', 0.5)
        )
        
        file_rows = process_comparison_results(
            filename, standard_documents, prediction_documents, 
            result, compare_fields, comparer, prompt_name, project_config
        )
        all_rows.extend(file_rows)
    
    # Calculate statistics
    statistics = calculate_evaluation_statistics(all_rows, excel_data)
    statistics['model_version'] = model_version
    
    # Generate Excel report
    excel_path, _ = generate_excel_report(excel_data, compare_fields, statistics, project_config)
    
    # Add Annotations and Predictions sheets to the Excel report
    try:
        project_id = getattr(project_config, 'project', None)
        project_id = getattr(project_id, 'id', None) if project_id else None
        excel_path = add_annotations_predictions_to_excel(excel_path, eval_list, project_id)
        logger.info(f"Successfully added Annotations and Predictions sheets to Excel report")
    except Exception as e:
        logger.warning(f"Failed to add Annotations and Predictions sheets: {e}")
    
    # Return tuple as expected by the calling function
    return excel_path, all_rows, statistics


def filter_predictions_by_criteria(task_predictions, prompt_filter, model_filter):
    """
    Filter predictions based on the filter criteria
    
    :param task_predictions: QuerySet of predictions for a task
    :param prompt_filter: Prompt name to filter by (empty string for no filter)
    :param model_filter: Model version to filter by (empty string for no filter)
    :return: Filtered prediction or None
    """
    original_count = task_predictions.count()
    logger.debug(f"Starting with {original_count} predictions for task")
    
    # Log all available predictions for debugging
    if logger.isEnabledFor(logging.DEBUG):
        for pred in task_predictions:
            logger.debug(f"Available prediction: prompt_name='{pred.prompt_name}', model_version='{pred.model_version}', id={pred.id}")
    
    filtered = task_predictions
    
    # Apply prompt filter if specified
    if prompt_filter:
        logger.debug(f"Applying prompt filter: '{prompt_filter}'")
        filtered = filtered.filter(prompt_name=prompt_filter)
        logger.debug(f"After prompt filter: {filtered.count()} predictions remaining")
    
    # Apply model version filter if specified
    if model_filter:
        logger.debug(f"Applying model version filter: '{model_filter}'")
        filtered = filtered.filter(model_version=model_filter)
        logger.debug(f"After model version filter: {filtered.count()} predictions remaining")
    
    # Return the latest matching prediction
    result = filtered.last() if filtered.exists() else None
    if result:
        logger.debug(f"Selected prediction: prompt_name='{result.prompt_name}', model_version='{result.model_version}', id={result.id}")
    else:
        logger.debug("No predictions matched the filter criteria")
    
    return result


def get_last_value(task_ann_preds):
    """Get the last value from queryset or result list"""
    ann_pred_list = list(task_ann_preds)
    if not ann_pred_list:
        return ""
    
    # Get the last item (which should be a result list)
    last_result = ann_pred_list[-1]
    
    # Handle the case where last_result is a list of result dictionaries
    if isinstance(last_result, list) and len(last_result) > 0:
        # Find the first item that has the expected structure
        for item in last_result:
            if isinstance(item, dict) and 'value' in item and 'text' in item['value']:
                text_list = item['value']['text']
                if text_list and len(text_list) > 0:
                    return text_list[-1]  # Return the last text item
    
    return ""


def evaluate_document_extraction_task(project, queryset, **kwargs):
    """
    Generic document extraction evaluation entry point
    
    This function replaces the invoice-specific evaluation and works with any document type
    based on the project's evaluation field configuration.
    """
    logger.info(f"Starting document extraction evaluation, project ID: {project.id}, task count: {queryset.count()}")
    
    # Get filter criteria from form data
    # First try to get from kwargs (direct parameter passing)
    prompt_filter = kwargs.get('prompt_filter', '')
    model_filter = kwargs.get('model_filter', '')
    
    # If not found in kwargs, try to get from request.data (form submission)
    if 'request' in kwargs and hasattr(kwargs['request'], 'data'):
        request_data = kwargs['request'].data
        if not prompt_filter:
            prompt_filter = request_data.get('prompt_filter', '')
        if not model_filter:
            model_filter = request_data.get('model_filter', '')
    
    logger.info(f"Using prediction filters - prompt: '{prompt_filter}', model: '{model_filter}'")
    logger.info(f"Raw kwargs received: {kwargs}")
    
    # Also log request.data if available
    if 'request' in kwargs and hasattr(kwargs['request'], 'data'):
        logger.info(f"Request data: {kwargs['request'].data}")
    
    # Get project evaluation configuration
    project_config = get_project_evaluation_config(project)
    
    # Note: Form no longer allows config selection, using project's current configuration
    logger.info(f"Using project's current evaluation configuration: {project_config.evaluation_config.name}")
    
    # Get tasks with both annotations and predictions
    tasks_with_both = queryset.filter(
        annotations__isnull=False,
        predictions__isnull=False
    ).distinct()
    
    logger.info(f"Found {tasks_with_both.count()} tasks with both annotations and predictions")
    
    # Collect annotation and prediction data
    results = {}
    model_version = 'N/A'
    processed_tasks = 0
    skipped_tasks = 0
    
    for task in tasks_with_both:
        # Get completed annotations
        task_annotations = task.annotations.filter(
            was_cancelled=False
        ).values_list('result', flat=True)
        
        # Get prediction objects
        task_predictions = task.predictions.all()
        
        if task_annotations and task_predictions:
            # Get last annotation as ground truth
            ann_text = get_last_value(task_annotations)
            
            # Apply prediction filtering
            selected_prediction = filter_predictions_by_criteria(task_predictions, prompt_filter, model_filter)
            
            if selected_prediction:
                pred_text = get_last_value([selected_prediction.result])
                
                # Extract model version
                if model_version == 'N/A' and hasattr(selected_prediction, 'model_version'):
                    model_version = selected_prediction.model_version or 'N/A'
                
                # Extract prompt name
                prompt_name = getattr(selected_prediction, 'prompt_name', 'N/A')
                
                task_data_dict = getattr(task, 'data', {})

                if 'filename' in task_data_dict:
                    filename = task_data_dict['filename']
                    results[filename] = (ann_text, pred_text, prompt_name)
                    processed_tasks += 1
                    logger.debug(f"Processed task {task.id} with filename {filename}")
                else:
                    task_id = getattr(task, 'id', 'NO_ID')
                    logger.error(f"Task {task_id} missing filename, skipping")
                    skipped_tasks += 1
            else:
                task_id = getattr(task, 'id', 'NO_ID')
                logger.warning(f"Task {task_id} has no predictions matching filter criteria: prompt='{prompt_filter}', model='{model_filter}'")
                skipped_tasks += 1

    # Log final processing summary
    logger.info(f"Task processing summary: {processed_tasks} processed, {skipped_tasks} skipped, {len(results)} total results")
    
    # Perform evaluation
    excel_path, all_rows, statistics = eval_documents(results, project_config, model_version=model_version)
    
    # Get the actual fields used in evaluation (effective required fields from project config)
    # Always use effective_required_fields to match the evaluation logic
    actual_fields_used = project_config.effective_required_fields
    logger.info(f"Actual fields used in evaluation: {actual_fields_used}")
    
    # Log project config for debugging if available
    if hasattr(project, 'evaluation_field_config') and project.evaluation_field_config:
        default_fields = project.evaluation_field_config.get('default_fields', [])
        logger.info(f"Project has default_fields: {default_fields}, but using required_fields for evaluation")
    
    # Build evaluation summary
    evaluation_summary = {
        'project_id': project.id,
        'evaluated_at': datetime.now().isoformat(),
        'task_count': len(results),
        'evaluation_type': 'document_extraction',
        'evaluation_config': {
            'name': project_config.evaluation_config.name,
            'key': project_config.evaluation_config.key,
            'fields': actual_fields_used  # Use actual fields used, not all possible fields
        },
        'excel_path': excel_path,
        'statistics': statistics
    }
    
    # Build detailed description based on filter criteria
    filter_description = ""
    if prompt_filter or model_filter:
        filter_parts = []
        if prompt_filter:
            filter_parts.append(f"prompt: {prompt_filter}")
        if model_filter:
            filter_parts.append(f"model: {model_filter}")
        filter_description = f" (filtered by {', '.join(filter_parts)})"
    
    return {
        'processed_items': len(results),
        'detail': f'{len(results)} tasks evaluated using {project_config.evaluation_config.name} configuration{filter_description}',
        'evaluation_type': 'document_extraction',
        'evaluation_results': evaluation_summary
    }


def create_evaluation_form(user, project):
    """
    Create form for evaluation action with prediction filtering options
    """
    # Prepare separate options for prompt and model version
    prompt_options = [{'value': '', 'label': 'Any Prompt'}]
    model_options = [{'value': '', 'label': 'Any Model Version'}]
    help_text = 'Select filters to apply'
    
    try:
        # Get all tasks with both annotations and predictions for this project
        all_tasks_with_both = Task.objects.filter(
            project=project,
            annotations__isnull=False,
            predictions__isnull=False
        ).distinct()
        
        if all_tasks_with_both.exists():
            options = get_available_prediction_options(project, all_tasks_with_both)
            
            # Add prompt name options
            for prompt_name in options['prompt_names']:
                prompt_options.append({'value': prompt_name, 'label': prompt_name})
            
            # Add model version options  
            for model_version in options['model_versions']:
                model_options.append({'value': model_version, 'label': model_version})
            
            help_text = f'Select filters to apply. Project has {options["total_predictions"]} predictions in {options["total_tasks"]} tasks.'
        else:
            help_text = 'No tasks with both annotations and predictions found in this project.'
            
    except Exception as e:
        # Fall back to default options if there's an error
        logger.warning(f"Error getting prediction options: {e}")
        help_text = 'Error loading prediction options. Using default settings.'
    
    # Return form field configuration in Label Studio format with two separate dropdowns
    return [
        {
            'columnCount': 1,
            'fields': [
                {
                    'type': 'select',
                    'name': 'prompt_filter',
                    'label': 'Prompt Filter',
                    'options': prompt_options,
                    'value': '',
                    'help_text': 'Filter by prompt name (optional)'
                }
            ],
        },
        {
            'columnCount': 1,
            'fields': [
                {
                    'type': 'select',
                    'name': 'model_filter',
                    'label': 'Model Version Filter',
                    'options': model_options,
                    'value': '',
                    'help_text': 'Filter by model version (optional)'
                }
            ],
        }
    ]


def preview_evaluation_filter(project, queryset, **kwargs):
    """
    预览过滤条件影响的任务数量，不执行实际评估
    """
    logger.info(f"Starting evaluation filter preview, project ID: {project.id}")
    
    # Get filter criteria from form data (same logic as main evaluation)
    prompt_filter = kwargs.get('prompt_filter', '')
    model_filter = kwargs.get('model_filter', '')
    
    # If not found in kwargs, try to get from request.data (form submission)
    if 'request' in kwargs and hasattr(kwargs['request'], 'data'):
        request_data = kwargs['request'].data
        if not prompt_filter:
            prompt_filter = request_data.get('prompt_filter', '')
        if not model_filter:
            model_filter = request_data.get('model_filter', '')
    
    logger.info(f"Preview filters - prompt: '{prompt_filter}', model: '{model_filter}'")
    
    # Get tasks with both annotations and predictions
    tasks_with_both = queryset.filter(
        annotations__isnull=False,
        predictions__isnull=False
    ).distinct()
    
    total_tasks = tasks_with_both.count()
    matching_tasks = 0
    sample_filenames = []
    
    for task in tasks_with_both:
        # Get prediction objects
        task_predictions = task.predictions.all()
        
        # Apply prediction filtering using the same logic as main evaluation
        selected_prediction = filter_predictions_by_criteria(task_predictions, prompt_filter, model_filter)
        
        if selected_prediction:
            matching_tasks += 1
            # Collect some sample filenames for preview
            if len(sample_filenames) < 3:
                filename = task.data.get('filename', f'Task {task.id}')
                sample_filenames.append(filename)
    
    skipped_tasks = total_tasks - matching_tasks
    
    # Build filter summary
    filter_parts = []
    if prompt_filter:
        filter_parts.append(f"prompt: '{prompt_filter}'")
    if model_filter:
        filter_parts.append(f"model: '{model_filter}'")
    
    filter_summary = f"Filters: {', '.join(filter_parts)}" if filter_parts else "No filters applied"
    
    # Create detailed message
    if matching_tasks == 0:
        detail_message = f"⚠️ No tasks match the filter criteria. All {total_tasks} tasks will be skipped."
    elif matching_tasks == total_tasks:
        detail_message = f"✅ All {total_tasks} tasks match the filter criteria. All will be processed."
    else:
        detail_message = f"📊 {matching_tasks} out of {total_tasks} tasks match the filter criteria. {skipped_tasks} tasks will be skipped."
        
    if sample_filenames:
        detail_message += f"\n\nSample matching files: {', '.join(sample_filenames)}"
        if matching_tasks > len(sample_filenames):
            detail_message += f" (and {matching_tasks - len(sample_filenames)} more...)"
    
    result = {
        'total_tasks_with_data': total_tasks,
        'matching_tasks': matching_tasks,
        'skipped_tasks': skipped_tasks,
        'filter_summary': filter_summary,
        'sample_filenames': sample_filenames,
        'detail': detail_message,
        'processed_items': 0,  # This is preview only, no actual processing
        'evaluation_type': 'preview'
    }
    
    logger.info(f"Preview result: {matching_tasks}/{total_tasks} tasks match criteria")
    
    return result


# Register document extraction evaluation action
actions = [
    {
        'id': 'evaluate_document_extraction_task',
        'entry_point': evaluate_document_extraction_task,
        'permission': all_permissions.predictions_any,
        'title': 'Evaluate Document Extraction',
        'order': 202,
        'dialog': {
            'text': 'This evaluation will compare annotation and prediction results for accuracy. The evaluation will use the current project configuration. To change evaluation fields, configure them in Project Settings > General Settings.',
            'type': 'confirm',
            'form': create_evaluation_form,
        },
    },
    {
        'id': 'preview_document_evaluation_filter',
        'entry_point': preview_evaluation_filter,
        'permission': all_permissions.predictions_any,
        'title': 'Preview Evaluation Filter',
        'order': 201,
        'dialog': {
            'text': 'Preview how many tasks will be affected by your filter criteria.',
            'type': 'confirm',
            'form': create_evaluation_form,
        },
    },
]


def evaluate_documents(queryset, project, **kwargs):
    """
    Main entry point for document evaluation
    This function provides a generic interface that can be used by tests and external calls
    """
    return evaluate_document_extraction_task(project, queryset, **kwargs) 
import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from core.permissions import AllPermissions
from django.db.models import Q, Count
from tasks.models import Task, Annotation, Prediction
from evaluation_configs.models import EvaluationFieldConfig, ProjectEvaluationConfig
from .invoice_compare.invoice_compare_utils import InvoiceComparer
import os
import tempfile
import pandas as pd


all_permissions = AllPermissions()
logger = logging.getLogger(__name__)


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
                    
                    # Use configured fields from project if available, otherwise use config defaults
                    default_fields = project_eval_config.get('default_fields', config.required_fields)
                    
                    # Create a temporary ProjectEvaluationConfig for consistency
                    return type('ProjectEvaluationConfig', (), {
                        'project': project,
                        'evaluation_config': config,
                        'effective_required_fields': default_fields,
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
    
    :param json_text: JSON array string
    :param fields: List of fields to keep
    :return: Filtered JSON array string
    """
    try:
        data = json.loads(json_text)
        if not isinstance(data, list):
            raise ValueError("Input JSON must be a list of dicts")
        filtered = [
            {k: v for k, v in item.items() if k in fields}
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
    
    # Process matched documents
    if result.get('matched_count', 0) > 0:
        remaining_predictions = list(range(len(prediction_documents)))
        
        for std_doc in standard_documents:
            # Check document type if needed
            if need_doc_type_check:
                std_doc_type = (std_doc.get('docType') or '').lower()
                if std_doc_type not in allowed_doc_types:
                    continue
                
            found_idx = -1
            matched_pred_doc = None
            
            # Find matching prediction document
            for i, pred_idx in enumerate(remaining_predictions):
                pred_doc = prediction_documents[pred_idx]
                is_equal, _ = comparer.invoices_equal(std_doc, pred_doc)
                
                if is_equal:
                    found_idx = i
                    matched_pred_doc = pred_doc
                    remaining_predictions.pop(found_idx)
                    break
            
            if matched_pred_doc:
                # Create data row
                row = {'filename': filename, 'prompt_name': prompt_name}
                
                # Add field values and comparison results
                for field in compare_fields:
                    std_value = std_doc.get(field, '')
                    pred_value = matched_pred_doc.get(field, '')
                    
                    # For matched documents, all fields should match
                    check_result = True
                    
                    row[f'std_{field}'] = std_value
                    row[f'pred_{field}'] = pred_value
                    row[f'check_{field}'] = check_result
                
                rows.append(row)
    
    # Process unmatched documents
    for unmatched_item in result.get('unmatched', []):
        std_doc = unmatched_item['standard']
        pred_doc = unmatched_item['prediction']
        
        # Check document type if needed
        if need_doc_type_check:
            std_doc_type = (std_doc.get('docType') or '').lower()
            if std_doc_type not in allowed_doc_types:
                continue
        
        row = {'filename': filename, 'prompt_name': prompt_name}
        
        for field in compare_fields:
            std_value = std_doc.get(field, '')
            pred_value = pred_doc.get(field, '')
            
            # Check if field is in diff_fields
            diff_fields = unmatched_item.get('diff_fields', [])
            check_result = field not in diff_fields
            
            row[f'std_{field}'] = std_value
            row[f'pred_{field}'] = pred_value
            row[f'check_{field}'] = check_result
        
        rows.append(row)
    
    # Process documents only in standard
    for std_doc in result.get('only_in_standard', []):
        # Check document type if needed
        if need_doc_type_check:
            std_doc_type = (std_doc.get('docType') or '').lower()
            if std_doc_type not in allowed_doc_types:
                continue
            
        row = {'filename': filename, 'prompt_name': prompt_name}
        
        for field in compare_fields:
            std_value = std_doc.get(field, '')
            
            row[f'std_{field}'] = std_value
            row[f'pred_{field}'] = ''  # No corresponding prediction
            row[f'check_{field}'] = False  # Missing document is considered mismatch
        
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
    
    # Create InvoiceComparer with configuration
    # Only use supported parameters: core_fields, verbose, name_overlap_threshold
    comparer = InvoiceComparer(
        core_fields=compare_fields, 
        verbose=False,
        name_overlap_threshold=eval_settings.get('name_overlap_threshold', 0.5)
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

    # Create column order
    columns = ['filename', 'prompt_name']
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
    """Create statistics sheet with evaluation configuration info"""
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
        
        # Get field label if available
        field_labels = getattr(evaluation_config.evaluation_config, 'field_labels', {})
        field_label = field_labels.get(field, field)
        
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


def calculate_evaluation_statistics(all_rows):
    """Calculate evaluation statistics from comparison results"""
    if not all_rows:
        return {
            'field_accuracy': {},
            'invoice_accuracy': 0.0,
            'document_accuracy': 0.0,
            'total_invoices': 0,
            'total_documents': 0
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
    
    return {
        'field_accuracy': field_accuracy,
        'invoice_accuracy': item_accuracy,  # Keep 'invoice' for compatibility
        'document_accuracy': document_accuracy,
        'total_invoices': len(all_rows),  # Keep 'invoices' for compatibility
        'total_documents': len(documents),
        'correct_invoices': correct_items,
        'correct_documents': correct_documents,
        'overall_field_accuracy': overall_field_accuracy
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
    # Use only the predefined fields from project's evaluation_field_config
    compare_fields = []
    
    # Get the project instance to access evaluation_field_config
    # project_config might be a ProjectEvaluationConfig or a direct project reference
    if hasattr(project_config, 'project'):
        project = project_config.project
    else:
        # project_config might be the project itself in some cases
        project = project_config
    
    if hasattr(project, 'evaluation_field_config') and project.evaluation_field_config:
        default_fields = project.evaluation_field_config.get('default_fields', [])
        if default_fields:
            compare_fields = default_fields
            logger.info(f"Using predefined fields from project config: {compare_fields}")
        else:
            # Fallback to effective required fields if no default_fields specified
            compare_fields = project_config.effective_required_fields
            logger.info(f"No default_fields found, using effective_required_fields: {compare_fields}")
    else:
        # Fallback to effective required fields if no project config
        compare_fields = project_config.effective_required_fields
        logger.info(f"No project evaluation_field_config found, using effective_required_fields: {compare_fields}")
    
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
    statistics = calculate_evaluation_statistics(all_rows)
    statistics['model_version'] = model_version
    
    # Generate Excel report
    excel_path, _ = generate_excel_report(excel_data, compare_fields, statistics, project_config)
    
    return excel_path, all_rows, statistics


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
    
    # Get project evaluation configuration
    project_config = get_project_evaluation_config(project)
    
    # Handle user form data if provided
    request = kwargs.get('request')
    if request and hasattr(request, 'data'):
        form_data = request.data or {}
        config_id = form_data.get('evaluation_config_id')
        
        if config_id:
            try:
                new_config = EvaluationFieldConfig.objects.get(id=config_id)
                # Update project configuration
                if hasattr(project_config, 'evaluation_config'):
                    project_config.evaluation_config = new_config
                else:
                    # Create new ProjectEvaluationConfig
                    project_config, created = ProjectEvaluationConfig.objects.get_or_create(
                        project=project,
                        defaults={'evaluation_config': new_config}
                    )
                    if not created:
                        project_config.evaluation_config = new_config
                        project_config.save()
                
                logger.info(f"Using evaluation configuration: {new_config.name}")
            except EvaluationFieldConfig.DoesNotExist:
                logger.warning(f"Evaluation config {config_id} not found, using project default")
    
    # Get tasks with both annotations and predictions
    tasks_with_both = queryset.filter(
        annotations__isnull=False,
        predictions__isnull=False
    ).distinct()
    
    # Collect annotation and prediction data
    results = {}
    model_version = 'N/A'
    
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
            
            # Get last prediction
            last_prediction = task_predictions.last()
            pred_text = get_last_value([last_prediction.result])
            
            # Extract model version
            if model_version == 'N/A' and hasattr(last_prediction, 'model_version'):
                model_version = last_prediction.model_version or 'N/A'
            
            # Extract prompt name
            prompt_name = getattr(last_prediction, 'prompt_name', 'N/A')
            
            task_data_dict = getattr(task, 'data', {})

            if 'filename' in task_data_dict:
                filename = task_data_dict['filename']
                results[filename] = (ann_text, pred_text, prompt_name)
            else:
                task_id = getattr(task, 'id', 'NO_ID')
                logger.error(f"Task {task_id} missing filename, skipping")

    # Perform evaluation
    excel_path, all_rows, statistics = eval_documents(results, project_config, model_version=model_version)
    
    # Get the actual fields used in evaluation (predefined fields from project config)
    actual_fields_used = []
    if hasattr(project, 'evaluation_field_config') and project.evaluation_field_config:
        default_fields = project.evaluation_field_config.get('default_fields', [])
        if default_fields:
            actual_fields_used = default_fields
        else:
            actual_fields_used = project_config.effective_required_fields
    else:
        actual_fields_used = project_config.effective_required_fields
    
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
    
    return {
        'processed_items': len(results),
        'detail': f'{len(results)} tasks evaluated using {project_config.evaluation_config.name} configuration',
        'evaluation_type': 'document_extraction',
        'evaluation_results': evaluation_summary
    }


def create_evaluation_form(user, project):
    """
    Create form for evaluation action with dynamic evaluation configurations
    """
    # Get available evaluation configurations
    available_configs = EvaluationFieldConfig.objects.filter(
        is_active=True
    ).order_by('name')
    
    # Get current project configuration
    current_config = get_project_evaluation_config(project)
    current_config_id = getattr(current_config.evaluation_config, 'id', None)
    
    # Build options
    options = []
    for config in available_configs:
        options.append({
            'value': str(config.id),
            'label': f'{config.name} - {config.description}'
        })
    
    fields = [
        {
            'type': 'select',
            'name': 'evaluation_config_id',
            'label': 'Evaluation Configuration',
            'value': str(current_config_id) if current_config_id else '',
            'options': options,
            'description': 'Select the evaluation configuration to use for this assessment'
        }
    ]
    
    return [
        {
            'columnCount': 1,
            'fields': fields
        }
    ]


# Register document extraction evaluation action
document_actions = [
    {
        'entry_point': evaluate_document_extraction_task,
        'permission': all_permissions.predictions_any,
        'title': 'Evaluate Document Extraction',
        'order': 202,
        'dialog': {
            'text': 'This evaluation will compare annotation and prediction results for accuracy. If multiple versions exist, the latest will be used. You can select the evaluation configuration and document type.',
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
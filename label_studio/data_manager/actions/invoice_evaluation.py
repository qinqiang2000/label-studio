import logging
import json
from datetime import datetime
from typing import Dict, List, Any, Optional
from decimal import Decimal, InvalidOperation
from difflib import SequenceMatcher

from core.permissions import AllPermissions
from django.db.models import Q, Count
from tasks.models import Task, Annotation, Prediction
from .invoice_compare.invoice_compare_utils import InvoiceComparer
import os
import tempfile
import pandas as pd


all_permissions = AllPermissions()
logger = logging.getLogger(__name__)

def post_process_invoices(invoices_data):
    """
    后处理发票数据，为缺少totalTaxAmount字段的发票添加该字段
    通过累加detailOfTaxSummary中的tax值来计算totalTaxAmount
    
    :param invoices_data: 发票数据，可以是JSON字符串或已解析的列表
    :return: 处理后的发票数据（与输入格式相同）
    """
    # 判断输入是字符串还是已解析的数据
    is_string_input = isinstance(invoices_data, str)
    
    try:
        # 如果是字符串，先解析
        if is_string_input:
            data = json.loads(invoices_data)
        else:
            data = invoices_data
            
        # 确保data是列表
        if not isinstance(data, list):
            print(f"Warning: invoices_data should be a list, got {type(data)}")
            return invoices_data
            
        # 遍历每个发票元素
        for invoice in data:
            if not isinstance(invoice, dict):
                continue
                
            # 检查是否已经有totalTaxAmount字段
            if "totalTaxAmount" in invoice:
                continue
                
            # 从detailOfTaxSummary中累加tax值
            detail_of_tax_summary = invoice.get("detailOfTaxSummary", [])
            total_tax = 0
            
            if isinstance(detail_of_tax_summary, list):
                for tax_item in detail_of_tax_summary:
                    if isinstance(tax_item, dict) and "tax" in tax_item:
                        tax_value = tax_item["tax"]
                        # 确保tax值是数字
                        if isinstance(tax_value, (int, float)):
                            total_tax += tax_value
                        elif isinstance(tax_value, str):
                            try:
                                total_tax += float(tax_value)
                            except ValueError:
                                print(f"Warning: invalid tax value '{tax_value}' in invoice")
                                
            # 添加totalTaxAmount字段
            invoice["totalTaxAmount"] = total_tax
            
        # 返回与输入格式相同的数据
        if is_string_input:
            return json.dumps(data, ensure_ascii=False, indent=2)
        else:
            return data
            
    except json.JSONDecodeError as e:
        print(f"Error parsing JSON: {e}")
        return invoices_data
    except Exception as e:
        print(f"Error in post_process_invoices: {e}")
        return invoices_data

def filter_json_by_fields(json_text: str, fields: List[str]) -> str:
    """
    过滤 json_text（json数组字符串）中的每个对象，只保留 fields 字段。
    :param json_text: json数组字符串
    :param fields: 需要保留的字段列表
    :return: 过滤后的json数组字符串
    """
    try:
        _data = json.loads(json_text)
        if not isinstance(_data, list):
            raise ValueError("Input JSON must be a list of dicts")
        filtered = [
            {k: v for k, v in item.items() if k in fields}
            for item in _data if isinstance(item, dict)
        ]
        return json.dumps(filtered, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"filter_json_by_fields error: {e}")
        return json_text  # fallback to original


def process_comparison_results(filename: str, standard_invoices: List[dict], 
                             prediction_invoices: List[dict], result: dict, 
                             compare_fields: List[str], comparer) -> List[dict]:
    """
    处理比对结果，生成Excel行数据
    只处理docType为'invoice'或'receipt'的票据
    """
    rows = []
    
    # 有效的文档类型
    valid_doc_types = {'invoice', 'receipt'}
    
    # 处理matched的票据
    if result.get('matched_count', 0) > 0:
        remaining_predictions = list(range(len(prediction_invoices)))
        
        for std_invoice in standard_invoices:
            # 只处理有效docType的票据
            std_doc_type = (std_invoice.get('docType') or '').lower()
            if std_doc_type not in valid_doc_types:
                continue
                
            found_idx = -1
            matched_pred_invoice = None
            
            # 寻找匹配的预测票据
            for i, pred_idx in enumerate(remaining_predictions):
                pred_invoice = prediction_invoices[pred_idx]
                is_equal, _ = comparer.invoices_equal(std_invoice, pred_invoice)
                
                if is_equal:
                    found_idx = i
                    matched_pred_invoice = pred_invoice
                    remaining_predictions.pop(found_idx)
                    break
            
            if matched_pred_invoice:
                # 创建数据行
                row = {'filename': filename}
                
                # 添加每个字段的标准值、预测值和检查结果
                for field in compare_fields:
                    std_value = std_invoice.get(field, '')
                    pred_value = matched_pred_invoice.get(field, '')
                    
                    # 使用invoices_equal方法结果来确定每个字段是否匹配
                    # 对于matched的票据，所有字段都应该匹配
                    check_result = True
                    
                    row[f'std_{field}'] = std_value
                    row[f'pred_{field}'] = pred_value
                    row[f'check_{field}'] = check_result
                
                rows.append(row)
    
    # 处理unmatched的票据
    for unmatched_item in result.get('unmatched', []):
        std_invoice = unmatched_item['standard']
        pred_invoice = unmatched_item['prediction']
        
        # 只处理有效docType的票据
        std_doc_type = (std_invoice.get('docType') or '').lower()
        if std_doc_type not in valid_doc_types:
            continue
        
        row = {'filename': filename}
        
        for field in compare_fields:
            std_value = std_invoice.get(field, '')
            pred_value = pred_invoice.get(field, '')
            
            # 检查是否在diff_fields中
            diff_fields = unmatched_item.get('diff_fields', [])
            check_result = field not in diff_fields
            
            row[f'std_{field}'] = std_value
            row[f'pred_{field}'] = pred_value
            row[f'check_{field}'] = check_result
        
        rows.append(row)
    
    # 处理only_in_standard的票据
    for std_invoice in result.get('only_in_standard', []):
        # 只处理有效docType的票据
        std_doc_type = (std_invoice.get('docType') or '').lower()
        if std_doc_type not in valid_doc_types:
            continue
            
        row = {'filename': filename}
        
        for field in compare_fields:
            std_value = std_invoice.get(field, '')
            
            row[f'std_{field}'] = std_value
            row[f'pred_{field}'] = ''  # 预测中没有对应票据
            row[f'check_{field}'] = False  # 缺失票据视为不匹配
        
        rows.append(row)
    
    return rows

def compare_invoices_with_comparer(annotation_text_filtered, prediction_text_filtered, compare_fields):
    """
    使用InvoiceComparer对比单个文件的票据数据
    :param annotation_text_filtered: 过滤后的标注数据（JSON字符串）
    :param prediction_text_filtered: 过滤后的预测数据（JSON字符串）
    :param compare_fields: 比对字段列表
    :return: 比对结果
    """
    # 创建InvoiceComparer实例
    comparer = InvoiceComparer(core_fields=compare_fields, verbose=False)
    
    try:
        # 调用InvoiceComparer进行票据比对
        result = comparer.compare_invoices(annotation_text_filtered, prediction_text_filtered)
                
        return result
        
    except Exception as e:
        print(f"InvoiceComparer比对出错: {e}")
        return {
            "error": str(e),
            "matched_count": 0,
            "unmatched_count": 0,
            "only_in_standard_count": 0,
            "only_in_prediction_count": 0,
            "invoice_accuracy": 0.0,
            "field_accuracy": 0.0
        }

def _create_overview_section(statistics):
    """
    创建总览部分的数据
    """
    return [
        ['总览'],
        ['总文档数:', statistics['total_documents']],
        ['总票据数:', statistics['total_invoices']],
        ['总字段数:', statistics['total_invoices'] * len(statistics['field_accuracy'])],
        ['模型版本:', statistics.get('model_version', 'N/A')],
        ['评估时间:', datetime.now().strftime('%Y-%m-%d %H:%M:%S')],
        ['']  # 空行
    ]

def _create_overall_metrics_section(statistics):
    """
    创建整体指标部分的数据
    """
    return [
        ['整体指标'],
        ['文档准确率:', f"{statistics['document_accuracy']}%"],
        ['票据准确率:', f"{statistics['invoice_accuracy']}%"],
        ['']  # 空行
    ]

def _create_field_metrics_section(statistics, compare_fields):
    """
    创建字段指标部分的数据
    """
    stats_data = [
        ['核心字段指标'],
        ['字段名称', '总样本数', '正确数', '识别正确率']
    ]
    
    # 添加每个字段的统计数据
    total_correct = 0
    for field in compare_fields:
        field_stats = statistics['field_accuracy'].get(field, 0)
        correct_count = round(statistics['total_invoices'] * field_stats / 100)
        total_correct += correct_count
        stats_data.append([
            field,
            statistics['total_invoices'],
            correct_count,
            f"{field_stats}%"
        ])
    
    # 添加总计行
    total_accuracy = round(total_correct / (statistics['total_invoices'] * len(compare_fields)) * 100, 2)
    stats_data.append([
        '总计',
        statistics['total_invoices'] * len(compare_fields),
        total_correct,
        f"{total_accuracy}%"
    ])
    
    return stats_data

def _create_statistics_sheet(writer, statistics, compare_fields):
    """
    创建统计sheet
    """
    # 合并所有统计数据
    stats_data = []
    stats_data.extend(_create_overview_section(statistics))
    stats_data.extend(_create_overall_metrics_section(statistics))
    stats_data.extend(_create_field_metrics_section(statistics, compare_fields))
    
    # 创建统计DataFrame并写入
    stats_df = pd.DataFrame(stats_data)
    stats_df.to_excel(writer, sheet_name='Statistics', index=False, header=False)
    
    # 调整列宽
    worksheet = writer.sheets['Statistics']
    for idx, col in enumerate(stats_df.columns):
        max_length = max(
            stats_df[col].astype(str).apply(len).max(),
            len(str(col))
        )
        worksheet.column_dimensions[chr(65 + idx)].width = max_length + 2

def _create_details_sheet(writer, all_rows, columns):
    """
    创建详情sheet
    """
    if all_rows:
        df = pd.DataFrame(all_rows, columns=columns)
        df.to_excel(writer, sheet_name='Details', index=False)
    else:
        df = pd.DataFrame(columns=columns)
        print("Excel报告已生成，无数据但创建了空工作表")
    
    df.to_excel(writer, sheet_name='Invoice_Details', index=False)

def generate_excel_report(excel_data, compare_fields, statistics):
    """
    生成Excel报告，包含票据比对结果
    
    Args:
        excel_data: 包含比对数据的列表，每个元素包含filename、annotation_text、prediction_text和result
        compare_fields: 需要比对的字段列表
        statistics: 统计数据（已算好）
    
    Returns:
        tuple: (excel_output_path, all_rows)
            - excel_output_path: 生成的Excel文件路径
            - all_rows: 所有比对结果数据
    """
    # 创建临时文件，使用.xlsx后缀
    temp_fd, excel_output_path = tempfile.mkstemp(suffix='.xlsx')
    os.close(temp_fd)  # 关闭文件描述符

    # 创建列顺序
    columns = ['filename']
    for field in compare_fields:
        columns.extend([f'std_{field}', f'pred_{field}', f'check_{field}'])
    
    all_rows = []
    
    try:
        # 处理数据
        for data in excel_data:
            filename = data['filename']
            annotation_text = data['annotation_text']
            prediction_text = data['prediction_text']
            result = data['result']
            
            # 解析JSON数据
            try:
                standard_invoices = json.loads(annotation_text)
                prediction_invoices = json.loads(prediction_text)
            except json.JSONDecodeError as e:
                print(f"解析JSON数据失败 {filename}: {e}")
                continue
            
            # 创建InvoiceComparer实例用于数据处理
            comparer = InvoiceComparer(core_fields=compare_fields, verbose=False)
            
            # 处理每种类型的比对结果
            file_rows = process_comparison_results(
                filename, standard_invoices, prediction_invoices, 
                result, compare_fields, comparer
            )
            all_rows.extend(file_rows)
        
        # 写入Excel
        with pd.ExcelWriter(excel_output_path, engine='openpyxl') as writer:
            # 先写入统计sheet
            _create_statistics_sheet(writer, statistics, compare_fields)
            # 再写入详情sheet
            _create_details_sheet(writer, all_rows, columns)
            
    except Exception as e:
        print(f"生成Excel报告时出错: {e}")
        # 如果出错，创建一个最基本的Excel文件
        try:
            df = pd.DataFrame(columns=columns)
            with pd.ExcelWriter(excel_output_path, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Invoice_Details', index=False)
            print(f"已创建空的Excel文件: {excel_output_path}")
        except Exception as fallback_e:
            print(f"创建备用Excel文件也失败: {fallback_e}")

    return excel_output_path, all_rows

def eval_ls(eval_list, compare_fields=["totalAmount", "invoiceDate", "docType", "currency", "billToName", "totalTaxAmount"]):
    logger.info(f"开始票据提取评估，可用文档数量: {len(eval_list)}")
    results = []
    excel_data = []  # 用于存储Excel数据

    # 遍历每个文件，进行票据比对
    for i, (filename, (annotation_text, prediction_text)) in enumerate(eval_list.items(), 1):
        # 后处理：为缺少totalTaxAmount的发票添加该字段
        prediction_text_processed = post_process_invoices(prediction_text)
        
        # 过滤只保留核心字段
        annotation_text_filtered = filter_json_by_fields(annotation_text, compare_fields)
        prediction_text_filtered = filter_json_by_fields(prediction_text_processed, compare_fields)
        
        # 根据参数选择比对方法
        result = compare_invoices_with_comparer(
            annotation_text_filtered,
            prediction_text_filtered,
            compare_fields
        )

        obj = {"id": filename, "result": result}
        results.append(obj)

        excel_data.append({
            'filename': filename,
            'annotation_text': annotation_text_filtered,
            'prediction_text': prediction_text_filtered,
            'result': result
        })

    if not results:
        logger.warning("results==none, 没有可评估的任务")
        return None, [], {}
    
    # 生成所有明细行
    all_rows = []
    for data in excel_data:
        filename = data['filename']
        annotation_text = data['annotation_text']
        prediction_text = data['prediction_text']
        result = data['result']
        try:
            standard_invoices = json.loads(annotation_text)
            prediction_invoices = json.loads(prediction_text)
        except json.JSONDecodeError as e:
            print(f"解析JSON数据失败 {filename}: {e}")
            continue
        comparer = InvoiceComparer(core_fields=compare_fields, verbose=False)
        file_rows = process_comparison_results(
            filename, standard_invoices, prediction_invoices, 
            result, compare_fields, comparer
        )
        all_rows.extend(file_rows)
    
    # 只算一次统计
    statistics = calculate_evaluation_statistics(all_rows)
    
    # 生成Excel报告
    excel_path, _ = generate_excel_report(excel_data, compare_fields, statistics)
    return excel_path, all_rows, statistics

# todo: 异常判读
def get_last_value(task_ann_preds):
    """获取queryset中指定键的最后一个值"""
    ann_pred = list(task_ann_preds)[-1][-1]
    return ann_pred['value']['text'][-1]

def calculate_evaluation_statistics(all_rows):
    """
    基于字段比较结果列表计算统计指标
    
    Args:
        all_rows: 字段比较结果的列表，每个元素包含一张票的比较结果
                 格式: [{'filename': 'xxx.pdf', 'std_field': value, 'pred_field': value, 'check_field': bool}, ...]
    
    Returns:
        dict: 包含各种准确率统计的字典
            - field_accuracy: 各字段准确率
            - invoice_accuracy: 票级别准确率
            - document_accuracy: 文档级别准确率
            - total_invoices: 总票数
            - total_documents: 总文档数
    """
    if not all_rows:
        return {
            'field_accuracy': {},
            'invoice_accuracy': 0.0,
            'document_accuracy': 0.0,
            'total_invoices': 0,
            'total_documents': 0
        }
    
    # 提取所有字段名（去除std_、pred_、check_前缀）
    field_names = set()
    for row in all_rows:
        for key in row.keys():
            if key.startswith('check_'):
                field_name = key[6:]  # 去除'check_'前缀
                field_names.add(field_name)
    
    field_names = sorted(list(field_names))
    
    # 1. 计算各字段准确率
    field_accuracy = {}
    for field in field_names:
        check_field = f'check_{field}'
        correct_count = sum(1 for row in all_rows if row.get(check_field, False))
        total_count = len(all_rows)
        field_accuracy[field] = round(correct_count / total_count * 100, 2) if total_count > 0 else 0.0
    
    # 2. 计算票级别准确率（每张票的所有字段都正确）
    correct_invoices = 0
    for row in all_rows:
        invoice_correct = True
        for field in field_names:
            check_field = f'check_{field}'
            if not row.get(check_field, False):
                invoice_correct = False
                break
        if invoice_correct:
            correct_invoices += 1
    
    invoice_accuracy = round(correct_invoices / len(all_rows) * 100, 2) if all_rows else 0.0
    
    # 3. 计算文档级别准确率（每个文档下的所有票都正确）
    # 按文档分组
    documents = {}
    for row in all_rows:
        filename = row.get('filename', 'unknown')
        if filename not in documents:
            documents[filename] = []
        documents[filename].append(row)
    
    correct_documents = 0
    for filename, invoices in documents.items():
        document_correct = True
        for invoice in invoices:
            invoice_correct = True
            for field in field_names:
                check_field = f'check_{field}'
                if not invoice.get(check_field, False):
                    invoice_correct = False
                    break
            if not invoice_correct:
                document_correct = False
                break
        if document_correct:
            correct_documents += 1
    
    document_accuracy = round(correct_documents / len(documents) * 100, 2) if documents else 0.0
    
    return {
        'field_accuracy': field_accuracy,
        'invoice_accuracy': invoice_accuracy,
        'document_accuracy': document_accuracy,
        'total_invoices': len(all_rows),
        'total_documents': len(documents),
        'correct_invoices': correct_invoices,
        'correct_documents': correct_documents
    }

def evaluate_invoice_extraction_task(project, queryset, **kwargs):
    """票据提取任务评估入口函数"""
    logger.info(f"开始票据提取评估，项目ID: {project.id}，任务数量: {queryset.count()}")
    
    # 获取同时有标注和预测的任务
    tasks_with_both = queryset.filter(
        annotations__isnull=False,
        predictions__isnull=False
    ).distinct()
        
    ann_task_num = 0

    # 收集标注和预测数据
    results = {}
    model_version = 'N/A'  # 初始化model_version
    
    for task in tasks_with_both:
        # 获取已完成的标注
        task_annotations = task.annotations.filter(
            was_cancelled=False
        ).values_list('result', flat=True)
        
        # 获取预测结果对象（包含model_version等完整信息）
        task_predictions = task.predictions.all()
        
        if task_annotations and task_predictions:
            # 取最后一个标注作为真实标签
            ann_text = get_last_value(task_annotations)
            
            # 获取最后一个预测的完整对象
            last_prediction = task_predictions.last()
            pred_text = get_last_value([last_prediction.result])
            
            # 提取model_version（如果还没有获取到的话）
            if model_version == 'N/A' and hasattr(last_prediction, 'model_version'):
                model_version = last_prediction.model_version or 'N/A'
            
            task_data_dict = getattr(task, 'data', {})

            if 'filename' in task_data_dict:
                filename = task_data_dict['filename']
                results[filename] = (ann_text, pred_text)
            else:
                id = getattr(task, 'id', 'NO_ID')
                logger.error(f"任务 {id} 没有文件名信息，跳过")

    # 字段明细比对列表
    excel_path, all_rows, statistics = eval_ls(results)
    
    # 将从预测对象中获取的model_version添加到统计信息中
    statistics['model_version'] = model_version
    
    # 构建评估摘要
    evaluation_summary = {
        'project_id': project.id,
        'evaluated_at': datetime.now().isoformat(),
        'task_count': len(results),
        'evaluation_type': 'invoice_extraction',
        'excel_path': excel_path,
        'statistics': statistics
    }
    
    
    return {
        'processed_items': len(results),
        'detail': f'{len(results)} 个任务已评估',
        'evaluation_type': 'invoice_extraction',
        'evaluation_results': evaluation_summary
    }


# 注册票据提取评估动作
invoice_actions = [
    {
        'entry_point': evaluate_invoice_extraction_task,
        'permission': all_permissions.predictions_any,
        'title': 'Evaluate Invoice Extraction',
        'order': 202,
        'dialog': {
            'text': '本评估是从标注和预测的结果中提取，如果有多个版本的标注或预测结果，将取最后一个版本的结果来评估。',
            'type': 'confirm',
        },
    },
]
import json
import os
import pandas as pd
import json
from openpyxl import Workbook
from openpyxl.utils.dataframe import dataframe_to_rows

fields = ["project", "id", "filename", "page", "docType", "invoiceType", "nameOfInvoice", "invoiceNumber", "invoiceCode", "originalInvoiceNumber", 
"invoiceDate", "originalInvoiceDate", "totalNetAmount", "totalAmount", "totalTaxAmount", "currency", 
"billToName", "billToComposite", "billToCountry", "billToTaxIdentificationNumber", "shipFromComposite", 
"billFromName", "billFromComposite", "billFromCountry", "billFromTaxIdentificationNumber", 
"purchaseOrderNumber", "shipmentNumber", "dueDate", "paymentDueInDays", "detailOfGoodsOrServices", "detailOfTaxSummary"]

def extract_valid_text(items_list):
    """
    从items_list中提取有效的JSON文本和字段备注
    :param items_list: annotations或predictions列表
    :return: (有效的JSON文本, 字段备注)，如果没有找到则返回("[]", {})
    """
    for item in items_list:
        # 跳过 was_cancelled 为 true 的 item
        if item.get("was_cancelled", False):
            continue
            
        # 检查是否有有效的 result 数据
        if "result" in item and item["result"]:
            result_list = item["result"]
            
            # 遍历 result 数组中的每个元素
            for result_item in result_list:
                if "value" in result_item:
                    value = result_item["value"]
                    if "text" in value and value["text"]:
                        text_data = value["text"]
                        # 处理text字段，可能是字符串或列表
                        if isinstance(text_data, list):
                            potential_text = text_data[-1]  # 获取列表的最后一个元素
                        else:
                            potential_text = text_data  # 直接使用字符串
                        
                        try:
                            json.loads(potential_text)
                            # 提取字段备注 - 从result的meta字段中获取
                            field_annotations = result_item.get("meta", {}).get("field_annotations", {})
                            return potential_text, field_annotations  # 找到有效的 JSON 后返回
                        except (json.JSONDecodeError, TypeError):
                            continue  # 不是有效 JSON，继续下一个 result 元素
    return "[]", {}

def get_dynamic_fields_from_data(data_list: list, include_annotations: bool = True) -> list:
    """
    从数据中动态生成字段列表
    :param data_list: 数据列表
    :param include_annotations: 是否包含备注列(_err和_note)
    :return: 字段列表
    """
    base_fields = ["project", "id", "filename", "page"]
    dynamic_fields = []
    
    for item in data_list:
        try:
            # 提取annotations和predictions中的text和字段备注
            annotation_text, _ = extract_valid_text(item.get("annotations", []))
            prediction_text, _ = extract_valid_text(item.get("predictions", []))
            
            for text in [annotation_text, prediction_text]:
                if text and text != "[]":
                    try:
                        parsed_data = json.loads(text)
                        if isinstance(parsed_data, list) and parsed_data:
                            for data_item in parsed_data:
                                if isinstance(data_item, dict):
                                    # 只添加顶层字段
                                    for key in data_item.keys():
                                        if key not in base_fields and key not in dynamic_fields:
                                            dynamic_fields.append(key)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue
    
    # 构建最终字段列表
    all_fields = base_fields.copy()
    for field in dynamic_fields:
        if include_annotations:
            # 为Annotations工作表：包含备注列
            all_fields.extend([field, f"{field}_err", f"{field}_note"])
        else:
            # 为Predictions工作表：只包含基础字段
            all_fields.append(field)
    
    return all_fields

def extract_annotations_and_data(json_path: str) -> dict:
    """
    读取label_studio导出的json数据，提取每个标注的id、filename、annotations和predictions中的text和字段备注
    输出为包含(project, id, filename, annotation_text, annotation_field_annotations, prediction_text, prediction_field_annotations)元组的列表。
    如果任何一个为空，则打印err并跳过该项。
    :param json_path: json文件路径
    :return: List[(project, id, filename, annotation_text, annotation_field_annotations, prediction_text, prediction_field_annotations)]
    """
    results = []
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for item in data:
            # 获取project、id和filename
            project = item.get("project", None)
            item_id = item.get("id", None)
            filename = item.get("data", {}).get("filename", None)
            
            # 提取annotations和predictions中的text和字段备注
            annotation_text, annotation_field_annotations = extract_valid_text(item.get("annotations", []))
            prediction_text, prediction_field_annotations = extract_valid_text(item.get("predictions", []))
            
            if not item_id or not filename:
                print(
                    f"err: project={project}, id={item_id}, filename={filename}, annotation_text={annotation_text}, prediction_text={prediction_text}"
                )
                continue
            
            results.append((project, item_id, filename, annotation_text, annotation_field_annotations, prediction_text, prediction_field_annotations))
    return results


def export_to_excel(json_path: str, output_data: str):
    """
    将 extract_annotations_and_data 的返回值写入 Excel 文件
    :param json_path: json文件路径
    :param output_data: 输出目录路径
    :return: Excel 文件路径
    """
    # 获取数据
    results = extract_annotations_and_data(json_path)
    
    # 读取原始数据以动态生成字段
    with open(json_path, "r", encoding="utf-8") as f:
        raw_data = json.load(f)
    
    # 动态生成字段映射
    annotation_fields = get_dynamic_fields_from_data(raw_data, include_annotations=True)
    prediction_fields = get_dynamic_fields_from_data(raw_data, include_annotations=False)
    
    # 创建工作簿
    wb = Workbook()
    
    # 创建两个工作表
    ws_annotation = wb.active
    ws_annotation.title = "Annotations"
    ws_prediction = wb.create_sheet(title="Predictions")
    
    # 添加表头
    for col_idx, field in enumerate(annotation_fields, 1):
        ws_annotation.cell(row=1, column=col_idx, value=field)
    
    for col_idx, field in enumerate(prediction_fields, 1):
        ws_prediction.cell(row=1, column=col_idx, value=field)
    
    # 处理每个结果
    annotation_row = 2  # 从第2行开始（第1行是表头）
    prediction_row = 2
    
    def process_text_data(text, field_annotations, worksheet, start_row, project, item_id, filename, include_annotations=True):
        """
        处理文本数据并写入工作表，将字段备注填入对应的_err和_note列
        :param text: JSON文本
        :param field_annotations: 字段备注数据
        :param worksheet: 工作表对象
        :param start_row: 起始行
        :param project: 项目ID
        :param item_id: 项目ID
        :param filename: 文件名
        :param include_annotations: 是否包含备注列
        :return: 下一行的行号
        """
        current_row = start_row
        try:
            data = json.loads(text)
            if isinstance(data, list):
                # 如果是空列表，仍然插入一行，只包含project、id和filename
                if len(data) == 0:
                    worksheet.cell(row=current_row, column=1, value=project)  # project列
                    worksheet.cell(row=current_row, column=2, value=item_id)  # id列
                    worksheet.cell(row=current_row, column=3, value=filename)  # filename列
                    current_row += 1
                else:
                    for ticket_index, item in enumerate(data):
                        # 设置基本字段
                        worksheet.cell(row=current_row, column=1, value=project)  # project列
                        worksheet.cell(row=current_row, column=2, value=item_id)  # id列
                        worksheet.cell(row=current_row, column=3, value=filename)  # filename列
                        
                        # 如果没有page字段，默认填入1
                        if "page" not in item:
                            worksheet.cell(row=current_row, column=4, value=1)  # page列
                        
                        # 处理其他字段（跳过基础字段）
                        col_idx = 5  # 从第5列开始（跳过project、id、filename、page）
                        
                        # 获取所有动态字段（不包括基础字段）
                        base_fields = ["project", "id", "filename", "page"]
                        # 根据工作表类型获取对应的字段列表
                        current_fields = annotation_fields if include_annotations else prediction_fields
                        dynamic_field_names = []
                        for field in current_fields:
                            if field not in base_fields and not field.endswith("_err") and not field.endswith("_note"):
                                dynamic_field_names.append(field)
                        
                        # 处理每个动态字段及其备注列
                        for field_name in dynamic_field_names:
                            # 处理主字段
                            if field_name in item:
                                value = item[field_name]
                                cell = worksheet.cell(row=current_row, column=col_idx)
                                
                                # 根据值类型设置单元格
                                if isinstance(value, (int, float)):
                                    cell.value = value
                                    cell.number_format = '0.00'  # 设置数字格式
                                elif isinstance(value, dict) or isinstance(value, list):
                                    # 格式化JSON对象，使其更易读
                                    cell.value = json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True)
                                else:
                                    # 确保字符串值正确处理，避免中文/日文乱码
                                    cell.value = str(value)
                            
                            # 只有在include_annotations为True时才处理备注信息
                            if include_annotations:
                                # 处理该字段的备注信息
                                annotation_key = f"ticket_{ticket_index}_{field_name}"
                                if annotation_key in field_annotations:
                                    annotation = field_annotations[annotation_key]
                                    
                                    # 填入错误类型到_err列
                                    if annotation.get("errorTypes"):
                                        error_types = annotation["errorTypes"]
                                        if isinstance(error_types, list):
                                            error_value = "; ".join(error_types)
                                        else:
                                            error_value = str(error_types)
                                        worksheet.cell(row=current_row, column=col_idx + 1, value=error_value)
                                    
                                    # 填入原因到_note列
                                    if annotation.get("reason"):
                                        worksheet.cell(row=current_row, column=col_idx + 2, value=annotation["reason"])
                                
                                    # 移动到下一组字段（主字段 + _err + _note）
                                col_idx += 3
                            else:
                                # 不包含备注列时，只移动到下一个主字段
                                col_idx += 1
                        
                        current_row += 1
        except json.JSONDecodeError:
            # 即使解析失败，也插入一行基本信息
            worksheet.cell(row=current_row, column=1, value=project)  # project列
            worksheet.cell(row=current_row, column=2, value=item_id)  # id列
            worksheet.cell(row=current_row, column=3, value=filename)  # filename列
            current_row += 1
            print(f"无法解析文本: {text}")
        return current_row
    
    for project, item_id, filename, annotation_text, annotation_field_annotations, prediction_text, prediction_field_annotations in results:
        # 处理 annotation_text (包含备注列)
        annotation_row = process_text_data(annotation_text, annotation_field_annotations, ws_annotation, annotation_row, project, item_id, filename, include_annotations=True)
        
        # 处理 prediction_text (不包含备注列)
        prediction_row = process_text_data(prediction_text, prediction_field_annotations, ws_prediction, prediction_row, project, item_id, filename, include_annotations=False)
    
    # 创建输出目录
    os.makedirs(output_data, exist_ok=True)
    excel_path = os.path.join(output_data, 'result.xlsx')
    
    # 保存Excel文件
    wb.save(excel_path)
    print(f"Excel文件已保存至: {excel_path}")
    
    return excel_path
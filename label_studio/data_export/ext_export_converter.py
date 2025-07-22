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
    从items_list中提取有效的JSON文本
    :param items_list: annotations或predictions列表
    :return: 有效的JSON文本，如果没有找到则返回None
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
                        potential_text = value["text"][-1]
                        try:
                            json.loads(potential_text)
                            return potential_text  # 找到有效的 JSON 后返回
                        except (json.JSONDecodeError, TypeError):
                            continue  # 不是有效 JSON，继续下一个 result 元素
    return "[]"

def get_dynamic_fields_from_data(data_list):
    """
    根据数据内容动态生成字段映射
    :param data_list: 解析后的数据列表
    :return: 字段列表
    """
    all_fields = ["project", "id", "filename", "page"]
    
    for item in data_list:
        try:
            # 提取annotations和predictions中的text
            annotation_text = extract_valid_text(item.get("annotations", []))
            prediction_text = extract_valid_text(item.get("predictions", []))
            
            for text in [annotation_text, prediction_text]:
                if text and text != "[]":
                    try:
                        parsed_data = json.loads(text)
                        if isinstance(parsed_data, list) and parsed_data:
                            for data_item in parsed_data:
                                if isinstance(data_item, dict):
                                    # 只添加顶层字段
                                    for key in data_item.keys():
                                        if key not in all_fields:
                                            all_fields.append(key)
                    except json.JSONDecodeError:
                        continue
        except Exception:
            continue
    
    return all_fields

def extract_annotations_and_data(json_path: str) -> dict:
    """
    读取label_studio导出的json数据，提取每个标注的id、filename、annotations和predictions中的text
    输出为包含(project, id, filename, annotation_text, prediction_text)元组的列表。
    如果任何一个为空，则打印err并跳过该项。
    :param json_path: json文件路径
    :return: List[(project, id, filename, annotation_text, prediction_text)]
    """
    results = []
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
        for item in data:
            # 获取project、id和filename
            project = item.get("project", None)
            item_id = item.get("id", None)
            filename = item.get("data", {}).get("filename", None)
            
            # 提取annotations和predictions中的text
            annotation_text = extract_valid_text(item.get("annotations", []))
            prediction_text = extract_valid_text(item.get("predictions", []))
            
            if not item_id or not filename:
                print(
                    f"err: project={project}, id={item_id}, filename={filename}, annotation_text={annotation_text}, prediction_text={prediction_text}"
                )
                continue
            
            results.append((project, item_id, filename, annotation_text, prediction_text))
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
    dynamic_fields = get_dynamic_fields_from_data(raw_data)
    
    # 创建工作簿
    wb = Workbook()
    
    # 创建两个工作表
    ws_annotation = wb.active
    ws_annotation.title = "Annotations"
    ws_prediction = wb.create_sheet(title="Predictions")
    
    # 添加表头
    for ws in [ws_annotation, ws_prediction]:
        for col_idx, field in enumerate(dynamic_fields, 1):
            ws.cell(row=1, column=col_idx, value=field)
    
    # 处理每个结果
    annotation_row = 2  # 从第2行开始（第1行是表头）
    prediction_row = 2
    
    def process_text_data(text, worksheet, start_row, project, item_id, filename):
        """
        处理文本数据并写入工作表
        :param text: JSON文本
        :param worksheet: 工作表对象
        :param start_row: 起始行
        :param project: 项目ID
        :param item_id: 项目ID
        :param filename: 文件名
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
                    for item in data:
                        # 设置基本字段
                        worksheet.cell(row=current_row, column=1, value=project)  # project列
                        worksheet.cell(row=current_row, column=2, value=item_id)  # id列
                        worksheet.cell(row=current_row, column=3, value=filename)  # filename列
                        
                        # 如果没有page字段，默认填入1
                        if "page" not in item:
                            worksheet.cell(row=current_row, column=4, value=1)  # page列
                        
                        # 处理其他字段
                        for col_idx, field in enumerate(dynamic_fields[3:], 4):  # 从第4列开始（跳过project、id和filename）
                            if field in item:
                                value = item[field]
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
                        
                        current_row += 1
        except json.JSONDecodeError:
            # 即使解析失败，也插入一行基本信息
            worksheet.cell(row=current_row, column=1, value=project)  # project列
            worksheet.cell(row=current_row, column=2, value=item_id)  # id列
            worksheet.cell(row=current_row, column=3, value=filename)  # filename列
            current_row += 1
            print(f"无法解析文本: {text}")
        return current_row
    
    for project, item_id, filename, annotation_text, prediction_text in results:
        # 处理 annotation_text
        annotation_row = process_text_data(annotation_text, ws_annotation, annotation_row, project, item_id, filename)
        
        # 处理 prediction_text
        prediction_row = process_text_data(prediction_text, ws_prediction, prediction_row, project, item_id, filename)
    
    # 创建输出目录
    os.makedirs(output_data, exist_ok=True)
    excel_path = os.path.join(output_data, 'result.xlsx')
    
    # 保存Excel文件
    wb.save(excel_path)
    print(f"Excel文件已保存至: {excel_path}")
    
    return excel_path
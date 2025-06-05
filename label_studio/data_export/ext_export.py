# label_studio/data_export/ext_export.py

from label_studio_sdk.converter.converter import Converter, Format
from enum import Enum
import pandas as pd
import os
from aenum import extend_enum

# 1. 扩展 Format 枚举
if not hasattr(Format, 'INV_EXCEL'):
    extend_enum(Format, 'INV_EXCEL', 1000)

# 2. 扩展 _FORMAT_INFO
Converter._FORMAT_INFO[Format.INV_EXCEL] = {
    "title": "INV_EXCEL",
    "description": "自定义的Excel导出格式（Demo）",
    "link": "https://yourdoc.com/inv_excel",
}

# 3. monkey patch convert 方法
old_convert = Converter.convert

def new_convert(self, input_data, output_data, format, is_dir=True, **kwargs):
    # 兼容字符串和枚举
    if isinstance(format, str):
        try:
            format = Format[format]
        except KeyError:
            pass
    if format == Format.INV_EXCEL:
        # 读取输入json（input_data 可能是文件或目录，这里只处理文件情况）
        if is_dir:
            raise NotImplementedError("INV_EXCEL 只支持单文件导出")
        import json
        with open(input_data, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
        # data 是 list，每个元素是一个任务
        # 这里只做简单演示，把所有任务的 id 和 data 字段导出
        rows = []
        for item in data:
            row = {
                'id': item.get('id'),
                **item.get('data', {})
            }
            rows.append(row)
        df = pd.DataFrame(rows)
        os.makedirs(output_data, exist_ok=True)
        excel_path = os.path.join(output_data, 'result.xlsx')
        df.to_excel(excel_path, index=False)
        return
    # 其他格式走原始逻辑
    return old_convert(self, input_data, output_data, format, is_dir, **kwargs)

Converter.convert = new_convert
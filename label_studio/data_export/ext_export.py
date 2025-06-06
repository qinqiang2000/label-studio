# 采用monkey patch的方式，扩展Format枚举，并扩展convert方法

from typing import OrderedDict
from label_studio_sdk.converter.converter import Converter, Format
from enum import Enum
import pandas as pd
import os
from aenum import extend_enum
from label_studio.data_export.ext_export_converter import export_to_excel

# 在文件顶部添加全局常量
PIAOZONE_EXCEL = 'PIAOZONE_EXCEL'

# 1. 扩展 Format 枚举
if not hasattr(Format, PIAOZONE_EXCEL):
    extend_enum(Format, PIAOZONE_EXCEL, 1000)

# 2. 扩展 _FORMAT_INFO
Converter._FORMAT_INFO[getattr(Format, PIAOZONE_EXCEL)] = {
    "title": PIAOZONE_EXCEL,
    "description": "发票云自定义的Excel导出格式",
    "link": f"https://yourdoc.com/{PIAOZONE_EXCEL}",
}

# 3. 调整展示顺序，让piaozone_excel排在最前面
original_all_formats = Converter.all_formats

def patched_all_formats(self):
    formats = original_all_formats(self)
    
    priority_keys = [getattr(Format, PIAOZONE_EXCEL)]  # 你要提前的元素，可多个
    other_keys = [k for k in formats if k not in priority_keys]
    final_keys = priority_keys + other_keys

    _FORMAT_INFO_REORDERED = OrderedDict((k, formats[k]) for k in final_keys)

    return _FORMAT_INFO_REORDERED

Converter.all_formats = patched_all_formats

# 4. monkey patch convert 方法
old_convert = Converter.convert

def new_convert(self, input_data, output_data, format, is_dir=True, **kwargs):
    # 兼容字符串和枚举
    if isinstance(format, str):
        try:
            format = Format[format]
        except KeyError:
            pass
    if format == getattr(Format, PIAOZONE_EXCEL):
        # 读取输入json（input_data 可能是文件或目录，这里只处理文件情况）
        if is_dir:
            raise NotImplementedError("PIAOZONE_EXCEL 只支持单文件导出")

        export_to_excel(input_data, output_data)
        # import json
        # with open(input_data, 'r', encoding='utf-8') as f:
        #     data = json.load(f)
            
        # # data 是 list，每个元素是一个任务
        # # 这里只做简单演示，把所有任务的 id 和 data 字段导出
        # rows = []
        # for item in data:
        #     row = {
        #         'id': item.get('id'),
        #         **item.get('data', {})
        #     }
        #     rows.append(row)
        # df = pd.DataFrame(rows)
        # os.makedirs(output_data, exist_ok=True)
        # excel_path = os.path.join(output_data, 'result.xlsx')
        # df.to_excel(excel_path, index=False)
        return
    # 其他格式走原始逻辑
    return old_convert(self, input_data, output_data, format, is_dir, **kwargs)

Converter.convert = new_convert
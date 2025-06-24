#!/usr/bin/env python3
"""
生成Excel文件测试修复效果
"""

import sys
import os
import json
import pandas as pd
from datetime import datetime

# 添加路径以便导入模块
sys.path.append('/Users/qinqiang02/colab/codespace/ai/label-studio')

def create_test_data():
    """创建测试数据"""
    
    # 标准数据 - 使用浮点数
    standard_invoices = [
        {
            'recieptNum': 25098000001,
            'tradeDate': '2024-05-18',
            'amount': 200.0  # 浮点数
        },
        {
            'recieptNum': 25098000002,
            'tradeDate': '2024-05-19',
            'amount': 10.0   # 浮点数
        },
        {
            'recieptNum': 25098000003,
            'tradeDate': '2024-05-20',
            'amount': 144.25 # 浮点数
        }
    ]
    
    # 预测数据 - 使用整数（模拟您的情况）
    prediction_invoices = [
        {
            'recieptNum': 25098000001,
            'tradeDate': '2024-05-18',
            'amount': 200    # 整数，但值相同
        },
        {
            'recieptNum': 25098000002,
            'tradeDate': '2024-05-19',
            'amount': 10     # 整数，但值相同
        },
        {
            'recieptNum': 25098000003,
            'tradeDate': '2024-05-20',
            'amount': 144.25 # 浮点数，相同
        }
    ]
    
    return standard_invoices, prediction_invoices

def test_invoice_comparison():
    """测试票据比较功能"""
    try:
        from label_studio.data_manager.actions.invoice_compare.invoice_compare_utils import InvoiceComparer
        from label_studio.data_manager.actions.invoice_evaluation import process_comparison_results
        
        print("=== 生成Excel文件测试修复效果 ===")
        
        # 创建测试数据
        standard_invoices, prediction_invoices = create_test_data()
        
        print(f"标准数据: {standard_invoices}")
        print(f"预测数据: {prediction_invoices}")
        
        # 创建比较器
        compare_fields = ['recieptNum', 'tradeDate', 'amount']
        comparer = InvoiceComparer(core_fields=compare_fields, verbose=True)
        
        # 进行比较
        result = comparer.compare_invoices(standard_invoices, prediction_invoices)
        print(f"\n比较结果: {result}")
        
        # 处理比较结果生成Excel行
        rows = process_comparison_results(
            filename='test_file.json',
            standard_invoices=standard_invoices,
            prediction_invoices=prediction_invoices,
            result=result,
            compare_fields=compare_fields,
            comparer=comparer,
            prompt_name='test_prompt'
        )
        
        print(f"\n生成的Excel行数: {len(rows)}")
        for i, row in enumerate(rows):
            print(f"行 {i+1}: {row}")
        
        # 创建DataFrame并保存为Excel
        if rows:
            df = pd.DataFrame(rows)
            excel_filename = 'test_comparison_result.xlsx'
            df.to_excel(excel_filename, index=False)
            print(f"\nExcel文件已生成: {excel_filename}")
            
            # 显示关键字段的比较结果
            print(f"\n关键字段比较结果:")
            for i, row in enumerate(rows):
                print(f"第 {i+1} 行:")
                for field in compare_fields:
                    std_val = row.get(f'std_{field}', 'N/A')
                    pred_val = row.get(f'pred_{field}', 'N/A')
                    check_val = row.get(f'check_{field}', 'N/A')
                    print(f"  {field}: std={std_val} pred={pred_val} check={check_val}")
                print()
            
            return excel_filename
        else:
            print("没有生成Excel行")
            return None
            
    except ImportError as e:
        print(f"导入错误: {e}")
        print("尝试直接测试字段比较逻辑...")
        return test_field_comparison_directly()
    except Exception as e:
        print(f"测试过程中出错: {e}")
        import traceback
        traceback.print_exc()
        return None

def test_field_comparison_directly():
    """直接测试字段比较逻辑"""
    print("\n=== 直接测试字段比较逻辑 ===")
    
    # 模拟修复后的field_values_equal方法
    def normalize_amount(amount):
        if amount is None:
            return 0.0
        if isinstance(amount, (int, float)):
            return float(amount)
        return 0.0
    
    def field_values_equal(value1, value2, field_name):
        if 'amount' in field_name.lower():
            # 金额字段使用数值比较
            norm1 = normalize_amount(value1)
            norm2 = normalize_amount(value2)
            return norm1 == norm2
        else:
            # 其他字段直接比较
            return str(value1) == str(value2)
    
    # 创建测试数据
    standard_invoices, prediction_invoices = create_test_data()
    
    # 生成Excel行
    rows = []
    compare_fields = ['recieptNum', 'tradeDate', 'amount']
    
    for i, (std_invoice, pred_invoice) in enumerate(zip(standard_invoices, prediction_invoices)):
        row = {'filename': 'test_file.json', 'prompt_name': 'test_prompt'}
        
        for field in compare_fields:
            std_value = std_invoice.get(field, '')
            pred_value = pred_invoice.get(field, '')
            
            # 使用修复后的逻辑
            check_result = field_values_equal(std_value, pred_value, field)
            
            row[f'std_{field}'] = std_value
            row[f'pred_{field}'] = pred_value
            row[f'check_{field}'] = check_result
        
        rows.append(row)
    
    # 创建DataFrame并保存为Excel
    df = pd.DataFrame(rows)
    excel_filename = 'test_direct_comparison.xlsx'
    df.to_excel(excel_filename, index=False)
    print(f"\nExcel文件已生成: {excel_filename}")
    
    # 显示结果
    print(f"\n字段比较结果:")
    for i, row in enumerate(rows):
        print(f"第 {i+1} 行:")
        for field in compare_fields:
            std_val = row.get(f'std_{field}', 'N/A')
            pred_val = row.get(f'pred_{field}', 'N/A')
            check_val = row.get(f'check_{field}', 'N/A')
            print(f"  {field}: std={std_val} pred={pred_val} check={check_val}")
        print()
    
    return excel_filename

if __name__ == "__main__":
    excel_file = test_invoice_comparison()
    if excel_file:
        print(f"\n✅ 成功生成Excel文件: {excel_file}")
        print("请打开该文件查看修复效果")
    else:
        print("\n❌ 生成Excel文件失败") 
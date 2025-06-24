#!/usr/bin/env python3
"""
检查包含多个字段的Excel文件内容
"""

import pandas as pd
import openpyxl
import sys
import os

def check_excel_file(excel_path):
    """检查Excel文件内容"""
    print(f"=== 检查Excel文件: {excel_path} ===")
    
    if not os.path.exists(excel_path):
        print(f"❌ 文件不存在: {excel_path}")
        return
    
    print(f"✅ 文件存在，大小: {os.path.getsize(excel_path)} bytes")
    
    try:
        # 使用openpyxl检查工作表
        workbook = openpyxl.load_workbook(excel_path)
        sheet_names = workbook.sheetnames
        print(f"工作表数量: {len(sheet_names)}")
        print(f"工作表名称: {sheet_names}")
        
        # 检查Document_Details工作表
        if 'Document_Details' in sheet_names:
            print(f"\n{'='*80}")
            print(f"检查Document_Details工作表")
            print(f"{'='*80}")
            
            df = pd.read_excel(excel_path, sheet_name='Document_Details')
            print(f"行数: {len(df)}")
            print(f"列数: {len(df.columns)}")
            print(f"列名: {list(df.columns)}")
            
            # 分析每个字段
            fields = ['recieptNum', 'tradeDate', 'amount']
            
            for field in fields:
                std_col = f'std_{field}'
                pred_col = f'pred_{field}'
                check_col = f'check_{field}'
                
                if pred_col in df.columns:
                    print(f"\n🎯 分析字段: {field}")
                    print(f"{'='*50}")
                    
                    std_values = df[std_col].tolist() if std_col in df.columns else []
                    pred_values = df[pred_col].tolist()
                    check_values = df[check_col].tolist() if check_col in df.columns else []
                    
                    print(f"std_{field}值: {std_values}")
                    print(f"pred_{field}值: {pred_values}")
                    print(f"check_{field}值: {check_values}")
                    
                    # 统计分析
                    empty_count = sum(1 for v in pred_values if v == '' or v == ' ')
                    none_count = sum(1 for v in pred_values if pd.isna(v))
                    non_empty_count = sum(1 for v in pred_values if not pd.isna(v) and str(v).strip() != '')
                    zero_count = sum(1 for v in pred_values if str(v) == '0' or v == 0)
                    
                    print(f"统计分析:")
                    print(f"  空字符串数量: {empty_count}")
                    print(f"  None/NaN数量: {none_count}")
                    print(f"  非空值数量: {non_empty_count}")
                    print(f"  零值数量: {zero_count}")
                    
                    # 检查是否有异常的零值
                    if field == 'amount' and zero_count > 0:
                        print(f"⚠️  警告: amount字段有{zero_count}个零值，可能不正确")
                        for i, v in enumerate(pred_values):
                            if str(v) == '0' or v == 0:
                                print(f"    第{i+1}行: pred_{field}={v}")
            
            # 详细显示每一行
            print(f"\n{'='*80}")
            print(f"详细行数据")
            print(f"{'='*80}")
            
            for i, row in df.iterrows():
                filename = row.get('filename', 'N/A')
                prompt_name = row.get('prompt_name', 'N/A')
                
                line_info = f"第{i+1:2d}行:"
                
                for field in fields:
                    std_val = row.get(f'std_{field}', 'N/A')
                    pred_val = row.get(f'pred_{field}', 'N/A')
                    check_val = row.get(f'check_{field}', 'N/A')
                    
                    # 处理NaN值的显示
                    if pd.isna(std_val):
                        std_val = 'NaN'
                    if pd.isna(pred_val):
                        pred_val = 'NaN'
                    
                    line_info += f" {field}(std='{std_val}' pred='{pred_val}' check={check_val})"
                
                print(line_info)
            
            print(f"\n{'='*80}")
            print(f"完整数据表格")
            print(f"{'='*80}")
            print(df.to_string())
            
            # 重点检查amount字段的问题
            if 'pred_amount' in df.columns:
                print(f"\n{'='*80}")
                print(f"重点检查amount字段问题")
                print(f"{'='*80}")
                
                amount_values = df['pred_amount'].tolist()
                print(f"所有pred_amount值及其类型:")
                for i, val in enumerate(amount_values):
                    val_type = type(val).__name__
                    print(f"  第{i+1}行: {repr(val)} (类型: {val_type})")
                
                # 检查是否有不应该为0的值
                problematic_rows = []
                for i, val in enumerate(amount_values):
                    if val == 0 or val == 0.0 or str(val) == '0':
                        check_val = df.iloc[i]['check_amount'] if 'check_amount' in df.columns else 'N/A'
                        if check_val == False:  # 不匹配的行不应该有0值
                            problematic_rows.append(i + 1)
                
                if problematic_rows:
                    print(f"\n❌ 发现问题行: {problematic_rows}")
                    print(f"这些行的check_amount=False，但pred_amount为0，这可能不正确")
                else:
                    print(f"\n✅ amount字段看起来正常")
        
        workbook.close()
        
    except Exception as e:
        print(f"❌ 处理Excel文件时出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 使用API返回的Excel路径
    excel_path = "/var/folders/sn/shdg2z_d4ds1b5l83wjxpbvr0000gn/T/tmpuenwe4uw.xlsx"
    check_excel_file(excel_path) 
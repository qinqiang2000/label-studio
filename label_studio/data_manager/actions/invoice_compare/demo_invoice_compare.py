#!/usr/bin/env python3
"""
票据对比工具演示
展示如何使用 InvoiceComparer 进行票据对比
"""

import json
from invoice_compare_utils import InvoiceComparer


def demo_basic_usage():
    """基本使用演示"""
    print("=== 基本使用演示 ===")
    
    # 示例数据
    standard_data = [
        {
            "docType": "invoice",
            "invoiceDate": "2025-04-06", 
            "totalAmount": 183700,
            "totalTaxAmount": 16700,
            "currency": "JPY",
            "billToName": "ハイセンスジャパン 株式会社"
        },
        {
            "docType": "invoice",
            "invoiceDate": "2025-05-02",
            "totalAmount": 606100, 
            "totalTaxAmount": 55100,
            "currency": "JPY",
            "billToName": "ハイセンスジャパン 株式会社"
        }
    ]
    
    prediction_data = [
        {
            "docType": "invoice",
            "invoiceDate": "2025-04-06",
            "totalAmount": "183700",  # 字符串格式的金额
            "totalTaxAmount": "16700",
            "currency": "JPY", 
            "billToName": "ハピネツジャパン 株式会社 商品管理部 商品プロモーションG 本堂 様"  # 不同的名称
        }
    ]
    
    # 创建比较器
    comparer = InvoiceComparer(verbose=True)
    
    # 进行比较
    result = comparer.compare_invoices(standard_data, prediction_data)
    
    print("\n比较结果:")
    print(json.dumps(result, ensure_ascii=False, indent=2))
    
    return result


def demo_accuracy_calculation():
    """准确率计算演示"""
    print("\n=== 准确率计算演示 ===")
    
    # 完全匹配的数据
    standard_data = [
        {
            "docType": "invoice",
            "invoiceDate": "2025-01-15",
            "totalAmount": 100000,
            "totalTaxAmount": 10000,
            "currency": "JPY",
            "billToName": "测试公司"
        },
        {
            "docType": "receipt", 
            "invoiceDate": "2025-01-16",
            "totalAmount": 50000,
            "totalTaxAmount": 5000,
            "currency": "USD",
            "billToName": "另一个公司"
        }
    ]
    
    prediction_data = [
        {
            "docType": "invoice",
            "invoiceDate": "2025-01-15", 
            "totalAmount": "100000",  # 字符串格式，但语义相等
            "totalTaxAmount": "10000",
            "currency": "jpy",  # 小写，但语义相等
            "billToName": " 测试公司 "  # 有空格，但语义相等
        },
        {
            "docType": "receipt",
            "invoiceDate": "2025-01-16",
            "totalAmount": 50000,
            "totalTaxAmount": 5000,
            "currency": "USD",
            "billToName": "另一个公司"
        }
    ]
    
    comparer = InvoiceComparer(verbose=False)
    result = comparer.compare_invoices(standard_data, prediction_data)
    
    print(f"匹配票据数: {result['matched_count']}")
    print(f"不匹配票据数: {result['unmatched_count']}")
    print(f"票据级准确率: {result['invoice_accuracy']:.2%}")
    print(f"字段级准确率: {result['field_accuracy']:.2%}")
    
    return result


def demo_partial_match():
    """部分匹配演示"""
    print("\n=== 部分匹配演示 ===")
    
    standard_data = [
        {
            "docType": "invoice",
            "invoiceDate": "2025-03-01",
            "totalAmount": 200000,
            "totalTaxAmount": 20000,
            "currency": "JPY",
            "billToName": "原始公司名称"
        }
    ]
    
    prediction_data = [
        {
            "docType": "invoice",
            "invoiceDate": "2025-03-01",
            "totalAmount": 200000,  # 金额、日期、类型匹配
            # "totalTaxAmount": 25000,  # 税额不匹配
            "currency": "USD",  # 币种不匹配
            "billToName": "完全不同的公司名称"  # 名称不匹配
        }
    ]
    
    comparer = InvoiceComparer(verbose=True)
    result = comparer.compare_invoices(standard_data, prediction_data)
    
    print(f"\n差异字段: {result['unmatched'][0]['diff_fields'] if result['unmatched'] else '无'}")
    print(f"正确字段数: {result['correct_field_count']}")
    print(f"总字段数: {result['total_field_count']}")
    
    return result


def demo_file_input():
    """文件输入演示"""
    print("\n=== 文件输入演示 ===")
    
    # 创建示例文件
    standard_data = [
        {
            "docType": "invoice",
            "invoiceDate": "2025-02-01",
            "totalAmount": 300000,
            "totalTaxAmount": 30000,
            "currency": "JPY",
            "billToName": "文件测试公司"
        }
    ]
    
    prediction_data = [
        {
            "docType": "invoice",
            "invoiceDate": "2025-02-01", 
            "totalAmount": "300000",
            "totalTaxAmount": "30000",
            "currency": "JPY",
            "billToName": "文件测试公司"
        }
    ]
    
    # 保存到文件
    with open('standard_demo.json', 'w', encoding='utf-8') as f:
        json.dump(standard_data, f, ensure_ascii=False, indent=2)
    
    with open('prediction_demo.json', 'w', encoding='utf-8') as f:
        json.dump(prediction_data, f, ensure_ascii=False, indent=2)
    
    # 从文件读取并比较
    comparer = InvoiceComparer(verbose=True)
    result = comparer.compare_invoices('standard_demo.json', 'prediction_demo.json')
    
    # 保存结果
    comparer.save_result(result, 'compare_result.json')
    
    print("文件已保存: standard_demo.json, prediction_demo.json, compare_result.json")
    
    return result


def demo_edge_cases():
    """边界情况演示"""
    print("\n=== 边界情况演示 ===")
    
    # 空数据
    print("1. 空数据测试:")
    comparer = InvoiceComparer()
    result = comparer.compare_invoices([], [])
    print(f"空数据结果: 准确率 {result['invoice_accuracy']}")
    
    # 只有标准无预测
    print("\n2. 只有标准数据:")
    standard_only = [{"docType": "invoice", "invoiceDate": "2025-01-01", "totalAmount": 1000, 
                     "totalTaxAmount": 100, "currency": "JPY", "billToName": "测试"}]
    result = comparer.compare_invoices(standard_only, [])
    print(f"only_in_standard_count: {result['only_in_standard_count']}")
    
    # 只有预测无标准
    print("\n3. 只有预测数据:")
    prediction_only = [{"docType": "invoice", "invoiceDate": "2025-01-01", "totalAmount": 1000,
                       "totalTaxAmount": 100, "currency": "JPY", "billToName": "测试"}]
    result = comparer.compare_invoices([], prediction_only)
    print(f"only_in_prediction_count: {result['only_in_prediction_count']}")


def main():
    """主演示函数"""
    print("票据对比工具演示")
    print("="*50)
    
    # 运行各种演示
    # demo_basic_usage()
    # demo_accuracy_calculation()
    demo_partial_match()
    # demo_file_input()
    # demo_edge_cases()
    
    print("\n演示完成！")
    print("\n使用方法:")
    print("1. 作为库使用:")
    print("   from invoice_compare_utils import InvoiceComparer")
    print("   comparer = InvoiceComparer()")
    print("   result = comparer.compare_invoices(standard_data, prediction_data)")
    print("\n2. 命令行使用:")
    print("   python invoice_compare_utils.py -s standard.json -p prediction.json -o result.json")


if __name__ == "__main__":
    main() 
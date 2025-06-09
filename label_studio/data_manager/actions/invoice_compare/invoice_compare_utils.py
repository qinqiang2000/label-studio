#!/usr/bin/env python3
"""
票据对比工具
支持从文件读取数据、计算准确率等功能
"""

import json
import re
import argparse
from datetime import datetime
from typing import List, Dict, Any, Tuple, Union
from pathlib import Path
from dataclasses import dataclass


@dataclass
class CompareResult:
    """比较结果数据类"""
    matched_count: int = 0
    unmatched_count: int = 0
    only_in_standard_count: int = 0
    only_in_prediction_count: int = 0
    total_standard: int = 0
    total_prediction: int = 0
    correct_field_count: int = 0
    total_field_count: int = 0
    unmatched: List[Dict] = None
    only_in_standard: List[Dict] = None
    only_in_prediction: List[Dict] = None

    def __post_init__(self):
        if self.unmatched is None:
            self.unmatched = []
        if self.only_in_standard is None:
            self.only_in_standard = []
        if self.only_in_prediction is None:
            self.only_in_prediction = []

    @property
    def invoice_accuracy(self) -> float:
        """票据级准确率"""
        if self.total_standard == 0:
            return 0.0
        return self.matched_count / self.total_standard

    @property
    def field_accuracy(self) -> float:
        """字段级准确率"""
        if self.total_field_count == 0:
            return 0.0
        return self.correct_field_count / self.total_field_count


class InvoiceComparer:
    """票据比较器"""
    
    # 默认的核心字段
    DEFAULT_CORE_FIELDS = ['totalAmount', 'invoiceDate', 'docType', 'currency', 'billToName', 'totalTaxAmount']
    
    def __init__(self, core_fields: List[str] = None, verbose: bool = False, name_overlap_threshold: float = 0.5):
        """
        初始化票据比较器
        
        Args:
            core_fields: 需要比较的核心字段列表，如果为None则使用默认字段
            verbose: 是否显示详细日志
            name_overlap_threshold: Name字段的重叠阈值，默认0.5（50%）
        """
        self.core_fields = core_fields if core_fields is not None else self.DEFAULT_CORE_FIELDS.copy()
        self.verbose = verbose
        self.name_overlap_threshold = name_overlap_threshold
        
        if self.verbose:
            print(f"[INFO] 使用的比较字段: {self.core_fields}")
            print(f"[INFO] Name字段重叠阈值: {self.name_overlap_threshold:.0%}")
    
    @classmethod
    def from_config_file(cls, config_path: Union[str, Path], verbose: bool = False) -> 'InvoiceComparer':
        """
        从配置文件创建比较器实例
        
        Args:
            config_path: 配置文件路径，JSON格式，包含 core_fields 字段
            verbose: 是否显示详细日志
            
        Returns:
            InvoiceComparer实例
        """
        config_path = Path(config_path)
        if not config_path.exists():
            raise FileNotFoundError(f"配置文件不存在: {config_path}")
        
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        core_fields = config.get('core_fields')
        if not core_fields or not isinstance(core_fields, list):
            raise ValueError("配置文件必须包含有效的 core_fields 数组")
        
        # 从配置文件读取Name字段重叠阈值，如果没有则使用默认值0.5
        name_overlap_threshold = config.get('name_overlap_threshold', 0.5)
        
        if verbose:
            print(f"[INFO] 从配置文件加载字段: {config_path}")
        
        return cls(core_fields=core_fields, verbose=verbose, name_overlap_threshold=name_overlap_threshold)
    
    @classmethod
    def generate_default_config(cls, output_path: Union[str, Path]) -> None:
        """
        生成默认配置文件
        
        Args:
            output_path: 输出配置文件路径
        """
        config = {
            "core_fields": cls.DEFAULT_CORE_FIELDS,
            "name_overlap_threshold": 0.5,
            "description": "票据比较默认字段配置",
            "field_descriptions": {
                "totalAmount": "总金额",
                "invoiceDate": "开票日期", 
                "docType": "文档类型",
                "currency": "货币类型",
                "billToName": "收票方名称",
                "totalTaxAmount": "总税额"
            },
            "settings_descriptions": {
                "name_overlap_threshold": "Name字段重叠阈值，0.5表示50%重叠即可匹配"
            }
        }
        
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
        
        print(f"默认配置文件已生成: {output_path}")
    
    def log(self, message: str):
        """记录日志"""
        if self.verbose:
            print(f"[INFO] {message}")
    
    def get_core_fields(self) -> List[str]:
        """获取当前配置的核心字段列表"""
        return self.core_fields.copy()
    
    def set_core_fields(self, fields: List[str]):
        """设置核心字段列表"""
        if not fields:
            raise ValueError("字段列表不能为空")
        self.core_fields = fields.copy()
        if self.verbose:
            print(f"[INFO] 更新比较字段为: {self.core_fields}")
    
    def normalize_amount(self, amount: Any) -> float:
        """标准化金额字段，支持int/float/str"""
        if amount is None:
            return 0.0
        if isinstance(amount, (int, float)):
            return float(amount)
        if isinstance(amount, str):
            # 移除逗号和其他分隔符
            amount_str = re.sub(r'[,\s]', '', amount)
            try:
                return float(amount_str)
            except ValueError:
                return 0.0
        return 0.0
    
    def normalize_date(self, date_str: Any) -> str:
        """标准化日期字段，支持不同格式"""
        if date_str is None:
            return ""
        
        date_str = str(date_str).strip()
        if not date_str:
            return ""
        
        # 常见日期格式
        date_formats = [
            '%Y-%m-%d',
            '%Y/%m/%d',
            '%Y.%m.%d',
            '%Y-%m-%d %H:%M:%S',
            '%Y/%m/%d %H:%M:%S',
            '%Y.%m.%d %H:%M:%S'
        ]
        
        for fmt in date_formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
        
        # 如果所有格式都失败，返回原始字符串
        return date_str
    
    def normalize_string(self, text: Any) -> str:
        """标准化字符串字段，忽略大小写和空格"""
        if text is None:
            return ""
        return str(text).strip().lower()
    
    def normalize_name_field(self, name: Any) -> set:
        """
        标准化Name字段，返回单词集合用于比较
        对含有Name（不区分大小写）的字段进行特殊处理
        """
        if name is None:
            return set()
        
        name_str = str(name).strip()
        if not name_str:
            return set()
        
        # 移除常见的标点符号和分隔符
        cleaned = re.sub(r'[^\w\u4e00-\u9fff\s]', ' ', name_str)
        
        # 分割成单词/词汇
        words = []
        for word in cleaned.split():
            word = word.strip().lower()
            if word:  # 过滤空字符串
                words.append(word)
        
        return set(words)
    
    def compare_name_fields(self, name1: Any, name2: Any, overlap_threshold: float = 0.5) -> bool:
        """
        比较两个Name字段，使用重叠度匹配
        
        Args:
            name1: 标准Name字段值
            name2: 预测Name字段值  
            overlap_threshold: 重叠阈值，默认0.5（50%）
            
        Returns:
            bool: 是否匹配（重叠度达到阈值）
        """
        words1 = self.normalize_name_field(name1)
        words2 = self.normalize_name_field(name2)
        
        # 如果其中一个为空，则不匹配
        if not words1 or not words2:
            return words1 == words2  # 都为空时返回True，否则False
        
        # 计算重叠度：交集大小 / 较小集合的大小
        intersection = words1.intersection(words2)
        min_size = min(len(words1), len(words2))
        
        if min_size == 0:
            return False
        
        overlap_ratio = len(intersection) / min_size
        
        if self.verbose:
            self.log(f"Name字段比较: '{name1}' vs '{name2}', 重叠度: {overlap_ratio:.2f}")
        
        return overlap_ratio >= overlap_threshold
    
    def is_name_field(self, field_name: str) -> bool:
        """判断字段是否为Name字段（不区分大小写）"""
        return 'name' in field_name.lower()
    
    def extract_core_fields(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """提取核心字段"""
        core_data = {}
        for field in self.core_fields:
            core_data[field] = invoice.get(field)
        return core_data
    
    def normalize_invoice(self, invoice: Dict[str, Any]) -> Dict[str, Any]:
        """标准化单张票据的核心字段"""
        normalized = {}
        
        for field in self.core_fields:
            value = invoice.get(field)
            
            if self.is_name_field(field):
                # Name字段保持原始值，在比较时使用特殊逻辑
                normalized[field] = value
            elif field in ['totalAmount', 'totalTaxAmount']:
                # 金额字段
                normalized[field] = self.normalize_amount(value)
            elif field in ['invoiceDate']:
                # 日期字段
                normalized[field] = self.normalize_date(value)
            else:
                # 其他字符串字段
                normalized[field] = self.normalize_string(value)
        
        return normalized
    
    def invoices_equal(self, inv1: Dict[str, Any], inv2: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """
        比较两张票据是否相等
        返回：(是否相等, 不同的字段列表)
        """
        norm1 = self.normalize_invoice(inv1)
        norm2 = self.normalize_invoice(inv2)
        
        diff_fields = []
        for field in self.core_fields:
            if self.is_name_field(field):
                # Name字段使用特殊比较逻辑
                if not self.compare_name_fields(norm1.get(field), norm2.get(field), self.name_overlap_threshold):
                    diff_fields.append(field)
            else:
                # 其他字段使用精确匹配
                if norm1.get(field) != norm2.get(field):
                    diff_fields.append(field)
        
        return len(diff_fields) == 0, diff_fields
    
    def load_data(self, data: Union[str, Path, List[Dict]]) -> List[Dict[str, Any]]:
        """
        加载数据，支持多种输入格式
        
        Args:
            data: JSON字符串、文件路径或已解析的列表
            
        Returns:
            票据列表
        """
        if isinstance(data, list):
            return data
        elif isinstance(data, Path):
            # 明确的文件路径对象
            if data.exists():
                self.log(f"从文件读取数据: {data}")
                with open(data, 'r', encoding='utf-8') as f:
                    content = f.read()
                try:
                    return json.loads(content)
                except json.JSONDecodeError as e:
                    raise ValueError(f"文件 {data} JSON解析错误: {e}")
            else:
                raise ValueError(f"文件不存在: {data}")
        elif isinstance(data, str):
            # 字符串：可能是文件路径或JSON字符串
            # 先尝试作为JSON解析，如果失败再尝试作为文件路径
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                # JSON解析失败，尝试作为文件路径
                path = Path(data)
                if path.exists():
                    self.log(f"从文件读取数据: {path}")
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    try:
                        return json.loads(content)
                    except json.JSONDecodeError as e:
                        raise ValueError(f"文件 {path} JSON解析错误: {e}")
                else:
                    raise ValueError(f"既不是有效的JSON字符串，也不是存在的文件路径: {data}")
        else:
            raise ValueError("不支持的数据格式")
    
    def compare_invoices(self, standard_data: Union[str, Path, List[Dict]], 
                        prediction_data: Union[str, Path, List[Dict]]) -> Dict[str, Any]:
        """
        比较标准票据和预测票据
        
        Args:
            standard_data: 标准票据数据
            prediction_data: 预测票据数据
            
        Returns:
            比较结果字典
        """
        # 加载数据
        standard_invoices = self.load_data(standard_data)
        prediction_invoices = self.load_data(prediction_data)
        
        if not isinstance(standard_invoices, list) or not isinstance(prediction_invoices, list):
            raise ValueError("输入数据必须是数组格式")
        
        self.log(f"标准票据数量: {len(standard_invoices)}")
        self.log(f"预测票据数量: {len(prediction_invoices)}")
        
        result = CompareResult()
        result.total_standard = len(standard_invoices)
        result.total_prediction = len(prediction_invoices)
        
        # 计算实际的total_field_count：只统计docType为invoice或receipt的票据
        actual_field_count = 0
        for invoice in standard_invoices:
            doc_type = invoice.get('docType', '').lower()
            if doc_type in ['invoice', 'receipt']:
                actual_field_count += len(self.core_fields)
        result.total_field_count = actual_field_count
        
        if self.verbose:
            valid_invoices = sum(1 for inv in standard_invoices if inv.get('docType', '').lower() in ['invoice', 'receipt'])
            self.log(f"有效票据数量 (docType为invoice/receipt): {valid_invoices}")
            self.log(f"实际字段总数: {actual_field_count}")
        
        # 创建预测票据的副本，用于标记已匹配的票据
        remaining_predictions = list(range(len(prediction_invoices)))
        
        # 遍历标准票据，寻找匹配
        for std_idx, std_invoice in enumerate(standard_invoices):
            self.log(f"处理标准票据 {std_idx + 1}/{len(standard_invoices)}")
            
            # 检查票据类型是否有效
            std_doc_type = std_invoice.get('docType', '').lower()
            is_valid_type = std_doc_type in ['invoice', 'receipt']
            
            std_core = self.extract_core_fields(std_invoice)
            
            # 在剩余的预测票据中寻找匹配
            found_idx = -1
            diff_fields = []
            
            for i, pred_idx in enumerate(remaining_predictions):
                pred_invoice = prediction_invoices[pred_idx]
                is_equal, fields_diff = self.invoices_equal(std_invoice, pred_invoice)
                
                if is_equal:
                    # 完全匹配
                    found_idx = i
                    diff_fields = []
                    result.matched_count += 1
                    # 只对有效类型的票据统计字段
                    if is_valid_type:
                        result.correct_field_count += len(self.core_fields)
                    self.log(f"找到完全匹配的票据")
                    break
                elif len(fields_diff) < len(self.core_fields):
                    # 部分匹配（用于unmatched）
                    norm_std = self.normalize_invoice(std_invoice)
                    norm_pred = self.normalize_invoice(pred_invoice)
                    
                    # 使用主键进行识别
                    key_fields = ['totalAmount', 'invoiceDate', 'docType']
                    key_match = all(norm_std.get(f) == norm_pred.get(f) for f in key_fields)
                    
                    if key_match:
                        found_idx = i
                        diff_fields = fields_diff
                        result.unmatched_count += 1
                        # 只对有效类型的票据统计字段
                        if is_valid_type:
                            correct_fields = len(self.core_fields) - len(diff_fields)
                            result.correct_field_count += correct_fields
                        self.log(f"找到部分匹配的票据，差异字段: {diff_fields}")
                        break
            
            if found_idx >= 0:
                # 找到匹配（完全或部分）
                pred_idx = remaining_predictions.pop(found_idx)
                
                if diff_fields:
                    # 部分匹配，添加到unmatched
                    pred_core = self.extract_core_fields(prediction_invoices[pred_idx])
                    result.unmatched.append({
                        'standard': std_core,
                        'prediction': pred_core,
                        'diff_fields': diff_fields
                    })
            else:
                # 在预测中没找到，添加到only_in_standard
                result.only_in_standard_count += 1
                result.only_in_standard.append(std_core)
                self.log("标准票据在预测中未找到匹配")
        
        # 剩余的预测票据都是only_in_prediction
        for pred_idx in remaining_predictions:
            pred_core = self.extract_core_fields(prediction_invoices[pred_idx])
            result.only_in_prediction.append(pred_core)
        
        result.only_in_prediction_count = len(remaining_predictions)
        
        # 添加准确率计算
        invoice_accuracy = result.invoice_accuracy
        field_accuracy = result.field_accuracy
        
        self.log(f"票据级准确率: {invoice_accuracy:.2%}")
        self.log(f"字段级准确率: {field_accuracy:.2%}")
        
        # 转换为字典格式
        return {
            'matched_count': result.matched_count,
            'unmatched_count': result.unmatched_count,
            'only_in_standard_count': result.only_in_standard_count,
            'only_in_prediction_count': result.only_in_prediction_count,
            'total_standard': result.total_standard,
            'total_prediction': result.total_prediction,
            'correct_field_count': result.correct_field_count,
            'total_field_count': result.total_field_count,
            'invoice_accuracy': round(invoice_accuracy, 4),
            'field_accuracy': round(field_accuracy, 4),
            'unmatched': result.unmatched,
            'only_in_standard': result.only_in_standard,
            'only_in_prediction': result.only_in_prediction
        }
    
    def save_result(self, result: Dict[str, Any], output_path: Union[str, Path]):
        """保存比较结果到文件"""
        output_path = Path(output_path)
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        self.log(f"结果已保存到: {output_path}")


def main():
    """命令行接口"""
    parser = argparse.ArgumentParser(description='票据对比工具')
    parser.add_argument('--standard', '-s',
                       help='标准票据数据文件路径或JSON字符串')
    parser.add_argument('--prediction', '-p',
                       help='预测票据数据文件路径或JSON字符串')
    parser.add_argument('--output', '-o', 
                       help='输出结果文件路径')
    parser.add_argument('--fields', '-f', nargs='+',
                       help='自定义要比较的字段列表，如：--fields totalAmount invoiceDate docType')
    parser.add_argument('--name-threshold', '-t', type=float, default=0.5,
                       help='Name字段重叠阈值（0.0-1.0），默认0.5即50%%重叠')
    parser.add_argument('--config', '-c',
                       help='配置文件路径，JSON格式，包含core_fields字段')
    parser.add_argument('--generate-config', '-g',
                       help='生成默认配置文件到指定路径')
    parser.add_argument('--verbose', '-v', action='store_true',
                       help='显示详细日志')
    
    args = parser.parse_args()
    
    # 生成配置文件
    if args.generate_config:
        InvoiceComparer.generate_default_config(args.generate_config)
        return 0
    
    # 检查必要参数
    if not args.standard or not args.prediction:
        print("错误: 必须提供 --standard 和 --prediction 参数")
        return 1
    
    # 参数冲突检查
    if args.fields and args.config:
        print("错误: --fields 和 --config 参数不能同时使用")
        return 1
    
    # 创建比较器实例
    if args.config:
        comparer = InvoiceComparer.from_config_file(args.config, verbose=args.verbose)
        # 如果命令行指定了阈值，覆盖配置文件中的设置
        if hasattr(args, 'name_threshold') and args.name_threshold != 0.5:
            comparer.name_overlap_threshold = args.name_threshold
            if args.verbose:
                print(f"[INFO] 使用命令行指定的Name字段重叠阈值: {args.name_threshold:.0%}")
    else:
        comparer = InvoiceComparer(core_fields=args.fields, verbose=args.verbose, 
                                   name_overlap_threshold=args.name_threshold)
    
    try:
        result = comparer.compare_invoices(args.standard, args.prediction)
        
        if args.output:
            comparer.save_result(result, args.output)
        else:
            print(json.dumps(result, ensure_ascii=False, indent=2))
            
    except Exception as e:
        print(f"错误: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    # 如果没有命令行参数，运行示例
    import sys
    if len(sys.argv) == 1:
        print("运行示例数据...")
        standard_data = """[{"docType": "invoice", "invoiceDate": "2025-04-06", "totalAmount": 183700, "totalTaxAmount": 16700, "currency": "JPY", "billToName": "ハイセンスジャパン 株式会社"}, {"docType": "invoice", "invoiceDate": "2025-05-02", "totalAmount": 606100, "totalTaxAmount": 55100, "currency": "JPY", "billToName": "ハイセンスジャパン 株式会社"}]"""
        
        prediction_data = """[{"docType": "invoice", "invoiceDate": "2025-04-06", "totalAmount": "183700", "totalTaxAmount": "16700", "currency": "JPY", "billToName": "ハピネツジャパン 株式会社 商品管理部 商品プロモーションG 本堂 様"}]"""
        
        print("\n示例1: 使用默认字段")
        comparer = InvoiceComparer(verbose=True)
        result = comparer.compare_invoices(standard_data, prediction_data)
        print("\n结果:")
        print(json.dumps(result, ensure_ascii=False, indent=2))
        
        print("\n" + "="*50)
        print("\n示例2: 使用自定义字段（只比较金额、日期和类型）")
        custom_fields = ['totalAmount', 'invoiceDate', 'docType']
        comparer2 = InvoiceComparer(core_fields=custom_fields, verbose=True)
        result2 = comparer2.compare_invoices(standard_data, prediction_data)
        print("\n结果:")
        print(json.dumps(result2, ensure_ascii=False, indent=2))
    else:
        exit(main()) 
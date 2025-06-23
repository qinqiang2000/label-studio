#!/usr/bin/env python3
"""
票据匹配策略模块
支持多种匹配策略：字段匹配、位置匹配、混合匹配等
"""

from enum import Enum
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class MatchingStrategyType(Enum):
    """匹配策略类型枚举"""
    FIELD_BASED = "field_based"           # 基于字段选择（现有方式）
    POSITION_BASED = "position_based"     # 基于位置匹配
    HYBRID = "hybrid"                     # 混合策略
    CUSTOM = "custom"                     # 自定义策略


class BaseMatchingStrategy(ABC):
    """匹配策略基类"""
    
    def __init__(self, config: Dict[str, Any] = None):
        """
        初始化匹配策略
        
        Args:
            config: 策略配置参数
        """
        self.config = config or {}
        self.verbose = self.config.get('verbose', False)
    
    def log(self, message: str):
        """记录日志"""
        if self.verbose:
            logger.info(f"[{self.__class__.__name__}] {message}")
    
    @abstractmethod
    def get_primary_key_fields(self, all_fields: List[str]) -> List[str]:
        """
        获取主键字段列表
        
        Args:
            all_fields: 所有可用字段列表
            
        Returns:
            主键字段列表
        """
        pass
    
    @abstractmethod
    def find_matching_invoice(self, 
                            std_invoice: Dict[str, Any], 
                            prediction_invoices: List[Dict[str, Any]], 
                            remaining_indices: List[int],
                            comparer) -> Tuple[Optional[int], List[str]]:
        """
        在预测票据中找到匹配的票据
        
        Args:
            std_invoice: 标准票据
            prediction_invoices: 预测票据列表
            remaining_indices: 剩余可匹配的预测票据索引
            comparer: 票据比较器实例
            
        Returns:
            (匹配的预测票据索引, 差异字段列表)，如果没找到匹配则返回(None, [])
        """
        pass


class FieldBasedStrategy(BaseMatchingStrategy):
    """基于字段的匹配策略（现有逻辑的增强版）"""
    
    def get_primary_key_fields(self, all_fields: List[str]) -> List[str]:
        """
        基于字段类型智能选择主键字段
        """
        # 如果配置了自定义主键字段，直接使用
        custom_primary_fields = self.config.get('custom_primary_fields', [])
        if custom_primary_fields:
            # 验证自定义字段是否在可用字段中
            valid_fields = [field for field in custom_primary_fields if field in all_fields]
            if valid_fields:
                self.log(f"🎯 使用自定义主键字段: {valid_fields}")
                self.log(f"📋 可用字段列表: {all_fields}")
                self.log(f"✅ 有效的自定义主键: {valid_fields}")
                return valid_fields
            else:
                self.log(f"⚠️ 自定义主键字段无效，回退到自动识别")
                self.log(f"📋 配置的自定义字段: {custom_primary_fields}")
                self.log(f"📋 可用字段列表: {all_fields}")
        
        key_fields = []
        
        self.log(f"🔍 开始自动识别主键字段...")
        self.log(f"📋 所有可用字段: {all_fields}")
        
        # 1. 优先选择具有唯一性的票据号码类字段
        receipt_num_keywords = self.config.get('receipt_num_keywords', 
                                             ['num', 'number', 'id', 'code', 'receipt', 'invoice', 'transaction'])
        self.log(f"🔑 票据号码关键词: {receipt_num_keywords}")
        
        for field in all_fields:
            field_lower = field.lower()
            if any(keyword in field_lower for keyword in receipt_num_keywords):
                key_fields.append(field)
                self.log(f"🎫 识别到票据号码字段: {field}")
                break
        
        # 2. 金额字段作为辅助主键
        amount_keywords = self.config.get('amount_keywords',
                                        ['amount', 'tax', 'total', 'sum', 'money', 'price', 'cost', 'fee'])
        self.log(f"💰 金额字段关键词: {amount_keywords}")
        
        for field in all_fields:
            field_lower = field.lower()
            if any(keyword in field_lower for keyword in amount_keywords):
                key_fields.append(field)
                self.log(f"💰 识别到金额字段: {field}")
                break
        
        # 3. 如果有docType字段，也加入主键
        if 'docType' in all_fields:
            key_fields.append('docType')
            self.log(f"📄 识别到文档类型字段: docType")
        
        # 4. 根据配置决定是否包含日期字段
        include_date = self.config.get('include_date_in_key', False)
        self.log(f"📅 是否包含日期字段: {include_date}")
        
        if include_date and len(key_fields) < 3:
            date_keywords = self.config.get('date_keywords',
                                          ['date', 'time', 'when', 'day', 'month', 'year'])
            self.log(f"📅 日期字段关键词: {date_keywords}")
            
            for field in all_fields:
                field_lower = field.lower()
                if any(keyword in field_lower for keyword in date_keywords):
                    key_fields.append(field)
                    self.log(f"📅 识别到日期字段: {field}")
                    break
        elif include_date:
            self.log(f"⏭️ 跳过日期字段 (已有足够主键字段: {len(key_fields)})")
        else:
            self.log(f"⏭️ 跳过日期字段 (include_date_in_key=False)")
        
        # 5. 如果没有找到合适的主键字段，使用配置的默认字段或前几个字段
        if not key_fields:
            default_key_count = self.config.get('default_key_count', 2)
            key_fields = all_fields[:default_key_count]
            self.log(f"⚠️ 未找到关键字段，使用前{default_key_count}个字段: {key_fields}")
        
        self.log(f"🎯 最终选择的主键字段: {key_fields}")
        self.log(f"📊 主键字段数量: {len(key_fields)}")
        return key_fields
    
    def find_matching_invoice(self, 
                            std_invoice: Dict[str, Any], 
                            prediction_invoices: List[Dict[str, Any]], 
                            remaining_indices: List[int],
                            comparer) -> Tuple[Optional[int], List[str]]:
        """
        基于字段匹配寻找对应票据
        """
        key_fields = self.get_primary_key_fields(comparer.core_fields)
        
        self.log(f"🔍 开始字段匹配，标准票据: {std_invoice}")
        self.log(f"🎯 使用主键字段: {key_fields}")
        self.log(f"📋 待匹配的预测票据索引: {remaining_indices}")
        
        for i, pred_idx in enumerate(remaining_indices):
            pred_invoice = prediction_invoices[pred_idx]
            self.log(f"📊 正在比较第{i+1}个预测票据 (索引 {pred_idx}): {pred_invoice}")
            
            is_equal, diff_fields = comparer.invoices_equal(std_invoice, pred_invoice)
            
            if is_equal:
                # 完全匹配
                self.log(f"✅ 找到完全匹配的票据 (索引 {pred_idx})")
                return pred_idx, []
            elif len(diff_fields) < len(comparer.core_fields):
                # 部分匹配，检查主键
                self.log(f"🔍 部分匹配，检查主键字段，差异字段: {diff_fields}")
                
                norm_std = comparer.normalize_invoice(std_invoice)
                norm_pred = comparer.normalize_invoice(pred_invoice)
                
                self.log(f"📋 标准票据标准化: {norm_std}")
                self.log(f"📋 预测票据标准化: {norm_pred}")
                
                key_matches = {}
                for f in key_fields:
                    if f in norm_std and f in norm_pred:
                        std_val = norm_std.get(f)
                        pred_val = norm_pred.get(f)
                        match = std_val == pred_val
                        key_matches[f] = {
                            'std': std_val,
                            'pred': pred_val,
                            'match': match
                        }
                        self.log(f"🔑 主键字段 {f}: 标准='{std_val}', 预测='{pred_val}', 匹配={match}")
                
                key_match = all(key_matches[f]['match'] for f in key_matches)
                self.log(f"🎯 主键匹配结果: {key_match}")
                
                if key_match:
                    self.log(f"✅ 找到部分匹配的票据 (索引 {pred_idx})，差异字段: {diff_fields}")
                    return pred_idx, diff_fields
                else:
                    self.log(f"❌ 主键不匹配，继续寻找")
            else:
                self.log(f"❌ 差异字段过多 ({len(diff_fields)}/{len(comparer.core_fields)})，跳过")
        
        self.log(f"❌ 未找到匹配的票据")
        return None, []


class PositionBasedStrategy(BaseMatchingStrategy):
    """基于位置的匹配策略"""
    
    def get_primary_key_fields(self, all_fields: List[str]) -> List[str]:
        """
        位置匹配不依赖主键字段，返回空列表
        """
        return []
    
    def find_matching_invoice(self, 
                            std_invoice: Dict[str, Any], 
                            prediction_invoices: List[Dict[str, Any]], 
                            remaining_indices: List[int],
                            comparer) -> Tuple[Optional[int], List[str]]:
        """
        基于位置匹配票据
        """
        # 获取标准票据在原始列表中的位置
        std_position = std_invoice.get('_original_position', -1)
        tolerance = self.config.get('position_tolerance', 1)
        
        if std_position == -1:
            # 如果没有位置信息，使用第一个可用的预测票据
            if remaining_indices:
                pred_idx = remaining_indices[0]
                pred_invoice = prediction_invoices[pred_idx]
                _, diff_fields = comparer.invoices_equal(std_invoice, pred_invoice)
                self.log(f"无位置信息，使用第一个可用票据 (索引 {pred_idx})")
                return pred_idx, diff_fields
            return None, []
        
        # 在容差范围内寻找匹配的位置
        for pred_idx in remaining_indices:
            pred_position = pred_idx  # 使用索引作为位置
            
            if abs(std_position - pred_position) <= tolerance:
                pred_invoice = prediction_invoices[pred_idx]
                _, diff_fields = comparer.invoices_equal(std_invoice, pred_invoice)
                self.log(f"找到位置匹配的票据 (标准位置 {std_position}, 预测位置 {pred_position})")
                return pred_idx, diff_fields
        
        # 如果在容差范围内没找到，使用最接近的位置
        if remaining_indices:
            closest_idx = min(remaining_indices, 
                             key=lambda idx: abs(std_position - idx))
            pred_invoice = prediction_invoices[closest_idx]
            _, diff_fields = comparer.invoices_equal(std_invoice, pred_invoice)
            self.log(f"使用最接近位置的票据 (标准位置 {std_position}, 预测位置 {closest_idx})")
            return closest_idx, diff_fields
        
        return None, []


class HybridStrategy(BaseMatchingStrategy):
    """混合匹配策略：先尝试字段匹配，失败后使用位置匹配"""
    
    def __init__(self, config: Dict[str, Any] = None):
        super().__init__(config)
        
        # 初始化子策略
        field_config = self.config.get('field_strategy_config', {})
        field_config['verbose'] = self.verbose
        self.field_strategy = FieldBasedStrategy(field_config)
        
        position_config = self.config.get('position_strategy_config', {})
        position_config['verbose'] = self.verbose
        self.position_strategy = PositionBasedStrategy(position_config)
    
    def get_primary_key_fields(self, all_fields: List[str]) -> List[str]:
        """
        使用字段策略的主键字段
        """
        return self.field_strategy.get_primary_key_fields(all_fields)
    
    def find_matching_invoice(self, 
                            std_invoice: Dict[str, Any], 
                            prediction_invoices: List[Dict[str, Any]], 
                            remaining_indices: List[int],
                            comparer) -> Tuple[Optional[int], List[str]]:
        """
        混合匹配：先字段匹配，后位置匹配
        """
        # 1. 首先尝试字段匹配
        pred_idx, diff_fields = self.field_strategy.find_matching_invoice(
            std_invoice, prediction_invoices, remaining_indices, comparer)
        
        if pred_idx is not None:
            self.log(f"字段匹配成功 (索引 {pred_idx})")
            return pred_idx, diff_fields
        
        # 2. 字段匹配失败，尝试位置匹配
        self.log("字段匹配失败，尝试位置匹配")
        pred_idx, diff_fields = self.position_strategy.find_matching_invoice(
            std_invoice, prediction_invoices, remaining_indices, comparer)
        
        if pred_idx is not None:
            self.log(f"位置匹配成功 (索引 {pred_idx})")
            return pred_idx, diff_fields
        
        self.log("混合匹配失败")
        return None, []


class CustomStrategy(BaseMatchingStrategy):
    """自定义匹配策略"""
    
    def get_primary_key_fields(self, all_fields: List[str]) -> List[str]:
        """
        使用配置中指定的主键字段
        """
        primary_fields = self.config.get('primary_fields', [])
        
        # 验证主键字段是否在可用字段中
        valid_fields = [field for field in primary_fields if field in all_fields]
        
        if not valid_fields:
            # 如果没有有效的主键字段，回退到默认策略
            self.log("自定义主键字段无效，回退到默认策略")
            default_strategy = FieldBasedStrategy(self.config)
            return default_strategy.get_primary_key_fields(all_fields)
        
        self.log(f"使用自定义主键字段: {valid_fields}")
        return valid_fields
    
    def find_matching_invoice(self, 
                            std_invoice: Dict[str, Any], 
                            prediction_invoices: List[Dict[str, Any]], 
                            remaining_indices: List[int],
                            comparer) -> Tuple[Optional[int], List[str]]:
        """
        使用自定义逻辑进行匹配
        """
        custom_logic = self.config.get('custom_logic', {})
        logic_type = custom_logic.get('type', 'field_based')
        
        if logic_type == 'position_based':
            strategy = PositionBasedStrategy(custom_logic)
        elif logic_type == 'hybrid':
            strategy = HybridStrategy(custom_logic)
        else:
            # 默认使用字段匹配
            strategy = FieldBasedStrategy(custom_logic)
        
        return strategy.find_matching_invoice(
            std_invoice, prediction_invoices, remaining_indices, comparer)


def create_matching_strategy(strategy_type: str, config: Dict[str, Any] = None) -> BaseMatchingStrategy:
    """
    工厂方法：创建匹配策略实例
    
    Args:
        strategy_type: 策略类型
        config: 策略配置
        
    Returns:
        匹配策略实例
    """
    config = config or {}
    
    if strategy_type == MatchingStrategyType.FIELD_BASED.value:
        return FieldBasedStrategy(config)
    elif strategy_type == MatchingStrategyType.POSITION_BASED.value:
        return PositionBasedStrategy(config)
    elif strategy_type == MatchingStrategyType.HYBRID.value:
        return HybridStrategy(config)
    elif strategy_type == MatchingStrategyType.CUSTOM.value:
        return CustomStrategy(config)
    else:
        logger.warning(f"未知的匹配策略类型: {strategy_type}，使用默认的字段匹配策略")
        return FieldBasedStrategy(config)


def get_default_strategy_config(document_type: str) -> Dict[str, Any]:
    """
    获取不同文档类型的默认策略配置
    
    Args:
        document_type: 文档类型
        
    Returns:
        默认策略配置
    """
    if document_type == 'invoice':
        return {
            'type': MatchingStrategyType.FIELD_BASED.value,
            'include_date_in_key': False,
            'default_key_count': 3,
            'receipt_num_keywords': ['invoice', 'number', 'id'],
            'amount_keywords': ['amount', 'total', 'tax']
        }
    elif document_type == 'bank_receipt':
        return {
            'type': MatchingStrategyType.POSITION_BASED.value,
            'position_tolerance': 0,  # 严格位置匹配
            'fallback_strategy': MatchingStrategyType.FIELD_BASED.value
        }
    elif document_type == 'receipt':
        return {
            'type': MatchingStrategyType.FIELD_BASED.value,
            'include_date_in_key': True,
            'default_key_count': 2
        }
    else:
        # 默认配置
        return {
            'type': MatchingStrategyType.FIELD_BASED.value,
            'include_date_in_key': False,
            'default_key_count': 2
        } 
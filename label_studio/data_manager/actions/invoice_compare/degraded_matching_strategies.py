#!/usr/bin/env python3
"""
降级匹配策略系统
实现从完整字段匹配到单字段匹配的智能降级逻辑
"""

import logging
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger(__name__)


class MatchingMode(Enum):
    """匹配模式枚举"""
    FIELD_BASED = "field_based"      # 基于字段匹配（支持降级）
    POSITION_BASED = "position_based"  # 基于位置匹配
    AUTO = "auto"                    # 自动选择最佳模式


class DegradedMatchingStrategy:
    """
    降级匹配策略
    核心思想：从完整字段组合逐步降级到单个字段，最后回退到位置匹配
    """
    
    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.verbose = self.config.get('verbose', False)
        self.mode = MatchingMode(self.config.get('mode', 'field_based'))
        
    def log(self, message: str):
        """输出调试信息"""
        if self.verbose:
            print(f"[DegradedMatching] {message}")
            
    def get_primary_key_combinations(self, all_fields: List[str]) -> List[List[str]]:
        """
        获取主键字段的降级组合
        返回从最完整到最简单的字段组合列表
        
        用户交互优化：
        - 如果用户配置了字段，直接使用
        - 如果用户配置为空或["_position"]，使用顺序匹配
        - 预设文档类型有默认主键配置
        """
        # 1. 检查是否有用户指定的字段
        specified_fields = self.config.get('primary_fields', [])
        
        # 优化：如果配置为空或者只有"_position"，直接使用顺序匹配
        if not specified_fields or specified_fields == ["_position"]:
            self.log(f"📍 使用顺序匹配（用户配置为空或_position）")
            return [["_position"]]
        
        # 2. 验证用户指定的字段
        valid_fields = [field for field in specified_fields if field in all_fields]
        if valid_fields:
            self.log(f"🎯 使用用户指定的主键字段: {valid_fields}")
            return self._generate_degraded_combinations(valid_fields)
        else:
            self.log(f"⚠️ 用户指定字段无效: {specified_fields}")
            self.log(f"📋 可用字段: {all_fields}")
            self.log(f"📍 回退到顺序匹配")
            return [["_position"]]
    
    # 注意：自动识别字段的逻辑已被移除
    # 当前系统只支持两种模式：
    # 1. 用户/预设指定的主键字段（降级匹配）
    # 2. 位置匹配（当字段为空时）
    
    def _generate_degraded_combinations(self, fields: List[str]) -> List[List[str]]:
        """
        生成降级字段组合
        例如：["docType", "invoiceDate", "totalAmount"] 
        -> [["docType", "invoiceDate", "totalAmount"], ["invoiceDate", "totalAmount"], ["totalAmount"]]
        """
        if not fields:
            return [["_position"]]  # 回退到位置匹配
        
        combinations = []
        
        # 从完整组合开始，逐步减少字段
        for i in range(len(fields)):
            combination = fields[i:]
            combinations.append(combination)
            self.log(f"🔄 生成降级组合 {i+1}: {combination}")
        
        # 最后添加位置匹配作为终极回退
        if self.mode != MatchingMode.POSITION_BASED:
            combinations.append(["_position"])
            self.log(f"🔄 添加位置匹配作为最终回退")
        
        return combinations
    
    def find_matching_invoice(self, 
                            std_invoice: Dict[str, Any], 
                            prediction_invoices: List[Dict[str, Any]], 
                            remaining_indices: List[int],
                            comparer) -> Tuple[Optional[int], List[str], str]:
        """
        使用降级策略寻找匹配的票据
        返回: (匹配索引, 差异字段列表, 使用的匹配策略)
        """
        all_fields = comparer.core_fields
        key_combinations = self.get_primary_key_combinations(all_fields)
        
        self.log(f"🔍 开始降级匹配，标准票据: {std_invoice}")
        self.log(f"📋 待匹配预测票据索引: {remaining_indices}")
        self.log(f"🎯 降级策略组合: {key_combinations}")
        
        # 逐级尝试每个降级组合
        for level, key_fields in enumerate(key_combinations):
            self.log(f"\n🔄 尝试降级级别 {level + 1}: {key_fields}")
            
            if key_fields == ["_position"]:
                # 位置匹配
                result = self._position_based_match(std_invoice, prediction_invoices, 
                                                  remaining_indices, comparer)
                if result[0] is not None:
                    strategy_used = f"位置匹配"
                    self.log(f"✅ 位置匹配成功")
                    return result[0], result[1], strategy_used
            else:
                # 字段匹配
                result = self._field_based_match(std_invoice, prediction_invoices, 
                                               remaining_indices, comparer, key_fields)
                if result[0] is not None:
                    strategy_used = f"字段匹配(级别{level + 1}): {key_fields}"
                    self.log(f"✅ 字段匹配成功，级别 {level + 1}")
                    return result[0], result[1], strategy_used
        
        self.log(f"❌ 所有降级策略都失败")
        return None, [], "无匹配"
    
    def _field_based_match(self, 
                          std_invoice: Dict[str, Any], 
                          prediction_invoices: List[Dict[str, Any]], 
                          remaining_indices: List[int],
                          comparer,
                          key_fields: List[str]) -> Tuple[Optional[int], List[str]]:
        """基于字段的匹配"""
        for i, pred_idx in enumerate(remaining_indices):
            pred_invoice = prediction_invoices[pred_idx]
            self.log(f"  📊 比较预测票据 {i+1} (索引 {pred_idx})")
            
            # 先检查完整匹配
            is_equal, diff_fields = comparer.invoices_equal(std_invoice, pred_invoice)
            
            if is_equal:
                self.log(f"  ✅ 完全匹配")
                return pred_idx, []
            
            # 检查主键匹配
            norm_std = comparer.normalize_invoice(std_invoice)
            norm_pred = comparer.normalize_invoice(pred_invoice)
            
            key_matches = {}
            all_keys_match = True
            
            for field in key_fields:
                if field in norm_std and field in norm_pred:
                    std_val = norm_std.get(field)
                    pred_val = norm_pred.get(field)
                    match = std_val == pred_val
                    key_matches[field] = {
                        'std': std_val,
                        'pred': pred_val,
                        'match': match
                    }
                    self.log(f"  🔑 主键 {field}: '{std_val}' vs '{pred_val}' = {match}")
                    if not match:
                        all_keys_match = False
                else:
                    self.log(f"  ⚠️ 主键字段 {field} 缺失")
                    all_keys_match = False
            
            if all_keys_match and key_matches:
                self.log(f"  ✅ 主键匹配成功，差异字段: {diff_fields}")
                return pred_idx, diff_fields
            else:
                self.log(f"  ❌ 主键不匹配")
        
        return None, []
    
    def _position_based_match(self, 
                            std_invoice: Dict[str, Any], 
                            prediction_invoices: List[Dict[str, Any]], 
                            remaining_indices: List[int],
                            comparer) -> Tuple[Optional[int], List[str]]:
        """基于位置的匹配"""
        std_position = std_invoice.get('_original_position', -1)
        tolerance = self.config.get('position_tolerance', 0)
        
        self.log(f"  📍 标准票据位置: {std_position}, 容差: {tolerance}")
        
        if std_position == -1:
            # 没有位置信息，使用第一个可用的
            if remaining_indices:
                pred_idx = remaining_indices[0]
                pred_invoice = prediction_invoices[pred_idx]
                _, diff_fields = comparer.invoices_equal(std_invoice, pred_invoice)
                self.log(f"  📍 无位置信息，使用第一个 (索引 {pred_idx})")
                return pred_idx, diff_fields
            return None, []
        
        # 在容差范围内寻找
        for pred_idx in remaining_indices:
            if abs(std_position - pred_idx) <= tolerance:
                pred_invoice = prediction_invoices[pred_idx]
                _, diff_fields = comparer.invoices_equal(std_invoice, pred_invoice)
                self.log(f"  📍 位置匹配 (标准: {std_position}, 预测: {pred_idx})")
                return pred_idx, diff_fields
        
        # 使用最接近的位置
        if remaining_indices:
            closest_idx = min(remaining_indices, key=lambda idx: abs(std_position - idx))
            pred_invoice = prediction_invoices[closest_idx]
            _, diff_fields = comparer.invoices_equal(std_invoice, pred_invoice)
            self.log(f"  📍 使用最接近位置 (标准: {std_position}, 预测: {closest_idx})")
            return closest_idx, diff_fields
        
        return None, []


def get_default_degraded_config(document_type: str) -> Dict[str, Any]:
    """
    获取不同文档类型的默认降级配置
    注意：自动识别功能已移除，只支持指定字段或位置匹配
    """
    base_config = {
        'mode': 'field_based',
        'verbose': True,
        'position_tolerance': 0
    }
    
    # 所有类型都使用相同的基础配置
    # 具体的主键字段在 init_evaluation_configs.py 中预设
    return {
        **base_config,
        'primary_fields': [],  # 由评估配置或用户指定
    }


def create_degraded_matching_strategy(document_type: str, 
                                    custom_config: Dict[str, Any] = None) -> DegradedMatchingStrategy:
    """
    创建降级匹配策略实例
    """
    default_config = get_default_degraded_config(document_type)
    
    if custom_config:
        # 合并用户配置
        config = {**default_config, **custom_config}
    else:
        config = default_config
    
    return DegradedMatchingStrategy(config)


# 兼容性包装器，保持与现有代码的兼容
class FieldBasedDegradedStrategy(DegradedMatchingStrategy):
    """字段匹配的降级策略包装器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config['mode'] = 'field_based'
        super().__init__(config)
    
    def get_primary_key_fields(self, all_fields: List[str]) -> List[str]:
        """返回第一级（最完整）的主键字段组合"""
        combinations = self.get_primary_key_combinations(all_fields)
        if combinations and combinations[0] != ["_position"]:
            return combinations[0]
        return []


class PositionBasedDegradedStrategy(DegradedMatchingStrategy):
    """位置匹配的降级策略包装器"""
    
    def __init__(self, config: Dict[str, Any] = None):
        config = config or {}
        config['mode'] = 'position_based'
        super().__init__(config)
    
    def get_primary_key_fields(self, all_fields: List[str]) -> List[str]:
        """位置匹配不需要主键字段"""
        return [] 
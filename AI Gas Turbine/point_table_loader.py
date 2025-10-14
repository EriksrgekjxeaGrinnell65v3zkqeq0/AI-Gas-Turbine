import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional, Tuple
import logging
import re

logger = logging.getLogger(__name__)

class PointTableLoader:
    """点表加载和解析器"""
    
    def __init__(self, point_file_path: str):
        self.point_file_path = point_file_path
        self.point_data = None
        self.kks_mapping = {}
        self.alarm_thresholds = {}
        self.detection_config = {}
        self.safe_ranges = {}  # 运行安全区间存储
        self.positive_correlations = {}  # 正相关测点
        self.negative_correlations = {}  # 负相关测点
        
    def load_point_table(self) -> bool:
        """加载点表文件"""
        try:
            self.point_data = pd.read_excel(self.point_file_path, sheet_name='Sheet1')
            print(f"成功读取点表，共 {len(self.point_data)} 行数据")
            
            # 检查列名
            print(f"点表列名: {list(self.point_data.columns)}")
            
            # 首先构建所有KKS映射
            self._build_kks_mapping()
            
            # 然后解析其他数据
            self._parse_point_data()
            
            logger.info(f"成功加载点表，共 {len(self.kks_mapping)} 个测点")
            
            # 打印统计信息
            self._print_debug_info()
                
            return True
        except Exception as e:
            logger.error(f"加载点表失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _build_kks_mapping(self):
        """构建所有KKS映射"""
        valid_rows = 0
        for index, row in self.point_data.iterrows():
            try:
                # 跳过空行
                if pd.isna(row['kks']) or str(row['kks']).strip() == '':
                    continue
                    
                kks = str(row['kks']).strip()
                
                # 基本信息
                self.kks_mapping[kks] = {
                    'system': self._get_cell_value(row, '所属系统', '未知'),
                    'name': self._get_cell_value(row, '设备/测点名称', '未知'),
                    'description': self._get_cell_value(row, '点含义', ''),
                    'unit': self._get_cell_value(row, '单位', ''),
                    'index': self._get_cell_value(row, '序号', index)
                }
                valid_rows += 1
                
            except Exception as e:
                print(f"构建KKS映射第{index+1}行时出错: {e}")
                continue
        
        print(f"有效测点行数: {valid_rows}")
    
    def _get_cell_value(self, row, column, default_value):
        """安全获取单元格值"""
        try:
            if pd.isna(row[column]):
                return default_value
            value = str(row[column]).strip()
            return value if value else default_value
        except:
            return default_value
    
    def _parse_point_data(self):
        """解析点表数据"""
        parsed_count = 0
        for index, row in self.point_data.iterrows():
            try:
                # 跳过空行
                if pd.isna(row['kks']) or str(row['kks']).strip() == '':
                    continue
                    
                kks = str(row['kks']).strip()
                if kks not in self.kks_mapping:
                    continue
                
                # 报警阈值
                self.alarm_thresholds[kks] = {
                    'LLL': self._parse_threshold(row['LLL告警值']),
                    'LL': self._parse_threshold(row['LL告警值']),
                    'L': self._parse_threshold(row['L告警值']),
                    'H': self._parse_threshold(row['H告警值']),
                    'HH': self._parse_threshold(row['HH告警值']),
                    'HHH': self._parse_threshold(row['HHH告警值']),
                    'lower_limit': self._parse_threshold(row['测点下限']),
                    'upper_limit': self._parse_threshold(row['测点上限'])
                }
                
                # 检测配置
                self.detection_config[kks] = {
                    'fluctuation_detection': self._parse_boolean(row['波动检测']),
                    'fluctuation_range': self._parse_range(row['波动幅度']),
                    'mutation_detection': self._parse_boolean(row['突变检测']),
                    'mutation_range': self._parse_range(row['突变幅度']),
                    'trend_prediction': self._parse_boolean(row['趋势预测'])
                }
                
                # 运行安全区间 - 修复解析逻辑
                safe_range = self._parse_safe_range(row['运行安全区间'])
                if safe_range:
                    self.safe_ranges[kks] = safe_range
                    print(f"安全区间解析: {kks} -> {safe_range}")  # 调试输出
                
                # 正相关测点
                positive_corr = self._parse_correlation_points(row['正相关测点'])
                if positive_corr:
                    self.positive_correlations[kks] = positive_corr
                
                # 负相关测点
                negative_corr = self._parse_correlation_points(row['负相关测点'])
                if negative_corr:
                    self.negative_correlations[kks] = negative_corr
                
                parsed_count += 1
                
            except Exception as e:
                print(f"解析点表第{index+1}行时出错: {e}")
                continue
        
        print(f"成功解析 {parsed_count} 个测点的完整配置")
    
    def _parse_boolean(self, value) -> bool:
        """解析布尔值"""
        if pd.isna(value):
            return False
        return str(value).strip() == '需要'
    
    def _parse_threshold(self, value) -> Optional[float]:
        """解析阈值"""
        if pd.isna(value) or str(value).strip().lower() in ['none', '']:
            return None
        try:
            value_str = str(value).strip()
            if 'XQ' in value_str:
                return value_str
            return float(value_str)
        except:
            return None
    
    def _parse_range(self, value) -> Optional[float]:
        """解析范围值"""
        if pd.isna(value) or str(value).strip() == '':
            return None
        try:
            value_str = str(value).strip()
            # 移除单位
            for unit in ['MW/s', '℃/s', 'bar/s', 'mm/s', 'A/s', 'mm/s²', 'KPa/s', 'MPa/s', '%/s', 'μm/s']:
                if unit in value_str:
                    value_str = value_str.replace(unit, '')
            return float(value_str.strip())
        except:
            return None
    
    def _parse_safe_range(self, safe_range_str) -> Optional[Tuple[float, float]]:
        """解析运行安全区间"""
        if pd.isna(safe_range_str) or str(safe_range_str).strip().lower() in ['none', '']:
            return None
            
        try:
            safe_range_str = str(safe_range_str).strip()
            print(f"解析安全区间原始字符串: '{safe_range_str}'")  # 调试输出
            
            # 处理各种分隔符，统一替换为连字符
            safe_range_str = safe_range_str.replace('~', '-').replace('—', '-').replace('–', '-').replace('﹣', '-')
            
            # 处理中文"至"分隔符
            safe_range_str = safe_range_str.replace('至', '-')
            
            # 移除所有空格
            safe_range_str = safe_range_str.replace(' ', '')
            
            # 检查是否包含连字符
            if '-' not in safe_range_str:
                print(f"警告: 安全区间 '{safe_range_str}' 不包含有效的分隔符")
                return None
            
            # 分割字符串
            parts = safe_range_str.split('-')
            if len(parts) != 2:
                print(f"警告: 安全区间 '{safe_range_str}' 分割后部分数量不正确: {parts}")
                return None
            
            lower_str, upper_str = parts[0], parts[1]
            
            # 清理字符串并转换为数字
            try:
                lower = float(lower_str)
                upper = float(upper_str)
            except ValueError as e:
                print(f"安全区间数值转换失败: '{lower_str}' 或 '{upper_str}' -> {e}")
                return None
            
            # 验证区间有效性
            if lower >= upper:
                print(f"警告: 安全区间 '{safe_range_str}' 下限 {lower} 大于等于上限 {upper}")
                # 不自动交换，因为可能是配置错误
                return None
            
            print(f"安全区间解析成功: '{safe_range_str}' -> ({lower}, {upper})")  # 调试输出
            return (lower, upper)
                
        except Exception as e:
            print(f"解析运行安全区间失败 '{safe_range_str}': {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _parse_correlation_points(self, correlation_str) -> List[str]:
        """解析相关性测点"""
        if pd.isna(correlation_str) or str(correlation_str).strip().lower() in ['none', '']:
            return []
        
        try:
            correlation_str = str(correlation_str).strip()
            
            # 处理多种分隔符：中文逗号、英文逗号、空格等
            correlation_str = re.sub(r'[，\s]+', ',', correlation_str)
            correlation_str = correlation_str.replace('，', ',')
            
            points = []
            if ',' in correlation_str:
                points = [p.strip() for p in correlation_str.split(',') if p.strip()]
            else:
                points = [correlation_str]
            
            # 过滤掉无效的测点并去重
            valid_points = []
            seen_points = set()
            
            for point in points:
                point = point.strip()
                if point and point.lower() != 'none' and point not in seen_points:
                    found_point = self._find_point_by_name_or_kks(point)
                    if found_point:
                        valid_points.append(found_point)
                        seen_points.add(found_point)
                    else:
                        print(f"警告: 相关性测点 '{point}' 不在点表中，尝试模糊匹配...")
                        fuzzy_match = self._fuzzy_match_point(point)
                        if fuzzy_match:
                            valid_points.append(fuzzy_match)
                            seen_points.add(fuzzy_match)
                            print(f"  使用模糊匹配: {point} -> {fuzzy_match}")
                        else:
                            print(f"  无法找到匹配的测点: {point}")
            
            return valid_points
            
        except Exception as e:
            print(f"解析相关性测点失败 '{correlation_str}': {e}")
            return []

    def _find_point_by_name_or_kks(self, point_identifier: str) -> Optional[str]:
        """通过名称或KKS代码查找测点"""
        point_identifier = point_identifier.strip()
        
        # 1. 直接匹配KKS代码
        if point_identifier in self.kks_mapping:
            return point_identifier
        
        # 2. 通过测点名称查找
        for kks, info in self.kks_mapping.items():
            if info['name'] == point_identifier:
                return kks
        
        # 3. 通过描述查找
        for kks, info in self.kks_mapping.items():
            if info['description'] == point_identifier:
                return kks
        
        return None

    def _fuzzy_match_point(self, point_identifier: str) -> Optional[str]:
        """模糊匹配测点"""
        point_identifier = point_identifier.lower().strip()
        
        best_match = None
        best_score = 0
        
        for kks, info in self.kks_mapping.items():
            score = 0
            
            if point_identifier in kks.lower():
                score += 0.6
            
            name = info['name'].lower()
            if point_identifier in name:
                score += 0.3
            
            description = info['description'].lower()
            if point_identifier in description:
                score += 0.1
            
            if score > best_score:
                best_score = score
                best_match = kks
        
        if best_score >= 0.6:
            return best_match
        
        return None
    
    def _print_debug_info(self):
        """打印调试信息"""
        if self.kks_mapping:
            print(f"\n=== 点表解析统计 ===")
            print(f"总测点数: {len(self.kks_mapping)}")
            print(f"有安全区间的测点: {len(self.safe_ranges)}")
            print(f"有正相关的测点: {len(self.positive_correlations)}")
            print(f"有负相关的测点: {len(self.negative_correlations)}")
            
            # 显示安全区间示例
            print(f"\n=== 安全区间示例 ===")
            count = 0
            for kks, safe_range in list(self.safe_ranges.items())[:10]:
                point_info = self.kks_mapping[kks]
                print(f"  {kks}: {point_info['name']}")
                print(f"    安全区间: {safe_range}")
                print(f"    正相关: {self.positive_correlations.get(kks, [])}")
                print(f"    负相关: {self.negative_correlations.get(kks, [])}")
                print()
                count += 1
    
    def get_point_info(self, kks: str) -> Optional[Dict]:
        """获取测点信息"""
        return self.kks_mapping.get(kks)
    
    def get_alarm_thresholds(self, kks: str) -> Optional[Dict]:
        """获取报警阈值"""
        return self.alarm_thresholds.get(kks)
    
    def get_detection_config(self, kks: str) -> Optional[Dict]:
        """获取检测配置"""
        return self.detection_config.get(kks)
    
    def get_safe_range(self, kks: str) -> Optional[Tuple[float, float]]:
        """获取运行安全区间"""
        return self.safe_ranges.get(kks)
    
    def get_positive_correlations(self, kks: str) -> List[str]:
        """获取正相关测点"""
        return self.positive_correlations.get(kks, [])
    
    def get_negative_correlations(self, kks: str) -> List[str]:
        """获取负相关测点"""
        return self.negative_correlations.get(kks, [])
    
    def get_all_correlations(self, kks: str) -> Dict[str, List[str]]:
        """获取所有相关测点"""
        return {
            'positive': self.get_positive_correlations(kks),
            'negative': self.get_negative_correlations(kks)
        }
    
    def get_all_kks(self) -> List[str]:
        """获取所有KKS代码"""
        return list(self.kks_mapping.keys())
    
    def resolve_threshold_reference(self, threshold_value, current_data: Dict) -> Optional[float]:
        """解析阈值引用"""
        if isinstance(threshold_value, str) and 'XQ' in threshold_value:
            return current_data.get(threshold_value)
        return threshold_value
    
    def get_system_points(self, system: str) -> List[str]:
        """获取指定系统的所有测点"""
        return [kks for kks, info in self.kks_mapping.items() if info['system'] == system]
    
    def get_correlation_stats(self) -> Dict:
        """获取相关性统计"""
        total_points = len(self.kks_mapping)
        points_with_positive = len([p for p in self.positive_correlations.values() if p])
        points_with_negative = len([p for p in self.negative_correlations.values() if p])
        
        return {
            'total_points': total_points,
            'points_with_positive_corr': points_with_positive,
            'points_with_negative_corr': points_with_negative,
            'positive_coverage': round(points_with_positive / total_points * 100, 2) if total_points > 0 else 0,
            'negative_coverage': round(points_with_negative / total_points * 100, 2) if total_points > 0 else 0
        }

    def get_safe_range_stats(self) -> Dict:
        """获取运行安全区间统计"""
        total_points = len(self.kks_mapping)
        points_with_safe_range = len([p for p in self.safe_ranges.values() if p])
        
        return {
            'total_points': total_points,
            'points_with_safe_range': points_with_safe_range,
            'coverage_rate': round(points_with_safe_range / total_points * 100, 2) if total_points > 0 else 0
        }
    
    def is_value_in_safe_range(self, kks: str, value: float) -> Tuple[bool, Optional[str]]:
        """检查数值是否在安全运行区间内"""
        safe_range = self.get_safe_range(kks)
        if not safe_range:
            return True, None  # 没有安全区间配置，默认为安全
        
        lower, upper = safe_range
        
        if lower <= value <= upper:
            return True, None
        else:
            if value < lower:
                return False, f"低于安全区间下限: {value} < {lower}"
            else:
                return False, f"高于安全区间上限: {value} > {upper}"
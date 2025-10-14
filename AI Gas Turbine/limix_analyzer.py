import torch
import numpy as np
import pandas as pd
import os
import sys
import time
from typing import Dict, List, Any, Tuple, Optional
import json
from datetime import datetime, timedelta
import math

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "LimiX"))
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

os.environ["RANK"] = "0"
os.environ["WORLD_SIZE"] = "1"
os.environ["MASTER_ADDR"] = "localhost"
os.environ["MASTER_PORT"] = "29500"
os.environ["CUDA_VISIBLE_DEVICES"] = ""

from inference.predictor import LimiXPredictor

class GasTurbineAnalyzer:
    """基于LimiX的燃气轮机分析引擎"""
    
    def __init__(self, model_path: str, point_loader):
        self.model_path = model_path
        self.point_loader = point_loader
        self.data_history = {}
        self.analysis_results = {}
        self.fault_history = {}
        self.prediction_alarms = []
        
        # 报警发送历史记录
        self.alarm_send_history = {}  # 格式: {kks: {alarm_type: last_sent_time}}
        self.alarm_cooldown_hours = 1  # 相同报警冷却时间（小时）
        
        self.prediction_interval = 5
        self.prediction_minutes = 3
        self.prediction_points = int((self.prediction_minutes * 60) / self.prediction_interval)
        
        # 常检测配置
        self.anomaly_config = {
            'min_data_points': 30,  # 最小数据点数才进行异常检测
            'stability_threshold': 0.01,  # 稳定性阈值（相对变化）
            'anomaly_prob_threshold': 0.8,  # 异常概率阈值
            'ignore_stable_data': True  # 忽略稳定数据的异常检测
        }
        
        self._load_models()
        
    def _load_models(self):
        """加载LimiX模型"""
        print("正在加载LimiX分析模型...")
        
        try:
            config_dir = os.path.join(ROOT_DIR, 'config')
            clf_config = os.path.join(config_dir, 'cls_default_noretrieval.json')
            reg_config = os.path.join(config_dir, 'reg_default_noretrieval.json')
            
            self.clf_predictor = LimiXPredictor(
                device=torch.device('cpu'),
                model_path=self.model_path,
                inference_config=clf_config,
                mix_precision=False,
                inference_with_DDP=False,
                outlier_remove_std=8.0
            )
            
            self.reg_predictor = LimiXPredictor(
                device=torch.device('cpu'),
                model_path=self.model_path,
                inference_config=reg_config,
                mix_precision=False,
                inference_with_DDP=False,
                outlier_remove_std=8.0
            )
            
            print("LimiX模型加载完成")
            print(f"预测配置: 每{self.prediction_interval}秒一个点，预测{self.prediction_minutes}分钟，共{self.prediction_points}个点")
            
        except Exception as e:
            print(f"模型加载失败: {e}")
            raise
    
    def add_data_point(self, kks: str, value: float, timestamp: datetime):
        """添加数据点"""
        if kks not in self.data_history:
            self.data_history[kks] = []
        
        self.data_history[kks].append({
            'timestamp': timestamp,
            'value': value
        })
        
        max_points = max(500, self.prediction_points * 3)
        if len(self.data_history[kks]) > max_points:
            self.data_history[kks] = self.data_history[kks][-max_points:]
    
    def analyze_current_status(self, current_data: Dict[str, float]) -> Dict[str, Any]:
        """分析当前状态"""
        analysis_time = datetime.now()
        results = {
            'timestamp': analysis_time.isoformat(),
            'overall_health': 'HEALTHY',
            'alarms': [],
            'warnings': [],
            'point_analysis': {},
            'summary': '',
            'risk_level': 'LOW',
            'fault_detected': False,
            'fault_points': [],
            'anomaly_signals': [],
            'prediction_alarms': [],
            'prediction_results': {}
        }
        
        for kks, value in current_data.items():
            point_info = self.point_loader.get_point_info(kks)
            if not point_info:
                continue
                
            point_result = self._analyze_single_point(kks, value, current_data)
            results['point_analysis'][kks] = point_result
            
            # 检查是否超出保护值
            protection_check = self._check_protection_thresholds(kks, value, current_data)
            
            # 生成报警信息
            alarm_info = self._generate_alarm_info(kks, value, point_info, point_result, protection_check)
            if alarm_info:
                if alarm_info['level'] == 'CRITICAL':
                    results['alarms'].append(alarm_info['message'])
                elif alarm_info['level'] in ['HIGH', 'MEDIUM']:
                    results['warnings'].append(alarm_info['message'])
            
            # 生成故障信息
            fault_generated = False
            if point_result['alarm_level'] == 'CRITICAL':
                # 严重报警必须生成故障记录
                anomaly_signals = [f"严重报警: {point_result['status_description']}"]
                results['fault_detected'] = True
                fault_info = self._create_fault_info(kks, point_result, analysis_time, anomaly_signals)
                
                # 检查是否需要发送到DeepSeek（避免一小时内重复发送）
                should_send_to_deepseek = self._should_send_alarm_to_deepseek(kks, point_result, protection_check)
                fault_info['send_to_deepseek'] = should_send_to_deepseek
                
                results['fault_points'].append(fault_info)
                results['anomaly_signals'].extend(anomaly_signals)
                fault_generated = True
            
            # 只有当实际波动或突变超过点表阈值时才视为故障
            anomaly_signals = self._detect_anomaly_signals(point_result)
            if anomaly_signals and not fault_generated:  # 避免重复添加
                results['fault_detected'] = True
                fault_info = self._create_fault_info(kks, point_result, analysis_time, anomaly_signals)
                
                # 检查是否需要发送到DeepSeek（避免一小时内重复发送）
                should_send_to_deepseek = self._should_send_alarm_to_deepseek(kks, point_result, protection_check)
                fault_info['send_to_deepseek'] = should_send_to_deepseek
                
                results['fault_points'].append(fault_info)
                results['anomaly_signals'].extend(anomaly_signals)
            
            if point_result.get('prediction_alarm_level'):
                prediction_alarm = {
                    'kks': kks,
                    'name': point_info['name'],
                    'alarm_level': point_result['prediction_alarm_level'],
                    'predicted_value': point_result.get('predicted_value'),
                    'threshold': point_result.get('prediction_threshold'),
                    'time_to_alarm': point_result.get('time_to_alarm'),
                    'description': f"{point_info['name']}预测{point_result.get('time_to_alarm', 0)}秒后将触及{point_result['prediction_alarm_level']}报警阈值: {point_result.get('predicted_value')} {point_info['unit']} > {point_result.get('prediction_threshold')} {point_info['unit']}"
                }
                results['prediction_alarms'].append(prediction_alarm)
            
            if point_result.get('detailed_prediction'):
                results['prediction_results'][kks] = point_result['detailed_prediction']
        
        results = self._generate_overall_health(results)
        results['summary'] = self._generate_summary(results)
        
        self.analysis_results = results
        return results
    
    def _should_send_alarm_to_deepseek(self, kks: str, point_result: Dict, protection_check: Dict) -> bool:
        """检查是否应该发送报警到DeepSeek（避免一小时内重复发送）"""
        current_time = datetime.now()
        
        # 生成报警标识符
        if protection_check['is_protection_breach']:
            alarm_identifier = f"{kks}_protection_breach"
        else:
            # 使用报警级别和主要异常信号作为标识符
            main_anomaly = point_result['status_description'].split('，')[0] if point_result['status_description'] else 'unknown'
            alarm_identifier = f"{kks}_{point_result['alarm_level']}_{main_anomaly}"
        
        # 检查是否在冷却期内
        if kks in self.alarm_send_history and alarm_identifier in self.alarm_send_history[kks]:
            last_sent_time = self.alarm_send_history[kks][alarm_identifier]
            time_diff = current_time - last_sent_time
            if time_diff.total_seconds() < self.alarm_cooldown_hours * 3600:
                print(f"报警 {alarm_identifier} 在一小时内已发送过，跳过DeepSeek分析")
                return False
        
        # 更新发送历史
        if kks not in self.alarm_send_history:
            self.alarm_send_history[kks] = {}
        self.alarm_send_history[kks][alarm_identifier] = current_time
        
        # 清理过期的历史记录（超过24小时）
        self._cleanup_old_alarm_history()
        
        return True
    
    def _cleanup_old_alarm_history(self):
        """清理过期的报警历史记录"""
        current_time = datetime.now()
        cleanup_threshold = 24  # 小时
        
        for kks in list(self.alarm_send_history.keys()):
            for alarm_identifier in list(self.alarm_send_history[kks].keys()):
                last_sent_time = self.alarm_send_history[kks][alarm_identifier]
                time_diff = current_time - last_sent_time
                if time_diff.total_seconds() > cleanup_threshold * 3600:
                    del self.alarm_send_history[kks][alarm_identifier]
            
            # 如果该测点的所有报警记录都已清理，删除测点键
            if not self.alarm_send_history[kks]:
                del self.alarm_send_history[kks]
    
    def _generate_alarm_info(self, kks: str, value: float, point_info: Dict, point_result: Dict, protection_check: Dict) -> Dict:
        """生成报警信息"""
        if protection_check['is_protection_breach']:
            direction_symbol = ">" if protection_check['direction'] == 'above' else "<"
            return {
                'level': 'CRITICAL',
                'message': f"{point_info['name']}超出保护值: {value} {point_info['unit']} {direction_symbol} {protection_check['protection_value']} {point_info['unit']}"
            }
        
        if point_result['alarm_level'] == 'CRITICAL':
            thresholds = self.point_loader.get_alarm_thresholds(kks)
            current_data = {kks: value}
            
            # 检查具体是哪个阈值触发的报警
            triggered_threshold = None
            threshold_value = None
            
            hhh_threshold = self._safe_parse_threshold(thresholds['HHH'], current_data)
            if hhh_threshold is not None and self._safe_compare(value, hhh_threshold, '>='):
                triggered_threshold = 'HHH'
                threshold_value = hhh_threshold
            
            lll_threshold = self._safe_parse_threshold(thresholds['LLL'], current_data)
            if lll_threshold is not None and self._safe_compare(value, lll_threshold, '<='):
                triggered_threshold = 'LLL'
                threshold_value = lll_threshold
            
            hh_threshold = self._safe_parse_threshold(thresholds['HH'], current_data)
            if hh_threshold is not None and self._safe_compare(value, hh_threshold, '>=') and not triggered_threshold:
                triggered_threshold = 'HH'
                threshold_value = hh_threshold
            
            ll_threshold = self._safe_parse_threshold(thresholds['LL'], current_data)
            if ll_threshold is not None and self._safe_compare(value, ll_threshold, '<=') and not triggered_threshold:
                triggered_threshold = 'LL'
                threshold_value = ll_threshold
            
            h_threshold = self._safe_parse_threshold(thresholds['H'], current_data)
            if h_threshold is not None and self._safe_compare(value, h_threshold, '>=') and not triggered_threshold:
                triggered_threshold = 'H'
                threshold_value = h_threshold
            
            l_threshold = self._safe_parse_threshold(thresholds['L'], current_data)
            if l_threshold is not None and self._safe_compare(value, l_threshold, '<=') and not triggered_threshold:
                triggered_threshold = 'L'
                threshold_value = l_threshold
            
            if triggered_threshold:
                direction = ">" if triggered_threshold in ['HHH', 'HH', 'H'] else "<"
                return {
                    'level': 'CRITICAL',
                    'message': f"{point_info['name']}触及{triggered_threshold}报警: {value} {point_info['unit']} {direction} {threshold_value} {point_info['unit']}"
                }
            else:
                # 如果没有找到具体阈值，使用状态描述
                return {
                    'level': 'CRITICAL',
                    'message': f"{point_info['name']}: {value} {point_info['unit']} - {point_result['status_description']}"
                }
        
        elif point_result['alarm_level'] == 'HIGH':
            return {
                'level': 'HIGH',
                'message': f"{point_info['name']}: {value} {point_info['unit']} - {point_result['status_description']}"
            }
        elif point_result['alarm_level'] == 'MEDIUM':
            return {
                'level': 'MEDIUM',
                'message': f"{point_info['name']}: {value} {point_info['unit']} - {point_result['status_description']}"
            }
        
        return None
    
    def _check_protection_thresholds(self, kks: str, value: float, current_data: Dict) -> Dict:
        """检查保护阈值"""
        thresholds = self.point_loader.get_alarm_thresholds(kks)
        if not thresholds:
            return {'is_protection_breach': False}
        
        # 检查是否超出上下限保护值
        upper_limit = self._safe_parse_threshold(thresholds.get('upper_limit'), current_data)
        lower_limit = self._safe_parse_threshold(thresholds.get('lower_limit'), current_data)
        
        if upper_limit is not None and self._safe_compare(value, upper_limit, '>'):
            return {
                'is_protection_breach': True,
                'protection_value': upper_limit,
                'direction': 'above'
            }
        
        if lower_limit is not None and self._safe_compare(value, lower_limit, '<'):
            return {
                'is_protection_breach': True,
                'protection_value': lower_limit,
                'direction': 'below'
            }
        
        return {'is_protection_breach': False}
    
    def _detect_anomaly_signals(self, point_result: Dict) -> List[str]:
        """检测异常信号"""
        signals = []
        
        # 只有当实际波动超过点表阈值时才视为异常
        if point_result['fluctuation_detected']:
            actual_fluct = point_result.get('actual_fluctuation', 0)
            threshold_fluct = point_result.get('fluctuation_range', 0)
            if actual_fluct > threshold_fluct:
                signals.append(f"剧烈波动({actual_fluct:.2f}>{threshold_fluct})")
        
        # 只有当实际突变超过点表阈值时才视为异常
        if point_result['mutation_detected']:
            actual_mut = point_result.get('actual_mutation', 0)
            threshold_mut = point_result.get('mutation_range', 0)
            if actual_mut > threshold_mut:
                signals.append(f"数值突变({actual_mut:.2f}>{threshold_mut})")
        
        # 异常概率检测 - 提高阈值并检查数据稳定性
        if (point_result['anomaly_probability'] > self.anomaly_config['anomaly_prob_threshold'] and
            not self._is_data_too_stable(point_result)):
            signals.append("异常模式")
        
        return signals
    
    def _is_data_too_stable(self, point_result: Dict) -> bool:
        """检查数据是否稳定"""
        # 如果数据几乎没有变化，则认为稳定
        kks = point_result['kks']
        if kks not in self.data_history or len(self.data_history[kks]) < 10:
            return False
        
        values = [point['value'] for point in self.data_history[kks][-20:]]
        if len(values) < 5:
            return False
        
        # 计算数据的相对变化
        min_val = min(values)
        max_val = max(values)
        if max_val == 0:  # 避免除零
            return True
        
        relative_change = (max_val - min_val) / max_val
        
        # 如果相对变化小于阈值，认为数据过于稳定
        return relative_change < self.anomaly_config['stability_threshold']
    
    def _create_fault_info(self, kks: str, point_result: Dict, timestamp: datetime, anomaly_signals: List[str]) -> Dict:
        """创建故障信息"""
        point_info = self.point_loader.get_point_info(kks)
        
        # 获取前2.5分钟历史数据（30个点，每5秒一个）
        two_and_half_minutes_ago = timestamp - timedelta(minutes=2, seconds=30)
        recent_history = []
        
        if kks in self.data_history:
            for data_point in self.data_history[kks]:
                if data_point['timestamp'] >= two_and_half_minutes_ago:
                    recent_history.append({
                        'timestamp': data_point['timestamp'].isoformat(),
                        'value': data_point['value']
                    })
        
        fault_info = {
            'kks': kks,
            'name': point_info['name'],
            'description': point_info['description'],
            'system': point_info['system'],
            'timestamp': timestamp.isoformat(),
            'current_value': point_result['current_value'],
            'unit': point_result['unit'],
            'alarm_level': point_result['alarm_level'],
            'fluctuation_detected': point_result['fluctuation_detected'],
            'mutation_detected': point_result['mutation_detected'],
            'anomaly_probability': point_result['anomaly_probability'],
            'trend': point_result['trend'],
            'predicted_trend': point_result['predicted_trend'],
            'recent_history': recent_history,
            'status_description': point_result['status_description'],
            'anomaly_signals': anomaly_signals,
            'fluctuation_range': point_result.get('fluctuation_range'),
            'mutation_range': point_result.get('mutation_range'),
            'actual_fluctuation': point_result.get('actual_fluctuation'),
            'actual_mutation': point_result.get('actual_mutation'),
            'send_to_deepseek': True  # 默认发送到DeepSeek
        }
        
        return fault_info
    
    def _analyze_single_point(self, kks: str, value: float, current_data: Dict) -> Dict[str, Any]:
        """分析单个测点"""
        point_info = self.point_loader.get_point_info(kks)
        thresholds = self.point_loader.get_alarm_thresholds(kks)
        detection_config = self.point_loader.get_detection_config(kks)
        
        result = {
            'kks': kks,
            'name': point_info['name'],
            'description': point_info['description'],
            'system': point_info['system'],
            'current_value': value,
            'unit': point_info['unit'],
            'alarm_level': 'NORMAL',
            'status_description': '',
            'trend': 'STABLE',
            'anomaly_probability': 0.0,
            'fluctuation_detected': False,
            'mutation_detected': False,
            'predicted_trend': 'STABLE',
            'prediction_error': None,
            'prediction_alarm_level': None,
            'predicted_value': None,
            'prediction_threshold': None,
            'time_to_alarm': None,
            'detailed_prediction': None,
            'fluctuation_range': detection_config.get('fluctuation_range'),
            'mutation_range': detection_config.get('mutation_range'),
            'actual_fluctuation': None,
            'actual_mutation': None
        }
        
        alarm_check = self._check_alarm_thresholds(kks, value, thresholds, current_data)
        result.update(alarm_check)
        
        if len(self.data_history.get(kks, [])) > 10:
            trend_analysis = self._analyze_trend(kks)
            result.update(trend_analysis)
        
        # 只有在有足够数据且数据不稳定的情况下才进行异常检测
        if (len(self.data_history.get(kks, [])) > self.anomaly_config['min_data_points'] and
            not self._is_data_too_stable(result)):
            anomaly_analysis = self._detect_anomalies(kks)
            result.update(anomaly_analysis)
        
        # 波动和突变检测
        if detection_config['fluctuation_detection']:
            fluctuation_result = self._detect_fluctuation(kks, detection_config['fluctuation_range'])
            result['fluctuation_detected'] = fluctuation_result['detected']
            result['actual_fluctuation'] = fluctuation_result['max_fluctuation']
        
        if detection_config['mutation_detection']:
            mutation_result = self._detect_mutation(kks, detection_config['mutation_range'])
            result['mutation_detected'] = mutation_result['detected']
            result['actual_mutation'] = mutation_result['mutation_value']
        
        if detection_config['trend_prediction'] and len(self.data_history.get(kks, [])) > self.prediction_points:
            prediction_result = self._predict_trend_and_alarm(kks, thresholds, current_data)
            result.update(prediction_result)
        
        result['status_description'] = self._generate_point_status_description(result)
        
        return result
    
    def _check_alarm_thresholds(self, kks: str, value: float, thresholds: Dict, current_data: Dict) -> Dict:
        """检查报警阈值 - 修复类型比较错误"""
        result = {'alarm_level': 'NORMAL'}
        
        # 解析阈值并确保为数值类型
        hhh_threshold = self._safe_parse_threshold(thresholds['HHH'], current_data)
        hh_threshold = self._safe_parse_threshold(thresholds['HH'], current_data)
        h_threshold = self._safe_parse_threshold(thresholds['H'], current_data)
        l_threshold = self._safe_parse_threshold(thresholds['L'], current_data)
        ll_threshold = self._safe_parse_threshold(thresholds['LL'], current_data)
        lll_threshold = self._safe_parse_threshold(thresholds['LLL'], current_data)
        
        # 检查阈值
        if hhh_threshold is not None and self._safe_compare(value, hhh_threshold, '>='):
            result['alarm_level'] = 'CRITICAL'
        elif lll_threshold is not None and self._safe_compare(value, lll_threshold, '<='):
            result['alarm_level'] = 'CRITICAL'
        elif hh_threshold is not None and self._safe_compare(value, hh_threshold, '>='):
            result['alarm_level'] = 'HIGH'
        elif ll_threshold is not None and self._safe_compare(value, ll_threshold, '<='):
            result['alarm_level'] = 'HIGH'
        elif h_threshold is not None and self._safe_compare(value, h_threshold, '>='):
            result['alarm_level'] = 'MEDIUM'
        elif l_threshold is not None and self._safe_compare(value, l_threshold, '<='):
            result['alarm_level'] = 'MEDIUM'
        
        return result
    
    def _safe_parse_threshold(self, threshold_value, current_data: Dict) -> Optional[float]:
        """解析阈值"""
        try:
            threshold = self.point_loader.resolve_threshold_reference(threshold_value, current_data)
            if threshold is None:
                return None
            
            # 确保返回浮点数
            if isinstance(threshold, (int, float)):
                return float(threshold)
            elif isinstance(threshold, str):
                # 尝试转换字符串为数字
                return float(threshold)
            else:
                print(f"阈值类型不支持: {type(threshold)}")
                return None
        except (ValueError, TypeError) as e:
            print(f"解析阈值失败: {threshold_value}, 错误: {e}")
            return None
    
    def _safe_compare(self, value: float, threshold, operator: str) -> bool:
        """安全比较数值"""
        try:
            # 确保阈值是数值类型
            if isinstance(threshold, (int, float)):
                threshold_float = float(threshold)
            elif isinstance(threshold, str):
                threshold_float = float(threshold)
            else:
                print(f"阈值类型不支持: {type(threshold)}")
                return False
            
            # 执行比较
            if operator == '>=':
                return value >= threshold_float
            elif operator == '<=':
                return value <= threshold_float
            elif operator == '>':
                return value > threshold_float
            elif operator == '<':
                return value < threshold_float
            else:
                return False
        except (ValueError, TypeError) as e:
            print(f"比较失败: {value} {operator} {threshold}, 错误: {e}")
            return False
    
    def _analyze_trend(self, kks: str) -> Dict:
        """分析趋势"""
        history = self.data_history.get(kks, [])
        if len(history) < 10:
            return {'trend': 'STABLE'}
        
        values = [point['value'] for point in history[-10:]]
        
        if len(values) >= 2:
            recent_change = values[-1] - values[-2]
            avg_change = (values[-1] - values[0]) / len(values)
            
            # 使用严格的趋势判断，避免微小波动误判
            change_threshold = max(abs(avg_change) * 3, 0.001)  # 最小变化阈值0.001
            if abs(recent_change) > change_threshold:
                trend = 'INCREASING' if recent_change > 0 else 'DECREASING'
            else:
                trend = 'STABLE'
        else:
            trend = 'STABLE'
        
        return {'trend': trend}
    
    def _detect_anomalies(self, kks: str) -> Dict:
        """检测异常"""
        try:
            history = self.data_history.get(kks, [])
            if len(history) < self.anomaly_config['min_data_points']:
                return {'anomaly_probability': 0.0}
            
            values = np.array([point['value'] for point in history[-20:]])
            
            # 检查数据稳定性
            if len(values) >= 5:
                min_val = np.min(values)
                max_val = np.max(values)
                if max_val != 0:
                    relative_change = (max_val - min_val) / max_val
                    # 如果数据稳定，直接返回低异常概率
                    if relative_change < self.anomaly_config['stability_threshold']:
                        return {'anomaly_probability': 0.1}  # 稳定数据给低异常概率
            
            values = values.reshape(-1, 1)
            
            X_ref = values[:10]
            y_ref = np.ones(len(X_ref))
            X_test = values[10:]
            
            # 如果测试数据为空，返回低异常概率
            if len(X_test) == 0:
                return {'anomaly_probability': 0.1}
            
            anomaly_scores = self.clf_predictor.predict(X_ref, y_ref, X_test)
            
            if hasattr(anomaly_scores, 'cpu'):
                anomaly_scores = anomaly_scores.cpu().numpy()
            
            if len(anomaly_scores.shape) > 1 and anomaly_scores.shape[1] > 1:
                anomaly_prob = np.mean(anomaly_scores[:, 1])
            else:
                anomaly_prob = np.mean(anomaly_scores)
            
            # 限制异常概率范围，避免极端值
            anomaly_prob = max(0.0, min(1.0, float(anomaly_prob)))
            
            return {'anomaly_probability': anomaly_prob}
            
        except Exception as e:
            print(f"异常检测失败 {kks}: {e}")
            return {'anomaly_probability': 0.0}
    
    def _detect_fluctuation(self, kks: str, fluctuation_range: float) -> Dict:
        """检测波动"""
        history = self.data_history.get(kks, [])
        if len(history) < 5 or fluctuation_range is None:
            return {'detected': False, 'max_fluctuation': 0.0}
        
        # 获取最近5个数据点
        values = [point['value'] for point in history[-5:]]
        
        # 计算相邻点之间的变化率（绝对值）
        fluctuations = []
        for i in range(1, len(values)):
            time_diff = 5  # 假设数据点间隔5秒
            fluctuation_rate = abs(values[i] - values[i-1]) / time_diff
            fluctuations.append(fluctuation_rate)
        
        max_fluctuation = max(fluctuations) if fluctuations else 0.0
        
        # 实际波动率必须超过点表配置的波动幅度才视为检测到
        detected = max_fluctuation > fluctuation_range
        
        return {
            'detected': detected,
            'max_fluctuation': max_fluctuation,
            'threshold': fluctuation_range
        }
    
    def _detect_mutation(self, kks: str, mutation_range: float) -> Dict:
        """检测突变"""
        history = self.data_history.get(kks, [])
        if len(history) < 3 or mutation_range is None:
            return {'detected': False, 'mutation_value': 0.0}
        
        values = [point['value'] for point in history[-3:]]
        if len(values) >= 3:
            # 计算最新两个点之间的突变值（绝对值）
            mutation_value = abs(values[-1] - values[-2])
            
            # 实际突变值必须超过点表配置的突变幅度才视为检测到
            detected = mutation_value > mutation_range
            
            return {
                'detected': detected,
                'mutation_value': mutation_value,
                'threshold': mutation_range
            }
        
        return {'detected': False, 'mutation_value': 0.0}
    
    def _predict_trend_and_alarm(self, kks: str, thresholds: Dict, current_data: Dict) -> Dict:
        """预测趋势并检查预测报警"""
        try:
            history = self.data_history.get(kks, [])
            if len(history) < self.prediction_points:
                return {'predicted_trend': 'STABLE'}
            
            values = [point['value'] for point in history]
            
            window_size = self.prediction_points
            X_train = []
            y_train = []
            
            for i in range(len(values) - window_size * 2):
                X_train.append(values[i:i + window_size])
                y_train.append(values[i + window_size:i + window_size * 2])
            
            if len(X_train) == 0:
                return {'predicted_trend': 'STABLE'}
            
            X_train = np.array(X_train, dtype=np.float32)
            y_train = np.array(y_train, dtype=np.float32)
            
            X_pred = np.array(values[-window_size:], dtype=np.float32).reshape(1, -1)
            
            if X_train.shape[1] != X_pred.shape[1]:
                return {'predicted_trend': 'STABLE'}
            
            predictions = self.reg_predictor.predict(X_train, y_train, X_pred)
            
            if hasattr(predictions, 'cpu'):
                predictions = predictions.cpu().numpy()
            
            result = {'predicted_trend': 'STABLE'}
            
            if len(predictions) > 0:
                pred_values = predictions.flatten()
                
                if len(pred_values) >= 2:
                    # 使用更严格的趋势判断阈值
                    if pred_values[-1] > pred_values[0] * 1.05:  # 5%变化才认为是上升趋势
                        result['predicted_trend'] = 'INCREASING'
                    elif pred_values[-1] < pred_values[0] * 0.95:  # 5%变化才认为是下降趋势
                        result['predicted_trend'] = 'DECREASING'
                
                detailed_prediction = []
                current_time = datetime.now()
                
                for i, pred_value in enumerate(pred_values):
                    pred_time = current_time + timedelta(seconds=(i + 1) * self.prediction_interval)
                    detailed_prediction.append({
                        'time_offset': (i + 1) * self.prediction_interval,
                        'timestamp': pred_time.isoformat(),
                        'predicted_value': float(pred_value)
                    })
                
                result['detailed_prediction'] = detailed_prediction
                
                alarm_check = self._check_prediction_alarm(kks, pred_values, thresholds, current_data, detailed_prediction)
                result.update(alarm_check)
            
            return result
            
        except Exception as e:
            error_msg = f"趋势预测失败 {kks}: {str(e)}"
            print(error_msg)
            return {'predicted_trend': 'STABLE', 'prediction_error': error_msg}
    
    def _check_prediction_alarm(self, kks: str, pred_values: List[float], thresholds: Dict, current_data: Dict, detailed_prediction: List) -> Dict:
        """检查预测报警"""
        result = {
            'prediction_alarm_level': None,
            'predicted_value': None,
            'prediction_threshold': None,
            'time_to_alarm': None
        }
        
        hhh_threshold = self._safe_parse_threshold(thresholds['HHH'], current_data)
        hh_threshold = self._safe_parse_threshold(thresholds['HH'], current_data)
        h_threshold = self._safe_parse_threshold(thresholds['H'], current_data)
        l_threshold = self._safe_parse_threshold(thresholds['L'], current_data)
        ll_threshold = self._safe_parse_threshold(thresholds['LL'], current_data)
        lll_threshold = self._safe_parse_threshold(thresholds['LLL'], current_data)
        
        for pred_point in detailed_prediction:
            pred_value = pred_point['predicted_value']
            time_to_alarm = pred_point['time_offset']
            
            if hhh_threshold is not None and self._safe_compare(pred_value, hhh_threshold, '>='):
                result.update({
                    'prediction_alarm_level': 'CRITICAL',
                    'predicted_value': pred_value,
                    'prediction_threshold': hhh_threshold,
                    'time_to_alarm': time_to_alarm
                })
                break
            elif lll_threshold is not None and self._safe_compare(pred_value, lll_threshold, '<='):
                result.update({
                    'prediction_alarm_level': 'CRITICAL',
                    'predicted_value': pred_value,
                    'prediction_threshold': lll_threshold,
                    'time_to_alarm': time_to_alarm
                })
                break
            elif hh_threshold is not None and self._safe_compare(pred_value, hh_threshold, '>='):
                result.update({
                    'prediction_alarm_level': 'HIGH',
                    'predicted_value': pred_value,
                    'prediction_threshold': hh_threshold,
                    'time_to_alarm': time_to_alarm
                })
                break
            elif ll_threshold is not None and self._safe_compare(pred_value, ll_threshold, '<='):
                result.update({
                    'prediction_alarm_level': 'HIGH',
                    'predicted_value': pred_value,
                    'prediction_threshold': ll_threshold,
                    'time_to_alarm': time_to_alarm
                })
                break
            elif h_threshold is not None and self._safe_compare(pred_value, h_threshold, '>='):
                result.update({
                    'prediction_alarm_level': 'MEDIUM',
                    'predicted_value': pred_value,
                    'prediction_threshold': h_threshold,
                    'time_to_alarm': time_to_alarm
                })
                break
            elif l_threshold is not None and self._safe_compare(pred_value, l_threshold, '<='):
                result.update({
                    'prediction_alarm_level': 'MEDIUM',
                    'predicted_value': pred_value,
                    'prediction_threshold': l_threshold,
                    'time_to_alarm': time_to_alarm
                })
                break
        
        return result
    
    def _generate_point_status_description(self, point_result: Dict) -> str:
        """生成测点状态描述"""
        descriptions = []
        
        if point_result['alarm_level'] == 'CRITICAL':
            descriptions.append("严重报警状态")
        elif point_result['alarm_level'] == 'HIGH':
            descriptions.append("高级报警状态")
        elif point_result['alarm_level'] == 'MEDIUM':
            descriptions.append("中级报警状态")
        else:
            descriptions.append("正常运行")
        
        if point_result['trend'] != 'STABLE':
            trend_desc = "上升" if point_result['trend'] == 'INCREASING' else "下降"
            descriptions.append(f"当前{trend_desc}趋势")
        
        # 当异常概率超过阈值且数据不稳定的情况下才显示异常模式
        if (point_result['anomaly_probability'] > self.anomaly_config['anomaly_prob_threshold'] and
            not self._is_data_too_stable(point_result)):
            descriptions.append("检测到异常模式")
        
        # 当实际波动超过点表阈值时才显示波动检测
        if point_result['fluctuation_detected']:
            actual_fluct = point_result.get('actual_fluctuation', 0)
            threshold_fluct = point_result.get('fluctuation_range', 0)
            if actual_fluct > threshold_fluct:
                descriptions.append(f"检测到剧烈波动({actual_fluct:.2f}>{threshold_fluct})")
        
        # 当实际突变超过点表阈值时才显示突变检测
        if point_result['mutation_detected']:
            actual_mut = point_result.get('actual_mutation', 0)
            threshold_mut = point_result.get('mutation_range', 0)
            if actual_mut > threshold_mut:
                descriptions.append(f"检测到数值突变({actual_mut:.2f}>{threshold_mut})")
        
        if point_result['predicted_trend'] != 'STABLE' and point_result['prediction_error'] is None:
            pred_desc = "上升" if point_result['predicted_trend'] == 'INCREASING' else "下降"
            descriptions.append(f"预计未来{pred_desc}趋势")
        
        if point_result['prediction_alarm_level']:
            alarm_desc = {
                'CRITICAL': '严重',
                'HIGH': '高级',
                'MEDIUM': '中级'
            }.get(point_result['prediction_alarm_level'], '')
            time_desc = f"{point_result['time_to_alarm']}秒" if point_result['time_to_alarm'] < 60 else f"{point_result['time_to_alarm']//60}分{point_result['time_to_alarm']%60}秒"
            descriptions.append(f"预测{time_desc}后将触及{alarm_desc}报警")
        
        return "，".join(descriptions) if descriptions else "状态正常"
    
    def _generate_overall_health(self, results: Dict) -> Dict:
        """生成总体健康状态"""
        critical_count = len(results['alarms'])
        warning_count = len(results['warnings'])
        fault_count = len(results['fault_points'])
        prediction_alarm_count = len(results['prediction_alarms'])
        
        if critical_count > 0:
            results['overall_health'] = 'CRITICAL'
            results['risk_level'] = 'VERY_HIGH'
        elif warning_count > 2:
            results['overall_health'] = 'WARNING'
            results['risk_level'] = 'HIGH'
        elif warning_count > 0:
            results['overall_health'] = 'ATTENTION'
            results['risk_level'] = 'MEDIUM'
        elif prediction_alarm_count > 0:
            max_prediction_level = max(
                [alarm['alarm_level'] for alarm in results['prediction_alarms']],
                key=lambda x: {'CRITICAL': 3, 'HIGH': 2, 'MEDIUM': 1}.get(x, 0),
                default=None
            )
            
            if max_prediction_level == 'CRITICAL':
                results['overall_health'] = 'PREDICTION_CRITICAL'
                results['risk_level'] = 'HIGH'
            elif max_prediction_level == 'HIGH':
                results['overall_health'] = 'PREDICTION_WARNING'
                results['risk_level'] = 'MEDIUM'
            else:
                results['overall_health'] = 'PREDICTION_ATTENTION'
                results['risk_level'] = 'LOW_MONITOR'
        elif fault_count > 0:
            results['overall_health'] = 'MONITOR'
            results['risk_level'] = 'LOW_MONITOR'
        else:
            results['overall_health'] = 'HEALTHY'
            results['risk_level'] = 'LOW'
        
        return results
    
    def _generate_summary(self, results: Dict) -> str:
        """生成总结语句"""
        critical_count = len(results['alarms'])
        warning_count = len(results['warnings'])
        fault_count = len(results['fault_points'])
        prediction_alarm_count = len(results['prediction_alarms'])
        
        if critical_count > 0:
            return f"系统处于严重报警状态，共检测到{critical_count}个严重报警，需要立即处理。"
        elif warning_count > 2:
            return f"系统存在多处异常，共检测到{warning_count}个警告，建议加强监视并及时调整。"
        elif warning_count > 0:
            return f"系统运行基本正常，存在{warning_count}个需要注意的警告，建议关注相关参数变化。"
        elif prediction_alarm_count > 0:
            critical_pred = len([a for a in results['prediction_alarms'] if a['alarm_level'] == 'CRITICAL'])
            high_pred = len([a for a in results['prediction_alarms'] if a['alarm_level'] == 'HIGH'])
            medium_pred = len([a for a in results['prediction_alarms'] if a['alarm_level'] == 'MEDIUM'])
            
            if critical_pred > 0:
                return f"系统参数预测将在3分钟内触及严重报警阈值，共{critical_pred}个测点，建议立即采取预防措施。"
            elif high_pred > 0:
                return f"系统参数预测将在3分钟内触及高级报警阈值，共{high_pred}个测点，建议密切关注并及时调整。"
            else:
                return f"系统参数预测将在3分钟内触及中级报警阈值，共{medium_pred}个测点，建议关注相关测点变化趋势。"
        elif fault_count > 0:
            anomaly_types = set()
            for fault_point in results['fault_points']:
                anomaly_types.update(fault_point['anomaly_signals'])
            
            anomaly_desc = "、".join(anomaly_types)
            return f"系统参数虽在安全范围内，但检测到{anomaly_desc}等异常信号，建议密切关注相关测点变化趋势。"
        else:
            return "系统运行正常，所有参数均在安全范围内，设备状态良好。"
    
    def get_prediction_data(self, kks: str) -> List[Dict]:
        """获取指定测点的预测数据"""
        if kks in self.data_history and len(self.data_history[kks]) >= self.prediction_points:
            current_data = {kks: self.data_history[kks][-1]['value']}
            point_result = self._analyze_single_point(kks, self.data_history[kks][-1]['value'], current_data)
            return point_result.get('detailed_prediction', [])
        return []
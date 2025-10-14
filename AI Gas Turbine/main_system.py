import os
import socket
import json
import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List
import queue

from config import config
from point_table_loader import PointTableLoader
from limix_analyzer import GasTurbineAnalyzer
from enhanced_deepseek_client import EnhancedDeepSeekClient

class GasTurbineMonitoringSystem:
    """基于LimiX（极数）分析模型与大语言模型Deepseek+RAG专家系统的燃气轮机监控主系统"""
    
    def __init__(self):
         # 获取项目根目录
         self.project_root = os.path.dirname(os.path.abspath(__file__))
         # 点表路径
         point_file_path = os.path.join(self.project_root, "point.xls")
         self.point_loader = PointTableLoader(point_file_path)
         self.analyzer = None
         self.deepseek_client = EnhancedDeepSeekClient()
    
         self.data_queue = queue.Queue()
         self.result_queue = queue.Queue()
         # DeepSeek分析任务队列
         self.deepseek_queue = queue.Queue()
    
         self.running = False
         self.threads = []
    
         self.logger = None
         self.current_log_date = None
         self._setup_logging()
    
         print("系统初始化中...")
    
    def _setup_logging(self):
        """设置日志记录"""
        config.cleanup_old_logs()
        
        self.logger = logging.getLogger('GasTurbineMonitor')
        self.logger.setLevel(logging.INFO)
        
        self._update_log_file()
        
    def _update_log_file(self):
        """更新日志文件"""
        current_date = datetime.now().strftime("%Y%m%d")
        
        if self.current_log_date != current_date:
            self.current_log_date = current_date
            
            for handler in self.logger.handlers[:]:
                self.logger.removeHandler(handler)
            
            log_file = config.get_current_log_filename()
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setLevel(logging.INFO)
            
            formatter = logging.Formatter(
                '%(asctime)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(formatter)
            
            self.logger.addHandler(file_handler)
            
            print(f"日志文件已更新: {log_file}")
    
    def initialize(self) -> bool:
        """初始化系统"""
        print("正在初始化燃气轮机监控系统...")
        
        if not self.point_loader.load_point_table():
            print("点表加载失败，系统初始化中止")
            return False
        
        # 显示统计信息
        corr_stats = self.point_loader.get_correlation_stats()
        print(f"相关性测点统计: 总测点数 {corr_stats['total_points']}, "
          f"正相关覆盖 {corr_stats['positive_coverage']}%, "
          f"负相关覆盖 {corr_stats['negative_coverage']}%")
    
        # 显示安全区间统计
        safe_range_stats = self.point_loader.get_safe_range_stats()
        print(f"运行安全区间统计: 总测点数 {safe_range_stats['total_points']}, "
          f"安全区间覆盖 {safe_range_stats['coverage_rate']}%")
    
        # 调试信息
        all_kks = self.point_loader.get_all_kks()
        if all_kks:
            print("\n=== 前20个测点的调试信息 ===")
            for kks in all_kks[:20]:
                point_info = self.point_loader.get_point_info(kks)
                safe_range = self.point_loader.get_safe_range(kks)
                positive_corr = self.point_loader.get_positive_correlations(kks)
                negative_corr = self.point_loader.get_negative_correlations(kks)
            
                print(f"  {kks}: {point_info['name']}")
                print(f"    安全区间: {safe_range}")
                print(f"    正相关: {positive_corr}")
                print(f"    负相关: {negative_corr}")
                print()
        
        try:
            self.analyzer = GasTurbineAnalyzer(config.MODEL_PATH, self.point_loader)
            print("分析引擎初始化成功")
        except Exception as e:
            print(f"分析引擎初始化失败: {e}")
            return False
        
        print("系统初始化完成 - 等待SIS数据源连接")
        return True
    
    def start(self):
        """启动系统"""
        if not self.initialize():
            print("系统初始化失败，无法启动")
            return
        
        self.running = True
        
        # 启动数据接收器
        receiver_thread = threading.Thread(target=self._data_receiver)
        receiver_thread.daemon = True
        receiver_thread.start()
        self.threads.append(receiver_thread)
        
        # 启动数据分析器
        analysis_thread = threading.Thread(target=self._data_analyzer)
        analysis_thread.daemon = True
        analysis_thread.start()
        self.threads.append(analysis_thread)
        
        # 启动结果发送器
        sender_thread = threading.Thread(target=self._result_sender)
        sender_thread.daemon = True
        sender_thread.start()
        self.threads.append(sender_thread)
        
        # 启动DeepSeek异步分析器
        deepseek_thread = threading.Thread(target=self._deepseek_analyzer)
        deepseek_thread.daemon = True
        deepseek_thread.start()
        self.threads.append(deepseek_thread)
        
        print("燃气轮机监控系统已启动")
        print("监听端口: 9001 - 等待SIS数据源连接")
        print("请确保SIS数据采集器正在运行")
        print("=" * 60)
        
        try:
            while self.running:
                time.sleep(1)
                self._update_log_file()
        except KeyboardInterrupt:
            self.stop()
    
    def stop(self):
        """停止系统"""
        print("正在停止系统...")
        self.running = False
        
        for thread in self.threads:
            thread.join(timeout=5)
        
        print("系统已停止")
    
    def _data_receiver(self):
        """数据接收线程"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((config.HOST, config.SIS_RECEIVE_PORT))
            server_socket.listen(5)
            print(f"数据接收器已启动，监听端口: {config.SIS_RECEIVE_PORT}")
            print("支持的数据源: SIS数据采集器")
            
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    client_socket, addr = server_socket.accept()
                    
                    with client_socket:
                        data = client_socket.recv(4096)
                        if data:
                            self._process_received_data(data, addr)
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"数据接收错误: {e}")
                    
        finally:
            server_socket.close()
    
    def _process_received_data(self, data: bytes, addr: tuple):
        """处理接收到的数据"""
        try:
            message = json.loads(data.decode('utf-8'))
            timestamp = datetime.fromisoformat(message['timestamp'])
            data_points = message['data_points']
            data_source = message.get('source', '未知')
            
            # 添加数据点到分析器历史
            for kks, value in data_points.items():
                self.analyzer.add_data_point(kks, value, timestamp)
            
            self.data_queue.put({
                'data_points': data_points,
                'timestamp': timestamp,
                'source': data_source,
                'address': addr
            })
            
            print(f"接收到SIS数据包 - 来源: {data_source}, 地址: {addr[0]}:{addr[1]}, 测点数: {len(data_points)}, 时间: {timestamp}")
            
        except Exception as e:
            print(f"处理接收数据错误: {e}")
    
    def _data_analyzer(self):
        """数据分析线程"""
        while self.running:
            try:
                data_package = self.data_queue.get(timeout=1.0)
                current_data = data_package['data_points']
                data_source = data_package['source']
                
                analysis_result = self.analyzer.analyze_current_status(current_data)
                
                # 添加数据源信息到分析结果
                analysis_result['data_source'] = data_source
                analysis_result['received_time'] = datetime.now().isoformat()
                
                self.result_queue.put(analysis_result)
                
                self._log_analysis_result(analysis_result)
                
                # 检测到故障或严重报警时发送故障报告
                if analysis_result['fault_detected'] or analysis_result['alarms']:
                    self._send_fault_reports(analysis_result['fault_points'])
                    # 异步发送到DeepSeek分析（包含相关性测点）
                    if analysis_result['fault_points']:
                        self._queue_deepseek_analysis(analysis_result['fault_points'], current_data)
                
                self._display_analysis_result(analysis_result)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"数据分析错误: {e}")
    
    def _queue_deepseek_analysis(self, fault_points: List[Dict], current_data: Dict):
        """将故障分析任务加入队列（异步处理），包含相关性测点"""
        for fault_info in fault_points:
            # 检查是否需要发送到DeepSeek（避免一小时内重复发送）
            if not fault_info.get('send_to_deepseek', True):
                print(f"跳过DeepSeek分析: {fault_info['name']} - 一小时内已发送过相同报警")
                continue
            
            # 获取相关性测点信息
            correlation_data = self._get_correlation_data(fault_info['kks'], current_data)
            fault_info['correlation_points'] = correlation_data
            
            # 将任务加入队列
            self.deepseek_queue.put(fault_info)
            print(f"已加入DeepSeek分析队列: {fault_info['name']} (包含{len(correlation_data['positive']) + len(correlation_data['negative'])}个相关测点)")
    
    def _get_correlation_data(self, fault_kks: str, current_data: Dict) -> Dict:
        """获取相关性测点数据"""
        correlation_data = {
            'positive': [],
            'negative': []
        }
        
        try:
            # 获取正相关测点
            positive_correlations = self.point_loader.get_positive_correlations(fault_kks)
            for corr_kks in positive_correlations:
                corr_data = self._get_correlation_point_data(corr_kks, current_data)
                if corr_data:
                    correlation_data['positive'].append(corr_data)
            
            # 获取负相关测点
            negative_correlations = self.point_loader.get_negative_correlations(fault_kks)
            for corr_kks in negative_correlations:
                corr_data = self._get_correlation_point_data(corr_kks, current_data)
                if corr_data:
                    correlation_data['negative'].append(corr_data)
                    
        except Exception as e:
            print(f"获取相关性测点数据失败 {fault_kks}: {e}")
            
        return correlation_data
    
    def _get_correlation_point_data(self, corr_kks: str, current_data: Dict) -> Dict:
        """获取单个相关性测点数据"""
        try:
            point_info = self.point_loader.get_point_info(corr_kks)
            if not point_info:
                return None
            
            # 获取当前值
            current_value = current_data.get(corr_kks)
            if current_value is None:
                return None
            
            # 获取前三分钟历史数据
            three_minutes_ago = datetime.now() - timedelta(minutes=3)
            recent_history = []
            
            if corr_kks in self.analyzer.data_history:
                for data_point in self.analyzer.data_history[corr_kks]:
                    if data_point['timestamp'] >= three_minutes_ago:
                        recent_history.append({
                            'timestamp': data_point['timestamp'].isoformat(),
                            'value': data_point['value']
                        })
            
            # 获取趋势预测
            prediction_data = self.analyzer.get_prediction_data(corr_kks)
            
            # 获取分析结果
            analysis_result = None
            if hasattr(self.analyzer, 'analysis_results') and self.analyzer.analysis_results:
                point_analysis = self.analyzer.analysis_results.get('point_analysis', {})
                if corr_kks in point_analysis:
                    analysis_result = {
                        'trend': point_analysis[corr_kks].get('trend', 'UNKNOWN'),
                        'predicted_trend': point_analysis[corr_kks].get('predicted_trend', 'UNKNOWN'),
                        'alarm_level': point_analysis[corr_kks].get('alarm_level', 'NORMAL'),
                        'anomaly_probability': point_analysis[corr_kks].get('anomaly_probability', 0.0)
                    }
            
            return {
                'kks': corr_kks,
                'name': point_info['name'],
                'description': point_info['description'],
                'system': point_info['system'],
                'current_value': current_value,
                'unit': point_info['unit'],
                'recent_history': recent_history[-36:],  # 最多36个点（3分钟数据）
                'prediction': prediction_data,
                'analysis': analysis_result
            }
            
        except Exception as e:
            print(f"获取相关性测点 {corr_kks} 数据失败: {e}")
            return None
    
    def _deepseek_analyzer(self):
        """DeepSeek异步分析线程"""
        while self.running:
            try:
                fault_info = self.deepseek_queue.get(timeout=1.0)
                
                # 异步处理DeepSeek分析
                self._process_deepseek_analysis(fault_info)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"DeepSeek队列处理错误: {e}")
    
    def _process_deepseek_analysis(self, fault_info: Dict):
        """处理DeepSeek分析（异步）"""
        max_retries = 2  # 最大重试次数
        retry_delay = 10  # 重试延迟（秒）
        
        for attempt in range(max_retries):
            try:
                print(f"开始DeepSeek分析: {fault_info['name']} (尝试 {attempt + 1}/{max_retries})")
                
                # 添加阈值信息
                fault_info_with_thresholds = self._add_threshold_info(fault_info)
                
                analysis_result = self.deepseek_client.analyze_fault(fault_info_with_thresholds)
                if analysis_result:
                    # 传入故障信息和分析结果
                    self.deepseek_client.send_analysis_result(fault_info_with_thresholds, analysis_result)
                    print(f"DeepSeek分析完成: {fault_info['name']}")
                    
                    # 记录DeepSeek分析结果到日志
                    self._log_deepseek_analysis(fault_info['kks'], analysis_result)
                    break  # 成功则退出重试循环
                else:
                    if attempt < max_retries - 1:
                        print(f"DeepSeek分析失败，{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                        time.sleep(retry_delay)
                    else:
                        print(f"DeepSeek分析最终失败: {fault_info['name']}")
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    print(f"发送到DeepSeek失败，{retry_delay}秒后重试... (尝试 {attempt + 1}/{max_retries})")
                    time.sleep(retry_delay)
                else:
                    print(f"发送到DeepSeek最终失败 {fault_info['kks']}: {e}")
    
    def _log_analysis_result(self, result: Dict):
        """记录分析结果到日志"""
        try:
            self._update_log_file()
            
            log_message = (
                f"分析完成 - 数据源: {result['data_source']}, "
                f"状态: {result['overall_health']}, "
                f"风险等级: {result['risk_level']}, "
                f"报警数: {len(result['alarms'])}, "
                f"警告数: {len(result['warnings'])}, "
                f"故障点: {len(result['fault_points'])}"
            )
            self.logger.info(log_message)
            
            # 记录所有报警和故障点
            for alarm in result['alarms']:
                self.logger.warning(f"严重报警: {alarm}")
            
            for fault_point in result['fault_points']:
                fault_log = (
                    f"故障检测 - 测点: {fault_point['name']} ({fault_point['kks']}), "
                    f"数值: {fault_point['current_value']} {fault_point['unit']}, "
                    f"报警级别: {fault_point['alarm_level']}, "
                    f"波动: {'是' if fault_point['fluctuation_detected'] else '否'}, "
                    f"突变: {'是' if fault_point['mutation_detected'] else '否'}, "
                    f"异常概率: {fault_point['anomaly_probability']:.3f}, "
                    f"异常信号: {', '.join(fault_point['anomaly_signals'])}"
                )
                self.logger.warning(fault_log)
                
        except Exception as e:
            print(f"记录日志错误: {e}")
    
    def _send_fault_reports(self, fault_points: List[Dict]):
        """发送故障报告到9003端口"""
        for fault_info in fault_points:
            try:
                # 添加阈值信息到故障信息中
                fault_info_with_thresholds = self._add_threshold_info(fault_info)
                fault_content = self._create_fault_file_content(fault_info_with_thresholds)
                
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                    sock.connect((config.HOST, config.FAULT_SEND_PORT))
                    
                    fault_filename = f"{fault_info['name']}（{fault_info['kks']}）_fault.txt"
                    sock.sendall(fault_filename.encode('utf-8') + b'\n')
                    
                    sock.sendall(fault_content.encode('utf-8'))
                    
                    print(f"故障文件已发送: {fault_filename}")
                    
            except Exception as e:
                print(f"发送故障报告失败 {fault_info['kks']}: {e}")
    
    def _add_threshold_info(self, fault_info: Dict) -> Dict:
        """添加阈值信息到故障信息中"""
        try:
            thresholds = self.point_loader.get_alarm_thresholds(fault_info['kks'])
            if thresholds:
                fault_info['thresholds'] = {
                    'HHH': thresholds.get('HHH'),
                    'HH': thresholds.get('HH'),
                    'H': thresholds.get('H'),
                    'L': thresholds.get('L'),
                    'LL': thresholds.get('LL'),
                    'LLL': thresholds.get('LLL'),
                    'lower_limit': thresholds.get('lower_limit'),
                    'upper_limit': thresholds.get('upper_limit')
                }
        except Exception as e:
            print(f"添加阈值信息失败: {e}")
        
        return fault_info
    
    def _log_deepseek_analysis(self, kks: str, analysis_result: Dict):
        """记录DeepSeek分析结果到日志"""
        try:
            self._update_log_file()
            
            log_message = f"DeepSeek分析结果 - 测点: {kks}, 置信度: {analysis_result['confidence_score']}"
            self.logger.info(log_message)
                
        except Exception as e:
            print(f"记录DeepSeek分析结果错误: {e}")
    
    def _create_fault_file_content(self, fault_info: Dict) -> str:
        """创建故障文件内容"""
        content = []
        content.append("-" * 80)
        content.append(f"故障记录时间: {fault_info['timestamp']}")
        content.append("-" * 80)
        content.append(f"当前数值: {fault_info['current_value']} {fault_info['unit']}")
        content.append(f"报警级别: {fault_info['alarm_level']}")
        
        # 只有当实际波动超过点表阈值时才记录
        if fault_info.get('fluctuation_detected'):
            actual_fluct = fault_info.get('actual_fluctuation', 0)
            threshold_fluct = fault_info.get('fluctuation_range', 0)
            content.append(f"检测到剧烈波动: {actual_fluct:.2f} {fault_info['unit']}/s > 阈值 {threshold_fluct} {fault_info['unit']}/s")
        
        # 只有当实际突变超过点表阈值时才记录
        if fault_info.get('mutation_detected'):
            actual_mut = fault_info.get('actual_mutation', 0)
            threshold_mut = fault_info.get('mutation_range', 0)
            content.append(f"检测到数值突变: {actual_mut:.2f} {fault_info['unit']} > 阈值 {threshold_mut} {fault_info['unit']}")
        
        content.append(f"异常概率: {fault_info['anomaly_probability']:.3f}")
        content.append(f"当前趋势: {fault_info['trend']}")
        content.append(f"预测趋势: {fault_info['predicted_trend']}")
        content.append(f"状态描述: {fault_info['status_description']}")
        content.append(f"异常信号: {', '.join(fault_info['anomaly_signals'])}")
        
        # 添加相关性测点信息
        if 'correlation_points' in fault_info:
            correlation_data = fault_info['correlation_points']
            content.append("")
            content.append("相关性测点信息:")
            content.append("-" * 40)
            
            if correlation_data['positive']:
                content.append("正相关测点:")
                for corr_point in correlation_data['positive']:
                    content.append(f"  - {corr_point['name']}: {corr_point['current_value']} {corr_point['unit']} "
                                 f"(趋势: {corr_point.get('analysis', {}).get('trend', 'UNKNOWN')})")
            
            if correlation_data['negative']:
                content.append("负相关测点:")
                for corr_point in correlation_data['negative']:
                    content.append(f"  - {corr_point['name']}: {corr_point['current_value']} {corr_point['unit']} "
                                 f"(趋势: {corr_point.get('analysis', {}).get('trend', 'UNKNOWN')})")
        
        # 添加阈值信息
        if 'thresholds' in fault_info:
            content.append("")
            content.append("报警阈值:")
            content.append("-" * 40)
            thresholds = fault_info['thresholds']
            if thresholds.get('HHH'):
                content.append(f"HHH: {thresholds['HHH']} {fault_info['unit']}")
            if thresholds.get('HH'):
                content.append(f"HH: {thresholds['HH']} {fault_info['unit']}")
            if thresholds.get('H'):
                content.append(f"H: {thresholds['H']} {fault_info['unit']}")
            if thresholds.get('L'):
                content.append(f"L: {thresholds['L']} {fault_info['unit']}")
            if thresholds.get('LL'):
                content.append(f"LL: {thresholds['LL']} {fault_info['unit']}")
            if thresholds.get('LLL'):
                content.append(f"LLL: {thresholds['LLL']} {fault_info['unit']}")
            if thresholds.get('lower_limit'):
                content.append(f"下限: {thresholds['lower_limit']} {fault_info['unit']}")
            if thresholds.get('upper_limit'):
                content.append(f"上限: {thresholds['upper_limit']} {fault_info['unit']}")
        
        content.append("")
        content.append("前2.5分钟历史数据:")
        content.append("-" * 40)
        
        # 显示30个历史数据点
        history_to_show = fault_info['recent_history'][-30:] if fault_info['recent_history'] else []
        for history_point in history_to_show:
            content.append(f"{history_point['timestamp']}: {history_point['value']} {fault_info['unit']}")
        
        return "\n".join(content)
    
    def _result_sender(self):
        """结果发送线程"""
        while self.running:
            try:
                result = self.result_queue.get(timeout=1.0)
                
                self._send_analysis_result(result)
                
            except queue.Empty:
                continue
            except Exception as e:
                print(f"结果发送错误: {e}")
    
    def _send_analysis_result(self, result: Dict):
        """发送分析结果"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.connect((config.HOST, config.RESULT_SEND_PORT))
                message = json.dumps(result, ensure_ascii=False).encode('utf-8')
                sock.sendall(message)
                print(f"分析结果已发送，总体状态: {result['overall_health']}")
        except Exception as e:
            pass
    
    def _display_analysis_result(self, result: Dict):
        """显示分析结果"""
        print("\n" + "=" * 80)
        print(f"数据源: {result['data_source']}")
        print(f"分析时间: {result['timestamp']}")
        print(f"接收时间: {result['received_time']}")
        print(f"总体健康状态: {result['overall_health']}")
        print(f"风险等级: {result['risk_level']}")
        print(f"总结: {result['summary']}")
        
        if result['alarms']:
            print("\n严重报警:")
            for alarm in result['alarms']:
                print(f"  [CRITICAL] {alarm}")
        
        if result['warnings']:
            print("\n警告信息:")
            for warning in result['warnings']:
                print(f"  [WARNING] {warning}")
        
        if result['fault_detected']:
            print("\n故障检测:")
            for fault in result['fault_points']:
                fault_type = []
                if fault['fluctuation_detected']:
                    actual_fluct = fault.get('actual_fluctuation', 0)
                    threshold_fluct = fault.get('fluctuation_range', 0)
                    fault_type.append(f"波动({actual_fluct:.2f}>{threshold_fluct})")
                if fault['mutation_detected']:
                    actual_mut = fault.get('actual_mutation', 0)
                    threshold_mut = fault.get('mutation_range', 0)
                    fault_type.append(f"突变({actual_mut:.2f}>{threshold_mut})")
                if fault['anomaly_probability'] > 0.8:
                    fault_type.append("异常")
                
                print(f"  [FAULT] {fault['name']}: {fault['current_value']} {fault['unit']} - {', '.join(fault_type)}")
        
        critical_points = {k: v for k, v in result['point_analysis'].items() 
                          if v['alarm_level'] in ['CRITICAL', 'HIGH']}
        
        if critical_points:
            print("\n关键测点状态:")
            for kks, point in critical_points.items():
                status_icon = "[CRITICAL]" if point['alarm_level'] == 'CRITICAL' else "[WARNING]"
                print(f"  {status_icon} {point['name']}: {point['current_value']} {point['unit']} - {point['status_description']}")
        
        if result['prediction_alarms']:
            print("\n预测报警:")
            for alarm in result['prediction_alarms']:
                print(f"  [PREDICTION] {alarm['name']}: {alarm['description']}")
        
        print("=" * 80)


def main():
    """主函数"""
    print("9F级燃气电厂智能监盘系统")
    print("基于LimiX（极数）模型的智能数据分析平台")
    print("系统配置: 支持SIS数据源")
    print("=" * 60)
    
    system = GasTurbineMonitoringSystem()
    system.start()

if __name__ == "__main__":
    main()
   

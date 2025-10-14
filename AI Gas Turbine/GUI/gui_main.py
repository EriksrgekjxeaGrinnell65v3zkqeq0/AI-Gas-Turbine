import sys
import os
import threading
import time
from datetime import datetime

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from PyQt5.QtWidgets import (QApplication, QMainWindow, QTabWidget, QVBoxLayout, 
                           QHBoxLayout, QWidget, QStatusBar, QMessageBox)
from PyQt5.QtCore import QTimer, pyqtSignal, QObject
from PyQt5.QtGui import QIcon

# 导入自定义组件
from GUI.components.main_dashboard import MainDashboard
from GUI.components.data_monitor import DataMonitor
from GUI.components.trend_analyzer import TrendAnalyzer
from GUI.components.fault_diagnosis import FaultDiagnosis
from GUI.components.system_config import SystemConfig
from GUI.models.data_manager import DataManager
from GUI.models.alarm_manager import AlarmManager

class SignalEmitter(QObject):
    """信号发射器，用于线程间通信"""
    data_updated = pyqtSignal(dict)  # 数据更新信号
    alarm_triggered = pyqtSignal(dict)  # 报警触发信号
    analysis_completed = pyqtSignal(dict)  # 分析完成信号
    deepseek_analysis_completed = pyqtSignal(dict)  # DeepSeek分析完成信号

class GasTurbineMonitorGUI(QMainWindow):
    """燃气轮机监控系统主窗口"""
    
    def __init__(self):
        super().__init__()
        self.signal_emitter = SignalEmitter()
        self.data_manager = DataManager()
        self.alarm_manager = AlarmManager()
        self.deepseek_client = None
        
        self.init_ui()
        self.init_data_connections()
        self.init_deepseek_client()
        self.start_background_tasks()
        
    def init_ui(self):
        """初始化用户界面"""
        self.setWindowTitle("9F燃气电厂智能监盘系统")
        self.setGeometry(100, 100, 1400, 900)
        
        # 创建中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 添加各个功能标签页
        self.dashboard_tab = MainDashboard(self.data_manager, self.alarm_manager)
        self.data_monitor_tab = DataMonitor(self.data_manager)
        self.trend_analyzer_tab = TrendAnalyzer(self.data_manager)
        self.fault_diagnosis_tab = FaultDiagnosis(self.data_manager)
        self.system_config_tab = SystemConfig()
        
        self.tab_widget.addTab(self.dashboard_tab, "主监控面板")
        self.tab_widget.addTab(self.data_monitor_tab, "数据监控")
        self.tab_widget.addTab(self.trend_analyzer_tab, "趋势分析")
        self.tab_widget.addTab(self.fault_diagnosis_tab, "故障诊断")
        self.tab_widget.addTab(self.system_config_tab, "系统配置")
        
        main_layout.addWidget(self.tab_widget)
        
        # 创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("系统初始化完成 - 等待数据连接")
        
        # 应用样式
        self.apply_styles()
        
    def init_data_connections(self):
        """初始化数据连接"""
        # 连接信号和槽
        self.signal_emitter.data_updated.connect(self.on_data_updated)
        self.signal_emitter.alarm_triggered.connect(self.on_alarm_triggered)
        self.signal_emitter.analysis_completed.connect(self.on_analysis_completed)
        self.signal_emitter.deepseek_analysis_completed.connect(self.on_deepseek_analysis_completed)
        
        # 设置定时器更新数据
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_display_data)
        self.data_timer.start(5000)  # 5秒更新一次
        
    def init_deepseek_client(self):
        """初始化DeepSeek客户端"""
        try:
            from enhanced_deepseek_client import EnhancedDeepSeekClient
            self.deepseek_client = EnhancedDeepSeekClient()
            print("DeepSeek客户端初始化成功")
        except ImportError as e:
            print(f"无法导入DeepSeek客户端: {e}")
            self.deepseek_client = None
        except Exception as e:
            print(f"DeepSeek客户端初始化失败: {e}")
            self.deepseek_client = None
    
    def start_background_tasks(self):
        """启动后台任务"""
        # 启动数据采集线程
        self.data_thread = threading.Thread(target=self.data_collection_worker, daemon=True)
        self.data_thread.start()
        
        # 启动分析线程
        self.analysis_thread = threading.Thread(target=self.analysis_worker, daemon=True)
        self.analysis_thread.start()
        
        # 启动DeepSeek分析线程
        self.deepseek_thread = threading.Thread(target=self.deepseek_analysis_worker, daemon=True)
        self.deepseek_thread.start()
        
    def data_collection_worker(self):
        """数据采集工作线程"""
        try:
            # 尝试导入SIS数据采集器
            from sis_data_collector import SISDataCollector
            from config import config
            
            # 使用绝对路径确保文件能找到
            cor_kks_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'Cor_kks.xls')
            
            collector = SISDataCollector(
                config.REAL_SIS_CONFIG['base_url'],
                config.REAL_SIS_CONFIG['username'],
                config.REAL_SIS_CONFIG['password']
            )
            
            # 重新加载KKS映射表
            collector.kks_mapper.excel_file_path = cor_kks_path
            collector.kks_mapper.load_mapping_data()
            
            if collector.login():
                print("SIS数据采集器登录成功")
                while True:
                    try:
                        tag_items = collector.get_tag_data()
                        if tag_items:
                            kks_data = collector.convert_to_kks_format(tag_items)
                            
                            # 更新数据管理器
                            self.data_manager.update_realtime_data(kks_data)
                            
                            # 发送数据更新信号
                            self.signal_emitter.data_updated.emit({
                                'timestamp': datetime.now().isoformat(),
                                'data_points': kks_data,
                                'source': 'REAL_SIS'
                            })
                        
                        time.sleep(5)  # 5秒采集间隔
                        
                    except Exception as e:
                        print(f"数据采集错误: {e}")
                        time.sleep(10)
            else:
                print("SIS登录失败，使用模拟数据")
                self.use_simulated_data()
                
        except ImportError:
            print("无法导入SIS数据采集器，使用模拟数据")
            self.use_simulated_data()
        except Exception as e:
            print(f"数据采集初始化失败: {e}")
            self.use_simulated_data()
    
    def use_simulated_data(self):
        """使用模拟数据"""
        import random
        import time
        
        # 模拟关键测点
        simulated_points = {
            "01MBY10CE901_XQ01": 380.0,   # GT负荷
            "01MBA10CS901_XQ01": 3010.5,  # 燃机转速
            "01HAD10CP901_XQ01": 585.3,   # 排气温度
            "01HAD10CP902_XQ01": 25.8,    # 燃料压力
            "01HAD10BL102-CAL": -50.2,    # 高压汽包水位
            "01MBA10CP901_XQ01": 2.5,     # 润滑油压力
        }
        
        while True:
            try:
                # 生成随机波动
                current_data = {}
                for kks, base_value in simulated_points.items():
                    # 在基础值上添加随机波动
                    variation = random.uniform(-0.05, 0.05) * base_value
                    current_data[kks] = base_value + variation
                
                # 更新数据管理器
                self.data_manager.update_realtime_data(current_data)
                
                # 发送数据更新信号
                self.signal_emitter.data_updated.emit({
                    'timestamp': datetime.now().isoformat(),
                    'data_points': current_data,
                    'source': 'SIMULATED'
                })
                
                time.sleep(5)
                
            except Exception as e:
                print(f"模拟数据生成错误: {e}")
                time.sleep(10)
    
    def analysis_worker(self):
        """分析工作线程"""
        try:
            # 尝试导入分析引擎
            from limix_analyzer import GasTurbineAnalyzer
            from point_table_loader import PointTableLoader
            
            # 使用绝对路径
            point_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'point.xls')
            point_loader = PointTableLoader(point_file_path)
            
            if point_loader.load_point_table():
                model_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'LimiX', 'models', 'LimiX-16M.ckpt')
                analyzer = GasTurbineAnalyzer(model_path, point_loader)
                
                while True:
                    try:
                        current_data = self.data_manager.get_current_data()
                        if current_data:
                            analysis_result = analyzer.analyze_current_status(current_data)
                            
                            # 更新报警管理器
                            self.alarm_manager.update_alarms(analysis_result)
                            
                            # 发送分析完成信号
                            self.signal_emitter.analysis_completed.emit(analysis_result)
                            
                            # 如果有故障点，触发DeepSeek分析
                            if analysis_result.get('fault_points'):
                                for fault_point in analysis_result['fault_points']:
                                    if fault_point.get('send_to_deepseek', True):
                                        self.trigger_deepseek_analysis(fault_point, current_data)
                        
                        time.sleep(10)  # 10秒分析间隔
                        
                    except Exception as e:
                        print(f"分析错误: {e}")
                        time.sleep(30)
            else:
                print("点表加载失败，跳过分析")
                
        except ImportError:
            print("无法导入分析引擎，跳过分析")
        except Exception as e:
            print(f"分析引擎初始化失败: {e}")
    
    def trigger_deepseek_analysis(self, fault_point, current_data):
        """触发DeepSeek分析"""
        if self.deepseek_client:
            try:
                # 在后台线程中执行DeepSeek分析
                threading.Thread(
                    target=self._run_deepseek_analysis,
                    args=(fault_point, current_data),
                    daemon=True
                ).start()
            except Exception as e:
                print(f"触发DeepSeek分析失败: {e}")
    
    def _run_deepseek_analysis(self, fault_point, current_data):
        """执行DeepSeek分析"""
        try:
            # 添加相关性测点信息
            if hasattr(self, 'point_loader'):
                correlation_data = self._get_correlation_data(fault_point['kks'], current_data)
                fault_point['correlation_points'] = correlation_data
            
            # 添加阈值信息
            fault_point_with_thresholds = self._add_threshold_info(fault_point)
            
            # 执行DeepSeek分析
            analysis_result = self.deepseek_client.analyze_fault(fault_point_with_thresholds)
            if analysis_result:
                # 发送分析完成信号
                self.signal_emitter.deepseek_analysis_completed.emit({
                    'fault_point': fault_point_with_thresholds,
                    'analysis_result': analysis_result
                })
                print(f"DeepSeek分析完成: {fault_point['name']}")
            
        except Exception as e:
            print(f"DeepSeek分析执行失败: {e}")
    
    def _get_correlation_data(self, fault_kks, current_data):
        """获取相关性测点数据（简化实现）"""
        return {
            'positive': [],
            'negative': []
        }
    
    def _add_threshold_info(self, fault_point):
        """添加阈值信息（简化实现）"""
        fault_point['thresholds'] = {
            'HHH': 495,
            'HH': 450,
            'H': 400,
            'L': 200,
            'LL': 150,
            'LLL': 100
        }
        return fault_point
    
    def deepseek_analysis_worker(self):
        """DeepSeek分析工作线程"""
        # 这个线程用于处理DeepSeek分析队列
        while True:
            time.sleep(1)
    
    def on_data_updated(self, data):
        """处理数据更新"""
        self.status_bar.showMessage(f"数据更新: {datetime.now().strftime('%H:%M:%S')} - {len(data['data_points'])}个测点")
        
        # 更新各个标签页
        self.dashboard_tab.update_display(data)
        self.data_monitor_tab.update_display(data)
        self.trend_analyzer_tab.update_data(data)
    
    def on_alarm_triggered(self, alarm_data):
        """处理报警触发"""
        # 显示报警对话框
        QMessageBox.warning(self, "系统报警", alarm_data['message'])
        
        # 更新报警显示
        self.dashboard_tab.update_alarms(alarm_data)
    
    def on_analysis_completed(self, analysis_data):
        """处理分析完成"""
        self.trend_analyzer_tab.update_analysis(analysis_data)
        self.fault_diagnosis_tab.update_diagnosis(analysis_data)
    
    def on_deepseek_analysis_completed(self, data):
        """处理DeepSeek分析完成"""
        self.fault_diagnosis_tab.update_deepseek_analysis(data)
    
    def update_display_data(self):
        """更新显示数据"""
        current_data = self.data_manager.get_current_data()
        if current_data:
            self.dashboard_tab.refresh_display()
    
    def apply_styles(self):
        """应用样式"""
        # 使用默认样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
                font-family: "Microsoft YaHei", "SimHei", sans-serif;
            }
            QTabWidget::pane {
                border: 1px solid #C2C7CB;
                background-color: white;
                border-radius: 4px;
            }
            QTabBar::tab {
                background-color: #E1E1E1;
                padding: 8px 16px;
                margin-right: 2px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }
            QTabBar::tab:selected {
                background-color: #4CAF50;
                color: white;
            }
            QTabBar::tab:hover {
                background-color: #D6D6D6;
            }
            QGroupBox {
                font-weight: bold;
                border: 1px solid #CCCCCC;
                border-radius: 4px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QTableWidget {
                gridline-color: #d0d0d0;
                selection-background-color: #4CAF50;
            }
            QTableWidget::item {
                padding: 5px;
            }
            QHeaderView::section {
                background-color: #f0f0f0;
                padding: 4px;
                border: 1px solid #d0d0d0;
                font-weight: bold;
            }
        """)
    
    def closeEvent(self, event):
        """关闭事件处理"""
        reply = QMessageBox.question(self, '确认退出', 
                                   '确定要退出监控系统吗？',
                                   QMessageBox.Yes | QMessageBox.No,
                                   QMessageBox.No)
        
        if reply == QMessageBox.Yes:
            # 停止定时器
            self.data_timer.stop()
            event.accept()
        else:
            event.ignore()

def main():
    app = QApplication(sys.argv)
    
    # 设置应用程序属性
    app.setApplicationName("基于LimiX（极数）分析模型与大语言模型Deepseek+RAG专家系统的燃气轮机监控系统")
    app.setApplicationVersion("1.0.0")
    
    # 创建并显示主窗口
    window = GasTurbineMonitorGUI()
    window.show()
    
    sys.exit(app.exec_())

if __name__ == '__main__':
    main()
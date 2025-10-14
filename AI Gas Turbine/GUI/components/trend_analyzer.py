from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QComboBox, 
                           QGroupBox, QLabel, QPushButton, QSpinBox)
from PyQt5.QtCore import Qt
import os
import sys

# 在文件开头的导入部分添加字体设置
try:
    import matplotlib
    # 设置matplotlib使用Qt5后端
    matplotlib.use('Qt5Agg')
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    from matplotlib import pyplot as plt
    import matplotlib.font_manager as fm
    
    # 设置中文字体 - 修复字体问题
    import platform
    system = platform.system()
    if system == "Windows":
        # Windows系统使用系统字体
        plt.rcParams['font.sans-serif'] = ['SimHei', 'Microsoft YaHei', 'DejaVu Sans']
    elif system == "Darwin":  # macOS
        plt.rcParams['font.sans-serif'] = ['Arial Unicode MS', 'Heiti TC', 'DejaVu Sans']
    else:  # Linux
        plt.rcParams['font.sans-serif'] = ['WenQuanYi Micro Hei', 'DejaVu Sans']
    
    plt.rcParams['axes.unicode_minus'] = False
    
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    print("Matplotlib不可用，趋势图表功能将受限")
    MATPLOTLIB_AVAILABLE = False

class TrendAnalyzer(QWidget):
    """趋势分析组件"""
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.current_kks = None
        self.history_points = 50  # 默认显示50个数据点
        
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建控制面板
        control_layout = QHBoxLayout()
        
        control_layout.addWidget(QLabel("选择测点:"))
        self.point_selector = QComboBox()
        self.point_selector.currentTextChanged.connect(self.on_point_selected)
        control_layout.addWidget(self.point_selector)
        
        control_layout.addWidget(QLabel("显示点数:"))
        self.points_spinbox = QSpinBox()
        self.points_spinbox.setRange(10, 500)
        self.points_spinbox.setValue(50)
        self.points_spinbox.valueChanged.connect(self.on_points_changed)
        control_layout.addWidget(self.points_spinbox)
        
        self.refresh_btn = QPushButton("刷新图表")
        self.refresh_btn.clicked.connect(self.refresh_chart)
        control_layout.addWidget(self.refresh_btn)
        
        control_layout.addStretch()
        layout.addLayout(control_layout)
        
        # 创建图表区域
        chart_group = QGroupBox("趋势分析图表")
        chart_layout = QVBoxLayout()
        
        if MATPLOTLIB_AVAILABLE:
            # 创建matplotlib图表
            self.figure = Figure(figsize=(10, 6), dpi=100)
            self.canvas = FigureCanvas(self.figure)
            self.ax = self.figure.add_subplot(111)
            
            # 设置图表样式
            self.ax.grid(True, alpha=0.3)
            self.ax.set_xlabel('时间')
            self.ax.set_ylabel('数值')
            self.ax.set_title('实时趋势图')
            
            chart_layout.addWidget(self.canvas)
            
            # 初始显示提示
            self.ax.text(0.5, 0.5, '请选择测点查看趋势', 
                        horizontalalignment='center',
                        verticalalignment='center',
                        transform=self.ax.transAxes,
                        fontsize=14,
                        color='gray')
            self.canvas.draw()
            
        else:
            # 如果没有matplotlib，显示提示信息
            warning_label = QLabel(
                "趋势图表功能需要安装matplotlib\n"
                "请运行: pip install matplotlib\n\n"
                "当前显示模拟趋势数据"
            )
            warning_label.setAlignment(Qt.AlignCenter)
            warning_label.setStyleSheet("color: red; font-size: 12pt;")
            chart_layout.addWidget(warning_label)
            
            # 创建简单的文本显示区域用于模拟
            self.trend_text = QLabel("趋势数据将在这里显示")
            self.trend_text.setAlignment(Qt.AlignCenter)
            chart_layout.addWidget(self.trend_text)
        
        chart_group.setLayout(chart_layout)
        layout.addWidget(chart_group)
        
        self.setLayout(layout)
        
        # 初始化测点列表
        self.update_point_list()
    
    def update_point_list(self):
        """更新测点列表"""
        self.point_selector.clear()
        
        # 获取所有可用的KKS代码
        all_kks = self.data_manager.get_all_kks()
        if all_kks:
            for kks in all_kks:
                self.point_selector.addItem(kks)
            
            # 默认选择第一个测点
            if all_kks:
                self.current_kks = all_kks[0]
                self.update_chart()
    
    def on_point_selected(self, kks):
        """测点选择变化"""
        if kks:
            self.current_kks = kks
            self.update_chart()
    
    def on_points_changed(self, value):
        """显示点数变化"""
        self.history_points = value
        self.update_chart()
    
    def refresh_chart(self):
        """刷新图表"""
        self.update_chart()
    
    def update_data(self, data):
        """更新数据"""
        # 数据更新时刷新测点列表（如果有新测点）
        current_count = self.point_selector.count()
        new_kks = list(data['data_points'].keys())
        
        if len(new_kks) != current_count:
            self.update_point_list()
        
        # 如果当前有选中的测点，更新图表
        if self.current_kks:
            self.update_chart()
    
    def update_chart(self):
        """更新图表"""
        if not self.current_kks:
            return
        
        if MATPLOTLIB_AVAILABLE:
            try:
                # 获取历史数据
                trend_data = self.data_manager.get_trend_data(self.current_kks, self.history_points)
                
                if not trend_data:
                    # 没有数据，显示提示
                    self.ax.clear()
                    self.ax.text(0.5, 0.5, '暂无数据', 
                                horizontalalignment='center',
                                verticalalignment='center',
                                transform=self.ax.transAxes,
                                fontsize=14,
                                color='gray')
                    self.ax.grid(True, alpha=0.3)
                    self.canvas.draw()
                    return
                
                # 提取时间和数值
                times = [t for t, v in trend_data]
                values = [v for t, v in trend_data]
                
                # 清空并重绘图表
                self.ax.clear()
                
                # 绘制趋势线
                self.ax.plot(times, values, 'b-', linewidth=2, label='实际值')
                
                # 设置图表属性
                self.ax.set_xlabel('时间')
                self.ax.set_ylabel('数值')
                self.ax.set_title(f'{self.current_kks} - 趋势分析')
                self.ax.grid(True, alpha=0.3)
                self.ax.legend()
                
                # 旋转x轴标签以避免重叠
                plt.setp(self.ax.xaxis.get_majorticklabels(), rotation=45)
                
                # 自动调整布局
                self.figure.tight_layout()
                
                # 刷新画布
                self.canvas.draw()
                
            except Exception as e:
                print(f"绘制图表错误: {e}")
                # 显示错误信息
                self.ax.clear()
                self.ax.text(0.5, 0.5, f'绘图错误: {str(e)}', 
                            horizontalalignment='center',
                            verticalalignment='center',
                            transform=self.ax.transAxes,
                            fontsize=12,
                            color='red')
                self.ax.grid(True, alpha=0.3)
                self.canvas.draw()
        else:
            # 没有matplotlib时的替代显示
            trend_data = self.data_manager.get_trend_data(self.current_kks, 10)  # 只显示最近10个点
            if trend_data:
                text = f"{self.current_kks} 最近趋势:\n"
                for i, (time, value) in enumerate(trend_data[-10:]):  # 显示最近10个点
                    time_str = time.strftime("%H:%M:%S")
                    text += f"{time_str}: {value:.2f}\n"
                self.trend_text.setText(text)
    
    def update_analysis(self, analysis_data):
        """更新分析结果"""
        # 这里可以添加基于分析结果的图表增强
        pass
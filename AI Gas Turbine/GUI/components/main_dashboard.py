from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, 
                           QGroupBox, QLabel, QTableWidget, QTableWidgetItem,
                           QProgressBar, QTextEdit)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor, QFont
from datetime import datetime

class MainDashboard(QWidget):
    """主监控面板"""
    
    def __init__(self, data_manager, alarm_manager):
        super().__init__()
        self.data_manager = data_manager
        self.alarm_manager = alarm_manager
        self.init_ui()
        
    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        
        # 顶部状态栏
        top_layout = self.create_top_status_bar()
        main_layout.addLayout(top_layout)
        
        # 中间主要内容区域
        middle_layout = QHBoxLayout()
        
        # 左侧关键参数区域
        left_panel = self.create_parameter_panel()
        middle_layout.addWidget(left_panel, 3)
        
        # 右侧报警和趋势区域
        right_panel = self.create_alarm_trend_panel()
        middle_layout.addWidget(right_panel, 2)
        
        main_layout.addLayout(middle_layout)
        
        # 底部系统信息区域
        bottom_panel = self.create_system_info_panel()
        main_layout.addWidget(bottom_panel)
        
        self.setLayout(main_layout)
        
    def create_top_status_bar(self):
        """创建顶部状态栏"""
        layout = QHBoxLayout()
        
        # 系统状态
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout()
        
        self.system_status_label = QLabel("● 正常运行")
        self.system_status_label.setStyleSheet("color: green; font-size: 16px; font-weight: bold;")
        status_layout.addWidget(self.system_status_label)
        
        self.data_source_label = QLabel("数据源: 等待连接...")
        status_layout.addWidget(self.data_source_label)
        
        self.update_time_label = QLabel("最后更新: --")
        status_layout.addWidget(self.update_time_label)
        
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 风险等级
        risk_group = QGroupBox("风险等级")
        risk_layout = QVBoxLayout()
        
        self.risk_level_label = QLabel("● 低风险")
        self.risk_level_label.setStyleSheet("color: blue; font-size: 16px; font-weight: bold;")
        risk_layout.addWidget(self.risk_level_label)
        
        self.risk_progress = QProgressBar()
        self.risk_progress.setMaximum(100)
        self.risk_progress.setValue(20)
        self.risk_progress.setStyleSheet("""
            QProgressBar {
                border: 1px solid grey;
                border-radius: 5px;
                text-align: center;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 4px;
            }
        """)
        risk_layout.addWidget(self.risk_progress)
        
        risk_group.setLayout(risk_layout)
        layout.addWidget(risk_group)
        
        # 报警统计
        alarm_group = QGroupBox("报警统计")
        alarm_layout = QGridLayout()
        
        self.critical_alarm_label = QLabel("严重: 0")
        self.critical_alarm_label.setStyleSheet("color: red; font-weight: bold; font-size: 14px;")
        alarm_layout.addWidget(self.critical_alarm_label, 0, 0)
        
        self.high_alarm_label = QLabel("高级: 0")
        self.high_alarm_label.setStyleSheet("color: orange; font-weight: bold; font-size: 14px;")
        alarm_layout.addWidget(self.high_alarm_label, 0, 1)
        
        self.medium_alarm_label = QLabel("中级: 0")
        self.medium_alarm_label.setStyleSheet("color: #FFD700; font-weight: bold; font-size: 14px;")
        alarm_layout.addWidget(self.medium_alarm_label, 1, 0)
        
        self.warning_label = QLabel("预警: 0")
        self.warning_label.setStyleSheet("color: #1E90FF; font-weight: bold; font-size: 14px;")
        alarm_layout.addWidget(self.warning_label, 1, 1)
        
        alarm_group.setLayout(alarm_layout)
        layout.addWidget(alarm_group)
        
        return layout
    
    def create_parameter_panel(self):
        """创建关键参数面板"""
        group = QGroupBox("关键测点监控")
        layout = QVBoxLayout()
        
        # 创建参数表格
        self.parameter_table = QTableWidget()
        self.parameter_table.setColumnCount(6)
        self.parameter_table.setHorizontalHeaderLabels(["测点", "当前值", "单位", "状态", "趋势", "报警级别"])
        self.parameter_table.setRowCount(0)
        
        # 设置表格属性
        self.parameter_table.setAlternatingRowColors(True)
        self.parameter_table.horizontalHeader().setStretchLastSection(True)
        self.parameter_table.setMinimumHeight(400)
        
        layout.addWidget(self.parameter_table)
        group.setLayout(layout)
        
        return group
    
    def create_alarm_trend_panel(self):
        """创建报警和趋势面板"""
        group = QGroupBox("实时状态")
        layout = QVBoxLayout()
        
        # 实时趋势图表区域
        trend_group = QGroupBox("实时趋势")
        trend_layout = QVBoxLayout()
        
        self.trend_chart_label = QLabel("趋势图表区域\n(需要安装matplotlib)")
        self.trend_chart_label.setMinimumHeight(200)
        self.trend_chart_label.setStyleSheet("""
            background-color: white; 
            border: 1px solid #ccc;
            padding: 10px;
            color: #666;
        """)
        self.trend_chart_label.setAlignment(Qt.AlignCenter)
        trend_layout.addWidget(self.trend_chart_label)
        
        trend_group.setLayout(trend_layout)
        layout.addWidget(trend_group)
        
        # 最新报警信息
        alarm_group = QGroupBox("最新故障诊断报告")
        alarm_layout = QVBoxLayout()
        
        self.alarm_text = QTextEdit()
        self.alarm_text.setMaximumHeight(150)
        self.alarm_text.setReadOnly(True)
        self.alarm_text.setStyleSheet("font-size: 10pt;")
        alarm_layout.addWidget(self.alarm_text)
        
        alarm_group.setLayout(alarm_layout)
        layout.addWidget(alarm_group)
        
        group.setLayout(layout)
        return group
    
    def create_system_info_panel(self):
        """创建系统信息面板"""
        group = QGroupBox("系统信息")
        layout = QHBoxLayout()
        
        self.system_info_label = QLabel("系统初始化中...")
        layout.addWidget(self.system_info_label)
        
        group.setLayout(layout)
        return group
    
    def update_display(self, data):
        """更新显示数据"""
        # 更新时间显示
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.update_time_label.setText(f"最后更新: {current_time}")
        
        # 更新数据源显示
        self.data_source_label.setText(f"数据源: {data.get('source', '未知')}")
        
        # 更新参数表格
        self.update_parameter_table(data['data_points'])
        
        # 更新报警统计
        self.update_alarm_stats()
        
        # 更新系统信息
        self.system_info_label.setText("系统运行正常 | 数据连接稳定 | 监控进行中")
    
    def update_parameter_table(self, data_points):
        """更新参数表格"""
        # 清空表格
        self.parameter_table.setRowCount(0)
        
        # 添加关键测点数据
        key_points = [
            "01MBY10CE901_XQ01",  # GT负荷
            "01MBA10CS901_XQ01",  # 燃机转速
            "01HAD10CP901_XQ01",  # 排气温度
            "01HAD10CP902_XQ01",  # 燃料压力
            "01HAD10BL102-CAL",   # 高压汽包水位
            "01MBA10CP901_XQ01",  # 润滑油压力
        ]
        
        for i, kks in enumerate(key_points):
            if kks in data_points:
                value = data_points[kks]
                
                # 获取测点信息
                point_info = self.get_point_info(kks)
                
                # 添加行
                row = self.parameter_table.rowCount()
                self.parameter_table.insertRow(row)
                
                # 添加数据
                self.parameter_table.setItem(row, 0, QTableWidgetItem(point_info['name']))
                self.parameter_table.setItem(row, 1, QTableWidgetItem(f"{value:.2f}"))
                self.parameter_table.setItem(row, 2, QTableWidgetItem(point_info['unit']))
                
                # 状态和趋势（简化实现）
                status_item = QTableWidgetItem("正常")
                trend_item = QTableWidgetItem("稳定")
                alarm_item = QTableWidgetItem("正常")
                
                # 根据数值设置颜色
                if self.is_value_alarming(kks, value):
                    alarm_item.setText("报警")
                    alarm_item.setForeground(QColor(255, 0, 0))
                    status_item.setForeground(QColor(255, 0, 0))
                
                self.parameter_table.setItem(row, 3, status_item)
                self.parameter_table.setItem(row, 4, trend_item)
                self.parameter_table.setItem(row, 5, alarm_item)
    
    def get_point_info(self, kks):
        """获取测点信息"""
        # 简化实现，实际应该从点表加载
        point_map = {
            "01MBY10CE901_XQ01": {"name": "GT负荷", "unit": "MW"},
            "01MBA10CS901_XQ01": {"name": "燃机转速", "unit": "rpm"},
            "01HAD10CP901_XQ01": {"name": "排气温度", "unit": "℃"},
            "01HAD10CP902_XQ01": {"name": "燃料压力", "unit": "bar"},
            "01HAD10BL102-CAL": {"name": "高压汽包水位", "unit": "mm"},
            "01MBA10CP901_XQ01": {"name": "润滑油压力", "unit": "bar"},
        }
        return point_map.get(kks, {"name": kks, "unit": ""})
    
    def is_value_alarming(self, kks, value):
        """检查数值是否报警"""
        # 简化实现，实际应该从点表获取阈值
        thresholds = {
            "01MBY10CE901_XQ01": (300, 450),  # GT负荷阈值
            "01HAD10CP901_XQ01": (500, 600),  # 排气温度阈值
            "01MBA10CS901_XQ01": (2900, 3100), # 燃机转速阈值
        }
        
        if kks in thresholds:
            min_val, max_val = thresholds[kks]
            return value < min_val or value > max_val
        
        return False
    
    def update_alarm_stats(self):
        """更新报警统计"""
        # 从报警管理器获取统计信息
        stats = self.alarm_manager.get_alarm_stats()
        
        self.critical_alarm_label.setText(f"严重: {stats.get('critical', 0)}")
        self.high_alarm_label.setText(f"高级: {stats.get('high', 0)}")
        self.medium_alarm_label.setText(f"中级: {stats.get('medium', 0)}")
        self.warning_label.setText(f"预警: {stats.get('warning', 0)}")
        
        # 更新风险进度条
        total_alarms = sum(stats.values())
        risk_value = min(total_alarms * 10, 100)
        self.risk_progress.setValue(risk_value)
        
        # 更新风险等级显示
        if stats.get('critical', 0) > 0:
            self.risk_level_label.setText("● 高风险")
            self.risk_level_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")
        elif stats.get('high', 0) > 0:
            self.risk_level_label.setText("● 中风险")
            self.risk_level_label.setStyleSheet("color: orange; font-size: 16px; font-weight: bold;")
        else:
            self.risk_level_label.setText("● 低风险")
            self.risk_level_label.setStyleSheet("color: blue; font-size: 16px; font-weight: bold;")
    
    def update_alarms(self, alarm_data):
        """更新报警显示"""
        # 在报警文本区域添加新报警
        current_text = self.alarm_text.toPlainText()
        timestamp = datetime.now().strftime("%H:%M:%S")
        new_alarm = f"● {timestamp} - {alarm_data['message']}\n"
        
        # 限制报警显示数量
        lines = current_text.split('\n')
        if len(lines) > 10:
            lines = lines[-9:]
        
        updated_text = '\n'.join(lines) + '\n' + new_alarm
        self.alarm_text.setText(updated_text)
        
        # 滚动到底部
        cursor = self.alarm_text.textCursor()
        cursor.movePosition(cursor.End)
        self.alarm_text.setTextCursor(cursor)
    
    def refresh_display(self):
        """刷新显示"""
        # 更新系统状态
        current_data = self.data_manager.get_current_data()
        if current_data:
            self.system_status_label.setText("● 正常运行")
            self.system_status_label.setStyleSheet("color: green; font-size: 16px; font-weight: bold;")
        else:
            self.system_status_label.setText("● 数据中断")
            self.system_status_label.setStyleSheet("color: red; font-size: 16px; font-weight: bold;")
    # 设置字体
def apply_styles(self):
    """应用样式"""
    import platform
    system = platform.system()
    
    if system == "Windows":
        font_family = "Microsoft YaHei, SimHei, sans-serif"
    elif system == "Darwin":  # macOS
        font_family = "PingFang SC, Hiragino Sans GB, sans-serif"
    else:  # Linux
        font_family = "WenQuanYi Micro Hei, sans-serif"
    
    self.setStyleSheet(f"""
        QMainWindow {{
            background-color: #f0f0f0;
            font-family: {font_family};
        }}
        /* 其他样式规则保持不变 */
    """)
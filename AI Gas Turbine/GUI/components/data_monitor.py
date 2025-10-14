from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, 
                           QGroupBox, QHeaderView, QComboBox, QLabel)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
import os
import pandas as pd

class DataMonitor(QWidget):
    """数据监控组件"""
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.kks_mapping = {}  # KKS到测点名称的映射
        self.init_kks_mapping()
        self.init_ui()
        
    def init_kks_mapping(self):
        """初始化KKS映射"""
        # 尝试从映射表加载
        try:
            project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            cor_kks_path = os.path.join(project_root, 'Cor_kks.xls')
            
            if os.path.exists(cor_kks_path):
                df = pd.read_excel(cor_kks_path, sheet_name='Sheet1')
                for _, row in df.iterrows():
                    sis_point = str(row['SIS数据点名']).strip() if pd.notna(row['SIS数据点名']) else ""
                    kks_point = str(row['对应KKS点名']).strip() if pd.notna(row['对应KKS点名']) else ""
                    description = str(row['测点']).strip() if pd.notna(row['测点']) else ""
                    
                    if sis_point and kks_point:
                        self.kks_mapping[kks_point] = {
                            'name': description if description else sis_point,
                            'sis_name': sis_point
                        }
                print(f"成功加载 {len(self.kks_mapping)} 个测点映射")
            else:
                print("映射表文件不存在，使用默认映射")
                self.create_default_mapping()
                
        except Exception as e:
            print(f"加载KKS映射表失败: {e}")
            self.create_default_mapping()
    
    def create_default_mapping(self):
        """创建默认映射"""
        default_mapping = {
            "01MBY10CE901_XQ01": {"name": "GT负荷", "sis_name": "GT_LOAD"},
            "01MBA10CS901_XQ01": {"name": "燃机转速", "sis_name": "GT_SPEED"},
            "01HAD10CP901_XQ01": {"name": "排气温度", "sis_name": "EXHAUST_TEMP"},
            "01HAD10CP902_XQ01": {"name": "燃料压力", "sis_name": "FUEL_PRESS"},
            "01HAD10BL102-CAL": {"name": "高压汽包水位", "sis_name": "DRUM_LEVEL"},
            "01MBA10CP901_XQ01": {"name": "润滑油压力", "sis_name": "LUBE_OIL_PRESS"},
        }
        self.kks_mapping.update(default_mapping)
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建筛选区域
        filter_layout = QHBoxLayout()
        filter_layout.addWidget(QLabel("系统筛选:"))
        
        self.system_filter = QComboBox()
        self.system_filter.addItem("所有系统")
        self.system_filter.addItem("GT系统")
        self.system_filter.addItem("HRSG系统")
        self.system_filter.addItem("辅助系统")
        self.system_filter.currentTextChanged.connect(self.filter_data)
        filter_layout.addWidget(self.system_filter)
        
        filter_layout.addStretch()
        layout.addLayout(filter_layout)
        
        group = QGroupBox("所有测点数据")
        table_layout = QVBoxLayout()
        
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels(["KKS代码", "测点名称", "当前值", "单位", "状态"])
        
        # 设置表格属性
        self.data_table.setAlternatingRowColors(True)
        self.data_table.horizontalHeader().setStretchLastSection(True)
        self.data_table.setSortingEnabled(True)
        
        # 设置列宽
        header = self.data_table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.Stretch)
        header.setSectionResizeMode(2, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        table_layout.addWidget(self.data_table)
        group.setLayout(table_layout)
        layout.addWidget(group)
        
        self.setLayout(layout)
    
    def update_display(self, data):
        """更新数据显示"""
        self.update_data_table(data['data_points'])
    
    def update_data_table(self, data_points):
        """更新数据表格"""
        # 清空表格
        self.data_table.setRowCount(0)
        
        # 获取系统筛选条件
        system_filter = self.system_filter.currentText()
        
        # 添加所有测点数据
        for kks, value in data_points.items():
            # 系统筛选
            if system_filter != "所有系统":
                system = self.get_point_system(kks)
                if system_filter == "GT系统" and system != "GT":
                    continue
                elif system_filter == "HRSG系统" and system != "HRSG":
                    continue
                elif system_filter == "辅助系统" and system not in ["AUX", "ELE"]:
                    continue
            
            # 获取测点信息
            point_info = self.kks_mapping.get(kks, {"name": kks, "unit": ""})
            
            # 添加行
            row = self.data_table.rowCount()
            self.data_table.insertRow(row)
            
            # 添加数据
            self.data_table.setItem(row, 0, QTableWidgetItem(kks))
            self.data_table.setItem(row, 1, QTableWidgetItem(point_info['name']))
            self.data_table.setItem(row, 2, QTableWidgetItem(f"{value:.2f}"))
            self.data_table.setItem(row, 3, QTableWidgetItem(self.get_point_unit(kks)))
            
            # 状态列
            status_item = QTableWidgetItem("正常")
            if self.is_value_alarming(kks, value):
                status_item.setText("报警")
                status_item.setForeground(QColor(255, 0, 0))
            else:
                status_item.setForeground(QColor(0, 128, 0))
            
            self.data_table.setItem(row, 4, status_item)
    
    def get_point_system(self, kks):
        """获取测点所属系统"""
        # 简化实现，根据KKS代码前缀判断
        if kks.startswith("01MBY") or kks.startswith("01MBA"):
            return "GT"
        elif kks.startswith("01HAD"):
            return "HRSG"
        else:
            return "AUX"
    
    def get_point_unit(self, kks):
        """获取测点单位"""
        # 简化实现，根据测点类型判断
        point_name = self.kks_mapping.get(kks, {}).get('name', '')
        if "负荷" in point_name or "LOAD" in kks:
            return "MW"
        elif "转速" in point_name or "SPEED" in kks:
            return "rpm"
        elif "温度" in point_name or "TEMP" in kks:
            return "℃"
        elif "压力" in point_name or "PRESS" in kks:
            return "bar"
        elif "水位" in point_name or "LEVEL" in kks:
            return "mm"
        else:
            return ""
    
    def is_value_alarming(self, kks, value):
        """检查数值是否报警"""
        # 简化实现
        thresholds = {
            "01MBY10CE901_XQ01": (300, 450),  # GT负荷阈值
            "01HAD10CP901_XQ01": (500, 600),  # 排气温度阈值
            "01MBA10CS901_XQ01": (2900, 3100), # 燃机转速阈值
            "01HAD10CP902_XQ01": (20, 30),    # 燃料压力阈值
            "01HAD10BL102-CAL": (-100, 100),  # 汽包水位阈值
            "01MBA10CP901_XQ01": (2.0, 3.0),  # 润滑油压力阈值
        }
        
        if kks in thresholds:
            min_val, max_val = thresholds[kks]
            return value < min_val or value > max_val
        
        return False
    
    def filter_data(self):
        """筛选数据"""
        # 触发表格更新
        current_data = self.data_manager.get_current_data()
        if current_data:
            self.update_data_table(current_data)
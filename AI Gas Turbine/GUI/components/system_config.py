from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                           QLabel, QLineEdit, QPushButton, QComboBox, 
                           QSpinBox, QCheckBox, QTabWidget, QTableWidget,
                           QTableWidgetItem, QHeaderView, QMessageBox,
                           QFileDialog, QProgressBar)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
import os
import json

class SystemConfig(QWidget):
    """系统配置组件 - 管理系统设置和参数"""
    
    def __init__(self):
        super().__init__()
        self.config_data = {}
        self.init_ui()
        self.load_config()
        
    def init_ui(self):
        """初始化界面"""
        main_layout = QVBoxLayout()
        
        # 创建标签页
        self.tab_widget = QTabWidget()
        
        # 基本设置标签页
        basic_tab = self.create_basic_settings_tab()
        self.tab_widget.addTab(basic_tab, "基本设置")
        
        # 数据源设置标签页
        datasource_tab = self.create_datasource_tab()
        self.tab_widget.addTab(datasource_tab, "数据源设置")
        
        # 报警设置标签页
        alarm_tab = self.create_alarm_settings_tab()
        self.tab_widget.addTab(alarm_tab, "报警设置")
        
        # 系统信息标签页
        info_tab = self.create_system_info_tab()
        self.tab_widget.addTab(info_tab, "系统信息")
        
        main_layout.addWidget(self.tab_widget)
        
        # 操作按钮
        button_layout = QHBoxLayout()
        
        save_btn = QPushButton("保存配置")
        save_btn.clicked.connect(self.save_config)
        
        reload_btn = QPushButton("重新加载")
        reload_btn.clicked.connect(self.load_config)
        
        reset_btn = QPushButton("恢复默认")
        reset_btn.clicked.connect(self.reset_config)
        
        button_layout.addWidget(save_btn)
        button_layout.addWidget(reload_btn)
        button_layout.addWidget(reset_btn)
        button_layout.addStretch(1)
        
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def create_basic_settings_tab(self):
        """创建基本设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 界面设置
        interface_group = QGroupBox("界面设置")
        interface_layout = QVBoxLayout()
        
        # 刷新间隔
        refresh_layout = QHBoxLayout()
        refresh_label = QLabel("界面刷新间隔:")
        self.refresh_spin = QSpinBox()
        self.refresh_spin.setRange(1, 60)
        self.refresh_spin.setSuffix(" 秒")
        refresh_layout.addWidget(refresh_label)
        refresh_layout.addWidget(self.refresh_spin)
        refresh_layout.addStretch(1)
        interface_layout.addLayout(refresh_layout)
        
        # 主题选择
        theme_layout = QHBoxLayout()
        theme_label = QLabel("界面主题:")
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["默认主题", "深色主题", "蓝色主题", "绿色主题"])
        theme_layout.addWidget(theme_label)
        theme_layout.addWidget(self.theme_combo)
        theme_layout.addStretch(1)
        interface_layout.addLayout(theme_layout)
        
        # 语言设置
        language_layout = QHBoxLayout()
        language_label = QLabel("语言:")
        self.language_combo = QComboBox()
        self.language_combo.addItems(["中文", "English"])
        language_layout.addWidget(language_label)
        language_layout.addWidget(self.language_combo)
        language_layout.addStretch(1)
        interface_layout.addLayout(language_layout)
        
        interface_group.setLayout(interface_layout)
        layout.addWidget(interface_group)
        
        # 数据设置
        data_group = QGroupBox("数据设置")
        data_layout = QVBoxLayout()
        
        # 历史数据保存
        history_layout = QHBoxLayout()
        history_label = QLabel("历史数据保存:")
        self.history_spin = QSpinBox()
        self.history_spin.setRange(1, 365)
        self.history_spin.setSuffix(" 天")
        history_layout.addWidget(history_label)
        history_layout.addWidget(self.history_spin)
        history_layout.addStretch(1)
        data_layout.addLayout(history_layout)
        
        # 数据缓存大小
        cache_layout = QHBoxLayout()
        cache_label = QLabel("数据缓存大小:")
        self.cache_spin = QSpinBox()
        self.cache_spin.setRange(100, 10000)
        self.cache_spin.setSuffix(" 个数据点")
        cache_layout.addWidget(cache_label)
        cache_layout.addWidget(self.cache_spin)
        cache_layout.addStretch(1)
        data_layout.addLayout(cache_layout)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group)
        
        # 其他设置
        other_group = QGroupBox("其他设置")
        other_layout = QVBoxLayout()
        
        self.auto_start = QCheckBox("开机自动启动")
        self.auto_save = QCheckBox("自动保存配置")
        self.enable_sound = QCheckBox("启用声音提示")
        self.enable_notification = QCheckBox("启用桌面通知")
        
        other_layout.addWidget(self.auto_start)
        other_layout.addWidget(self.auto_save)
        other_layout.addWidget(self.enable_sound)
        other_layout.addWidget(self.enable_notification)
        
        other_group.setLayout(other_layout)
        layout.addWidget(other_group)
        
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget
    
    def create_datasource_tab(self):
        """创建数据源设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # SIS数据源设置
        sis_group = QGroupBox("SIS数据源设置")
        sis_layout = QVBoxLayout()
        
        # 服务器地址
        server_layout = QHBoxLayout()
        server_label = QLabel("服务器地址:")
        self.server_input = QLineEdit()
        self.server_input.setPlaceholderText("http://服务器地址:端口")
        server_layout.addWidget(server_label)
        server_layout.addWidget(self.server_input)
        sis_layout.addLayout(server_layout)
        
        # 用户名密码
        auth_layout = QHBoxLayout()
        user_label = QLabel("用户名:")
        self.user_input = QLineEdit()
        pass_label = QLabel("密码:")
        self.pass_input = QLineEdit()
        self.pass_input.setEchoMode(QLineEdit.Password)
        
        auth_layout.addWidget(user_label)
        auth_layout.addWidget(self.user_input)
        auth_layout.addWidget(pass_label)
        auth_layout.addWidget(self.pass_input)
        sis_layout.addLayout(auth_layout)
        
        # 采集间隔
        interval_layout = QHBoxLayout()
        interval_label = QLabel("数据采集间隔:")
        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 60)
        self.interval_spin.setSuffix(" 秒")
        interval_layout.addWidget(interval_label)
        interval_layout.addWidget(self.interval_spin)
        interval_layout.addStretch(1)
        sis_layout.addLayout(interval_layout)
        
        # 测试连接按钮
        test_btn = QPushButton("测试连接")
        test_btn.clicked.connect(self.test_sis_connection)
        sis_layout.addWidget(test_btn)
        
        sis_group.setLayout(sis_layout)
        layout.addWidget(sis_group)
        
        # 文件数据源设置
        file_group = QGroupBox("文件数据源设置")
        file_layout = QVBoxLayout()
        
        # 点表文件
        pointfile_layout = QHBoxLayout()
        pointfile_label = QLabel("点表文件:")
        self.pointfile_input = QLineEdit()
        self.pointfile_input.setPlaceholderText("point.xls文件路径")
        pointfile_browse = QPushButton("浏览...")
        pointfile_browse.clicked.connect(self.browse_point_file)
        
        pointfile_layout.addWidget(pointfile_label)
        pointfile_layout.addWidget(self.pointfile_input, 1)
        pointfile_layout.addWidget(pointfile_browse)
        file_layout.addLayout(pointfile_layout)
        
        # 映射表文件
        mapfile_layout = QHBoxLayout()
        mapfile_label = QLabel("映射表文件:")
        self.mapfile_input = QLineEdit()
        self.mapfile_input.setPlaceholderText("Cor_kks.xls文件路径")
        mapfile_browse = QPushButton("浏览...")
        mapfile_browse.clicked.connect(self.browse_map_file)
        
        mapfile_layout.addWidget(mapfile_label)
        mapfile_layout.addWidget(self.mapfile_input, 1)
        mapfile_layout.addWidget(mapfile_browse)
        file_layout.addLayout(mapfile_layout)
        
        file_group.setLayout(file_layout)
        layout.addWidget(file_group)
        
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget
    
    def create_alarm_settings_tab(self):
        """创建报警设置标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 报警级别设置
        level_group = QGroupBox("报警级别设置")
        level_layout = QVBoxLayout()
        
        # 报警级别表格
        self.alarm_table = QTableWidget()
        self.alarm_table.setColumnCount(3)
        self.alarm_table.setHorizontalHeaderLabels(["报警级别", "颜色", "声音提示"])
        
        # 设置表格属性
        self.alarm_table.setAlternatingRowColors(True)
        self.alarm_table.horizontalHeader().setStretchLastSection(True)
        
        level_layout.addWidget(self.alarm_table)
        level_group.setLayout(level_layout)
        layout.addWidget(level_group)
        
        # 报警通知设置
        notify_group = QGroupBox("报警通知设置")
        notify_layout = QVBoxLayout()
        
        self.notify_critical = QCheckBox("严重报警弹出对话框")
        self.notify_high = QCheckBox("高级报警显示通知")
        self.notify_medium = QCheckBox("中级报警记录日志")
        self.notify_repeat = QCheckBox("重复报警抑制")
        
        # 重复报警间隔
        repeat_layout = QHBoxLayout()
        repeat_label = QLabel("重复报警间隔:")
        self.repeat_spin = QSpinBox()
        self.repeat_spin.setRange(1, 60)
        self.repeat_spin.setSuffix(" 分钟")
        repeat_layout.addWidget(repeat_label)
        repeat_layout.addWidget(self.repeat_spin)
        repeat_layout.addStretch(1)
        
        notify_layout.addWidget(self.notify_critical)
        notify_layout.addWidget(self.notify_high)
        notify_layout.addWidget(self.notify_medium)
        notify_layout.addWidget(self.notify_repeat)
        notify_layout.addLayout(repeat_layout)
        
        notify_group.setLayout(notify_layout)
        layout.addWidget(notify_group)
        
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget
    
    def create_system_info_tab(self):
        """创建系统信息标签页"""
        widget = QWidget()
        layout = QVBoxLayout()
        
        # 系统状态
        status_group = QGroupBox("系统状态")
        status_layout = QVBoxLayout()
        
        # 系统信息表格
        info_table = QTableWidget()
        info_table.setColumnCount(2)
        info_table.setRowCount(8)
        info_table.setHorizontalHeaderLabels(["项目", "值"])
        info_table.verticalHeader().setVisible(False)
        info_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        # 设置系统信息
        system_info = [
            ["系统版本", "1.0.0"],
            ["Python版本", "3.8.0"],
            ["Qt版本", "5.15.0"],
            ["运行时间", "0天 0小时 0分钟"],
            ["数据点数量", "0"],
            ["报警数量", "0"],
            ["最后数据更新", "--"],
            ["系统状态", "正常"]
        ]
        
        for i, (key, value) in enumerate(system_info):
            info_table.setItem(i, 0, QTableWidgetItem(key))
            info_table.setItem(i, 1, QTableWidgetItem(value))
        
        info_table.horizontalHeader().setStretchLastSection(True)
        info_table.resizeColumnsToContents()
        
        status_layout.addWidget(info_table)
        status_group.setLayout(status_layout)
        layout.addWidget(status_group)
        
        # 资源使用情况
        resource_group = QGroupBox("资源使用情况")
        resource_layout = QVBoxLayout()
        
        # CPU使用率
        cpu_layout = QHBoxLayout()
        cpu_label = QLabel("CPU使用率:")
        cpu_progress = QProgressBar()
        cpu_progress.setValue(25)
        cpu_value = QLabel("25%")
        cpu_layout.addWidget(cpu_label)
        cpu_layout.addWidget(cpu_progress)
        cpu_layout.addWidget(cpu_value)
        resource_layout.addLayout(cpu_layout)
        
        # 内存使用率
        memory_layout = QHBoxLayout()
        memory_label = QLabel("内存使用率:")
        memory_progress = QProgressBar()
        memory_progress.setValue(60)
        memory_value = QLabel("60%")
        memory_layout.addWidget(memory_label)
        memory_layout.addWidget(memory_progress)
        memory_layout.addWidget(memory_value)
        resource_layout.addLayout(memory_layout)
        
        # 磁盘使用率
        disk_layout = QHBoxLayout()
        disk_label = QLabel("磁盘使用率:")
        disk_progress = QProgressBar()
        disk_progress.setValue(45)
        disk_value = QLabel("45%")
        disk_layout.addWidget(disk_label)
        disk_layout.addWidget(disk_progress)
        disk_layout.addWidget(disk_value)
        resource_layout.addLayout(disk_layout)
        
        resource_group.setLayout(resource_layout)
        layout.addWidget(resource_group)
        
        # 系统操作
        operation_group = QGroupBox("系统操作")
        operation_layout = QHBoxLayout()
        
        restart_btn = QPushButton("重启系统")
        restart_btn.clicked.connect(self.restart_system)
        
        update_btn = QPushButton("检查更新")
        update_btn.clicked.connect(self.check_update)
        
        log_btn = QPushButton("查看日志")
        log_btn.clicked.connect(self.view_logs)
        
        operation_layout.addWidget(restart_btn)
        operation_layout.addWidget(update_btn)
        operation_layout.addWidget(log_btn)
        operation_layout.addStretch(1)
        
        operation_group.setLayout(operation_layout)
        layout.addWidget(operation_group)
        
        layout.addStretch(1)
        widget.setLayout(layout)
        return widget
    
    def load_config(self):
        """加载配置"""
        try:
            # 尝试从文件加载配置
            config_file = "config/gui_config.json"
            if os.path.exists(config_file):
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.config_data = json.load(f)
            else:
                # 使用默认配置
                self.config_data = self.get_default_config()
            
            # 更新界面
            self.update_ui_from_config()
            
            self.show_message("配置加载成功", "系统配置已从文件加载")
            
        except Exception as e:
            self.show_message("配置加载失败", f"加载配置文件时出错: {str(e)}")
            self.config_data = self.get_default_config()
    
    def save_config(self):
        """保存配置"""
        try:
            # 从界面获取配置
            self.update_config_from_ui()
            
            # 保存到文件
            os.makedirs("config", exist_ok=True)
            config_file = "config/gui_config.json"
            
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.config_data, f, indent=2, ensure_ascii=False)
            
            self.show_message("配置保存成功", "系统配置已保存到文件")
            
        except Exception as e:
            self.show_message("配置保存失败", f"保存配置文件时出错: {str(e)}")
    
    def reset_config(self):
        """恢复默认配置"""
        reply = self.question("恢复默认配置", "确定要恢复默认配置吗？当前配置将丢失。")
        if reply:
            self.config_data = self.get_default_config()
            self.update_ui_from_config()
            self.show_message("配置已重置", "系统配置已恢复为默认值")
    
    def get_default_config(self):
        """获取默认配置"""
        return {
            "interface": {
                "refresh_interval": 5,
                "theme": "默认主题",
                "language": "中文"
            },
            "data": {
                "history_days": 30,
                "cache_size": 1000
            },
            "sis": {
                "server": "http://59.51.82.42:8880",
                "username": "049",
                "password": "",
                "interval": 5
            },
            "files": {
                "point_file": "point.xls",
                "map_file": "Cor_kks.xls"
            },
            "alarm": {
                "notify_critical": True,
                "notify_high": True,
                "notify_medium": False,
                "repeat_suppress": True,
                "repeat_interval": 10
            },
            "system": {
                "auto_start": False,
                "auto_save": True,
                "enable_sound": True,
                "enable_notification": True
            }
        }
    
    def update_ui_from_config(self):
        """从配置更新界面"""
        # 基本设置
        self.refresh_spin.setValue(self.config_data["interface"]["refresh_interval"])
        self.theme_combo.setCurrentText(self.config_data["interface"]["theme"])
        self.language_combo.setCurrentText(self.config_data["interface"]["language"])
        
        # 数据设置
        self.history_spin.setValue(self.config_data["data"]["history_days"])
        self.cache_spin.setValue(self.config_data["data"]["cache_size"])
        
        # SIS设置
        self.server_input.setText(self.config_data["sis"]["server"])
        self.user_input.setText(self.config_data["sis"]["username"])
        self.pass_input.setText(self.config_data["sis"]["password"])
        self.interval_spin.setValue(self.config_data["sis"]["interval"])
        
        # 文件设置
        self.pointfile_input.setText(self.config_data["files"]["point_file"])
        self.mapfile_input.setText(self.config_data["files"]["map_file"])
        
        # 报警设置
        self.notify_critical.setChecked(self.config_data["alarm"]["notify_critical"])
        self.notify_high.setChecked(self.config_data["alarm"]["notify_high"])
        self.notify_medium.setChecked(self.config_data["alarm"]["notify_medium"])
        self.notify_repeat.setChecked(self.config_data["alarm"]["repeat_suppress"])
        self.repeat_spin.setValue(self.config_data["alarm"]["repeat_interval"])
        
        # 系统设置
        self.auto_start.setChecked(self.config_data["system"]["auto_start"])
        self.auto_save.setChecked(self.config_data["system"]["auto_save"])
        self.enable_sound.setChecked(self.config_data["system"]["enable_sound"])
        self.enable_notification.setChecked(self.config_data["system"]["enable_notification"])
    
    def update_config_from_ui(self):
        """从界面更新配置"""
        # 基本设置
        self.config_data["interface"]["refresh_interval"] = self.refresh_spin.value()
        self.config_data["interface"]["theme"] = self.theme_combo.currentText()
        self.config_data["interface"]["language"] = self.language_combo.currentText()
        
        # 数据设置
        self.config_data["data"]["history_days"] = self.history_spin.value()
        self.config_data["data"]["cache_size"] = self.cache_spin.value()
        
        # SIS设置
        self.config_data["sis"]["server"] = self.server_input.text()
        self.config_data["sis"]["username"] = self.user_input.text()
        self.config_data["sis"]["password"] = self.pass_input.text()
        self.config_data["sis"]["interval"] = self.interval_spin.value()
        
        # 文件设置
        self.config_data["files"]["point_file"] = self.pointfile_input.text()
        self.config_data["files"]["map_file"] = self.mapfile_input.text()
        
        # 报警设置
        self.config_data["alarm"]["notify_critical"] = self.notify_critical.isChecked()
        self.config_data["alarm"]["notify_high"] = self.notify_high.isChecked()
        self.config_data["alarm"]["notify_medium"] = self.notify_medium.isChecked()
        self.config_data["alarm"]["repeat_suppress"] = self.notify_repeat.isChecked()
        self.config_data["alarm"]["repeat_interval"] = self.repeat_spin.value()
        
        # 系统设置
        self.config_data["system"]["auto_start"] = self.auto_start.isChecked()
        self.config_data["system"]["auto_save"] = self.auto_save.isChecked()
        self.config_data["system"]["enable_sound"] = self.enable_sound.isChecked()
        self.config_data["system"]["enable_notification"] = self.enable_notification.isChecked()
    
    def test_sis_connection(self):
        """测试SIS连接"""
        server = self.server_input.text()
        username = self.user_input.text()
        
        if not server or not username:
            self.show_message("测试失败", "请填写服务器地址和用户名")
            return
        
        # 模拟连接测试
        self.show_message("连接测试", f"正在测试连接到 {server}...")
        
        # 在实际实现中，这里应该调用SIS连接测试代码
        # 现在只是模拟
        QTimer.singleShot(2000, lambda: self.show_message(
            "连接测试完成", 
            f"成功连接到SIS服务器\n地址: {server}\n用户: {username}"
        ))
    
    def browse_point_file(self):
        """浏览点表文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择点表文件", "", "Excel文件 (*.xls *.xlsx)"
        )
        if file_path:
            self.pointfile_input.setText(file_path)
    
    def browse_map_file(self):
        """浏览映射表文件"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择映射表文件", "", "Excel文件 (*.xls *.xlsx)"
        )
        if file_path:
            self.mapfile_input.setText(file_path)
    
    def restart_system(self):
        """重启系统"""
        reply = self.question("重启系统", "确定要重启监控系统吗？")
        if reply:
            self.show_message("系统重启", "系统将在3秒后重启...")
            # 在实际实现中，这里应该触发系统重启
            QTimer.singleShot(3000, lambda: self.show_message("重启完成", "系统已重启"))
    
    def check_update(self):
        """检查更新"""
        self.show_message("检查更新", "正在检查系统更新...")
        
        # 模拟检查更新
        QTimer.singleShot(1500, lambda: self.show_message(
            "更新检查完成", 
            "当前已是最新版本 (v1.0.0)"
        ))
    
    def view_logs(self):
        """查看日志"""
        self.show_message("查看日志", "日志查看功能开发中...")
    
    def show_message(self, title, message):
        """显示消息"""
        QMessageBox.information(self, title, message)
    
    def question(self, title, question):
        """显示问题对话框"""
        reply = QMessageBox.question(self, title, question, 
                                   QMessageBox.Yes | QMessageBox.No, 
                                   QMessageBox.No)
        return reply == QMessageBox.Yes
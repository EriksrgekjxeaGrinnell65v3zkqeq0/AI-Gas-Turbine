class StyleManager:
    """样式管理工具"""
    
    def __init__(self):
        self.styles = {}
        self.load_styles()
    
    def load_styles(self):
        """加载样式"""
        self.styles = {
            "default": self.get_default_style(),
            "dark": self.get_dark_style(),
            "blue": self.get_blue_style(),
            "green": self.get_green_style()
        }
    
    def get_style(self, style_name):
        """获取样式"""
        return self.styles.get(style_name, self.styles["default"])
    
    def get_default_style(self):
        """获取默认样式"""
        return """
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
        QPushButton {
            background-color: #4CAF50;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #45a049;
        }
        QPushButton:pressed {
            background-color: #3d8b40;
        }
        QLineEdit, QComboBox, QSpinBox {
            padding: 6px;
            border: 1px solid #ccc;
            border-radius: 4px;
        }
        QProgressBar {
            border: 1px solid grey;
            border-radius: 5px;
            text-align: center;
        }
        QProgressBar::chunk {
            background-color: #4CAF50;
            border-radius: 4px;
        }
        QTextEdit {
            border: 1px solid #ccc;
            border-radius: 4px;
            padding: 4px;
        }
        """
    
    def get_dark_style(self):
        """获取深色样式"""
        return """
        QMainWindow {
            background-color: #2b2b2b;
            color: #ffffff;
            font-family: "Microsoft YaHei", "SimHei", sans-serif;
        }
        QTabWidget::pane {
            border: 1px solid #555555;
            background-color: #3c3c3c;
            border-radius: 4px;
        }
        QTabBar::tab {
            background-color: #555555;
            color: #ffffff;
            padding: 8px 16px;
            margin-right: 2px;
            border-top-left-radius: 4px;
            border-top-right-radius: 4px;
        }
        QTabBar::tab:selected {
            background-color: #007acc;
            color: white;
        }
        QTabBar::tab:hover {
            background-color: #666666;
        }
        QGroupBox {
            font-weight: bold;
            border: 1px solid #555555;
            border-radius: 4px;
            margin-top: 10px;
            padding-top: 10px;
            color: #ffffff;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #ffffff;
        }
        QTableWidget {
            gridline-color: #555555;
            selection-background-color: #007acc;
            background-color: #3c3c3c;
            color: #ffffff;
            alternate-background-color: #454545;
        }
        QTableWidget::item {
            padding: 5px;
            color: #ffffff;
        }
        QHeaderView::section {
            background-color: #555555;
            padding: 4px;
            border: 1px solid #555555;
            font-weight: bold;
            color: #ffffff;
        }
        QPushButton {
            background-color: #007acc;
            border: none;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QPushButton:hover {
            background-color: #005a9e;
        }
        QPushButton:pressed {
            background-color: #004578;
        }
        QLineEdit, QComboBox, QSpinBox {
            padding: 6px;
            border: 1px solid #555555;
            border-radius: 4px;
            background-color: #3c3c3c;
            color: #ffffff;
        }
        QProgressBar {
            border: 1px solid #555555;
            border-radius: 5px;
            text-align: center;
            color: #ffffff;
        }
        QProgressBar::chunk {
            background-color: #007acc;
            border-radius: 4px;
        }
        QTextEdit {
            border: 1px solid #555555;
            border-radius: 4px;
            padding: 4px;
            background-color: #3c3c3c;
            color: #ffffff;
        }
        """
    
    def get_blue_style(self):
        """获取蓝色样式"""
        style = self.get_default_style()
        # 替换颜色为蓝色系
        style = style.replace("#4CAF50", "#2196F3")  # 绿色 -> 蓝色
        style = style.replace("#45a049", "#1976D2")
        style = style.replace("#3d8b40", "#0D47A1")
        return style
    
    def get_green_style(self):
        """获取绿色样式"""
        # 默认样式已经是绿色系，直接返回
        return self.get_default_style()
"""
项目路径管理模块
统一管理所有文件路径，确保项目可移植性
"""

import os

class ProjectPaths:
    """项目路径管理类"""
    
    def __init__(self):
        # 项目根目录
        self.root = os.path.dirname(os.path.abspath(__file__))
        
        # 数据目录
        self.data_dir = os.path.join(self.root, "data")
        
        # 模型目录
        self.models_dir = os.path.join(self.root, "LimiX", "models")
        self.limix_model = os.path.join(self.models_dir, "LimiX-16M.ckpt")
        
        # 知识库目录
        self.knowledge_base = os.path.join(self.root, "knowledge_base")
        self.vector_db = os.path.join(self.root, "chroma_db")
        
        # 日志目录
        self.logs_dir = os.path.join(self.root, "logs")
        
        # 故障报告目录
        self.fault_reports_dir = os.path.join(self.root, "fault_reports")
        
        # 点表文件
        self.point_table = os.path.join(self.root, "point.xls")
    
    def create_directories(self):
        """创建必要的目录结构"""
        directories = [
            self.data_dir,
            self.models_dir,
            self.knowledge_base,
            self.vector_db,
            self.logs_dir,
            self.fault_reports_dir
        ]
        
        for directory in directories:
            os.makedirs(directory, exist_ok=True)
        
        print("项目目录结构已创建")
    
    def validate_paths(self):
        """验证关键路径是否存在"""
        required_paths = {
            "点表文件": self.point_table,
            "LimiX模型": self.limix_model
        }
        
        missing_paths = []
        for name, path in required_paths.items():
            if not os.path.exists(path):
                missing_paths.append((name, path))
        
        if missing_paths:
            print("警告: 以下关键文件缺失:")
            for name, path in missing_paths:
                print(f"  {name}: {path}")
            return False
        else:
            print("所有关键文件路径验证通过")
            return True

# 全局路径管理实例
project_paths = ProjectPaths()
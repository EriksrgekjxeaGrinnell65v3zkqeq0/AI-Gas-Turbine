import os
from datetime import datetime

# 系统配置
class Config:
    # 端口配置
    SIS_RECEIVE_PORT = 9001
    RESULT_SEND_PORT = 9002
    FAULT_SEND_PORT = 9003
    DEEPSEEK_SEND_PORT = 9004
    HOST = 'localhost'
    
    # 获取项目根目录
    PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

    # 模型路径
    MODEL_PATH = os.path.join(PROJECT_ROOT, "LimiX", "models", "LimiX-16M.ckpt")
    
    # DeepSeek配置
    DEEPSEEK_HOST = 'localhost'
    DEEPSEEK_PORT = 11434
    DEEPSEEK_MODEL = 'deepseek-r1:14b'
    
    # RAG配置
    RAG_KNOWLEDGE_BASE = "knowledge_base"
    RAG_VECTOR_DB = "chroma_db"
    RAG_EMBEDDING_MODEL = "nomic-embed-text"
    
    # 数据存储
    DATA_BUFFER_SIZE = 1000
    MAX_HISTORY_POINTS = 500
    
    # 分析配置
    ANALYSIS_WINDOW = 50
    TREND_STEPS = 5
    PREDICTION_MINUTES = 3
    
    # 日志配置
    LOG_DIR = "logs"
    LOG_RETENTION_HOURS = 24
    
    # GUI配置 - 新增
    GUI_CONFIG = {
        'refresh_interval': 5000,           # 界面刷新间隔(毫秒)
        'max_display_points': 50,           # 最大显示点数
        'theme': 'default',                 # 界面主题
        'window_size': [1400, 900],         # 窗口默认尺寸
        'data_history_days': 30,            # 历史数据保存天数
        'chart_update_frequency': 2000,     # 图表更新频率(毫秒)
        'auto_save_interval': 60000,        # 自动保存间隔(毫秒)
        'max_alarm_history': 100,           # 最大报警历史记录数
    }
    
    # 真实SIS配置（仅支持真实SIS数据源）
    REAL_SIS_CONFIG = {
        'base_url': 'http://59.51.82.42:8880',
        'username': '049', 
        'password': 'Hdw19951125',
        'monitor_interval': 5  # 监控间隔5秒
    }
    
    # 报警等级
    ALARM_LEVELS = {
        'LLL': {'level': 'CRITICAL', 'priority': 1},
        'HHH': {'level': 'CRITICAL', 'priority': 1},
        'LL': {'level': 'HIGH', 'priority': 2},
        'HH': {'level': 'HIGH', 'priority': 2},
        'L': {'level': 'MEDIUM', 'priority': 3},
        'H': {'level': 'MEDIUM', 'priority': 3}
    }
    
    @staticmethod
    def get_current_log_filename():
        """获取当前日志文件名"""
        if not os.path.exists(Config.LOG_DIR):
            os.makedirs(Config.LOG_DIR)
        current_date = datetime.now().strftime("%Y%m%d")
        return os.path.join(Config.LOG_DIR, f"monitoring_log_{current_date}.log")
    
    @staticmethod
    def cleanup_old_logs():
        """清理过期日志"""
        try:
            if not os.path.exists(Config.LOG_DIR):
                return
            
            current_time = datetime.now()
            for filename in os.listdir(Config.LOG_DIR):
                if filename.startswith("monitoring_log_") and filename.endswith(".log"):
                    filepath = os.path.join(Config.LOG_DIR, filename)
                    file_time = datetime.fromtimestamp(os.path.getctime(filepath))
                    
                    if (current_time - file_time).total_seconds() > Config.LOG_RETENTION_HOURS * 3600:
                        os.remove(filepath)
                        print(f"已删除过期日志文件: {filename}")
        except Exception as e:
            print(f"清理日志文件时出错: {e}")

config = Config()
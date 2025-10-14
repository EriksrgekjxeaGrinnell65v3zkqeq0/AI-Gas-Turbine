import threading
from datetime import datetime, timedelta
from collections import deque

class DataManager:
    """数据管理器"""
    
    def __init__(self):
        self.realtime_data = {}
        self.historical_data = {}  # KKS -> deque of (timestamp, value)
        self.data_lock = threading.Lock()
        self.max_history_points = 1000
        
        # 初始化历史数据结构
        self.init_historical_storage()
    
    def init_historical_storage(self):
        """初始化历史数据存储"""
        # 这里可以加载已有的历史数据
        pass
    
    def update_realtime_data(self, data_points):
        """更新实时数据"""
        with self.data_lock:
            self.realtime_data = data_points.copy()
            
            # 更新历史数据
            current_time = datetime.now()
            for kks, value in data_points.items():
                if kks not in self.historical_data:
                    self.historical_data[kks] = deque(maxlen=self.max_history_points)
                
                self.historical_data[kks].append((current_time, value))
    
    def get_current_data(self):
        """获取当前数据"""
        with self.data_lock:
            return self.realtime_data.copy()
    
    def get_historical_data(self, kks, minutes=30):
        """获取历史数据"""
        with self.data_lock:
            if kks not in self.historical_data:
                return []
            
            cutoff_time = datetime.now() - timedelta(minutes=minutes)
            return [(t, v) for t, v in self.historical_data[kks] if t >= cutoff_time]
    
    def get_trend_data(self, kks, points=50):
        """获取趋势数据（固定点数）"""
        with self.data_lock:
            if kks not in self.historical_data:
                return []
            
            # 返回最近的点
            return list(self.historical_data[kks])[-points:]
    
    def get_all_kks(self):
        """获取所有KKS代码"""
        with self.data_lock:
            return list(self.realtime_data.keys())
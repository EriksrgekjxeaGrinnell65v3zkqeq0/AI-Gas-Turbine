from datetime import datetime
from collections import defaultdict

class AlarmManager:
    """报警管理器"""
    
    def __init__(self):
        self.active_alarms = []
        self.alarm_history = []
        self.alarm_stats = defaultdict(int)
        
    def update_alarms(self, analysis_result):
        """更新报警信息"""
        # 清空当前报警统计
        self.alarm_stats.clear()
        
        # 处理严重报警
        for alarm_msg in analysis_result.get('alarms', []):
            self.add_alarm('critical', alarm_msg)
        
        # 处理警告信息
        for warning_msg in analysis_result.get('warnings', []):
            self.add_alarm('high', warning_msg)
        
        # 处理故障点
        for fault_point in analysis_result.get('fault_points', []):
            alarm_level = fault_point.get('alarm_level', 'medium').lower()
            alarm_msg = f"{fault_point['name']}: {fault_point['status_description']}"
            self.add_alarm(alarm_level, alarm_msg)
    
    def add_alarm(self, level, message):
        """添加报警"""
        alarm = {
            'timestamp': datetime.now(),
            'level': level,
            'message': message,
            'acknowledged': False
        }
        
        self.active_alarms.append(alarm)
        self.alarm_history.append(alarm)
        self.alarm_stats[level] += 1
        
        # 限制历史记录数量
        if len(self.alarm_history) > 1000:
            self.alarm_history = self.alarm_history[-1000:]
    
    def get_alarm_stats(self):
        """获取报警统计"""
        return self.alarm_stats.copy()
    
    def get_active_alarms(self):
        """获取活动报警"""
        return [alarm for alarm in self.active_alarms if not alarm['acknowledged']]
    
    def acknowledge_alarm(self, alarm_index):
        """确认报警"""
        if 0 <= alarm_index < len(self.active_alarms):
            self.active_alarms[alarm_index]['acknowledged'] = True
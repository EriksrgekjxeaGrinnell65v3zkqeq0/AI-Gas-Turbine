import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np
from datetime import datetime, timedelta

class ChartRenderer:
    """图表渲染工具"""
    
    def __init__(self):
        self.figure = None
        self.ax = None
        self.canvas = None
        
    def create_figure(self, width=10, height=6, dpi=100):
        """创建图表"""
        self.figure = Figure(figsize=(width, height), dpi=dpi)
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        return self.canvas
    
    def render_trend_chart(self, times, values, title="趋势分析", ylabel="数值", 
                          show_trend_line=True, show_prediction=False):
        """渲染趋势图表"""
        if not self.ax:
            return None
        
        self.ax.clear()
        
        # 绘制实际值
        self.ax.plot(times, values, 'b-', linewidth=2, label='实际值', alpha=0.8)
        self.ax.scatter(times, values, color='blue', s=20, alpha=0.6)
        
        # 绘制趋势线
        if show_trend_line and len(values) > 1:
            trend_line = self.calculate_trend_line(times, values)
            if trend_line:
                trend_times, trend_values = trend_line
                self.ax.plot(trend_times, trend_values, 'r--', linewidth=1.5, 
                            label='趋势线', alpha=0.7)
        
        # 绘制预测
        if show_prediction and len(values) > 5:
            prediction = self.calculate_prediction(values)
            if prediction:
                future_times = self.generate_future_times(times, len(prediction))
                self.ax.plot(future_times, prediction, 'g:', linewidth=1.5, 
                            label='预测', alpha=0.7)
        
        # 设置图表属性
        self.ax.set_xlabel('时间')
        self.ax.set_ylabel(ylabel)
        self.ax.set_title(title)
        self.ax.legend()
        self.ax.grid(True, linestyle='--', alpha=0.7)
        
        # 格式化时间显示
        self.format_time_axis(times)
        
        # 自动调整布局
        self.figure.tight_layout()
        
        return self.canvas
    
    def calculate_trend_line(self, times, values):
        """计算趋势线"""
        try:
            # 将时间转换为数值（从第一个时间点开始的秒数）
            time_nums = [(t - times[0]).total_seconds() for t in times]
            
            # 线性拟合
            z = np.polyfit(time_nums, values, 1)
            trend_line = np.poly1d(z)
            
            # 生成趋势线数据
            trend_times = [times[0] + timedelta(seconds=s) for s in 
                          np.linspace(0, time_nums[-1], 100)]
            trend_values = trend_line(np.linspace(0, time_nums[-1], 100))
            
            return trend_times, trend_values
        except:
            return None
    
    def calculate_prediction(self, values, steps=10):
        """计算预测值"""
        try:
            # 简单的移动平均预测
            if len(values) < 3:
                return None
            
            # 使用最后几个点的趋势进行预测
            last_values = values[-5:]
            trend = np.polyfit(range(len(last_values)), last_values, 1)
            prediction_line = np.poly1d(trend)
            
            # 生成预测值
            future_indices = range(len(last_values), len(last_values) + steps)
            prediction = prediction_line(future_indices)
            
            return prediction
        except:
            return None
    
    def generate_future_times(self, times, steps, interval_seconds=5):
        """生成未来时间点"""
        if not times:
            return []
        
        last_time = times[-1]
        future_times = [last_time + timedelta(seconds=interval_seconds * (i + 1)) 
                       for i in range(steps)]
        
        return future_times
    
    def format_time_axis(self, times):
        """格式化时间轴"""
        if not times:
            return
        
        time_span = (times[-1] - times[0]).total_seconds()
        
        if time_span > 86400:  # 超过1天显示日期
            self.ax.xaxis.set_major_formatter(plt.FuncFormatter(
                lambda x, _: (times[0] + timedelta(seconds=x)).strftime('%m/%d %H:%M')
            ))
        elif time_span > 3600:  # 超过1小时显示小时和分钟
            self.ax.xaxis.set_major_formatter(plt.FuncFormatter(
                lambda x, _: (times[0] + timedelta(seconds=x)).strftime('%H:%M')
            ))
        else:  # 1小时内显示分钟和秒
            self.ax.xaxis.set_major_formatter(plt.FuncFormatter(
                lambda x, _: (times[0] + timedelta(seconds=x)).strftime('%M:%S')
            ))
    
    def clear_chart(self):
        """清空图表"""
        if self.ax:
            self.ax.clear()
            self.ax.set_xlabel('时间')
            self.ax.set_ylabel('数值')
            self.ax.set_title('趋势分析')
            self.ax.grid(True, linestyle='--', alpha=0.7)
            
            if self.canvas:
                self.canvas.draw()
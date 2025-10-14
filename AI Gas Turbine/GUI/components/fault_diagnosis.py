from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QGroupBox, 
                           QTextEdit, QLabel, QTableWidget, QTableWidgetItem,
                           QSplitter)
from PyQt5.QtCore import Qt
from datetime import datetime

class FaultDiagnosis(QWidget):
    """故障诊断组件"""
    
    def __init__(self, data_manager):
        super().__init__()
        self.data_manager = data_manager
        self.deepseek_analysis_history = []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 创建分割器，使界面可以调整大小
        splitter = QSplitter(Qt.Vertical)
        
        # 实时故障诊断区域
        realtime_group = QGroupBox("实时故障诊断")
        realtime_layout = QVBoxLayout()
        
        self.realtime_diagnosis_text = QTextEdit()
        self.realtime_diagnosis_text.setReadOnly(True)
        self.realtime_diagnosis_text.setPlaceholderText("实时故障诊断信息将在这里显示...")
        realtime_layout.addWidget(self.realtime_diagnosis_text)
        
        realtime_group.setLayout(realtime_layout)
        splitter.addWidget(realtime_group)
        
        # DeepSeek分析区域
        deepseek_group = QGroupBox("DeepSeek智能分析")
        deepseek_layout = QVBoxLayout()
        
        self.deepseek_analysis_text = QTextEdit()
        self.deepseek_analysis_text.setReadOnly(True)
        self.deepseek_analysis_text.setPlaceholderText("DeepSeek分析结果将在这里显示...")
        deepseek_layout.addWidget(self.deepseek_analysis_text)
        
        deepseek_group.setLayout(deepseek_layout)
        splitter.addWidget(deepseek_group)
        
        # 设置分割器比例
        splitter.setSizes([300, 400])
        
        layout.addWidget(splitter)
        self.setLayout(layout)
    
    def update_diagnosis(self, analysis_data):
        """更新故障诊断"""
        diagnosis_text = ""
        
        # 添加时间戳
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        diagnosis_text += f"=== 分析时间: {current_time} ===\n\n"
        
        # 添加总体状态
        diagnosis_text += f"总体健康状态: {analysis_data.get('overall_health', '未知')}\n"
        diagnosis_text += f"风险等级: {analysis_data.get('risk_level', '未知')}\n"
        diagnosis_text += f"系统总结: {analysis_data.get('summary', '')}\n\n"
        
        # 添加报警信息
        if analysis_data.get('alarms'):
            diagnosis_text += "🚨 严重报警:\n"
            for alarm in analysis_data['alarms']:
                diagnosis_text += f"   • {alarm}\n"
            diagnosis_text += "\n"
        
        if analysis_data.get('warnings'):
            diagnosis_text += "⚠️ 警告信息:\n"
            for warning in analysis_data['warnings']:
                diagnosis_text += f"   • {warning}\n"
            diagnosis_text += "\n"
        
        # 添加故障点信息
        if analysis_data.get('fault_points'):
            diagnosis_text += "🔧 故障检测:\n"
            for fault in analysis_data['fault_points']:
                diagnosis_text += f"   • {fault['name']} ({fault['kks']}): {fault['current_value']} {fault.get('unit', '')}\n"
                diagnosis_text += f"     状态: {fault['status_description']}\n"
                if fault.get('anomaly_signals'):
                    diagnosis_text += f"     异常信号: {', '.join(fault['anomaly_signals'])}\n"
            diagnosis_text += "\n"
        
        # 添加预测报警
        if analysis_data.get('prediction_alarms'):
            diagnosis_text += "📊 预测报警:\n"
            for alarm in analysis_data['prediction_alarms']:
                diagnosis_text += f"   • {alarm['description']}\n"
        
        self.realtime_diagnosis_text.setText(diagnosis_text)
    
    def update_deepseek_analysis(self, data):
        """更新DeepSeek分析结果"""
        fault_point = data['fault_point']
        analysis_result = data['analysis_result']
        
        # 添加到历史记录
        self.deepseek_analysis_history.append(data)
        
        # 构建显示文本
        analysis_text = ""
        
        # 添加时间戳
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        analysis_text += f"=== DeepSeek分析报告 - {current_time} ===\n\n"
        
        # 添加故障点信息
        analysis_text += f"🔍 分析对象: {fault_point['name']} ({fault_point['kks']})\n"
        analysis_text += f"📊 当前数值: {fault_point['current_value']} {fault_point.get('unit', '')}\n"
        analysis_text += f"🚨 报警级别: {fault_point.get('alarm_level', '未知')}\n"
        analysis_text += f"📈 置信度: {analysis_result.get('confidence_score', 0):.2f}\n\n"
        
        # 添加专家分析
        analysis_text += "💡 专家分析:\n"
        analysis_text += analysis_result.get('expert_analysis', '暂无分析结果') + "\n\n"
        
        # 添加知识来源
        source_docs = analysis_result.get('source_documents', [])
        if source_docs:
            analysis_text += "📚 参考文档:\n"
            for i, doc in enumerate(source_docs, 1):
                source_name = doc.get('source', '未知文档')
                # 只显示文件名
                import os
                source_name = os.path.basename(source_name)
                analysis_text += f"   {i}. {source_name}\n"
        
        # 更新显示
        current_text = self.deepseek_analysis_text.toPlainText()
        if current_text:
            # 在现有文本前添加新分析
            updated_text = analysis_text + "\n" + "="*50 + "\n\n" + current_text
        else:
            updated_text = analysis_text
        
        self.deepseek_analysis_text.setText(updated_text)
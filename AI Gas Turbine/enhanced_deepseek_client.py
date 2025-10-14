import os
import socket
import json
import requests
from typing import Dict, Any, Optional
from config import config
import time
from rag_system import rag_system
from langchain_community.vectorstores import Chroma

class EnhancedDeepSeekClient:
    """DeepSeek客户端，集成RAG功能和支持相关性测点分析"""
    
    def __init__(self):
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.vector_db_path = os.path.join(self.project_root, "chroma_db")
        self.host = config.DEEPSEEK_HOST
        self.port = config.DEEPSEEK_PORT
        self.model = config.DEEPSEEK_MODEL
        self.is_ready = False
        self.rag_initialized = False
        self._initialize_rag_system()
    
    def _initialize_rag_system(self):
        """初始化RAG系统"""
        try:
            if not self.rag_initialized:
                # 检查向量数据库是否存在
                if os.path.exists(self.vector_db_path):
                    # 加载现有向量数据库
                    rag_system.vector_store = Chroma(
                        persist_directory=self.vector_db_path,
                        embedding_function=rag_system.embeddings
                    )
                    rag_system._create_qa_chain()
                    self.rag_initialized = True
                    print("RAG系统加载完成")
                else:
                    print("RAG向量数据库未找到，将使用基础分析模式")
                    print("请运行 python init_rag.py 初始化RAG系统")
                    
        except Exception as e:
            print(f"RAG系统初始化失败: {e}")
    
    def analyze_fault(self, fault_data: Dict) -> Optional[Dict]:
        """分析故障并返回处理建议"""
        # 如果服务未就绪，先检查状态
        if not self.is_ready:
            if not self._check_ollama_health():
                print("DeepSeek服务未就绪，跳过分析")
                return None
            self.is_ready = True
        
        try:
            # 先使用RAG系统分析
            rag_result = None
            if self.rag_initialized:
                rag_result = rag_system.analyze_fault_with_rag(fault_data)
                print(f"RAG分析完成，置信度: {rag_result['confidence_score']}")
            
            # 如果RAG置信度较低或需要补充，使用原始DeepSeek分析
            if not rag_result or rag_result['confidence_score'] < 0.3:
                print("RAG置信度较低，使用原始DeepSeek分析...")
                original_analysis = self._analyze_with_deepseek(fault_data)
                
                if rag_result:
                    # 合并结果
                    combined_analysis = f"{rag_result['expert_analysis']}\n\n补充分析:\n{original_analysis}"
                    rag_result['expert_analysis'] = combined_analysis
                else:
                    rag_result = {
                        "expert_analysis": original_analysis,
                        "source_documents": [],
                        "confidence_score": 0.0
                    }
            
            return rag_result
            
        except Exception as e:
            print(f"增强分析故障失败: {e}")
            return None
    
    def _analyze_with_deepseek(self, fault_data: Dict) -> Optional[str]:
        """使用原始DeepSeek分析"""
        prompt = self._create_prompt(fault_data)
        
        # 添加重试机制
        max_retries = 2
        for attempt in range(max_retries):
            response = self._send_to_deepseek(prompt)
            if response is not None:
                return response
            
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 10
                print(f"DeepSeek分析失败，{wait_time}秒后重试...")
                time.sleep(wait_time)
        
        return None
    
    def _check_ollama_health(self) -> bool:
        """检查Ollama服务健康状态"""
        try:
            url = f"http://{self.host}:{self.port}/api/tags"
            response = requests.get(url, timeout=10)
            if response.status_code == 200:
                print("DeepSeek服务状态正常")
                return True
            else:
                print(f"DeepSeek服务异常: {response.status_code}")
                return False
        except Exception as e:
            print(f"DeepSeek健康检查失败: {e}")
            return False
    
    def _create_prompt(self, fault_data: Dict) -> str:
        """创建提示词"""
        # 获取详细的阈值信息
        thresholds_info = self._get_detailed_threshold_info(fault_data)
        
        # 提示词，包含背景和要求
        prompt = f"""你是一位9F燃机电厂专家，请对以下故障进行分析并给出处理方式。请参考电厂运行规程、设备维护手册和专家知识库。

故障信息：
- 测点名称: {fault_data['name']}
- 测点描述: {fault_data['description']}
- 所属系统: {fault_data['system']}
- 故障时间: {fault_data['timestamp']}
- 当前数值: {fault_data['current_value']} {fault_data['unit']}
- 报警级别: {fault_data['alarm_level']}
- 异常信号: {', '.join(fault_data['anomaly_signals'])}
- 当前趋势: {fault_data['trend']}
- 预测趋势: {fault_data['predicted_trend']}
- 状态描述: {fault_data['status_description']}
{thresholds_info}

波动突变检测详情:
"""
        
        # 添加波动和突变的具体数据
        if fault_data.get('fluctuation_detected'):
            actual_fluct = fault_data.get('actual_fluctuation', 0)
            threshold_fluct = fault_data.get('fluctuation_range', 0)
            prompt += f"- 波动检测: 实际波动率 {actual_fluct:.2f} {fault_data['unit']}/s > 阈值 {threshold_fluct} {fault_data['unit']}/s\n"
        
        if fault_data.get('mutation_detected'):
            actual_mut = fault_data.get('actual_mutation', 0)
            threshold_mut = fault_data.get('mutation_range', 0)
            prompt += f"- 突变检测: 实际突变值 {actual_mut:.2f} {fault_data['unit']} > 阈值 {threshold_mut} {fault_data['unit']}\n"

        # 添加相关性测点信息
        if 'correlation_points' in fault_data:
            correlation_data = fault_data['correlation_points']
            
            if correlation_data['positive']:
                prompt += "\n正相关测点状态:\n"
                for corr_point in correlation_data['positive']:
                    analysis = corr_point.get('analysis', {})
                    prompt += f"- {corr_point['name']}: {corr_point['current_value']} {corr_point['unit']} "
                    prompt += f"(趋势: {analysis.get('trend', '未知')}, "
                    prompt += f"报警: {analysis.get('alarm_level', '正常')}, "
                    prompt += f"异常概率: {analysis.get('anomaly_probability', 0):.3f})\n"
            
            if correlation_data['negative']:
                prompt += "\n负相关测点状态:\n"
                for corr_point in correlation_data['negative']:
                    analysis = corr_point.get('analysis', {})
                    prompt += f"- {corr_point['name']}: {corr_point['current_value']} {corr_point['unit']} "
                    prompt += f"(趋势: {analysis.get('trend', '未知')}, "
                    prompt += f"报警: {analysis.get('alarm_level', '正常')}, "
                    prompt += f"异常概率: {analysis.get('anomaly_probability', 0):.3f})\n"

        prompt += "\n故障测点近期数据（最近36个数据点，每5秒一个点，共3分钟）:"
        
        # 显示最近36个数据点（3分钟数据，每5秒一个点）
        recent_data = fault_data['recent_history'][-36:] if fault_data['recent_history'] else []
        for i, history_point in enumerate(recent_data):
            time_str = history_point['timestamp'][11:19]  # 只显示时间部分
            prompt += f"\n- {time_str}: {history_point['value']} {fault_data['unit']}"
        
        prompt += """

请按照以下结构进行分析：
1. 故障类型识别和影响范围评估
2. 可能原因分析（考虑相关性测点的状态）
3. 立即处理措施和操作步骤
4. 后续监控重点（包括相关测点）
5. 预防性维护建议

请特别关注相关性测点的状态变化，正相关测点通常会同向变化，负相关测点通常反向变化。
请基于9F级燃气轮机的特性和电厂运行经验提供专业建议。请确保分析基于提供的运行数据，并参考电厂运行规程和设备维护手册。"""

        return prompt
    
    def _get_detailed_threshold_info(self, fault_data: Dict) -> str:
        """获取详细的阈值信息"""
        thresholds_info = "报警阈值信息:\n"
        
        if 'thresholds' in fault_data:
            thresholds = fault_data['thresholds']
            if thresholds.get('HHH'):
                thresholds_info += f"- HHH报警值: {thresholds['HHH']} {fault_data['unit']}\n"
            if thresholds.get('HH'):
                thresholds_info += f"- HH报警值: {thresholds['HH']} {fault_data['unit']}\n"
            if thresholds.get('H'):
                thresholds_info += f"- H报警值: {thresholds['H']} {fault_data['unit']}\n"
            if thresholds.get('L'):
                thresholds_info += f"- L报警值: {thresholds['L']} {fault_data['unit']}\n"
            if thresholds.get('LL'):
                thresholds_info += f"- LL报警值: {thresholds['LL']} {fault_data['unit']}\n"
            if thresholds.get('LLL'):
                thresholds_info += f"- LLL报警值: {thresholds['LLL']} {fault_data['unit']}\n"
            if thresholds.get('lower_limit'):
                thresholds_info += f"- 下限: {thresholds['lower_limit']} {fault_data['unit']}\n"
            if thresholds.get('upper_limit'):
                thresholds_info += f"- 上限: {thresholds['upper_limit']} {fault_data['unit']}\n"
        else:
            thresholds_info += "- 阈值信息暂不可用\n"
        
        return thresholds_info
    
    def _send_to_deepseek(self, prompt: str) -> Optional[str]:
        """发送请求到DeepSeek"""
        try:
            url = f"http://{self.host}:{self.port}/api/generate"
            
            # 进一步优化的请求参数
            payload = {
                "model": self.model,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.3,
                    "num_predict": 800,  # 增加预测长度以处理相关性分析
                    "top_k": 20,
                    "top_p": 0.85,
                    "repeat_penalty": 1.1
                }
            }
            
            # 分阶段超时：连接15秒，读取120秒
            response = requests.post(url, json=payload, timeout=(15, 120))
            
            if response.status_code != 200:
                print(f"DeepSeek API返回错误: {response.status_code}")
                return None
                
            result = response.json()
            response_text = result.get("response", "").strip()
            
            if not response_text:
                print("DeepSeek返回空响应")
                return None
                
            return response_text
            
        except requests.exceptions.Timeout:
            print("DeepSeek API调用超时")
            return None
        except requests.exceptions.ConnectionError:
            print("无法连接到Ollama服务")
            self.is_ready = False
            return None
        except Exception as e:
            print(f"DeepSeek API调用失败: {e}")
            return None
    
    def send_analysis_result(self, fault_info: Dict, analysis_result: Dict):
        """发送分析结果到9004端口"""
        try:
            # 创建包含故障信息和分析结果的完整报告
            full_report = self._create_full_report(fault_info, analysis_result)
            
            # 限制报告长度，避免socket问题
            if len(full_report) > 6000:  # 增加长度限制以容纳相关性信息
                full_report = full_report[:6000] + "...\n[内容过长已截断]"
                
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(10)
                sock.connect((config.HOST, config.DEEPSEEK_SEND_PORT))
                message = full_report.encode('utf-8')
                sock.sendall(message)
                print("DeepSeek完整分析报告已发送")
        except socket.timeout:
            print("发送DeepSeek分析报告超时")
        except Exception as e:
            print(f"发送DeepSeek分析报告失败: {e}")
    
    def _create_full_report(self, fault_info: Dict, analysis_result: Dict) -> str:
        """创建包含故障信息和AI分析的完整报告"""
        # 获取详细的阈值信息
        thresholds_info = self._get_formatted_thresholds(fault_info)
        
        # 格式化历史数据 - 显示36个点（3分钟数据）
        history_data = ""
        recent_data = fault_info['recent_history'][-36:] if fault_info['recent_history'] else []
        for i, history_point in enumerate(recent_data):
            time_str = history_point['timestamp'][11:19]
            history_data += f"  {time_str}: {history_point['value']} {fault_info['unit']}\n"
            if (i + 1) % 12 == 0 and i < len(recent_data) - 1:  # 每12个点分隔
                history_data += "  " + "-" * 30 + "\n"
        
        # 创建完整报告
        report = f"""
{'=' * 80}
DeepSeek+RAG专家分析报告 (置信度: {analysis_result['confidence_score']})
{'=' * 80}

故障信息详情：
  测点名称: {fault_info['name']} ({fault_info['description']})
  所属系统: {fault_info['system']}
  故障时间: {fault_info['timestamp']}
  当前数值: {fault_info['current_value']} {fault_info['unit']}
  报警级别: {fault_info['alarm_level']}
  异常信号: {', '.join(fault_info['anomaly_signals'])}
  当前趋势: {fault_info['trend']}
  预测趋势: {fault_info['predicted_trend']}
  状态描述: {fault_info['status_description']}

报警阈值:
{thresholds_info}

波动突变检测:
"""
        
        # 添加波动和突变的具体信息
        if fault_info.get('fluctuation_detected'):
            actual_fluct = fault_info.get('actual_fluctuation', 0)
            threshold_fluct = fault_info.get('fluctuation_range', 0)
            report += f"  波动检测: 实际波动率 {actual_fluct:.2f} {fault_info['unit']}/s > 阈值 {threshold_fluct} {fault_info['unit']}/s\n"
        
        if fault_info.get('mutation_detected'):
            actual_mut = fault_info.get('actual_mutation', 0)
            threshold_mut = fault_info.get('mutation_range', 0)
            report += f"  突变检测: 实际突变值 {actual_mut:.2f} {fault_info['unit']} > 阈值 {threshold_mut} {fault_info['unit']}\n"
        
        if not fault_info.get('fluctuation_detected') and not fault_info.get('mutation_detected'):
            report += "  无波动或突变检测\n"

        # 添加相关性测点信息
        if 'correlation_points' in fault_info:
            correlation_data = fault_info['correlation_points']
            
            if correlation_data['positive']:
                report += f"\n正相关测点 ({len(correlation_data['positive'])}个):\n"
                for corr_point in correlation_data['positive']:
                    analysis = corr_point.get('analysis', {})
                    report += f"  - {corr_point['name']}: {corr_point['current_value']} {corr_point['unit']}\n"
                    report += f"    趋势: {analysis.get('trend', '未知')}, "
                    report += f"报警: {analysis.get('alarm_level', '正常')}, "
                    report += f"异常概率: {analysis.get('anomaly_probability', 0):.3f}\n"
            
            if correlation_data['negative']:
                report += f"\n负相关测点 ({len(correlation_data['negative'])}个):\n"
                for corr_point in correlation_data['negative']:
                    analysis = corr_point.get('analysis', {})
                    report += f"  - {corr_point['name']}: {corr_point['current_value']} {corr_point['unit']}\n"
                    report += f"    趋势: {analysis.get('trend', '未知')}, "
                    report += f"报警: {analysis.get('alarm_level', '正常')}, "
                    report += f"异常概率: {analysis.get('anomaly_probability', 0):.3f}\n"

        # 添加知识来源
        report += f"\n知识来源:\n"
        if analysis_result['source_documents']:
            for i, doc in enumerate(analysis_result['source_documents'], 1):
                source_name = os.path.basename(doc['source'])
                report += f"  {i}. {source_name}\n"
        else:
            report += "  基于通用知识库分析\n"

        report += f"""
近期数据趋势（最近36个数据点，3分钟）:
{history_data if history_data else '  无历史数据'}

{'=' * 80}
专家分析：
{'=' * 80}
{analysis_result['expert_analysis']}

{'=' * 80}
报告生成时间: {time.strftime('%Y-%m-%d %H:%M:%S')}
{'=' * 80}
"""
        return report
    
    def _get_formatted_thresholds(self, fault_info: Dict) -> str:
        """格式化阈值信息"""
        thresholds_text = ""
        
        if 'thresholds' in fault_info:
            thresholds = fault_info['thresholds']
            if thresholds.get('HHH'):
                thresholds_text += f"  HHH报警值: {thresholds['HHH']} {fault_info['unit']}\n"
            if thresholds.get('HH'):
                thresholds_text += f"  HH报警值: {thresholds['HH']} {fault_info['unit']}\n"
            if thresholds.get('H'):
                thresholds_text += f"  H报警值: {thresholds['H']} {fault_info['unit']}\n"
            if thresholds.get('L'):
                thresholds_text += f"  L报警值: {thresholds['L']} {fault_info['unit']}\n"
            if thresholds.get('LL'):
                thresholds_text += f"  LL报警值: {thresholds['LL']} {fault_info['unit']}\n"
            if thresholds.get('LLL'):
                thresholds_text += f"  LLL报警值: {thresholds['LLL']} {fault_info['unit']}\n"
            if thresholds.get('lower_limit'):
                thresholds_text += f"  下限: {thresholds['lower_limit']} {fault_info['unit']}\n"
            if thresholds.get('upper_limit'):
                thresholds_text += f"  上限: {thresholds['upper_limit']} {fault_info['unit']}\n"
        else:
            thresholds_text = "  无阈值数据\n"
        
        return thresholds_text


if __name__ == "__main__":
    client = EnhancedDeepSeekClient()
    
    # 测试数据
    test_fault_data = {
        'kks': '01MBY10CE901_XQ01',
        'name': 'GT LOAD',
        'description': '燃机负荷',
        'system': 'GT',
        'timestamp': '2024-01-15T14:30:00',
        'current_value': 380.0,
        'unit': 'MW',
        'alarm_level': 'HIGH',
        'anomaly_signals': ['剧烈波动'],
        'trend': 'INCREASING',
        'predicted_trend': 'INCREASING',
        'status_description': '高级报警状态',
        'recent_history': [
            {'timestamp': '2024-01-15T14:28:00', 'value': 340.0},
            {'timestamp': '2024-01-15T14:29:00', 'value': 360.0}
        ],
        'thresholds': {
            'HHH': 495,
            'HH': 450,
            'H': 400
        },
        'correlation_points': {
            'positive': [
                {
                    'kks': '01MBA10CS901_XQ01',
                    'name': 'GT SPD',
                    'description': '燃机转速',
                    'system': 'GT',
                    'current_value': 3010.5,
                    'unit': 'rpm',
                    'analysis': {
                        'trend': 'INCREASING',
                        'alarm_level': 'NORMAL',
                        'anomaly_probability': 0.2
                    }
                }
            ],
            'negative': [
                {
                    'kks': '01HAD10BL102-CAL',
                    'name': '高压汽包水位2计算后',
                    'description': '高压汽包水位',
                    'system': 'HRSG',
                    'current_value': -50.2,
                    'unit': 'mm',
                    'analysis': {
                        'trend': 'STABLE',
                        'alarm_level': 'NORMAL',
                        'anomaly_probability': 0.1
                    }
                }
            ]
        }
    }
    
    result = client.analyze_fault(test_fault_data)
    if result:
        print("测试分析结果:")
        client.send_analysis_result(test_fault_data, result)
    else:
        print("测试分析失败")
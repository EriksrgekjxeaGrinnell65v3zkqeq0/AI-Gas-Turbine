import os
import glob
from typing import List, Dict, Any
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredWordDocumentLoader
)
try:
    from langchain_chroma import Chroma  # 新的Chroma
    from langchain_ollama import OllamaEmbeddings, OllamaLLM  # 新的Ollama组件
    USE_NEW_LANGCHAIN = True
except ImportError:
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import OllamaEmbeddings
    from langchain_community.llms import Ollama
    USE_NEW_LANGCHAIN = False
from langchain.chains import RetrievalQA
from langchain.prompts import PromptTemplate

class ConfidenceConfig:
    """置信度计算配置类"""
    
    # 权重配置
    WEIGHTS = {
        'document_count': 0.3,      # 文档数量权重
        'document_quality': 0.4,    # 文档质量权重  
        'query_relevance': 0.3      # 查询相关性权重
    }
    
    # 文档来源权重
    SOURCE_WEIGHTS = {
        '运行规程': 1.2,
        '操作规程': 1.2,
        '维护手册': 1.1,
        '检修指南': 1.1,
        '专家经验': 1.0,
        '技术笔记': 1.0,
        '故障案例': 0.9,
        '默认': 0.8
    }
    
    # 文档长度阈值
    LENGTH_THRESHOLDS = {
        'too_short': 100,    # 过短阈值
        'optimal_min': 200,  # 最优最小长度
        'optimal_max': 800   # 最优最大长度
    }
    
    # 置信度级别阈值
    CONFIDENCE_LEVELS = {
        'very_high': 0.8,    # 非常高
        'high': 0.6,         # 高
        'medium': 0.4,       # 中等
        'low': 0.2,          # 低
        'very_low': 0.0      # 非常低
    }
    
    @classmethod
    def get_confidence_level(cls, score: float) -> str:
        """根据得分获取置信度级别"""
        if score >= cls.CONFIDENCE_LEVELS['very_high']:
            return "非常高"
        elif score >= cls.CONFIDENCE_LEVELS['high']:
            return "高"
        elif score >= cls.CONFIDENCE_LEVELS['medium']:
            return "中等"
        elif score >= cls.CONFIDENCE_LEVELS['low']:
            return "低"
        else:
            return "非常低"
    
    @classmethod
    def get_source_weight(cls, source_path: str) -> float:
        """根据文档路径获取权重"""
        if not source_path:
            return cls.SOURCE_WEIGHTS['默认']
            
        source_lower = source_path.lower()
        for key, weight in cls.SOURCE_WEIGHTS.items():
            if key in source_lower:
                return weight
        return cls.SOURCE_WEIGHTS['默认']

class GasTurbineRAGSystem:
    """燃气轮机RAG专家系统"""
    
    def __init__(self, knowledge_base_path: str = "knowledge_base"):
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        
        # 知识库路径
        self.knowledge_base_path = os.path.join(self.project_root, knowledge_base_path)
        # 向量数据库路径
        self.vector_db_path = os.path.join(self.project_root, "chroma_db")
        
        self.vector_store = None
        self.qa_chain = None
        self.llm = None
        self.embedding_model = "nomic-embed-text"  # 默认嵌入模型
        self.confidence_config = ConfidenceConfig()
        
        # 初始化模型
        self._initialize_models()
        
        # 尝试加载现有向量数据库
        self._load_existing_vector_db()
        
    def _initialize_models(self):
        """初始化Ollama模型"""
        try:
            # 尝试使用首选嵌入模型
            try:
                if USE_NEW_LANGCHAIN:
                    self.embeddings = OllamaEmbeddings(
                        model=self.embedding_model,
                        base_url="http://localhost:11434"
                    )
                else:
                    self.embeddings = OllamaEmbeddings(
                        model=self.embedding_model,
                        base_url="http://localhost:11434"
                    )
                print(f"嵌入模型 {self.embedding_model} 初始化成功")
            except Exception as e:
                print(f"嵌入模型 {self.embedding_model} 初始化失败: {e}")
                # 尝试备选模型
                self.embedding_model = "all-minilm"
                print(f"尝试使用备选模型: {self.embedding_model}")
                if USE_NEW_LANGCHAIN:
                    self.embeddings = OllamaEmbeddings(
                        model=self.embedding_model,
                        base_url="http://localhost:11434"
                    )
                else:
                    self.embeddings = OllamaEmbeddings(
                        model=self.embedding_model,
                        base_url="http://localhost:11434"
                    )
                print(f"备选嵌入模型 {self.embedding_model} 初始化成功")
            
            # 初始化LLM
            if USE_NEW_LANGCHAIN:
                self.llm = OllamaLLM(
                    model="deepseek-r1:14b",
                    base_url="http://localhost:11434",
                    temperature=0.1,
                    num_predict=1000
                )
            else:
                self.llm = Ollama(
                    model="deepseek-r1:14b",
                    base_url="http://localhost:11434",
                    temperature=0.1,
                    num_predict=1000
                )
            
            print("RAG系统模型初始化完成")
            
        except Exception as e:
            print(f"模型初始化失败: {e}")
            raise
    
    def _load_existing_vector_db(self):
        """加载现有的向量数据库"""
        try:
            if os.path.exists(self.vector_db_path):
                print(f"尝试加载现有向量数据库: {self.vector_db_path}")
                if USE_NEW_LANGCHAIN:
                    self.vector_store = Chroma(
                        persist_directory=self.vector_db_path,
                        embedding_function=self.embeddings
                    )
                else:
                    self.vector_store = Chroma(
                        persist_directory=self.vector_db_path,
                        embedding_function=self.embeddings
                    )
                self._create_qa_chain()
                print("现有向量数据库加载成功")
            else:
                print("向量数据库不存在，请先运行 init_rag.py 构建知识库")
        except Exception as e:
            print(f"加载现有向量数据库失败: {e}")
            self.vector_store = None
            self.qa_chain = None
    
    def build_knowledge_base(self):
        """构建知识库向量数据库"""
        print("开始构建知识库...")
        
        # 收集所有文档
        all_documents = []
        
        # 加载PDF文档
        pdf_files = glob.glob(os.path.join(self.knowledge_base_path, "**/*.pdf"), recursive=True)
        for pdf_file in pdf_files:
            try:
                loader = PyPDFLoader(pdf_file)
                documents = loader.load()
                all_documents.extend(documents)
                print(f"加载PDF: {os.path.basename(pdf_file)} - {len(documents)}页")
            except Exception as e:
                print(f"加载PDF失败 {pdf_file}: {e}")
        
        # 加载Word文档
        docx_files = glob.glob(os.path.join(self.knowledge_base_path, "**/*.docx"), recursive=True)
        for docx_file in docx_files:
            try:
                loader = UnstructuredWordDocumentLoader(docx_file)
                documents = loader.load()
                all_documents.extend(documents)
                print(f"加载Word: {os.path.basename(docx_file)} - {len(documents)}节")
            except Exception as e:
                print(f"加载Word失败 {docx_file}: {e}")
        
        # 加载文本文件
        txt_files = glob.glob(os.path.join(self.knowledge_base_path, "**/*.txt"), recursive=True)
        for txt_file in txt_files:
            try:
                loader = TextLoader(txt_file, encoding='utf-8')
                documents = loader.load()
                all_documents.extend(documents)
                print(f"加载文本: {os.path.basename(txt_file)}")
            except Exception as e:
                print(f"加载文本失败 {txt_file}: {e}")
        
        if not all_documents:
            print("未找到任何文档，请检查知识库路径")
            return False
        
        # 文档分割
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len
        )
        
        split_documents = text_splitter.split_documents(all_documents)
        print(f"文档分割完成: {len(split_documents)}个片段")
        
        # 创建向量数据库
        try:
            if USE_NEW_LANGCHAIN:
                self.vector_store = Chroma.from_documents(
                    documents=split_documents,
                    embedding=self.embeddings,
                    persist_directory=self.vector_db_path
                )
            else:
                self.vector_store = Chroma.from_documents(
                    documents=split_documents,
                    embedding=self.embeddings,
                    persist_directory=self.vector_db_path
                )
            
            # 创建检索QA链
            self._create_qa_chain()
            
            print("知识库构建完成")
            return True
            
        except Exception as e:
            print(f"构建向量数据库失败: {e}")
            return False
    
    def _create_qa_chain(self):
        """创建QA检索链"""
        try:
            # 检查必要的组件是否存在
            if self.vector_store is None:
                print("错误: 向量数据库未初始化，无法创建QA链")
                return
            
            if self.llm is None:
                print("错误: LLM未初始化，无法创建QA链")
                return
            
            # 创建检索器
            retriever = self.vector_store.as_retriever(
                search_type="mmr",  # 最大边际相关性
                search_kwargs={"k": 5, "fetch_k": 10}  # 检索5个最相关文档
            )
            
            # 创建QA链 - 使用更简单的方法，避免复杂的变量传递
            self.qa_chain = RetrievalQA.from_chain_type(
                llm=self.llm,
                chain_type="stuff",
                retriever=retriever,
                return_source_documents=True
            )
            
            print("QA链创建成功")
            
        except Exception as e:
            print(f"创建QA链失败: {e}")
            self.qa_chain = None
    
    def analyze_fault_with_rag(self, fault_data: Dict) -> Dict[str, Any]:
        """使用RAG分析故障"""
        try:
            # 检查QA链是否已初始化
            if self.qa_chain is None:
                print("错误: QA链未初始化，无法进行分析")
                return self._create_fallback_response("RAG系统未正确初始化，请先构建知识库")
            
            # 准备查询 - 将所有故障信息整合到查询中
            query = self._create_comprehensive_query(fault_data)
            
            print(f"RAG查询: {query}")
            
            # 执行RAG查询 - 只传递查询字符串
            result = self.qa_chain.invoke({"query": query})
            
            # 使用增强的置信度计算
            confidence_score = self._calculate_confidence(
                result["source_documents"], 
                query
            )
            
            # 获取置信度详细分解
            confidence_breakdown = self.get_confidence_breakdown(result["source_documents"], query)
            
            # 解析结果
            analysis_result = {
                "expert_analysis": result["result"],
                "source_documents": [
                    {
                        "source": doc.metadata.get("source", "未知"),
                        "content": doc.page_content[:200] + "...",
                        "relevance_score": self._calculate_document_relevance(doc, query)
                    }
                    for doc in result["source_documents"]
                ],
                "confidence_score": confidence_score,
                "confidence_breakdown": confidence_breakdown,
                "query_used": query
            }
            
            return analysis_result
            
        except Exception as e:
            print(f"RAG分析失败: {e}")
            import traceback
            traceback.print_exc()
            
            return self._create_fallback_response(f"RAG系统分析失败: {str(e)}")
    
    def _create_comprehensive_query(self, fault_data: Dict) -> str:
        """创建包含所有故障信息的综合查询"""
        # 构建详细的故障描述
        fault_description = f"""
故障分析请求：

测点信息:
- 名称: {fault_data.get('name', '未知')}
- KKS代码: {fault_data.get('kks', '未知')}
- 系统: {fault_data.get('system', '未知')}
- 描述: {fault_data.get('description', '无描述')}

当前状态:
- 当前值: {fault_data.get('current_value', 0)} {fault_data.get('unit', '')}
- 报警级别: {fault_data.get('alarm_level', '未知')}
- 当前趋势: {fault_data.get('trend', '未知')}
- 预测趋势: {fault_data.get('predicted_trend', '未知')}
- 异常信号: {', '.join(fault_data.get('anomaly_signals', []))}
- 状态描述: {fault_data.get('status_description', '无描述')}

请基于9F燃气轮机的运行规程、维护手册和专家经验，提供以下分析:
1. 故障类型识别和严重程度评估
2. 可能的根本原因分析（参考类似历史案例）
3. 立即处理措施和操作步骤
4. 后续监控重点和预防建议
5. 如需要停机检查，说明判断依据

请确保建议具体、可操作，并参考相关规程标准。
"""
        
        # 添加关键词以改善检索
        keywords = self._create_keywords(fault_data)
        
        return keywords + fault_description
    
    def _create_keywords(self, fault_data: Dict) -> str:
        """创建用于检索的关键词"""
        base_keywords = f"{fault_data.get('name', '')} {fault_data.get('description', '')} "
        
        # 根据异常信号添加关键词
        anomaly_signals = fault_data.get('anomaly_signals', [])
        if "剧烈波动" in anomaly_signals:
            base_keywords += "波动 振荡 不稳定 "
        if "数值突变" in anomaly_signals:
            base_keywords += "突变 跳变 阶跃变化 "
        if "异常模式" in anomaly_signals:
            base_keywords += "异常 故障 诊断 "
        
        # 根据系统添加领域关键词
        system_keywords = {
            "GT": "燃气轮机 透平 燃烧室 燃气 进气室",
            "ST": "汽轮机 蒸汽 透平 汽机 旁路 过热度", 
            "HRSG": "余热锅炉 汽包 水位 锅炉 过热度",
            "AUX": "辅助系统 润滑油 液压 辅助",
            "ELE": "电气 电流 电机 电气系统"
        }
        system = fault_data.get('system', '')
        base_keywords += system_keywords.get(system, "")
        
        return base_keywords + " 处理措施 维护手册 运行规程 故障处理 检修指南"
    
    def _create_fallback_response(self, error_message: str) -> Dict[str, Any]:
        """创建降级响应"""
        return {
            "expert_analysis": f"RAG系统暂时无法提供分析: {error_message}。请参考常规处理流程。",
            "source_documents": [],
            "confidence_score": 0.0,
            "confidence_breakdown": {
                "overall_confidence": 0.0,
                "confidence_level": "非常低",
                "breakdown": {
                    "document_count": 0,
                    "document_quality": 0.0,
                    "query_relevance": 0.0
                }
            },
            "query_used": ""
        }
    
    def _calculate_confidence(self, source_documents: List, query: str = "") -> float:
        """基于配置的智能置信度计算"""
        if not source_documents:
            return 0.0
        
        # 使用配置的权重
        weights = self.confidence_config.WEIGHTS
        
        # 1. 文档数量因子
        doc_count_factor = min(len(source_documents) / 5.0, 1.0) * weights['document_count']
        
        # 2. 文档质量因子
        quality_factor = self._calculate_document_quality(source_documents) * weights['document_quality']
        
        # 3. 相关性因子
        relevance_factor = self._calculate_query_relevance(source_documents, query) * weights['query_relevance']
        
        confidence_score = doc_count_factor + quality_factor + relevance_factor
        
        # 确保在0-1范围内
        confidence_score = max(0.0, min(1.0, confidence_score))
        
        return round(confidence_score, 2)
    
    def _calculate_document_quality(self, source_documents: List) -> float:
        """基于配置的文档质量计算"""
        if not source_documents:
            return 0.0
        
        quality_score = 0.0
        total_weight = 0
        
        for doc in source_documents:
            source_path = doc.metadata.get("source", "")
            
            # 使用配置的源权重
            weight = self.confidence_config.get_source_weight(source_path)
            
            # 根据文档长度调整
            content_length = len(doc.page_content)
            if content_length < self.confidence_config.LENGTH_THRESHOLDS['too_short']:
                weight *= 0.7  # 过短文档降权
            elif content_length > self.confidence_config.LENGTH_THRESHOLDS['optimal_max']:
                weight *= 1.0  # 超长文档保持原权重
            elif content_length >= self.confidence_config.LENGTH_THRESHOLDS['optimal_min']:
                weight *= 1.1  # 合适长度文档加权
            
            quality_score += weight
            total_weight += 1
        
        # 归一化到0-1范围
        max_possible_score = max(self.confidence_config.SOURCE_WEIGHTS.values()) * 1.1
        normalized_score = quality_score / (total_weight * max_possible_score) if total_weight > 0 else 0.0
        
        return normalized_score
    
    def _calculate_query_relevance(self, source_documents: List, query: str) -> float:
        """计算查询相关性因子"""
        if not source_documents or not query:
            return 0.5  # 默认中等相关性
        
        query_terms = set(query.lower().split())
        relevance_scores = []
        
        for doc in source_documents:
            content = doc.page_content.lower()
            doc_terms = set(content.split())
            
            # 计算Jaccard相似度
            intersection = query_terms.intersection(doc_terms)
            union = query_terms.union(doc_terms)
            
            if len(union) == 0:
                similarity = 0.0
            else:
                similarity = len(intersection) / len(union)
            
            relevance_scores.append(similarity)
        
        # 返回平均相关性
        return sum(relevance_scores) / len(relevance_scores) if relevance_scores else 0.0
    
    def _calculate_document_relevance(self, document, query: str) -> float:
        """计算单个文档的相关性得分"""
        if not query:
            return 0.5
        
        content = document.page_content.lower()
        query_terms = set(query.lower().split())
        doc_terms = set(content.split())
        
        intersection = query_terms.intersection(doc_terms)
        union = query_terms.union(doc_terms)
        
        if len(union) == 0:
            return 0.0
        
        return round(len(intersection) / len(union), 3)
    
    def get_confidence_breakdown(self, source_documents: List, query: str) -> Dict:
        """获取置信度详细分解"""
        if not source_documents:
            return {
                "overall_confidence": 0.0,
                "confidence_level": "非常低",
                "breakdown": {
                    "document_count": 0,
                    "document_quality": 0.0,
                    "query_relevance": 0.0
                }
            }
        
        weights = self.confidence_config.WEIGHTS
        
        doc_count = len(source_documents)
        doc_count_score = min(doc_count / 5.0, 1.0)
        quality_score = self._calculate_document_quality(source_documents)
        relevance_score = self._calculate_query_relevance(source_documents, query)
        
        overall_confidence = (
            doc_count_score * weights['document_count'] +
            quality_score * weights['document_quality'] +
            relevance_score * weights['query_relevance']
        )
        
        return {
            "overall_confidence": round(overall_confidence, 2),
            "confidence_level": self.confidence_config.get_confidence_level(overall_confidence),
            "breakdown": {
                "document_count": doc_count,
                "document_count_score": round(doc_count_score, 2),
                "document_quality": round(quality_score, 2),
                "query_relevance": round(relevance_score, 2),
                "documents": [
                    {
                        "source": doc.metadata.get("source", "未知"),
                        "relevance": self._calculate_document_relevance(doc, query)
                    }
                    for doc in source_documents
                ]
            }
        }
    
    def update_confidence_weights(self, new_weights: Dict):
        """更新置信度权重配置"""
        if 'document_count' in new_weights:
            self.confidence_config.WEIGHTS['document_count'] = new_weights['document_count']
        if 'document_quality' in new_weights:
            self.confidence_config.WEIGHTS['document_quality'] = new_weights['document_quality']
        if 'query_relevance' in new_weights:
            self.confidence_config.WEIGHTS['query_relevance'] = new_weights['query_relevance']
        
        print("置信度权重已更新")
        print(f"新权重配置: {self.confidence_config.WEIGHTS}")

# 单例实例
rag_system = GasTurbineRAGSystem()
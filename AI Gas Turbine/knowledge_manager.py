import os
import shutil
from datetime import datetime

class KnowledgeBaseManager:
    """知识库管理工具"""
    
    def __init__(self, knowledge_base_path: str = "knowledge_base"):
        # 获取项目根目录
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.knowledge_base_path = os.path.join(self.project_root, knowledge_base_path)
        self.vector_db_path = os.path.join(self.project_root, "chroma_db")
        
    def add_document(self, file_path: str, category: str = "未分类"):
        """添加文档到知识库"""
        try:
            # 创建分类目录
            category_path = os.path.join(self.knowledge_base_path, category)
            os.makedirs(category_path, exist_ok=True)
            
            # 复制文件
            filename = os.path.basename(file_path)
            dest_path = os.path.join(category_path, filename)
            shutil.copy2(file_path, dest_path)
            
            print(f"文档已添加到知识库: {category}/{filename}")
            return True
            
        except Exception as e:
            print(f"添加文档失败: {e}")
            return False
    
    def list_documents(self, category: str = None):
        """列出知识库文档"""
        base_path = self.knowledge_base_path
        if category:
            base_path = os.path.join(base_path, category)
        
        documents = []
        for root, dirs, files in os.walk(base_path):
            for file in files:
                if file.endswith(('.pdf', '.docx', '.txt', '.md')):
                    full_path = os.path.join(root, file)
                    rel_path = os.path.relpath(full_path, self.knowledge_base_path)
                    file_size = os.path.getsize(full_path)
                    mod_time = datetime.fromtimestamp(os.path.getmtime(full_path))
                    
                    documents.append({
                        'path': rel_path,
                        'size': file_size,
                        'modified': mod_time
                    })
        
        return documents
    
    def rebuild_vector_database(self):
        """重新构建向量数据库"""
        try:
            # 删除旧的向量数据库
            if os.path.exists(self.vector_db_path):
                shutil.rmtree(self.vector_db_path)
                print("旧的向量数据库已删除")
            
            # 重新构建
            from rag_system import rag_system
            success = rag_system.build_knowledge_base()
            
            if success:
                print("向量数据库重建完成")
                return True
            else:
                print("向量数据库重建失败")
                return False
                
        except Exception as e:
            print(f"重建向量数据库失败: {e}")
            return False

    def get_knowledge_base_stats(self):
        """获取知识库统计信息"""
        stats = {
            'total_documents': 0,
            'total_size': 0,
            'categories': {},
            'file_types': {}
        }
        
        for root, dirs, files in os.walk(self.knowledge_base_path):
            category = os.path.relpath(root, self.knowledge_base_path)
            if category == '.':
                category = '根目录'
                
            for file in files:
                if file.endswith(('.pdf', '.docx', '.txt', '.md')):
                    full_path = os.path.join(root, file)
                    file_size = os.path.getsize(full_path)
                    file_ext = os.path.splitext(file)[1].lower()
                    
                    stats['total_documents'] += 1
                    stats['total_size'] += file_size
                    
                    # 按分类统计
                    if category not in stats['categories']:
                        stats['categories'][category] = 0
                    stats['categories'][category] += 1
                    
                    # 按文件类型统计
                    if file_ext not in stats['file_types']:
                        stats['file_types'][file_ext] = 0
                    stats['file_types'][file_ext] += 1
        
        # 转换大小为MB
        stats['total_size_mb'] = round(stats['total_size'] / (1024 * 1024), 2)
        
        return stats

# 使用示例
if __name__ == "__main__":
    manager = KnowledgeBaseManager()
    
    # 显示知识库统计
    stats = manager.get_knowledge_base_stats()
    print("知识库统计信息:")
    print(f"总文档数: {stats['total_documents']}")
    print(f"总大小: {stats['total_size_mb']} MB")
    print("分类统计:")
    for category, count in stats['categories'].items():
        print(f"  {category}: {count} 个文档")
    print("文件类型统计:")
    for file_type, count in stats['file_types'].items():
        print(f"  {file_type}: {count} 个文件")
#!/usr/bin/env python3
"""
RAG系统初始化脚本
用于构建知识库向量数据库
"""

import os
import sys
from knowledge_manager import KnowledgeBaseManager

def initialize_rag_system():
    """初始化RAG系统"""
    print("=" * 60)
    print("9F燃气电厂专家系统RAG系统初始化")
    print("=" * 60)
    
    # 创建知识库管理器
    manager = KnowledgeBaseManager()
    
    # 确保知识库目录存在
    if not os.path.exists(manager.knowledge_base_path):
        os.makedirs(manager.knowledge_base_path)
        print(f"创建知识库目录: {manager.knowledge_base_path}")
        print("请将电厂相关文档放入以下子目录:")
        print(f"  - {os.path.join(manager.knowledge_base_path, '运行规程')}")
        print(f"  - {os.path.join(manager.knowledge_base_path, '维护手册')}") 
        print(f"  - {os.path.join(manager.knowledge_base_path, '历史故障案例')}")
        print(f"  - {os.path.join(manager.knowledge_base_path, '专家经验库')}")
        print("\n然后重新运行此脚本。")
        return False
    
    # 检查知识库是否有文档
    stats = manager.get_knowledge_base_stats()
    if stats['total_documents'] == 0:
        print("知识库中没有找到任何文档!")
        print("请将电厂相关文档放入 knowledge_base/ 目录")
        return False
    
    print(f"发现 {stats['total_documents']} 个文档，总大小 {stats['total_size_mb']} MB")
    print("文档分类:")
    for category, count in stats['categories'].items():
        print(f"  {category}: {count} 个文档")
    
    # 确认是否继续
    print("\n即将构建向量数据库，这可能需要一些时间...")
    try:
        input("按 Enter 键继续，或按 Ctrl+C 取消...")
    except KeyboardInterrupt:
        print("\n用户取消操作")
        return False
    
    # 重建向量数据库
    print("\n开始构建向量数据库...")
    success = manager.rebuild_vector_database()
    
    if success:
        print("\n RAG系统初始化完成!")
        print("向量数据库已构建，可以启动主系统了。")
        return True
    else:
        print("\n RAG系统初始化失败!")
        return False

if __name__ == "__main__":
    try:
        success = initialize_rag_system()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"初始化过程中发生错误: {e}")
        sys.exit(1)
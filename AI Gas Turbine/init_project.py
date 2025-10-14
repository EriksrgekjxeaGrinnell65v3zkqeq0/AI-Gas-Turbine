#!/usr/bin/env python3
"""
项目初始化脚本
创建必要的目录结构并验证路径
"""

import os
import sys
from project_paths import project_paths

def initialize_project():
    """初始化项目目录结构"""
    print("=" * 60)
    print("9F燃气电厂智能监盘系统 - 项目初始化")
    print("=" * 60)
    
    # 创建目录结构
    project_paths.create_directories()
    
    # 验证关键路径
    if not project_paths.validate_paths():
        print("\n警告: 部分关键文件缺失，系统可能无法正常运行")
        print("请确保以下文件已正确放置:")
        print(f"  - 点表文件: {project_paths.point_table}")
        print(f"  - LimiX模型: {project_paths.limix_model}")
        
        response = input("\n是否继续初始化? (y/n): ")
        if response.lower() != 'y':
            print("初始化已取消")
            return False
    
    print("\n项目初始化完成!")
    print("现在可以运行以下命令启动系统:")
    print("  python init_rag.py    # 初始化RAG系统")
    print("  start_system.bat      # 启动完整系统")
    
    return True

if __name__ == "__main__":
    try:
        success = initialize_project()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"项目初始化失败: {e}")
        sys.exit(1)
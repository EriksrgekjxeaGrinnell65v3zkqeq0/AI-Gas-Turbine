#!/usr/bin/env python3
"""
9F燃气电厂智能监盘系统 - GUI启动脚本
"""

import sys
import os
import subprocess
import platform

def check_dependencies():
    """检查必要的依赖包"""
    required_packages = ['PyQt5', 'matplotlib', 'numpy', 'pandas']
    missing_packages = []
    
    for package in required_packages:
        try:
            __import__(package)
        except ImportError:
            missing_packages.append(package)
    
    return missing_packages

def install_dependencies(missing_packages):
    """安装缺失的依赖包"""
    if not missing_packages:
        return True
        
    print("发现缺失的依赖包:", missing_packages)
    response = input("是否自动安装这些依赖包? (y/n): ")
    
    if response.lower() != 'y':
        print("请手动安装缺失的依赖包:")
        for package in missing_packages:
            print(f"  pip install {package}")
        return False
    
    try:
        for package in missing_packages:
            print(f"正在安装 {package}...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        return True
    except subprocess.CalledProcessError as e:
        print(f"安装依赖包失败: {e}")
        return False

def setup_environment():
    """设置运行环境"""
    # 将GUI目录添加到Python路径
    gui_dir = os.path.join(os.path.dirname(__file__), 'GUI')
    if gui_dir not in sys.path:
        sys.path.insert(0, gui_dir)
    
    # 检查必要的目录
    required_dirs = [
        'GUI/components',
        'GUI/models', 
        'GUI/utils'
    ]
    
    for dir_path in required_dirs:
        full_path = os.path.join(os.path.dirname(__file__), dir_path)
        if not os.path.exists(full_path):
            print(f"错误: 缺少必要的目录 {dir_path}")
            return False
    
    return True

def check_data_files():
    """检查必要的数据文件"""
    required_files = ['point.xls', 'Cor_kks.xls']
    missing_files = []
    
    for file_name in required_files:
        if not os.path.exists(file_name):
            missing_files.append(file_name)
    
    if missing_files:
        print("警告: 缺少必要的数据文件:")
        for file_name in missing_files:
            print(f"  - {file_name}")
        print("请将文件放置在项目根目录下")
        return False
    
    return True

def main():
    """主函数"""
    print("=" * 60)
    print("9F燃气电厂智能监盘系统 - GUI界面")
    print("=" * 60)
    
    # 检查系统平台
    system = platform.system()
    print(f"操作系统: {system}")
    
    # 检查数据文件
    print("检查数据文件...")
    if not check_data_files():
        print("数据文件不完整，系统可能无法正常工作")
    
    # 检查依赖
    print("检查依赖包...")
    missing_packages = check_dependencies()
    
    if missing_packages:
        if not install_dependencies(missing_packages):
            print("依赖包安装失败，无法启动GUI")
            input("按Enter键退出...")
            return
    
    # 设置环境
    print("设置运行环境...")
    if not setup_environment():
        print("环境设置失败")
        input("按Enter键退出...")
        return
    
    # 启动GUI
    try:
        print("启动GUI界面...")
        from GUI.gui_main import main as gui_main
        gui_main()
    except ImportError as e:
        print(f"导入GUI模块失败: {e}")
        print("请确保GUI目录结构正确")
        input("按Enter键退出...")
    except Exception as e:
        print(f"启动GUI时发生错误: {e}")
        input("按Enter键退出...")

if __name__ == '__main__':
    main()
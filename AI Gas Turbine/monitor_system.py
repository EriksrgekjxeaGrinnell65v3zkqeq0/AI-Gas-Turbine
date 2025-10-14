import requests
import psutil
import time
from datetime import datetime

def monitor_system():
    """监控系统资源状态"""
    print("系统资源监控")
    print("=" * 50)
    
    # 检查Ollama服务
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        ollama_status = "运行中" if response.status_code == 200 else "异常"
    except:
        ollama_status = "未运行"
    
    # 检查Python进程
    python_processes = []
    for proc in psutil.process_iter(['pid', 'name', 'memory_info']):
        if 'python' in proc.info['name'].lower():
            memory_mb = proc.info['memory_info'].rss / 1024 / 1024
            python_processes.append({
                'pid': proc.info['pid'],
                'memory_mb': round(memory_mb, 1)
            })
    
    # 系统内存使用
    memory = psutil.virtual_memory()
    
    print(f"当前时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Ollama状态: {ollama_status}")
    print(f"Python进程数: {len(python_processes)}")
    print(f"系统内存使用: {memory.percent}%")
    print(f"可用内存: {round(memory.available / 1024 / 1024, 1)} MB")
    
    if python_processes:
        print("\nPython进程详情:")
        for proc in python_processes:
            print(f"  PID {proc['pid']}: {proc['memory_mb']} MB")

if __name__ == "__main__":
    monitor_system()
import socket
import os
import json
import threading
from datetime import datetime
from config import config

class FaultReceiver:
    """故障文件接收器"""
    
    def __init__(self):
        self.running = False
        self.thread = None
          # 获取项目根目录
        self.project_root = os.path.dirname(os.path.abspath(__file__))
        self.fault_dir = os.path.join(self.project_root, "fault_reports")
        
        if not os.path.exists(self.fault_dir):
            os.makedirs(self.fault_dir)
    
    def start(self):
        """启动接收器"""
        self.running = True
        self.thread = threading.Thread(target=self._receive_faults)
        self.thread.daemon = True
        self.thread.start()
        print(f"故障接收器已启动，监听端口: {config.FAULT_SEND_PORT}")
    
    def stop(self):
        """停止接收器"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _receive_faults(self):
        """接收故障文件"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((config.HOST, config.FAULT_SEND_PORT))
            server_socket.listen(5)
            
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    client_socket, addr = server_socket.accept()
                    
                    with client_socket:
                        filename_data = b""
                        while True:
                            chunk = client_socket.recv(1)
                            if chunk == b'\n':
                                break
                            filename_data += chunk
                        
                        filename = filename_data.decode('utf-8')
                        
                        content_data = b""
                        while True:
                            chunk = client_socket.recv(1024)
                            if not chunk:
                                break
                            content_data += chunk
                        
                        content = content_data.decode('utf-8')
                        
                        self._save_fault_file(filename, content)
                        print(f"接收到故障文件: {filename}")
                        
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"接收故障文件错误: {e}")
                    
        finally:
            server_socket.close()
    
    def _save_fault_file(self, filename: str, content: str):
        """保存故障文件"""
        try:
            current_date = datetime.now().strftime("%Y%m%d")
            
            name, ext = os.path.splitext(filename)
            daily_filename = f"{name}_{current_date}{ext}"
            filepath = os.path.join(self.fault_dir, daily_filename)
            
            file_exists = os.path.exists(filepath)
            
            with open(filepath, 'a', encoding='utf-8') as f:
                if not file_exists:
                    f.write("=" * 80 + "\n")
                    f.write(f"燃气轮机监控系统 - 故障报告汇总\n")
                    f.write(f"测点: {name}\n")
                    f.write(f"日期: {datetime.now().strftime('%Y-%m-%d')}\n")
                    f.write("=" * 80 + "\n\n")
                
                f.write(content)
                f.write("\n\n")
            
            action = "更新" if file_exists else "创建"
            print(f"故障文件已{action}: {daily_filename}")
            
        except Exception as e:
            print(f"保存故障文件失败: {e}")
    
    def get_daily_fault_files(self):
        """获取当日的故障文件列表"""
        current_date = datetime.now().strftime("%Y%m%d")
        daily_files = []
        
        if os.path.exists(self.fault_dir):
            for filename in os.listdir(self.fault_dir):
                if filename.endswith(f"_{current_date}.txt"):
                    daily_files.append(filename)
        
        return daily_files


def main():
    """主函数"""
    print("故障文件接收器")
    print("监听9003端口接收故障报告")
    print("每个测点每日生成一个故障日志文件")
    print("=" * 50)
    
    receiver = FaultReceiver()
    receiver.start()
    
    try:
        while True:
            input("按Enter键退出...\n")
            break
    except KeyboardInterrupt:
        pass
    finally:
        receiver.stop()
        print("故障接收器已停止")

if __name__ == "__main__":
    main()
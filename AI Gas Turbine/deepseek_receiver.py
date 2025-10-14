import socket
import json
import threading
from config import config

class DeepSeekReceiver:
    """DeepSeek分析结果接收器"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """启动接收器"""
        self.running = True
        self.thread = threading.Thread(target=self._receive_results)
        self.thread.daemon = True
        self.thread.start()
        print(f"DeepSeek结果接收器已启动，监听端口: {config.DEEPSEEK_SEND_PORT}")
        print("等待接收包含故障信息和AI分析的完整报告...")
    
    def stop(self):
        """停止接收器"""
        self.running = False
        if self.thread:
            self.thread.join()
    
    def _receive_results(self):
        """接收结果"""
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            server_socket.bind((config.HOST, config.DEEPSEEK_SEND_PORT))
            server_socket.listen(5)
            
            while self.running:
                try:
                    server_socket.settimeout(1.0)
                    client_socket, addr = server_socket.accept()
                    
                    with client_socket:
                        data = client_socket.recv(65536)
                        if data:
                            self._process_result(data)
                            
                except socket.timeout:
                    continue
                except Exception as e:
                    print(f"DeepSeek结果接收错误: {e}")
                    
        finally:
            server_socket.close()
    
    def _process_result(self, data: bytes):
        """处理接收到的结果"""
        try:
            result = data.decode('utf-8')
            self._display_deepseek_result(result)
            
        except Exception as e:
            print(f"处理DeepSeek结果数据错误: {e}")
    
    def _display_deepseek_result(self, result: str):
        """显示DeepSeek分析结果"""
        # 直接显示完整的报告，不再添加额外的边框
        print("\n" + result)


def main():
    """主函数"""
    print("DeepSeek分析结果接收器")
    print("监听DeepSeek发送的完整分析报告")
    print("=" * 60)
    
    receiver = DeepSeekReceiver()
    receiver.start()
    
    try:
        # 保持运行
        while True:
            input("按Enter键退出...\n")
            break
    except KeyboardInterrupt:
        pass
    finally:
        receiver.stop()
        print("DeepSeek结果接收器已停止")

if __name__ == "__main__":
    main()
import socket
import json
import threading
from config import config

class ResultReceiver:
    """分析结果接收器"""
    
    def __init__(self):
        self.running = False
        self.thread = None
    
    def start(self):
        """启动接收器"""
        self.running = True
        self.thread = threading.Thread(target=self._receive_results)
        self.thread.daemon = True
        self.thread.start()
        print(f"结果接收器已启动，监听端口: {config.RESULT_SEND_PORT}")
    
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
            server_socket.bind((config.HOST, config.RESULT_SEND_PORT))
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
                    print(f"结果接收错误: {e}")
                    
        finally:
            server_socket.close()
    
    def _process_result(self, data: bytes):
        """处理接收到的结果"""
        try:
            result = json.loads(data.decode('utf-8'))
            self._display_detailed_result(result)
            
        except Exception as e:
            print(f"处理结果数据错误: {e}")
    
    def _display_detailed_result(self, result: dict):
        """显示详细结果"""
        print("\n" + "=" * 100)
        print("详细分析结果")
        print("=" * 100)
        print(f"分析时间: {result['timestamp']}")
        print(f"总体健康状态: {result['overall_health']}")
        print(f"风险等级: {result['risk_level']}")
        print(f"系统总结: {result['summary']}")
        
        if result['alarms']:
            print("\n严重报警列表:")
            for i, alarm in enumerate(result['alarms'], 1):
                print(f"  {i}. {alarm}")
        
        if result['warnings']:
            print("\n警告信息列表:")
            for i, warning in enumerate(result['warnings'], 1):
                print(f"  {i}. {warning}")
        
        print("\n测点详细分析:")
        print("-" * 100)
        
        for kks, point in result['point_analysis'].items():
            status_prefix = ""
            if point['alarm_level'] == 'CRITICAL':
                status_prefix = "[CRITICAL] "
            elif point['alarm_level'] == 'HIGH':
                status_prefix = "[HIGH] "
            elif point['alarm_level'] == 'MEDIUM':
                status_prefix = "[MEDIUM] "
            
            print(f"{status_prefix}{point['name']} ({kks})")
            print(f"  当前值: {point['current_value']} {point['unit']}")
            print(f"  系统: {point['system']}")
            print(f"  状态: {point['status_description']}")
            print(f"  当前趋势: {point['trend']}")
            print(f"  异常概率: {point['anomaly_probability']:.3f}")
            print(f"  波动检测: {'是' if point['fluctuation_detected'] else '否'}")
            print(f"  突变检测: {'是' if point['mutation_detected'] else '否'}")
            print(f"  预测趋势: {point['predicted_trend']}")
            print()


def main():
    """主函数"""
    print("分析结果接收器")
    print("监听分析系统发送的结果")
    print("=" * 50)
    
    receiver = ResultReceiver()
    receiver.start()
    
    try:
        while True:
            input("按Enter键退出...\n")
            break
    except KeyboardInterrupt:
        pass
    finally:
        receiver.stop()
        print("结果接收器已停止")

if __name__ == "__main__":
    main()
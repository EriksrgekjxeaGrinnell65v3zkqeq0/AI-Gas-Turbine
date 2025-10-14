import socket
import json
import time
import pandas as pd
from datetime import datetime
import logging
from sis_data_collector import SISDataCollector
from config import config

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class SISDataSender:
    """SIS数据发送器 - 独立运行，发送数据到主系统端口"""
    
    def __init__(self, host='localhost', port=9001):
        self.host = host
        self.port = port
        self.socket = None
    
    def connect(self, max_retries=10, retry_delay=5):
        """连接到主系统端口，支持重试机制"""
        for attempt in range(max_retries):
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10)  # 设置连接超时
                self.socket.connect((self.host, self.port))
                logger.info(f"已连接到主系统端口 {self.host}:{self.port}")
                return True
            except Exception as e:
                logger.warning(f"连接主系统端口失败 (尝试 {attempt + 1}/{max_retries}): {e}")
                if attempt < max_retries - 1:
                    logger.info(f"{retry_delay}秒后重试...")
                    time.sleep(retry_delay)
                else:
                    logger.error(f"连接主系统端口最终失败: {e}")
                    return False
    
    def send_data(self, data):
        """发送数据到主系统"""
        if not self.socket:
            if not self.connect():
                return False
        
        try:
            # 转换为JSON格式并发送
            message = json.dumps(data, ensure_ascii=False).encode('utf-8')
            self.socket.sendall(message)
            logger.info(f"已发送数据包，包含 {len(data.get('data_points', {}))} 个测点")
            return True
        except Exception as e:
            logger.error(f"发送数据失败: {e}")
            # 尝试重新连接
            try:
                self.socket.close()
            except:
                pass
            self.socket = None
            
            # 重新连接并重试发送
            if self.connect(max_retries=3, retry_delay=3):
                try:
                    message = json.dumps(data, ensure_ascii=False).encode('utf-8')
                    self.socket.sendall(message)
                    logger.info(f"重连后成功发送数据包")
                    return True
                except Exception as retry_e:
                    logger.error(f"重连后发送数据失败: {retry_e}")
                    return False
            else:
                return False
    
    def close(self):
        """关闭连接"""
        if self.socket:
            try:
                self.socket.close()
                logger.info("连接已关闭")
            except:
                pass
            self.socket = None

def wait_for_main_system(max_wait=60):
    """等待主监控系统启动"""
    print("等待主监控系统启动...")
    for i in range(max_wait):
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('localhost', 9001))
            sock.close()
            if result == 0:
                print("✓ 主监控系统已就绪")
                return True
            else:
                if i % 5 == 0:  # 每5秒显示一次等待信息
                    print(f"等待主监控系统启动... ({i+1}/{max_wait}秒)")
                time.sleep(1)
        except Exception as e:
            if i % 5 == 0:
                print(f"等待主监控系统启动... ({i+1}/{max_wait}秒)")
            time.sleep(1)
    
    print("✗ 主监控系统启动超时")
    return False

def main():
    """主函数"""
    print("=" * 60)
    print("SIS数据发送器 - 独立运行")
    print("=" * 60)
    
    # 首先等待主监控系统启动
    if not wait_for_main_system():
        print("请先启动主监控系统，然后再运行数据发送器")
        return
    
    # 创建数据收集器和发送器
    collector = SISDataCollector(
        config.REAL_SIS_CONFIG['base_url'],
        config.REAL_SIS_CONFIG['username'], 
        config.REAL_SIS_CONFIG['password']
    )
    sender = SISDataSender(config.HOST, config.SIS_RECEIVE_PORT)
    
    try:
        # 尝试登录SIS系统
        print("正在登录SIS系统...")
        if collector.login():
            print("✓ SIS系统登录成功！")
            
            # 连接主系统
            print("正在连接主监控系统...")
            if sender.connect():
                print("✓ 已连接到主监控系统")
                
                # 持续监控循环
                interval = config.REAL_SIS_CONFIG['monitor_interval']
                print(f"✓ 开始持续监控，每 {interval} 秒发送一次数据...")
                print("按 Ctrl+C 停止")
                
                data_count = 0
                consecutive_failures = 0
                max_consecutive_failures = 3
                
                try:
                    while True:
                        # 获取测点数据
                        tag_items = collector.get_tag_data()
                        if tag_items:
                            # 转换为KKS格式
                            kks_data = collector.convert_to_kks_format(tag_items)
                            data_count += 1
                            
                            # 创建数据包
                            data_package = {
                                'timestamp': datetime.now().isoformat(),
                                'data_points': kks_data,
                                'source': 'REAL_SIS'
                            }
                            
                            # 发送数据到主系统
                            if sender.send_data(data_package):
                                print(f"[{data_count}] ✓ 成功发送 {len(kks_data)} 个测点数据")
                                consecutive_failures = 0  # 重置连续失败计数
                            else:
                                consecutive_failures += 1
                                print(f"[{data_count}] ✗ 数据发送失败 (连续失败: {consecutive_failures})")
                                
                                # 如果连续失败次数过多，尝试重新连接
                                if consecutive_failures >= max_consecutive_failures:
                                    print("连续失败次数过多，尝试重新连接...")
                                    if sender.connect():
                                        print("✓ 重新连接成功")
                                        consecutive_failures = 0
                                    else:
                                        print("✗ 重新连接失败")
                                        break
                        else:
                            print(f"[{data_count}] ⚠ 获取SIS数据失败")
                            consecutive_failures += 1
                        
                        # 等待下一次采集
                        time.sleep(interval)
                        
                except KeyboardInterrupt:
                    print("\n监控已停止")
            else:
                print("✗ 连接主系统失败")
        else:
            print("✗ SIS系统登录失败，请检查：")
            print("  1. 网络连接")
            print("  2. 服务器状态") 
            print("  3. 用户名和密码")
            
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 关闭连接
        sender.close()

if __name__ == "__main__":
    main()
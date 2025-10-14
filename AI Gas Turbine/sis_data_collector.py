import os
import requests
import json
import time
import socket
import pandas as pd
from datetime import datetime
import logging
import re
import base64

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class KKSMapper:
    """KKS映射器 - 处理SIS测点到KKS测点的映射"""
    
    def __init__(self, excel_file_path=None):
        if excel_file_path is None:
            # 使用绝对路径
            import os
            project_root = os.path.dirname(os.path.abspath(__file__))
            self.excel_file_path = os.path.join(project_root, 'Cor_kks.xls')
        else:
            self.excel_file_path = excel_file_path
            
        self.mapping_dict = {}
        self.load_mapping_data()
    
    def load_mapping_data(self):
        """从Excel文件加载映射数据"""
        try:
            if not os.path.exists(self.excel_file_path):
                print(f"警告: 映射表文件不存在: {self.excel_file_path}")
                # 创建空的映射字典
                self.mapping_dict = {}
                return
                
            # 读取Excel文件
            df = pd.read_excel(self.excel_file_path, sheet_name='Sheet1')
            
            # 构建映射字典：SIS数据点名 -> KKS点名
            for _, row in df.iterrows():
                sis_point = str(row['SIS数据点名']).strip() if pd.notna(row['SIS数据点名']) else ""
                kks_point = str(row['对应KKS点名']).strip() if pd.notna(row['对应KKS点名']) else ""
                description = str(row['测点']).strip() if pd.notna(row['测点']) else ""
                
                if sis_point and kks_point:
                    self.mapping_dict[sis_point] = {
                        'kks': kks_point,
                        'description': description if description else sis_point
                    }
            
            print(f"成功加载 {len(self.mapping_dict)} 个测点映射")
            
        except Exception as e:
            print(f"加载KKS映射表失败: {e}")
            # 创建空的映射字典
            self.mapping_dict = {}
    
    def get_kks_mapping(self, sis_point_name):
        """获取SIS测点对应的KKS测点"""
        return self.mapping_dict.get(sis_point_name)
    
    def get_all_mappings(self):
        """获取所有映射"""
        return self.mapping_dict

class SISDataCollector:
    def __init__(self, base_url, username, password, data_callback=None):
        self.base_url = base_url.rstrip('/')
        self.username = username
        self.password = password
        self.session = requests.Session()
        self.token = None
        self.is_logged_in = False
        self.data_callback = data_callback  
        
        # 初始化KKS映射器
        project_root = os.path.dirname(os.path.abspath(__file__))
        cor_kks_path = os.path.join(project_root, 'Cor_kks.xls')
        self.kks_mapper = KKSMapper(cor_kks_path)
        
        # 设置真实的浏览器请求头
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def decode_base64(self, encoded_str):
        """解码base64字符串"""
        try:
            # 添加可能缺失的填充
            padding = 4 - len(encoded_str) % 4
            if padding != 4:
                encoded_str += "=" * padding
            decoded = base64.b64decode(encoded_str).decode('utf-8')
            return decoded
        except Exception as e:
            logger.error(f"Base64解码失败: {e}")
            return encoded_str
    
    def get_login_page(self):
        """获取登录页面并提取必要信息"""
        login_url = f"{self.base_url}/login.html"
        
        try:
            response = self.session.get(login_url)
            response.raise_for_status()
            
            logger.info("成功获取登录页面")
            
            # 检查是否有重定向
            if response.history:
                logger.info(f"发生了重定向: {response.url}")
            
            # 尝试从响应中提取token或其他认证信息
            content = response.text
            
            # 检查是否有错误信息
            if "503" in content or "Service Unavailable" in content:
                logger.error("服务器返回503错误")
                return False
            
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"获取登录页面失败: {e}")
            return False
    
    def try_direct_access(self):
        """尝试直接访问数据API"""
        # 首先尝试访问主页，看是否已经自动登录
        main_url = f"{self.base_url}/index.html"
        
        try:
            response = self.session.get(main_url)
            response.raise_for_status()
            
            if "login" not in response.url.lower():
                logger.info("可能已经处于登录状态")
                return True
            else:
                logger.info("需要登录")
                return False
                
        except requests.exceptions.RequestException as e:
            logger.error(f"访问主页失败: {e}")
            return False
    
    def try_js_login_simulation(self):
        """尝试模拟JavaScript登录逻辑"""
        # 从源代码中看到，系统检查sessionStorage中的认证信息
        # 我们尝试直接设置这些值来模拟登录状态
        
        # 访问主页前先设置一些必要的cookie或header
        self.session.headers.update({
            'Referer': f'{self.base_url}/login.html',
            'Origin': self.base_url
        })
        
        # 尝试访问主页
        main_url = f"{self.base_url}/index.html"
        
        try:
            response = self.session.get(main_url)
            
            # 检查是否被重定向到登录页
            if "login" in response.url:
                logger.info("被重定向到登录页面，需要认证")
                return False
            else:
                logger.info("成功访问主页")
                return True
                
        except requests.exceptions.RequestException as e:
            logger.error(f"访问主页失败: {e}")
            return False
    
    def try_alternative_login_endpoints(self):
        """尝试其他可能的登录端点"""
        endpoints = [
            "/api/Account/Login",
            "/api/auth/login",
            "/api/user/login",
            "/TokenAuth/Authenticate",
            "/api/authenticate",
            "/login"
        ]
        
        login_data = {
            "userNameOrEmailAddress": self.username,
            "password": self.password,
            "username": self.username,
            "password": self.password,
            "rememberMe": True,
            "rememberClient": True
        }
        
        for endpoint in endpoints:
            login_url = f"{self.base_url}{endpoint}"
            logger.info(f"尝试登录端点: {endpoint}")
            
            try:
                # 尝试JSON格式
                response = self.session.post(
                    login_url, 
                    json=login_data,
                    headers={'Content-Type': 'application/json'}
                )
                
                if response.status_code == 200:
                    try:
                        result = response.json()
                        if result.get('success') or 'token' in result or 'accessToken' in result:
                            logger.info(f"登录成功于: {endpoint}")
                            self.token = result.get('accessToken') or result.get('token')
                            if self.token:
                                self.session.headers.update({
                                    'Authorization': f'Bearer {self.token}'
                                })
                            self.is_logged_in = True
                            return True
                    except:
                        pass
                
                # 尝试表单格式
                response = self.session.post(
                    login_url,
                    data=login_data
                )
                
                if response.status_code == 200:
                    logger.info(f"表单登录可能成功于: {endpoint}")
                    self.is_logged_in = True
                    return True
                    
            except requests.exceptions.RequestException as e:
                logger.warning(f"端点 {endpoint} 失败: {e}")
                continue
        
        return False
    
    def login(self):
        """综合登录方法"""
        logger.info("开始登录流程...")
        
        # 1. 首先获取登录页面
        if not self.get_login_page():
            logger.error("无法获取登录页面")
            return False
        
        # 2. 尝试直接访问（可能已有session）
        if self.try_direct_access():
            self.is_logged_in = True
            logger.info("通过直接访问登录成功")
            return True
        
        # 3. 尝试JavaScript模拟登录
        if self.try_js_login_simulation():
            self.is_logged_in = True
            logger.info("通过JS模拟登录成功")
            return True
        
        # 4. 尝试各种登录端点
        if self.try_alternative_login_endpoints():
            logger.info("通过API端点登录成功")
            return True
        
        logger.error("所有登录方法都失败了")
        return False
    
    def get_tag_data(self):
        """获取测点数据"""
        if not self.is_logged_in:
            logger.error("请先登录")
            return None
        
        # 使用新的URL
        tag_url = f"{self.base_url}/luculent-liems-sis/api/services/realdb/TagInfo/GetTagInfosWithValueByNameList"
        
        # 从映射表中获取所有SIS测点名称
        mapping_dict = self.kks_mapper.get_all_mappings()
        sis_point_names = list(mapping_dict.keys())
        
        if not sis_point_names:
            logger.error("没有找到映射的测点名称")
            return None
        
        # 尝试使用常见的属性名包装测点名称列表
        payload_options = [
            {"tagNames": sis_point_names},
            {"names": sis_point_names},
            {"tagNameList": sis_point_names},
            {"nameList": sis_point_names},
            {"tags": sis_point_names},
            {"points": sis_point_names}
        ]
        
        # 添加必要的headers
        headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
            'sis-language': 'zh-Hans',
            'Referer': f'{self.base_url}/luculent-liems-sis/app/sis/query/tag-query-list/index.html'
        }
        
        # 尝试不同的payload格式
        for payload in payload_options:
            logger.info(f"尝试payload格式: {list(payload.keys())[0]}")
            
            try:
                response = self.session.post(tag_url, json=payload, headers=headers)
                logger.info(f"请求状态码: {response.status_code}")
                
                if response.status_code == 200:
                    result = response.json()
                    if result.get('success'):
                        items = result['result']['items']
                        logger.info(f"成功获取 {len(items)} 个测点数据")
                        
                        # 触发数据回调
                        if self.data_callback:
                            kks_data = self.convert_to_kks_format(items)
                            callback_data = {
                                'timestamp': datetime.now().isoformat(),
                                'data_points': kks_data,
                                'source': 'REAL_SIS'
                            }
                            self.data_callback(callback_data)
                        
                        return items
                    else:
                        logger.error(f"API返回失败: {result.get('error', '未知错误')}")
                elif response.status_code == 400:
                    # 继续尝试下一个payload格式
                    continue
                else:
                    logger.error(f"HTTP错误: {response.status_code} - {response.text}")
                    
            except requests.exceptions.RequestException as e:
                logger.error(f"数据请求失败: {e}")
            except json.JSONDecodeError as e:
                logger.error(f"JSON解析失败: {e}")
                logger.error(f"响应内容: {response.text[:200]}...")
        
        logger.error("所有payload格式都失败了")
        return None
    
    def convert_to_kks_format(self, tag_items):
        """将SIS测点数据转换为KKS格式"""
        kks_data = {}
        unmapped_points = []
        
        for tag in tag_items:
            sis_point_name = tag.get('name', '')
            mapping = self.kks_mapper.get_kks_mapping(sis_point_name)
            
            if mapping:
                kks_point = mapping['kks']
                try:
                    # 尝试将值转换为浮点数
                    value = float(tag.get('value', 0))
                    kks_data[kks_point] = value
                except (ValueError, TypeError):
                    logger.warning(f"无法转换测点值: {sis_point_name} -> {tag.get('value')}")
            else:
                unmapped_points.append(sis_point_name)
        
        if unmapped_points:
            logger.warning(f"发现 {len(unmapped_points)} 个未映射的测点: {unmapped_points[:5]}...")
        
        return kks_data
    
    def display_data(self, tag_items, kks_data):
        """显示测点数据"""
        if not tag_items:
            print("无数据可显示")
            return
        
        print("\n" + "="*120)
        print(f"{'SIS测点名称':<35} {'KKS测点':<25} {'描述':<20} {'当前值':<15} {'单位':<10} {'更新时间':<20}")
        print("="*120)
        
        for tag in tag_items:
            sis_name = tag.get('name', '')[:33]
            mapping = self.kks_mapper.get_kks_mapping(sis_name)
            kks_point = mapping['kks'] if mapping else "未映射"
            desc = tag.get('desc', '')[:18]
            value = str(tag.get('value', ''))[:13]
            unit = tag.get('unit', '')[:8]
            timestamp = tag.get('timeStamp', '')[:18]
            
            print(f"{sis_name:<35} {kks_point:<25} {desc:<20} {value:<15} {unit:<10} {timestamp:<20}")
        
        print("="*120)
        print(f"总计: {len(tag_items)} 个SIS测点 -> {len(kks_data)} 个KKS测点")

def main():
    # 配置信息
    BASE_URL = "http://59.51.82.42:8880"
    USERNAME = "049"
    PASSWORD = "Hdw19951125"
    
    # 创建数据收集器
    collector = SISDataCollector(BASE_URL, USERNAME, PASSWORD)
    
    try:
        # 尝试登录
        if collector.login():
            print("登录成功！")
            
            # 获取测点数据
            print("获取测点数据...")
            tag_items = collector.get_tag_data()
            
            if tag_items:
                # 转换为KKS格式
                kks_data = collector.convert_to_kks_format(tag_items)
                
                # 显示数据
                collector.display_data(tag_items, kks_data)
                
                # 询问是否持续监控
                choice = input("\n是否开始持续监控? (y/n): ").lower()
                if choice == 'y':
                    interval = 5
                    try:
                        interval_input = input("请输入刷新间隔(秒，默认5): ")
                        interval = int(interval_input) if interval_input else 5
                    except:
                        interval = 5
                    
                    print(f"\n开始持续监控，每 {interval} 秒刷新一次...")
                    print("按 Ctrl+C 停止")
                    
                    try:
                        while True:
                            print(f"\n{'-'*50}")
                            print(f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            print(f"{'-'*50}")
                            
                            tag_items = collector.get_tag_data()
                            if tag_items:
                                kks_data = collector.convert_to_kks_format(tag_items)
                                collector.display_data(tag_items, kks_data)
                            
                            time.sleep(interval)
                    except KeyboardInterrupt:
                        print("\n监控已停止")
            else:
                print("获取数据失败")
        else:
            print("登录失败，请检查：")
            print("1. 网络连接")
            print("2. 服务器状态")
            print("3. 用户名和密码")
            print("4. 尝试直接在浏览器中访问系统")
            
    except Exception as e:
        logger.error(f"程序执行出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
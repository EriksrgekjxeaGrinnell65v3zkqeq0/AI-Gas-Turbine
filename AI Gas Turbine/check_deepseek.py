import requests
import json
import sys

def check_deepseek_health():
    """检查DeepSeek服务健康状态"""
    print("DeepSeek服务健康检查...")
    
    try:
        # 检查Ollama服务
        url = "http://localhost:11434/api/tags"
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            models = response.json()
            print("✓ Ollama服务运行正常")
            print("已加载的模型:")
            for model in models.get('models', []):
                print(f"  - {model['name']}")
            
            # 检查DeepSeek模型是否在列表中
            deepseek_loaded = any('deepseek-r1:14b' in model['name'] for model in models.get('models', []))
            
            if deepseek_loaded:
                print("✓ DeepSeek模型已加载")
                
                # 测试模型响应
                test_prompt = "请用一句话回答：你好"
                generate_url = "http://localhost:11434/api/generate"
                payload = {
                    "model": "deepseek-r1:14b",
                    "prompt": test_prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.1,
                        "num_predict": 50
                    }
                }
                
                print("测试模型响应...")
                response = requests.post(generate_url, json=payload, timeout=30)
                
                if response.status_code == 200:
                    result = response.json()
                    print("模型响应测试成功!")
                    print(f"响应: {result.get('response', '无响应')}")
                    return True
                else:
                    print(f"模型响应测试失败: {response.status_code}")
                    return False
            else:
                print("DeepSeek模型未加载，请运行: ollama run deepseek-r1:14b")
                return False
        else:
            print(f"Ollama服务检查失败: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"DeepSeek健康检查失败: {e}")
        return False

if __name__ == "__main__":
    if check_deepseek_health():
        print("\nDeepSeek服务状态正常")
        sys.exit(0)
    else:
        print("\nDeepSeek服务存在问题")
        sys.exit(1)
"""
AI Adapter 测试脚本
测试 DeepSeek API 集成和代码生成功能
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent.ai_adapter import AIAdapter, AIConfig
import logging


def test_basic_config():
    """测试基础配置"""
    print("\n=== 测试1: 基础配置 ===")
    
    # 测试默认配置
    adapter = AIAdapter()
    print(f"✓ 默认配置加载成功")
    print(f"  Provider: {adapter.config.provider}")
    print(f"  Model: {adapter.config.model}")
    print(f"  API Base: {adapter.config.api_base}")
    print(f"  Max Tokens: {adapter.config.max_tokens}")
    
    # 测试自定义配置
    custom_config = AIConfig(
        api_key="test_key",
        model="deepseek-reasoner",
        max_tokens=3000
    )
    adapter2 = AIAdapter(custom_config)
    print(f"✓ 自定义配置加载成功")
    print(f"  Max Tokens: {adapter2.config.max_tokens}")


def test_prompt_building():
    """测试提示词构建"""
    print("\n=== 测试2: 提示词构建 ===")
    
    adapter = AIAdapter()
    
    # 测试基础提示词
    prompt1 = adapter._build_code_generation_prompt(
        "读取文本文件",
        None
    )
    print(f"✓ 基础提示词构建成功")
    print(f"  长度: {len(prompt1)} 字符")
    
    # 测试带上下文的提示词
    context = {
        "existing_capabilities": [
            {"name": "file_reader", "description": "读取文件"},
            {"name": "data_parser", "description": "解析数据"}
        ]
    }
    prompt2 = adapter._build_code_generation_prompt(
        "统计文件行数",
        context
    )
    print(f"✓ 带上下文提示词构建成功")
    print(f"  长度: {len(prompt2)} 字符")
    print(f"  包含上下文: {'existing_capabilities' in str(context)}")


def test_response_parsing():
    """测试响应解析"""
    print("\n=== 测试3: 响应解析 ===")
    
    adapter = AIAdapter()
    
    # 测试标准JSON格式
    test_response1 = '''```json
{
  "description": "读取文本文件",
  "entry_function": "read_file",
  "dependencies": [],
  "code": "def read_file(path: str):\\n    pass"
}
```'''
    
    try:
        result1 = adapter._parse_code_response(test_response1)
        print(f"✓ 标准JSON格式解析成功")
        print(f"  Entry Function: {result1['entry_function']}")
        print(f"  Description: {result1['description']}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")
    
    # 测试纯JSON格式
    test_response2 = '''{
  "description": "计算文件大小",
  "entry_function": "get_file_size",
  "dependencies": ["os"],
  "code": "import os\\ndef get_file_size(path): return os.path.getsize(path)"
}'''
    
    try:
        result2 = adapter._parse_code_response(test_response2)
        print(f"✓ 纯JSON格式解析成功")
        print(f"  Entry Function: {result2['entry_function']}")
        print(f"  Dependencies: {result2['dependencies']}")
    except Exception as e:
        print(f"✗ 解析失败: {e}")


def test_api_call():
    """测试实际API调用（需要有效的API密钥）"""
    print("\n=== 测试4: 实际API调用 ===")
    
    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    
    if not api_key:
        print("⚠️  跳过实际API调用测试（未设置DEEPSEEK_API_KEY）")
        print("   如需测试，请运行:")
        print("   Windows: set DEEPSEEK_API_KEY=your_key")
        print("   Linux/Mac: export DEEPSEEK_API_KEY=your_key")
        return
    
    print(f"✓ API密钥已设置")
    print(f"  开始调用 DeepSeek API...")
    
    adapter = AIAdapter()
    
    # 测试简单的代码生成
    result = adapter.generate_code(
        "创建一个函数，接收一个字符串，返回字符串的长度"
    )
    
    if result["success"]:
        print(f"✓ API调用成功")
        print(f"  功能描述: {result['description']}")
        print(f"  入口函数: {result['entry_function']}")
        print(f"  依赖库: {result['dependencies']}")
        print(f"  代码预览 (前200字符):")
        print(f"  {'-'*60}")
        print(f"  {result['code'][:200]}...")
        print(f"  {'-'*60}")
    else:
        print(f"✗ API调用失败")
        print(f"  错误: {result['error']}")


def test_error_handling():
    """测试错误处理"""
    print("\n=== 测试5: 错误处理 ===")
    
    # 测试无效API密钥
    config = AIConfig(api_key="invalid_key")
    adapter = AIAdapter(config)
    
    result = adapter.generate_code("测试功能")
    
    if not result["success"]:
        print(f"✓ 正确处理无效API密钥")
        print(f"  错误信息: {result['error'][:100]}...")
    else:
        print(f"⚠️  未能检测到无效API密钥")


def main():
    """运行所有测试"""
    print("="*70)
    print("AI Adapter 测试套件")
    print("="*70)
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    try:
        test_basic_config()
        test_prompt_building()
        test_response_parsing()
        test_error_handling()
        test_api_call()  # 最后测试，因为需要真实API调用
        
        print("\n" + "="*70)
        print("✓ 所有测试完成")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

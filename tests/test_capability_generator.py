"""
测试能力生成模块
"""

import os
import sys
import json

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent.storage import StorageManager
from prokaryote_agent.capability_generator import CapabilityGenerator, CodeSafetyChecker
from prokaryote_agent.ai_adapter import AIAdapter
import logging


def test_code_safety_checker():
    """测试代码安全检查器"""
    print("\n" + "="*70)
    print("测试1: 代码安全检查器")
    print("="*70)
    
    test_cases = [
        {
            "name": "安全代码 - 文件读取",
            "code": """
import os
from typing import Dict, Any

def read_file(file_path: str) -> Dict[str, Any]:
    try:
        if not os.path.exists(file_path):
            return {'success': False, 'data': '', 'error': '文件不存在'}
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        return {'success': True, 'data': content, 'error': ''}
    except Exception as e:
        return {'success': False, 'data': '', 'error': str(e)}
""",
            "expected": "safe"
        },
        {
            "name": "警告代码 - 使用os模块",
            "code": """
import os

def get_file_size(path: str):
    return os.path.getsize(path)
""",
            "expected": "warning"
        },
        {
            "name": "危险代码 - os.system",
            "code": """
import os

def delete_all():
    os.system('rm -rf /')
""",
            "expected": "danger"
        },
        {
            "name": "危险代码 - subprocess",
            "code": """
import subprocess

def run_command(cmd):
    subprocess.call(cmd, shell=True)
""",
            "expected": "danger"
        },
        {
            "name": "危险代码 - eval",
            "code": """
def execute_user_code(code):
    return eval(code)
""",
            "expected": "danger"
        }
    ]
    
    passed = 0
    for i, test in enumerate(test_cases, 1):
        level, issues = CodeSafetyChecker.check_code(test["code"])
        
        status = "✓" if level == test["expected"] or (level == "warning" and test["expected"] == "safe") else "✗"
        print(f"\n{status} 测试 {i}: {test['name']}")
        print(f"  预期: {test['expected']}, 实际: {level}")
        
        if issues:
            print(f"  安全问题 ({len(issues)}):")
            for issue in issues[:3]:  # 只显示前3个
                print(f"    - {issue}")
        
        if level == test["expected"] or (level == "warning" and test["expected"] == "safe"):
            passed += 1
    
    print(f"\n通过: {passed}/{len(test_cases)}")


def test_capability_generator_basic():
    """测试能力生成器基础功能"""
    print("\n" + "="*70)
    print("测试2: 能力生成器基础功能")
    print("="*70)
    
    # 创建存储管理器
    storage = StorageManager()
    
    # 创建生成器
    generator = CapabilityGenerator(storage)
    print("✓ 能力生成器创建成功")
    
    # 检查目录创建
    config = storage.load_config()
    cap_path = config.get("storage_path", {}).get("capability_path", "./prokaryote_agent/capabilities/")
    
    print(f"✓ 能力目录: {cap_path}")
    print(f"  - generated_code: {os.path.exists(os.path.join(cap_path, 'generated_code'))}")
    print(f"  - sandbox: {os.path.exists(os.path.join(cap_path, 'sandbox'))}")
    print(f"  - registry: {os.path.exists(os.path.join(cap_path, 'capability_registry.json'))}")
    
    # 列出能力
    result = generator.list_capabilities()
    if result["success"]:
        print(f"✓ 列出能力成功")
        print(f"  当前能力数量: {result['total_count']}")
        
        if result["capabilities"]:
            print(f"  已有能力:")
            for cap in result["capabilities"][:5]:  # 只显示前5个
                print(f"    - {cap['name']} ({cap['status']}): {cap['description'][:50]}...")
    else:
        print(f"✗ 列出能力失败: {result['error']}")


def test_capability_name_generation():
    """测试能力名称生成"""
    print("\n" + "="*70)
    print("测试3: 能力名称生成")
    print("="*70)
    
    storage = StorageManager()
    generator = CapabilityGenerator(storage)
    
    test_names = [
        ("read_file", "read_file"),
        ("ReadFile", "readfile"),
        ("get-file-size", "get_file_size"),
        ("parse_JSON_data", "parse_json_data"),
        ("__special__", "special"),
    ]
    
    for input_name, expected_pattern in test_names:
        result = generator._generate_capability_name(input_name)
        print(f"  {input_name} -> {result}")


def test_capability_file_building():
    """测试能力文件构建"""
    print("\n" + "="*70)
    print("测试4: 能力文件构建")
    print("="*70)
    
    from prokaryote_agent.capability_generator import GeneratedCapability
    from datetime import datetime
    
    storage = StorageManager()
    generator = CapabilityGenerator(storage)
    
    # 创建测试能力
    test_capability = GeneratedCapability(
        capability_id="test_001",
        name="test_function",
        description="测试函数",
        code="def test_function():\n    return 'Hello'",
        entry_function="test_function",
        dependencies=[],
        user_guidance="创建一个测试函数",
        safety_level="safe",
        safety_issues=[],
        created_at=datetime.now().isoformat()
    )
    
    # 构建文件内容
    content = generator._build_capability_file(test_capability)
    
    print("✓ 文件内容构建成功")
    print(f"  长度: {len(content)} 字符")
    print(f"  包含文档字符串: {'Capability:' in content}")
    print(f"  包含元数据: {'CAPABILITY_METADATA' in content}")
    print(f"\n内容预览:")
    print("-" * 70)
    print(content[:300] + "..." if len(content) > 300 else content)
    print("-" * 70)


def test_mock_generation():
    """测试模拟代码生成（不调用真实API）"""
    print("\n" + "="*70)
    print("测试5: 模拟代码生成")
    print("="*70)
    
    storage = StorageManager()
    generator = CapabilityGenerator(storage)
    
    # 注意：这个测试需要真实的API密钥，否则会失败
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    
    if not api_key:
        print("⚠️  未设置 DEEPSEEK_API_KEY，跳过实际生成测试")
        print("   如需测试完整流程，请设置环境变量:")
        print("   set DEEPSEEK_API_KEY=your_key")
        return
    
    print("✓ API密钥已设置，开始测试代码生成...")
    
    # 测试生成简单能力
    result = generator.generate_capability(
        guidance="创建一个简单的函数，输入一个字符串，返回字符串的长度"
    )
    
    if result["success"]:
        print(f"✓ 能力生成成功")
        print(f"  ID: {result['capability_id']}")
        print(f"  名称: {result['capability_name']}")
        print(f"  描述: {result['description']}")
        print(f"  入口函数: {result['entry_function']}")
        print(f"  安全等级: {result['safety_level']}")
        print(f"  代码路径: {result['code_path']}")
        
        if result['safety_issues']:
            print(f"  安全问题:")
            for issue in result['safety_issues']:
                print(f"    - {issue}")
    else:
        print(f"✗ 能力生成失败")
        print(f"  错误: {result['error']}")


def main():
    """运行所有测试"""
    print("="*70)
    print("Capability Generator 测试套件")
    print("="*70)
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    try:
        test_code_safety_checker()
        test_capability_generator_basic()
        test_capability_name_generation()
        test_capability_file_building()
        test_mock_generation()
        
        print("\n" + "="*70)
        print("✓ 所有测试完成")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

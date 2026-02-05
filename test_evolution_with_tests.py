#!/usr/bin/env python3
"""测试进化功能中的测试生成和验证"""

import sys
sys.path.insert(0, '.')

from prokaryote_agent.ai_adapter import AIAdapter, AIConfig
from prokaryote_agent.storage import StorageManager
from prokaryote_agent.capability_generator import CapabilityGenerator

def test_test_generation():
    """测试AI生成测试功能"""
    print("=" * 60)
    print("测试1: AI测试生成功能")
    print("=" * 60)
    
    storage = StorageManager()
    config_result = storage.load_config()
    config = config_result.get('config', {})
    cap_config = config.get('capability_config', {})
    
    print(f"API Key: {cap_config.get('api_key', '')[:10]}...")
    
    # 创建AI适配器
    ai_config = AIConfig(
        api_key=cap_config.get('api_key', ''),
        model=cap_config.get('model', 'deepseek-reasoner'),
        api_base=cap_config.get('base_url', 'https://api.deepseek.com/v1'),
        max_tokens=cap_config.get('max_tokens', 8000)
    )
    adapter = AIAdapter(ai_config)
    
    # 测试代码
    test_code = '''
def reverse_string(s: str) -> dict:
    """反转字符串"""
    if not isinstance(s, str):
        return {"success": False, "error": "Input must be a string", "result": ""}
    return {"success": True, "error": "", "result": s[::-1]}
'''
    
    print("\n原始代码:")
    print(test_code)
    
    # 生成测试
    print("\n开始生成测试...")
    result = adapter.generate_tests(test_code, 'reverse_string', '字符串反转函数')
    
    print(f"\n测试生成结果: {'成功' if result['success'] else '失败'}")
    
    if result['success']:
        print(f"测试代码长度: {len(result['test_code'])}")
        print(f"测试用例数: {len(result['test_cases'])}")
        print("\n--- 测试用例描述 ---")
        for i, case in enumerate(result['test_cases'], 1):
            print(f"  {i}. {case}")
        print("\n--- 测试代码 ---")
        print(result['test_code'][:800] + "..." if len(result['test_code']) > 800 else result['test_code'])
    else:
        print(f"错误: {result['error']}")
    
    return result['success']

def test_sandbox_execution():
    """测试沙箱执行功能"""
    print("\n" + "=" * 60)
    print("测试2: 沙箱测试执行")
    print("=" * 60)
    
    storage = StorageManager()
    config_result = storage.load_config()
    config = config_result.get('config', {})
    cap_config = config.get('capability_config', {})
    
    ai_config = AIConfig(
        api_key=cap_config.get('api_key', ''),
        model=cap_config.get('model', 'deepseek-reasoner'),
        api_base=cap_config.get('base_url', 'https://api.deepseek.com/v1'),
        max_tokens=cap_config.get('max_tokens', 8000)
    )
    
    generator = CapabilityGenerator(storage, ai_config)
    
    # 测试代码
    capability_code = '''
def reverse_string(s: str) -> dict:
    """反转字符串"""
    if not isinstance(s, str):
        return {"success": False, "error": "Input must be a string", "result": ""}
    return {"success": True, "error": "", "result": s[::-1]}
'''
    
    # 简单的测试代码
    test_code = '''
def test_normal_case():
    """测试正常情况"""
    result = reverse_string("hello")
    assert result["success"] == True
    assert result["result"] == "olleh"

def test_empty_string():
    """测试空字符串"""
    result = reverse_string("")
    assert result["success"] == True
    assert result["result"] == ""

def test_invalid_input():
    """测试无效输入"""
    result = reverse_string(123)
    assert result["success"] == False

def run_tests():
    """运行所有测试"""
    results = []
    test_funcs = [test_normal_case, test_empty_string, test_invalid_input]
    for test_func in test_funcs:
        try:
            test_func()
            results.append({"name": test_func.__name__, "passed": True, "error": ""})
        except AssertionError as e:
            results.append({"name": test_func.__name__, "passed": False, "error": str(e)})
        except Exception as e:
            results.append({"name": test_func.__name__, "passed": False, "error": str(e)})
    return results
'''
    
    print("\n执行沙箱测试...")
    results = generator._execute_tests_in_sandbox(capability_code, test_code)
    
    print(f"\n测试结果: {len(results)} 个测试")
    passed = 0
    for r in results:
        status = "✓" if r['passed'] else "✗"
        print(f"  {status} {r['name']}: {'通过' if r['passed'] else r['error']}")
        if r['passed']:
            passed += 1
    
    print(f"\n总计: {passed}/{len(results)} 通过")
    return passed == len(results)

def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("  进化测试验证功能 - 单元测试")
    print("=" * 60 + "\n")
    
    # 先测试沙箱执行（不需要API调用）
    sandbox_ok = test_sandbox_execution()
    
    # 再测试AI测试生成（需要API调用）
    if sandbox_ok:
        print("\n沙箱测试通过，继续测试AI生成...")
        ai_ok = test_test_generation()
        
        # 如果AI生成也通过，测试完整的进化流程
        if ai_ok:
            print("\nAI测试生成通过，测试完整进化流程...")
            evolution_ok = test_full_evolution()
        else:
            evolution_ok = False
    else:
        ai_ok = False
        evolution_ok = False

    print("\n" + "=" * 60)
    print("  测试总结")
    print("=" * 60)
    print(f"  沙箱执行: {'✓ 通过' if sandbox_ok else '✗ 失败'}")
    print(f"  AI测试生成: {'✓ 通过' if ai_ok else '✗ 失败'}")
    print(f"  完整进化: {'✓ 通过' if evolution_ok else '✗ 失败'}")
    print("=" * 60)
    
    return 0 if (sandbox_ok and ai_ok and evolution_ok) else 1


def test_full_evolution():
    """测试完整的进化流程（生成能力+生成测试+执行测试）"""
    print("\n" + "=" * 60)
    print("测试3: 完整进化流程")
    print("=" * 60)
    
    storage = StorageManager()
    config_result = storage.load_config()
    config = config_result.get('config', {})
    cap_config = config.get('capability_config', {})
    
    ai_config = AIConfig(
        api_key=cap_config.get('api_key', ''),
        model=cap_config.get('model', 'deepseek-reasoner'),
        api_base=cap_config.get('base_url', 'https://api.deepseek.com/v1'),
        max_tokens=cap_config.get('max_tokens', 8000)
    )
    
    # 创建AIAdapter，然后传给CapabilityGenerator
    ai_adapter = AIAdapter(ai_config)
    generator = CapabilityGenerator(storage, ai_adapter)
    
    # 执行进化
    print("\n开始进化: 生成一个计算两个数之和的函数...")
    result = generator.generate_capability("创建一个简单的加法函数，接收两个数字参数，返回它们的和")
    
    print(f"\n进化结果: {'成功' if result['success'] else '失败'}")
    
    if result['success']:
        print(f"  能力ID: {result.get('capability_id', 'N/A')}")
        print(f"  能力名称: {result.get('capability_name', 'N/A')}")
        print(f"  测试通过: {result.get('test_passed', False)}")
        print(f"  代码路径: {result.get('code_path', 'N/A')}")
        print(f"  测试结果: {result.get('test_results', [])}")
        return True
    else:
        print(f"  错误: {result.get('error', 'N/A')}")
        print(f"  消息: {result.get('message', 'N/A')}")
        if 'test_results' in result:
            print(f"  测试结果: {result.get('test_results', [])}")
        return False


if __name__ == "__main__":
    sys.exit(main())
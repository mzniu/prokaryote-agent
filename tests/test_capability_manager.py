"""
测试能力管理器
"""

import os
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent.storage import StorageManager
from prokaryote_agent.capability_manager import CapabilityManager
import logging


def test_basic_operations():
    """测试基础操作"""
    print("\n" + "="*70)
    print("测试1: 能力管理器基础操作")
    print("="*70)
    
    storage = StorageManager()
    manager = CapabilityManager(storage)
    
    print("✓ 能力管理器创建成功")
    
    # 列出能力
    result = manager.list_capabilities()
    
    if result["success"]:
        print(f"\n✓ 能力统计:")
        print(f"  总数: {result['total_count']}")
        print(f"  启用: {result['enabled_count']}")
        print(f"  禁用: {result['disabled_count']}")
        
        if result["capabilities"]:
            print(f"\n  能力列表 (前5个):")
            for cap in result["capabilities"][:5]:
                status_icon = "✓" if cap['status'] == 'enabled' else "✗"
                print(f"    {status_icon} {cap['name']}")
                print(f"       ID: {cap['id']}")
                print(f"       状态: {cap['status']}")
                print(f"       描述: {cap['description'][:60]}...")
                
                perf = cap.get('performance', {})
                if perf.get('total_invocations', 0) > 0:
                    print(f"       性能: 平均{perf['avg_execution_time_ms']:.2f}ms, " +
                          f"成功率{perf['success_rate']*100:.1f}%")
                print()
        else:
            print("\n  (暂无能力)")
    else:
        print(f"✗ 列出能力失败: {result['error']}")


def test_capability_status():
    """测试能力状态管理"""
    print("\n" + "="*70)
    print("测试2: 能力状态管理")
    print("="*70)
    
    storage = StorageManager()
    manager = CapabilityManager(storage)
    
    # 获取第一个能力
    result = manager.list_capabilities()
    
    if result["success"] and result["total_count"] > 0:
        cap = result["capabilities"][0]
        cap_id = cap["id"]
        cap_name = cap["name"]
        
        print(f"测试能力: {cap_name} ({cap_id})")
        print(f"当前状态: {cap['status']}")
        
        # 测试启用/禁用
        if cap['status'] == 'disabled':
            print("\n尝试启用...")
            enable_result = manager.enable_capability(cap_id)
            if enable_result["success"]:
                print(f"✓ {enable_result['message']}")
            else:
                print(f"✗ {enable_result['error']}")
            
            # 再次禁用
            print("\n尝试禁用...")
            disable_result = manager.disable_capability(cap_id)
            if disable_result["success"]:
                print(f"✓ {disable_result['message']}")
        else:
            print("\n尝试禁用...")
            disable_result = manager.disable_capability(cap_id)
            if disable_result["success"]:
                print(f"✓ {disable_result['message']}")
            
            # 再次启用
            print("\n尝试启用...")
            enable_result = manager.enable_capability(cap_id)
            if enable_result["success"]:
                print(f"✓ {enable_result['message']}")
    else:
        print("⚠️  暂无能力可测试")


def test_capability_info():
    """测试获取能力信息"""
    print("\n" + "="*70)
    print("测试3: 获取能力详细信息")
    print("="*70)
    
    storage = StorageManager()
    manager = CapabilityManager(storage)
    
    result = manager.list_capabilities()
    
    if result["success"] and result["total_count"] > 0:
        cap = result["capabilities"][0]
        cap_id = cap["id"]
        
        info_result = manager.get_capability_info(cap_id)
        
        if info_result["success"]:
            cap_info = info_result["capability"]
            print(f"✓ 能力详情:")
            print(f"  名称: {cap_info['name']}")
            print(f"  ID: {cap_info['id']}")
            print(f"  版本: {cap_info['version']}")
            print(f"  状态: {cap_info['status']}")
            print(f"  描述: {cap_info['description']}")
            print(f"  入口函数: {cap_info['entry_function']}")
            print(f"  依赖: {cap_info['dependencies']}")
            print(f"  安全等级: {cap_info['safety_level']}")
            print(f"  创建时间: {cap_info['created_at']}")
            print(f"  代码路径: {cap_info['code_path']}")
            
            if cap_info.get('safety_issues'):
                print(f"  安全问题:")
                for issue in cap_info['safety_issues']:
                    print(f"    - {issue}")
        else:
            print(f"✗ 获取能力信息失败: {info_result['error']}")
    else:
        print("⚠️  暂无能力可查看")


def test_filter_by_status():
    """测试按状态过滤"""
    print("\n" + "="*70)
    print("测试4: 按状态过滤能力")
    print("="*70)
    
    storage = StorageManager()
    manager = CapabilityManager(storage)
    
    # 列出所有启用的能力
    enabled_result = manager.list_capabilities(status_filter="enabled")
    print(f"已启用能力: {enabled_result['total_count']} 个")
    for cap in enabled_result["capabilities"][:3]:
        print(f"  - {cap['name']}")
    
    # 列出所有禁用的能力
    disabled_result = manager.list_capabilities(status_filter="disabled")
    print(f"\n已禁用能力: {disabled_result['total_count']} 个")
    for cap in disabled_result["capabilities"][:3]:
        print(f"  - {cap['name']}")


def main():
    """运行所有测试"""
    print("="*70)
    print("Capability Manager 测试套件")
    print("="*70)
    
    # 配置日志
    logging.basicConfig(
        level=logging.INFO,
        format='[%(asctime)s] [%(levelname)s] %(message)s'
    )
    
    try:
        test_basic_operations()
        test_capability_info()
        test_filter_by_status()
        test_capability_status()
        
        print("\n" + "="*70)
        print("✓ 所有测试完成")
        print("="*70)
        
    except Exception as e:
        print(f"\n✗ 测试过程中出现异常: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()

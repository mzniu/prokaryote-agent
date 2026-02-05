"""
简单集成测试 - 验证核心功能
"""

import sys
import os
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import init_prokaryote, start_prokaryote, stop_prokaryote, query_prokaryote_state


def test_init():
    """测试初始化"""
    print("\n测试1: 初始化内核")
    result = init_prokaryote()
    assert result['success'], f"初始化失败: {result['msg']}"
    assert 'data' in result
    assert 'base_state' in result['data']
    print("✅ 初始化测试通过")
    return result


def test_start():
    """测试启动"""
    print("\n测试2: 启动内核")
    result = start_prokaryote()
    assert result['success'], f"启动失败: {result['msg']}"
    assert result['pid'] > 0
    print(f"✅ 启动测试通过 (PID: {result['pid']})")
    return result


def test_monitoring():
    """测试监控"""
    print("\n测试3: 状态监控")
    
    # 等待几秒，让监控模块运行
    print("等待5秒，观察监控...")
    for i in range(5):
        time.sleep(1)
        state = query_prokaryote_state()
        assert state['state'] in ['running', 'stopped'], f"状态异常: {state['state']}"
        print(f"  [{i+1}/5] 内存: {state['resource'].get('memory_mb', 0):.2f}MB, "
              f"CPU: {state['resource'].get('cpu_percent', 0):.2f}%")
    
    print("✅ 监控测试通过")


def test_stop():
    """测试停止"""
    print("\n测试4: 停止内核")
    result = stop_prokaryote()
    assert result['success'], f"停止失败: {result['msg']}"
    print("✅ 停止测试通过")
    return result


def test_query():
    """测试状态查询"""
    print("\n测试5: 状态查询")
    state = query_prokaryote_state()
    assert 'state' in state
    assert 'resource' in state
    assert 'repair_history' in state
    print(f"✅ 查询测试通过 (状态: {state['state']})")
    return state


def main():
    """运行所有测试"""
    print("=" * 60)
    print("prokaryote-agent V0.1 - 集成测试")
    print("=" * 60)
    
    try:
        # 运行测试
        test_init()
        test_start()
        test_monitoring()
        test_stop()
        test_query()
        
        print("\n" + "=" * 60)
        print("✅ 所有测试通过!")
        print("=" * 60)
        return True
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {str(e)}")
        # 确保清理
        try:
            stop_prokaryote()
        except:
            pass
        return False
        
    except Exception as e:
        print(f"\n❌ 测试异常: {str(e)}")
        import traceback
        traceback.print_exc()
        # 确保清理
        try:
            stop_prokaryote()
        except:
            pass
        return False


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)

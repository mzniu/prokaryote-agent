"""
Prokaryote Agent 完整演示
展示如何使用AI驱动的能力扩展功能，让Agent"自我进化"
"""

import os
import sys
import time

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import (
    init_prokaryote,
    start_prokaryote,
    stop_prokaryote,
    query_prokaryote_state,
    generate_capability,
    manage_capabilities,
    invoke_capability
)


def print_section(title: str):
    """打印章节标题"""
    print("\n" + "="*70)
    print(f"  {title}")
    print("="*70)


def demo_v01_basic():
    """演示V0.1基础功能：初始化、监控、修复"""
    print_section("第一部分：V0.1 基础功能演示")
    
    # 1. 初始化
    print("\n[1] 初始化 Prokaryote Agent...")
    result = init_prokaryote()
    
    if result['success']:
        print(f"✓ 初始化成功")
        print(f"  配置路径: {result['data'].get('config_path', 'N/A')}")
        print(f"  日志路径: {result['data'].get('log_path', 'N/A')}")
    else:
        print(f"✗ 初始化失败: {result['msg']}")
        return False
    
    # 2. 启动监控
    print("\n[2] 启动核心监控...")
    start_result = start_prokaryote()
    
    if start_result['success']:
        print(f"✓ 监控已启动")
        print(f"  监控间隔: 1秒")
        print(f"  PID: {start_result.get('pid', 'N/A')}")
    else:
        print(f"✗ 启动失败: {start_result['msg']}")
        return False
    
    # 3. 查询状态
    print("\n[3] 查询系统状态...")
    time.sleep(2)  # 等待监控数据
    
    state = query_prokaryote_state()
    print(f"  状态: {state['state']}")
    print(f"  内存: {state['resource'].get('memory_mb', 0):.2f} MB")
    print(f"  CPU: {state['resource'].get('cpu_percent', 0):.2f}%")
    print(f"  磁盘剩余: {state['resource'].get('disk_free_mb', 0):.0f} MB")
    
    return True


def demo_v02_evolution():
    """演示V0.2能力扩展：AI驱动的进化"""
    print_section("第二部分：V0.2 AI驱动的能力扩展")
    
    # 检查API密钥
    api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    
    if not api_key:
        print("\n⚠️  未设置 DEEPSEEK_API_KEY 环境变量")
        print("   V0.2 功能需要DeepSeek API密钥才能生成新能力")
        print("   请运行: set DEEPSEEK_API_KEY=your_api_key")
        print("\n   跳过能力生成演示，展示其他功能...")
        
        # 只展示列表功能
        print("\n[4] 列出现有能力...")
        list_result = manage_capabilities("list")
        
        if list_result["success"]:
            print(f"✓ 当前能力数量: {list_result['total_count']}")
            print(f"  启用: {list_result['enabled_count']}")
            print(f"  禁用: {list_result['disabled_count']}")
        
        return False
    
    print("\n✓ API密钥已设置，开始AI驱动的能力生成...")
    
    # 4. 生成第一个能力：文件读取
    print("\n[4] 生成能力 #1: 文件读取器")
    print("   用户指引: '创建一个读取文本文件的函数，支持UTF-8编码'")
    
    gen_result_1 = generate_capability(
        "创建一个读取文本文件的函数，支持UTF-8编码"
    )
    
    if gen_result_1["success"]:
        print(f"✓ 能力生成成功!")
        print(f"  ID: {gen_result_1['capability_id']}")
        print(f"  名称: {gen_result_1['capability_name']}")
        print(f"  描述: {gen_result_1['description']}")
        print(f"  入口函数: {gen_result_1['entry_function']}")
        print(f"  安全等级: {gen_result_1['safety_level']}")
        print(f"  代码路径: {gen_result_1['code_path']}")
        
        if gen_result_1.get('safety_issues'):
            print(f"  安全提示:")
            for issue in gen_result_1['safety_issues']:
                print(f"    - {issue}")
        
        cap1_id = gen_result_1['capability_id']
        cap1_name = gen_result_1['capability_name']
    else:
        print(f"✗ 生成失败: {gen_result_1['error']}")
        return False
    
    # 5. 生成第二个能力：数据统计
    print("\n[5] 生成能力 #2: 文本统计器")
    print("   用户指引: '创建一个统计文本中单词数量、行数的函数'")
    
    gen_result_2 = generate_capability(
        "创建一个统计文本中单词数量、行数的函数"
    )
    
    if gen_result_2["success"]:
        print(f"✓ 能力生成成功!")
        print(f"  ID: {gen_result_2['capability_id']}")
        print(f"  名称: {gen_result_2['capability_name']}")
        cap2_id = gen_result_2['capability_id']
    else:
        print(f"✗ 生成失败: {gen_result_2['error']}")
        cap2_id = None
    
    # 6. 列出所有能力
    print("\n[6] 查看所有已生成的能力...")
    list_result = manage_capabilities("list")
    
    if list_result["success"]:
        print(f"✓ 当前能力数量: {list_result['total_count']}")
        print(f"  启用: {list_result['enabled_count']}")
        print(f"  禁用: {list_result['disabled_count']}")
        
        print(f"\n  能力列表:")
        for cap in list_result["capabilities"]:
            status_icon = "✓" if cap['status'] == 'enabled' else "✗"
            print(f"    {status_icon} {cap['name']} ({cap['status']})")
            print(f"       {cap['description'][:60]}...")
    
    # 7. 启用第一个能力
    print(f"\n[7] 启用能力: {cap1_name}")
    enable_result = manage_capabilities("enable", capability_id=cap1_id)
    
    if enable_result["success"]:
        print(f"✓ {enable_result['message']}")
    else:
        print(f"✗ 启用失败: {enable_result['error']}")
        return False
    
    # 8. 创建测试文件并调用能力
    print(f"\n[8] 测试调用能力: {cap1_name}")
    
    # 创建测试文件
    test_file = "./prokaryote_agent/capabilities/test_input.txt"
    os.makedirs(os.path.dirname(test_file), exist_ok=True)
    
    with open(test_file, 'w', encoding='utf-8') as f:
        f.write("Hello, Prokaryote Agent!\n")
        f.write("This is a test file for capability demonstration.\n")
        f.write("AI-driven evolution is working!\n")
    
    print(f"  测试文件已创建: {test_file}")
    
    # 调用能力
    invoke_result = invoke_capability(
        cap1_name,
        {"file_path": test_file}
    )
    
    if invoke_result["success"]:
        print(f"✓ 能力调用成功!")
        print(f"  执行时间: {invoke_result['execution_time_ms']:.2f}ms")
        print(f"  内存使用: {invoke_result['memory_usage_mb']:.2f}MB")
        print(f"  返回数据:")
        
        data = invoke_result['data']
        if isinstance(data, dict):
            for key, value in data.items():
                if key == 'data' or key == 'content':
                    # 截断长文本
                    value_str = str(value)
                    if len(value_str) > 100:
                        value_str = value_str[:100] + "..."
                    print(f"    {key}: {value_str}")
                else:
                    print(f"    {key}: {value}")
        else:
            print(f"    {data}")
    else:
        print(f"✗ 调用失败: {invoke_result['error']}")
    
    # 9. 查看能力详情和性能数据
    print(f"\n[9] 查看能力详情和性能统计...")
    info_result = manage_capabilities("info", capability_id=cap1_id)
    
    if info_result["success"]:
        cap_info = info_result["capability"]
        print(f"✓ 能力详情:")
        print(f"  名称: {cap_info['name']}")
        print(f"  版本: {cap_info['version']}")
        print(f"  状态: {cap_info['status']}")
        print(f"  创建时间: {cap_info['created_at']}")
        
        perf = cap_info.get('performance', {})
        if perf.get('total_invocations', 0) > 0:
            print(f"\n  性能统计:")
            print(f"    总调用次数: {perf['total_invocations']}")
            print(f"    平均执行时间: {perf['avg_execution_time_ms']:.2f}ms")
            print(f"    平均内存使用: {perf['memory_usage_mb']:.2f}MB")
            print(f"    成功率: {perf['success_rate']*100:.1f}%")
    
    return True


def demo_cleanup():
    """清理和停止"""
    print_section("第三部分：清理")
    
    print("\n[10] 停止监控...")
    stop_result = stop_prokaryote()
    
    if stop_result['success']:
        print(f"✓ {stop_result['msg']}")
    else:
        print(f"  {stop_result['msg']}")
    
    print("\n✓ 演示完成!")


def main():
    """主函数"""
    print("="*70)
    print("  Prokaryote Agent - 完整功能演示")
    print("  V0.2: AI驱动的能力扩展")
    print("="*70)
    
    try:
        # V0.1 基础功能
        if not demo_v01_basic():
            print("\n✗ V0.1基础功能演示失败")
            return
        
        # 等待一下
        time.sleep(1)
        
        # V0.2 能力扩展
        demo_v02_evolution()
        
        # 等待一下
        time.sleep(1)
        
        # 清理
        demo_cleanup()
        
        print("\n" + "="*70)
        print("  🎉 Prokaryote Agent 已经学会自我进化!")
        print("  - 通过AI生成新能力")
        print("  - 在沙箱中安全测试")
        print("  - 性能自动监控")
        print("  - 持续优化迭代")
        print("="*70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        demo_cleanup()
    except Exception as e:
        print(f"\n✗ 演示过程中出现异常: {e}")
        import traceback
        traceback.print_exc()
        demo_cleanup()


if __name__ == "__main__":
    main()

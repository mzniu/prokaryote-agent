"""
长时间运行示例 - 测试内核稳定性
"""

import time
import signal
import sys
import os

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import init_prokaryote, start_prokaryote, stop_prokaryote, query_prokaryote_state


running = True


def signal_handler(sig, frame):
    """处理Ctrl+C信号"""
    global running
    print("\n\n接收到停止信号，正在停止内核...")
    running = False


def main():
    """长时间运行测试"""
    
    global running
    
    # 注册信号处理器
    signal.signal(signal.SIGINT, signal_handler)
    
    print("=" * 60)
    print("prokaryote-agent V0.1 - 长时间运行测试")
    print("=" * 60)
    print()
    
    # 初始化
    print("正在初始化内核...")
    result = init_prokaryote()
    if not result['success']:
        print(f"初始化失败: {result['msg']}")
        return
    print("✅ 初始化成功\n")
    
    # 启动
    print("正在启动内核...")
    result = start_prokaryote()
    if not result['success']:
        print(f"启动失败: {result['msg']}")
        return
    print(f"✅ 启动成功 (PID: {result['pid']})\n")
    
    # 运行
    print("内核正在运行，按 Ctrl+C 停止")
    print("状态将每30秒报告一次")
    print("-" * 60)
    print()
    
    start_time = time.time()
    last_report = start_time
    report_interval = 30  # 30秒报告一次
    
    while running:
        time.sleep(1)
        
        current_time = time.time()
        elapsed = current_time - start_time
        
        # 定期报告状态
        if current_time - last_report >= report_interval:
            state = query_prokaryote_state()
            
            print(f"\n[运行时间: {int(elapsed)}秒 / {elapsed/60:.1f}分钟]")
            print(f"  状态: {state['state']}")
            print(f"  内存: {state['resource'].get('memory_mb', 0):.2f} MB")
            print(f"  CPU: {state['resource'].get('cpu_percent', 0):.2f} %")
            print(f"  修复次数: {len(state.get('repair_history', []))}")
            
            # 如果有修复历史，显示最近一次
            repair_history = state.get('repair_history', [])
            if repair_history:
                last_repair = repair_history[-1]
                print(f"  最近修复: {last_repair.get('abnormal_type', 'unknown')} "
                      f"({last_repair.get('timestamp', 'unknown')})")
            
            print()
            last_report = current_time
    
    # 停止
    print("\n正在停止内核...")
    result = stop_prokaryote()
    if result['success']:
        print("✅ 内核已停止")
    
    # 最终报告
    total_time = time.time() - start_time
    print()
    print("=" * 60)
    print(f"总运行时间: {int(total_time)}秒 ({total_time/60:.2f}分钟)")
    
    final_state = query_prokaryote_state()
    repair_count = len(final_state.get('repair_history', []))
    print(f"总修复次数: {repair_count}")
    
    if repair_count > 0:
        success_count = sum(1 for r in final_state['repair_history'] if r.get('success', False))
        print(f"修复成功率: {success_count}/{repair_count} ({success_count/repair_count*100:.1f}%)")
    
    print("=" * 60)


if __name__ == "__main__":
    main()

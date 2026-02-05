"""
自动进化模式 - 无需交互，自动运行
读取 evolution_goals.md 并连续执行
"""

import sys
import time
import signal
from prokaryote_agent import (
    init_prokaryote,
    start_prokaryote,
    stop_prokaryote,
    generate_capability,
    manage_capabilities,
    EvolutionGoalManager
)

# 全局标志
running = True

def signal_handler(signum, frame):
    """处理Ctrl+C信号"""
    global running
    print("\n\n接收到中断信号，正在停止...")
    running = False

# 注册信号处理
signal.signal(signal.SIGINT, signal_handler)

def main():
    global running
    
    print("=" * 70)
    print("原智 (YuanZhi) - 自动进化模式")
    print("=" * 70)
    print()
    
    # 初始化
    print("[初始化] 正在启动系统...")
    init_result = init_prokaryote()
    if not init_result['success']:
        print(f"✗ 初始化失败: {init_result['msg']}")
        return 1
    
    start_result = start_prokaryote()
    if not start_result['success']:
        print(f"✗ 启动失败: {start_result['msg']}")
        return 1
    
    print("✓ 系统已启动")
    print()
    
    # 加载进化目标管理器
    goal_manager = EvolutionGoalManager()
    
    evolution_count = 0
    interval = 10  # 秒
    
    print(f"[配置]")
    print(f"  进化间隔: {interval} 秒")
    print(f"  目标文件: evolution_goals.md")
    print()
    print("=" * 70)
    print("开始自动进化循环 (按 Ctrl+C 停止)")
    print("=" * 70)
    print()
    
    while running:
        try:
            # 加载进化目标
            result = goal_manager.load_goals()
            if not result["success"]:
                print(f"⚠️  加载进化目标失败: {result['error']}")
                time.sleep(interval)
                continue
            
            goals = result["goals"]
            
            # 获取下一个待执行目标
            next_goal = goal_manager.get_next_goal()
            if not next_goal:
                print("\n🎉 所有进化目标都已完成！")
                print()
                
                # 显示统计
                stats = manage_capabilities("list")
                if stats["success"]:
                    print(f"最终统计:")
                    print(f"  总能力数: {stats['total_count']}")
                    print(f"  已启用: {stats['enabled_count']}")
                    print(f"  已禁用: {stats['disabled_count']}")
                    print(f"  进化次数: {evolution_count}")
                break
            
            # 显示当前目标
            print(f"\n{'='*70}")
            print(f"[进化 #{evolution_count + 1}] {next_goal.title}")
            print(f"{'='*70}")
            print(f"状态: {next_goal.status.value}")
            print(f"优先级: {next_goal.priority.value}")
            print(f"描述: {next_goal.description[:80]}...")
            print()
            
            # 生成指引
            guidance = goal_manager.generate_guidance_from_goal(next_goal)
            
            # 执行进化
            print("开始生成能力...")
            gen_result = generate_capability(guidance)
            
            if gen_result["success"]:
                evolution_count += 1
                print(f"\n✓ 进化成功！")
                print(f"  能力ID: {gen_result['capability_id']}")
                print(f"  能力名: {gen_result['capability_name']}")
                print(f"  描述: {gen_result['description']}")
                print(f"  安全等级: {gen_result['safety_level']}")
                
                if gen_result.get('safety_issues'):
                    print(f"  ⚠️  安全提示: {', '.join(gen_result['safety_issues'])}")
                
                # 标记完成
                goal_manager.mark_goal_completed(next_goal.title)
                print(f"  ✓ 目标已标记为完成")
                
                # 立即继续下一个目标（不等待）
                print(f"\n继续下一个目标...")
                time.sleep(2)
                
            else:
                print(f"\n✗ 进化失败: {gen_result.get('error', 'Unknown')}")
                print(f"\n等待 {interval} 秒后重试...")
                time.sleep(interval)
        
        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"\n✗ 异常: {e}")
            import traceback
            traceback.print_exc()
            print(f"\n等待 {interval} 秒后继续...")
            time.sleep(interval)
    
    # 清理
    print("\n正在停止系统...")
    stop_prokaryote()
    print("✓ 系统已停止")
    print()
    print("=" * 70)
    print("自动进化已结束")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)

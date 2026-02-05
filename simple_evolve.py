#!/usr/bin/env python3
"""
简化版自动进化脚本 - 专注于能力生成，不启动监测系统
"""
import sys
import time
import signal
from pathlib import Path

# 添加当前目录到 sys.path
sys.path.insert(0, str(Path(__file__).parent))

from prokaryote_agent.api import generate_capability
from prokaryote_agent.goal_manager import EvolutionGoalManager, GoalStatus

# 全局标志
keep_running = True

def signal_handler(signum, frame):
    """处理中断信号"""
    global keep_running
    keep_running = False
    print("\n\n接收到中断信号，正在优雅退出...")

def main():
    """主函数"""
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    print("=" * 70)
    print("原智 (YuanZhi) - 简化自动进化")
    print("=" * 70)
    print()
    
    # 配置
    goals_file = Path("evolution_goals.md")
    interval = 10
    
    print(f"[配置]")
    print(f"  进化间隔: {interval} 秒")
    print(f"  目标文件: {goals_file}")
    print()
    
    # 加载目标管理器
    goal_manager = EvolutionGoalManager(str(goals_file))
    load_result = goal_manager.load_goals()
    
    print(f"[调试] 加载结果: {load_result['success']}")
    print(f"[调试] 目标数量: {len(goal_manager.goals)}")
    if goal_manager.goals:
        for g in goal_manager.goals:
            print(f"  - {g.title}: status={g.status.value}, priority={g.priority.value}")
    else:
        print("[调试] 没有找到任何目标！")
    
    # 统计
    evolution_count = 0
    
    print("=" * 70)
    print("开始自动进化循环")
    print("=" * 70)
    print()
    
    while keep_running:
        try:
            # 获取待完成目标列表（pending 或 in_progress）
            all_goals = goal_manager.goals
            pending_or_in_progress = [g for g in all_goals if g.status in [GoalStatus.PENDING, GoalStatus.IN_PROGRESS]]
            
            if not pending_or_in_progress:
                print("✓ 所有目标已完成！")
                break
            
            # 选择第一个未完成目标
            next_goal = pending_or_in_progress[0]
            
            print(f"\n{'='*70}")
            print(f"进化目标 #{evolution_count + 1}: {next_goal.title}")
            print(f"{'='*70}")
            print(f"优先级: {next_goal.priority.value}")
            print(f"描述: {next_goal.description[:100]}...")
            print()
            
            # 生成指引
            guidance = goal_manager.generate_guidance_from_goal(next_goal)
            
            # 执行进化
            print("⏳ 开始生成能力（这可能需要30-120秒）...")
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
                
                # 立即继续下一个目标
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
    
    print()
    print("=" * 70)
    print(f"进化统计: 共完成 {evolution_count} 个能力")
    print("=" * 70)
    
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n\n用户中断")
        sys.exit(0)

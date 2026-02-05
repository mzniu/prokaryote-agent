"""
快速进化模式 - 立即执行进化目标
专为测试设计，间隔时间短
"""

import sys
import time
from prokaryote_agent import (
    init_prokaryote,
    start_prokaryote,
    generate_capability,
    EvolutionGoalManager
)

def main():
    print("=" * 60)
    print("原智 - 快速进化模式")
    print("=" * 60)
    
    # 初始化
    print("\n[1/4] 初始化系统...")
    init_result = init_prokaryote()
    if not init_result['success']:
        print(f"✗ 初始化失败: {init_result['msg']}")
        return
    print("✓ 初始化成功")
    
    # 启动监控
    print("\n[2/4] 启动监控...")
    start_result = start_prokaryote()
    if not start_result['success']:
        print(f"✗ 启动失败: {start_result['msg']}")
        return
    print("✓ 监控已启动")
    
    # 加载进化目标
    print("\n[3/4] 加载进化目标...")
    goal_manager = EvolutionGoalManager()
    result = goal_manager.load_goals()
    
    if not result["success"]:
        print(f"✗ 加载失败: {result['error']}")
        return
    
    goals = result["goals"]
    print(f"✓ 加载了 {len(goals)} 个目标")
    
    # 获取下一个目标
    next_goal = goal_manager.get_next_goal()
    if not next_goal:
        print("\n所有目标都已完成！🎉")
        return
    
    print(f"\n[4/4] 开始进化: {next_goal.title}")
    print(f"  状态: {next_goal.status.value}")
    print(f"  优先级: {next_goal.priority.value}")
    print(f"  描述: {next_goal.description[:100]}...")
    print()
    
    # 生成指引
    guidance = goal_manager.generate_guidance_from_goal(next_goal)
    print("进化指引:")
    print("-" * 60)
    print(guidance)
    print("-" * 60)
    print()
    
    # 执行进化
    print("开始生成能力...")
    print()
    
    result = generate_capability(guidance)
    
    if result["success"]:
        print("\n✓ 进化成功！")
        print(f"  能力ID: {result['capability_id']}")
        print(f"  能力名: {result['capability_name']}")
        print(f"  描述: {result['description']}")
        print(f"  安全等级: {result['safety_level']}")
        
        if result.get('safety_issues'):
            print(f"  ⚠️  安全提示: {', '.join(result['safety_issues'])}")
        
        # 标记完成
        goal_manager.mark_goal_completed(next_goal.title)
        print(f"\n✓ 目标已标记为完成")
        
    else:
        print(f"\n✗ 进化失败: {result.get('error', 'Unknown')}")
    
    print("\n" + "=" * 60)
    print("快速进化完成")
    print("=" * 60)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()

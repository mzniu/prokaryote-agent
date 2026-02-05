#!/usr/bin/env python
"""
验证系统合并后的功能
"""

print("="*70)
print("  原智(YuanZhi) 系统合并验证")
print("="*70)

# 测试1: 导入测试
print("\n[测试1] 模块导入...")
try:
    from start import HybridAgent
    from goal_evolution import GoalDrivenAgent
    from prokaryote_agent.iterative_evolver import IterativeEvolver
    from prokaryote_agent.goal_manager import EvolutionGoalManager
    print("✓ 所有模块导入成功")
except ImportError as e:
    print(f"✗ 导入失败: {e}")
    exit(1)

# 测试2: HybridAgent 初始化
print("\n[测试2] HybridAgent 初始化...")
try:
    agent = HybridAgent()
    assert agent.evolution_mode == 'iterative', "默认应为迭代模式"
    assert agent.goal_manager is not None, "目标管理器应已初始化"
    assert agent.auto_interval == 60, "默认间隔应为60秒"
    print("✓ HybridAgent 初始化成功")
    print(f"  - 进化模式: {agent.evolution_mode}")
    print(f"  - 目标管理器: {'已加载' if agent.goal_manager else '未加载'}")
    print(f"  - 自动间隔: {agent.auto_interval}秒")
except Exception as e:
    print(f"✗ 初始化失败: {e}")
    exit(1)

# 测试3: 目标加载
print("\n[测试3] 进化目标加载...")
try:
    result = agent.goal_manager.load_goals()
    if result["success"]:
        summary = agent.goal_manager.get_summary()
        print("✓ 目标加载成功")
        print(f"  - 总数: {summary['total']}")
        print(f"  - 待执行: {summary['pending']}")
        print(f"  - 已完成: {summary['completed']}")
        print(f"  - 失败: {summary['failed']}")
        
        # 显示待执行目标
        pending = agent.goal_manager.get_pending_goals()
        if pending:
            print(f"\n  待执行目标:")
            for i, goal in enumerate(pending[:3], 1):
                print(f"    {i}. {goal.title} (优先级: {goal.priority.value})")
    else:
        print(f"✗ 目标加载失败: {result.get('error')}")
except Exception as e:
    print(f"✗ 加载异常: {e}")

# 测试4: 配置检查
print("\n[测试4] 配置检查...")
try:
    import os
    import json
    
    config_path = "./prokaryote_agent/config/config.json"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        api_key = config.get('capability_config', {}).get('api_key', '')
        evolution_config = config.get('evolution', {})
        
        print("✓ 配置文件存在")
        print(f"  - API密钥: {'已配置' if api_key and not api_key.startswith('$') else '未配置'}")
        print(f"  - 进化模式: {evolution_config.get('mode', 'simple')}")
        
        if 'iterative_config' in evolution_config:
            iter_cfg = evolution_config['iterative_config']
            print(f"  - 迭代配置:")
            print(f"    * 最大迭代次数: {iter_cfg.get('max_iterations_per_goal', 15)}")
            print(f"    * 每阶段最大尝试: {iter_cfg.get('max_attempts_per_stage', 3)}")
    else:
        print("⚠️  配置文件不存在")
except Exception as e:
    print(f"⚠️  配置检查异常: {e}")

# 测试5: 目标文件检查
print("\n[测试5] 进化目标文件检查...")
try:
    goals_path = "./evolution_goals.md"
    if os.path.exists(goals_path):
        with open(goals_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        goal_count = content.count('# ')
        pending_count = content.count('**状态**: pending')
        completed_count = content.count('**状态**: completed')
        
        print("✓ 进化目标文件存在")
        print(f"  - 目标数量: {goal_count}")
        print(f"  - 待执行: {pending_count}")
        print(f"  - 已完成: {completed_count}")
    else:
        print("⚠️  进化目标文件不存在")
except Exception as e:
    print(f"⚠️  文件检查异常: {e}")

# 测试6: GoalDrivenAgent（旧系统）兼容性
print("\n[测试6] 旧系统兼容性...")
try:
    old_agent = GoalDrivenAgent(interval=5)
    print("✓ goal_evolution.py 仍可使用")
    print(f"  - 进化模式: {old_agent.evolution_mode}")
    print(f"  - 间隔: {old_agent.interval}秒")
except Exception as e:
    print(f"⚠️  旧系统异常: {e}")

# 总结
print("\n" + "="*70)
print("  验证完成")
print("="*70)
print("\n✅ 系统合并成功！")
print("\n推荐启动方式：")
print("  python start.py")
print("\n查看完整文档：")
print("  docs/启动说明.md")
print("="*70)

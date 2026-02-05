#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
演示技能学习系统的完整流程
展示技能如何通过真实网络搜索获取外部信息
"""

import os
import sys
import shutil

# 确保可以导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prokaryote_agent.skills.skill_generator import SkillGenerator
from prokaryote_agent.skills.skill_base import SkillLibrary
from prokaryote_agent.skills.skill_executor import SkillExecutor


def demo_skill_learning():
    """演示技能学习流程"""
    print("=" * 60)
    print("🧬 原核生物 Agent - 技能学习系统演示")
    print("=" * 60)
    print()
    
    # 清理旧的演示数据
    demo_path = "./demo_skills"
    if os.path.exists(demo_path):
        shutil.rmtree(demo_path)
    
    # 初始化组件
    library = SkillLibrary(demo_path)
    generator = SkillGenerator(library)
    executor = SkillExecutor(library)
    
    # 1. 学习法律检索技能
    print("📚 步骤1: 学习新技能 - 法律检索")
    print("-" * 40)
    
    skill_definition = {
        'id': 'legal_research_v1',
        'name': '法律检索',
        'tier': 'basic',
        'domain': 'legal',
        'description': '从互联网检索相关法律法规、司法解释和判例',
        'capabilities': ['法规检索', '判例搜索', '司法解释查询'],
        'prerequisites': []
    }
    
    result = generator.learn_skill(skill_definition)
    
    if result['success']:
        skill_id = result['skill_id']
        print(f"✓ 技能代码已生成: {skill_id}")
        print(f"  代码路径: {result.get('code_path', '')}")
        print(f"  需要训练: {result.get('needs_training', False)}")
        
        skill = library.get_skill(skill_id)
        if skill:
            print(f"  技能名称: {skill.metadata.name}")
            print(f"  技能等级: {skill.metadata.level} (需训练升至 Lv.1)")
    else:
        print(f"✗ 学习失败: {result.get('error', '未知错误')}")
        return
    print()
    
    # 2. 执行技能 - 实际网络搜索
    print("🔍 步骤2: 执行技能 - 搜索劳动法相关内容")
    print("-" * 40)
    
    exec_result = executor.execute(
        skill_id, 
        query="劳动合同解除条件",
        sources=["法律法规", "判例"]
    )
    
    if exec_result.get('success'):
        print(f"✓ 搜索成功!")
        # 技能返回 result，不是 data
        data = exec_result.get('result', {})
        print(f"  查询: {data.get('query', '')}")
        print(f"  找到结果: {data.get('total_found', 0)} 条")
        
        results = data.get('results', [])
        print("  搜索结果:")
        for i, r in enumerate(results[:3], 1):
            title = r.get('title', '无标题')
            source = r.get('source', '未知来源')
            print(f"    {i}. [{source}] {title[:50]}")
    else:
        print(f"✗ 搜索失败: {exec_result.get('error', '未知错误')}")
    print()
    
    # 3. 技能训练升级
    print("🎯 步骤3: 训练技能升级到 Lv.1")
    print("-" * 40)
    
    training_result = generator.upgrade_skill(skill_id, target_level=1)
    
    if training_result["success"]:
        print(f"✓ 训练完成!")
        print(f"  旧等级: {training_result.get('old_level', 0)}")
        print(f"  新等级: {training_result.get('new_level', 1)}")
        
        tasks = training_result.get("tasks_completed", [])
        if tasks:
            print(f"  完成的训练任务:")
            for task in tasks:
                print(f"    - {task.get('task', '')}")
                task_result = task.get('result', {})
                if task_result.get('success'):
                    total = task_result.get('data', {}).get('total_found', 0)
                    print(f"      ✓ 找到 {total} 条结果")
    else:
        print(f"✗ 训练失败: {training_result.get('error', '未知错误')}")
    print()
    
    # 4. 学习软件技能
    print("💻 步骤4: 学习软件开发技能 - 调试助手")
    print("-" * 40)
    
    debug_definition = {
        'id': 'debug_assistant_v1',
        'name': '调试助手',
        'tier': 'basic',
        'domain': 'software_dev',
        'description': '帮助诊断和解决代码错误',
        'capabilities': ['错误诊断', '解决方案搜索', 'Stack Overflow查询'],
        'prerequisites': []
    }
    
    debug_result = generator.learn_skill(debug_definition)
    
    if debug_result['success']:
        debug_skill_id = debug_result['skill_id']
        print(f"✓ 调试技能已生成: {debug_skill_id}")
    else:
        print(f"✗ 学习失败: {debug_result.get('error', '')}")
        debug_skill_id = None
    print()
    
    # 5. 执行调试技能
    if debug_skill_id:
        print("🔧 步骤5: 使用调试技能")
        print("-" * 40)
        
        exec_result = executor.execute(
            debug_skill_id,
            error="TypeError: 'NoneType' object is not subscriptable",
            language="python"
        )
        
        if exec_result.get('success'):
            print(f"✓ 调试分析完成!")
            # 技能返回 result，不是 data
            data = exec_result.get('result', {})
            error_msg = data.get('error', '')[:50]
            print(f"  错误: {error_msg}...")
            print(f"  分析: {data.get('analysis', '')}")
            
            solutions = data.get('possible_solutions', [])
            print(f"  找到 {len(solutions)} 个可能的解决方案:")
            for i, s in enumerate(solutions[:2], 1):
                title = s.get('title', '无标题')
                print(f"    {i}. {title[:60]}")
        else:
            print(f"✗ 调试失败: {exec_result.get('error', '未知错误')}")
        print()
    
    # 6. 展示技能库
    print("📋 步骤6: 技能库概览")
    print("-" * 40)
    
    all_skills = library.list_skills()
    print(f"当前已学习 {len(all_skills)} 个技能:")
    for skill_meta in all_skills:
        status = "🟢" if skill_meta.level > 0 else "🟡"
        print(f"  {status} {skill_meta.name} (Lv.{skill_meta.level}) - {skill_meta.domain}")
    print()
    
    print("=" * 60)
    print("✨ 演示完成! Agent 现在可以通过网络获取真实信息!")
    print("=" * 60)


if __name__ == "__main__":
    demo_skill_learning()

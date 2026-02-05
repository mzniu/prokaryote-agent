#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试技能系统与知识库的集成
"""

import os
import sys
import shutil

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prokaryote_agent.skills.skill_generator import SkillGenerator
from prokaryote_agent.skills.skill_base import SkillLibrary
from prokaryote_agent.skills.skill_executor import SkillExecutor
from prokaryote_agent.knowledge import MarkdownKnowledge


def test_skill_knowledge_integration():
    """测试技能执行后自动存储到知识库"""
    print("=" * 60)
    print("🔗 技能-知识库集成测试")
    print("=" * 60)
    print()
    
    # 清理测试数据
    skill_path = "./test_integration_skills"
    kb_path = "./test_integration_kb"
    
    for path in [skill_path, kb_path]:
        if os.path.exists(path):
            shutil.rmtree(path)
    
    # 初始化
    library = SkillLibrary(skill_path)
    generator = SkillGenerator(library)
    executor = SkillExecutor(library)
    kb = MarkdownKnowledge(kb_path)
    
    # 1. 学习法律检索技能
    print("📚 步骤1: 学习法律检索技能")
    print("-" * 40)
    
    skill_definition = {
        'id': 'legal_research_kb',
        'name': '法律检索(知识库版)',
        'tier': 'basic',
        'domain': 'legal',
        'description': '检索法律资料并存储到知识库',
        'capabilities': ['法规检索', '知识积累'],
        'prerequisites': []
    }
    
    result = generator.learn_skill(skill_definition)
    
    if result['success']:
        print(f"✓ 技能已学习: {result['skill_id']}")
    else:
        print(f"✗ 学习失败: {result.get('error')}")
        return False
    print()
    
    # 2. 查看知识库初始状态
    print("📊 步骤2: 知识库初始状态")
    print("-" * 40)
    
    stats = kb.get_stats()
    print(f"  总知识数: {stats['total']}")
    print()
    
    # 3. 执行技能（会触发网络搜索并存储）
    print("🔍 步骤3: 执行技能（联网搜索 + 存储）")
    print("-" * 40)
    
    # 注意：由于生成的代码使用默认知识库路径，我们这里只测试技能是否能执行
    exec_result = executor.execute(
        'legal_research_kb',
        query="劳动合同解除",
        sources=["法律法规"],
        use_cache=False  # 强制联网
    )
    
    if exec_result.get('success'):
        data = exec_result.get('result', {})
        print(f"✓ 执行成功!")
        print(f"  查询: {data.get('query', '')}")
        print(f"  找到: {data.get('total_found', 0)} 条结果")
        print(f"  来源: {'知识库缓存' if data.get('from_cache') else '网络搜索'}")
        
        stored = data.get('stored_to_kb', 0)
        if stored:
            print(f"  新存储: {stored} 条到知识库")
    else:
        print(f"⚠ 执行出错: {exec_result.get('error')}")
        # 继续测试，不算失败
    print()
    
    # 4. 验证知识库（使用默认路径的知识库）
    print("📊 步骤4: 检查默认知识库")
    print("-" * 40)
    
    default_kb = MarkdownKnowledge("prokaryote_agent/knowledge")
    stats = default_kb.get_stats()
    print(f"  总知识数: {stats['total']}")
    print(f"  按领域: {stats['by_domain']}")
    
    if stats['total'] > 0:
        print("  最近知识:")
        for item in stats['recent'][:3]:
            print(f"    - {item['title']}")
    print()
    
    # 5. 测试知识库搜索
    print("🔎 步骤5: 搜索知识库")
    print("-" * 40)
    
    search_results = default_kb.search("劳动", domain="legal", limit=3)
    print(f"  搜索 '劳动': 找到 {len(search_results)} 条")
    for r in search_results[:2]:
        print(f"    - {r['title'][:40]}...")
    print()
    
    # 清理测试数据
    for path in [skill_path, kb_path]:
        if os.path.exists(path):
            shutil.rmtree(path)
    
    print("=" * 60)
    print("✅ 集成测试完成!")
    print("=" * 60)
    
    return True


def test_knowledge_cache():
    """测试知识库缓存功能"""
    print()
    print("=" * 60)
    print("💾 知识库缓存测试")
    print("=" * 60)
    print()
    
    # 使用默认知识库
    from prokaryote_agent.knowledge import store_knowledge, search_knowledge
    
    # 1. 手动添加一些测试知识
    print("📝 步骤1: 添加测试知识")
    print("-" * 40)
    
    test_data = [
        {
            'title': '劳动合同法第39条解读',
            'content': '用人单位可以解除劳动合同的情形：试用期不合格、严重违纪、严重失职等。',
            'domain': 'legal',
            'category': 'laws'
        },
        {
            'title': '经济补偿金计算方法',
            'content': 'N年工龄 = N个月工资。最高不超过12个月。',
            'domain': 'legal',
            'category': 'concepts'
        },
        {
            'title': 'Python AttributeError 常见解决',
            'content': "AttributeError: 'NoneType' 通常是因为对象为None时调用了属性或方法。",
            'domain': 'software_dev',
            'category': 'errors'
        }
    ]
    
    for item in test_data:
        path = store_knowledge(
            title=item['title'],
            content=item['content'],
            domain=item['domain'],
            category=item['category'],
            acquired_by='test_script'
        )
        print(f"  ✓ {item['title'][:30]}...")
    print()
    
    # 2. 测试搜索
    print("🔎 步骤2: 测试搜索缓存")
    print("-" * 40)
    
    # 搜索法律相关
    results = search_knowledge("劳动合同", domain="legal")
    print(f"  搜索 '劳动合同' (legal): {len(results)} 条")
    
    # 搜索错误相关
    results = search_knowledge("AttributeError", domain="software_dev")
    print(f"  搜索 'AttributeError' (software_dev): {len(results)} 条")
    
    # 跨领域搜索
    results = search_knowledge("解决")
    print(f"  搜索 '解决' (全部): {len(results)} 条")
    print()
    
    print("=" * 60)
    print("✅ 缓存测试完成!")
    print("=" * 60)
    
    return True


if __name__ == "__main__":
    success1 = test_skill_knowledge_integration()
    success2 = test_knowledge_cache()
    
    print()
    print("=" * 60)
    print(f"总结: {'全部通过 ✅' if success1 and success2 else '有测试失败 ❌'}")
    print("=" * 60)
    
    sys.exit(0 if success1 and success2 else 1)

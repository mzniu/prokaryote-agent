#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试 Markdown 知识库功能
"""

import os
import sys
import shutil

# 确保可以导入模块
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prokaryote_agent.knowledge import MarkdownKnowledge, Knowledge
from prokaryote_agent.knowledge.knowledge_base import store_knowledge, search_knowledge


def test_basic_store_and_search():
    """测试基本存储和搜索"""
    print("=" * 60)
    print("测试1: 基本存储和搜索")
    print("=" * 60)
    
    # 使用临时目录
    test_path = "./test_knowledge"
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    kb = MarkdownKnowledge(test_path)
    
    # 存储知识
    knowledge1 = Knowledge(
        id="kb_legal_001",
        title="劳动合同解除的法定情形",
        content="""
根据《劳动合同法》第39条，用人单位可以解除劳动合同的情形包括：
1. 在试用期间被证明不符合录用条件的
2. 严重违反用人单位的规章制度的
3. 严重失职，营私舞弊，给用人单位造成重大损害的
        """.strip(),
        domain="legal",
        category="laws",
        keywords=["劳动合同", "解除", "第39条"],
        source_url="https://www.court.gov.cn/example",
        acquired_by="legal_research_v1"
    )
    
    path1 = kb.store(knowledge1)
    print(f"✓ 存储知识1: {path1}")
    
    # 存储第二条知识
    knowledge2 = Knowledge(
        id="kb_legal_002",
        title="经济补偿金计算标准",
        content="""
经济补偿按劳动者在本单位工作的年限计算：
- 每满一年支付一个月工资
- 六个月以上不满一年的，按一年计算
- 不满六个月的，支付半个月工资
        """.strip(),
        domain="legal",
        category="concepts",
        keywords=["经济补偿金", "计算", "N+1"],
        source_url="https://www.example.com/compensation",
        acquired_by="legal_research_v1"
    )
    
    path2 = kb.store(knowledge2)
    print(f"✓ 存储知识2: {path2}")
    
    # 存储软件开发知识
    knowledge3 = Knowledge(
        id="kb_dev_001",
        title="Python TypeError 解决方法",
        content="""
TypeError: 'NoneType' object is not subscriptable

常见原因：
1. 函数返回 None 但尝试对结果进行索引
2. 变量未正确初始化
3. API 调用失败返回 None

解决方法：
- 检查函数返回值
- 添加 None 检查
- 使用默认值
        """.strip(),
        domain="software_dev",
        category="errors",
        keywords=["TypeError", "NoneType", "Python"],
        source_url="https://stackoverflow.com/questions/example"
    )
    
    path3 = kb.store(knowledge3)
    print(f"✓ 存储知识3: {path3}")
    
    # 搜索测试
    print()
    print("搜索 '劳动合同':")
    results = kb.search("劳动合同")
    print(f"  找到 {len(results)} 条结果")
    for r in results:
        print(f"  - [{r['score']}分] {r['title']}")
    
    assert len(results) >= 1, "应该找到至少1条结果"
    
    print()
    print("搜索 '经济补偿' (限定 legal 领域):")
    results = kb.search("经济补偿", domain="legal")
    print(f"  找到 {len(results)} 条结果")
    for r in results:
        print(f"  - [{r['score']}分] {r['title']}")
    
    print()
    print("搜索 'TypeError':")
    results = kb.search("TypeError")
    print(f"  找到 {len(results)} 条结果")
    for r in results:
        print(f"  - [{r['score']}分] {r['title']} ({r['domain']})")
    
    # 清理
    shutil.rmtree(test_path)
    print()
    print("✓ 测试1通过!")
    return True


def test_store_from_search():
    """测试从搜索结果存储"""
    print()
    print("=" * 60)
    print("测试2: 从搜索结果存储")
    print("=" * 60)
    
    test_path = "./test_knowledge2"
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    kb = MarkdownKnowledge(test_path)
    
    # 模拟搜索结果存储
    path = kb.store_from_search(
        title="劳动争议仲裁时效",
        content="劳动争议申请仲裁的时效期间为一年，从当事人知道或者应当知道其权利被侵害之日起计算。",
        domain="legal",
        category="concepts",
        source_url="https://www.example.com/arbitration",
        acquired_by="legal_research_v1"
    )
    
    print(f"✓ 存储成功: {path}")
    
    # 验证文件内容
    from pathlib import Path
    content = Path(path).read_text(encoding='utf-8')
    
    assert "劳动争议仲裁时效" in content, "标题应该在内容中"
    assert "kb_legal_" in content, "应该有自动生成的ID"
    assert "domain: legal" in content, "应该有领域信息"
    
    print("✓ 文件内容验证通过")
    
    # 清理
    shutil.rmtree(test_path)
    print("✓ 测试2通过!")
    return True


def test_index_management():
    """测试索引管理"""
    print()
    print("=" * 60)
    print("测试3: 索引管理")
    print("=" * 60)
    
    test_path = "./test_knowledge3"
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    kb = MarkdownKnowledge(test_path)
    
    # 存储多条知识
    for i in range(3):
        kb.store_from_search(
            title=f"测试知识{i+1}",
            content=f"这是测试内容{i+1}",
            domain="legal",
            category="laws",
            source_url=f"https://example.com/{i+1}"
        )
    
    kb.store_from_search(
        title="软件开发知识",
        content="这是软件开发相关内容",
        domain="software_dev",
        category="apis"
    )
    
    # 检查索引文件
    from pathlib import Path
    index_path = Path(test_path) / "_index.md"
    
    assert index_path.exists(), "索引文件应该存在"
    
    index_content = index_path.read_text(encoding='utf-8')
    print("索引文件内容:")
    print("-" * 40)
    print(index_content)
    print("-" * 40)
    
    assert "总知识数: 4" in index_content, "应该有4条知识"
    assert "legal" in index_content, "应该有 legal 领域"
    assert "software_dev" in index_content, "应该有 software_dev 领域"
    
    # 测试统计
    stats = kb.get_stats()
    print()
    print(f"统计信息: 总计 {stats['total']} 条")
    print(f"  按领域: {stats['by_domain']}")
    
    assert stats['total'] == 4, "总数应该是4"
    assert stats['by_domain'].get('legal') == 3, "legal 应该有3条"
    assert stats['by_domain'].get('software_dev') == 1, "software_dev 应该有1条"
    
    # 清理
    shutil.rmtree(test_path)
    print()
    print("✓ 测试3通过!")
    return True


def test_duplicate_detection():
    """测试去重功能"""
    print()
    print("=" * 60)
    print("测试4: 去重功能")
    print("=" * 60)
    
    test_path = "./test_knowledge4"
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    kb = MarkdownKnowledge(test_path)
    
    # 存储第一条
    path1 = kb.store_from_search(
        title="重复测试",
        content="第一次内容",
        domain="legal",
        category="laws"
    )
    print(f"✓ 第一次存储: {path1}")
    
    # 存储相同标题的第二条
    path2 = kb.store_from_search(
        title="重复测试",
        content="第二次内容",
        domain="legal",
        category="laws"
    )
    print(f"✓ 第二次存储: {path2}")
    
    # 应该是同一个文件（去重）
    assert path1 == path2, "重复内容应该返回相同路径"
    
    # 检查统计
    stats = kb.get_stats()
    assert stats['total'] == 1, "应该只有1条知识（去重）"
    
    # 清理
    shutil.rmtree(test_path)
    print("✓ 测试4通过!")
    return True


def test_get_knowledge():
    """测试获取知识"""
    print()
    print("=" * 60)
    print("测试5: 获取知识")
    print("=" * 60)
    
    test_path = "./test_knowledge5"
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    kb = MarkdownKnowledge(test_path)
    
    # 存储
    original = Knowledge(
        id="kb_test_001",
        title="获取测试",
        content="这是测试内容，用于验证获取功能。",
        domain="legal",
        category="laws",
        keywords=["测试", "获取"],
        source_url="https://example.com/test",
        quality_score=0.8
    )
    
    path = kb.store(original)
    print(f"✓ 存储知识: {path}")
    
    # 通过路径获取
    retrieved = kb.get(path)
    assert retrieved is not None, "应该能获取到知识"
    assert retrieved.title == original.title, "标题应该匹配"
    assert retrieved.id == original.id, "ID应该匹配"
    print(f"✓ 通过路径获取: {retrieved.title}")
    
    # 通过ID获取
    retrieved2 = kb.get("kb_test_001")
    assert retrieved2 is not None, "应该能通过ID获取"
    assert retrieved2.title == original.title, "标题应该匹配"
    print(f"✓ 通过ID获取: {retrieved2.title}")
    
    # 清理
    shutil.rmtree(test_path)
    print("✓ 测试5通过!")
    return True


def test_convenience_functions():
    """测试便捷函数"""
    print()
    print("=" * 60)
    print("测试6: 便捷函数")
    print("=" * 60)
    
    # 注意：这会使用默认路径 prokaryote_agent/knowledge
    # 先清理可能存在的测试数据
    test_path = "prokaryote_agent/knowledge/test_domain"
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    # 使用便捷函数存储
    path = store_knowledge(
        title="便捷函数测试",
        content="这是通过便捷函数存储的内容",
        domain="test_domain",
        category="test_cat",
        source_url="https://example.com/convenience"
    )
    print(f"✓ store_knowledge: {path}")
    
    # 使用便捷函数搜索
    results = search_knowledge("便捷函数", domain="test_domain")
    print(f"✓ search_knowledge: 找到 {len(results)} 条")
    
    assert len(results) >= 1, "应该找到至少1条"
    
    # 清理
    if os.path.exists(test_path):
        shutil.rmtree(test_path)
    
    print("✓ 测试6通过!")
    return True


def run_all_tests():
    """运行所有测试"""
    print("=" * 60)
    print("🧪 Markdown 知识库测试套件")
    print("=" * 60)
    print()
    
    tests = [
        ("基本存储和搜索", test_basic_store_and_search),
        ("从搜索结果存储", test_store_from_search),
        ("索引管理", test_index_management),
        ("去重功能", test_duplicate_detection),
        ("获取知识", test_get_knowledge),
        ("便捷函数", test_convenience_functions),
    ]
    
    passed = 0
    failed = 0
    
    for name, test_func in tests:
        try:
            if test_func():
                passed += 1
            else:
                failed += 1
                print(f"✗ {name} 失败")
        except Exception as e:
            failed += 1
            print(f"✗ {name} 异常: {e}")
            import traceback
            traceback.print_exc()
    
    print()
    print("=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)

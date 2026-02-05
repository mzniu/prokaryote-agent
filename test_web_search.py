#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""测试网络搜索功能"""

from prokaryote_agent.skills.web_tools import web_search, search_legal, search_wikipedia

def test_web_search():
    print("=" * 50)
    print("测试网络搜索...")
    print("=" * 50)
    
    results = web_search("Python 教程", max_results=3)
    print(f"web_search 结果: {len(results)} 条")
    for r in results[:2]:
        title = r.get("title", "无标题")
        url = r.get("url", "")
        print(f"  - {title[:60]}")
        print(f"    URL: {url[:80]}")
    print()

def test_legal_search():
    print("=" * 50)
    print("测试法律搜索...")
    print("=" * 50)
    
    legal_results = search_legal("劳动合同", "laws")
    print(f"search_legal (laws) 结果: {len(legal_results)} 条")
    for r in legal_results[:2]:
        title = r.get("title", "无标题")
        print(f"  - {title[:60]}")
    print()
    
    case_results = search_legal("劳动合同 解除", "cases")
    print(f"search_legal (cases) 结果: {len(case_results)} 条")
    for r in case_results[:2]:
        title = r.get("title", "无标题")
        print(f"  - {title[:60]}")
    print()

def test_wikipedia():
    print("=" * 50)
    print("测试 Wikipedia 搜索...")
    print("=" * 50)
    
    wiki_results = search_wikipedia("人工智能")
    print(f"search_wikipedia 结果: {len(wiki_results)} 条")
    for r in wiki_results[:2]:
        title = r.get("title", "无标题")
        print(f"  - {title[:60]}")
    print()

if __name__ == "__main__":
    test_web_search()
    test_legal_search()
    test_wikipedia()
    print("=" * 50)
    print("所有测试完成!")
    print("=" * 50)

"""
技能: 法律检索
描述: 检索法律条文、判例和法规的能力
领域: legal
层级: basic
生成时间: 2026-02-06T19:43:32.161164

能力:
- 检索法条
- 查找判例
- 搜索法规
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from typing import Dict, Any, List


class LegalResearchBasic(Skill):
    """
    法律检索

    检索法律条文、判例和法规的能力
    """

    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="legal_research_basic",
                name="法律检索",
                tier="basic",
                domain="legal",
                description="检索法律条文、判例和法规的能力"
            )
        super().__init__(metadata)

    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return ['检索法条', '查找判例', '搜索法规']

    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        
        query = kwargs.get('query')
        return query is not None and len(query.strip()) > 0

    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行技能

        
        Args:
            query: 检索关键词
            sources: 检索源列表 ['法律法规', '司法解释', '判例']
            use_cache: 是否优先使用本地知识库 (默认True)

        Returns:
            检索结果，包含标题、内容、URL等
            from_cache: 是否来自知识库
            stored_to_kb: 新存储到知识库的数量
        """
        try:
            
            from prokaryote_agent.skills.web_tools import search_legal_deep, deep_search
            from prokaryote_agent.knowledge import store_knowledge, search_knowledge

            query = kwargs.get('query', '')
            sources = kwargs.get('sources', ['法律法规', '司法解释', '判例'])
            use_cache = kwargs.get('use_cache', True)

            # 1. 先查本地知识库
            if use_cache:
                local_results = search_knowledge(query, domain="legal", limit=5)
                if len(local_results) >= 3:
                    result = {
                        'query': query,
                        'sources': sources,
                        'results': [{'title': r['title'], 'source': 'knowledge_base',
                                    'content': r.get('content', r.get('snippet', ''))} for r in local_results],
                        'total_found': len(local_results),
                        'from_cache': True,
                        'stored_to_kb': 0
                    }
                    return {'success': True, 'result': result}

            # 2. 本地知识不足，深度联网搜索
            all_results = []

            # 根据 sources 决定搜索类别
            category = 'all'
            for src in sources:
                if '法规' in src or '法律' in src:
                    category = 'laws'
                    break
                if '判例' in src or '案例' in src:
                    category = 'cases'
                    break

            # 执行深度搜索（会抓取网页内容）
            all_results = search_legal_deep(query, category=category, max_results=3)

            # 3. 存储搜索结果到知识库（有内容的才存）
            stored_count = 0
            for r in all_results[:5]:
                content = r.get('content', '')
                if content and len(content) > 100:  # 只存有内容的
                    try:
                        store_knowledge(
                            title=r.get('title', query),
                            content=content,
                            domain="legal",
                            category=r.get('category', 'general'),
                            source_url=r.get('url', ''),
                            acquired_by=self.metadata.skill_id
                        )
                        stored_count += 1
                    except Exception:
                        pass

            result = {
                'query': query,
                'sources': sources,
                'results': all_results,
                'total_found': len(all_results),
                'from_cache': False,
                'stored_to_kb': stored_count
            }

            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [{'input': {'query': '劳动合同解除'}, 'description': '检索劳动合同相关法规'}, {'input': {'query': '知识产权侵权', 'sources': ['判例']}, 'description': '检索知识产权判例'}]

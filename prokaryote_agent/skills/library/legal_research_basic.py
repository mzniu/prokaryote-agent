"""
技能: 法律检索
描述: 检索法律条文、判例和法规的能力
领域: legal
层级: basic
生成时间: 2026-02-06T21:44:53.324456

能力:
- 检索法条
- 查找判例
- 搜索法规
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from prokaryote_agent.skills.skill_context import SkillContext
from typing import Dict, Any, List, Optional


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

    def execute(self, context: SkillContext = None, **kwargs) -> Dict[str, Any]:
        """
        执行技能

        Args:
            context: 技能执行上下文，提供知识库访问、技能互调用、产出物保存
        
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
            
            from prokaryote_agent.skills.web_tools import deep_search_by_categories, deep_search
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
                    # 缓存路径也保存产出物
                    if context and result:
                        self._save_output(context, result)
                    return {'success': True, 'result': result}

            # 2. 本地知识不足，深度联网搜索
            # 法律领域的类别配置（领域特定逻辑在 skill 层）
            legal_categories = {
                'laws': '法律法规 法条 条文',
                'cases': '判例 案例 裁判文书',
                'interpretations': '司法解释 最高法 最高检'
            }

            # 根据 sources 决定搜索类别
            category_filter = 'all'
            for src in sources:
                if '法规' in src or '法律' in src:
                    category_filter = 'laws'
                    break
                if '判例' in src or '案例' in src:
                    category_filter = 'cases'
                    break

            # 执行通用的分类深度搜索
            all_results = deep_search_by_categories(
                query=query,
                categories=legal_categories,
                category_filter=category_filter,
                max_results=5
            )

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

            # 保存产出物到Knowledge（如果有context）
            if context and result:
                self._save_output(context, result)

            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _save_output(self, context: SkillContext, result: Dict[str, Any]):
        """保存产出物到Knowledge"""
        
        # 保存检索结果
        results = result.get('results', [])
        if results:
            content_lines = [f"## 检索查询: {result.get('query', '')}\n"]
            for i, r in enumerate(results[:5], 1):
                content_lines.append(f"### {i}. {r.get('title', '无标题')}")
                content_lines.append(f"- 来源: {r.get('source', '未知')}")
                if r.get('url'):
                    content_lines.append(f"- URL: {r.get('url')}")
                # 保存完整内容，不截断
                content = r.get('content', '')
                content_lines.append(f"\n{content}\n")
            context.save_output(
                output_type='research',
                title=f"法律检索_{result.get('query', '未知')[:20]}",
                content='\n'.join(content_lines),
                category='research_results',
                metadata={'total_found': result.get('total_found', 0), 'from_cache': result.get('from_cache', False)}
            )

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [{'input': {'query': '劳动合同解除'}, 'description': '检索劳动合同相关法规'}, {'input': {'query': '知识产权侵权', 'sources': ['判例']}, 'description': '检索知识产权判例'}]

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
import re
import json


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
            analysis: AI分析结果
            law_references: 法律引用列表
        """
        try:
            
            query = kwargs.get('query', '')
            sources = kwargs.get('sources', ['法律法规', '司法解释', '判例'])
            use_cache = kwargs.get('use_cache', True)
            
            # 扩展搜索关键词
            search_keywords = self._expand_search_keywords(query)
            
            # 1. 先查本地知识库
            local_results = []
            if use_cache:
                for keyword in search_keywords:
                    local_results.extend(context.search_knowledge(keyword, limit=5))
            
            # 去重本地结果
            seen_titles = set()
            unique_local_results = []
            for r in local_results:
                title = r.get('title', '')
                if title not in seen_titles:
                    seen_titles.add(title)
                    unique_local_results.append(r)
            
            all_results = []
            stored_count = 0
            from_cache = False
            
            # 2. 如果本地结果足够，直接使用
            if use_cache and len(unique_local_results) >= 3:
                from_cache = True
                all_results = [{
                    'title': r.get('title', ''),
                    'source': 'knowledge_base',
                    'content': r.get('content', r.get('snippet', '')),
                    'url': r.get('source_url', ''),
                    'category': r.get('category', 'general')
                } for r in unique_local_results[:10]]
            else:
                # 3. 本地知识不足，深度联网搜索
                # 法律领域的类别配置（领域特定逻辑在 skill 层）
                legal_categories = {
                    'laws': '法律法规 法条 条文',
                    'cases': '判例 案例 裁判文书',
                    'interpretations': '司法解释 最高法 最高检'
                }

                # 根据 sources 决定搜索类别
                category_filter = 'all'
                if any('法规' in src or '法律' in src for src in sources):
                    category_filter = 'laws'
                elif any('判例' in src or '案例' in src for src in sources):
                    category_filter = 'cases'

                try:
                    # 对每个关键词执行搜索
                    web_results = []
                    for keyword in search_keywords[:3]:  # 限制关键词数量
                        try:
                            results = context.deep_search_by_categories(
                                query=keyword,
                                categories=legal_categories,
                                category_filter=category_filter,
                                max_results=5
                            )
                            web_results.extend(results)
                        except Exception:
                            continue
                    
                    # 去重并限制数量
                    seen_urls = set()
                    for r in web_results:
                        url = r.get('url', '')
                        if url and url not in seen_urls:
                            seen_urls.add(url)
                            all_results.append(r)
                    
                    all_results = all_results[:15]  # 限制总结果数
                    
                    # 4. 存储搜索结果到知识库（有内容的才存）
                    for r in all_results:
                        content = r.get('content', '')
                        title = r.get('title', query)
                        if content and len(content) > 50:  # 降低阈值确保存储
                            try:
                                context.store_knowledge(
                                    title=title[:200],
                                    content=content[:5000],
                                    category=r.get('category', 'general'),
                                    source=r.get('url', ''),
                                    tags=['法律', '检索']
                                )
                                stored_count += 1
                            except Exception as e:
                                # 尝试简化存储
                                try:
                                    context.store_knowledge(
                                        title=title[:100],
                                        content=content[:2000],
                                        category='general',
                                        source=r.get('url', '')[:500]
                                    )
                                    stored_count += 1
                                except Exception:
                                    pass
                except Exception as e:
                    # 网络搜索失败，使用本地结果
                    if unique_local_results:
                        all_results = [{
                            'title': r.get('title', ''),
                            'source': 'knowledge_base',
                            'content': r.get('content', r.get('snippet', '')),
                            'url': r.get('source_url', ''),
                            'category': r.get('category', 'general')
                        } for r in unique_local_results[:10]]
                        from_cache = True
                    else:
                        all_results = []

            # 5. 提取法律引用并生成深度分析
            law_references = []
            analysis_content = ""
            
            # 提取法律引用
            for result in all_results:
                content = result.get('content', '')
                if content:
                    refs = self._extract_law_references(content)
                    law_references.extend(refs)
            
            # 去重法律引用
            law_references = list(set(law_references))[:20]  # 限制数量
            
            # 生成深度分析（使用context.call_ai）
            try:
                if all_results and len(law_references) > 0:
                    analysis_prompt = f"""
                    请对以下法律检索结果进行深度分析：

                    查询主题：{query}
                    检索来源：{', '.join(sources)}
                    相关法律引用：{', '.join(law_references[:10])}

                    请提供：
                    1. 相关法律领域的概述
                    2. 主要法律条文的解释
                    3. 实际应用建议
                    4. 潜在的法律风险提示
                    
                    请以专业、详细的方式撰写分析报告，字数不少于800字。
                    """
                    ai_result = context.call_ai(analysis_prompt, max_tokens=1500)
                    if ai_result.get('success'):
                        analysis_content = ai_result['content']
                elif all_results:
                    analysis_prompt = f"""
                    请对以下法律检索结果进行分析：

                    查询主题：{query}
                    检索来源：{', '.join(sources)}
                    
                    请总结检索结果的关键信息，并提供相关的法律见解。
                    字数不少于500字。
                    """
                    ai_result = context.call_ai(analysis_prompt, max_tokens=1000)
                    if ai_result.get('success'):
                        analysis_content = ai_result['content']
            except Exception:
                # AI不可用，生成基本分析
                analysis_content = self._generate_basic_analysis(query, all_results, law_references)
            
            result = {
                'query': query,
                'sources': sources,
                'results': all_results[:10],  # 返回前10个结果
                'total_found': len(all_results),
                'from_cache': from_cache,
                'stored_to_kb': stored_count,
                'analysis': analysis_content,
                'law_references': law_references,
                'search_keywords_used': search_keywords
            }

            # 保存产出物到Knowledge（如果有context）
            if context:
                self._save_output(context, result)

            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'result': {
                    'query': kwargs.get('query', ''),
                    'sources': kwargs.get('sources', []),
                    'results': [],
                    'total_found': 0,
                    'from_cache': False,
                    'stored_to_kb': 0,
                    'analysis': f"检索过程中出现错误：{str(e)}",
                    'law_references': [],
                    'search_keywords_used': []
                }
            }

    def _expand_search_keywords(self, query: str) -> List[str]:
        """扩展搜索关键词"""
        keywords = [query]
        
        # 添加常见法律后缀
        legal_suffixes = ['法律法规', '法条', '司法解释', '案例', '判例', '规定', '条例']
        for suffix in legal_suffixes:
            keywords.append(f"{query} {suffix}")
        
        # 如果是中文，尝试拆分查询词
        if re.search(r'[\u4e00-\u9fff]', query):
            # 简单的分词：按常见法律连接词拆分
            connectors = ['与', '和', '及', '以及', '或', '或者', '的']
            parts = re.split('|'.join(connectors), query)
            for part in parts:
                part = part.strip()
                if part and part != query and len(part) > 1:
                    keywords.append(part)
        
        # 添加相关领域关键词
        legal_fields = {
            '合同': ['合同法', '契约', '协议'],
            '侵权': ['侵权责任', '损害赔偿', '赔偿'],
            '刑事': ['刑法', '犯罪', '刑事责任'],
            '民事': ['民法', '民事诉讼', '民事纠纷'],
            '行政': ['行政法', '行政处罚', '行政复议']
        }
        
        for field, related in legal_fields.items():
            if field in query:
                keywords.extend(related)
        
        # 去重
        unique_keywords = []
        seen = set()
        for kw in keywords:
            if kw and kw not in seen:
                seen.add(kw)
                unique_keywords.append(kw)
        
        return unique_keywords[:10]  # 限制关键词数量

    def _extract_law_references(self, text: str) -> List[str]:
        """从文本中提取法律引用"""
        references = []
        
        # 匹配法律名称模式
        patterns = [
            r'《([^》]{2,20}法)》',  # 《合同法》
            r'《([^》]{2,20}条例)》',  # 《劳动合同条例》
            r'《([^》]{2,20}规定)》',  # 《最高人民法院规定》
            r'《([^》]{2,20}解释)》',  # 《司法解释》
            r'([^》]{2,15}法第[零一二三四五六七八九十百千0-9]+条)',  # 合同法第十五条
            r'([^》]{2,15}条例第[零一二三四五六七八九十百千0-9]+条)',  # 劳动合同条例第十条
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, text)
            references.extend(matches)
        
        # 匹配法条引用
        law_patterns = [
            r'(第[零一二三四五六七八九十百千0-9]+条[^，。；]{0,50})',
            r'([零一二三四五六七八九十百千0-9]+年[零一二三四五六七八九十百千0-9]+月[零一二三四五六七八九十百千0-9]+日[^，。；]{0,30})',
        ]
        
        for pattern in law_patterns:
            matches = re.findall(pattern, text)
            references.extend(matches)
        
        # 清理结果
        cleaned_refs = []
        for ref in references:
            ref = ref.strip()
            if ref and len(ref) > 2:
                cleaned_refs.append(ref)
        
        return cleaned_refs[:20]  # 限制数量

    def _generate_basic_analysis(self, query: str, results: List[Dict], law_references: List[str]) -> str:
        """生成基础分析报告"""
        if not results:
            return "未找到相关检索结果。"
        
        analysis_lines = [
            f"# 法律检索分析报告",
            f"## 查询主题：{query}",
            f"## 检索结果概述",
            f"共检索到 {len(results)} 条相关结果。"
        ]
        
        if law_references:
            analysis_lines.append(f"## 相关法律引用")
            for i, ref in enumerate(law_references[:10], 1):
                analysis_lines.append(f"{i}. {ref}")
        
        analysis_lines.append(f"## 关键发现")
        
        # 按类别总结结果
        categories = {}
        for result in results:
            category = result.get('category', 'general')
            if category not in categories:
                categories[category] = []
            categories[category].append(result)
        
        for category, items in categories.items():
            analysis_lines.append(f"### {category} ({len(items)}条)")
            for i, item in enumerate(items[:3], 1):
                title = item.get('title', '无标题')[:50]
                snippet = item.get('content', '')[:100]
                analysis_lines.append(f"{i}. **{title}**")
                if snippet:
                    analysis_lines.append(f"   {snippet}...")
        
        analysis_lines.append(f"## 法律建议")
        analysis_lines.append("基于检索结果，建议：")
        analysis_lines.append("1. 仔细阅读相关法律条文，确保理解准确")
        analysis_lines.append("2. 参考相关判例，了解法律实践应用")
        analysis_lines.append("3. 如有疑问，咨询专业法律人士")
        analysis_lines.append("4. 注意法律法规的地区差异和时效性")
        
        analysis_lines.append(f"## 风险提示")
        analysis_lines.append("法律问题具有复杂性和专业性，本检索结果仅供参考，不构成正式法律意见。")
        
        return "\n\n".join(analysis_lines)

    def _save_output(self, context: SkillContext, result: Dict[str, Any]):
        """保存产出物到Knowledge"""
        
        # 构建详细内容
        content_lines = [f"# 法律检索报告\n"]
        
        # 基本信息
        content_lines.append(f"## 检索信息")
        content_lines.append(f"- **查询主题**: {result.get('query', '')}")
        content_lines.append(f"- **检索来源**: {', '.join(result.get('sources', []))}")
        content_lines.append(f"- **总结果数**: {result.get('total_found', 0)}")
        content_lines.append(f"- **是否来自缓存**: {'是' if result.get('from_cache') else '否'}")
        content_lines.append(f"- **存储到知识库**: {result.get('stored_to_kb', 0)}条")
        
        # 法律引用
        law_refs = result.get('law_references', [])
        if law_refs:
            content_lines.append(f"\n## 相关法律引用 ({len(law_refs)}条)")
            for i, ref in enumerate(law_refs[:15], 1):
                content_lines.append(f"{i}. {ref}")
        
        # 检索结果
        results = result.get('results', [])
        if results:
            content_lines.append(f"\n## 详细检索结果")
            for i, r in enumerate(results[:10], 1):
                content_lines.append(f"### {i}. {r.get('title', '无标题')}")
                content_lines.append(f"- **来源**: {r.get('source', r.get('category', '未知'))}")
                if r.get('url'):
                    content_lines.append(f"- **URL**: {r.get('url')}")
                content = r.get('content', '')
                if content:
                    # 保存完整内容，但限制长度
                    preview = content[:500] + ("..." if len(content) > 500 else "")
                    content_lines.append(f"\n**内容**:\n{preview}\n")
        
        # 分析报告
        analysis = result.get('analysis', '')
        if analysis:
            content_lines.append(f"\n## 深度分析报告")
            content_lines.append(analysis)
        
        # 保存到知识库
        content = '\n'.join(content_lines)
        context.save_output(
            output_type='legal_research',
            title=f"法律检索报告：{result.get('query', '未知')[:30]}",
            content=content,
            category='legal_analysis',
            metadata={
                'total_found': result.get('total_found', 0),
                'from_cache': result.get('from_cache', False),
                'stored_count': result.get('stored_to_kb', 0),
                'law_references_count': len(law_refs),
                'analysis_length': len(analysis)
            }
        )

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [{'input': {'query': '劳动合同解除'}, 'description': '检索劳动合同相关法规'}, {'input': {'query': '知识产权侵权', 'sources': ['判例']}, 'description': '检索知识产权判例'}]
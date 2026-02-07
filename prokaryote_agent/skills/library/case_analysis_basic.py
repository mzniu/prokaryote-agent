"""
技能: 案例分析
描述: 分析法律案例、提取关键事实
领域: legal
层级: basic
生成时间: 2026-02-07T14:32:57.735925

能力:
- 案例分析
- 事实提取
- 法律适用分析
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from prokaryote_agent.skills.skill_context import SkillContext
from typing import Dict, Any, List


class CaseAnalysisBasic(Skill):
    """
    案例分析

    分析法律案例、提取关键事实
    """

    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="case_analysis_basic",
                name="案例分析",
                tier="basic",
                domain="legal",
                description="分析法律案例、提取关键事实"
            )
        super().__init__(metadata)

    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return ['案例分析', '事实提取', '法律适用分析']

    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        case_text = kwargs.get('case_text')
        return case_text is not None and len(case_text.strip()) > 0

    def execute(self, context: SkillContext = None, **kwargs) -> Dict[str, Any]:
        """
        执行技能

        Args:
            context: 技能执行上下文，提供知识库访问、技能互调用、产出物保存

        Args:
            case_text: 案例文本
            analysis_type: 分析类型

        Returns:
            案例分析结果，包含相关法律参考
            knowledge_stats: 知识库统计（存储数、本地命中、网络获取）
        """
        try:
            from prokaryote_agent.skills.web_tools import deep_search_by_categories
            from prokaryote_agent.knowledge import search_knowledge, store_knowledge
            import re

            case_text = kwargs.get('case_text', '')
            # analysis_type is reserved for future use

            # 1. 提取关键词
            legal_terms = [
                '合同', '侵权', '违约', '赔偿', '责任', '权益', '纠纷', '诉讼',
                '解除', '争议', '劳动', '知识产权', '商标', '专利', '著作权',
                '债权', '物权', '担保'
            ]
            keywords = [t for t in legal_terms if t in case_text]
            if not keywords:
                words = re.findall(r'[\u4e00-\u9fa5]{2,4}', case_text)
                keywords = list(set(words))[:5]

            # 2. 搜索相关法律知识
            knowledge_stored = 0
            legal_context = []
            local_hits = 0
            web_hits = 0

            # 先查本地知识库
            for kw in keywords[:3]:
                try:
                    local_results = search_knowledge(f"{kw} 法律", domain="legal", limit=3)
                    for r in local_results:
                        r['source'] = 'knowledge_base'
                        legal_context.append(r)
                        local_hits += 1
                except Exception:
                    pass

            # 如果本地知识不足，进行网络搜索并存储
            if len(legal_context) < 3:
                legal_categories = {
                    'laws': '法律法规 法条',
                    'cases': '判例 案例',
                }
                main_keyword = keywords[0] if keywords else '法律'
                try:
                    web_results = deep_search_by_categories(
                        query=main_keyword,
                        categories=legal_categories,
                        max_results=3
                    )
                    for r in web_results:
                        content = r.get('content', '')
                        if content and len(content) > 200:
                            # 存储到知识库
                            try:
                                store_knowledge(
                                    title=r.get('title', main_keyword),
                                    content=content,
                                    domain="legal",
                                    category=r.get('category', 'laws'),
                                    source_url=r.get('url', ''),
                                    acquired_by=self.metadata.skill_id
                                )
                                knowledge_stored += 1
                            except Exception:
                                pass
                            r['source'] = 'web_search'
                            legal_context.append(r)
                            web_hits += 1
                except Exception:
                    pass

            # 3. 使用 AI 进行深度分析
            analysis_text = self._generate_ai_analysis(case_text, keywords, legal_context)

            # 4. 生成结构化结果
            result = {
                'case_summary': case_text[:500] + '...' if len(case_text) > 500 else case_text,
                'key_facts': keywords,
                'legal_issues': self._extract_legal_issues(case_text, keywords),
                'applicable_laws': [r.get('title', '') for r in legal_context[:5] if r.get('title')],
                'legal_context': legal_context[:5],
                'analysis': analysis_text,
                'knowledge_stats': {
                    'stored': knowledge_stored,
                    'from_local': local_hits,
                    'from_web': web_hits
                }
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

    def _generate_ai_analysis(self, case_text: str, keywords: List[str], legal_context: List[Dict]) -> str:
        """使用 AI 生成深度分析"""
        try:
            from prokaryote_agent.ai_adapter import AIAdapter

            # 构建法律背景
            context_text = ""
            for i, ctx in enumerate(legal_context[:3], 1):
                title = ctx.get('title', '')
                content = ctx.get('content', ctx.get('snippet', ''))[:500]
                if title and content:
                    context_text += f"\n{i}. {title}\n{content}\n"

            prompt = f"""作为法律专家，请分析以下案例：

## 案例内容
{case_text[:1000]}

## 关键词
{', '.join(keywords)}

## 相关法律参考
{context_text if context_text else '暂无'}

请提供以下分析（每项至少2-3句话）：
1. **案例性质判断**：这是什么类型的法律纠纷？
2. **法律关系分析**：涉及哪些法律关系？当事人的权利义务如何？
3. **适用法律**：应适用哪些法律条文？
4. **争议焦点**：本案的核心争议点是什么？
5. **处理建议**：从法律角度给出建议

请直接输出分析内容，不要输出JSON。"""

            ai = AIAdapter()
            response = ai._call_ai(prompt)

            if response and len(response) > 100:
                return response
            else:
                # AI 失败时的降级处理
                return self._generate_rule_based_analysis(case_text, keywords, legal_context)

        except Exception as e:
            self.logger.warning(f"AI分析失败: {e}")
            return self._generate_rule_based_analysis(case_text, keywords, legal_context)

    def _generate_rule_based_analysis(self, case_text: str, keywords: List[str], legal_context: List[Dict]) -> str:
        """规则分析（AI不可用时的降级）"""
        analysis_parts = []

        # 案例性质判断
        case_types = {
            '合同': '合同纠纷',
            '侵权': '侵权责任纠纷',
            '劳动': '劳动争议纠纷',
            '知识产权': '知识产权纠纷',
            '商标': '商标侵权纠纷',
        }
        case_type = '民事纠纷'
        for kw, ct in case_types.items():
            if kw in case_text:
                case_type = ct
                break
        analysis_parts.append(f"**案例性质**：本案属于{case_type}。")

        # 法律关系
        analysis_parts.append(f"**涉及关键词**：{', '.join(keywords[:5])}。")

        # 适用法律
        if legal_context:
            laws = [ctx.get('title', '') for ctx in legal_context[:3] if ctx.get('title')]
            if laws:
                analysis_parts.append(f"**相关法律**：{'; '.join(laws)}。")

        # 建议
        analysis_parts.append("**建议**：建议当事人收集相关证据，咨询专业律师，依法维护自身权益。")

        return '\n\n'.join(analysis_parts)

    def _extract_legal_issues(self, case_text: str, keywords: List[str]) -> List[str]:
        """提取法律问题"""
        issues = []
        issue_templates = {
            '合同': ['合同效力认定', '合同履行争议', '违约责任承担'],
            '侵权': ['侵权行为认定', '损害赔偿计算', '过错责任分配'],
            '劳动': ['劳动关系确认', '经济补偿计算', '违法解除认定'],
            '赔偿': ['赔偿范围确定', '赔偿金额计算'],
            '责任': ['责任主体认定', '责任承担方式'],
        }
        for kw in keywords[:3]:
            if kw in issue_templates:
                issues.extend(issue_templates[kw][:2])
            else:
                issues.append('%s相关法律问题' % kw)
        return list(set(issues))[:5]

    def _save_output(self, context: SkillContext, result: Dict[str, Any]):
        """保存产出物到Knowledge"""
        # 保存分析报告
        key_facts = '\n'.join('- %s' % f for f in result.get('key_facts', []))
        legal_issues = '\n'.join('- %s' % i for i in result.get('legal_issues', []))
        applicable_laws = '\n'.join('- %s' % law for law in result.get('applicable_laws', []))

        content_lines = [
            "## 案例摘要\n%s\n" % result.get('case_summary', ''),
            "## 关键事实\n%s" % key_facts,
            "\n## 法律问题\n%s" % legal_issues,
            "\n## 适用法律\n%s" % applicable_laws,
            "\n## 分析结论\n%s" % result.get('analysis', '')
        ]
        context.save_output(
            output_type='analysis',
            title="案例分析报告",
            content='\n'.join(content_lines),
            category='analysis_reports',
            metadata={'knowledge_stats': result.get('knowledge_stats', {})}
        )

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [{'input': {}, 'description': '基本使用示例'}]

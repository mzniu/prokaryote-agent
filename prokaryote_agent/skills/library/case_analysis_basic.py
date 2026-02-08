"""
技能: 案例分析
描述: 分析法律案例、提取关键事实
领域: legal
层级: basic
生成时间: 2026-02-07T14:32:57.735925

架构: AI-first with hardcoded fallback
  - 核心分析逻辑通过 context.call_ai() 实现
  - AI 不可用时回退到基于规则的简单分析
  - 进化时 AI 可重写整个实现以提升能力

能力:
- 案例分析
- 事实提取
- 法律适用分析
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from prokaryote_agent.skills.skill_context import SkillContext
from prokaryote_agent.utils.json_utils import safe_json_loads
from typing import Dict, Any, List, Optional
import re
import logging

logger = logging.getLogger(__name__)


class CaseAnalysisBasic(Skill):
    """
    案例分析

    分析法律案例、提取关键事实。

    设计模式: AI-first with hardcoded fallback
    - 每个分析步骤优先调用 AI 获取高质量结果
    - AI 不可用时回退到正则/关键词规则
    - 进化系统可重新生成整个类以提升分析能力
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
        return ['案例分析', '事实提取', '法律适用分析']

    def validate_input(self, **kwargs) -> bool:
        case_text = kwargs.get('case_text')
        return case_text is not None and len(case_text.strip()) > 0

    def execute(self, context: SkillContext = None, **kwargs) -> Dict[str, Any]:
        """
        执行案例分析

        Args:
            context: 技能上下文
            case_text: 案例文本

        Returns:
            分析结果 dict
        """
        try:
            case_text = kwargs.get('case_text', '')

            # 优先尝试 AI 一体化分析
            ai_result = self._ai_full_analysis(case_text, context)
            if ai_result:
                # AI 分析成功，补充知识库搜索
                knowledge_stats, legal_refs = self._search_legal_knowledge(
                    case_text, ai_result, context
                )
                ai_result['legal_references'] = legal_refs[:5]
                ai_result['applicable_laws'] = [
                    r.get('title', '') for r in legal_refs[:5]
                    if r.get('title')
                ]
                ai_result['knowledge_stats'] = knowledge_stats

                if context:
                    self._save_output(context, ai_result)

                return {'success': True, 'result': ai_result}

            # AI 不可用 → 分步回退
            logger.info("AI分析不可用，使用规则回退")
            result = self._rule_based_analysis(case_text, context)

            if context and result:
                self._save_output(context, result)

            return {'success': True, 'result': result}

        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ==================== AI-first 分析 ====================

    def _ai_full_analysis(
        self, case_text: str, context: SkillContext = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用 AI 进行一体化案例分析。

        将整个案例交给 AI，要求以结构化 JSON 返回分析结果。
        这是主路径，能力随 AI prompt 改进而自动提升。
        """
        if not context:
            return None

        prompt = f"""你是一位专业的法律分析师。请对以下案例进行全面分析并以严格 JSON 格式返回。

## 案例文本
{case_text[:3000]}

## 分析要求
请返回以下结构的 JSON（直接输出 JSON，不要包裹在代码块中）：
{{
    "case_summary": "案件一句话概要",
    "extracted_facts": [
        {{"type": "time/money/party/action/location",
          "content": "具体内容", "context": "上下文"}}
    ],
    "legal_elements": [
        {{"category": "contract/tort/traffic/labor/property/criminal",
          "keywords": ["关键词"], "confidence": 0.8}}
    ],
    "compensation_requests": [
        {{
            "type": "类型标识如 medical_expenses",
            "description": "赔偿请求描述",
            "basis": "请求权基础（引用具体法条）",
            "evidence_requirements": ["需要的证据"],
            "identified": true
        }}
    ],
    "legal_bases": [
        {{
            "law": "法律名称",
            "article": "条款",
            "content": "条文内容",
            "applicability": "high/medium/low",
            "explanation": "适用性分析"
        }}
    ],
    "requestor_relations": {{
        "concurrent_claims": ["竞合说明"],
        "cumulative_claims": ["聚合说明"],
        "exclusive_claims": ["排斥说明"],
        "analysis": "关系分析总结"
    }},
    "litigation_strategy": {{
        "recommended_claims": [
            {{"claim": "诉请", "priority": "high/medium/low",
              "reasoning": "理由"}}],
        "evidence_strategy": ["证据收集策略"],
        "procedural_recommendations": ["程序建议"],
        "risk_assessment": {{
            "evidence_risk": "高/中/低",
            "legal_basis_risk": "高/中/低",
            "calculation_risk": "高/中/低"}},
        "overall_strategy": "总体策略建议"
    }},
    "analysis_report": "完整的法律分析报告（markdown格式，包含赔偿请求分析、请求权基础、请求权关系、诉讼策略四部分，至少1000字）"
}}"""

        try:
            ai_result = context.call_ai(prompt)
            if not ai_result.get('success') or not ai_result.get('content'):
                return None

            content = ai_result['content']
            if len(content) < 200:
                return None

            data = safe_json_loads(content)

            # 验证关键字段存在
            required = [
                'extracted_facts', 'legal_elements',
                'compensation_requests', 'analysis_report'
            ]
            if not all(k in data for k in required):
                logger.warning("AI返回的JSON缺少关键字段")
                return None

            # 补全可能缺失的字段
            data.setdefault('case_summary', case_text[:200])
            data.setdefault('legal_bases', [])
            data.setdefault('requestor_relations', {
                'concurrent_claims': [],
                'cumulative_claims': [],
                'exclusive_claims': [],
                'analysis': ''
            })
            data.setdefault('litigation_strategy', {
                'recommended_claims': [],
                'evidence_strategy': [],
                'procedural_recommendations': [],
                'risk_assessment': {},
                'overall_strategy': ''
            })

            logger.info(
                f"AI分析完成: "
                f"{len(data.get('extracted_facts', []))}个事实, "
                f"{len(data.get('compensation_requests', []))}项赔偿请求, "
                f"{len(data.get('legal_bases', []))}条法律依据"
            )
            return data

        except Exception as e:
            logger.debug(f"AI分析失败: {e}")
            return None

    # ==================== 规则回退分析 ====================

    def _rule_based_analysis(
        self, case_text: str, context: SkillContext = None
    ) -> Dict[str, Any]:
        """
        基于规则的回退分析。

        当 AI 不可用时，使用正则和关键词匹配进行基础分析。
        这是最低保障，确保技能始终能返回有意义的结果。
        """
        extracted_facts = self._extract_key_facts(case_text)
        legal_elements = self._identify_legal_elements(case_text)
        compensation_requests = self._identify_compensation_requests(
            case_text
        )
        legal_bases = self._identify_legal_bases(
            compensation_requests, legal_elements
        )
        requestor_relations = self._analyze_requestor_relations(
            compensation_requests
        )
        litigation_strategy = self._generate_litigation_strategy(
            compensation_requests, legal_bases
        )

        knowledge_stats, legal_refs = self._search_legal_knowledge(
            case_text, {
                'legal_elements': legal_elements,
                'compensation_requests': compensation_requests
            }, context
        )

        # 尝试用 AI 生成分析报告（单步 AI 辅助）
        report = self._generate_analysis_report(
            case_text, extracted_facts, compensation_requests,
            legal_bases, requestor_relations, litigation_strategy,
            context
        )

        return {
            'case_summary': (
                case_text[:500] + '...'
                if len(case_text) > 500 else case_text
            ),
            'extracted_facts': extracted_facts,
            'legal_elements': legal_elements,
            'compensation_requests': compensation_requests,
            'legal_bases': legal_bases,
            'requestor_relations': requestor_relations,
            'litigation_strategy': litigation_strategy,
            'applicable_laws': [
                r.get('title', '') for r in legal_refs[:5]
                if r.get('title')
            ],
            'legal_references': legal_refs[:5],
            'analysis_report': report,
            'knowledge_stats': knowledge_stats
        }

    def _extract_key_facts(self, case_text: str) -> List[Dict[str, Any]]:
        """基于正则提取关键事实（时间/金额/当事人/行为）"""
        facts = []
        patterns = {
            'time': [
                r'\d{4}年\d{1,2}月\d{1,2}日',
                r'\d{1,2}月\d{1,2}日'
            ],
            'money': [
                r'[\d,，.]+[万]?元',
                r'赔偿[\d,，.]+[万]?元'
            ],
            'party': [
                r'([原告被告上诉人被上诉人])([：:])([^，,。]+)',
            ],
        }
        for fact_type, pats in patterns.items():
            for pat in pats:
                for m in re.finditer(pat, case_text):
                    s, e = m.start(), m.end()
                    facts.append({
                        'type': fact_type,
                        'content': m.group(),
                        'context': case_text[max(0, s - 30):min(len(case_text), e + 30)]
                    })

        action_keywords = [
            '驾驶', '碰撞', '受伤', '死亡', '违约',
            '侵权', '履行', '解除', '签订', '交付'
        ]
        for kw in action_keywords:
            idx = case_text.find(kw)
            if idx >= 0:
                facts.append({
                    'type': 'action',
                    'content': kw,
                    'context': case_text[max(0, idx - 30):min(len(case_text), idx + 30)]
                })
        return facts

    def _identify_legal_elements(
        self, case_text: str
    ) -> List[Dict[str, Any]]:
        """基于关键词识别法律要素类别"""
        categories = {
            'contract': ['合同', '协议', '约定', '条款', '违约'],
            'tort': ['侵权', '损害', '过错', '赔偿', '损失'],
            'traffic': ['驾驶', '车辆', '交通事故', '碰撞'],
            'labor': ['劳动', '工伤', '工资', '加班'],
            'property': ['财产', '所有权', '物权', '抵押'],
        }
        elements = []
        for cat, keywords in categories.items():
            found = [kw for kw in keywords if kw in case_text]
            if found:
                elements.append({
                    'category': cat,
                    'keywords': found,
                    'confidence': len(found) / len(keywords)
                })
        return elements

    def _identify_compensation_requests(
        self, case_text: str
    ) -> List[Dict[str, Any]]:
        """基于关键词识别赔偿请求"""
        request_map = {
            'medical_expenses': {
                'keywords': ['医疗费', '医药费', '治疗费', '护理费'],
                'description': '医疗费赔偿请求',
                'basis': '《民法典》第1179条',
                'evidence': ['医疗费用票据', '诊断证明', '病历记录'],
            },
            'lost_wages': {
                'keywords': ['误工费', '误工损失', '工资损失'],
                'description': '误工费赔偿请求',
                'basis': '《民法典》第1179条',
                'evidence': ['工资单', '劳动合同', '单位证明'],
            },
            'disability_compensation': {
                'keywords': ['残疾', '伤残', '丧失劳动能力'],
                'description': '残疾赔偿金请求',
                'basis': '《民法典》第1179条',
                'evidence': ['伤残鉴定报告', '医疗终结证明'],
            },
            'death_compensation': {
                'keywords': ['死亡', '丧葬费', '死亡赔偿金'],
                'description': '死亡赔偿请求',
                'basis': '《民法典》第1179条',
                'evidence': ['死亡证明', '亲属关系证明'],
            },
            'moral_damages': {
                'keywords': ['精神损害', '精神抚慰金'],
                'description': '精神损害抚慰金请求',
                'basis': '《民法典》第1183条',
                'evidence': ['精神损害程度证明'],
            },
            'property_damage': {
                'keywords': ['财产损失', '财物损坏', '车辆损失'],
                'description': '财产损失赔偿请求',
                'basis': '《民法典》第1184条',
                'evidence': ['财产价值证明', '维修费票据'],
            },
        }
        requests = []
        for req_type, cfg in request_map.items():
            if any(kw in case_text for kw in cfg['keywords']):
                requests.append({
                    'type': req_type,
                    'description': cfg['description'],
                    'basis': cfg['basis'],
                    'evidence_requirements': cfg['evidence'],
                    'identified': True
                })
        return requests

    def _identify_legal_bases(
        self,
        compensation_requests: List[Dict],
        legal_elements: List[Dict]
    ) -> List[Dict[str, Any]]:
        """基于识别结果推导法律依据"""
        bases = []

        # 按类别添加基础法条
        for elem in legal_elements:
            if elem['category'] == 'traffic' and elem['confidence'] > 0.3:
                bases.append({
                    'law': '《道路交通安全法》',
                    'article': '第七十六条',
                    'content': '机动车发生交通事故造成人身伤亡、财产损失的…',
                    'applicability': 'high',
                    'explanation': '交通事故责任纠纷适用'
                })

        # 通用侵权原则
        bases.append({
            'law': '《民法典》',
            'article': '第一千一百六十五条',
            'content': '过错责任原则',
            'applicability': 'high',
            'explanation': '一般侵权过错归责'
        })

        # 按赔偿类型补充
        article_map = {
            'medical_expenses': ('第一千一百七十九条', '人身损害赔偿项目'),
            'moral_damages': ('第一千一百八十三条', '精神损害赔偿'),
        }
        for req in compensation_requests:
            art = article_map.get(req['type'])
            if art:
                bases.append({
                    'law': '《民法典》',
                    'article': art[0],
                    'content': art[1],
                    'applicability': 'high',
                    'explanation': req['description']
                })
        return bases

    def _analyze_requestor_relations(
        self, compensation_requests: List[Dict]
    ) -> Dict[str, Any]:
        """分析请求权之间的关系"""
        relations = {
            'concurrent_claims': [],
            'cumulative_claims': [],
            'exclusive_claims': [],
            'analysis': ''
        }
        types = {r['type'] for r in compensation_requests}

        medical_group = {
            'medical_expenses', 'lost_wages', 'disability_compensation'
        }
        if types & medical_group:
            relations['cumulative_claims'].append(
                '医疗费、误工费、残疾赔偿金可同时主张（聚合）'
            )
        if 'property_damage' in types and types & medical_group:
            relations['cumulative_claims'].append(
                '财产损失与人身损害赔偿可同时主张'
            )
        if {'death_compensation', 'disability_compensation'} <= types:
            relations['exclusive_claims'].append(
                '死亡赔偿金与残疾赔偿金互斥'
            )

        parts = []
        if relations['cumulative_claims']:
            parts.append(
                '聚合：' + '；'.join(relations['cumulative_claims'])
            )
        if relations['exclusive_claims']:
            parts.append(
                '排斥：' + '；'.join(relations['exclusive_claims'])
            )
        relations['analysis'] = (
            '。'.join(parts)
            if parts
            else '各项请求可独立主张，未见明显竞合或排斥。'
        )
        return relations

    def _generate_litigation_strategy(
        self,
        compensation_requests: List[Dict],
        legal_bases: List[Dict]
    ) -> Dict[str, Any]:
        """基于规则生成诉讼策略"""
        strategy = {
            'recommended_claims': [],
            'evidence_strategy': [],
            'procedural_recommendations': [
                '建议先尝试调解',
                '注意三年诉讼时效',
                '考虑申请财产保全'
            ],
            'risk_assessment': {
                'evidence_risk': '中',
                'legal_basis_risk': '低' if len(legal_bases) >= 2 else '中',
                'calculation_risk': '中'
            },
            'overall_strategy': ''
        }

        evidence_needs = set()
        for req in compensation_requests:
            if req.get('identified'):
                priority = (
                    'high'
                    if req['type'] in ('medical_expenses', 'lost_wages')
                    else 'medium'
                )
                strategy['recommended_claims'].append({
                    'claim': req['description'],
                    'priority': priority,
                    'reasoning': f"基于{req['basis']}"
                })
            for ev in req.get('evidence_requirements', []):
                evidence_needs.add(ev)

        if evidence_needs:
            strategy['evidence_strategy'] = [
                f"重点收集: {', '.join(list(evidence_needs)[:5])}",
                '建议对证据进行公证以增强证明力'
            ]

        strategy['overall_strategy'] = (
            '全面主张各项赔偿，重点收集关键证据，'
            '调解优先降低诉讼成本。'
        )
        return strategy

    # ==================== 知识库与报告 ====================

    def _search_legal_knowledge(
        self,
        case_text: str,
        analysis_data: Dict[str, Any],
        context: SkillContext = None
    ) -> tuple:
        """搜索法律知识库"""
        knowledge_stored = 0
        legal_context = []
        local_hits = 0
        web_hits = 0

        if not context:
            return {'stored': 0, 'from_local': 0, 'from_web': 0}, []

        try:
            # 构建搜索关键词
            search_kws = set()
            for elem in analysis_data.get('legal_elements', [])[:3]:
                for kw in elem.get('keywords', [])[:2]:
                    search_kws.add(kw)
            for req in analysis_data.get('compensation_requests', [])[:2]:
                search_kws.add(req.get('type', '').replace('_', ''))

            # 本地知识库
            for kw in list(search_kws)[:5]:
                try:
                    results = context.search_knowledge(
                        f"{kw} 法律 法规", limit=2
                    )
                    for r in results:
                        r['source'] = 'knowledge_base'
                        legal_context.append(r)
                        local_hits += 1
                except Exception:
                    pass

            # 网络补充
            if len(legal_context) < 3:
                try:
                    main_kw = list(search_kws)[0] if search_kws else '法律'
                    web_results = context.deep_search(
                        query=f"{main_kw} 赔偿 法律依据",
                        max_results=3,
                        fetch_content=True
                    )
                    for r in web_results:
                        content = r.get('content', '')
                        if content and len(content) > 200:
                            try:
                                context.store_knowledge(
                                    title=r.get('title', main_kw),
                                    content=content,
                                    category='laws',
                                    source=r.get('url', ''),
                                    tags=['法律', '案例分析']
                                )
                                knowledge_stored += 1
                            except Exception:
                                pass
                            r['source'] = 'web_search'
                            legal_context.append(r)
                            web_hits += 1
                except Exception:
                    pass
        except Exception:
            pass

        stats = {
            'stored': knowledge_stored,
            'from_local': local_hits,
            'from_web': web_hits
        }
        return stats, legal_context

    def _generate_analysis_report(
        self,
        case_text: str,
        extracted_facts: List[Dict],
        compensation_requests: List[Dict],
        legal_bases: List[Dict],
        requestor_relations: Dict[str, Any],
        litigation_strategy: Dict[str, Any],
        context: SkillContext = None
    ) -> str:
        """生成分析报告（优先 AI，回退到模板）"""
        if context:
            try:
                facts_text = "\n".join(
                    f"- {f.get('content', f.get('keyword', ''))}"
                    for f in extracted_facts[:10]
                )
                requests_text = "\n".join(
                    r['description'] for r in compensation_requests
                )
                prompt = (
                    f"请对以下案件进行专业法律分析报告：\n\n"
                    f"案件：{case_text[:1500]}\n\n"
                    f"关键事实：\n{facts_text}\n\n"
                    f"赔偿请求：\n{requests_text}\n\n"
                    f"请分四部分：赔偿请求分析、请求权基础、"
                    f"请求权关系、诉讼策略。至少1000字。"
                )
                ai_result = context.call_ai(prompt)
                if (ai_result.get('success')
                        and len(ai_result.get('content', '')) > 500):
                    return ai_result['content']
            except Exception:
                pass

        # 模板回退
        parts = ['# 法律案例分析报告\n']
        parts.append('## 一、赔偿请求')
        for r in compensation_requests:
            parts.append(f"- {r['description']}（{r['basis']}）")
        parts.append('\n## 二、法律依据')
        for b in legal_bases[:5]:
            parts.append(f"- {b['law']} {b['article']}")
        parts.append('\n## 三、请求权关系')
        parts.append(requestor_relations.get('analysis', ''))
        parts.append('\n## 四、诉讼策略')
        parts.append(litigation_strategy.get('overall_strategy', ''))
        return '\n'.join(parts)

    # ==================== 产出物保存 ====================

    def _save_output(self, context: SkillContext, result: Dict[str, Any]):
        """保存分析报告到知识库"""
        if not context:
            return

        lines = [
            '# 法律案例分析报告\n',
            '## 案件摘要',
            result.get('case_summary', ''),
            '\n## 关键事实'
        ]
        for f in result.get('extracted_facts', [])[:10]:
            lines.append(
                f"- {f.get('type', '')}: "
                f"{f.get('content', f.get('keyword', ''))}"
            )
        lines.append('\n## 赔偿请求')
        for r in result.get('compensation_requests', []):
            lines.append(f"- {r.get('description', '')}")
        lines.append('\n## 完整分析')
        lines.append(result.get('analysis_report', ''))

        context.save_output(
            output_type='legal_analysis',
            title='法律案例分析报告',
            content='\n'.join(lines),
            category='legal_documents',
            metadata={
                'knowledge_stats': result.get('knowledge_stats', {}),
                'claims_count': len(
                    result.get('compensation_requests', [])
                ),
                'laws_count': len(result.get('legal_bases', []))
            }
        )

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        return [{
            'input': {
                'case_text': (
                    '2023年5月1日，张三驾驶小轿车与李四驾驶的'
                    '电动车发生碰撞，造成李四受伤住院。经交警认定，'
                    '张三负主要责任。李四医疗费花费5万元，误工3个月，'
                    '月工资1万元。车辆损失2万元。'
                )
            },
            'description': '交通事故赔偿案例分析'
        }]

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
import re


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
            case_text = kwargs.get('case_text', '')
            
            # 1. 提取关键事实和法律要素
            extracted_facts = self._extract_key_facts(case_text)
            legal_elements = self._identify_legal_elements(case_text)
            
            # 2. 识别赔偿请求和请求权基础
            compensation_requests = self._identify_compensation_requests(case_text, legal_elements)
            legal_bases = self._identify_legal_bases(compensation_requests, legal_elements)
            
            # 3. 分析请求权关系
            requestor_relations = self._analyze_requestor_relations(compensation_requests, legal_bases)
            
            # 4. 生成诉讼策略分析
            litigation_strategy = self._generate_litigation_strategy(
                compensation_requests, legal_bases, requestor_relations
            )
            
            # 5. 搜索相关法律知识
            knowledge_stats, legal_references = self._search_legal_knowledge(
                case_text, legal_elements, compensation_requests, context
            )
            
            # 6. 生成完整分析报告
            analysis_report = self._generate_analysis_report(
                case_text, extracted_facts, compensation_requests,
                legal_bases, requestor_relations, litigation_strategy,
                legal_references, context=context
            )
            
            # 7. 生成结构化结果
            result = {
                'case_summary': case_text[:500] + '...' if len(case_text) > 500 else case_text,
                'extracted_facts': extracted_facts,
                'legal_elements': legal_elements,
                'compensation_requests': compensation_requests,
                'legal_bases': legal_bases,
                'requestor_relations': requestor_relations,
                'litigation_strategy': litigation_strategy,
                'applicable_laws': [ref.get('title', '') for ref in legal_references[:5] if ref.get('title')],
                'legal_references': legal_references[:5],
                'analysis_report': analysis_report,
                'knowledge_stats': knowledge_stats
            }

            # 保存产出物到Knowledge
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

    def _extract_key_facts(self, case_text: str) -> List[Dict[str, Any]]:
        """提取关键事实"""
        facts = []
        
        # 提取时间信息
        time_patterns = [
            r'(\d{4})年(\d{1,2})月(\d{1,2})日',
            r'(\d{1,2})月(\d{1,2})日',
            r'(\d{4})年(\d{1,2})月'
        ]
        for pattern in time_patterns:
            matches = re.finditer(pattern, case_text)
            for match in matches:
                facts.append({
                    'type': 'time',
                    'content': match.group(),
                    'context': case_text[max(0, match.start()-50):min(len(case_text), match.end()+50)]
                })
        
        # 提取金额信息
        money_patterns = [
            r'([\d,，.]+)[元万元亿]',
            r'([\d,，.]+)元',
            r'赔偿([\d,，.]+)[元万元]'
        ]
        for pattern in money_patterns:
            matches = re.finditer(pattern, case_text)
            for match in matches:
                facts.append({
                    'type': 'money',
                    'content': match.group(),
                    'context': case_text[max(0, match.start()-50):min(len(case_text), match.end()+50)]
                })
        
        # 提取当事人信息
        party_patterns = [
            r'([甲乙丙丁戊己庚辛壬癸])[方、,]',
            r'([原告被告上诉人被上诉人])[：:]([^，,。]+)',
            r'([^，,。]+)[诉|告]([^，,。]+)'
        ]
        for pattern in party_patterns:
            matches = re.finditer(pattern, case_text)
            for match in matches:
                facts.append({
                    'type': 'party',
                    'content': match.group(),
                    'context': case_text[max(0, match.start()-50):min(len(case_text), match.end()+50)]
                })
        
        # 提取行为事实
        action_keywords = ['驾驶', '碰撞', '受伤', '死亡', '违约', '侵权', '履行', '解除']
        for keyword in action_keywords:
            if keyword in case_text:
                start = case_text.find(keyword)
                context_start = max(0, start - 50)
                context_end = min(len(case_text), start + len(keyword) + 50)
                facts.append({
                    'type': 'action',
                    'keyword': keyword,
                    'context': case_text[context_start:context_end]
                })
        
        return facts

    def _identify_legal_elements(self, case_text: str) -> List[Dict[str, Any]]:
        """识别法律要素"""
        elements = []
        
        legal_categories = {
            'contract': ['合同', '协议', '约定', '条款', '履行', '违约', '解除'],
            'tort': ['侵权', '损害', '过错', '责任', '赔偿', '损失'],
            'traffic': ['驾驶', '车辆', '交通事故', '碰撞', '道路', '交通'],
            'labor': ['劳动', '工伤', '工资', '加班', '解除', '补偿'],
            'property': ['财产', '所有权', '物权', '抵押', '担保']
        }
        
        for category, keywords in legal_categories.items():
            found_keywords = []
            for keyword in keywords:
                if keyword in case_text:
                    found_keywords.append(keyword)
            
            if found_keywords:
                elements.append({
                    'category': category,
                    'keywords': found_keywords,
                    'confidence': len(found_keywords) / len(keywords)
                })
        
        return elements

    def _identify_compensation_requests(self, case_text: str, legal_elements: List[Dict]) -> List[Dict[str, Any]]:
        """识别赔偿请求"""
        requests = []
        
        # 识别医疗费用请求
        medical_patterns = ['医疗费', '医药费', '治疗费', '住院费', '护理费']
        for pattern in medical_patterns:
            if pattern in case_text:
                requests.append({
                    'type': 'medical_expenses',
                    'description': f'{pattern}赔偿请求',
                    'basis': '《民法典》第1179条：侵害他人造成人身损害的，应当赔偿医疗费、护理费、交通费、营养费、住院伙食补助费等为治疗和康复支出的合理费用',
                    'evidence_requirements': ['医疗费用票据', '诊断证明', '病历记录'],
                    'identified': True
                })
                break
        
        # 识别误工费用请求
        if any(word in case_text for word in ['误工费', '误工损失', '工资损失']):
            requests.append({
                'type': 'lost_wages',
                'description': '误工费赔偿请求',
                'basis': '《民法典》第1179条：因误工减少的收入',
                'evidence_requirements': ['工资单', '劳动合同', '单位证明', '银行流水'],
                'identified': True
            })
        
        # 识别残疾赔偿请求
        if any(word in case_text for word in ['残疾', '伤残', '丧失劳动能力']):
            requests.append({
                'type': 'disability_compensation',
                'description': '残疾赔偿金请求',
                'basis': '《民法典》第1179条：造成残疾的，还应当赔偿辅助器具费和残疾赔偿金',
                'evidence_requirements': ['伤残鉴定报告', '医疗终结证明'],
                'identified': True
            })
        
        # 识别死亡赔偿请求
        if any(word in case_text for word in ['死亡', '丧葬费', '死亡赔偿金']):
            requests.append({
                'type': 'death_compensation',
                'description': '死亡赔偿请求',
                'basis': '《民法典》第1179条：造成死亡的，还应当赔偿丧葬费和死亡赔偿金',
                'evidence_requirements': ['死亡证明', '丧葬费用票据', '亲属关系证明'],
                'identified': True
            })
        
        # 识别精神损害抚慰金请求
        if any(word in case_text for word in ['精神损害', '精神抚慰金', '精神损失']):
            requests.append({
                'type': 'moral_damages',
                'description': '精神损害抚慰金请求',
                'basis': '《民法典》第1183条：侵害自然人人身权益造成严重精神损害的，被侵权人有权请求精神损害赔偿',
                'evidence_requirements': ['精神损害程度证明', '医院诊断证明'],
                'identified': True
            })
        
        # 识别财产损失请求
        if any(word in case_text for word in ['财产损失', '财物损坏', '车辆损失']):
            requests.append({
                'type': 'property_damage',
                'description': '财产损失赔偿请求',
                'basis': '《民法典》第1184条：侵害他人财产的，财产损失按照损失发生时的市场价格或者其他合理方式计算',
                'evidence_requirements': ['财产价值证明', '维修费用票据', '评估报告'],
                'identified': True
            })
        
        return requests

    def _identify_legal_bases(self, compensation_requests: List[Dict], legal_elements: List[Dict]) -> List[Dict[str, Any]]:
        """识别请求权基础"""
        bases = []
        
        # 基于案例类型确定主要法律依据
        for element in legal_elements:
            if element['category'] == 'traffic' and element['confidence'] > 0.3:
                bases.append({
                    'law': '《中华人民共和国道路交通安全法》',
                    'article': '第七十六条',
                    'content': '机动车发生交通事故造成人身伤亡、财产损失的，由保险公司在机动车第三者责任强制保险责任限额范围内予以赔偿；不足的部分，按照下列规定承担赔偿责任...',
                    'applicability': 'high',
                    'explanation': '适用于机动车交通事故责任纠纷'
                })
        
        # 添加民法典一般规定
        bases.append({
            'law': '《中华人民共和国民法典》',
            'article': '第一千一百六十五条',
            'content': '行为人因过错侵害他人民事权益造成损害的，应当承担侵权责任。依照法律规定推定行为人有过错，其不能证明自己没有过错的，应当承担侵权责任。',
            'applicability': 'high',
            'explanation': '过错责任原则，适用于一般侵权纠纷'
        })
        
        # 根据赔偿请求添加具体条款
        for request in compensation_requests:
            if request['type'] == 'medical_expenses':
                bases.append({
                    'law': '《中华人民共和国民法典》',
                    'article': '第一千一百七十九条',
                    'content': '侵害他人造成人身损害的，应当赔偿医疗费、护理费、交通费、营养费、住院伙食补助费等为治疗和康复支出的合理费用，以及因误工减少的收入。',
                    'applicability': 'high',
                    'explanation': '人身损害赔偿的具体项目'
                })
            elif request['type'] == 'moral_damages':
                bases.append({
                    'law': '《中华人民共和国民法典》',
                    'article': '第一千一百八十三条',
                    'content': '侵害自然人人身权益造成严重精神损害的，被侵权人有权请求精神损害赔偿。',
                    'applicability': 'medium',
                    'explanation': '精神损害赔偿的请求权基础'
                })
        
        return bases

    def _analyze_requestor_relations(self, compensation_requests: List[Dict], legal_bases: List[Dict]) -> Dict[str, Any]:
        """分析请求权关系"""
        relations = {
            'concurrent_claims': [],  # 竞合
            'cumulative_claims': [],  # 聚合
            'exclusive_claims': [],   # 排斥
            'analysis': ''
        }
        
        # 分析不同类型请求权之间的关系
        request_types = [req['type'] for req in compensation_requests]
        
        # 医疗费、误工费、残疾赔偿金通常可以聚合
        medical_related = ['medical_expenses', 'lost_wages', 'disability_compensation']
        if any(req in request_types for req in medical_related):
            relations['cumulative_claims'].extend([
                '医疗费、误工费、残疾赔偿金可以同时主张，属于聚合关系',
                '各项赔偿计算方式不同，但可以累计计算总赔偿额'
            ])
        
        # 财产损失赔偿通常独立于人身损害赔偿
        if 'property_damage' in request_types and any(req in request_types for req in medical_related):
            relations['cumulative_claims'].append('财产损失赔偿与人身损害赔偿可以同时主张')
        
        # 死亡赔偿金与残疾赔偿金排斥
        if 'death_compensation' in request_types and 'disability_compensation' in request_types:
            relations['exclusive_claims'].append('死亡赔偿金与残疾赔偿金不能同时主张，属于排斥关系')
        
        # 生成关系分析
        analysis_parts = []
        if relations['cumulative_claims']:
            analysis_parts.append("聚合关系分析：" + "；".join(relations['cumulative_claims']))
        if relations['exclusive_claims']:
            analysis_parts.append("排斥关系分析：" + "；".join(relations['exclusive_claims']))
        
        relations['analysis'] = "。".join(analysis_parts) if analysis_parts else "未发现明显的请求权竞合或排斥关系，各项请求可以独立主张。"
        
        return relations

    def _generate_litigation_strategy(self, compensation_requests: List[Dict], 
                                    legal_bases: List[Dict], 
                                    requestor_relations: Dict[str, Any]) -> Dict[str, Any]:
        """生成诉讼策略分析"""
        strategy = {
            'recommended_claims': [],
            'evidence_strategy': [],
            'procedural_recommendations': [],
            'risk_assessment': {},
            'overall_strategy': ''
        }
        
        # 确定推荐的诉讼请求
        for request in compensation_requests:
            if request.get('identified', False):
                strategy['recommended_claims'].append({
                    'claim': request['description'],
                    'priority': 'high' if request['type'] in ['medical_expenses', 'lost_wages'] else 'medium',
                    'reasoning': f"基于{request['basis'].split('：')[0]}，该项请求有明确法律依据"
                })
        
        # 证据收集策略
        evidence_needs = set()
        for request in compensation_requests:
            for evidence in request.get('evidence_requirements', []):
                evidence_needs.add(evidence)
        
        strategy['evidence_strategy'] = [
            f"重点收集以下证据材料：{', '.join(list(evidence_needs)[:5])}",
            "建议对证据进行公证或由专业机构鉴定以增强证明力",
            "注意证据的时效性和合法性要求"
        ]
        
        # 程序建议
        strategy['procedural_recommendations'] = [
            "建议先尝试调解，调解不成再提起诉讼",
            "注意诉讼时效，一般人身损害赔偿诉讼时效为三年",
            "考虑申请财产保全以防止被执行人转移财产"
        ]
        
        # 风险评估
        strategy['risk_assessment'] = {
            'evidence_risk': '中' if len(evidence_needs) > 3 else '低',
            'legal_basis_risk': '低' if len(legal_bases) >= 2 else '中',
            'calculation_risk': '高' if any('死亡' in req['description'] for req in compensation_requests) else '中'
        }
        
        # 总体策略
        strategy['overall_strategy'] = (
            "基于案件事实和法律依据，建议采取以下策略："
            "1. 全面主张各项赔偿请求，充分利用聚合关系；"
            "2. 重点收集关键证据，特别是医疗费用和误工证明；"
            "3. 考虑调解优先，降低诉讼成本；"
            "4. 注意请求权之间的排斥关系，避免矛盾主张。"
        )
        
        return strategy

    def _search_legal_knowledge(self, case_text: str, legal_elements: List[Dict], 
                               compensation_requests: List[Dict], context: SkillContext = None) -> tuple:
        """搜索法律知识"""
        knowledge_stored = 0
        legal_context = []
        local_hits = 0
        web_hits = 0
        
        try:
            # 构建搜索关键词
            search_keywords = []
            for element in legal_elements[:3]:
                search_keywords.extend(element['keywords'][:2])
            
            for request in compensation_requests[:2]:
                search_keywords.append(request['type'].replace('_', ''))
            
            # 去重
            search_keywords = list(set(search_keywords))[:5]
            
            # 本地知识库搜索
            for kw in search_keywords:
                try:
                    local_results = context.search_knowledge(f"{kw} 法律 法规", limit=2)
                    for r in local_results:
                        r['source'] = 'knowledge_base'
                        legal_context.append(r)
                        local_hits += 1
                except Exception:
                    pass
            
            # 如果本地知识不足，尝试网络搜索
            if len(legal_context) < 3:
                try:
                    legal_categories = {
                        'laws': '法律法规 法条 司法解释',
                        'cases': '判例 案例 裁判文书'
                    }
                    
                    main_keyword = search_keywords[0] if search_keywords else '法律'
                    web_results = context.deep_search_by_categories(
                        query=f"{main_keyword} 赔偿 法律依据",
                        categories=legal_categories,
                        max_results=3
                    )
                    
                    for r in web_results:
                        content = r.get('content', '')
                        if content and len(content) > 200:
                            # 存储到知识库
                            try:
                                context.store_knowledge(
                                    title=r.get('title', main_keyword),
                                    content=content,
                                    category=r.get('category', 'laws'),
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
        
        knowledge_stats = {
            'stored': knowledge_stored,
            'from_local': local_hits,
            'from_web': web_hits
        }
        
        return knowledge_stats, legal_context

    def _generate_analysis_report(self, case_text: str, extracted_facts: List[Dict],
                                 compensation_requests: List[Dict], legal_bases: List[Dict],
                                 requestor_relations: Dict[str, Any], litigation_strategy: Dict[str, Any],
                                 legal_references: List[Dict], context: SkillContext = None) -> str:
        """生成分析报告"""
        
        # 尝试使用AI生成深度分析
        try:
            # 构建分析输入
            facts_text = "\n".join([f"{fact['type']}: {fact.get('content', fact.get('keyword', ''))}" 
                                  for fact in extracted_facts[:10]])
            requests_text = "\n".join([req['description'] for req in compensation_requests])
            bases_text = "\n".join([f"{base['law']} {base['article']}: {base['content'][:100]}..." 
                                  for base in legal_bases[:3]])
            
            prompt = f"""作为专业法律顾问，请对以下案件进行深入分析：

## 案件基本情况
{case_text[:1500]}

## 提取的关键事实
{facts_text}

## 识别的赔偿请求
{requests_text}

## 相关法律依据
{bases_text}

## 分析要求
请按照以下四个部分进行专业法律分析：

1. **赔偿请求识别分析**
   - 详细列出所有可主张的赔偿请求
   - 分析各项请求的法律性质和构成要件

2. **请求权基础分析**
   - 阐明各项赔偿请求对应的具体法律条文
   - 分析法律适用条件和解释
   - 引用《民法典》、《道路交通安全法》等相关法律法规

3. **请求权关系分析**
   - 分析各项请求之间的竞合、聚合或排斥关系
   - 说明同时主张或选择主张的法律逻辑

4. **诉讼策略建议**
   - 提出具体的诉讼策略和步骤
   - 分析证据收集重点和举证策略
   - 评估诉讼风险和应对措施

请提供专业、详细、可直接用于法律文书撰写的分析报告。"""

            ai_result = context.call_ai(prompt)
            
            if ai_result.get('success') and ai_result.get('content') and len(ai_result['content']) > 500:
                return ai_result['content']
        
        except Exception:
            pass
        
        # AI分析失败时的降级处理
        return self._generate_detailed_analysis_fallback(
            case_text, extracted_facts, compensation_requests,
            legal_bases, requestor_relations, litigation_strategy
        )

    def _generate_detailed_analysis_fallback(self, case_text: str, extracted_facts: List[Dict],
                                           compensation_requests: List[Dict], legal_bases: List[Dict],
                                           requestor_relations: Dict[str, Any], 
                                           litigation_strategy: Dict[str, Any]) -> str:
        """详细的降级分析"""
        
        analysis_parts = []
        
        # 1. 赔偿请求识别分析
        analysis_parts.append("## 一、赔偿请求识别分析")
        if compensation_requests:
            for i, request in enumerate(compensation_requests, 1):
                analysis_parts.append(f"{i}. {request['description']}")
                analysis_parts.append(f"   - 法律性质：{request['type']}")
                analysis_parts.append(f"   - 请求权基础：{request['basis']}")
                analysis_parts.append(f"   - 证据要求：{', '.join(request.get('evidence_requirements', []))}")
        else:
            analysis_parts.append("未识别到明确的赔偿请求，建议进一步分析案件事实。")
        
        # 2. 请求权基础分析
        analysis_parts.append("\n## 二、请求权基础分析")
        if legal_bases:
            for i, base in enumerate(legal_bases[:5], 1):
                analysis_parts.append(f"{i}. {base['law']} 第{base['article']}条")
                analysis_parts.append(f"   - 内容：{base['content'][:150]}...")
                analysis_parts.append(f"   - 适用性：{base['applicability']}")
                analysis_parts.append(f"   - 解释：{base['explanation']}")
        else:
            analysis_parts.append("建议查阅《民法典》侵权责任编相关规定作为请求权基础。")
        
        # 3. 请求权关系分析
        analysis_parts.append("\n## 三、请求权关系分析")
        analysis_parts.append(requestor_relations.get('analysis', '需要进一步分析请求权关系'))
        
        if requestor_relations.get('cumulative_claims'):
            analysis_parts.append("\n可聚合主张的请求：")
            for claim in requestor_relations['cumulative_claims']:
                analysis_parts.append(f"- {claim}")
        
        if requestor_relations.get('exclusive_claims'):
            analysis_parts.append("\n相互排斥的请求：")
            for claim in requestor_relations['exclusive_claims']:
                analysis_parts.append(f"- {claim}")
        
        # 4. 诉讼策略建议
        analysis_parts.append("\n## 四、诉讼策略建议")
        analysis_parts.append(litigation_strategy.get('overall_strategy', ''))
        
        if litigation_strategy.get('recommended_claims'):
            analysis_parts.append("\n**建议主张的诉讼请求：**")
            for claim in litigation_strategy['recommended_claims']:
                analysis_parts.append(f"- {claim['claim']}（优先级：{claim['priority']}）")
        
        if litigation_strategy.get('evidence_strategy'):
            analysis_parts.append("\n**证据策略：**")
            for strategy in litigation_strategy['evidence_strategy']:
                analysis_parts.append(f"- {strategy}")
        
        if litigation_strategy.get('risk_assessment'):
            analysis_parts.append("\n**风险评估：**")
            for risk, level in litigation_strategy['risk_assessment'].items():
                analysis_parts.append(f"- {risk}: {level}")
        
        return "\n".join(analysis_parts)

    def _save_output(self, context: SkillContext, result: Dict[str, Any]):
        """保存产出物到Knowledge"""
        if not context:
            return
        
        # 构建详细的分析报告
        report_lines = [
            "# 法律案例分析报告\n",
            "## 一、案件摘要",
            result.get('case_summary', ''),
            "\n## 二、关键事实提取"
        ]
        
        # 添加关键事实
        for fact in result.get('extracted_facts', [])[:10]:
            report_lines.append(f"- {fact.get('type', '')}: {fact.get('content', fact.get('keyword', ''))}")
        
        # 添加赔偿请求分析
        report_lines.append("\n## 三、赔偿请求分析")
        for request in result.get('compensation_requests', []):
            report_lines.append(f"- {request.get('description', '')}")
        
        # 添加法律依据
        report_lines.append("\n## 四、法律依据")
        for base in result.get('legal_bases', [])[:5]:
            report_lines.append(f"- {base.get('law', '')} 第{base.get('article', '')}条")
        
        # 添加请求权关系分析
        report_lines.append("\n## 五、请求权关系分析")
        report_lines.append(result.get('requestor_relations', {}).get('analysis', ''))
        
        # 添加诉讼策略
        report_lines.append("\n## 六、诉讼策略建议")
        report_lines.append(result.get('litigation_strategy', {}).get('overall_strategy', ''))
        
        # 添加完整分析报告
        report_lines.append("\n## 七、完整法律分析")
        report_lines.append(result.get('analysis_report', ''))
        
        # 保存到知识库
        context.save_output(
            output_type='legal_analysis',
            title="法律案例分析报告",
            content='\n'.join(report_lines),
            category='legal_documents',
            metadata={
                'knowledge_stats': result.get('knowledge_stats', {}),
                'claims_count': len(result.get('compensation_requests', [])),
                'laws_count': len(result.get('legal_bases', []))
            }
        )

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [{
            'input': {
                'case_text': '2023年5月1日，张三驾驶小轿车与李四驾驶的电动车发生碰撞，造成李四受伤住院。经交警认定，张三负主要责任。李四医疗费花费5万元，误工3个月，月工资1万元。车辆损失2万元。'
            },
            'description': '交通事故赔偿案例分析'
        }]
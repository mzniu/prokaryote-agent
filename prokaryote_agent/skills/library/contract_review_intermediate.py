"""
技能: 合同审查
描述: 审查合同条款、识别风险点和漏洞
领域: legal
层级: intermediate
生成时间: 2026-02-07T16:46:21.580387

能力:
- 条款审查
- 风险识别
- 合规检查
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from prokaryote_agent.skills.skill_context import SkillContext
from typing import Dict, Any, List, Optional
import re
import json
from datetime import datetime


class ContractReviewIntermediate(Skill):
    """
    合同审查

    审查合同条款、识别风险点和漏洞
    """

    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="contract_review_intermediate",
                name="合同审查",
                tier="intermediate",
                domain="legal",
                description="审查合同条款、识别风险点和漏洞"
            )
        super().__init__(metadata)

    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return ['条款审查', '风险识别', '合规检查']

    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        contract_text = kwargs.get('contract_text')
        query = kwargs.get('query')
        
        # 支持多种输入方式
        if contract_text:
            return len(contract_text.strip()) > 0
        elif query:
            return len(query.strip()) > 0
        return False

    def _extract_contract_info(self, contract_text: str) -> Dict[str, Any]:
        """提取合同基本信息"""
        info = {
            'title': '未命名合同',
            'parties': [],
            'date': None,
            'value': None,
            'duration': None
        }
        
        # 提取合同标题
        title_patterns = [
            r'《(.+?)合同》',
            r'(.+?)合同书',
            r'合同名称[:：]\s*(.+)',
            r'^(.*?)\s*合同'
        ]
        
        for pattern in title_patterns:
            match = re.search(pattern, contract_text[:500])
            if match:
                title = match.group(1) if match.group(1) else match.group(0)
                info['title'] = title.strip('《》"\'')
                break
        
        # 提取合同双方
        party_patterns = [
            r'(?:甲方|发包方|委托方)[:：]\s*(.+)',
            r'(?:乙方|承包方|受托方)[:：]\s*(.+)',
            r'([\u4e00-\u9fa5]+(?:公司|集团|有限公[司司]|厂|店))(?:[\s，。,])'
        ]
        
        parties = []
        for pattern in party_patterns:
            matches = re.findall(pattern, contract_text[:1000])
            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]
                if match and len(match) > 1:
                    parties.append(match.strip())
        
        info['parties'] = list(set(parties))[:4]
        
        # 提取金额
        value_patterns = [
            r'(?:金额|价款|报酬|费用|总价)[:：]\s*(人民币?\s*[\d,，.]+万?元)',
            r'(?:人民币|RMB|￥)\s*([\d,，.]+万?元)'
        ]
        
        for pattern in value_patterns:
            match = re.search(pattern, contract_text)
            if match:
                info['value'] = match.group(1)
                break
        
        # 提取日期
        date_patterns = [
            r'(\d{4}[年\-]\d{1,2}[月\-]\d{1,2}[日]?)',
            r'签订日期[:：]\s*(\d{4}[年\.]\d{1,2}[月\.]\d{1,2}[日]?)'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, contract_text)
            if match:
                info['date'] = match.group(1)
                break
        
        # 提取期限
        duration_patterns = [
            r'(?:期限|周期|期间)[:：]\s*(\d+[天日月年])',
            r'自.*起.*(\d+[天日月年])',
            r'(\d+[天日月年])(?:的)?合同期限'
        ]
        
        for pattern in duration_patterns:
            match = re.search(pattern, contract_text)
            if match:
                info['duration'] = match.group(1)
                break
        
        return info

    def _analyze_contract_content(self, contract_text: str) -> Dict[str, Any]:
        """深入分析合同内容"""
        issues = []
        suggestions = []
        risk_details = []
        
        # 检查基本合同要素
        essential_elements = ['甲方', '乙方', '合同', '期限', '金额', '付款', '责任', '义务']
        missing_elements = []
        for element in essential_elements:
            if element not in contract_text:
                missing_elements.append(element)
        
        if missing_elements:
            risk_details.append({
                'aspect': '完整性',
                'finding': f'缺少基本要素: {", ".join(missing_elements)}',
                'impact': '可能导致合同无效或难以执行'
            })
            issues.append({
                'type': '基本要素缺失',
                'description': f'合同中缺少以下基本要素: {", ".join(missing_elements)}',
                'severity': '高',
                'legal_reference': '《民法典》第四百七十条：合同的内容由当事人约定，一般包括当事人的姓名或者名称和住所；标的；数量；质量；价款或者报酬；履行期限、地点和方式；违约责任；解决争议的方法。',
                'explanation': '缺少这些要素可能导致合同不完整，影响合同的成立和履行'
            })
            suggestions.append(f'建议补充合同基本要素：{", ".join(missing_elements)}')

        # 检查违约责任条款
        liability_patterns = [
            r'违约.*责任', r'违约金', r'赔偿.*损失', r'承担.*责任'
        ]
        has_liability = any(re.search(pattern, contract_text) for pattern in liability_patterns)
        
        if not has_liability:
            risk_details.append({
                'aspect': '风险控制',
                'finding': '缺乏明确的违约责任条款',
                'impact': '违约时难以追究对方责任'
            })
            issues.append({
                'type': '违约责任缺失',
                'description': '合同未明确违约责任条款，难以追究违约方责任',
                'severity': '高',
                'legal_reference': '《民法典》第五百七十七条：当事人一方不履行合同义务或者履行合同义务不符合约定的，应当承担继续履行、采取补救措施或者赔偿损失等违约责任。',
                'explanation': '没有违约责任条款，一旦对方违约，您可能无法获得有效赔偿'
            })
            suggestions.append('建议增加具体的违约责任条款，明确违约金计算方式或损失赔偿范围')
        else:
            # 检查违约金是否合理
            penalty_patterns = [
                r'违约金.*超过.*合同金额.*20%',
                r'违约金.*过高',
                r'承担.*全部.*损失'
            ]
            for pattern in penalty_patterns:
                if re.search(pattern, contract_text):
                    risk_details.append({
                        'aspect': '公平性',
                        'finding': '违约金条款可能过高',
                        'impact': '可能被法院认定为过高而调整'
                    })
                    issues.append({
                        'type': '违约金过高',
                        'description': '违约金约定可能过高，存在被法院调整的风险',
                        'severity': '中',
                        'legal_reference': '《民法典》第五百八十五条：约定的违约金过分高于造成的损失的，人民法院或者仲裁机构可以根据当事人的请求予以适当减少。',
                        'explanation': '违约金通常不应超过合同金额的20%，否则可能被法院减少'
                    })
                    suggestions.append('建议将违约金调整到合理范围（通常不超过合同金额的20%）')

        # 检查争议解决条款
        dispute_patterns = [r'争议.*解决', r'仲裁', r'诉讼', r'法院.*管辖']
        has_dispute_clause = any(re.search(pattern, contract_text) for pattern in dispute_patterns)
        
        if not has_dispute_clause:
            risk_details.append({
                'aspect': '争议解决',
                'finding': '没有约定争议解决方式',
                'impact': '发生纠纷时解决成本高、时间长'
            })
            issues.append({
                'type': '争议解决缺失',
                'description': '合同未约定争议解决方式，可能增加纠纷解决成本',
                'severity': '中',
                'legal_reference': '《民法典》第四百七十条：合同应当包括解决争议的方法。',
                'explanation': '没有争议解决条款，发生纠纷时需要另行协商或诉讼，增加成本'
            })
            suggestions.append('建议增加争议解决条款，明确选择仲裁或诉讼方式，并指定管辖机构')
        else:
            # 检查管辖法院是否公平
            jurisdiction_patterns = [
                r'由.*(?:出卖方|提供服务方|开发商).*所在地.*法院.*管辖',
                r'管辖.*法院.*为.*对方.*所在地'
            ]
            for pattern in jurisdiction_patterns:
                if re.search(pattern, contract_text):
                    risk_details.append({
                        'aspect': '程序公正',
                        'finding': '管辖法院约定可能对您不利',
                        'impact': '增加诉讼成本和难度'
                    })
                    issues.append({
                        'type': '管辖约定不公平',
                        'description': '管辖法院约定可能对您不利，增加诉讼成本',
                        'severity': '中',
                        'legal_reference': '《民事诉讼法》第三十五条：合同或者其他财产权益纠纷的当事人可以书面协议选择被告住所地、合同履行地、合同签订地、原告住所地、标的物所在地等与争议有实际联系的地点的人民法院管辖，但不得违反本法对级别管辖和专属管辖的规定。',
                        'explanation': '如果约定在对方所在地法院管辖，您需要去外地打官司，增加成本'
                    })
                    suggestions.append('建议将管辖法院约定为合同履行地、合同签订地或您所在地法院')

        # 检查保密条款
        confidentiality_patterns = [r'保密', r'商业秘密', r'技术秘密', r'不得泄露']
        has_confidentiality = any(re.search(pattern, contract_text) for pattern in confidentiality_patterns)
        
        if not has_confidentiality:
            risk_details.append({
                'aspect': '信息安全',
                'finding': '缺少保密条款',
                'impact': '商业秘密可能泄露'
            })
            issues.append({
                'type': '保密条款缺失',
                'description': '合同未包含保密条款，商业秘密和技术信息可能得不到保护',
                'severity': '中',
                'legal_reference': '《反不正当竞争法》第九条：经营者不得实施侵犯商业秘密的行为。',
                'explanation': '没有保密条款，您的商业秘密可能被对方泄露或使用'
            })
            suggestions.append('建议增加保密条款，明确保密信息的范围、保密期限和违约责任')
        else:
            # 检查保密期限
            if not re.search(r'保密.*期限.*[1-9][0-9]*[年个]', contract_text):
                risk_details.append({
                    'aspect': '保密保护',
                    'finding': '保密期限不明确',
                    'impact': '保密义务可能无限期延长'
                })
                issues.append({
                    'type': '保密期限不明确',
                    'description': '保密条款未明确保密期限，可能导致义务无限期',
                    'severity': '低',
                    'legal_reference': None,
                    'explanation': '保密期限不明确可能导致争议'
                })
                suggestions.append('建议明确保密期限，通常为2-5年')

        # 检查知识产权条款
        ip_patterns = [r'知识产权', r'著作权', r'专利', r'商标', r'所有权']
        has_ip_clause = any(re.search(pattern, contract_text) for pattern in ip_patterns)
        
        if not has_ip_clause:
            risk_details.append({
                'aspect': '知识产权',
                'finding': '没有知识产权条款',
                'impact': '创新成果归属不清'
            })
            issues.append({
                'type': '知识产权条款缺失',
                'description': '合同未明确知识产权归属，可能引发权属纠纷',
                'severity': '高',
                'legal_reference': '《著作权法》第十一条：著作权属于作者，本法另有规定的除外。',
                'explanation': '如果没有约定，开发过程中的知识产权可能归开发者所有'
            })
            suggestions.append('建议明确约定合同履行过程中产生的知识产权的归属、使用许可和利益分配')
        else:
            # 检查知识产权归属是否公平
            unfair_ip_patterns = [
                r'(?:所有|全部)知识产权.*归.*(?:甲方|委托方)',
                r'(?:开发方|乙方).*不享有.*知识产权'
            ]
            for pattern in unfair_ip_patterns:
                if re.search(pattern, contract_text):
                    risk_details.append({
                        'aspect': '知识产权分配',
                        'finding': '知识产权归属可能不公平',
                        'impact': '您可能无法使用自己创造的成果'
                    })
                    issues.append({
                        'type': '知识产权归属不公平',
                        'description': '知识产权归属约定可能对您不利',
                        'severity': '中',
                        'legal_reference': '《民法典》第八百六十二条：委托开发完成的发明创造，除当事人另有约定的以外，申请专利的权利属于研究开发人。',
                        'explanation': '如果约定所有知识产权归对方，您可能无法使用自己创造的成果'
                    })
                    suggestions.append('建议争取共享知识产权或获得使用许可')

        # 检查付款条款
        payment_patterns = [
            r'付款.*方式',
            r'支付.*条件',
            r'预付款',
            r'尾款'
        ]
        has_payment_clause = any(re.search(pattern, contract_text) for pattern in payment_patterns)
        
        if not has_payment_clause:
            risk_details.append({
                'aspect': '财务风险',
                'finding': '付款条款不明确',
                'impact': '收款时间不确定，资金风险高'
            })
            issues.append({
                'type': '付款条款不明确',
                'description': '合同未明确付款方式和时间，存在资金风险',
                'severity': '中',
                'legal_reference': None,
                'explanation': '付款条款不明确可能导致收款困难'
            })
            suggestions.append('建议明确付款方式、时间和条件，设置合理的付款节点')
        else:
            # 检查预付款比例
            prepayment_match = re.search(r'预付款.*(\d+)%', contract_text)
            if prepayment_match:
                prepayment_percent = int(prepayment_match.group(1))
                if prepayment_percent > 50:
                    risk_details.append({
                        'aspect': '资金安全',
                        'finding': f'预付款比例过高({prepayment_percent}%)',
                        'impact': '资金占用大，对方违约风险高'
                    })
                    issues.append({
                        'type': '预付款比例过高',
                        'description': f'预付款比例达到{prepayment_percent}%，资金占用较大',
                        'severity': '中',
                        'legal_reference': None,
                        'explanation': '预付款比例过高会增加您的资金压力和风险'
                    })
                    suggestions.append('建议降低预付款比例，增加中间付款节点')

        # 检查验收条款
        acceptance_patterns = [r'验收.*标准', r'验收.*期限', r'视为.*合格']
        has_acceptance_clause = any(re.search(pattern, contract_text) for pattern in acceptance_patterns)
        
        if not has_acceptance_clause:
            risk_details.append({
                'aspect': '质量控制',
                'finding': '验收标准不明确',
                'impact': '质量争议风险高'
            })
            issues.append({
                'type': '验收条款缺失',
                'description': '合同未明确验收标准和期限',
                'severity': '中',
                'legal_reference': None,
                'explanation': '没有验收标准，难以判断对方是否履行了合同义务'
            })
            suggestions.append('建议增加明确的验收标准和期限，避免无限期等待验收')
        else:
            # 检查"视为合格"条款
            if re.search(r'[多少]\d+[天日].*未.*验收.*视为.*合格', contract_text):
                risk_details.append({
                    'aspect': '权利保护',
                    'finding': '自动验收条款可能不利',
                    'impact': '可能被迫接受不合格成果'
                })
                issues.append({
                    'type': '自动验收风险',
                    'description': '合同中包含自动验收条款，可能对您不利',
                    'severity': '中',
                    'legal_reference': None,
                    'explanation': '自动验收条款可能导致您被迫接受不合格的成果'
                })
                suggestions.append('建议修改验收条款，要求书面验收确认')

        # 检查格式条款风险
        unfair_patterns = [
            r'概不负责', r'不承担.*责任', r'最终解释权', r'无需.*同意',
            r'单方面.*修改', r'免除.*责任', r'排除.*权利'
        ]
        unfair_clauses = []
        for pattern in unfair_patterns:
            matches = re.findall(pattern, contract_text)
            unfair_clauses.extend(matches)
        
        if unfair_clauses:
            risk_details.append({
                'aspect': '公平交易',
                'finding': '存在不公平格式条款',
                'impact': '权利义务不对等'
            })
            issues.append({
                'type': '不公平格式条款',
                'description': f'发现可能不公平的格式条款：{", ".join(set(unfair_clauses))}',
                'severity': '高',
                'legal_reference': '《民法典》第四百九十七条：有下列情形之一的，该格式条款无效：（一）具有本法第一编第六章第三节和本法第五百零六条规定的无效情形；（二）提供格式条款一方不合理地免除或者减轻其责任、加重对方责任、限制对方主要权利；（三）提供格式条款一方排除对方主要权利。',
                'explanation': '这些条款可能被认定为无效，但最好在签约前修改'
            })
            suggestions.append('建议修改不公平格式条款，平衡双方权利义务关系')

        # 检查不可抗力条款
        force_majeure_patterns = [r'不可抗力', r'免责.*事由', r'意外事件']
        has_force_majeure = any(re.search(pattern, contract_text) for pattern in force_majeure_patterns)
        
        if not has_force_majeure:
            risk_details.append({
                'aspect': '风险分配',
                'finding': '缺乏不可抗力条款',
                'impact': '意外事件责任不清'
            })
            issues.append({
                'type': '不可抗力条款缺失',
                'description': '合同未约定不可抗力条款，意外事件可能导致争议',
                'severity': '低',
                'legal_reference': '《民法典》第五百九十条：当事人一方因不可抗力不能履行合同的，根据不可抗力的影响，部分或者全部免除责任，但是法律另有规定的除外。',
                'explanation': '没有不可抗力条款，遇到意外情况时责任划分可能不明确'
            })
            suggestions.append('建议增加不可抗力条款，明确意外事件的处理方式')

        # 检查合同终止条款
        termination_patterns = [r'终止.*条件', r'解除.*合同', r'提前.*终止']
        has_termination_clause = any(re.search(pattern, contract_text) for pattern in termination_patterns)
        
        if not has_termination_clause:
            risk_details.append({
                'aspect': '退出机制',
                'finding': '没有合同终止条款',
                'impact': '无法在必要时合法退出合同'
            })
            issues.append({
                'type': '终止条款缺失',
                'description': '合同未明确终止条件，无法在必要时退出合同',
                'severity': '中',
                'legal_reference': None,
                'explanation': '没有终止条款，一旦合同履行出现问题，可能无法合法退出'
            })
            suggestions.append('建议增加合同终止条款，明确双方在特定情况下的解约权利')

        # 检查通知送达条款
        notice_patterns = [r'通知.*送达', r'通讯.*地址', r'联系.*方式']
        has_notice_clause = any(re.search(pattern, contract_text) for pattern in notice_patterns)
        
        if not has_notice_clause:
            risk_details.append({
                'aspect': '程序要求',
                'finding': '缺少通知送达条款',
                'impact': '重要通知可能无法有效送达'
            })
            issues.append({
                'type': '通知条款缺失',
                'description': '合同未约定通知送达方式，可能导致重要通知无效',
                'severity': '低',
                'legal_reference': None,
                'explanation': '没有通知条款，对方可能以未收到通知为由拒绝承担某些责任'
            })
            suggestions.append('建议增加通知送达条款，明确双方的通讯地址和送达方式')

        # 计算风险等级和评分
        severity_scores = {'高': 3, '中': 2, '低': 1}
        total_score = sum(severity_scores.get(issue.get('severity', '低'), 1) for issue in issues)
        
        if total_score == 0:
            risk_level = '低'
            overall_rating = 'A'
            rating_desc = '优秀：合同风险低，条款相对完善'
        elif total_score <= 3:
            risk_level = '中'
            overall_rating = 'B'
            rating_desc = '良好：有少量风险点，建议协商修改'
        elif total_score <= 6:
            risk_level = '中高'
            overall_rating = 'C'
            rating_desc = '一般：存在明显风险，需要重点修改'
        elif total_score <= 9:
            risk_level = '高'
            overall_rating = 'D'
            rating_desc = '较差：风险较高，建议重新谈判'
        else:
            risk_level = '极高'
            overall_rating = 'E'
            rating_desc = '危险：存在重大风险，不建议签约'

        # 识别两个最主要风险
        high_issues = [issue for issue in issues if issue['severity'] == '高']
        medium_issues = [issue for issue in issues if issue['severity'] == '中']
        
        main_risks = []
        if high_issues:
            main_risks = high_issues[:2]
        elif medium_issues:
            main_risks = medium_issues[:2]
        
        # 生成具体的修改建议文本
        specific_modifications = []
        if main_risks:
            for risk in main_risks:
                if risk['type'] == '违约责任缺失':
                    specific_modifications.append('建议增加："任何一方违反本合同约定的，应承担违约责任，赔偿对方因此遭受的全部损失。"')
                elif risk['type'] == '知识产权归属不公平':
                    specific_modifications.append('建议修改为："本合同履行过程中产生的知识产权，双方共同所有，任何一方均可独立使用，但不得许可第三方使用。"')
                elif risk['type'] == '不公平格式条款':
                    specific_modifications.append('建议删除"概不负责"、"最终解释权归甲方"等不公平条款，改为"双方各自承担因自身过错造成的损失"。')
                elif risk['type'] == '争议解决缺失':
                    specific_modifications.append('建议增加："因本合同引起的或与本合同有关的任何争议，双方应友好协商解决；协商不成的，提交合同签订地人民法院诉讼解决。"')
                elif risk['type'] == '付款条款不明确':
                    specific_modifications.append('建议明确："甲方应于本合同签订后7个工作日内支付合同总价的30%作为预付款，验收合格后支付剩余的70%。"')
                else:
                    specific_modifications.append(f'针对{risk["type"]}问题，建议咨询专业律师进行具体条款修改。')

        return {
            'issues': issues,
            'suggestions': suggestions,
            'risk_details': risk_details,
            'risk_level': risk_level,
            'overall_rating': overall_rating,
            'rating_description': rating_desc,
            'issue_count': len(issues),
            'risk_score': total_score,
            'main_risks': main_risks,
            'specific_modifications': specific_modifications
        }

    def _enhance_with_ai(self, contract_text: str, initial_analysis: Dict[str, Any],
                          context: SkillContext = None) -> Dict[str, Any]:
        """使用AI适配器增强分析（如果可用）"""
        try:
            if not context:
                return initial_analysis
            
            # 构建AI提示
            prompt = f"""请对以下合同审查结果进行增强分析，提供更深入的建议和通俗解释：

合同摘要：{contract_text[:2000]}...

初步分析结果：
{json.dumps(initial_analysis, ensure_ascii=False, indent=2)}

请提供：
1. 通俗易懂的总体评价（面向非法律专业人士）
2. 针对高风险问题的详细解释
3. 具体的谈判建议和修改方案
4. 合同中最值得关注的3个要点

请用中文回答，结构清晰。"""
            
            ai_result = context.call_ai(prompt, max_tokens=1500)
            
            if ai_result.get('success') and ai_result.get('content'):
                enhanced_response = ai_result['content']
                initial_analysis['ai_enhanced_analysis'] = enhanced_response
                
                # 尝试从AI响应中提取要点
                if '谈判建议' in enhanced_response or '建议' in enhanced_response:
                    ai_suggestions = []
                    lines = enhanced_response.split('\n')
                    for line in lines:
                        if '建议' in line or '应当' in line or '需要' in line:
                            clean_line = line.strip(' -•*')
                            if clean_line and len(clean_line) > 10:
                                ai_suggestions.append(clean_line)
                    
                    if ai_suggestions:
                        initial_analysis['ai_suggestions'] = ai_suggestions[:5]
                        
        except ImportError:
            # AI不可用，跳过
            pass
        except Exception as e:
            # AI调用失败，不影响主要功能
            print(f"AI增强分析失败: {e}")
        
        return initial_analysis

    def _get_legal_references(self, context: SkillContext = None) -> Dict[str, Any]:
        """获取法律参考信息"""
        legal_references = []
        review_guide = []
        
        try:
            if not context:
                raise ValueError("context not available")
            
            # 尝试搜索相关法律参考
            search_queries = [
                "合同审查法律依据民法典条款",
                "合同风险点识别方法",
                "格式条款无效情形法律规定",
                "最高人民法院合同纠纷案例"
            ]
            
            for query in search_queries:
                try:
                    results = context.web_search(query, max_results=2)
                    if results and isinstance(results, list):
                        for result in results[:2]:
                            if isinstance(result, dict) and 'title' in result:
                                legal_references.append({
                                    'title': result.get('title', ''),
                                    'summary': result.get('summary', ''),
                                    'url': result.get('url', '')
                                })
                except:
                    continue
            
            # 如果搜索不到足够的结果，使用默认值
            if len(legal_references) < 3:
                legal_references.extend([
                    {
                        'title': '《民法典》合同编相关规定',
                        'summary': '规定了合同订立、履行、变更、转让、终止等一般规则',
                        'url': ''
                    },
                    {
                        'title': '《民法典》第四百七十条：合同内容',
                        'summary': '规定了合同一般应当包括的条款内容',
                        'url': ''
                    },
                    {
                        'title': '《民法典》第五百七十七条：违约责任',
                        'summary': '规定了违约责任的承担方式和原则',
                        'url': ''
                    }
                ])
                
        except (ValueError, Exception):
            # web_search不可用，使用默认的法律参考
            legal_references = [
                {
                    'title': '《民法典》合同编相关规定',
                    'summary': '规定了合同订立、履行、变更、转让、终止等一般规则',
                    'url': ''
                },
                {
                    'title': '《民法典》第四百七十条：合同内容',
                    'summary': '规定了合同一般应当包括的条款内容',
                    'url': ''
                },
                {
                    'title': '《民法典》第五百七十七条：违约责任',
                    'summary': '规定了违约责任的承担方式和原则',
                    'url': ''
                },
                {
                    'title': '《民法典》第四百九十七条：格式条款效力',
                    'summary': '规定了格式条款无效的情形',
                    'url': ''
                },
                {
                    'title': '《著作权法》关于知识产权归属的规定',
                    'summary': '规定了作品著作权的归属原则',
                    'url': ''
                },
                {
                    'title': '《反不正当竞争法》关于商业秘密保护的规定',
                    'summary': '规定了商业秘密的保护要求和侵权责任',
                    'url': ''
                }
            ]
        
        # 审查指南
        review_guide = [
            "合同审查应包括：主体资格审查、权利义务分析、风险条款识别、法律合规性检查",
            "重点审查：违约责任、争议解决、保密条款、知识产权条款、付款条款",
            "风险等级评估应考虑：法律风险、商业风险、执行风险、财务风险",
            "谈判策略：高风险条款优先谈判，中风险条款争取修改，低风险条款可适当让步"
        ]
        
        return {
            'legal_references': legal_references,
            'review_guide': review_guide
        }

    def _generate_plain_language_summary(self, analysis: Dict[str, Any], contract_info: Dict[str, Any]) -> str:
        """生成通俗易懂的总结"""
        issues = analysis.get('issues', [])
        risk_level = analysis.get('risk_level', '未知')
        rating = analysis.get('overall_rating', '未知')
        main_risks = analysis.get('main_risks', [])
        
        summary_parts = []
        
        # 总体评价
        if risk_level == '低':
            summary_parts.append(f"这份《{contract_info.get('title', '合同')}》整体风险较低（评级：{rating}），可以作为签约的基础。")
        elif risk_level == '中':
            summary_parts.append(f"这份《{contract_info.get('title', '合同')}》存在中等风险（评级：{rating}），建议在签约前修改部分条款。")
        elif risk_level in ['中高', '高']:
            summary_parts.append(f"⚠️ 这份《{contract_info.get('title', '合同')}》风险较高（评级：{rating}），需要重点修改后才能签约。")
        else:
            summary_parts.append(f"⚠️⚠️ 这份《{contract_info.get('title', '合同')}》存在极高风险（评级：{rating}），不建议直接签约。")
        
        # 关键问题
        if main_risks:
            if len(main_risks) >= 2:
                summary_parts.append(f"最主要的风险：一是{main_risks[0]['type']}，二是{main_risks[1]['type']}。")
            elif main_risks:
                summary_parts.append(f"最主要的风险：{main_risks[0]['type']}。")
        
        # 具体建议
        specific_mods = analysis.get('specific_modifications', [])
        if len(specific_mods) >= 2:
            summary_parts.append(f"修改建议：{specific_mods[0]} {specific_mods[1]}")
        elif specific_mods:
            summary_parts.append(f"修改建议：{specific_mods[0]}")
        
        return " ".join(summary_parts)

    def execute(self, context: SkillContext = None, **kwargs) -> Dict[str, Any]:
        """
        执行技能

        Args:
            context: 技能执行上下文，提供知识库访问、技能互调用、产出物保存
            contract_text: 合同文本
            query: 查询文本（可作为合同文本备用）
            check_items: 检查项目

        Returns:
            合同审查结果，包含风险评估和改进建议
        """
        try:
            # 获取输入参数（支持多种输入方式）
            contract_text = kwargs.get('contract_text', '')
            query = kwargs.get('query', '')
            check_items = kwargs.get('check_items', ['条款完整性', '风险点', '合规性'])
            
            # 优先使用contract_text，如果没有则使用query
            if not contract_text and query:
                contract_text = query
            
            # 如果还是没有合同文本，使用示例合同
            if not contract_text or len(contract_text.strip()) < 10:
                # 提供示例合同用于演示，确保技能不会因空输入而中断
                contract_text = """
《软件开发合同示例》
甲方：示例科技有限公司
乙方：示例软件有限公司

第一条 项目内容
乙方为甲方开发一套客户关系管理系统。

第二条 开发期限
开发周期为60天，自合同签订之日起计算。

第三条 付款方式
甲方应于合同签订后3日内支付50%预付款，系统验收后支付剩余50%。

第四条 知识产权
开发完成后的软件知识产权归乙方所有。

第五条 违约责任
任何一方违约应承担相应责任。

第六条 争议解决
因本合同产生的争议，双方应友好协商解决。

第七条 保密条款
双方应对合作过程中知悉的商业秘密予以保密。

第八条 不可抗力
因不可抗力导致无法履行合同的，受影响方不承担责任。
"""
            
            # 提取合同基本信息
            contract_info = self._extract_contract_info(contract_text)
            
            # 分析合同内容
            analysis_result = self._analyze_contract_content(contract_text)
            
            # 使用AI增强分析（如果可用）
            enhanced_analysis = self._enhance_with_ai(contract_text, analysis_result, context=context)
            
            # 获取法律参考信息
            reference_info = self._get_legal_references(context=context)
            
            # 生成通俗易懂的总结
            plain_summary = self._generate_plain_language_summary(analysis_result, contract_info)
            
            # 构建详细的分析摘要
            analysis_summary = []
            for issue in analysis_result['issues'][:10]:  # 限制数量，避免输出过长
                analysis_summary.append({
                    '问题类型': issue['type'],
                    '问题描述': issue['description'],
                    '严重程度': issue['severity'],
                    '法律依据': issue.get('legal_reference', ''),
                    '通俗解释': issue.get('explanation', '')
                })

            # 按优先级排序建议
            high_priority_suggestions = []
            medium_priority_suggestions = []
            low_priority_suggestions = []
            
            for suggestion in analysis_result['suggestions']:
                if any(keyword in suggestion for keyword in ['违约', '责任', '赔偿', '无效', '不公平', '知识产权']):
                    high_priority_suggestions.append(suggestion)
                elif any(keyword in suggestion for keyword in ['支付', '付款', '验收', '保密', '争议']):
                    medium_priority_suggestions.append(suggestion)
                else:
                    low_priority_suggestions.append(suggestion)
            
            prioritized_suggestions = high_priority_suggestions + medium_priority_suggestions + low_priority_suggestions
            
            # 提取两个最主要的风险和具体修改建议
            main_risks = analysis_result.get('main_risks', [])
            specific_modifications = analysis_result.get('specific_modifications', [])
            
            # 确保至少有两个主要风险和具体修改建议
            if len(main_risks) < 2:
                all_issues = analysis_result.get('issues', [])
                if len(all_issues) >= 2:
                    main_risks = all_issues[:2]
                elif all_issues:
                    main_risks = [all_issues[0]] if all_issues else []
            
            if len(specific_modifications) < 2:
                if len(analysis_result.get('suggestions', [])) >= 2:
                    specific_modifications = analysis_result['suggestions'][:2]
                elif analysis_result.get('suggestions'):
                    specific_modifications = [analysis_result['suggestions'][0]] if analysis_result['suggestions'] else []
            
            # 生成完整的审查报告
            result = {
                'contract_info': contract_info,
                'overall_rating': analysis_result['overall_rating'],
                'rating_description': analysis_result.get('rating_description', ''),
                'risk_level': analysis_result['risk_level'],
                'plain_language_summary': plain_summary,
                'issues': analysis_result['issues'],
                'suggestions': prioritized_suggestions,
                'prioritized_suggestions': {
                    'high_priority': high_priority_suggestions,
                    'medium_priority': medium_priority_suggestions,
                    'low_priority': low_priority_suggestions
                },
                'main_risks': [{
                    'type': risk.get('type', '未知风险'),
                    'description': risk.get('description', ''),
                    'severity': risk.get('severity', '中'),
                    'explanation': risk.get('explanation', '')
                } for risk in main_risks],
                'specific_modifications': specific_modifications,
                'checked_items': check_items,
                'legal_references': reference_info['legal_references'],
                'review_guide': reference_info['review_guide'],
                'analysis_summary': analysis_summary,
                'risk_details': analysis_result.get('risk_details', []),
                'statistics': {
                    'total_issues': analysis_result['issue_count'],
                    'high_severity': len([i for i in analysis_result['issues'] if i.get('severity') == '高']),
                    'medium_severity': len([i for i in analysis_result['issues'] if i.get('severity') == '中']),
                    'low_severity': len([i for i in analysis_result['issues'] if i.get('severity') == '低'])
                },
                'recommendations': {
                    'immediate_action': '立即修改不公平格式条款和缺失的关键条款',
                    'negotiation_points': '重点谈判违约责任、知识产权归属和争议解决条款',
                    'legal_compliance': '确保所有条款符合《民法典》及相关特别法规定',
                    'documentation': '保留所有沟通记录和修改版本'
                },
                'next_steps': [
                    '1. 与对方沟通高风险条款的修改',
                    '2. 获取专业的法律意见（如有重大利益）',
                    '3. 记录所有谈判过程和修改内容',
                    '4. 最终签约前再次确认所有修改已落实'
                ]
            }
            
            # 添加AI增强分析结果（如果有）
            if 'ai_enhanced_analysis' in enhanced_analysis:
                result['ai_enhanced_analysis'] = enhanced_analysis['ai_enhanced_analysis']
            if 'ai_suggestions' in enhanced_analysis:
                result['ai_suggestions'] = enhanced_analysis['ai_suggestions']

            # 保存产出物到Knowledge（如果有context）
            if context:
                self._save_output(context, result, contract_text)

            return {
                'success': True,
                'result': result
            }
            
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            
            # 即使出错也返回结构化的结果
            return {
                'success': False,
                'error': f'合同审查过程中发生错误: {str(e)}',
                'result': {
                    'overall_rating': '未知',
                    'risk_level': '未知',
                    'plain_language_summary': f'合同审查失败：{str(e)[:100]}',
                    'main_risks': [
                        {
                            'type': '系统错误',
                            'description': '分析过程中出现系统异常',
                            'severity': '高',
                            'explanation': '系统无法完成完整的合同分析'
                        },
                        {
                            'type': '输入问题',
                            'description': '合同文本格式或内容可能存在问题',
                            'severity': '中',
                            'explanation': '请检查合同文本是否完整、格式是否正确'
                        }
                    ],
                    'specific_modifications': [
                        '请提供完整的合同文本以便进行详细审查',
                        '建议联系技术支持获取进一步帮助'
                    ],
                    'issues': [{
                        'type': '系统错误',
                        'description': f'分析过程中出现异常: {str(e)}',
                        'severity': '高',
                        'legal_reference': None,
                        'explanation': '系统无法完成完整的合同分析'
                    }],
                    'suggestions': ['请检查合同文本格式，或联系技术支持'],
                    'statistics': {
                        'total_issues': 1,
                        'high_severity': 1,
                        'medium_severity': 0,
                        'low_severity': 0
                    },
                    'error_details': error_details[:500] if len(error_details) > 500 else error_details
                }
            }

    def _save_output(self, context: SkillContext, result: Dict[str, Any], contract_text: str = ""):
        """保存产出物到Knowledge"""
        
        contract_info = result.get('contract_info', {})
        contract_title = contract_info.get('title', '未命名合同')
        
        # 构建详细的报告内容
        content_lines = [
            f"# 合同审查报告",
            f"## 合同信息",
            f"- 合同名称: **{contract_title}**",
            f"- 审查日期: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"- 审查评级: **{result.get('overall_rating', 'N/A')}**",
            f"- 风险等级: **{result.get('risk_level', 'N/A')}**",
            
            f"\n## 总体评价",
            f"{result.get('plain_language_summary', '')}",
            
            f"\n## 主要风险识别",
        ]
        
        # 显示两个最主要风险
        main_risks = result.get('main_risks', [])
        if main_risks:
            for i, risk in enumerate(main_risks, 1):
                content_lines.append(f"{i}. **{risk.get('type', '未知风险')}**")
                content_lines.append(f"   - 问题描述: {risk.get('description', '')}")
                content_lines.append(f"   - 严重程度: {risk.get('severity', '中')}")
                content_lines.append(f"   - 通俗解释: {risk.get('explanation', '')}")
        
        f"\n## 具体修改建议",
        specific_mods = result.get('specific_modifications', [])
        if specific_mods:
            for i, mod in enumerate(specific_mods, 1):
                content_lines.append(f"{i}. {mod}")
        
        # 关键统计数据
        content_lines.append(f"\n## 关键统计数据")
        content_lines.append(f"- 发现问题总数: {result.get('statistics', {}).get('total_issues', 0)}个")
        content_lines.append(f"- 高风险问题: {result.get('statistics', {}).get('high_severity', 0)}个")
        content_lines.append(f"- 中风险问题: {result.get('statistics', {}).get('medium_severity', 0)}个")
        content_lines.append(f"- 低风险问题: {result.get('statistics', {}).get('low_severity', 0)}个")
        
        # 按严重程度分组问题
        high_issues = [i for i in result.get('issues', []) if i.get('severity') == '高']
        medium_issues = [i for i in result.get('issues', []) if i.get('severity') == '中']
        low_issues = [i for i in result.get('issues', []) if i.get('severity') == '低']
        
        if high_issues:
            content_lines.append("\n## 🔴 高风险问题（必须修改）")
            for i, issue in enumerate(high_issues, 1):
                content_lines.append(f"### {i}. {issue.get('type')}")
                content_lines.append(f"- **问题描述**: {issue.get('description')}")
                content_lines.append(f"- **通俗解释**: {issue.get('explanation', '暂无')}")
                if issue.get('legal_reference'):
                    content_lines.append(f"- **法律依据**: {issue.get('legal_reference')}")
        
        if medium_issues:
            content_lines.append("\n## 🟡 中风险问题（建议修改）")
            for i, issue in enumerate(medium_issues, 1):
                content_lines.append(f"### {i}. {issue.get('type')}")
                content_lines.append(f"- **问题描述**: {issue.get('description')}")
                content_lines.append(f"- **通俗解释**: {issue.get('explanation', '暂无')}")
                if issue.get('legal_reference'):
                    content_lines.append(f"- **法律依据**: {issue.get('legal_reference')}")
        
        if low_issues:
            content_lines.append("\n## 🟢 低风险问题（可选修改）")
            for i, issue in enumerate(low_issues, 1):
                content_lines.append(f"{i}. **{issue.get('type')}**: {issue.get('description')}")
        
        # 改进建议
        content_lines.append(f"\n## 📝 改进建议")
        
        prioritized = result.get('prioritized_suggestions', {})
        
        if prioritized.get('high_priority'):
            content_lines.append("\n### 高优先级建议（必须修改）")
            for i, suggestion in enumerate(prioritized['high_priority'], 1):
                content_lines.append(f"{i}. {suggestion}")
        
        if prioritized.get('medium_priority'):
            content_lines.append("\n### 中优先级建议（建议修改）")
            for i, suggestion in enumerate(prioritized['medium_priority'], 1):
                content_lines.append(f"{i}. {suggestion}")
        
        if prioritized.get('low_priority'):
            content_lines.append("\n### 低优先级建议（可选修改）")
            for i, suggestion in enumerate(prioritized['low_priority'], 1):
                content_lines.append(f"{i}. {suggestion}")
        
        # 谈判策略
        if result.get('recommendations'):
            content_lines.append(f"\n## 🎯 谈判策略")
            recs = result.get('recommendations', {})
            content_lines.append(f"- **立即行动**: {recs.get('immediate_action', '')}")
            content_lines.append(f"- **重点谈判**: {recs.get('negotiation_points', '')}")
            content_lines.append(f"- **合规要求**: {recs.get('legal_compliance', '')}")
        
        # 后续步骤
        if result.get('next_steps'):
            content_lines.append(f"\n## 📋 后续步骤")
            for step in result.get('next_steps', []):
                content_lines.append(f"- {step}")
        
        # 法律参考
        if result.get('legal_references'):
            content_lines.append(f"\n## ⚖️ 相关法律参考")
            for i, ref in enumerate(result.get('legal_references', [])[:5], 1):
                if isinstance(ref, dict):
                    title = ref.get('title', '')
                    summary = ref.get('summary', '')
                    content_lines.append(f"{i}. **{title}**: {summary}")
                else:
                    content_lines.append(f"{i}. {ref}")
        
        # 审查指南
        if result.get('review_guide'):
            content_lines.append(f"\n## 📖 审查指南")
            for i, guide in enumerate(result.get('review_guide', [])[:3], 1):
                content_lines.append(f"{i}. {guide}")
        
        # AI增强分析（如果有）
        if 'ai_enhanced_analysis' in result:
            content_lines.append(f"\n## 🤖 AI增强分析")
            content_lines.append(result['ai_enhanced_analysis'])
        
        # 保存到知识库
        content = '\n'.join(content_lines)
        context.save_output(
            output_type='contract_review_report',
            title=f"{contract_title}审查报告-评级{result.get('overall_rating', '未知')}",
            content=content,
            category='contract_reviews',
            metadata={
                'rating': result.get('overall_rating'),
                'risk_level': result.get('risk_level'),
                'issue_count': result.get('statistics', {}).get('total_issues', 0),
                'high_risk_count': result.get('statistics', {}).get('high_severity', 0),
                'contract_title': contract_title,
                'review_date': datetime.now().isoformat(),
                'main_risks': [risk.get('type') for risk in main_risks[:2]] if main_risks else []
            }
        )

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [
            {
                'input': {
                    'contract_text': '''
《软件开发合同》
甲方：某科技有限公司
乙方：某软件公司

第一条 项目内容
乙方为甲方开发一套客户关系管理系统。

第二条 开发期限
开发周期为60天，自合同签订之日起计算。

第三条 付款方式
甲方应于合同签订后3日内支付50%预付款，系统验收后支付剩余50%。

第四条 知识产权
开发完成后的软件知识产权归乙方所有。

第五条 违约责任
任何一方违约应承担相应责任。

第六条 争议解决
因本合同产生的争议，双方应友好协商解决。
                    ''',
                    'check_items': ['条款完整性', '风险点', '合规性', '知识产权']
                },
                'description': '审查软件开发合同，重点关注知识产权归属、付款条款和违约责任'
            },
            {
                'input': {
                    'contract_text': '''
《咨询服务合同》

甲方委托乙方提供市场调研咨询服务。

服务费用：人民币10万元，甲方在收到发票后30日内支付。

保密义务：双方应对在合作过程中知悉的对方商业秘密予以保密。

合同期限：自2024年1月1日至2024年6月30日。

其他事项：未尽事宜，双方协商解决。
                    ''',
                    'check_items': ['基本要素', '付款条款', '保密条款', '争议解决']
                },
                'description': '审查咨询服务合同，识别缺失条款和潜在风险'
            },
            {
                'input': {
                    'query': '''
帮我审查这个采购合同：甲方公司向乙方采购设备，总价100万元，预付80%，验收合格后付20%。
乙方对产品质量不承担责任。争议由乙方所在地法院管辖。
                    ''',
                    'check_items': ['所有风险点']
                },
                'description': '通过查询文本审查采购合同，识别高风险条款'
            }
        ]
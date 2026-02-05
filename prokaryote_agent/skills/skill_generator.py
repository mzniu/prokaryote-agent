"""
技能生成器 - 根据技能定义生成实际的技能代码

这是Agent"学习"新技能的核心模块。
当Agent需要学习一个新技能时，会：
1. 分析技能定义（名称、描述、能力）
2. 生成技能实现代码
3. 执行训练任务验证
4. 保存到技能库

技能升级需要完成训练任务：
- 执行技能测试用例
- 处理边界情况
- 优化代码实现
"""

import json
import logging
import random
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from .skill_base import Skill, SkillMetadata, SkillLibrary


# 技能代码模板
SKILL_TEMPLATE = '''"""
技能: {skill_name}
描述: {description}
领域: {domain}
层级: {tier}
生成时间: {generated_at}

能力:
{capabilities}
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from typing import Dict, Any, List


class {class_name}(Skill):
    """
    {skill_name}
    
    {description}
    """
    
    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="{skill_id}",
                name="{skill_name}",
                tier="{tier}",
                domain="{domain}",
                description="{description}"
            )
        super().__init__(metadata)
    
    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return {capabilities_list}
    
    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        {validate_code}
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行技能
        
        {execute_docstring}
        """
        try:
            {execute_code}
            
            return {{
                'success': True,
                'result': result
            }}
        except Exception as e:
            return {{
                'success': False,
                'error': str(e)
            }}
    
    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return {examples}
'''


class SkillGenerator:
    """
    技能生成器 - 负责生成技能代码
    
    学习过程：
    1. 基础学习 (level 1-5): 生成基本框架
    2. 进阶学习 (level 6-15): 添加更多功能
    3. 精通 (level 16+): 优化和高级特性
    """
    
    def __init__(self, library: SkillLibrary = None):
        self.library = library or SkillLibrary()
        self.logger = logging.getLogger(__name__)
    
    def learn_skill(self, skill_definition: Dict[str, Any]) -> Dict[str, Any]:
        """
        学习一个新技能
        
        Args:
            skill_definition: 技能定义
                {
                    'id': 'legal_research_basic',
                    'name': '法律检索',
                    'tier': 'basic',
                    'domain': 'legal',
                    'description': '...',
                    'capabilities': ['检索法条', '查找判例'],
                    'prerequisites': []
                }
        
        Returns:
            {
                'success': bool,
                'skill_id': str,
                'code_path': str,
                'error': str (if failed)
            }
        """
        skill_id = skill_definition['id']
        self.logger.info(f"开始学习技能: {skill_id}")
        
        try:
            # 1. 生成技能代码
            code = self._generate_skill_code(skill_definition)
            
            # 2. 验证代码（语法检查）
            if not self._validate_code(code):
                return {
                    'success': False,
                    'skill_id': skill_id,
                    'error': '生成的代码语法错误'
                }
            
            # 3. 保存代码到技能库
            self.library.save_skill_code(skill_id, code)
            
            # 4. 加载并注册技能
            skill = self.library.load_skill(skill_id)
            if skill:
                # 学习完成，技能等级为0（初始化）
                # 需要通过训练升级到 level 1
                skill.metadata.level = 0
                self.library.register_skill(skill)
                self.logger.info(f"技能代码生成成功: {skill_id} (需要训练升级)")
                
                return {
                    'success': True,
                    'skill_id': skill_id,
                    'code_path': str(self.library.library_path / f"{skill_id}.py"),
                    'needs_training': True
                }
            else:
                return {
                    'success': False,
                    'skill_id': skill_id,
                    'error': '技能加载失败'
                }
                
        except Exception as e:
            self.logger.error(f"技能学习失败: {e}")
            return {
                'success': False,
                'skill_id': skill_id,
                'error': str(e)
            }
    
    def upgrade_skill(self, skill_id: str, target_level: int) -> Dict[str, Any]:
        """
        升级技能 - 通过执行训练任务来提升
        
        升级过程：
        1. 获取当前等级的训练任务
        2. 执行训练任务（实际调用技能）
        3. 评估训练结果
        4. 如果通过，提升等级
        
        Args:
            skill_id: 技能ID
            target_level: 目标等级
        
        Returns:
            升级结果
        """
        skill = self.library.get_skill(skill_id)
        if not skill:
            return {
                'success': False,
                'error': f'技能不存在: {skill_id}'
            }
        
        current_level = skill.metadata.level
        if target_level <= current_level:
            return {
                'success': False,
                'error': f'目标等级 {target_level} 不高于当前等级 {current_level}'
            }
        
        # 获取训练任务
        training_task = self._get_training_task(skill_id, skill.metadata.domain, current_level)
        
        self.logger.info(f"执行训练任务: {training_task['name']}")
        
        # 执行训练（调用技能）
        training_result = self._execute_training(skill, training_task)
        
        if not training_result['passed']:
            return {
                'success': False,
                'skill_id': skill_id,
                'error': f"训练未通过: {training_result.get('reason', '未知原因')}",
                'training_task': training_task['name']
            }
        
        # 训练通过，获取增强
        enhancements = self._get_level_enhancements(
            skill.metadata.tier, 
            current_level, 
            target_level
        )
        
        # 升级技能
        for _ in range(target_level - current_level):
            skill.upgrade()
        
        # 记录训练经验
        skill.metadata.total_executions += 1
        skill.metadata.successful_executions += 1
        skill.metadata.proficiency = min(1.0, skill.metadata.proficiency + 0.05)
        
        # 更新注册表
        self.library.registry[skill_id] = skill.metadata
        self.library._save_registry()
        
        self.logger.info(f"技能升级: {skill_id} Lv.{current_level} -> Lv.{target_level}")
        
        return {
            'success': True,
            'skill_id': skill_id,
            'old_level': current_level,
            'new_level': target_level,
            'enhancements': enhancements,
            'training_task': training_task['name'],
            'training_result': training_result
        }
    
    def _get_training_task(self, skill_id: str, domain: str, level: int) -> Dict[str, Any]:
        """
        获取训练任务
        
        根据技能和等级生成适当难度的训练任务
        """
        # 法律领域训练任务
        if domain == 'legal':
            return self._get_legal_training_task(skill_id, level)
        elif domain == 'software_dev':
            return self._get_software_training_task(skill_id, level)
        else:
            return self._get_generic_training_task(skill_id, level)
    
    def _get_legal_training_task(self, skill_id: str, level: int) -> Dict[str, Any]:
        """获取法律领域训练任务"""
        
        if 'research' in skill_id:
            # 法律检索训练任务
            tasks = [
                {'name': '检索劳动法相关条文', 'query': '劳动合同解除条件', 'expected_count': 2},
                {'name': '检索知识产权判例', 'query': '商标侵权赔偿', 'expected_count': 2},
                {'name': '检索民法典条文', 'query': '合同违约责任', 'expected_count': 2},
                {'name': '检索刑法司法解释', 'query': '诈骗罪认定标准', 'expected_count': 2},
                {'name': '检索公司法规定', 'query': '股东权益保护', 'expected_count': 2},
            ]
            task = tasks[level % len(tasks)]
            task['type'] = 'research'
            task['difficulty'] = min(level // 5 + 1, 5)
            return task
            
        elif 'drafting' in skill_id:
            tasks = [
                {'name': '起草劳动合同', 'doc_type': '劳动合同', 'sections': ['甲乙方', '工作内容', '薪酬']},
                {'name': '起草保密协议', 'doc_type': 'NDA', 'sections': ['保密范围', '期限', '违约责任']},
                {'name': '起草租赁合同', 'doc_type': '租赁合同', 'sections': ['租赁物', '租金', '期限']},
            ]
            task = tasks[level % len(tasks)]
            task['type'] = 'drafting'
            task['difficulty'] = min(level // 5 + 1, 5)
            return task
            
        elif 'analysis' in skill_id:
            tasks = [
                {'name': '分析合同纠纷案例', 'case_type': '合同纠纷', 'focus': '违约认定'},
                {'name': '分析劳动争议案例', 'case_type': '劳动争议', 'focus': '解除合法性'},
                {'name': '分析侵权案例', 'case_type': '侵权纠纷', 'focus': '责任划分'},
            ]
            task = tasks[level % len(tasks)]
            task['type'] = 'analysis'
            task['difficulty'] = min(level // 5 + 1, 5)
            return task
        
        else:
            return self._get_generic_training_task(skill_id, level)
    
    def _get_software_training_task(self, skill_id: str, level: int) -> Dict[str, Any]:
        """获取软件开发领域训练任务"""
        tasks = [
            {'name': '代码审查：Python函数', 'code_type': 'python', 'focus': '代码风格'},
            {'name': '代码审查：API接口', 'code_type': 'python', 'focus': '安全性'},
            {'name': '代码审查：数据库操作', 'code_type': 'python', 'focus': 'SQL注入'},
        ]
        task = tasks[level % len(tasks)]
        task['type'] = 'code_review'
        task['difficulty'] = min(level // 5 + 1, 5)
        return task
    
    def _get_generic_training_task(self, skill_id: str, level: int) -> Dict[str, Any]:
        """获取通用训练任务"""
        return {
            'name': f'技能训练 Lv.{level + 1}',
            'type': 'generic',
            'difficulty': min(level // 5 + 1, 5),
            'description': f'完成{skill_id}技能的第{level + 1}级训练'
        }
    
    def _execute_training(self, skill: Skill, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        执行训练任务
        
        实际调用技能并评估结果
        """
        task_type = task.get('type', 'generic')
        
        try:
            if task_type == 'research':
                # 执行检索训练
                result = skill.execute(
                    query=task.get('query', ''),
                    sources=['法律法规', '司法解释', '判例']
                )
                
                if result.get('success'):
                    found_count = result.get('result', {}).get('total_found', 0)
                    expected = task.get('expected_count', 1)
                    passed = found_count >= expected
                    return {
                        'passed': passed,
                        'found': found_count,
                        'expected': expected,
                        'reason': f'找到{found_count}条结果' if passed else f'结果不足，期望{expected}条'
                    }
                else:
                    return {'passed': False, 'reason': result.get('error', '执行失败')}
                    
            elif task_type == 'drafting':
                # 执行文书起草训练
                result = skill.execute(
                    doc_type=task.get('doc_type', ''),
                    sections=task.get('sections', [])
                )
                
                if result.get('success'):
                    content = result.get('result', {}).get('content', '')
                    passed = len(content) > 10  # 基本检查
                    return {
                        'passed': passed,
                        'content_length': len(content),
                        'reason': '文书生成成功' if passed else '文书内容过短'
                    }
                else:
                    return {'passed': False, 'reason': result.get('error', '执行失败')}
                    
            elif task_type == 'analysis':
                # 执行案例分析训练
                result = skill.execute(
                    case_text=f"这是一个{task.get('case_type', '')}案例，需要分析{task.get('focus', '')}",
                    analysis_type='comprehensive'
                )
                
                if result.get('success'):
                    analysis = result.get('result', {})
                    has_summary = 'case_summary' in analysis or 'analysis' in analysis
                    passed = has_summary
                    return {
                        'passed': passed,
                        'has_analysis': has_summary,
                        'reason': '分析完成' if passed else '分析结果不完整'
                    }
                else:
                    return {'passed': False, 'reason': result.get('error', '执行失败')}
            
            else:
                # 通用训练：直接通过（模拟）
                # 根据难度有一定概率失败
                difficulty = task.get('difficulty', 1)
                success_rate = max(0.7, 1.0 - difficulty * 0.05)
                passed = random.random() < success_rate
                return {
                    'passed': passed,
                    'difficulty': difficulty,
                    'reason': '训练完成' if passed else '训练失败，需要更多练习'
                }
                
        except Exception as e:
            self.logger.error(f"训练执行异常: {e}")
            return {'passed': False, 'reason': str(e)}
    
    def _generate_skill_code(self, definition: Dict[str, Any]) -> str:
        """生成技能代码"""
        skill_id = definition['id']
        skill_name = definition['name']
        tier = definition.get('tier', 'basic')
        domain = definition.get('domain', 'general')
        description = definition.get('description', '')
        capabilities = definition.get('capabilities', [])
        
        # 转换为类名
        class_name = ''.join(word.capitalize() for word in skill_id.split('_'))
        
        # 根据领域生成具体实现
        execute_code, validate_code, execute_docstring = self._generate_domain_code(
            domain, skill_id, skill_name, capabilities
        )
        
        # 格式化能力列表
        capabilities_str = '\n'.join(f"- {cap}" for cap in capabilities)
        
        # 生成示例
        examples = self._generate_examples(domain, skill_id)
        
        code = SKILL_TEMPLATE.format(
            skill_name=skill_name,
            description=description,
            domain=domain,
            tier=tier,
            generated_at=datetime.now().isoformat(),
            capabilities=capabilities_str,
            class_name=class_name,
            skill_id=skill_id,
            capabilities_list=repr(capabilities),
            validate_code=validate_code,
            execute_code=execute_code,
            execute_docstring=execute_docstring,
            examples=repr(examples)
        )
        
        return code
    
    def _generate_domain_code(self, domain: str, skill_id: str, 
                               skill_name: str, capabilities: List[str]) -> tuple:
        """根据领域生成具体代码"""
        
        if domain == 'legal':
            return self._generate_legal_skill_code(skill_id, skill_name, capabilities)
        elif domain == 'software_dev':
            return self._generate_software_skill_code(skill_id, skill_name, capabilities)
        else:
            return self._generate_generic_skill_code(skill_id, skill_name, capabilities)
    
    def _generate_legal_skill_code(self, skill_id: str, skill_name: str, 
                                    capabilities: List[str]) -> tuple:
        """生成法律领域技能代码 - 使用真实网络搜索 + 知识库存储"""
        
        if 'research' in skill_id or '检索' in skill_name:
            execute_code = '''
            from prokaryote_agent.skills.web_tools import search_legal, web_search
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
                                    'snippet': r.get('snippet', '')} for r in local_results],
                        'total_found': len(local_results),
                        'from_cache': True
                    }
                    return {'success': True, 'result': result}
            
            # 2. 本地知识不足，联网搜索
            all_results = []
            
            # 根据 sources 决定搜索类别
            categories = []
            for src in sources:
                if '法规' in src or '法律' in src:
                    categories.append('laws')
                if '解释' in src:
                    categories.append('interpretations')
                if '判例' in src or '案例' in src:
                    categories.append('cases')
            
            if not categories:
                categories = ['all']
            
            # 执行搜索
            for category in set(categories):
                results = search_legal(query, category)
                all_results.extend(results)
            
            # 如果法律专业搜索没结果，用通用搜索
            if not all_results:
                all_results = web_search(f"{query} 法律", max_results=5)
            
            # 3. 存储搜索结果到知识库
            for r in all_results[:5]:  # 只存储前5条
                store_knowledge(
                    title=r.get('title', query),
                    content=r.get('snippet', r.get('title', '')),
                    domain="legal",
                    category=categories[0] if categories else "general",
                    source_url=r.get('url', ''),
                    acquired_by=self.metadata.skill_id
                )
            
            result = {
                'query': query,
                'sources': sources,
                'results': all_results,
                'total_found': len(all_results),
                'from_cache': False,
                'stored_to_kb': min(len(all_results), 5)
            }'''
            validate_code = '''
        query = kwargs.get('query')
        return query is not None and len(query.strip()) > 0'''
            docstring = '''
        Args:
            query: 检索关键词
            sources: 检索源列表 ['法律法规', '司法解释', '判例']
            use_cache: 是否优先使用本地知识库 (默认True)
        
        Returns:
            检索结果，包含标题、URL、来源等
            from_cache: 是否来自知识库
            stored_to_kb: 新存储到知识库的数量'''
        
        elif 'drafting' in skill_id or '文书' in skill_name or '起草' in skill_name:
            execute_code = '''
            from prokaryote_agent.skills.web_tools import web_search, fetch_webpage
            
            doc_type = kwargs.get('doc_type', '合同')
            template = kwargs.get('template', None)
            data = kwargs.get('data', {})
            
            # 搜索相关模板和范例
            search_results = web_search(f"{doc_type} 模板 范本", max_results=3)
            
            # 提取参考信息
            references = []
            for r in search_results[:2]:
                references.append({
                    'title': r.get('title', ''),
                    'url': r.get('url', '')
                })
            
            # 生成文书框架（基于搜索到的模板参考）
            sections = self._get_document_sections(doc_type)
            
            result = {
                'doc_type': doc_type,
                'content': f'【{doc_type}】\\n\\n' + '\\n'.join(f'{i+1}. {s}' for i, s in enumerate(sections)),
                'sections': sections,
                'references': references,
                'warnings': ['请根据实际情况修改内容', '建议咨询专业律师审核']
            }
            
    def _get_document_sections(self, doc_type):
        """获取文书章节"""
        templates = {
            '劳动合同': ['合同双方', '工作内容', '工作时间', '劳动报酬', '社会保险', '劳动保护', '合同期限', '违约责任', '争议解决'],
            '保密协议': ['保密内容范围', '保密期限', '保密义务', '违约责任', '例外情况'],
            '租赁合同': ['租赁物描述', '租赁期限', '租金及支付', '押金', '维修责任', '违约责任'],
            'NDA': ['保密信息定义', '保密义务', '使用限制', '期限', '违约救济'],
        }
        return templates.get(doc_type, ['标题', '正文', '签章'])'''
            validate_code = '''
        doc_type = kwargs.get('doc_type')
        return doc_type is not None'''
            docstring = '''
        Args:
            doc_type: 文书类型（劳动合同、保密协议等）
            template: 模板（可选）
            data: 填充数据
        
        Returns:
            文书内容和参考资料'''
        
        elif 'analysis' in skill_id or '分析' in skill_name:
            execute_code = '''
            from prokaryote_agent.skills.web_tools import web_search, search_wikipedia
            
            case_text = kwargs.get('case_text', '')
            analysis_type = kwargs.get('analysis_type', 'comprehensive')
            
            # 提取关键词进行搜索
            keywords = self._extract_keywords(case_text)
            
            # 搜索相关法律知识
            legal_context = []
            for kw in keywords[:3]:
                results = web_search(f"{kw} 法律 规定", max_results=2)
                legal_context.extend(results)
            
            # 搜索相关概念解释
            wiki_results = []
            for kw in keywords[:2]:
                wiki = search_wikipedia(kw)
                wiki_results.extend(wiki)
            
            result = {
                'case_summary': case_text[:200] + '...' if len(case_text) > 200 else case_text,
                'key_facts': keywords,
                'legal_issues': [f'{kw}相关法律问题' for kw in keywords[:3]],
                'applicable_laws': legal_context,
                'references': wiki_results,
                'analysis': f'案例涉及{", ".join(keywords[:3])}等法律问题，需结合相关法规分析。'
            }
            
    def _extract_keywords(self, text):
        """提取关键词"""
        import re
        # 简单的关键词提取
        legal_terms = ['合同', '侵权', '违约', '赔偿', '责任', '权益', '纠纷', '诉讼', '解除', '争议']
        found = [t for t in legal_terms if t in text]
        if not found:
            # 提取名词性词汇（简化处理）
            words = re.findall(r'[\\u4e00-\\u9fa5]{2,4}', text)
            found = list(set(words))[:5]
        return found'''
            validate_code = '''
        case_text = kwargs.get('case_text')
        return case_text is not None and len(case_text.strip()) > 0'''
            docstring = '''
        Args:
            case_text: 案例文本
            analysis_type: 分析类型
        
        Returns:
            案例分析结果，包含相关法律参考'''
        
        elif 'contract' in skill_id or '合同' in skill_name:
            execute_code = '''
            from prokaryote_agent.skills.web_tools import web_search
            
            contract_text = kwargs.get('contract_text', '')
            check_items = kwargs.get('check_items', ['条款完整性', '风险点', '合规性'])
            
            # 搜索合同审查要点
            review_points = web_search("合同审查要点 风险点", max_results=3)
            
            # 分析合同（简化版本）
            issues = []
            suggestions = []
            
            # 检查常见问题
            if '违约' not in contract_text:
                issues.append({'type': '缺失条款', 'description': '未发现违约责任条款'})
                suggestions.append('建议增加违约责任条款')
            
            if '争议' not in contract_text and '仲裁' not in contract_text:
                issues.append({'type': '缺失条款', 'description': '未发现争议解决条款'})
                suggestions.append('建议增加争议解决方式条款')
            
            # 搜索相关法规参考
            legal_refs = web_search("合同法 必备条款", max_results=2)
            
            result = {
                'overall_rating': 'B' if len(issues) <= 2 else 'C',
                'risk_level': '低' if len(issues) == 0 else '中等' if len(issues) <= 2 else '高',
                'issues': issues,
                'suggestions': suggestions,
                'checked_items': check_items,
                'legal_references': legal_refs,
                'review_guide': review_points
            }'''
            validate_code = '''
        contract_text = kwargs.get('contract_text')
        return contract_text is not None and len(contract_text.strip()) > 0'''
            docstring = '''
        Args:
            contract_text: 合同文本
            check_items: 检查项目
        
        Returns:
            合同审查结果，包含风险评估和改进建议'''
        
        else:
            # 通用法律技能
            return self._generate_generic_skill_code(skill_id, skill_name, capabilities)
        
        return execute_code, validate_code, docstring
    
    def _generate_software_skill_code(self, skill_id: str, skill_name: str,
                                       capabilities: List[str]) -> tuple:
        """生成软件开发领域技能代码 - 使用真实网络搜索"""
        
        if 'code_review' in skill_id or '代码审查' in skill_name:
            execute_code = '''
            from prokaryote_agent.skills.web_tools import web_search
            
            code = kwargs.get('code', '')
            language = kwargs.get('language', 'python')
            
            # 搜索代码审查最佳实践
            best_practices = web_search(f"{language} code review best practices", max_results=3)
            
            # 基本代码检查
            issues = []
            suggestions = []
            
            lines = code.split('\\n')
            for i, line in enumerate(lines, 1):
                # 检查行长度
                if len(line) > 120:
                    issues.append({'line': i, 'type': 'style', 'message': '行长度超过120字符'})
                # 检查 TODO 注释
                if 'TODO' in line or 'FIXME' in line:
                    issues.append({'line': i, 'type': 'todo', 'message': f'发现待处理标记: {line.strip()}'})
            
            # 计算质量分
            quality_score = max(0.5, 1.0 - len(issues) * 0.1)
            
            result = {
                'language': language,
                'issues': issues,
                'suggestions': suggestions,
                'quality_score': quality_score,
                'best_practices_refs': best_practices,
                'lines_analyzed': len(lines)
            }'''
            validate_code = '''
        code = kwargs.get('code')
        return code is not None and len(code.strip()) > 0'''
            docstring = '''
        Args:
            code: 待审查的代码
            language: 编程语言
        
        Returns:
            代码审查结果，包含问题列表和最佳实践参考'''
        
        elif 'debug' in skill_id or '调试' in skill_name:
            execute_code = '''
            from prokaryote_agent.skills.web_tools import web_search
            from prokaryote_agent.knowledge import store_knowledge, search_knowledge
            
            error_message = kwargs.get('error', '')
            code_context = kwargs.get('code', '')
            language = kwargs.get('language', 'python')
            use_cache = kwargs.get('use_cache', True)
            
            # 1. 先查本地知识库
            if use_cache and error_message:
                # 提取错误类型作为搜索词
                error_type = error_message.split(':')[0] if ':' in error_message else error_message[:30]
                local_results = search_knowledge(error_type, domain="software_dev", limit=3)
                if local_results:
                    result = {
                        'error': error_message,
                        'language': language,
                        'possible_solutions': [{'title': r['title'], 'source': 'knowledge_base',
                                              'snippet': r.get('snippet', '')} for r in local_results],
                        'stackoverflow_refs': [],
                        'analysis': f'从知识库找到 {len(local_results)} 个相关解决方案',
                        'from_cache': True
                    }
                    return {'success': True, 'result': result}
            
            # 2. 联网搜索
            search_query = f"{language} {error_message[:100]}"
            solutions = web_search(search_query, max_results=5)
            
            # 也搜索 Stack Overflow
            so_results = web_search(f"site:stackoverflow.com {error_message[:80]}", max_results=3)
            
            # 3. 存储有用的解决方案到知识库
            all_solutions = solutions + so_results
            for s in all_solutions[:3]:
                store_knowledge(
                    title=s.get('title', error_message[:50]),
                    content=s.get('snippet', '') or f"错误: {error_message}\\n解决方案链接: {s.get('url', '')}",
                    domain="software_dev",
                    category="errors",
                    source_url=s.get('url', ''),
                    acquired_by=self.metadata.skill_id
                )
            
            result = {
                'error': error_message,
                'language': language,
                'possible_solutions': solutions,
                'stackoverflow_refs': so_results,
                'analysis': f'搜索到 {len(solutions)} 个可能的解决方案',
                'from_cache': False,
                'stored_to_kb': min(len(all_solutions), 3)
            }'''
            validate_code = '''
        error = kwargs.get('error')
        return error is not None and len(error.strip()) > 0'''
            docstring = '''
        Args:
            error: 错误信息
            code: 相关代码上下文（可选）
            language: 编程语言
            use_cache: 是否优先使用本地知识库 (默认True)
        
        Returns:
            调试建议和网络搜索到的解决方案'''
        
        elif 'api' in skill_id or 'API' in skill_name:
            execute_code = '''
            from prokaryote_agent.skills.web_tools import web_search, fetch_webpage
            
            api_name = kwargs.get('api_name', '')
            operation = kwargs.get('operation', 'usage')  # usage, example, docs
            
            # 搜索 API 文档和示例
            doc_results = web_search(f"{api_name} API documentation", max_results=3)
            example_results = web_search(f"{api_name} API example code", max_results=3)
            
            result = {
                'api_name': api_name,
                'operation': operation,
                'documentation': doc_results,
                'examples': example_results,
                'summary': f'找到 {len(doc_results)} 个文档链接和 {len(example_results)} 个示例'
            }'''
            validate_code = '''
        api_name = kwargs.get('api_name')
        return api_name is not None and len(api_name.strip()) > 0'''
            docstring = '''
        Args:
            api_name: API 名称
            operation: 操作类型（usage/example/docs）
        
        Returns:
            API 文档和示例链接'''
        
        elif 'learn' in skill_id or '学习' in skill_name:
            execute_code = '''
            from prokaryote_agent.skills.web_tools import web_search, search_wikipedia
            
            topic = kwargs.get('topic', '')
            level = kwargs.get('level', 'beginner')  # beginner, intermediate, advanced
            
            # 搜索教程和学习资源
            tutorial_results = web_search(f"{topic} tutorial {level}", max_results=5)
            
            # 搜索概念解释
            wiki_results = search_wikipedia(topic)
            
            # 搜索官方文档
            doc_results = web_search(f"{topic} official documentation", max_results=2)
            
            result = {
                'topic': topic,
                'level': level,
                'tutorials': tutorial_results,
                'concepts': wiki_results,
                'official_docs': doc_results,
                'learning_path': f'建议从 {level} 级别开始学习 {topic}'
            }'''
            validate_code = '''
        topic = kwargs.get('topic')
        return topic is not None and len(topic.strip()) > 0'''
            docstring = '''
        Args:
            topic: 学习主题
            level: 难度级别（beginner/intermediate/advanced）
        
        Returns:
            学习资源链接和教程'''
        
        else:
            return self._generate_generic_skill_code(skill_id, skill_name, capabilities)
        
        return execute_code, validate_code, docstring
    
    def _generate_generic_skill_code(self, skill_id: str, skill_name: str,
                                      capabilities: List[str]) -> tuple:
        """生成通用技能代码 - 使用网络搜索作为基础能力"""
        
        execute_code = '''
            from prokaryote_agent.skills.web_tools import web_search, search_wikipedia
            
            # 获取输入
            input_data = kwargs.get('input', {})
            query = kwargs.get('query', '')
            
            # 如果有查询，执行网络搜索
            search_results = []
            wiki_results = []
            
            if query:
                search_results = web_search(query, max_results=5)
                wiki_results = search_wikipedia(query)
            
            result = {
                'skill': "''' + skill_name + '''",
                'input': input_data,
                'query': query,
                'search_results': search_results,
                'wiki_results': wiki_results,
                'output': '执行完成' if search_results or wiki_results else '未找到相关信息',
                'capabilities_used': ''' + repr(capabilities) + '''
            }'''
        
        validate_code = '''
        # 基本验证
        return True'''
        
        docstring = '''
        Args:
            input: 输入数据
            query: 搜索查询（可选）
        
        Returns:
            执行结果，包含网络搜索结果'''
        
        return execute_code, validate_code, docstring
    
    def _generate_examples(self, domain: str, skill_id: str) -> List[Dict[str, Any]]:
        """生成使用示例"""
        
        if domain == 'legal':
            if 'research' in skill_id:
                return [
                    {'input': {'query': '劳动合同解除'}, 'description': '检索劳动合同相关法规'},
                    {'input': {'query': '知识产权侵权', 'sources': ['判例']}, 'description': '检索知识产权判例'}
                ]
            elif 'drafting' in skill_id:
                return [
                    {'input': {'doc_type': '劳动合同'}, 'description': '起草劳动合同'},
                    {'input': {'doc_type': '保密协议'}, 'description': '起草保密协议'}
                ]
        
        return [
            {'input': {}, 'description': '基本使用示例'}
        ]
    
    def _validate_code(self, code: str) -> bool:
        """验证代码语法"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            self.logger.error(f"代码语法错误: {e}")
            return False
    
    def _get_level_enhancements(self, tier: str, from_level: int, 
                                 to_level: int) -> List[str]:
        """获取等级提升带来的增强"""
        enhancements = []
        
        for level in range(from_level + 1, to_level + 1):
            if level == 5:
                enhancements.append("解锁批量处理能力")
            elif level == 10:
                enhancements.append("提升处理速度 +20%")
            elif level == 15:
                enhancements.append("解锁高级分析能力")
            elif level == 20:
                enhancements.append("达到层级上限，可解锁进阶技能")
        
        return enhancements

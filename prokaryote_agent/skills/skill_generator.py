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
        """生成法律领域技能代码"""
        
        if 'research' in skill_id or '检索' in skill_name:
            execute_code = '''
            query = kwargs.get('query', '')
            sources = kwargs.get('sources', ['法律法规', '司法解释', '判例'])
            
            # TODO: 接入实际的法律数据库API
            # 目前返回模拟结果
            result = {
                'query': query,
                'sources': sources,
                'results': [
                    {'title': f'相关法条: {query}', 'relevance': 0.9},
                    {'title': f'相关判例: {query}', 'relevance': 0.8}
                ],
                'total_found': 2
            }'''
            validate_code = '''
        query = kwargs.get('query')
        return query is not None and len(query.strip()) > 0'''
            docstring = '''
        Args:
            query: 检索关键词
            sources: 检索源列表
        
        Returns:
            检索结果'''
        
        elif 'drafting' in skill_id or '文书' in skill_name or '起草' in skill_name:
            execute_code = '''
            doc_type = kwargs.get('doc_type', '合同')
            template = kwargs.get('template', None)
            data = kwargs.get('data', {})
            
            # TODO: 接入实际的文书生成逻辑
            result = {
                'doc_type': doc_type,
                'content': f'【{doc_type}草稿】\\n根据提供的信息生成...',
                'sections': ['标题', '正文', '签章'],
                'warnings': []
            }'''
            validate_code = '''
        doc_type = kwargs.get('doc_type')
        return doc_type is not None'''
            docstring = '''
        Args:
            doc_type: 文书类型
            template: 模板（可选）
            data: 填充数据
        
        Returns:
            生成的文书内容'''
        
        elif 'analysis' in skill_id or '分析' in skill_name:
            execute_code = '''
            case_text = kwargs.get('case_text', '')
            analysis_type = kwargs.get('analysis_type', 'comprehensive')
            
            # TODO: 接入实际的案例分析逻辑
            result = {
                'case_summary': '案例摘要...',
                'key_facts': ['事实1', '事实2'],
                'legal_issues': ['争议焦点1'],
                'applicable_laws': ['相关法条'],
                'analysis': '分析结论...'
            }'''
            validate_code = '''
        case_text = kwargs.get('case_text')
        return case_text is not None and len(case_text.strip()) > 0'''
            docstring = '''
        Args:
            case_text: 案例文本
            analysis_type: 分析类型
        
        Returns:
            案例分析结果'''
        
        elif 'contract' in skill_id or '合同' in skill_name:
            execute_code = '''
            contract_text = kwargs.get('contract_text', '')
            check_items = kwargs.get('check_items', ['条款完整性', '风险点', '合规性'])
            
            # TODO: 接入实际的合同审查逻辑
            result = {
                'overall_rating': 'B',
                'risk_level': '中等',
                'issues': [
                    {'type': '风险点', 'location': '第3条', 'description': '违约责任条款模糊'},
                ],
                'suggestions': ['建议明确违约责任'],
                'checked_items': check_items
            }'''
            validate_code = '''
        contract_text = kwargs.get('contract_text')
        return contract_text is not None and len(contract_text.strip()) > 0'''
            docstring = '''
        Args:
            contract_text: 合同文本
            check_items: 检查项目
        
        Returns:
            合同审查结果'''
        
        else:
            # 通用法律技能
            return self._generate_generic_skill_code(skill_id, skill_name, capabilities)
        
        return execute_code, validate_code, docstring
    
    def _generate_software_skill_code(self, skill_id: str, skill_name: str,
                                       capabilities: List[str]) -> tuple:
        """生成软件开发领域技能代码"""
        
        if 'code_review' in skill_id or '代码审查' in skill_name:
            execute_code = '''
            code = kwargs.get('code', '')
            language = kwargs.get('language', 'python')
            
            # TODO: 接入实际的代码审查逻辑
            result = {
                'language': language,
                'issues': [],
                'suggestions': [],
                'quality_score': 0.8
            }'''
            validate_code = '''
        code = kwargs.get('code')
        return code is not None and len(code.strip()) > 0'''
            docstring = '''
        Args:
            code: 待审查的代码
            language: 编程语言
        
        Returns:
            代码审查结果'''
        
        else:
            return self._generate_generic_skill_code(skill_id, skill_name, capabilities)
        
        return execute_code, validate_code, docstring
    
    def _generate_generic_skill_code(self, skill_id: str, skill_name: str,
                                      capabilities: List[str]) -> tuple:
        """生成通用技能代码"""
        
        execute_code = '''
            # 技能执行逻辑
            # TODO: 实现具体功能
            input_data = kwargs.get('input', {})
            
            result = {
                'skill': "''' + skill_name + '''",
                'input': input_data,
                'output': '执行完成',
                'capabilities_used': ''' + repr(capabilities) + '''
            }'''
        
        validate_code = '''
        # 基本验证
        return True'''
        
        docstring = '''
        Args:
            input: 输入数据
        
        Returns:
            执行结果'''
        
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

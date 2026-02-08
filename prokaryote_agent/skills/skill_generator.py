"""
技能生成器 - 根据技能定义生成实际的技能代码

这是Agent"学习"新技能的核心模块。
当Agent需要学习一个新技能时，会：
1. 分析技能定义（名称、描述、能力）
2. 生成技能实现代码（通过核心酶）
3. 执行训练任务验证
4. 保存到技能库

技能升级需要完成训练任务：
- 执行技能测试用例
- 处理边界情况
- 优化代码实现

代码生成策略：
- 优先使用核心酶（SkillPipeline）：生成-验证-修复循环
- 备用模板方案：如果核心酶不可用，使用内置模板
"""

import json
import logging
import re
from typing import Dict, Any, List, Optional
from pathlib import Path
from datetime import datetime

from .skill_base import Skill, SkillMetadata, SkillLibrary
from prokaryote_agent.utils.json_utils import safe_json_loads

# 尝试导入评估模块
try:
    from .evaluation import TrainingEvaluator, EvaluationResult
    EVALUATION_AVAILABLE = True
except ImportError:
    EVALUATION_AVAILABLE = False
    TrainingEvaluator = None
    EvaluationResult = None

# 尝试导入核心酶（可选依赖）
try:
    from prokaryote_agent.core_enzymes import SkillPipeline, get_skill_pipeline
    CORE_ENZYMES_AVAILABLE = True
except ImportError:
    CORE_ENZYMES_AVAILABLE = False


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
from prokaryote_agent.skills.skill_context import SkillContext
from typing import Dict, Any, List, Optional


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

    def execute(self, context: SkillContext = None, **kwargs) -> Dict[str, Any]:
        """
        执行技能

        Args:
            context: 技能执行上下文，提供知识库访问、技能互调用、产出物保存
        {execute_docstring}
        """
        try:
            {execute_code}

            # 保存产出物到Knowledge（如果有context）
            if context and result:
                self._save_output(context, result)

            return {{
                'success': True,
                'result': result
            }}
        except Exception as e:
            return {{
                'success': False,
                'error': str(e)
            }}

    def _save_output(self, context: SkillContext, result: Dict[str, Any]):
        """保存产出物到Knowledge"""
        {save_output_code}

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

    代码生成：
    - 优先使用核心酶（SkillPipeline）进行代码生成
    - 核心酶不可用时，使用内置模板方案
    """

    def __init__(self, library: SkillLibrary = None, use_core_enzymes: bool = True):
        """
        初始化技能生成器

        Args:
            library: 技能库实例
            use_core_enzymes: 是否使用核心酶生成代码（默认True）
        """
        self.library = library or SkillLibrary()
        self.logger = logging.getLogger(__name__)
        self.use_core_enzymes = use_core_enzymes and CORE_ENZYMES_AVAILABLE
        self._pipeline = None
        self._evaluator = None
        self._ai_adapter = None

        # AI 训练规划器的提示（由外部设置）
        self.training_hints: Dict[str, Any] = {}

        if self.use_core_enzymes:
            self.logger.info("技能生成器: 使用核心酶模式")
        else:
            self.logger.info("技能生成器: 使用模板模式")

        if EVALUATION_AVAILABLE:
            self.logger.info("技能生成器: AI评估功能可用")
        else:
            self.logger.info("技能生成器: 使用规则评估")

    # ==================== 可用技能上下文 ====================

    def _build_available_skills_context(
        self,
        exclude_skill_id: str = None,
        domain: str = None,
        max_skills: int = 20
    ) -> str:
        """
        构建可用技能列表的上下文文本，供 AI 生成代码/任务时参考。

        包含每个技能的 ID、名称、描述、等级和能力列表，
        让 AI 知道可以通过 context.call_skill(skill_id, **kwargs)
        调用哪些已有技能来协作完成任务。

        Args:
            exclude_skill_id: 排除当前技能自身（避免自递归）
            domain: 如果指定，优先列出同领域技能
            max_skills: 最多列出的技能数量

        Returns:
            格式化的技能列表文本，若无可用技能则返回空字符串
        """
        if not self.library:
            return ""

        all_skills = self.library.list_skills()
        if not all_skills:
            return ""

        # 排除自身
        if exclude_skill_id:
            all_skills = [
                s for s in all_skills if s.skill_id != exclude_skill_id
            ]

        # 只展示已学会的技能（level >= 1）
        learned = [s for s in all_skills if s.level >= 1]
        if not learned:
            return ""

        # 排序：同领域优先，然后按等级降序
        def sort_key(s):
            domain_match = 1 if (domain and s.domain == domain) else 0
            return (-domain_match, -s.level, s.skill_id)

        learned.sort(key=sort_key)
        learned = learned[:max_skills]

        # 构建文本
        lines = [
            "\n## 可调用的已有技能",
            "以下技能可通过 `context.call_skill(skill_id, **kwargs)` 调用："
        ]
        for s in learned:
            caps = ""
            # 尝试获取已加载技能的能力列表
            skill_instance = self.library.skills.get(s.skill_id)
            if skill_instance:
                try:
                    cap_list = skill_instance.get_capabilities()
                    if cap_list:
                        caps = f"  能力: {', '.join(cap_list)}"
                except Exception:
                    pass
            line = (
                f"- `{s.skill_id}` | {s.name} (Lv.{s.level})"
                f" — {s.description}"
            )
            if caps:
                line += f"\n  {caps}"
            lines.append(line)

        lines.append("")
        return "\n".join(lines)

    @property
    def pipeline(self) -> Optional['SkillPipeline']:
        """获取技能生成管线（延迟加载）"""
        if self._pipeline is None and self.use_core_enzymes:
            self._pipeline = get_skill_pipeline()
        return self._pipeline

    @property
    def evaluator(self) -> Optional['TrainingEvaluator']:
        """获取训练评估器（延迟加载）"""
        if self._evaluator is None and EVALUATION_AVAILABLE:
            self._evaluator = TrainingEvaluator()
        return self._evaluator

    @property
    def ai_adapter(self):
        """获取AI适配器（延迟加载）"""
        if self._ai_adapter is None:
            try:
                from prokaryote_agent.ai_adapter import AIAdapter
                self._ai_adapter = AIAdapter()
            except Exception:
                pass
        return self._ai_adapter

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
            # 1. 生成技能代码（优先使用核心酶）
            if self.use_core_enzymes and self.pipeline:
                self.logger.info(f"使用核心酶生成代码: {skill_id}")
                gen_result = self.pipeline.generate(skill_definition)

                if gen_result['success']:
                    code = gen_result['code']
                    self.logger.info(
                        f"核心酶生成成功: {skill_id}, "
                        f"尝试次数={gen_result['attempts']}, "
                        f"修复={gen_result['repairs']}"
                    )
                else:
                    # 核心酶失败，尝试模板方案
                    self.logger.warning(
                        f"核心酶生成失败: {gen_result['error']}, 尝试模板方案"
                    )
                    code = self._generate_skill_code(skill_definition)
            else:
                # 使用模板方案
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

    def upgrade_skill(self, skill_id: str, target_level: int,
                       skill_definition: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        升级技能 - 通过执行训练任务来提升

        升级过程：
        1. 获取当前等级的训练任务（难度递进）
        2. 执行训练任务（实际调用技能）
        3. 使用AI评估训练结果（多维度评分）
        4. 如果通过，提升等级
        5. 在关键等级点（5/10/15/20）触发代码进化

        Args:
            skill_id: 技能ID
            target_level: 目标等级
            skill_definition: 技能定义（可选，用于AI评估时获取更多上下文）

        Returns:
            升级结果，包含评估详情、知识统计和能力提升信息
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

        # 获取训练任务（根据等级调整难度）
        training_task = self._get_training_task(
            skill_id, skill.metadata.domain, current_level,
            skill_definition=skill_definition
        )

        self.logger.info(f"执行训练任务: {training_task['name']}")

        # 执行训练（调用技能）
        training_result = self._execute_training(skill, training_task)

        # 使用AI评估或规则评估
        evaluation_result = self._evaluate_training(
            skill=skill,
            task=training_task,
            execution_result=training_result,
            skill_definition=skill_definition
        )

        # 检查评估结果
        if not evaluation_result['passed']:
            self.logger.warning(
                f"训练未通过: {skill_id} "
                f"得分 {evaluation_result.get('score', '?')}/"
                f"{evaluation_result.get('threshold', '?')} "
                f"({evaluation_result.get('method', '?')})"
            )
            if evaluation_result.get('reason'):
                reason = evaluation_result['reason']
                self.logger.warning(
                    f"  原因: {reason[:300]}"
                    f"{'...' if len(reason) > 300 else ''}"
                )
            if evaluation_result.get('summary'):
                self.logger.info(
                    f"  摘要: {evaluation_result['summary'][:300]}"
                )

            # 记录失败并分析原因
            optimization_info = self._record_training_failure(
                skill_id=skill_id,
                level=current_level,
                eval_result=evaluation_result,
                execution_result=training_result
            )

            # 持久化训练档案
            try:
                from .evolution.training_archive import record_training
                record_training(
                    skill_id=skill_id,
                    level=current_level,
                    target_level=target_level,
                    task=training_task,
                    execution_result=training_result,
                    evaluation=evaluation_result,
                    success=False,
                )
            except Exception:
                pass

            return {
                'success': False,
                'skill_id': skill_id,
                'error': f"训练未通过: {evaluation_result.get('reason', '未知原因')}",
                'training_task': training_task['name'],
                'evaluation': evaluation_result,
                'optimization_info': optimization_info  # 新增：优化建议
            }

        # 训练通过 - 记录成功，清除失败计数器
        try:
            from .evolution.skill_optimizer import record_training_result
            record_training_result(
                skill_id=skill_id,
                level=current_level,
                success=True,
                eval_result=evaluation_result
            )
        except ImportError:
            pass

        # 训练通过，获取增强
        enhancements = self._get_level_enhancements(
            skill.metadata.tier,
            current_level,
            target_level,
            skill_name=skill.metadata.name
        )

        # 升级技能
        for _ in range(target_level - current_level):
            skill.upgrade()

        # 记录训练经验（含知识贡献加成）
        skill.metadata.total_executions += 1
        skill.metadata.successful_executions += 1

        # 知识固化加成：存储的知识越多，熟练度提升越快
        knowledge_stored = training_result.get('knowledge_stored', 0)
        base_gain = 0.05
        knowledge_bonus = min(0.05, knowledge_stored * 0.01)  # 每条知识+1%，最多+5%
        skill.metadata.proficiency = min(1.0, skill.metadata.proficiency + base_gain + knowledge_bonus)

        # 检查是否需要代码进化（关键等级点）
        code_evolved = False
        if target_level in [5, 10, 15, 20] and self.use_core_enzymes:
            code_evolved = self._evolve_skill_code(skill, target_level, enhancements)

        # 更新注册表
        self.library.registry[skill_id] = skill.metadata
        self.library._save_registry()

        self.logger.info(f"技能升级: {skill_id} Lv.{current_level} -> Lv.{target_level}")
        if knowledge_stored > 0:
            self.logger.info(f"  知识固化: {knowledge_stored} 条新知识")
        if code_evolved:
            self.logger.info(f"  代码进化: 技能能力已增强")

        # 持久化训练档案
        try:
            from .evolution.training_archive import record_training
            record_training(
                skill_id=skill_id,
                level=current_level,
                target_level=target_level,
                task=training_task,
                execution_result=training_result,
                evaluation=evaluation_result,
                success=True,
                knowledge_stored=knowledge_stored,
                code_evolved=code_evolved,
            )
        except Exception:
            pass

        return {
            'success': True,
            'skill_id': skill_id,
            'old_level': current_level,
            'new_level': target_level,
            'enhancements': enhancements,
            'training_task': training_task['name'],
            'training_result': training_result,
            'evaluation': evaluation_result,
            'knowledge_stored': knowledge_stored,
            'code_evolved': code_evolved,
            'proficiency': skill.metadata.proficiency
        }

    def _evaluate_training(
        self,
        skill: Skill,
        task: Dict[str, Any],
        execution_result: Dict[str, Any],
        skill_definition: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        评估训练结果

        优先使用AI评估，AI不可用时回退到规则评估。

        Args:
            skill: 技能实例
            task: 训练任务
            execution_result: 执行结果
            skill_definition: 技能定义（用于获取评估配置）

        Returns:
            评估结果字典
        """
        # 构建技能定义（如果没有传入）
        if skill_definition is None:
            skill_definition = {
                'id': skill.metadata.skill_id,
                'name': skill.metadata.name,
                'description': skill.metadata.description,
                'domain': skill.metadata.domain,
                'tier': skill.metadata.tier,
                'capabilities': skill.get_capabilities()
            }

        # 获取产出物列表
        outputs = execution_result.get('outputs', [])

        # 尝试AI评估
        if self.evaluator:
            try:
                eval_result = self.evaluator.evaluate(
                    skill_definition=skill_definition,
                    task=task,
                    execution_result=execution_result,
                    current_level=skill.metadata.level,
                    outputs=outputs
                )

                # 返回结构化评估结果
                return {
                    'passed': eval_result.passed,
                    'score': eval_result.total_score,
                    'threshold': eval_result.pass_threshold,
                    'decision': eval_result.decision.value,
                    'reason': eval_result.overall_feedback,
                    'dimension_scores': [d.to_dict() for d in eval_result.dimension_scores],
                    'improvement_suggestions': eval_result.improvement_suggestions,
                    'method': eval_result.evaluation_method,
                    'summary': eval_result.get_summary()
                }

            except Exception as e:
                self.logger.warning(f"AI评估失败，使用简单规则: {e}")

        # 回退到简单规则评估（兼容旧逻辑）
        return self._simple_rule_evaluate(execution_result, task)

    def _simple_rule_evaluate(
        self,
        execution_result: Dict[str, Any],
        task: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        简单规则评估（回退方案）

        保持与原有逻辑兼容
        """
        task_type = task.get('type', 'generic')
        passed = execution_result.get('passed', False)
        reason = execution_result.get('reason', '')

        # 根据任务类型做基本判断
        if task_type == 'research':
            found = execution_result.get('found', 0)
            expected = task.get('expected_count', 1)
            if found >= expected:
                score = min(10, 6.0 + (found / max(expected, 1)) * 2)
                reason = f'找到{found}条结果（期望{expected}条）'
            elif found > 0:
                score = 3.0 + (found / max(expected, 1)) * 3
                reason = f'结果不足，找到{found}条（期望{expected}条）'
            else:
                score = 1.0
                reason = '未找到任何结果'

        elif task_type == 'drafting':
            content_len = execution_result.get('content_length', 0)
            content = execution_result.get('content', '')

            # 检测占位符内容（说明实际内容为空）
            placeholder_count = content.count('[请填写')

            if content_len >= 800 and placeholder_count == 0:
                score = 8.5
                reason = f'文书生成完整（{content_len}字符）'
            elif content_len >= 500 and placeholder_count <= 1:
                score = 7.0
                reason = f'文书基本完成（{content_len}字符）'
            elif content_len >= 300 and placeholder_count == 0:
                score = 6.5
                reason = f'文书内容可用（{content_len}字符）'
            elif content_len >= 200 and placeholder_count <= 2:
                score = 5.5
                reason = f'文书内容尚可（{content_len}字符）'
            elif content_len >= 50:
                score = 3.5
                reason = f'文书内容较短（{content_len}字符）'
            else:
                score = 1.0
                reason = '文书内容严重不足'

            # 占位符惩罚：大量占位符说明没有实质内容
            if placeholder_count >= 3:
                penalty = min(4.0, placeholder_count * 1.0)
                score = max(1.0, score - penalty)
                reason += f'，{placeholder_count}处占位符未填写'

        elif task_type == 'analysis':
            has_analysis = execution_result.get('has_analysis', False)
            knowledge_stored = execution_result.get('knowledge_stored', 0)
            if has_analysis and knowledge_stored > 0:
                score = 7.5
                reason = f'分析完成，固化{knowledge_stored}条知识'
            elif has_analysis:
                score = 6.0
                reason = '分析完成但未固化知识'
            else:
                score = 3.0
                reason = '分析结果不完整'

        else:
            # 通用：直接使用执行结果
            score = 7.0 if passed else 3.0

        # 统一通过判定：分数 >= 6.0 才算通过
        passed = score >= 6.0

        return {
            'passed': passed,
            'score': score,
            'threshold': 6.0,
            'decision': 'upgrade' if passed else 'needs_practice',
            'reason': reason,
            'dimension_scores': [],
            'improvement_suggestions': [],
            'method': 'simple_rule'
        }

    def _record_training_failure(
        self,
        skill_id: str,
        level: int,
        eval_result: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        记录训练失败并分析原因

        当连续失败次数超过阈值时，自动触发 AI 技能修复。

        Args:
            skill_id: 技能ID
            level: 当前等级
            eval_result: 评估结果
            execution_result: 执行结果

        Returns:
            优化信息，包含连续失败次数、优化建议和修复结果
        """
        try:
            from .evolution.skill_optimizer import (
                record_training_result,
                get_skill_optimizer,
            )

            result = record_training_result(
                skill_id=skill_id,
                level=level,
                success=False,
                eval_result=eval_result,
                execution_result=execution_result
            )

            if result and result.get('should_optimize'):
                consecutive = result.get('consecutive_failures', 0)
                self.logger.warning(
                    f"技能 {skill_id} 需要优化，"
                    f"连续失败 {consecutive} 次"
                )

                # 输出优化建议
                suggestions = result.get('optimization_suggestions', [])
                if suggestions:
                    self.logger.info("优化建议:")
                    for i, s in enumerate(suggestions[:3], 1):
                        self.logger.info(
                            f"  {i}. [{s.get('strategy')}] "
                            f"{s.get('description')}"
                        )

                # 自动触发 AI 修复
                failure_analysis = result.get('failure_analysis', {})
                self.logger.info(
                    f"🤖 触发 AI 自修复: {skill_id}"
                )

                optimizer = get_skill_optimizer()
                repair_result = optimizer.ai_repair_skill(
                    skill_id=skill_id,
                    failure_analysis=failure_analysis,
                    suggestions=suggestions,
                )

                result['repair_result'] = repair_result

                if repair_result.get('success'):
                    self.logger.info(
                        f"✅ AI 自修复成功: {skill_id}"
                    )
                    changes = repair_result.get(
                        'changes_summary', [])
                    for ch in changes[:5]:
                        self.logger.info(f"   {ch}")

                    # 重新加载技能到库中（热重载，无需重启）
                    if self.library:
                        reloaded = self.library.reload_skill(skill_id)
                        if reloaded:
                            self.logger.info(
                                "   技能已热重载"
                            )
                else:
                    self.logger.warning(
                        f"❌ AI 自修复失败: "
                        f"{repair_result.get('error')}"
                    )

            return result or {}

        except ImportError:
            self.logger.debug("技能优化模块未加载")
            return {}
        except Exception as e:
            self.logger.warning(f"记录训练失败异常: {e}")
            return {}

    def _evolve_skill_code(self, skill: Skill, new_level: int,
                           enhancements: List[str]) -> bool:
        """
        在关键等级点进化技能代码

        读取当前技能源码，连同增强规格一起传给核心酶，
        让 AI 在现有实现基础上改进而非从零重写。

        Args:
            skill: 技能实例
            new_level: 新等级
            enhancements: 本次升级获得的增强

        Returns:
            是否成功进化
        """
        if not self.pipeline:
            return False

        try:
            # 读取当前技能源码
            current_code = None
            skill_path = (
                self.library.library_path
                / f"{skill.metadata.skill_id}.py"
            )
            if skill_path.exists():
                try:
                    current_code = skill_path.read_text(encoding='utf-8')
                    self.logger.info(
                        f"读取现有代码: {skill_path.name} "
                        f"({len(current_code)} chars)"
                    )
                except Exception as e:
                    self.logger.warning(f"读取现有代码失败: {e}")

            # 构建增强规格
            enhanced_spec = {
                'id': skill.metadata.skill_id,
                'name': skill.metadata.name,
                'description': skill.metadata.description,
                'domain': skill.metadata.domain,
                'tier': skill.metadata.tier,
                'capabilities': skill.get_capabilities(),
                'level': new_level,
                'enhancements': enhancements,
                # 传入现有源码供 AI 改进
                'current_code': current_code,
                # 根据等级添加特定能力要求
                'requirements': self._get_level_requirements(
                    new_level,
                    skill_name=skill.metadata.name,
                    domain=skill.metadata.domain
                )
            }

            # 调用核心酶重新生成代码
            result = self.pipeline.generate(enhanced_spec)

            if result.get('success'):
                # 保存新版本
                code = result['code']
                version = f"1.0.{new_level}"

                # 保存到版本目录
                self._save_skill_version(skill.metadata.skill_id, code, version)

                # 更新当前技能文件
                skill_path = self.library.library_path / f"{skill.metadata.skill_id}.py"
                skill_path.write_text(code, encoding='utf-8')

                skill.metadata.version = version
                self.logger.info(f"代码进化成功: {skill.metadata.skill_id} -> v{version}")
                return True
            else:
                self.logger.warning(f"代码进化失败: {result.get('error')}")
                return False

        except Exception as e:
            self.logger.error(f"代码进化异常: {e}")
            return False

    def _get_level_requirements(self, level: int,
                                skill_name: str = '',
                                domain: str = '') -> List[str]:
        """获取等级对应的能力要求（根据技能和领域调整）"""
        requirements = []
        context = skill_name or domain or '技能'

        if level >= 5:
            requirements.append(f"{context}支持批量处理多个输入")
        if level >= 10:
            requirements.append("优先查询本地知识库，减少重复搜索")
            requirements.append("添加结果缓存和去重机制")
        if level >= 15:
            requirements.append(f"支持{context}的多维度深度分析")
            requirements.append("生成质量自评分并据此改进")
        if level >= 20:
            requirements.append("自适应处理策略，根据输入特征选择最优路径")
            requirements.append("支持增量更新，避免重复计算")
            requirements.append("对复杂场景的鲁棒处理")

        return requirements

    def _save_skill_version(self, skill_id: str, code: str, version: str):
        """保存技能代码版本"""
        versions_dir = self.library.library_path / ".versions"
        versions_dir.mkdir(exist_ok=True)

        version_file = versions_dir / f"{skill_id}_v{version}.py"
        version_file.write_text(code, encoding='utf-8')
        self.logger.debug(f"版本已保存: {version_file}")

    def _get_training_task(self, skill_id: str, domain: str, level: int,
                           skill_definition: Optional[Dict[str, Any]] = None
                           ) -> Dict[str, Any]:
        """
        获取训练任务

        优先使用AI生成上下文相关的训练任务，
        AI不可用时回退到内置任务模板。
        """
        # 尝试获取历史评估反馈
        past_feedback = self._get_past_feedback(skill_id)
        if past_feedback:
            self.logger.info(
                "📋 训练参考用户反馈 %d 条: %s",
                len(past_feedback), skill_id
            )
            for fb in past_feedback:
                self.logger.info("   ↳ %s", fb[:120])

        # 优先使用AI生成训练任务
        ai_task = self._generate_ai_training_task(
            skill_id, domain, level, skill_definition, past_feedback
        )
        if ai_task:
            return ai_task

        # AI不可用，回退到内置任务
        self.logger.debug(f"使用内置训练任务模板: {skill_id}")
        # 法律领域训练任务
        if domain == 'legal':
            return self._get_legal_training_task(skill_id, level)
        elif domain == 'software_dev':
            return self._get_software_training_task(skill_id, level)
        else:
            return self._get_generic_training_task(skill_id, level)

    def _generate_ai_training_task(
        self,
        skill_id: str,
        domain: str,
        level: int,
        skill_definition: Optional[Dict[str, Any]] = None,
        past_feedback: Optional[List[str]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        使用AI生成上下文相关的训练任务

        根据技能定义、当前等级和历史评估反馈，
        动态生成难度适当、内容丰富的训练任务。

        Returns:
            训练任务字典，AI不可用时返回None
        """
        adapter = self.ai_adapter
        if not adapter or not adapter.config.api_key:
            return None

        # 构建技能上下文
        if skill_definition:
            skill_info = (
                f"- 名称: {skill_definition.get('name', skill_id)}\n"
                f"- 描述: {skill_definition.get('description', '')}\n"
                f"- 能力: {', '.join(skill_definition.get('capabilities', []))}\n"
            )
        else:
            skill_info = f"- 技能ID: {skill_id}\n"

        feedback_section = ""
        if past_feedback:
            feedback_section = (
                "\n历史评估反馈（请据此调整训练重点）:\n"
                + "\n".join(f"- {fb}" for fb in past_feedback[:5])
            )

        # AI 规划器提示
        plan_section = ""
        hints = self.training_hints.get(skill_id, {})
        if hints:
            focus = hints.get("focus_dimensions", [])
            task_hint = hints.get("task_hint", "")
            if focus:
                plan_section += (
                    f"\n训练规划器要求侧重维度: "
                    f"{', '.join(focus)}\n"
                )
            if task_hint:
                plan_section += (
                    f"训练规划器任务建议: {task_hint}\n"
                )

        difficulty = min(level // 5 + 1, 5)

        # 构建可用技能上下文
        skills_context = self._build_available_skills_context(
            exclude_skill_id=skill_id,
            domain=domain
        )

        prompt = f"""你是一个AI技能训练任务生成器。请根据以下信息生成一个恰当的训练任务。

技能信息:
{skill_info}- 领域: {domain}
- 当前等级: {level}（目标提升到 {level + 1}）
- 目标难度: {difficulty}/5
{feedback_section}
{plan_section}
{skills_context}
任务设计要求:
1. 难度与等级匹配：等级0-4为基础，5-9为进阶，10-14为高级，15+为专家
2. 任务应测试该技能的核心能力
3. 提供具体、可执行的任务内容（不要抽象描述）
4. 如果有历史反馈，针对性地设计任务来弥补薄弱环节
5. 如果有可调用的其他技能，可设计需要技能协作的复合任务

请以严格的JSON格式返回，不要包含其他文字:
{{
    "name": "任务名称（简短描述）",
    "type": "research 或 drafting 或 analysis 或 code_review 或 generic",
    "difficulty": {difficulty},
    "description": "详细任务描述",
    "query": "如果是research类型，填写具体查询内容",
    "expected_count": 2,
    "sources": ["查询来源列表，根据领域填写"],
    "doc_type": "如果是drafting类型，填写文书类型",
    "sections": ["如果是drafting类型，列出需要包含的章节"],
    "case_type": "如果是analysis类型，填写案例类型",
    "focus": "如果是analysis类型，填写分析重点"
}}"""

        try:
            result = adapter._call_ai(prompt)
            if result.get('success') and result.get('content'):
                content = result['content'].strip()

                # 尝试从代码块中提取JSON
                json_match = re.search(
                    r'```(?:json)?\s*([\s\S]*?)```', content
                )
                if json_match:
                    content = json_match.group(1).strip()

                task = safe_json_loads(content)

                # 确保必要字段
                if 'name' not in task:
                    task['name'] = f'AI训练任务 Lv.{level + 1}'
                if 'type' not in task:
                    task['type'] = 'generic'
                if 'difficulty' not in task:
                    task['difficulty'] = difficulty

                self.logger.info(
                    f"AI生成训练任务: {task['name']} "
                    f"(类型: {task['type']})"
                )
                return task

        except json.JSONDecodeError as e:
            self.logger.warning(f"AI训练任务JSON解析失败: {e}")
        except Exception as e:
            self.logger.warning(f"AI生成训练任务失败: {e}")

        return None

    def _get_past_feedback(self, skill_id: str) -> List[str]:
        """获取技能的历史评估反馈 + 用户测试反馈，用于指导后续训练"""
        feedback = []

        # 1. 从持久化训练档案获取历史反馈（优先，重启不丢失）
        try:
            from .evolution.training_archive import analyze_skill
            analysis = analyze_skill(skill_id, days=14)
            if analysis.get("data_available"):
                # 弱项维度
                weak = analysis.get("weak_dimensions", {})
                if weak:
                    dims = ", ".join(
                        f"{k}({v}次)" for k, v in weak.items()
                    )
                    feedback.append(
                        f"历史弱项维度: {dims}"
                    )
                # 改进建议
                for s in analysis.get(
                    "recent_suggestions", []
                )[:3]:
                    feedback.append(f"评估建议: {s[:120]}")
                # 趋势
                trend = analysis.get("recent_trend", 0)
                if trend < -0.5:
                    feedback.append(
                        f"注意: 近期得分呈下降趋势"
                        f" ({trend:+.1f})"
                    )
        except (ImportError, Exception):
            pass

        # 2. 从内存 optimizer 补充（当前进程的即时反馈）
        if len(feedback) < 5:
            try:
                from .evolution.skill_optimizer import (
                    get_skill_optimizer,
                )
                optimizer = get_skill_optimizer()
                failures = optimizer.failure_history.get(
                    skill_id, []
                )
                if failures:
                    for entry in failures[-3:]:
                        suggestions = entry.get(
                            'improvement_suggestions', []
                        )
                        feedback.extend(suggestions[:2])
                        reason = entry.get('reason', '')
                        if reason and len(feedback) < 8:
                            feedback.append(reason[:120])
            except (ImportError, Exception):
                pass

        # 3. 从用户测试反馈中获取改进建议
        try:
            from web.services.feedback_service import (
                get_user_feedback_for_training,
            )
            user_feedback = get_user_feedback_for_training(
                skill_id=skill_id, limit=5,
            )
            feedback.extend(user_feedback)
        except (ImportError, Exception):
            pass

        return feedback[:10]

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
        产出物会通过SkillContext自动保存到Knowledge目录
        """
        from .skill_context import SkillContext

        task_type = task.get('type', 'generic')

        # 创建执行上下文
        context = SkillContext(
            skill_id=skill.metadata.skill_id,
            skill_library=self.library,
            domain=skill.metadata.domain
        )

        try:
            if task_type == 'research':
                # 执行检索训练
                result = skill.execute(
                    context=context,
                    query=task.get('query', ''),
                    sources=task.get('sources', [])
                )

                if result.get('success'):
                    res = result.get('result', {})
                    found_count = res.get('total_found', 0)
                    expected = task.get('expected_count', 1)
                    passed = found_count >= expected

                    # 提取知识固化统计
                    knowledge_stored = res.get('stored_to_kb', 0)

                    return {
                        'passed': passed,
                        'found': found_count,
                        'expected': expected,
                        'reason': f'找到{found_count}条结果' if passed else f'结果不足，期望{expected}条',
                        'knowledge_stored': knowledge_stored,
                        'from_cache': res.get('from_cache', False),
                        'outputs': context.get_outputs()
                    }
                else:
                    return {'passed': False, 'reason': result.get('error', '执行失败')}

            elif task_type == 'drafting':
                # 执行文书起草训练
                result = skill.execute(
                    context=context,
                    doc_type=task.get('doc_type', ''),
                    sections=task.get('sections', [])
                )

                if result.get('success'):
                    res = result.get('result', {})
                    content = res.get('content', '')
                    # 不预判 passed，交给评估器决定
                    return {
                        'content_length': len(content),
                        'content': content[:3000],  # 传递实际内容供评估
                        'result': res,
                        'reason': f'文书内容 {len(content)} 字符',
                        'outputs': context.get_outputs()
                    }
                else:
                    return {'passed': False, 'reason': result.get('error', '执行失败')}

            elif task_type == 'analysis':
                # 执行案例分析训练
                result = skill.execute(
                    context=context,
                    case_text=f"这是一个{task.get('case_type', '')}案例，需要分析{task.get('focus', '')}",
                    analysis_type='comprehensive'
                )

                if result.get('success'):
                    analysis = result.get('result', {})
                    has_summary = 'case_summary' in analysis or 'analysis' in analysis
                    passed = has_summary

                    # 提取知识固化统计
                    knowledge_stats = analysis.get('knowledge_stats', {})
                    knowledge_stored = knowledge_stats.get('stored', 0)

                    return {
                        'passed': passed,
                        'has_analysis': has_summary,
                        'reason': '分析完成' if passed else '分析结果不完整',
                        'knowledge_stored': knowledge_stored,
                        'knowledge_stats': knowledge_stats,
                        'outputs': context.get_outputs()
                    }
                else:
                    return {'passed': False, 'reason': result.get('error', '执行失败')}

            else:
                # 通用训练：尝试实际执行技能
                query = task.get('query', task.get('description', ''))
                try:
                    result = skill.execute(
                        context=context,
                        query=query,
                        input=task.get('input', {}),
                        **{k: v for k, v in task.items()
                           if k not in ('name', 'type', 'difficulty',
                                        'description', 'query', 'input')}
                    )

                    if result.get('success'):
                        res = result.get('result', {})
                        return {
                            'passed': True,
                            'result': res,
                            'reason': '训练执行完成',
                            'outputs': context.get_outputs()
                        }
                    else:
                        return {
                            'passed': False,
                            'reason': result.get('error', '执行失败'),
                            'outputs': context.get_outputs()
                        }
                except Exception as exec_err:
                    self.logger.warning(
                        f"通用训练执行失败: {exec_err}"
                    )
                    return {
                        'passed': False,
                        'reason': f'执行异常: {exec_err}',
                        'outputs': context.get_outputs()
                    }

        except Exception as e:
            self.logger.error(f"训练执行异常: {e}")
            return {'passed': False, 'reason': str(e)}

    def _generate_skill_code(self, definition: Dict[str, Any]) -> str:
        """生成技能代码 - 优先使用AI，回退到内置模板"""
        skill_id = definition['id']
        skill_name = definition['name']
        tier = definition.get('tier', 'basic')
        domain = definition.get('domain', 'general')
        description = definition.get('description', '')
        capabilities = definition.get('capabilities', [])

        # 转换为类名
        class_name = ''.join(word.capitalize() for word in skill_id.split('_'))

        # 优先使用AI生成领域代码
        ai_result = self._generate_ai_domain_code(
            domain, skill_id, skill_name, description, capabilities
        )

        if ai_result:
            execute_code, validate_code, execute_docstring, save_output_code = ai_result
            self.logger.info(f"AI生成技能代码: {skill_id}")
        else:
            # 回退到内置模板
            self.logger.debug(f"使用内置模板生成代码: {skill_id}")
            execute_code, validate_code, execute_docstring, save_output_code = (
                self._generate_domain_code(
                    domain, skill_id, skill_name, capabilities
                )
            )

        # 格式化能力列表
        capabilities_str = '\n'.join(f"- {cap}" for cap in capabilities)

        # 生成示例
        examples = self._generate_examples(
            domain, skill_id,
            skill_name=skill_name,
            capabilities=capabilities
        )

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
            save_output_code=save_output_code,
            examples=repr(examples)
        )

        return code

    def _generate_ai_domain_code(
        self,
        domain: str,
        skill_id: str,
        skill_name: str,
        description: str,
        capabilities: List[str]
    ) -> Optional[tuple]:
        """
        使用AI生成技能的核心代码片段

        生成 execute_code, validate_code, docstring, save_output_code 四部分，
        然后嵌入到标准的SKILL_TEMPLATE中。

        Returns:
            (execute_code, validate_code, docstring, save_output_code)
            AI不可用时返回None
        """
        adapter = self.ai_adapter
        if not adapter or not adapter.config.api_key:
            return None

        caps_str = ', '.join(capabilities) if capabilities else '通用'

        # 构建可用技能上下文
        skills_context = self._build_available_skills_context(
            exclude_skill_id=skill_id,
            domain=domain
        )

        prompt = f"""你是一个Python技能代码生成器。请为以下技能生成核心实现代码。

技能信息:
- ID: {skill_id}
- 名称: {skill_name}
- 领域: {domain}
- 描述: {description}
- 能力: {caps_str}

你需要生成4个代码片段，它们会被嵌入到一个Skill类模板中：

1. **execute_code**: execute方法的实现体（缩进8格）
   - 可以使用 `kwargs` 获取输入参数
   - 可以使用 `context` (SkillContext) 统一访问所有基础能力：
     ▸ AI大模型: `context.call_ai(prompt, system_prompt=None, temperature=None)` → {{"success": bool, "content": str}}
     ▸ 联网搜索: `context.web_search(query, max_results=5)` → [list of results]
     ▸ 深度搜索: `context.deep_search(query, max_results=5, fetch_content=True)` → [results with content]
     ▸ URL抓取: `context.fetch_url(url)` → {{"success": bool, "content": str}}
     ▸ 知识库搜索: `context.search_knowledge(query, category=None, limit=5)` → [results]
     ▸ 知识库存储: `context.store_knowledge(title, content, category, source, tags)` → bool
     ▸ 智能搜索(本地+网络): `context.smart_search(query, category=None, use_web=True)` → dict
     ▸ 调用其他技能: `context.call_skill(skill_id, **kwargs)` → dict
     ▸ 文件读取: `context.read_file(path)` → {{"success": bool, "content": str}}
     ▸ 文件写入: `context.write_file(path, content)` → {{"success": bool, "path": str}}
     ▸ 列出文件: `context.list_files(directory, pattern, recursive)` → [paths]
     ▸ 保存产出物: `context.save_output(output_type, title, content, format, category)` → path
     ▸ 日志: `context.log(message, level='info')`
   - **禁止直接import web_tools或ai_adapter，所有能力通过context调用**
   - 可以使用 `from prokaryote_agent.utils.json_utils import safe_json_loads` 来安全解析AI返回的JSON
   - 最终结果存储在 `result` 变量中（dict类型）
{skills_context}
2. **validate_code**: validate_input方法的实现体（缩进8格）
   - 验证kwargs中的输入参数，返回bool

3. **docstring**: execute方法的docstring内容
   - 描述Args和Returns

4. **save_output_code**: _save_output方法的实现体（缩进8格）
   - 使用 `context.save_output(output_type=..., title=..., content=..., category=...)`
   - `result` 变量包含execute的返回结果

重要要求:
- 代码必须是真正可执行的Python代码
- 所有基础能力(AI/联网/文件)统一通过context对象调用，不要直接import
- 不要使用占位符或TODO注释
- 代码应专注于"{skill_name}"的实际功能实现
- 如果其他技能可以辅助完成任务，优先通过 context.call_skill() 复用而不是重复实现

核心设计模式 — AI-first with hardcoded fallback:
- 所有领域专业逻辑（分析、生成、推理、评估）必须优先通过 context.call_ai() 实现
- 仅在 AI 不可用时回退到简单的规则/关键词/模板
- **禁止**大量硬编码领域知识（如正则提取、关键词列表、固定模板）作为主路径
- 推荐模式：
  ```
  # AI 主路径
  ai_result = context.call_ai(structured_prompt)
  if ai_result.get('success') and ai_result.get('content'):
      data = safe_json_loads(ai_result['content'])
      ...使用 data...
  else:
      # 简单规则回退
      data = basic_rule_fallback(...)
  ```
- 回退逻辑应尽量简短，核心智能由 AI 提供
- 这种模式使代码能在进化时被 AI 改进（更好的 prompt → 更好的结果）

请以JSON格式返回，不要其他文字:
{{
    "execute_code": "python代码字符串",
    "validate_code": "python代码字符串",
    "docstring": "docstring内容",
    "save_output_code": "python代码字符串"
}}"""

        try:
            result = adapter._call_ai(prompt)
            if not result.get('success') or not result.get('content'):
                return None

            content = result['content'].strip()

            # 提取JSON
            json_match = re.search(
                r'```(?:json)?\s*([\s\S]*?)```', content
            )
            if json_match:
                content = json_match.group(1).strip()

            parts = safe_json_loads(content)

            execute_code = parts.get('execute_code', '')
            validate_code = parts.get('validate_code', '')
            docstring = parts.get('docstring', '')
            save_output_code = parts.get('save_output_code', '')

            if not execute_code:
                self.logger.warning("AI未生成有效的execute_code")
                return None

            # 验证生成的代码片段语法（简单检查）
            test_code = f"def _test():\n    {execute_code}"
            try:
                compile(test_code, '<ai_generated>', 'exec')
            except SyntaxError as e:
                self.logger.warning(
                    f"AI生成代码语法错误: {e}"
                )
                return None

            self.logger.info(
                f"AI生成技能代码成功: {skill_id} "
                f"(execute: {len(execute_code)} chars)"
            )
            return (execute_code, validate_code, docstring,
                    save_output_code)

        except json.JSONDecodeError as e:
            self.logger.warning(f"AI技能代码JSON解析失败: {e}")
        except Exception as e:
            self.logger.warning(f"AI生成技能代码失败: {e}")

        return None

    def _generate_domain_code(self, domain: str, skill_id: str,
                               skill_name: str, capabilities: List[str]) -> tuple:
        """根据领域生成具体代码（返回4元组：execute, validate, docstring, save_output）"""

        if domain == 'legal':
            return self._generate_legal_skill_code(skill_id, skill_name, capabilities)
        elif domain == 'software_dev':
            return self._generate_software_skill_code(skill_id, skill_name, capabilities)
        else:
            return self._generate_generic_skill_code(skill_id, skill_name, capabilities)

    def _generate_legal_skill_code(self, skill_id: str, skill_name: str,
                                    capabilities: List[str]) -> tuple:
        """生成法律领域技能代码 - 使用深度网络搜索 + 知识库存储"""

        if 'research' in skill_id or '检索' in skill_name:
            execute_code = '''
            query = kwargs.get('query', '')
            sources = kwargs.get('sources', ['法律法规', '司法解释', '判例'])
            use_cache = kwargs.get('use_cache', True)

            # 1. 先查本地知识库
            if use_cache:
                local_results = context.search_knowledge(query, limit=5)
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
                    if context and result:
                        self._save_output(context, result)
                    return {'success': True, 'result': result}

            # 2. 本地知识不足，深度联网搜索
            legal_query = f"{query} 法律法规 法条"
            all_results = context.deep_search(legal_query, max_results=3)

            # 3. 存储搜索结果到知识库（有内容的才存）
            stored_count = 0
            for r in all_results[:5]:
                content = r.get('content', '')
                if content and len(content) > 100:
                    try:
                        context.store_knowledge(
                            title=r.get('title', query),
                            content=content,
                            category=r.get('category', 'general'),
                            source=r.get('url', ''),
                            tags=['法律', '检索']
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
            检索结果，包含标题、内容、URL等
            from_cache: 是否来自知识库
            stored_to_kb: 新存储到知识库的数量'''

        elif 'drafting' in skill_id or '文书' in skill_name or '起草' in skill_name:
            execute_code = '''
            doc_type = kwargs.get('doc_type', '合同')
            template = kwargs.get('template', None)
            data = kwargs.get('data', {})

            # 文书模板库
            doc_templates = {
                '劳动合同': ['合同双方', '工作内容', '工作时间', '劳动报酬', '社会保险', '劳动保护', '合同期限', '违约责任', '争议解决'],
                '保密协议': ['保密内容范围', '保密期限', '保密义务', '违约责任', '例外情况'],
                '租赁合同': ['租赁物描述', '租赁期限', '租金及支付', '押金', '维修责任', '违约责任'],
                'NDA': ['保密信息定义', '保密义务', '使用限制', '期限', '违约救济'],
                '起诉状': ['原告信息', '被告信息', '诉讼请求', '事实与理由', '证据清单'],
                '答辩状': ['答辩人信息', '答辩意见', '事实与理由', '证据清单'],
            }

            # 获取文书章节
            sections = doc_templates.get(doc_type, ['标题', '正文', '签章'])

            # 搜索相关模板和范例
            try:
                search_results = context.web_search(f"{doc_type} 模板 范本", max_results=3)
                references = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in search_results[:2]]
            except Exception:
                references = []

            # 生成文书框架
            content_lines = [f'【{doc_type}】', '']
            for i, section in enumerate(sections):
                content_lines.append(f'{i+1}. {section}')
                content_lines.append(f'   [请填写{section}内容]')
                content_lines.append('')

            result = {
                'doc_type': doc_type,
                'content': '\\n'.join(content_lines),
                'sections': sections,
                'references': references,
                'warnings': ['请根据实际情况修改内容', '建议咨询专业律师审核']
            }'''
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
            import re

            case_text = kwargs.get('case_text', '')
            analysis_type = kwargs.get('analysis_type', 'comprehensive')

            # 1. 提取关键词
            legal_terms = ['合同', '侵权', '违约', '赔偿', '责任', '权益', '纠纷', '诉讼', '解除', '争议']
            keywords = [t for t in legal_terms if t in case_text]
            if not keywords:
                words = re.findall(r'[\\u4e00-\\u9fa5]{2,4}', case_text)
                keywords = list(set(words))[:5]

            # 2. 智能搜索（优先本地知识库，不足时深度网络搜索并固化）
            knowledge_stored = 0
            legal_context = []

            for kw in keywords[:2]:
                try:
                    search_result = context.smart_search(
                        query=f"{kw} 法律 规定",
                        use_web=True,
                        auto_store=True
                    )
                    legal_context.extend(search_result.get('all_results', []))
                    knowledge_stored += search_result.get('stored', 0)
                except Exception:
                    pass

            # 3. 生成分析结果
            result = {
                'case_summary': case_text[:200] + '...' if len(case_text) > 200 else case_text,
                'key_facts': keywords,
                'legal_issues': [f'{kw}相关法律问题' for kw in keywords[:3]],
                'applicable_laws': [r.get('title', '') for r in legal_context[:5]],
                'legal_context': legal_context[:5],
                'analysis': f'案例涉及{", ".join(keywords[:3])}等法律问题，需结合相关法规分析。',
                'knowledge_stats': {
                    'stored': knowledge_stored,
                    'from_local': sum(1 for r in legal_context if r.get('source') == 'knowledge_base'),
                    'from_web': sum(1 for r in legal_context if r.get('source') != 'knowledge_base')
                }
            }'''
            validate_code = '''
        case_text = kwargs.get('case_text')
        return case_text is not None and len(case_text.strip()) > 0'''
            docstring = '''
        Args:
            case_text: 案例文本
            analysis_type: 分析类型

        Returns:
            案例分析结果，包含相关法律参考
            knowledge_stats: 知识库统计（存储数、本地命中、网络获取）'''

        elif 'contract' in skill_id or '合同' in skill_name:
            execute_code = '''
            contract_text = kwargs.get('contract_text', '')
            check_items = kwargs.get('check_items', ['条款完整性', '风险点', '合规性'])

            # 搜索合同审查要点
            review_points = context.web_search("合同审查要点 风险点", max_results=3)

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
            legal_refs = context.web_search("合同法 必备条款", max_results=2)

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

        # 生成产出物保存代码
        if 'research' in skill_id or '检索' in skill_name:
            save_output_code = '''
        # 保存检索结果
        results = result.get('results', [])
        if results:
            content_lines = [f"## 检索查询: {result.get('query', '')}\\n"]
            for i, r in enumerate(results[:5], 1):
                content_lines.append(f"### {i}. {r.get('title', '无标题')}")
                content_lines.append(f"- 来源: {r.get('source', '未知')}")
                if r.get('url'):
                    content_lines.append(f"- URL: {r.get('url')}")
                # 保存完整内容
                content = r.get('content', '')
                content_lines.append(f"\\n{content}\\n")
            context.save_output(
                output_type='research',
                title=f"法律检索_{result.get('query', '未知')[:20]}",
                content='\\n'.join(content_lines),
                category='research_results',
                metadata={'total_found': result.get('total_found', 0), 'from_cache': result.get('from_cache', False)}
            )'''
        elif 'drafting' in skill_id or '文书' in skill_name:
            save_output_code = '''
        # 保存文书草稿
        context.save_output(
            output_type='document',
            title=f"{result.get('doc_type', '文书')}草稿",
            content=result.get('content', ''),
            category='drafts',
            metadata={'sections': result.get('sections', []), 'references': result.get('references', [])}
        )'''
        elif 'analysis' in skill_id or '分析' in skill_name:
            save_output_code = '''
        # 保存分析报告
        content_lines = [
            f"## 案例摘要\\n{result.get('case_summary', '')}\\n",
            f"## 关键事实\\n" + '\\n'.join(f"- {f}" for f in result.get('key_facts', [])),
            f"\\n## 法律问题\\n" + '\\n'.join(f"- {i}" for i in result.get('legal_issues', [])),
            f"\\n## 适用法律\\n" + '\\n'.join(f"- {l}" for l in result.get('applicable_laws', [])),
            f"\\n## 分析结论\\n{result.get('analysis', '')}"
        ]
        context.save_output(
            output_type='analysis',
            title=f"案例分析报告",
            content='\\n'.join(content_lines),
            category='analysis_reports',
            metadata={'knowledge_stats': result.get('knowledge_stats', {})}
        )'''
        elif 'contract' in skill_id or '合同' in skill_name:
            save_output_code = '''
        # 保存合同审查报告
        content_lines = [
            f"## 合同审查报告\\n",
            f"- 整体评级: {result.get('overall_rating', 'N/A')}",
            f"- 风险等级: {result.get('risk_level', 'N/A')}\\n",
            f"## 发现的问题\\n" + '\\n'.join(f"- [{i.get('type')}] {i.get('description')}" for i in result.get('issues', [])),
            f"\\n## 改进建议\\n" + '\\n'.join(f"- {s}" for s in result.get('suggestions', []))
        ]
        context.save_output(
            output_type='review',
            title=f"合同审查报告",
            content='\\n'.join(content_lines),
            category='contract_reviews'
        )'''
        else:
            save_output_code = '''
        # 通用产出物保存
        import json
        context.save_output(
            output_type='result',
            title=f"技能执行结果_{self.metadata.skill_id}",
            content=json.dumps(result, ensure_ascii=False, indent=2),
            format='json',
            category='skill_outputs'
        )'''

        return execute_code, validate_code, docstring, save_output_code

    def _generate_software_skill_code(self, skill_id: str, skill_name: str,
                                       capabilities: List[str]) -> tuple:
        """生成软件开发领域技能代码 - 使用真实网络搜索"""

        if 'code_review' in skill_id or '代码审查' in skill_name:
            execute_code = '''
            code = kwargs.get('code', '')
            language = kwargs.get('language', 'python')

            # 搜索代码审查最佳实践
            best_practices = context.web_search(f"{language} code review best practices", max_results=3)

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
            error_message = kwargs.get('error', '')
            code_context = kwargs.get('code', '')
            language = kwargs.get('language', 'python')
            use_cache = kwargs.get('use_cache', True)

            # 1. 先查本地知识库
            if use_cache and error_message:
                error_type = error_message.split(':')[0] if ':' in error_message else error_message[:30]
                local_results = context.search_knowledge(error_type, limit=3)
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
            solutions = context.web_search(search_query, max_results=5)

            # 也搜索 Stack Overflow
            so_results = context.web_search(f"site:stackoverflow.com {error_message[:80]}", max_results=3)

            # 3. 存储有用的解决方案到知识库
            all_solutions = solutions + so_results
            for s in all_solutions[:3]:
                context.store_knowledge(
                    title=s.get('title', error_message[:50]),
                    content=s.get('snippet', '') or f"错误: {error_message}\\n解决方案链接: {s.get('url', '')}",
                    category="errors",
                    source=s.get('url', ''),
                    tags=['调试', language]
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
            api_name = kwargs.get('api_name', '')
            operation = kwargs.get('operation', 'usage')  # usage, example, docs

            # 搜索 API 文档和示例
            doc_results = context.web_search(f"{api_name} API documentation", max_results=3)
            example_results = context.web_search(f"{api_name} API example code", max_results=3)

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
            tutorial_results = context.web_search(f"{topic} tutorial {level}", max_results=5)

            # 搜索概念解释（通过web搜索）
            wiki_results = context.web_search(f"{topic} wikipedia 概念", max_results=3)

            # 搜索官方文档
            doc_results = context.
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

        # 生成产出物保存代码
        if 'code_review' in skill_id or '代码审查' in skill_name:
            save_output_code = '''
        # 保存代码审查报告
        content_lines = [
            f"## 代码审查报告\\n",
            f"- 语言: {result.get('language', 'unknown')}",
            f"- 质量评分: {result.get('quality_score', 0):.2f}",
            f"- 分析行数: {result.get('lines_analyzed', 0)}\\n",
            f"## 发现的问题\\n"
        ]
        for issue in result.get('issues', []):
            content_lines.append(f"- 行 {issue.get('line', '?')}: [{issue.get('type', 'issue')}] {issue.get('message', '')}")
        context.save_output(
            output_type='code_review',
            title=f"代码审查_{result.get('language', 'code')}",
            content='\\n'.join(content_lines),
            category='code_reviews'
        )'''
        elif 'debug' in skill_id or '调试' in skill_name:
            save_output_code = '''
        # 保存调试方案
        content_lines = [
            f"## 错误调试报告\\n",
            f"### 错误信息\\n```\\n{result.get('error', '')}\\n```\\n",
            f"### 可能的解决方案\\n"
        ]
        for s in result.get('possible_solutions', [])[:5]:
            content_lines.append(f"- [{s.get('title', '方案')}]({s.get('url', '')})")
        context.save_output(
            output_type='debug',
            title=f"调试方案_{result.get('language', 'code')}",
            content='\\n'.join(content_lines),
            category='debug_solutions'
        )'''
        else:
            save_output_code = '''
        # 通用产出物保存
        import json
        context.save_output(
            output_type='result',
            title=f"技能执行结果_{self.metadata.skill_id}",
            content=json.dumps(result, ensure_ascii=False, indent=2),
            format='json',
            category='skill_outputs'
        )'''

        return execute_code, validate_code, docstring, save_output_code

    def _generate_generic_skill_code(self, skill_id: str, skill_name: str,
                                      capabilities: List[str]) -> tuple:
        """生成通用技能代码 - 使用context提供的基础能力"""

        execute_code = '''
            # 获取输入
            input_data = kwargs.get('input', {})
            query = kwargs.get('query', '')

            # 如果有查询，执行网络搜索
            search_results = []
            wiki_results = []

            if query:
                search_results = context.web_search(query, max_results=5)
                wiki_results = context.web_search(f"{query} wikipedia 概念", max_results=3)

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

        save_output_code = '''
        # 通用产出物保存
        import json
        context.save_output(
            output_type='generic',
            title=f"执行结果_{self.metadata.skill_id}",
            content=json.dumps(result, ensure_ascii=False, indent=2),
            format='json',
            category='generic_outputs'
        )'''

        return execute_code, validate_code, docstring, save_output_code

    def _generate_examples(self, domain: str, skill_id: str,
                           skill_name: str = '',
                           capabilities: Optional[List[str]] = None
                           ) -> List[Dict[str, Any]]:
        """生成使用示例（根据技能信息动态构建）"""
        examples = []

        if 'research' in skill_id or '检索' in (skill_name or ''):
            examples.append({
                'input': {'query': f'{domain}领域相关查询'},
                'description': f'使用{skill_name or skill_id}进行检索'
            })
        elif 'drafting' in skill_id or '文书' in (skill_name or ''):
            examples.append({
                'input': {'doc_type': '文书'},
                'description': f'使用{skill_name or skill_id}起草文书'
            })
        elif 'analysis' in skill_id or '分析' in (skill_name or ''):
            examples.append({
                'input': {'case_text': '示例案例文本'},
                'description': f'使用{skill_name or skill_id}进行分析'
            })

        if not examples:
            cap = (capabilities[0] if capabilities
                   else '基本功能')
            examples.append({
                'input': {'query': cap},
                'description': f'{skill_name or skill_id}使用示例'
            })

        return examples

    def _validate_code(self, code: str) -> bool:
        """验证代码语法"""
        try:
            compile(code, '<string>', 'exec')
            return True
        except SyntaxError as e:
            self.logger.error(f"代码语法错误: {e}")
            return False

    def _get_level_enhancements(self, tier: str, from_level: int,
                                to_level: int,
                                skill_name: str = '') -> List[str]:
        """获取等级提升带来的增强（根据技能上下文调整）"""
        enhancements = []
        context = skill_name or tier

        for level in range(from_level + 1, to_level + 1):
            if level == 5:
                enhancements.append(
                    f"{context}解锁批量处理能力"
                )
            elif level == 10:
                enhancements.append(
                    f"{context}启用知识库缓存加速"
                )
            elif level == 15:
                enhancements.append(
                    f"{context}解锁高级深度分析能力"
                )
            elif level == 20:
                enhancements.append(
                    f"{context}达到层级上限，可解锁进阶技能"
                )

        return enhancements

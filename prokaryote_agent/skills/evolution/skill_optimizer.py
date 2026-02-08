"""
技能自优化器 - 当训练失败时自动分析原因并优化技能实现

设计思路（AI 诊断驱动的多策略修复）：
1. 检测连续训练失败（如连续3次失败）
2. AI 诊断根因类型（知识不足 / prompt 质量 / 代码缺陷）
3. 按优先级执行修复策略：
   - knowledge_enhancement: 搜索+存储领域知识
   - prompt_improvement:  只改 context.call_ai() 的 prompt
   - code_repair:         全量代码重写（最后手段）
4. 验证修复效果，记录修复经验

核心流程：
  train() → fail → _ai_diagnose() → strategies → verify → record
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillOptimizer:
    """技能自优化器"""

    def __init__(self, max_failures: int = 3, auto_optimize: bool = False):
        """
        初始化优化器

        Args:
            max_failures: 触发优化的最大失败次数
            auto_optimize: 是否自动优化（False时只生成建议）
        """
        self.max_failures = max_failures
        self.auto_optimize = auto_optimize
        self.failure_history: Dict[str, List[Dict]] = {}

    def record_failure(
        self,
        skill_id: str,
        level: int,
        eval_result: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        记录训练失败

        Args:
            skill_id: 技能ID
            level: 当前技能等级
            eval_result: 评估结果（包含分数、详细反馈等）
            execution_result: 执行结果（包含产出物等）

        Returns:
            包含连续失败次数、是否需要优化、失败分析
        """
        if skill_id not in self.failure_history:
            self.failure_history[skill_id] = []

        failure_record = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'score': eval_result.get('score', 0),
            'reason': eval_result.get('reason', ''),
            'summary': eval_result.get('summary', ''),
            'dimension_scores': eval_result.get('dimension_scores', []),
            'improvement_suggestions': eval_result.get(
                'improvement_suggestions', []),
            'method': eval_result.get('method', ''),
            'execution_result': self._extract_key_info(execution_result),
        }

        self.failure_history[skill_id].append(failure_record)

        # 统计连续失败次数
        consecutive = self._count_consecutive_failures(skill_id)

        # 分析失败原因
        failure_analysis = self.analyze_failures(skill_id)

        # 灾难性失败检测：得分极低说明技能代码有根本性问题
        score = eval_result.get('score', 0)
        is_catastrophic = score <= 1.0

        should_optimize = (
            consecutive >= self.max_failures
            or is_catastrophic
        )

        result = {
            'consecutive_failures': consecutive,
            'should_optimize': should_optimize,
            'failure_analysis': failure_analysis,
        }

        if should_optimize:
            if is_catastrophic:
                logger.warning(
                    "技能 %s 灾难性失败 (得分 %.1f)，"
                    "立即触发 AI 修复",
                    skill_id, score
                )
            else:
                logger.warning(
                    "技能 %s 连续失败 %d 次，建议进行优化",
                    skill_id, consecutive
                )
            result['optimization_suggestions'] = (
                self.generate_optimization_suggestions(
                    skill_id, failure_analysis
                )
            )

        return result

    def record_success(self, skill_id: str):
        """记录训练成功，清空失败历史"""
        if skill_id in self.failure_history:
            self.failure_history[skill_id] = []

    def _extract_key_info(self, execution_result: Dict) -> Dict:
        """提取执行结果的关键信息（通用，不依赖特定领域字段）"""
        result = execution_result.get('result', {})
        info: Dict[str, Any] = {
            'success': execution_result.get('success', False),
            'output_size': len(str(result)),
        }

        # 动态提取结果中的关键统计
        if isinstance(result, dict):
            for key, val in result.items():
                if key in ('success',):
                    continue
                if isinstance(val, str):
                    info[f'{key}_length'] = len(val)
                elif isinstance(val, (list, tuple)):
                    info[f'{key}_count'] = len(val)
                elif isinstance(val, dict):
                    info[f'{key}_keys'] = list(val.keys())[:5]

        return info

    def _count_consecutive_failures(self, skill_id: str) -> int:
        """统计连续失败次数"""
        failures = self.failure_history.get(skill_id, [])
        return len(failures)  # 成功时会清空，所以长度即连续失败次数

    def analyze_failures(self, skill_id: str) -> Dict[str, Any]:
        """
        分析失败原因

        基于 AI 评估的真实反馈（维度得分、改进建议）进行分析，
        而非使用硬编码的领域特定指标。

        Returns:
            包含评估反馈摘要、薄弱维度、改进建议
        """
        failures = self.failure_history.get(skill_id, [])
        if not failures:
            return {'causes': [], 'eval_feedback': ''}

        recent = failures[-3:]
        num = len(recent)

        # 1. 汇总评估反馈
        reasons = [f.get('reason', '') for f in recent if f.get('reason')]
        summaries = [
            f.get('summary', '') for f in recent if f.get('summary')
        ]

        # 2. 聚合维度得分，找出薄弱项
        dim_totals: Dict[str, List[float]] = {}
        for f in recent:
            for dim in f.get('dimension_scores', []):
                name = dim.get('name', dim.get('dimension', ''))
                score = dim.get('score', dim.get('weighted_score', 0))
                if name:
                    dim_totals.setdefault(name, []).append(score)

        weak_dimensions = []
        for name, scores in dim_totals.items():
            avg = sum(scores) / len(scores)
            if avg < 6.0:  # 低于及格线
                weak_dimensions.append({
                    'dimension': name,
                    'avg_score': round(avg, 1),
                    'detail': f'{name} 平均得分 {avg:.1f}/10',
                })
        weak_dimensions.sort(key=lambda x: x['avg_score'])

        # 3. 汇总 AI 评估的改进建议
        all_suggestions = []
        seen = set()
        for f in recent:
            for s in f.get('improvement_suggestions', []):
                text = s if isinstance(s, str) else str(s)
                if text and text not in seen:
                    seen.add(text)
                    all_suggestions.append(text)

        # 4. 基础统计
        avg_score = sum(
            f.get('score', 0) for f in recent
        ) / num
        avg_output = sum(
            f['execution_result'].get('output_size', 0)
            for f in recent
        ) / num

        return {
            'avg_score': round(avg_score, 1),
            'avg_output_size': round(avg_output, 0),
            'eval_feedback': '\n'.join(reasons[-2:]),
            'eval_summary': '\n'.join(summaries[-2:]),
            'weak_dimensions': weak_dimensions,
            'improvement_suggestions': all_suggestions[:5],
            'causes': weak_dimensions,  # 兼容旧接口
        }

    def generate_optimization_suggestions(
        self,
        skill_id: str,
        failure_analysis: Dict
    ) -> List[Dict]:
        """
        基于实际评估反馈生成上下文相关的优化建议

        不再使用硬编码的 cause→strategy 映射表，
        而是直接使用 AI 评估器给出的改进建议和薄弱维度。
        """
        suggestions = []

        # 1. 来自 AI 评估的改进建议（最有针对性）
        for i, text in enumerate(
            failure_analysis.get('improvement_suggestions', [])[:5]
        ):
            suggestions.append({
                'strategy': 'eval_suggestion',
                'description': text,
                'priority': i + 1,
                'source': 'ai_evaluation',
            })

        # 2. 来自薄弱维度的针对性建议
        for dim in failure_analysis.get('weak_dimensions', [])[:3]:
            suggestions.append({
                'strategy': 'fix_dimension',
                'description': (
                    f"提升 {dim['dimension']} "
                    f"(当前 {dim['avg_score']}/10)"
                ),
                'priority': 10,
                'source': 'weak_dimension',
            })

        # 3. 通用兜底（仅当以上都没有时）
        if not suggestions:
            suggestions.append({
                'strategy': 'general_improve',
                'description': '增强 execute() 方法的实际处理逻辑',
                'priority': 99,
                'source': 'fallback',
            })

        suggestions.sort(key=lambda x: x.get('priority', 99))
        return suggestions

    # ==========================================================
    #  Phase 1: AI 根因诊断
    # ==========================================================

    def _ai_diagnose(
        self,
        skill_id: str,
        source_code: str,
        failure_analysis: Dict[str, Any],
        suggestions: List[Dict],
    ) -> Dict[str, Any]:
        """
        让 AI 诊断失败根因并生成分层修复计划。

        根因类型:
        - knowledge_gap:  缺少领域知识（法条/模板/格式/惯例）
        - prompt_quality:  AI-first 技能的 prompt 不够好
        - code_bug:        代码逻辑错误或结构问题
        - context_misuse:  未正确使用 context API
        - task_mismatch:   技能定位与任务不匹配

        Returns:
            {
              "diagnosis": "一句话诊断",
              "root_cause": "knowledge_gap|prompt_quality|code_bug|...",
              "confidence": 0.85,
              "strategies": [
                {"type": "knowledge_enhancement|prompt_improvement|code_repair",
                 "priority": 1, "description": "...", "actions": [...]}
              ]
            }
        """
        try:
            from prokaryote_agent.ai_adapter import AIAdapter
            ai = AIAdapter()
            if not ai.config.api_key:
                return self._fallback_diagnosis(failure_analysis)
        except Exception:
            return self._fallback_diagnosis(failure_analysis)

        # 构建诊断 prompt
        eval_feedback = failure_analysis.get('eval_feedback', '')
        eval_summary = failure_analysis.get('eval_summary', '')
        weak_dims = '\n'.join(
            f"  - {d['dimension']}: {d['avg_score']}/10"
            for d in failure_analysis.get('weak_dimensions', [])
        ) or '  无'
        suggestion_texts = '\n'.join(
            f"  - [{s.get('strategy')}] {s.get('description')}"
            for s in suggestions[:5]
        ) or '  无'
        avg_score = failure_analysis.get('avg_score', 0)
        # 截断源码防止超 token
        code_preview = source_code[:4000]
        if len(source_code) > 4000:
            code_preview += '\n# ... (已截断) ...'

        prompt = f"""你是技能修复诊断专家。分析以下技能连续失败的根因，
并制定分层修复计划。

## 技能 ID: {skill_id}
## 平均分: {avg_score}/10

## 评估反馈
{eval_feedback}

## 评估摘要
{eval_summary}

## 薄弱维度
{weak_dims}

## 改进建议
{suggestion_texts}

## 当前源码
```python
{code_preview}
```

## 根因类型选择（只选一个最主要的）
- knowledge_gap: 缺少领域知识（如法律条文、文书格式、行业惯例）
- prompt_quality: 代码中 call_ai() 的 prompt 质量不够好
- code_bug: 代码逻辑错误、API使用不当、返回格式错误
- context_misuse: 未正确使用 context 的 search_knowledge/call_skill 等
- task_mismatch: 技能能力与训练任务不匹配

## 修复策略类型
- knowledge_enhancement: 为技能搜索并存储领域知识到知识库
- prompt_improvement: 只修改代码中 call_ai() 的 prompt 内容
- code_repair: 重写整个技能代码

请返回严格 JSON（不要代码块包裹）：
{{
  "diagnosis": "一句话诊断",
  "root_cause": "上述类型之一",
  "confidence": 0.0到1.0,
  "knowledge_topics": ["如果是knowledge_gap,列出缺失的知识主题"],
  "strategies": [
    {{
      "type": "knowledge_enhancement或prompt_improvement或code_repair",
      "priority": 1,
      "description": "做什么",
      "actions": ["具体步骤1", "步骤2"]
    }}
  ]
}}"""

        try:
            from prokaryote_agent.utils.json_utils import safe_json_loads
            response = ai._call_ai(prompt)
            if not response.get('success') or not response.get('content'):
                return self._fallback_diagnosis(failure_analysis)

            plan = safe_json_loads(response['content'])
            # 校验关键字段
            if 'root_cause' not in plan or 'strategies' not in plan:
                logger.warning("AI诊断结果缺少关键字段，使用回退")
                return self._fallback_diagnosis(failure_analysis)

            plan.setdefault('confidence', 0.5)
            plan.setdefault('diagnosis', '未知')
            plan.setdefault('knowledge_topics', [])

            logger.info(
                f"🔍 AI 诊断: {plan['diagnosis']} "
                f"(根因={plan['root_cause']}, "
                f"置信度={plan['confidence']:.0%})"
            )
            for s in plan.get('strategies', []):
                logger.info(
                    f"   策略 [{s.get('type')}] "
                    f"P{s.get('priority', '?')}: "
                    f"{s.get('description', '')}"
                )
            return plan

        except Exception as e:
            logger.warning(f"AI诊断异常: {e}，使用回退")
            return self._fallback_diagnosis(failure_analysis)

    def _fallback_diagnosis(
        self, failure_analysis: Dict[str, Any]
    ) -> Dict[str, Any]:
        """AI不可用时的规则回退诊断"""
        avg_score = failure_analysis.get('avg_score', 0)

        # 简单规则推断
        if avg_score <= 2.0:
            root_cause = 'code_bug'
            desc = '极低分暗示代码有根本性错误'
        elif failure_analysis.get('improvement_suggestions'):
            root_cause = 'prompt_quality'
            desc = '有改进建议但得分低,可能是prompt质量问题'
        else:
            root_cause = 'knowledge_gap'
            desc = '缺少足够领域知识支撑分析'

        return {
            'diagnosis': desc,
            'root_cause': root_cause,
            'confidence': 0.3,
            'knowledge_topics': [],
            'strategies': [
                {
                    'type': 'knowledge_enhancement',
                    'priority': 1,
                    'description': '补充领域知识',
                    'actions': ['搜索相关领域知识'],
                },
                {
                    'type': 'code_repair',
                    'priority': 2,
                    'description': '重写技能代码',
                    'actions': ['基于评估反馈重写'],
                },
            ],
        }

    # ==========================================================
    #  Phase 2: 修复策略执行
    # ==========================================================

    def _enhance_knowledge(
        self,
        skill_id: str,
        diagnosis: str,
        knowledge_topics: List[str],
        actions: List[str],
    ) -> Dict[str, Any]:
        """
        知识增强策略：搜索并存储领域知识到知识库。

        搜索 → AI 总结 → store_knowledge()
        使技能下次执行时通过 context.search_knowledge() 可检索。
        """
        from prokaryote_agent.skills.skill_context import SkillContext

        ctx = SkillContext(
            skill_id=skill_id,
            domain='legal'
        )

        stored_count = 0
        search_topics = knowledge_topics or actions or [diagnosis]

        logger.info(
            f"📚 知识增强: 搜索 {len(search_topics)} 个主题"
        )

        for topic in search_topics[:5]:
            try:
                # 深度搜索: 抓取网页内容
                results = ctx.deep_search(
                    query=topic,
                    max_results=3,
                    fetch_content=True
                )

                for r in results:
                    content = r.get('content', '')
                    if not content or len(content) < 200:
                        continue

                    # AI 总结为结构化知识条目
                    summary_result = ctx.call_ai(
                        f"将以下内容总结为专业知识条目"
                        f"（保留关键信息、条文编号、"
                        f"格式要求等）:\n\n"
                        f"{content[:3000]}"
                    )

                    if (summary_result.get('success')
                            and summary_result.get('content')
                            and len(summary_result['content']) > 100):
                        stored = ctx.store_knowledge(
                            title=r.get('title', topic),
                            content=summary_result['content'],
                            category='skill_knowledge',
                            source=r.get('url', ''),
                            tags=[
                                skill_id, 'auto_repair',
                                'knowledge_enhancement'
                            ]
                        )
                        if stored:
                            stored_count += 1
                            logger.info(
                                f"   ✓ 存储: "
                                f"{r.get('title', topic)[:50]}"
                            )
                    else:
                        # AI 总结失败,直接存原文摘要
                        stored = ctx.store_knowledge(
                            title=r.get('title', topic),
                            content=content[:2000],
                            category='skill_knowledge',
                            source=r.get('url', ''),
                            tags=[
                                skill_id, 'auto_repair',
                                'raw_content'
                            ]
                        )
                        if stored:
                            stored_count += 1

            except Exception as e:
                logger.debug(f"   知识搜索失败 [{topic}]: {e}")
                continue

        logger.info(f"📚 知识增强完成: 存储 {stored_count} 条")
        return {
            'success': stored_count > 0,
            'stored_count': stored_count,
            'topics_searched': len(search_topics),
        }

    def _improve_prompts(
        self,
        skill_id: str,
        source_code: str,
        diagnosis: str,
        actions: List[str],
        failure_analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prompt 优化策略：只修改代码中 call_ai() 的 prompt。

        不改变代码结构/方法签名/导入,仅改善 AI 提示词质量。
        比全量重写更安全、更精确。
        """
        from pathlib import Path

        try:
            from prokaryote_agent.ai_adapter import AIAdapter
            ai = AIAdapter()
            if not ai.config.api_key:
                return {'success': False, 'error': 'API Key 未配置'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

        actions_text = '\n'.join(f'  - {a}' for a in actions) or '  改善prompt'
        eval_feedback = failure_analysis.get('eval_feedback', '')
        suggestions_text = '\n'.join(
            f'  - {s}' for s in
            failure_analysis.get('improvement_suggestions', [])[:3]
        )

        prompt = f"""你是 Python 代码优化专家。
请**只修改**以下代码中 context.call_ai() 调用的 prompt 参数。

## 严格限制
1. 不要改变类名、方法签名、导入语句、继承关系
2. 不要改变代码结构和控制流
3. 只修改字符串内容（prompt 文本）
4. 保持所有 try/except 和回退逻辑不变

## 诊断
{diagnosis}

## 改进方向
{actions_text}

## 评估反馈
{eval_feedback}

## 改进建议
{suggestions_text}

## 当前源码
```python
{source_code}
```

## 输出
返回修改后的完整 Python 文件（放在 ```python ... ``` 中）。
只改 prompt 字符串,其他代码一字不动。"""

        try:
            response = ai._call_ai(prompt)
            if not response.get('success') or not response.get('content'):
                return {
                    'success': False,
                    'error': 'AI 调用失败',
                }

            new_code = self._extract_code_from_response(
                response['content']
            )
            if not new_code:
                return {
                    'success': False,
                    'error': '未找到有效代码',
                }

            # 语法验证
            try:
                compile(new_code, f'{skill_id}.py', 'exec')
            except SyntaxError as e:
                return {
                    'success': False,
                    'error': f'语法错误: {e}',
                }

            # 安全检查: 确认结构没有大变化
            if not self._is_minimal_change(source_code, new_code):
                logger.warning(
                    "prompt_improvement 产生了过大变更，降级为 code_repair"
                )
                return {
                    'success': False,
                    'error': 'prompt优化产生了过大代码变更',
                    'escalate': True,
                }

            # 写入
            library_path = Path("prokaryote_agent/skills/library")
            skill_file = library_path / f"{skill_id}.py"

            # 备份
            self._backup_skill(
                skill_id, source_code, library_path, 'prompt_fix'
            )

            skill_file.write_text(new_code, encoding='utf-8')
            logger.info(
                f"✏️ Prompt 优化已写入: {skill_file.name}"
            )

            # 重载验证
            reload_ok = self._try_reload_skill(
                skill_id, library_path
            )
            if not reload_ok:
                skill_file.write_text(source_code, encoding='utf-8')
                return {
                    'success': False,
                    'error': 'prompt优化代码无法加载（已回滚）',
                }

            return {
                'success': True,
                'strategy': 'prompt_improvement',
                'changes_summary': ['优化了 AI prompt 质量'],
                'code_size_before': len(source_code),
                'code_size_after': len(new_code),
            }

        except Exception as e:
            logger.error(f"Prompt 优化异常: {e}")
            return {'success': False, 'error': str(e)}

    def _full_code_repair(
        self,
        skill_id: str,
        source_code: str,
        failure_analysis: Dict[str, Any],
        suggestions: List[Dict],
        diagnosis_plan: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        全量代码重写策略（最后手段）。

        与原 ai_repair_skill 逻辑类似，但 prompt 中包含诊断信息。
        """
        from pathlib import Path

        try:
            from prokaryote_agent.ai_adapter import AIAdapter
            ai = AIAdapter()
            if not ai.config.api_key:
                return {
                    'success': False,
                    'skill_id': skill_id,
                    'error': 'API Key 未配置',
                }
        except Exception as e:
            return {
                'success': False,
                'skill_id': skill_id,
                'error': str(e),
            }

        prompt = self._build_repair_prompt(
            skill_id, source_code, failure_analysis,
            suggestions, diagnosis_plan
        )

        try:
            response = ai._call_ai(prompt)
            if not response.get('success') or not response.get('content'):
                return {
                    'success': False,
                    'skill_id': skill_id,
                    'error': f"AI 调用失败: {response.get('error')}",
                }

            new_code = self._extract_code_from_response(
                response['content']
            )
            if not new_code:
                return {
                    'success': False,
                    'skill_id': skill_id,
                    'error': 'AI 返回中未找到有效代码',
                }

            logger.info(
                f"   AI 生成修复代码: {len(new_code)} 字符"
            )
        except Exception as e:
            return {
                'success': False,
                'skill_id': skill_id,
                'error': str(e),
            }

        # 语法验证
        try:
            compile(new_code, f'{skill_id}.py', 'exec')
        except SyntaxError as e:
            return {
                'success': False,
                'skill_id': skill_id,
                'error': f'修复代码语法错误: {e}',
            }

        # 备份 + 写入
        library_path = Path("prokaryote_agent/skills/library")
        skill_file = library_path / f"{skill_id}.py"

        self._backup_skill(
            skill_id, source_code, library_path, 'code_repair'
        )

        skill_file.write_text(new_code, encoding='utf-8')
        logger.info(f"   已写入修复代码: {skill_file}")

        # 重载
        reload_ok = self._try_reload_skill(skill_id, library_path)
        if not reload_ok:
            logger.warning("   修复代码加载失败，回滚")
            skill_file.write_text(source_code, encoding='utf-8')
            return {
                'success': False,
                'skill_id': skill_id,
                'error': '修复代码无法加载（已回滚）',
            }

        changes = self._summarize_changes(source_code, new_code)
        return {
            'success': True,
            'skill_id': skill_id,
            'strategy': 'code_repair',
            'changes_summary': changes,
            'code_size_before': len(source_code),
            'code_size_after': len(new_code),
        }

    # ==========================================================
    #  ai_repair_skill: 3 阶段编排
    # ==========================================================

    def ai_repair_skill(
        self,
        skill_id: str,
        failure_analysis: Dict[str, Any],
        suggestions: List[Dict],
        last_task: Dict[str, Any] = None,
    ) -> Dict[str, Any]:
        """
        AI 驱动的多策略技能修复。

        Phase 1: AI 诊断根因
        Phase 2: 按优先级执行策略（知识→prompt→代码）
        Phase 3: 记录修复经验

        Args:
            skill_id: 技能ID
            failure_analysis: 来自 analyze_failures 的分析
            suggestions: 来自 generate_optimization_suggestions 的建议
            last_task: 触发失败的训练任务（用于验证修复）

        Returns:
            {success, skill_id, strategy, changes_summary, ...}
        """
        from pathlib import Path

        logger.info(f"🔧 开始 AI 多策略修复: {skill_id}")

        # 读取源码
        library_path = Path("prokaryote_agent/skills/library")
        skill_file = library_path / f"{skill_id}.py"

        if not skill_file.exists():
            return {
                'success': False,
                'skill_id': skill_id,
                'error': f'技能文件不存在: {skill_file}',
            }

        source_code = skill_file.read_text(encoding='utf-8')
        logger.info(f"   原始代码: {len(source_code)} 字符")

        # ── Phase 1: AI 诊断 ──
        diagnosis_plan = self._ai_diagnose(
            skill_id, source_code, failure_analysis, suggestions
        )
        root_cause = diagnosis_plan.get('root_cause', 'code_bug')
        knowledge_topics = diagnosis_plan.get('knowledge_topics', [])

        # ── Phase 2: 按策略优先级执行 ──
        strategies = diagnosis_plan.get('strategies', [])
        if not strategies:
            # 诊断没给策略，提供默认的
            strategies = [
                {
                    'type': 'knowledge_enhancement',
                    'priority': 1,
                    'description': '补充知识',
                    'actions': knowledge_topics or ['领域知识搜索'],
                },
                {
                    'type': 'code_repair',
                    'priority': 2,
                    'description': '代码重写',
                    'actions': ['基于诊断重写'],
                },
            ]
        strategies.sort(key=lambda s: s.get('priority', 99))

        final_result = {
            'success': False,
            'skill_id': skill_id,
            'diagnosis': diagnosis_plan.get('diagnosis', ''),
            'root_cause': root_cause,
            'strategies_tried': [],
        }

        for strategy in strategies:
            stype = strategy.get('type', 'code_repair')
            actions = strategy.get('actions', [])
            desc = strategy.get('description', stype)

            logger.info(
                f"   ▶ 执行策略: {stype} — {desc}"
            )

            if stype == 'knowledge_enhancement':
                result = self._enhance_knowledge(
                    skill_id,
                    diagnosis_plan.get('diagnosis', ''),
                    knowledge_topics,
                    actions,
                )
                final_result['strategies_tried'].append({
                    'type': stype,
                    'result': result,
                })
                if result.get('success'):
                    logger.info(
                        f"   ✓ 知识增强完成 "
                        f"({result.get('stored_count', 0)} 条)"
                    )
                # 知识增强总是继续执行下一个策略
                # 因为光加知识不改代码不够

            elif stype == 'prompt_improvement':
                # 重新读取源码(知识增强不改文件,但以防万一)
                current_code = skill_file.read_text(encoding='utf-8')
                result = self._improve_prompts(
                    skill_id, current_code,
                    diagnosis_plan.get('diagnosis', ''),
                    actions, failure_analysis,
                )
                final_result['strategies_tried'].append({
                    'type': stype,
                    'result': result,
                })

                if result.get('success'):
                    # prompt 修复成功,清空失败历史
                    self.record_success(skill_id)
                    final_result.update(result)
                    final_result['success'] = True
                    logger.info(
                        "   ✓ Prompt 优化成功"
                    )
                    break
                elif result.get('escalate'):
                    # 变更过大,继续下一策略(code_repair)
                    logger.info(
                        "   → 升级到 code_repair"
                    )
                    continue
                else:
                    logger.warning(
                        f"   ✗ Prompt 优化失败: "
                        f"{result.get('error')}"
                    )
                    continue

            elif stype == 'code_repair':
                current_code = skill_file.read_text(encoding='utf-8')
                result = self._full_code_repair(
                    skill_id, current_code,
                    failure_analysis, suggestions,
                    diagnosis_plan,
                )
                final_result['strategies_tried'].append({
                    'type': stype,
                    'result': result,
                })

                if result.get('success'):
                    self.record_success(skill_id)
                    final_result.update(result)
                    final_result['success'] = True
                    logger.info(
                        "   ✓ 代码重写成功"
                    )
                    break
                else:
                    logger.warning(
                        f"   ✗ 代码重写失败: "
                        f"{result.get('error')}"
                    )
                    continue
            else:
                logger.debug(f"   跳过未知策略: {stype}")

        # ── Phase 3: 记录修复经验 ──
        self._record_repair_experience(
            skill_id, diagnosis_plan, final_result
        )

        if final_result['success']:
            logger.info(
                f"✅ 技能 {skill_id} 多策略修复成功 "
                f"(策略: {final_result.get('strategy', '?')})"
            )
        else:
            logger.warning(
                f"❌ 技能 {skill_id} 所有修复策略均失败"
            )

        return final_result

    # ==========================================================
    #  Phase 3: 经验记录
    # ==========================================================

    def _record_repair_experience(
        self,
        skill_id: str,
        diagnosis_plan: Dict[str, Any],
        repair_result: Dict[str, Any],
    ):
        """
        将修复经验存入知识库，下次同类失败可复用。
        """
        if not repair_result.get('success'):
            return  # 只记录成功的经验

        try:
            from prokaryote_agent.skills.skill_context import (
                SkillContext,
            )
            ctx = SkillContext(
                skill_id='skill_optimizer',
                domain='system'
            )

            strategies_tried = repair_result.get(
                'strategies_tried', []
            )
            strategy_names = [
                s.get('type', '?') for s in strategies_tried
            ]

            experience = (
                f"# 技能修复经验: {skill_id}\n\n"
                f"## 诊断\n"
                f"{diagnosis_plan.get('diagnosis', '未知')}\n\n"
                f"## 根因\n"
                f"{diagnosis_plan.get('root_cause', '未知')}\n\n"
                f"## 成功策略\n"
                f"{repair_result.get('strategy', '未知')}\n\n"
                f"## 尝试过的策略\n"
                f"{', '.join(strategy_names)}\n\n"
                f"## 变更摘要\n"
            )
            for ch in repair_result.get('changes_summary', [])[:5]:
                experience += f"- {ch}\n"

            ctx.store_knowledge(
                title=f"修复经验_{skill_id}_{datetime.now():%Y%m%d}",
                content=experience,
                category='repair_experience',
                source='skill_optimizer',
                tags=[
                    skill_id, 'repair',
                    diagnosis_plan.get('root_cause', '')
                ]
            )
            logger.debug(f"已记录修复经验: {skill_id}")

        except Exception as e:
            logger.debug(f"记录修复经验失败: {e}")

    # ==========================================================
    #  工具方法
    # ==========================================================

    def _build_repair_prompt(
        self,
        skill_id: str,
        source_code: str,
        failure_analysis: Dict,
        suggestions: List[Dict],
        diagnosis_plan: Dict[str, Any] = None,
    ) -> str:
        """构造全量重写的 LLM prompt（包含诊断信息）"""
        eval_feedback = failure_analysis.get(
            'eval_feedback', '无具体反馈'
        )
        eval_summary = failure_analysis.get('eval_summary', '')

        weak_dims_text = ""
        for dim in failure_analysis.get('weak_dimensions', []):
            weak_dims_text += (
                f"- {dim['dimension']}: "
                f"{dim['avg_score']}/10\n"
            )
        if not weak_dims_text:
            weak_dims_text = "无具体维度数据\n"

        suggestions_text = ""
        for s in suggestions[:5]:
            suggestions_text += f"- {s.get('description')}\n"
        if not suggestions_text:
            suggestions_text = "无具体建议\n"

        avg_score = failure_analysis.get('avg_score', 0)
        avg_output = failure_analysis.get('avg_output_size', 0)

        # 诊断信息
        diag_section = ""
        if diagnosis_plan:
            diag_section = f"""
## AI 诊断结果
- 诊断: {diagnosis_plan.get('diagnosis', '未知')}
- 根因: {diagnosis_plan.get('root_cause', '未知')}
- 置信度: {diagnosis_plan.get('confidence', 0):.0%}
"""

        prompt = f"""你是 Python 技能代码优化专家。
请修复以下技能代码使其通过训练评估。

## 技能 ID
{skill_id}
{diag_section}
## 当前源码
```python
{source_code}
```

## 评估反馈
{eval_feedback}

## 评估摘要
{eval_summary}

## 薄弱维度
{weak_dims_text}

## 统计
- 平均评估得分: {avg_score}/10
- 平均产出物大小: {avg_output:.0f} 字符

## 改进建议
{suggestions_text}

## 修复要求
1. 保持类名、方法签名和继承关系不变
2. 保持核心方法签名不变
3. 重点修复 execute 方法的实际逻辑
4. 返回格式为 {{'success': True/False, 'result': {{...}}}}
5. 领域专业逻辑优先使用 context.call_ai() 实现
6. 简单的规则/模板作为 AI 不可用时的回退
7. 使用 context.search_knowledge() 先查知识库
8. 通过 context.save_output() 保存产出物
9. 可以使用 safe_json_loads 解析 AI 返回的 JSON
10. 不要引入新外部依赖

## 输出
只输出修复后的完整 Python 文件（```python ... ```）。"""

        return prompt

    def _is_minimal_change(
        self, old_code: str, new_code: str
    ) -> bool:
        """
        检查变更是否够小（用于 prompt_improvement 安全检查）。

        如果方法签名、类定义、导入发生了大变化,说明
        AI 不只是改了 prompt,应升级为 code_repair。
        """
        import re

        # 计算行级差异比例
        old_lines = set(old_code.splitlines())
        new_lines = set(new_code.splitlines())
        changed = len(old_lines.symmetric_difference(new_lines))
        total = max(len(old_lines), len(new_lines), 1)
        diff_ratio = changed / total

        if diff_ratio > 0.4:
            logger.debug(
                f"变更比例 {diff_ratio:.0%} > 40%，判定为大变更"
            )
            return False

        # 检查关键结构是否保持
        def extract_signatures(code):
            return set(re.findall(
                r'^\s*(class \w+|def \w+)', code, re.MULTILINE
            ))

        old_sigs = extract_signatures(old_code)
        new_sigs = extract_signatures(new_code)
        if old_sigs != new_sigs:
            logger.debug("类/方法签名发生变化，判定为大变更")
            return False

        return True

    def _backup_skill(
        self,
        skill_id: str,
        source_code: str,
        library_path,
        tag: str = 'repair',
    ):
        """备份技能文件到 .versions/"""
        versions_dir = library_path / ".versions"
        versions_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{skill_id}_pre_{tag}_{timestamp}.py"
        backup_path = versions_dir / backup_name
        backup_path.write_text(source_code, encoding='utf-8')
        logger.info(f"   已备份: {backup_path}")
        return str(backup_path)

    def _extract_code_from_response(self, content: str) -> Optional[str]:
        """从 LLM 响应中提取 Python 代码块"""
        if not content:
            return None

        # 查找 ```python ... ``` 代码块
        import re
        pattern = r'```python\s*\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)

        if matches:
            # 取最长的代码块（通常是完整文件）
            code = max(matches, key=len).strip()
            if len(code) > 50:  # 最小合理长度
                return code

        # 备选：尝试提取所有 ``` 代码块
        pattern2 = r'```\s*\n(.*?)```'
        matches2 = re.findall(pattern2, content, re.DOTALL)
        if matches2:
            code = max(matches2, key=len).strip()
            if len(code) > 50 and 'class ' in code and 'def execute' in code:
                return code

        # 最后手段：如果整个 content 看起来像 Python 代码
        if 'class ' in content and 'def execute' in content and 'import' in content:
            return content.strip()

        return None

    def _try_reload_skill(self, skill_id: str, library_path) -> bool:
        """尝试重新加载技能模块"""
        import importlib
        import importlib.util
        import sys

        skill_file = library_path / f"{skill_id}.py"

        try:
            # 清除旧的缓存模块
            if skill_id in sys.modules:
                del sys.modules[skill_id]

            spec = importlib.util.spec_from_file_location(
                skill_id, str(skill_file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 检查是否有 Skill 子类
            from prokaryote_agent.skills.skill_base import Skill
            found = False
            for name, obj in vars(module).items():
                if (isinstance(obj, type)
                        and issubclass(obj, Skill)
                        and obj is not Skill):
                    found = True
                    break

            return found
        except Exception as e:
            logger.error(f"重新加载技能失败: {e}")
            return False

    def _summarize_changes(
        self, old_code: str, new_code: str
    ) -> List[str]:
        """简要总结代码变更"""
        changes = []

        old_lines = old_code.splitlines()
        new_lines = new_code.splitlines()

        # 行数变化
        diff = len(new_lines) - len(old_lines)
        if diff > 0:
            changes.append(f"代码增加了 {diff} 行 ({len(old_lines)} → {len(new_lines)})")
        elif diff < 0:
            changes.append(f"代码减少了 {abs(diff)} 行 ({len(old_lines)} → {len(new_lines)})")
        else:
            changes.append(f"代码行数不变 ({len(new_lines)} 行)")

        # 检查关键变更
        old_text = old_code.lower()
        new_text = new_code.lower()

        if 'aiAdapter' in new_code or 'ai_adapter' in new_code:
            if 'ai_adapter' not in old_text:
                changes.append("新增: AI 适配器集成")

        if 'web_search' in new_text and 'web_search' not in old_text:
            changes.append("新增: 网络搜索功能")

        if 'context.save_output' in new_text:
            if 'context.save_output' not in old_text:
                changes.append("新增: 知识库产出物保存")
            elif new_text.count('context.save_output') > old_text.count('context.save_output'):
                changes.append("增强: 更多产出物保存到知识库")

        if 'try:' in new_text:
            old_try = old_text.count('try:')
            new_try = new_text.count('try:')
            if new_try > old_try:
                changes.append(f"增强: 错误处理 ({old_try} → {new_try} 个 try 块)")

        if not changes[1:]:
            changes.append("代码逻辑已重构优化")

        return changes


# 全局优化器实例
_optimizer: Optional[SkillOptimizer] = None


def get_skill_optimizer(
    max_failures: int = 3,
    auto_optimize: bool = False
) -> SkillOptimizer:
    """获取或创建技能优化器实例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = SkillOptimizer(max_failures, auto_optimize)
    return _optimizer


def record_training_result(
    skill_id: str,
    level: int,
    success: bool,
    eval_result: Dict = None,
    execution_result: Dict = None
) -> Optional[Dict]:
    """
    记录训练结果，失败时触发分析

    Args:
        skill_id: 技能ID
        level: 当前等级
        success: 是否成功
        eval_result: 评估结果
        execution_result: 执行结果

    Returns:
        失败时返回优化建议，成功时返回 None
    """
    optimizer = get_skill_optimizer()

    if success:
        optimizer.record_success(skill_id)
        return None
    else:
        return optimizer.record_failure(
            skill_id, level,
            eval_result or {},
            execution_result or {}
        )

"""
AI训练评估器

使用AI对技能训练结果进行多维度评估，决定是否应该升级。
"""

import logging
import re
from typing import Dict, Any, List, Optional

from prokaryote_agent.utils.json_utils import safe_json_loads

from .result import (
    EvaluationResult,
    EvaluationContext,
    DimensionScore,
    LevelDecision
)
from .config_resolver import EvaluationConfigResolver


logger = logging.getLogger(__name__)


class TrainingEvaluator:
    """
    AI训练评估器

    使用AI对技能训练结果进行评估，支持：
    - 多维度评分
    - 动态通过阈值
    - 升级决策建议
    - 回退到规则评估
    """

    def __init__(self, ai_adapter=None):
        """
        初始化评估器

        Args:
            ai_adapter: AI适配器实例，如果为None则尝试自动创建
        """
        self.logger = logging.getLogger(f"{__name__}.TrainingEvaluator")
        self.config_resolver = EvaluationConfigResolver()
        self._ai_adapter = ai_adapter

    @property
    def ai_adapter(self):
        """延迟加载AI适配器"""
        if self._ai_adapter is None:
            try:
                from prokaryote_agent.ai_adapter import AIAdapter
                self._ai_adapter = AIAdapter()
            except Exception as e:
                self.logger.warning(f"无法加载AI适配器: {e}")
        return self._ai_adapter

    def evaluate(
        self,
        skill_definition: Dict[str, Any],
        task: Dict[str, Any],
        execution_result: Dict[str, Any],
        current_level: int = 0,
        outputs: Optional[List[str]] = None
    ) -> EvaluationResult:
        """
        评估训练结果

        Args:
            skill_definition: 技能定义
            task: 训练任务
            execution_result: 执行结果
            current_level: 当前技能等级
            outputs: 执行产出物路径列表

        Returns:
            EvaluationResult: 评估结果
        """
        skill_id = skill_definition.get("id", "unknown")
        skill_name = skill_definition.get("name", skill_id)
        task_type = task.get("type", "generic")

        self.logger.info(f"开始评估技能 [{skill_name}] Lv.{current_level} 的训练结果")

        # 解析评估配置
        eval_config = self.config_resolver.resolve(skill_definition, task_type)
        pass_threshold = self.config_resolver.calculate_threshold(eval_config, current_level)

        # 构建评估上下文
        context = EvaluationContext(
            skill_id=skill_id,
            skill_name=skill_name,
            skill_description=skill_definition.get("description", ""),
            skill_capabilities=skill_definition.get("capabilities", []),
            current_level=current_level,
            task_type=task_type,
            task_description=task.get("description", task.get("name", "")),
            task_params=self._extract_task_params(task),
            execution_result=execution_result,
            execution_outputs=outputs or [],
            dimensions=eval_config["dimensions"],
            pass_threshold=pass_threshold
        )

        # 尝试AI评估
        try:
            if self.ai_adapter and self.ai_adapter.config.api_key:
                result = self._ai_evaluate(context)
                if result:
                    self.logger.info(
                        f"AI评估完成: {skill_name} - "
                        f"得分 {result.total_score:.1f}, "
                        f"{'通过' if result.passed else '未通过'}"
                    )
                    # 详细评估日志
                    self._log_evaluation_details(result)
                    return result
            else:
                self.logger.debug("AI适配器不可用，使用规则评估")
        except Exception as e:
            self.logger.warning(f"AI评估失败，回退到规则评估: {e}")

        # 回退到规则评估
        return self._rule_evaluate(context)

    def _extract_task_params(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        提取任务参数，排除元数据
        """
        exclude_keys = {"type", "name", "description", "difficulty"}
        return {k: v for k, v in task.items() if k not in exclude_keys}

    def _log_evaluation_details(self, result) -> None:
        """输出详细评估信息到日志，方便调试"""
        self.logger.info(
            f"  评估方法: {result.evaluation_method} | "
            f"阈值: {result.pass_threshold:.1f} | "
            f"决策: {result.decision.value}"
        )

        # 维度得分
        if result.dimension_scores:
            self.logger.info("  维度得分:")
            for ds in result.dimension_scores:
                feedback_text = (
                    f" | {ds.feedback[:80]}"
                    if ds.feedback else ""
                )
                self.logger.info(
                    f"    - {ds.name}: "
                    f"{ds.score:.1f}/10 "
                    f"(权重 {ds.weight:.0%}, "
                    f"加权 {ds.weighted_score:.2f})"
                    f"{feedback_text}"
                )

        # 总体反馈
        if result.overall_feedback:
            feedback = result.overall_feedback
            self.logger.info(
                f"  总体反馈: {feedback[:200]}"
                f"{'...' if len(feedback) > 200 else ''}"
            )

        # 改进建议
        if result.improvement_suggestions:
            self.logger.info("  改进建议:")
            for i, s in enumerate(
                result.improvement_suggestions[:5], 1
            ):
                text = s if isinstance(s, str) else str(s)
                self.logger.info(f"    {i}. {text[:100]}")

        # AI 原始响应（debug 级别，避免日志过长）
        if hasattr(result, 'raw_ai_response') and result.raw_ai_response:
            self.logger.debug(
                f"  AI原始响应:\n{result.raw_ai_response[:1000]}"
            )

    def _ai_evaluate(self, context: EvaluationContext) -> Optional[EvaluationResult]:
        """
        使用AI进行评估

        Args:
            context: 评估上下文

        Returns:
            评估结果，失败返回None
        """
        # 构建评估提示词
        try:
            prompt = self._build_evaluation_prompt(context)
        except Exception as e:
            self.logger.error(f"构建评估提示词失败: {e}")
            return None

        # 调用AI (使用适配器的默认温度设置)
        response = self.ai_adapter._call_ai(prompt)

        if not response.get("success"):
            self.logger.warning(f"AI调用失败: {response.get('error')}")
            return None

        content = response.get("content", "")

        # 解析AI响应
        return self._parse_ai_response(content, context)

    def _build_evaluation_prompt(self, context: EvaluationContext) -> str:
        """
        构建评估提示词

        Args:
            context: 评估上下文

        Returns:
            完整的评估提示词
        """
        # 维度说明
        dimensions_text = self._format_dimensions(context.dimensions)

        # 上下文信息
        context_text = context.to_prompt_context()

        prompt = f"""你是一个严格的技能训练评估专家。请根据以下信息对技能训练结果进行评估。

{context_text}

## 评估维度
请按照以下维度进行评分（每个维度0-10分）：

{dimensions_text}

## 通过阈值
- 当前等级: Lv.{context.current_level}
- 通过阈值: {context.pass_threshold:.2f} (即加权总分需达到 {context.pass_threshold * 10:.1f} 分)

## 核心评估原则（必须遵守）

1. **实质内容优先于形式**：评估的是"做了什么"，不是"框架写得好不好"。
   - 如果产出物只有标题和空白模板，即使结构清晰，也不应通过。
   - 占位符（如"[请填写...]"、"[待补充]"等）不算实质内容。
   - 一个结构完美但全是占位符的模板，得分不应超过3分。

2. **评估实际能力**：技能训练是要验证技能的真实执行能力。
   - 如果执行结果显示"未找到结果"、"生成失败"等，应给极低分。
   - 产出物长度过短、缺少核心内容的，应大幅扣分。
   - 空的检索结果、只有提示语没有分析的，不应通过。

3. **等级越高，标准越严**：
   - Lv.0-5: 基本完成即可通过
   - Lv.6-10: 需要有实质内容和一定质量
   - Lv.11+: 需要高质量、有深度的专业产出

## 评估要求
请严格按照以下JSON格式输出评估结果：

```json
{{
    "dimension_scores": [
        {{"name": "维度名称", "score": 8.5, "feedback": "该维度的具体反馈"}}
    ],
    "total_score": 7.8,
    "passed": true,
    "decision": "upgrade",
    "overall_feedback": "整体评价...",
    "improvement_suggestions": ["建议1", "建议2"]
}}
```

字段说明：
- dimension_scores: 各维度评分，score为0-10的浮点数
- total_score: 加权总分（0-10）
- passed: 是否通过（total_score/10 >= {context.pass_threshold:.2f}）
- decision: "upgrade"(建议升级), "maintain"(维持等级), "needs_practice"(需要更多练习)
- overall_feedback: 整体评价
- improvement_suggestions: 改进建议列表

请直接输出JSON，不要有其他内容。"""

        return prompt

    def _format_dimensions(self, dimensions: List[Dict[str, Any]]) -> str:
        """
        格式化维度为文本
        """
        lines = []
        for i, dim in enumerate(dimensions, 1):
            lines.append(f"{i}. **{dim['name']}** (权重: {dim['weight']:.0%})")
            lines.append(f"   - 评估标准: {dim['description']}")
            lines.append(f"   - 评分指南: {dim['scoring_guide']}")
            lines.append("")
        return "\n".join(lines)

    def _parse_ai_response(
        self,
        content: str,
        context: EvaluationContext
    ) -> Optional[EvaluationResult]:
        """
        解析AI响应

        Args:
            content: AI响应内容
            context: 评估上下文

        Returns:
            评估结果
        """
        # 策略1: 结构化JSON解析
        result = self._parse_json_response(content, context)
        if result:
            return result

        # 策略2: 从自然语言文本中提取分数
        self.logger.info("JSON解析失败，尝试从文本中提取评估结果")
        result = self._parse_text_response(content, context)
        if result:
            return result

        self.logger.warning(
            f"无法从AI响应中解析评估结果，"
            f"响应前500字符:\n{content[:500]}"
        )
        return None

    def _parse_json_response(
        self,
        content: str,
        context: EvaluationContext
    ) -> Optional[EvaluationResult]:
        """从AI响应中提取JSON格式的评估结果"""
        try:
            data = safe_json_loads(content)

            # 解析维度分数
            dimension_scores = []
            dim_name_to_weight = {d["name"]: d["weight"] for d in context.dimensions}

            for ds in data.get("dimension_scores", []):
                name = ds.get("name", "")
                score = float(ds.get("score", 0))
                weight = dim_name_to_weight.get(name, 0.25)

                dimension_scores.append(DimensionScore(
                    name=name,
                    score=score,
                    weight=weight,
                    weighted_score=score * weight,
                    feedback=ds.get("feedback", "")
                ))

            # 计算总分（如果AI没给或不准确，重新计算）
            if dimension_scores:
                calculated_total = sum(ds.weighted_score for ds in dimension_scores)
            else:
                calculated_total = data.get("total_score", 0)

            total_score = data.get("total_score", calculated_total)

            # 判断是否通过
            passed = (total_score / 10.0) >= context.pass_threshold

            # 解析决策
            decision_str = data.get("decision", "maintain")
            decision_map = {
                "upgrade": LevelDecision.UPGRADE,
                "maintain": LevelDecision.MAINTAIN,
                "needs_practice": LevelDecision.NEEDS_PRACTICE
            }
            decision = decision_map.get(decision_str, LevelDecision.MAINTAIN)

            # 如果通过但decision不是upgrade，修正为upgrade
            if passed and decision != LevelDecision.UPGRADE:
                decision = LevelDecision.UPGRADE

            # 如果未通过但decision是upgrade，修正
            if not passed and decision == LevelDecision.UPGRADE:
                decision = LevelDecision.NEEDS_PRACTICE

            return EvaluationResult(
                skill_id=context.skill_id,
                skill_name=context.skill_name,
                current_level=context.current_level,
                passed=passed,
                total_score=total_score,
                pass_threshold=context.pass_threshold * 10,  # 转换为10分制
                dimension_scores=dimension_scores,
                decision=decision,
                overall_feedback=data.get("overall_feedback", ""),
                improvement_suggestions=data.get(
                    "improvement_suggestions", []
                ),
                evaluation_method="ai",
                raw_ai_response=content,
                task_type=context.task_type,
                task_description=context.task_description
            )

        except Exception as e:
            self.logger.debug(f"JSON解析失败: {e}")
            return None

    def _parse_text_response(
        self,
        content: str,
        context: EvaluationContext
    ) -> Optional[EvaluationResult]:
        """
        从自然语言文本中提取评估分数（AI未按JSON格式输出时的回退）

        支持的模式:
        - "总分: 7.5" / "总分：7.5分" / "total_score: 7.5"
        - "维度名称: 8分" / "维度名称（8.5分）" / "维度名称: 8.5/10"
        - "通过" / "未通过" / "建议升级" / "维持等级"
        """
        try:
            # 提取各维度分数
            dimension_scores = []
            for dim in context.dimensions:
                name = dim["name"]
                weight = dim["weight"]
                score = self._extract_dimension_score(content, name)
                if score is not None:
                    dimension_scores.append(DimensionScore(
                        name=name,
                        score=score,
                        weight=weight,
                        weighted_score=score * weight,
                        feedback=""
                    ))

            # 提取总分
            total_score = self._extract_total_score(content)

            # 如果有维度分数但没总分，计算加权总分
            if dimension_scores and total_score is None:
                total_score = sum(
                    ds.weighted_score for ds in dimension_scores
                )

            # 如果没有维度分数也没有总分，放弃
            if total_score is None:
                self.logger.debug("无法从文本中提取任何分数")
                return None

            # 判断通过
            passed = (total_score / 10.0) >= context.pass_threshold

            # 提取决策
            decision = self._extract_decision(content)
            if decision is None:
                if passed:
                    decision = LevelDecision.UPGRADE
                else:
                    decision = LevelDecision.NEEDS_PRACTICE

            # 提取反馈文本（取前300字符作为整体反馈）
            feedback = content.strip()[:300]

            self.logger.info(
                f"从文本提取评估: 总分={total_score:.1f}, "
                f"维度数={len(dimension_scores)}, "
                f"{'通过' if passed else '未通过'}"
            )

            return EvaluationResult(
                skill_id=context.skill_id,
                skill_name=context.skill_name,
                current_level=context.current_level,
                passed=passed,
                total_score=total_score,
                pass_threshold=context.pass_threshold * 10,
                dimension_scores=dimension_scores,
                decision=decision,
                overall_feedback=feedback,
                improvement_suggestions=[],
                evaluation_method="ai_text",
                raw_ai_response=content,
                task_type=context.task_type,
                task_description=context.task_description
            )

        except Exception as e:
            self.logger.debug(f"文本解析失败: {e}")
            return None

    @staticmethod
    def _extract_dimension_score(
        text: str, dim_name: str
    ) -> Optional[float]:
        """从文本中提取指定维度的分数"""
        # 模式: "维度名称: 8.5分" / "维度名称：8.5" / "维度名称（8.5分）"
        # 也支持 "维度名称: 8.5/10"
        patterns = [
            rf'{re.escape(dim_name)}[：:\s]*(\d+(?:\.\d+)?)\s*[分/]',
            rf'{re.escape(dim_name)}[：:\s]*(\d+(?:\.\d+)?)',
            rf'{re.escape(dim_name)}[（(]\s*(\d+(?:\.\d+)?)\s*分?[）)]',
        ]
        for pattern in patterns:
            m = re.search(pattern, text)
            if m:
                score = float(m.group(1))
                if 0 <= score <= 10:
                    return score
        return None

    @staticmethod
    def _extract_total_score(text: str) -> Optional[float]:
        """从文本中提取总分"""
        patterns = [
            r'(?:总分|total_score|加权总分|综合[评得]分)[：:\s]*(\d+(?:\.\d+)?)',
            r'(\d+(?:\.\d+)?)\s*[分/]\s*(?:总分|满分)',
            r'(?:最终|综合)\s*(?:评分|得分|分数)[：:\s]*(\d+(?:\.\d+)?)',
        ]
        for pattern in patterns:
            m = re.search(pattern, text, re.IGNORECASE)
            if m:
                score = float(m.group(1))
                if 0 <= score <= 10:
                    return score
        return None

    @staticmethod
    def _extract_decision(text: str) -> Optional[LevelDecision]:
        """从文本中提取决策建议"""
        if re.search(r'建议升级|recommend.*upgrade|升级到', text, re.I):
            return LevelDecision.UPGRADE
        if re.search(r'维持等级|maintain|保持当前', text, re.I):
            return LevelDecision.MAINTAIN
        if re.search(r'需要.*练习|needs.*practice|未通过', text, re.I):
            return LevelDecision.NEEDS_PRACTICE
        return None

    def _rule_evaluate(self, context: EvaluationContext) -> EvaluationResult:
        """
        使用规则进行评估（AI不可用时的回退方案）

        Args:
            context: 评估上下文

        Returns:
            评估结果
        """
        self.logger.info("使用规则评估")

        result = context.execution_result
        task_type = context.task_type

        # 基于任务类型的简单规则评估
        if task_type == "research":
            score, feedback = self._rule_eval_research(result, context)
        elif task_type == "drafting":
            score, feedback = self._rule_eval_drafting(result, context)
        elif task_type == "analysis":
            score, feedback = self._rule_eval_analysis(result, context)
        else:
            score, feedback = self._rule_eval_generic(result, context)

        passed = score >= (context.pass_threshold * 10)

        if passed:
            decision = LevelDecision.UPGRADE
        elif score >= (context.pass_threshold * 10 - 1):  # 接近通过
            decision = LevelDecision.MAINTAIN
        else:
            decision = LevelDecision.NEEDS_PRACTICE

        # 生成简单的维度分数
        dimension_scores = []
        for dim in context.dimensions[:3]:  # 只取前3个维度
            dim_score = score + (hash(dim["name"]) % 3 - 1) * 0.5  # 添加一些变化
            dim_score = max(0, min(10, dim_score))
            dimension_scores.append(DimensionScore(
                name=dim["name"],
                score=dim_score,
                weight=dim["weight"],
                weighted_score=dim_score * dim["weight"],
                feedback=f"基于规则评估: {dim['name']}"
            ))

        return EvaluationResult(
            skill_id=context.skill_id,
            skill_name=context.skill_name,
            current_level=context.current_level,
            passed=passed,
            total_score=score,
            pass_threshold=context.pass_threshold * 10,
            dimension_scores=dimension_scores,
            decision=decision,
            overall_feedback=feedback,
            improvement_suggestions=["建议启用AI评估以获得更准确的反馈"],
            evaluation_method="rule",
            task_type=context.task_type,
            task_description=context.task_description
        )

    def _rule_eval_research(
        self,
        result: Dict[str, Any],
        context: EvaluationContext
    ) -> tuple:
        """研究类任务的规则评估"""
        if not result.get("success", True):
            return 3.0, f"执行失败: {result.get('error', '未知错误')}"

        res = result.get("result", result)
        found_count = res.get("total_found", res.get("found", 0))
        expected = context.task_params.get("expected_count", 1)

        if found_count >= expected:
            score = 7.0 + min(found_count / expected, 1.5) * 2
            feedback = f"检索完成，找到{found_count}条结果（期望{expected}条）"
        elif found_count > 0:
            score = 5.0 + (found_count / expected) * 2
            feedback = f"检索部分完成，找到{found_count}条（期望{expected}条）"
        else:
            score = 3.0
            feedback = "未找到任何结果"

        return min(score, 10), feedback

    def _rule_eval_drafting(
        self,
        result: Dict[str, Any],
        context: EvaluationContext
    ) -> tuple:
        """文档类任务的规则评估"""
        if not result.get("success", True):
            return 3.0, f"执行失败: {result.get('error', '未知错误')}"

        # 获取实际文档内容（不用 str(result) 作为后备）
        res = result.get("result", result)
        content = res.get("content", "")
        if not content:
            content = result.get("content", "")

        content_len = len(content) if content else 0
        # 如果没有内容文本，退而使用 content_length 字段
        if content_len == 0:
            content_len = result.get("content_length",
                                    res.get("content_length", 0))

        # 检测占位符（[请填写...] 表示模板未填写）
        placeholder_count = content.count('[请填写') if content else 0

        # 评分：内容量 + 实质性内容
        if content_len >= 800 and placeholder_count == 0:
            score = 8.5
            feedback = f"文档生成完整（{content_len}字符）"
        elif content_len >= 500 and placeholder_count <= 1:
            score = 7.0
            feedback = f"文档基本完成（{content_len}字符）"
        elif content_len >= 300 and placeholder_count == 0:
            score = 6.5
            feedback = f"文档内容可用（{content_len}字符）"
        elif content_len >= 200 and placeholder_count <= 2:
            score = 5.5
            feedback = f"文档内容尚可（{content_len}字符）"
        elif content_len >= 50:
            score = 4.0
            feedback = f"文档内容较短（{content_len}字符）"
        else:
            score = 2.0
            feedback = "文档内容严重不足"

        # 占位符惩罚
        if placeholder_count >= 3:
            penalty = min(4.0, placeholder_count * 1.0)
            score = max(1.0, score - penalty)
            feedback += f"（含{placeholder_count}处未填写占位符，" \
                        f"缺少实质内容）"

        return score, feedback

    def _rule_eval_analysis(
        self,
        result: Dict[str, Any],
        context: EvaluationContext
    ) -> tuple:
        """分析类任务的规则评估"""
        if not result.get("success", True):
            return 3.0, f"执行失败: {result.get('error', '未知错误')}"

        res = result.get("result", result)

        # 检查关键字段
        has_summary = any(k in res for k in ['summary', 'case_summary', 'analysis', 'conclusion'])
        has_details = any(k in res for k in ['details', 'findings', 'issues', 'points'])

        if has_summary and has_details:
            score = 8.0
            feedback = "分析完整，包含摘要和详细内容"
        elif has_summary:
            score = 6.5
            feedback = "分析基本完成，有摘要"
        elif has_details:
            score = 5.5
            feedback = "分析有内容，但缺少总结"
        else:
            score = 4.0
            feedback = "分析结果不完整"

        return score, feedback

    def _rule_eval_generic(
        self,
        result: Dict[str, Any],
        context: EvaluationContext
    ) -> tuple:
        """通用任务的规则评估"""
        # 检查是否有明确的失败
        if result.get("passed") is False:
            return 4.0, result.get("reason", "任务未通过")

        if result.get("passed") is True:
            return 7.5, result.get("reason", "任务完成")

        # 检查是否有success字段
        if result.get("success") is True:
            return 7.0, "任务执行成功"
        elif result.get("success") is False:
            return 3.5, result.get("error", "任务执行失败")

        # 无法判断，给中等分数
        return 6.0, "任务执行情况未知，给予中等评分"

    def batch_evaluate(
        self,
        evaluations: List[Dict[str, Any]]
    ) -> List[EvaluationResult]:
        """
        批量评估多个训练结果

        Args:
            evaluations: 评估任务列表，每个包含：
                - skill_definition: 技能定义
                - task: 训练任务
                - execution_result: 执行结果
                - current_level: 当前等级
                - outputs: 产出物列表

        Returns:
            评估结果列表
        """
        results = []
        for eval_item in evaluations:
            result = self.evaluate(
                skill_definition=eval_item["skill_definition"],
                task=eval_item["task"],
                execution_result=eval_item["execution_result"],
                current_level=eval_item.get("current_level", 0),
                outputs=eval_item.get("outputs")
            )
            results.append(result)
        return results

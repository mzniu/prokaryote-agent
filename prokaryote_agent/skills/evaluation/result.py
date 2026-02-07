"""
评估结果数据类

定义技能训练评估的结果结构。
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from datetime import datetime
from enum import Enum


class LevelDecision(Enum):
    """升级决策枚举"""
    UPGRADE = "upgrade"         # 建议升级
    MAINTAIN = "maintain"       # 维持当前等级
    NEEDS_PRACTICE = "needs_practice"  # 需要更多练习


@dataclass
class DimensionScore:
    """单个维度的评分"""
    name: str                    # 维度名称
    score: float                 # 分数 (0-10)
    weight: float                # 权重 (0-1)
    weighted_score: float        # 加权分数
    feedback: str                # 该维度的反馈

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "score": self.score,
            "weight": self.weight,
            "weighted_score": self.weighted_score,
            "feedback": self.feedback
        }


@dataclass
class EvaluationResult:
    """
    技能训练评估结果

    包含整体评分、各维度评分、升级建议等信息。
    """
    # 基本信息
    skill_id: str                           # 技能ID
    skill_name: str                         # 技能名称
    current_level: int                      # 当前等级

    # 评估结果
    passed: bool                            # 是否通过
    total_score: float                      # 总分 (0-10)
    pass_threshold: float                   # 通过阈值

    # 详细分数
    dimension_scores: List[DimensionScore] = field(default_factory=list)

    # 决策和反馈
    decision: LevelDecision = LevelDecision.MAINTAIN
    overall_feedback: str = ""              # 整体评价
    improvement_suggestions: List[str] = field(default_factory=list)  # 改进建议

    # 元数据
    evaluated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    evaluation_method: str = "ai"           # 评估方法: "ai" 或 "rule"
    raw_ai_response: Optional[str] = None   # 原始AI响应（调试用）

    # 训练任务信息
    task_type: str = ""
    task_description: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "skill_id": self.skill_id,
            "skill_name": self.skill_name,
            "current_level": self.current_level,
            "passed": self.passed,
            "total_score": self.total_score,
            "pass_threshold": self.pass_threshold,
            "dimension_scores": [d.to_dict() for d in self.dimension_scores],
            "decision": self.decision.value,
            "overall_feedback": self.overall_feedback,
            "improvement_suggestions": self.improvement_suggestions,
            "evaluated_at": self.evaluated_at,
            "evaluation_method": self.evaluation_method,
            "task_type": self.task_type,
            "task_description": self.task_description
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'EvaluationResult':
        """从字典创建"""
        dimension_scores = [
            DimensionScore(**d) for d in data.get("dimension_scores", [])
        ]

        return cls(
            skill_id=data.get("skill_id", ""),
            skill_name=data.get("skill_name", ""),
            current_level=data.get("current_level", 0),
            passed=data.get("passed", False),
            total_score=data.get("total_score", 0.0),
            pass_threshold=data.get("pass_threshold", 0.6),
            dimension_scores=dimension_scores,
            decision=LevelDecision(data.get("decision", "maintain")),
            overall_feedback=data.get("overall_feedback", ""),
            improvement_suggestions=data.get("improvement_suggestions", []),
            evaluated_at=data.get("evaluated_at", datetime.now().isoformat()),
            evaluation_method=data.get("evaluation_method", "ai"),
            task_type=data.get("task_type", ""),
            task_description=data.get("task_description", "")
        )

    def get_summary(self) -> str:
        """获取评估摘要"""
        status = "✓ 通过" if self.passed else "✗ 未通过"
        decision_text = {
            LevelDecision.UPGRADE: "🎉 建议升级",
            LevelDecision.MAINTAIN: "📊 维持等级",
            LevelDecision.NEEDS_PRACTICE: "📚 需要练习"
        }

        lines = [
            f"【{self.skill_name}】训练评估结果",
            f"当前等级: Lv.{self.current_level}",
            f"评估结果: {status}",
            f"总分: {self.total_score:.1f}/10 (阈值: {self.pass_threshold:.1f})",
            f"决策建议: {decision_text.get(self.decision, '未知')}",
            "",
            "维度得分:",
        ]

        for ds in self.dimension_scores:
            lines.append(f"  • {ds.name}: {ds.score:.1f}/10 (权重{ds.weight:.0%})")

        if self.overall_feedback:
            lines.extend(["", "整体评价:", f"  {self.overall_feedback}"])

        if self.improvement_suggestions:
            lines.extend(["", "改进建议:"])
            for suggestion in self.improvement_suggestions:
                lines.append(f"  • {suggestion}")

        return "\n".join(lines)


@dataclass
class EvaluationContext:
    """
    评估上下文

    收集评估所需的所有信息。
    """
    # 技能信息
    skill_id: str
    skill_name: str
    skill_description: str
    skill_capabilities: List[str]
    current_level: int

    # 任务信息
    task_type: str
    task_description: str
    task_params: Dict[str, Any]

    # 执行结果
    execution_result: Dict[str, Any]
    execution_outputs: List[str]  # 输出文件路径

    # 评估配置
    dimensions: List[Dict[str, Any]]
    pass_threshold: float

    def to_prompt_context(self) -> str:
        """
        转换为提示词上下文

        Returns:
            格式化的上下文字符串，供AI评估使用
        """
        # 技能信息
        skill_info = f"""## 技能信息
- 技能ID: {self.skill_id}
- 技能名称: {self.skill_name}
- 当前等级: Lv.{self.current_level}
- 技能描述: {self.skill_description}
- 技能能力: {', '.join(self.skill_capabilities) if self.skill_capabilities else '无'}"""

        # 任务信息
        task_params_str = self._format_result(self.task_params) if self.task_params else '{}'
        task_info = f"""## 训练任务
- 任务类型: {self.task_type}
- 任务描述: {self.task_description}
- 任务参数: {task_params_str}"""

        # 执行结果
        result_info = f"""## 执行结果
```json
{self._format_result(self.execution_result)}
```"""

        # 产出物
        if self.execution_outputs:
            # 处理可能是字典列表或字符串列表的情况
            output_lines = []
            for o in self.execution_outputs:
                if isinstance(o, dict):
                    # 如果是字典，提取路径和标题
                    path = o.get('path', o.get('title', str(o)))
                    output_lines.append(f"- {path}")
                else:
                    output_lines.append(f"- {o}")
            outputs_info = f"""## 产出物
产出了以下文件:
{chr(10).join(output_lines)}"""
        else:
            outputs_info = "## 产出物\n无文件产出"

        return f"{skill_info}\n\n{task_info}\n\n{result_info}\n\n{outputs_info}"

    def _format_result(self, result: Dict[str, Any], indent: int = 2) -> str:
        """格式化执行结果，限制长度"""
        import json
        try:
            formatted = json.dumps(result, ensure_ascii=False, indent=indent)
            # 限制长度，避免token过多
            if len(formatted) > 2000:
                formatted = formatted[:2000] + "\n... (结果已截断)"
            return formatted
        except Exception:
            return str(result)[:2000]

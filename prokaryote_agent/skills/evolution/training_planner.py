"""
AI 训练规划器

每轮进化前，由 AI 分析全局训练档案、技能状态、用户反馈，
输出结构化训练计划：练哪个技能、练什么内容、侧重哪个维度。

替代原有硬编码的阶段系统（sprouting/growing/maturing/specializing）。
"""
import json
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def create_training_plan(
    skill_stats: List[Dict[str, Any]],
    archive_analysis: Dict[str, Any],
    available_skills: List[Dict[str, Any]],
    max_picks: int = 3,
    ai_adapter=None,
) -> Dict[str, Any]:
    """
    AI 驱动的训练计划生成

    Args:
        skill_stats: 每个已学技能的状态
            [{skill_id, name, level, domain, tier,
              success_rate, avg_score, weak_dims}]
        archive_analysis: training_archive.analyze_global() 的输出
        available_skills: 尚未学习但可以学习的技能列表
        max_picks: 本轮最多训练几个技能
        ai_adapter: AIAdapter 实例

    Returns:
        {
            plan: [{
                action: "train" | "unlock" | "repair",
                skill_id: str,
                reason: str,
                focus_dimensions: [str],
                task_hint: str,
                priority: int  (1=最高)
            }],
            analysis_summary: str,
            method: "ai" | "rule"
        }
    """
    # 优先 AI 规划
    if ai_adapter and ai_adapter.config.api_key:
        result = _ai_plan(
            skill_stats, archive_analysis,
            available_skills, max_picks, ai_adapter,
        )
        if result:
            return result

    # 回退：基于规则的规划
    return _rule_plan(
        skill_stats, archive_analysis,
        available_skills, max_picks,
    )


# ==================== AI 规划 ====================

def _ai_plan(
    skill_stats, archive_analysis,
    available_skills, max_picks, ai_adapter,
) -> Optional[Dict[str, Any]]:
    """用 AI 生成训练计划"""
    prompt = _build_plan_prompt(
        skill_stats, archive_analysis,
        available_skills, max_picks,
    )

    try:
        result = ai_adapter._call_ai(prompt)
        if not result.get("success"):
            return None

        content = result["content"]
        plan = _parse_plan_response(content, max_picks)
        if plan:
            logger.info(
                "🧠 AI训练规划完成: %d 个训练项",
                len(plan["plan"]),
            )
            for item in plan["plan"]:
                logger.info(
                    "   [P%d] %s %s — %s",
                    item["priority"],
                    item["action"],
                    item["skill_id"],
                    item["reason"][:80],
                )
            return plan
    except Exception as e:
        logger.warning("AI训练规划失败: %s", e)

    return None


def _build_plan_prompt(
    skill_stats, archive_analysis,
    available_skills, max_picks,
) -> str:
    """构建训练规划 prompt"""
    # 已学技能状态
    skills_text = ""
    for s in skill_stats[:20]:
        weak = s.get("weak_dims", {})
        weak_str = (
            ", ".join(f"{k}({v}次)" for k, v in weak.items())
            if weak else "无"
        )
        skills_text += (
            f"- {s['skill_id']} (Lv.{s.get('level', 0)}, "
            f"{s.get('domain', '?')}): "
            f"成功率{s.get('success_rate', '?')}, "
            f"均分{s.get('avg_score', '?')}, "
            f"弱项[{weak_str}]\n"
        )

    # 可学习新技能
    new_skills_text = ""
    for ns in available_skills[:10]:
        new_skills_text += (
            f"- {ns.get('skill_id', ns.get('id', '?'))}: "
            f"{ns.get('name', '?')} "
            f"({ns.get('domain', '?')})\n"
        )

    # 全局分析
    global_text = ""
    if archive_analysis.get("data_available"):
        global_text = (
            f"总训练次数: {archive_analysis.get('total_trainings', 0)}\n"
            f"总体成功率: {archive_analysis.get('overall_success_rate', 0)}\n"
            f"全局弱项维度: {archive_analysis.get('global_weak_dimensions', {})}\n"
        )
        struggling = archive_analysis.get(
            "most_struggling_skills", []
        )
        if struggling:
            global_text += "最需提升的技能: " + ", ".join(
                f"{s['skill_id']}(成功率{s['success_rate']})"
                for s in struggling
            ) + "\n"

        uf = archive_analysis.get("user_feedback_summary", [])
        if uf:
            global_text += "用户反馈:\n"
            for fb in uf[:3]:
                global_text += f"  - {fb[:100]}\n"

    return f"""你是一个AI技能训练规划器。请根据以下信息制定本轮训练计划。

## 已学技能现状
{skills_text if skills_text else "暂无已学技能"}

## 可学习的新技能
{new_skills_text if new_skills_text else "暂无新技能可学"}

## 全局训练分析
{global_text if global_text else "暂无训练数据"}

## 规划要求
1. 从以上技能中选择最多 {max_picks} 个进行训练
2. 每个训练项指定 action（train=提升已有技能, unlock=学习新技能, repair=修复低分技能）
3. 优先级原则：
   - 修复严重问题 > 提升弱项 > 学习新技能
   - 用户反馈直接相关的维度优先
   - 成功率低的技能需要针对性训练
   - 长时间未训练的技能适当安排
4. 给出 focus_dimensions（侧重维度）和 task_hint（训练任务建议）

请返回严格JSON：
```json
{{
  "plan": [
    {{
      "action": "train",
      "skill_id": "xxx",
      "reason": "选择原因",
      "focus_dimensions": ["维度1", "维度2"],
      "task_hint": "具体训练建议",
      "priority": 1
    }}
  ],
  "analysis_summary": "整体分析总结"
}}
```"""


def _parse_plan_response(
    content: str, max_picks: int,
) -> Optional[Dict[str, Any]]:
    """解析 AI 返回的训练计划"""
    # 尝试提取 JSON
    import re
    json_match = re.search(
        r'```(?:json)?\s*(.*?)```',
        content, re.DOTALL,
    )
    text = json_match.group(1) if json_match else content

    # 找 { 开始的 JSON
    start = text.find('{')
    if start < 0:
        return None
    # 找最后一个 }
    end = text.rfind('}')
    if end < 0:
        return None

    try:
        data = json.loads(text[start:end + 1])
    except json.JSONDecodeError:
        return None

    plan_list = data.get("plan", [])
    if not isinstance(plan_list, list) or not plan_list:
        return None

    # 规范化
    clean_plan = []
    for i, item in enumerate(plan_list[:max_picks]):
        clean_plan.append({
            "action": item.get("action", "train"),
            "skill_id": item.get("skill_id", ""),
            "reason": item.get("reason", ""),
            "focus_dimensions": item.get(
                "focus_dimensions", []
            ),
            "task_hint": item.get("task_hint", ""),
            "priority": item.get("priority", i + 1),
        })

    return {
        "plan": clean_plan,
        "analysis_summary": data.get(
            "analysis_summary", ""
        ),
        "method": "ai",
    }


# ==================== 规则回退 ====================

def _rule_plan(
    skill_stats, archive_analysis,
    available_skills, max_picks,
) -> Dict[str, Any]:
    """基于规则的训练计划（AI不可用时回退）"""
    plan = []

    # 1. 修复：成功率低于 0.3 且训练次数≥3 的技能
    for s in skill_stats:
        if (s.get("success_rate", 1) < 0.3
                and s.get("total_trainings", 0) >= 3):
            plan.append({
                "action": "repair",
                "skill_id": s["skill_id"],
                "reason": (
                    f"成功率仅{s['success_rate']}, "
                    f"需要修复"
                ),
                "focus_dimensions": list(
                    s.get("weak_dims", {}).keys()
                )[:2],
                "task_hint": "针对弱项维度专项训练",
                "priority": len(plan) + 1,
            })

    # 2. 训练：找最需要提升的技能（分数最低或弱项最多）
    trainable = sorted(
        [s for s in skill_stats
         if s.get("success_rate", 1) >= 0.3
         and s["skill_id"] not in
         {p["skill_id"] for p in plan}],
        key=lambda s: s.get("avg_score", 10),
    )
    for s in trainable:
        if len(plan) >= max_picks:
            break
        plan.append({
            "action": "train",
            "skill_id": s["skill_id"],
            "reason": (
                f"均分{s.get('avg_score', '?')}, "
                f"有提升空间"
            ),
            "focus_dimensions": list(
                s.get("weak_dims", {}).keys()
            )[:2],
            "task_hint": "",
            "priority": len(plan) + 1,
        })

    # 3. 解锁新技能（如果还有名额）
    if len(plan) < max_picks and available_skills:
        ns = available_skills[0]
        plan.append({
            "action": "unlock",
            "skill_id": ns.get(
                "skill_id", ns.get("id", "new_skill")
            ),
            "reason": "扩展能力范围",
            "focus_dimensions": [],
            "task_hint": "",
            "priority": len(plan) + 1,
        })

    return {
        "plan": plan[:max_picks],
        "analysis_summary": "基于规则的训练计划",
        "method": "rule",
    }

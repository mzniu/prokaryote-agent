"""
训练档案持久化存储

记录每次训练的完整数据（任务、结果、评估、弱项维度），
供 AI 训练规划器和智能训练选择使用。
重启不丢失。
"""
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from collections import Counter

logger = logging.getLogger(__name__)

ARCHIVE_DIR = (
    Path(__file__).resolve().parent.parent.parent
    / "prokaryote_agent" / "log" / "training_archive"
)


def _ensure_dir():
    ARCHIVE_DIR.mkdir(parents=True, exist_ok=True)


# ==================== 写入 ====================

def record_training(
    skill_id: str,
    level: int,
    target_level: int,
    task: Dict[str, Any],
    execution_result: Dict[str, Any],
    evaluation: Dict[str, Any],
    success: bool,
    duration_ms: int = 0,
    knowledge_stored: int = 0,
    code_evolved: bool = False,
) -> Dict[str, Any]:
    """
    记录一次训练的完整档案

    Returns:
        写入的档案记录
    """
    _ensure_dir()

    record = {
        "skill_id": skill_id,
        "timestamp": datetime.now().isoformat(),
        "level": level,
        "target_level": target_level,
        "success": success,
        # 训练任务
        "task_name": task.get("name", ""),
        "task_type": task.get("type", "generic"),
        "task_difficulty": task.get("difficulty", 1),
        "task_query": task.get("query", ""),
        # 评估结果
        "score": evaluation.get("score", 0),
        "threshold": evaluation.get("threshold", 6.0),
        "method": evaluation.get("method", "unknown"),
        "reason": evaluation.get("reason", "")[:300],
        "dimension_scores": _extract_dimensions(evaluation),
        "weak_dimensions": _find_weak_dimensions(evaluation),
        "improvement_suggestions": (
            evaluation.get("improvement_suggestions", [])[:5]
        ),
        # 执行统计
        "duration_ms": duration_ms,
        "knowledge_stored": knowledge_stored,
        "code_evolved": code_evolved,
        # 执行结果摘要
        "exec_summary": _summarize_execution(execution_result),
    }

    # 按日期分文件
    date_str = datetime.now().strftime("%Y-%m-%d")
    fp = ARCHIVE_DIR / f"{date_str}.jsonl"
    try:
        with open(fp, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        logger.debug(
            "训练档案已记录: %s Lv.%d %s",
            skill_id, level, "✓" if success else "✗",
        )
    except Exception as e:
        logger.warning("训练档案写入失败: %s", e)

    return record


def _extract_dimensions(evaluation: Dict) -> List[Dict]:
    """提取维度评分为精简格式"""
    dims = evaluation.get("dimension_scores", [])
    result = []
    for d in dims:
        if isinstance(d, dict):
            result.append({
                "name": d.get("name", d.get("dimension", "")),
                "score": d.get("score", 0),
                "weight": d.get("weight", 0),
            })
    return result


def _find_weak_dimensions(evaluation: Dict) -> List[str]:
    """找出低于 6.0 分的弱项维度"""
    dims = evaluation.get("dimension_scores", [])
    weak = []
    for d in dims:
        if isinstance(d, dict):
            score = d.get("score", 10)
            name = d.get("name", d.get("dimension", ""))
            if score < 6.0 and name:
                weak.append(name)
    return weak


def _summarize_execution(result: Dict) -> Dict:
    """提取执行结果摘要（避免存储过大内容）"""
    return {
        "success": result.get("success", False),
        "total_found": result.get("total_found", 0),
        "stored_to_kb": result.get("stored_to_kb", 0),
        "from_cache": result.get("from_cache", False),
        "has_content": bool(result.get("content")),
    }


# ==================== 读取 ====================

def get_skill_history(
    skill_id: str,
    limit: int = 20,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """获取某个技能的训练历史"""
    return _query_archive(
        skill_id=skill_id, limit=limit, days=days,
    )


def get_all_history(
    limit: int = 100,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """获取全部训练历史"""
    return _query_archive(limit=limit, days=days)


def _query_archive(
    skill_id: Optional[str] = None,
    limit: int = 100,
    days: int = 30,
) -> List[Dict[str, Any]]:
    """查询训练档案"""
    _ensure_dir()
    cutoff = (datetime.now() - timedelta(days=days)).isoformat()
    records = []

    files = sorted(ARCHIVE_DIR.glob("*.jsonl"), reverse=True)
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    r = json.loads(line)
                    if r.get("timestamp", "") < cutoff:
                        continue
                    if skill_id and r.get("skill_id") != skill_id:
                        continue
                    records.append(r)
        except Exception:
            continue
        if len(records) >= limit * 2:
            break

    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records[:limit]


# ==================== 分析 ====================

def analyze_skill(skill_id: str, days: int = 14) -> Dict[str, Any]:
    """
    分析单个技能的训练状况

    Returns:
        {
            skill_id, total_trainings, success_rate,
            avg_score, recent_trend, weak_dimensions,
            recent_suggestions, last_trained
        }
    """
    history = get_skill_history(skill_id, limit=50, days=days)
    if not history:
        return {
            "skill_id": skill_id,
            "total_trainings": 0,
            "data_available": False,
        }

    total = len(history)
    successes = sum(1 for r in history if r.get("success"))
    scores = [r.get("score", 0) for r in history]
    avg_score = sum(scores) / len(scores) if scores else 0

    # 趋势：最近5次 vs 之前
    recent = scores[:5]
    older = scores[5:10]
    if recent and older:
        trend = sum(recent) / len(recent) - sum(older) / len(older)
    else:
        trend = 0

    # 弱项维度统计
    weak_counter = Counter()
    for r in history:
        for dim in r.get("weak_dimensions", []):
            weak_counter[dim] += 1

    # 最近改进建议（去重）
    seen_suggestions = set()
    suggestions = []
    for r in history[:10]:
        for s in r.get("improvement_suggestions", []):
            key = s[:50]
            if key not in seen_suggestions:
                seen_suggestions.add(key)
                suggestions.append(s)
            if len(suggestions) >= 5:
                break

    return {
        "skill_id": skill_id,
        "total_trainings": total,
        "success_rate": round(successes / total, 2) if total else 0,
        "avg_score": round(avg_score, 1),
        "recent_trend": round(trend, 2),
        "weak_dimensions": dict(weak_counter.most_common(5)),
        "recent_suggestions": suggestions,
        "last_trained": history[0].get("timestamp", "") if history else "",
        "current_level": history[0].get("target_level", 0),
        "data_available": True,
    }


def analyze_global(days: int = 14) -> Dict[str, Any]:
    """
    全局训练分析 — 供 AI 训练规划器使用

    Returns:
        {
            total_trainings, overall_success_rate,
            skill_summaries: [{skill_id, trainings, success_rate,
                               avg_score, weak_dims}],
            global_weak_dimensions,
            most_struggling_skills,
            most_improved_skills,
            user_feedback_summary
        }
    """
    all_records = get_all_history(limit=200, days=days)

    if not all_records:
        return {
            "total_trainings": 0,
            "data_available": False,
        }

    # 按技能分组
    by_skill: Dict[str, List[Dict]] = {}
    for r in all_records:
        sid = r.get("skill_id", "unknown")
        by_skill.setdefault(sid, []).append(r)

    total = len(all_records)
    successes = sum(1 for r in all_records if r.get("success"))

    # 每个技能的摘要
    skill_summaries = []
    for sid, records in by_skill.items():
        count = len(records)
        succ = sum(1 for r in records if r.get("success"))
        scores = [r.get("score", 0) for r in records]
        avg = sum(scores) / len(scores) if scores else 0
        weak = Counter()
        for r in records:
            for d in r.get("weak_dimensions", []):
                weak[d] += 1

        skill_summaries.append({
            "skill_id": sid,
            "trainings": count,
            "success_rate": round(succ / count, 2),
            "avg_score": round(avg, 1),
            "weak_dims": dict(weak.most_common(3)),
        })

    # 全局弱项维度
    global_weak = Counter()
    for r in all_records:
        for d in r.get("weak_dimensions", []):
            global_weak[d] += 1

    # 最挣扎的技能（成功率最低且训练次数≥2）
    struggling = sorted(
        [s for s in skill_summaries if s["trainings"] >= 2],
        key=lambda s: s["success_rate"],
    )[:3]

    # 进步最大的技能（对比最近5次和更早的分数）
    improving = []
    for sid, records in by_skill.items():
        scores = [r.get("score", 0) for r in records]
        recent = scores[:5]
        older = scores[5:10]
        if recent and older:
            diff = sum(recent) / len(recent) - sum(older) / len(older)
            improving.append({"skill_id": sid, "improvement": round(diff, 2)})
    improving.sort(key=lambda x: x["improvement"], reverse=True)

    # 用户反馈摘要
    user_feedback = []
    try:
        from web.services.feedback_service import (
            get_user_feedback_for_training,
        )
        user_feedback = get_user_feedback_for_training(limit=5)
    except (ImportError, Exception):
        pass

    return {
        "total_trainings": total,
        "overall_success_rate": round(successes / total, 2),
        "skill_summaries": skill_summaries,
        "global_weak_dimensions": dict(global_weak.most_common(5)),
        "most_struggling_skills": struggling,
        "most_improved_skills": improving[:3],
        "user_feedback_summary": user_feedback,
        "data_available": True,
    }

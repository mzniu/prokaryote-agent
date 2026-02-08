"""
反馈服务 - 用户反馈存储 + 进化策略更新

反馈闭环:
1. 用户提交反馈 → log/feedback/YYYY-MM-DD.jsonl
2. 汇总反馈热点 → config/evolution_strategy.json
3. 训练时读取策略 → 影响任务生成和评估权重
"""

import json
import logging
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent

FEEDBACK_DIR = PROJECT_ROOT / "prokaryote_agent" / "log" / "feedback"
STRATEGY_FILE = PROJECT_ROOT / "prokaryote_agent" / "config" / "evolution_strategy.json"

# 默认进化策略
DEFAULT_STRATEGY = {
    "focus_dimensions": {
        "accuracy": 0.30,
        "completeness": 0.25,
        "format": 0.15,
        "robustness": 0.15,
        "usefulness": 0.15,
    },
    "feedback_hotspots": [],
    "training_bias": {
        "domains": {},
        "skills": {},
    },
    "updated_at": None,
}


def _ensure_dirs():
    FEEDBACK_DIR.mkdir(parents=True, exist_ok=True)
    STRATEGY_FILE.parent.mkdir(parents=True, exist_ok=True)


def submit_feedback(
    interaction_id: str,
    rating: int,
    resolved: bool,
    tags: List[str] = None,
    comment: str = "",
) -> Dict[str, Any]:
    """
    提交用户反馈

    Args:
        interaction_id: 关联的交互ID
        rating: 满意度 1-5
        resolved: 是否解决了问题
        tags: 结构化标签 ['accuracy', 'completeness', ...]
        comment: 自由文本建议

    Returns:
        {"success": True, "feedback_id": "..."}
    """
    _ensure_dirs()

    feedback = {
        "feedback_id": f"fb_{datetime.now().strftime('%Y%m%d%H%M%S')}",
        "interaction_id": interaction_id,
        "timestamp": datetime.now().isoformat(),
        "rating": max(1, min(5, rating)),
        "resolved": resolved,
        "tags": tags or [],
        "comment": comment,
    }

    date_str = datetime.now().strftime("%Y-%m-%d")
    filepath = FEEDBACK_DIR / f"{date_str}.jsonl"
    try:
        with open(filepath, "a", encoding="utf-8") as f:
            f.write(json.dumps(feedback, ensure_ascii=False) + "\n")
        logger.info(
            "反馈已记录: id=%s, rating=%d, resolved=%s, tags=%s",
            feedback["feedback_id"], rating, resolved, tags
        )
    except Exception as e:
        logger.error("保存反馈失败: %s", e)
        return {"success": False, "error": str(e)}

    # 更新进化策略
    _update_strategy()

    return {"success": True, "feedback_id": feedback["feedback_id"]}


def get_feedback_list(limit: int = 50) -> List[Dict[str, Any]]:
    """获取最近反馈列表"""
    _ensure_dirs()
    records = []
    files = sorted(FEEDBACK_DIR.glob("*.jsonl"), reverse=True)
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        records.append(json.loads(line))
        except Exception:
            continue
        if len(records) >= limit:
            break
    records.sort(key=lambda r: r.get("timestamp", ""), reverse=True)
    return records[:limit]


def get_feedback_stats() -> Dict[str, Any]:
    """获取反馈统计"""
    feedbacks = get_feedback_list(limit=200)
    if not feedbacks:
        return {
            "total": 0,
            "avg_rating": 0,
            "resolved_rate": 0,
            "tag_counts": {},
        }

    total = len(feedbacks)
    avg_rating = sum(f["rating"] for f in feedbacks) / total
    resolved = sum(1 for f in feedbacks if f.get("resolved"))
    tag_counter = Counter()
    for f in feedbacks:
        tag_counter.update(f.get("tags", []))

    return {
        "total": total,
        "avg_rating": round(avg_rating, 2),
        "resolved_rate": round(resolved / total, 2),
        "tag_counts": dict(tag_counter.most_common(10)),
    }


# ==================== 进化策略管理 ====================

def get_strategy() -> Dict[str, Any]:
    """获取当前进化策略"""
    if STRATEGY_FILE.exists():
        try:
            with open(STRATEGY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return DEFAULT_STRATEGY.copy()


def _update_strategy():
    """根据累积反馈更新进化策略"""
    _ensure_dirs()
    feedbacks = get_feedback_list(limit=100)
    if not feedbacks:
        return

    strategy = get_strategy()

    # 1. 更新反馈热点
    tag_counter = Counter()
    for f in feedbacks:
        tag_counter.update(f.get("tags", []))
    strategy["feedback_hotspots"] = [
        {"tag": tag, "count": count}
        for tag, count in tag_counter.most_common(10)
    ]

    # 2. 动态调整评估维度权重
    #    用户频繁标记的维度权重提高
    tag_to_dim = {
        "accuracy": "accuracy",
        "completeness": "completeness",
        "format": "format",
        "robustness": "robustness",
        "usefulness": "usefulness",
    }

    total_tags = sum(tag_counter.values()) or 1
    dims = dict(DEFAULT_STRATEGY["focus_dimensions"])

    for tag, dim in tag_to_dim.items():
        count = tag_counter.get(tag, 0)
        if count > 0:
            # 频率越高，权重越大（最多增加0.15）
            boost = min(0.15, (count / total_tags) * 0.3)
            dims[dim] = dims.get(dim, 0.15) + boost

    # 归一化
    total_weight = sum(dims.values())
    if total_weight > 0:
        dims = {k: round(v / total_weight, 3) for k, v in dims.items()}
    strategy["focus_dimensions"] = dims

    # 3. 低评分反馈自动提取建议（将 comment 纳入策略）
    low_rating_comments = [
        f.get("comment", "") for f in feedbacks
        if f.get("rating", 5) <= 2 and f.get("comment")
    ]
    strategy["low_rating_feedback"] = low_rating_comments[:10]

    strategy["updated_at"] = datetime.now().isoformat()

    # 保存
    try:
        with open(STRATEGY_FILE, "w", encoding="utf-8") as f:
            json.dump(strategy, f, ensure_ascii=False, indent=2)
        logger.info("进化策略已更新")
    except Exception as e:
        logger.error("保存进化策略失败: %s", e)


def get_user_feedback_for_training(
    skill_id: Optional[str] = None,
    limit: int = 10,
) -> List[str]:
    """
    获取用于训练任务生成的用户反馈摘要

    供 skill_generator._generate_ai_training_task() 调用
    """
    feedbacks = get_feedback_list(limit=50)
    suggestions = []

    for f in feedbacks:
        if f.get("rating", 5) <= 3:
            comment = f.get("comment", "")
            tags = f.get("tags", [])
            if comment:
                suggestions.append(
                    f"用户反馈(评分{f['rating']}): {comment}"
                )
            if tags:
                suggestions.append(
                    f"用户关注维度: {', '.join(tags)}"
                )
        if len(suggestions) >= limit:
            break

    return suggestions

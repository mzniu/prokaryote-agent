"""Agent 测试路由 - 求解 + 反馈 + 历史"""

import logging
from typing import Optional, List
from fastapi import APIRouter
from pydantic import BaseModel, Field

from web.services.agent_service import (
    solve,
    get_interactions,
    get_interaction,
    get_available_skills_info,
)
from web.services.feedback_service import (
    submit_feedback,
    get_feedback_list,
    get_feedback_stats,
    get_strategy,
)

router = APIRouter()
logger = logging.getLogger(__name__)


# ==================== 请求模型 ====================

class SolveRequest(BaseModel):
    query: str = Field(..., min_length=1, description="用户问题")
    mode: str = Field("auto", description="auto / manual")
    skill_id: Optional[str] = Field(None, description="手动模式技能ID")
    use_knowledge_first: bool = Field(True, description="优先使用知识库")
    allow_web: bool = Field(False, description="允许联网搜索")


class FeedbackRequest(BaseModel):
    interaction_id: str = Field(..., description="交互ID")
    rating: int = Field(..., ge=1, le=5, description="满意度 1-5")
    resolved: bool = Field(..., description="是否解决问题")
    tags: List[str] = Field(default_factory=list,
                            description="标签")
    comment: str = Field("", description="文本建议")


# ==================== 求解 ====================

@router.post("/solve")
async def agent_solve(req: SolveRequest):
    """Agent 求解问题"""
    logger.info("Agent求解请求: %s (模式: %s)", req.query[:50], req.mode)
    result = solve(
        query=req.query,
        mode=req.mode,
        skill_id=req.skill_id,
        use_knowledge_first=req.use_knowledge_first,
        allow_web=req.allow_web,
    )
    return result


# ==================== 反馈 ====================

@router.post("/feedback")
async def agent_feedback(req: FeedbackRequest):
    """提交用户反馈"""
    return submit_feedback(
        interaction_id=req.interaction_id,
        rating=req.rating,
        resolved=req.resolved,
        tags=req.tags,
        comment=req.comment,
    )


@router.get("/feedback/list")
async def list_feedback(limit: int = 50):
    """获取反馈列表"""
    return get_feedback_list(limit=limit)


@router.get("/feedback/stats")
async def feedback_stats():
    """获取反馈统计"""
    return get_feedback_stats()


# ==================== 交互记录 ====================

@router.get("/interactions")
async def list_interactions(limit: int = 20):
    """获取交互记录"""
    return get_interactions(limit=limit)


@router.get("/interactions/{interaction_id}")
async def get_interaction_detail(interaction_id: str):
    """获取交互详情"""
    record = get_interaction(interaction_id)
    if record:
        return record
    return {"error": "未找到该交互记录"}


# ==================== 技能 & 策略 ====================

@router.get("/skills")
async def available_skills():
    """获取可用技能列表"""
    return get_available_skills_info()


@router.get("/strategy")
async def evolution_strategy():
    """获取当前进化策略"""
    return get_strategy()

"""进化目标路由"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from web.services.goal_service import (
    get_all_goals, get_goal_stats, update_goal_status,
    create_goal, delete_goal,
)

router = APIRouter()


class GoalCreate(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    acceptance_criteria: List[str] = []


class GoalStatusUpdate(BaseModel):
    status: str


@router.get("")
async def list_goals():
    """获取所有进化目标"""
    return {
        'goals': get_all_goals(),
        'stats': get_goal_stats(),
    }


@router.post("")
async def add_goal(body: GoalCreate):
    """创建新目标"""
    return create_goal(
        title=body.title,
        description=body.description,
        priority=body.priority,
        acceptance_criteria=body.acceptance_criteria,
    )


@router.put("/{goal_id}/status")
async def change_goal_status(goal_id: str, body: GoalStatusUpdate):
    """更新目标状态"""
    return update_goal_status(goal_id, body.status)


@router.delete("/{goal_id}")
async def remove_goal(goal_id: str):
    """删除目标"""
    return delete_goal(goal_id)

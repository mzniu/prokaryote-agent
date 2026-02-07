"""技能树路由"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Optional, List
from web.services.tree_service import (
    get_general_tree, get_domain_tree, get_tree_stats,
    get_skill_registry, update_skill_priority, unlock_skill,
    add_custom_skill, reload_skill, reload_all_skills,
)

router = APIRouter()


class PriorityUpdate(BaseModel):
    priority: float


class UnlockRequest(BaseModel):
    pass  # 无需参数


class NewSkill(BaseModel):
    id: str
    name: str
    category: str = "knowledge_acquisition"
    tier: str = "basic"
    max_level: int = 20
    unlocked: bool = False
    prerequisites: List[str] = []
    description: str = ""


@router.get("/general")
async def general_tree():
    """获取通用技能树"""
    return get_general_tree()


@router.get("/domain")
async def domain_tree():
    """获取专业技能树"""
    return get_domain_tree()


@router.get("/stats")
async def tree_stats():
    """获取双树统计"""
    return get_tree_stats()


@router.get("/registry")
async def skill_registry():
    """获取已学技能注册表"""
    return get_skill_registry()


@router.put("/{tree_type}/skills/{skill_id}/priority")
async def set_skill_priority(tree_type: str, skill_id: str,
                             body: PriorityUpdate):
    """设置技能优先级"""
    return update_skill_priority(tree_type, skill_id, body.priority)


@router.put("/{tree_type}/skills/{skill_id}/unlock")
async def force_unlock_skill(tree_type: str, skill_id: str):
    """手动解锁技能"""
    return unlock_skill(tree_type, skill_id)


@router.post("/{tree_type}/skills")
async def create_skill(tree_type: str, skill: NewSkill):
    """添加自定义技能"""
    return add_custom_skill(tree_type, skill.model_dump())


@router.post("/skills/{skill_id}/reload")
async def reload_single_skill(skill_id: str):
    """热重载指定技能（不重启服务器）"""
    return reload_skill(skill_id)


@router.post("/skills/reload-all")
async def reload_all():
    """热重载所有已注册技能"""
    return reload_all_skills()

"""系统状态路由"""

from fastapi import APIRouter
from web.services.evolution_service import get_system_status
from web.services.tree_service import get_tree_stats

router = APIRouter()


@router.get("/status")
async def system_status():
    """获取系统运行状态"""
    status = get_system_status()
    stats = get_tree_stats()
    return {
        'system': status,
        'evolution': stats,
    }


@router.get("/stats")
async def evolution_stats():
    """获取进化统计"""
    return get_tree_stats()

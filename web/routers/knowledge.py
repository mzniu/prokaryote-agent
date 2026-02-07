"""知识库路由"""

from fastapi import APIRouter, Query
from typing import Optional
from web.services.evolution_service import (
    get_knowledge_list, get_knowledge_detail,
)

router = APIRouter()


@router.get("")
async def list_knowledge(
    domain: Optional[str] = Query(None, description="按领域筛选"),
    q: Optional[str] = Query(None, description="搜索关键词"),
):
    """获取知识列表"""
    return {
        'items': get_knowledge_list(domain=domain, query=q),
    }


@router.get("/{knowledge_id}")
async def knowledge_detail(knowledge_id: str):
    """获取知识详情"""
    return get_knowledge_detail(knowledge_id)

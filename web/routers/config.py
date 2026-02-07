"""配置管理路由"""

from fastapi import APIRouter
from pydantic import BaseModel
from typing import Dict, Any
from web.services.evolution_service import (
    get_daemon_config, update_daemon_config,
)

router = APIRouter()


class ConfigUpdate(BaseModel):
    updates: Dict[str, Any]


@router.get("")
async def read_config():
    """读取守护进程配置"""
    return get_daemon_config()


@router.put("")
async def write_config(body: ConfigUpdate):
    """更新配置"""
    return update_daemon_config(body.updates)

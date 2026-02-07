"""日志路由 - REST + WebSocket"""

import asyncio
import aiofiles
from pathlib import Path
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from typing import Optional
from web.services.evolution_service import get_evolution_logs

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


@router.get("")
async def read_logs(
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
):
    """获取历史日志"""
    return get_evolution_logs(limit=limit, offset=offset)


@router.websocket("/ws")
async def websocket_logs(ws: WebSocket):
    """WebSocket 实时日志推送"""
    await ws.accept()

    log_file = PROJECT_ROOT / "prokaryote_agent" / "log" / "daemon.log"

    try:
        # 先读取文件当前大小
        if log_file.exists():
            pos = log_file.stat().st_size
        else:
            pos = 0

        while True:
            await asyncio.sleep(1)  # 每秒检查

            if not log_file.exists():
                continue

            current_size = log_file.stat().st_size
            if current_size > pos:
                async with aiofiles.open(log_file, 'r',
                                         encoding='utf-8') as f:
                    await f.seek(pos)
                    new_content = await f.read()
                    pos = current_size

                    for line in new_content.strip().split('\n'):
                        if line.strip():
                            await ws.send_json({
                                'type': 'log',
                                'data': line.strip()
                            })
            elif current_size < pos:
                # 日志文件被轮转
                pos = 0

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.close()
        except Exception:
            pass

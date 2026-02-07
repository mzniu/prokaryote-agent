"""
原智 Web 控制台 - FastAPI 后端入口

提供 REST API + WebSocket 实时日志推送
生产模式下同时托管 Vue 前端静态文件
"""

import sys
import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

# 确保项目根目录在 sys.path 中
PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from web.routers import status, trees, goals, config, evolve, knowledge, logs  # noqa: E402


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期"""
    print("🌐 原智 Web 控制台启动中...")
    yield
    print("🌐 原智 Web 控制台已关闭")


app = FastAPI(
    title="原智控制台",
    description="prokaryote-agent Web Console API",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS - 开发模式允许前端 dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(status.router, prefix="/api", tags=["系统状态"])
app.include_router(trees.router, prefix="/api/trees", tags=["技能树"])
app.include_router(goals.router, prefix="/api/goals", tags=["进化目标"])
app.include_router(config.router, prefix="/api/config", tags=["配置管理"])
app.include_router(evolve.router, prefix="/api/evolve", tags=["进化控制"])
app.include_router(knowledge.router, prefix="/api/knowledge", tags=["知识库"])
app.include_router(logs.router, prefix="/api/logs", tags=["日志"])

# 生产模式：托管前端静态文件
DIST_DIR = Path(__file__).parent / "frontend" / "dist"
if DIST_DIR.exists():
    app.mount("/", StaticFiles(directory=str(DIST_DIR), html=True), name="frontend")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "web.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        reload_dirs=[str(PROJECT_ROOT / "web")],
    )

"""进化控制路由"""

import logging
import threading
from datetime import datetime
from pathlib import Path
from fastapi import APIRouter

router = APIRouter()

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
LOG_FILE = PROJECT_ROOT / "prokaryote_agent" / "log" / "prokaryote.log"

# 简单的进化状态管理
_evolution_thread = None
_evolution_running = False
_evolution_agent = None
_evolution_started_at = None


def _setup_file_logging():
    """为进化线程配置文件日志，使 WebSocket 能读取"""
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    root_logger = logging.getLogger()
    # 避免重复添加
    for h in root_logger.handlers[:]:
        if isinstance(h, logging.FileHandler) and \
                h.baseFilename == str(LOG_FILE.resolve()):
            return
    fh = logging.FileHandler(str(LOG_FILE), encoding='utf-8')
    fh.setFormatter(logging.Formatter(
        '[%(asctime)s] %(message)s', datefmt='%H:%M:%S'))
    root_logger.addHandler(fh)


@router.post("/trigger")
async def trigger_evolution():
    """手动触发一次进化"""
    try:
        _setup_file_logging()
        from simple_agent import SimpleEvolutionAgent
        from prokaryote_agent.api import stop_prokaryote
        agent = SimpleEvolutionAgent(interval=0)
        agent.initialize()
        # 运行单次进化循环
        result = agent._evolution_cycle()
        # 释放核心系统状态，允许下次重新初始化
        try:
            stop_prokaryote()
        except Exception:
            pass
        return {'success': True, 'message': '已触发一次进化',
                'result': str(result)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@router.post("/start")
async def start_evolution():
    """启动自动进化"""
    global _evolution_thread, _evolution_running, _evolution_agent
    global _evolution_started_at

    if _evolution_running:
        return {'success': False, 'message': '进化已在运行中'}

    def run_evolution():
        global _evolution_running, _evolution_agent
        try:
            _setup_file_logging()
            from simple_agent import SimpleEvolutionAgent
            agent = SimpleEvolutionAgent(interval=60)
            _evolution_agent = agent
            _evolution_running = True
            agent.run()
        except Exception as e:
            logging.getLogger(__name__).error(f"进化线程异常: {e}")
        finally:
            _evolution_running = False
            _evolution_agent = None

    _evolution_started_at = datetime.now().isoformat()
    _evolution_thread = threading.Thread(target=run_evolution, daemon=True)
    _evolution_thread.start()

    return {'success': True, 'message': '自动进化已启动'}


@router.post("/stop")
async def stop_evolution():
    """停止自动进化"""
    global _evolution_running, _evolution_agent
    if _evolution_agent:
        _evolution_agent.running = False
    _evolution_running = False

    # 确保核心系统状态重置，允许下次重新初始化
    try:
        from prokaryote_agent.api import stop_prokaryote
        stop_prokaryote()
    except Exception:
        pass

    return {'success': True, 'message': '已发送停止信号'}


@router.get("/running")
async def evolution_status():
    """查询进化运行状态"""
    return {'running': _evolution_running}

"""进化控制路由"""

import asyncio
import threading
from fastapi import APIRouter

router = APIRouter()

# 简单的进化状态管理
_evolution_thread = None
_evolution_running = False


@router.post("/trigger")
async def trigger_evolution():
    """手动触发一次进化"""
    try:
        from simple_agent import SimpleEvolutionAgent
        agent = SimpleEvolutionAgent(interval=0)
        agent.initialize()
        # 运行单次进化循环
        result = agent._evolution_cycle()
        return {'success': True, 'message': '已触发一次进化', 'result': str(result)}
    except Exception as e:
        return {'success': False, 'error': str(e)}


@router.post("/start")
async def start_evolution():
    """启动自动进化"""
    global _evolution_thread, _evolution_running

    if _evolution_running:
        return {'success': False, 'message': '进化已在运行中'}

    def run_evolution():
        global _evolution_running
        try:
            from simple_agent import SimpleEvolutionAgent
            agent = SimpleEvolutionAgent(interval=60)
            agent.initialize()
            _evolution_running = True
            agent.run()
        except Exception as e:
            print(f"进化线程异常: {e}")
        finally:
            _evolution_running = False

    _evolution_thread = threading.Thread(target=run_evolution, daemon=True)
    _evolution_thread.start()

    return {'success': True, 'message': '自动进化已启动'}


@router.post("/stop")
async def stop_evolution():
    """停止自动进化"""
    global _evolution_running
    _evolution_running = False
    return {'success': True, 'message': '已发送停止信号'}


@router.get("/running")
async def evolution_status():
    """查询进化运行状态"""
    return {'running': _evolution_running}

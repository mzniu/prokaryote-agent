"""
Prokaryote Agent 核心API
对外提供的极简接口: init_prokaryote, start_prokaryote, stop_prokaryote, query_prokaryote_state
"""
import logging
from typing import Dict, Any, Optional
from threading import Lock

from .core.storage import StorageManager
from .core.init_module import ProkaryoteInit
from .core.monitor_module import ProkaryoteMonitor, Anomaly
from .core.repair_module import ProkaryoteRepair

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

_agent_lock = Lock()
_agent_state: Dict[str, Any] = {
    "initialized": False, "running": False,
    "storage": None, "init_module": None, "monitor": None, "repair": None
}


def _on_anomaly(anomaly: Anomaly) -> None:
    repair = _agent_state.get("repair")
    if repair:
        repair.handle_anomaly(anomaly)


def _on_emergency_stop(reason: str) -> None:
    with _agent_lock:
        _agent_state["running"] = False
        monitor = _agent_state.get("monitor")
        if monitor:
            monitor.stop()


def init_prokaryote(config_path: Optional[str] = None) -> Dict[str, Any]:
    """初始化 Prokaryote Agent"""
    with _agent_lock:
        if _agent_state["initialized"]:
            return {"success": False, "msg": "Agent已初始化，如需重新初始化请先调用stop_prokaryote", "data": {}}
        
        try:
            storage = StorageManager()
            _agent_state["storage"] = storage
            
            init_module = ProkaryoteInit(config_path)
            result = init_module.init_core()
            if not result["success"]:
                return result
            
            _agent_state["init_module"] = init_module
            
            monitor = ProkaryoteMonitor(storage)
            config = result["data"].get("config", {})
            if config:
                monitor.set_config(config)
            _agent_state["monitor"] = monitor
            
            repair = ProkaryoteRepair(storage, monitor)
            repair.set_emergency_callback(_on_emergency_stop)
            _agent_state["repair"] = repair
            
            monitor.register_callback(_on_anomaly)
            _agent_state["initialized"] = True
            
            return {"success": True, "msg": "Agent初始化成功", "data": result["data"]}
        except Exception as e:
            return {"success": False, "msg": f"初始化异常: {str(e)}", "data": {}}


def start_prokaryote() -> Dict[str, Any]:
    """启动 Prokaryote Agent"""
    with _agent_lock:
        if not _agent_state["initialized"]:
            return {"success": False, "msg": "Agent未初始化，请先调用init_prokaryote"}
        if _agent_state["running"]:
            return {"success": False, "msg": "Agent已在运行中"}
        
        repair = _agent_state.get("repair")
        if repair and repair.emergency_stopped:
            return {"success": False, "msg": "Agent处于紧急停止状态，请检查并处理后手动重置"}
        
        try:
            monitor = _agent_state["monitor"]
            result = monitor.start()
            if result["success"]:
                _agent_state["running"] = True
                storage = _agent_state["storage"]
                if storage:
                    storage.write_log("INFO", "API", "Agent启动")
            return result
        except Exception as e:
            return {"success": False, "msg": f"启动异常: {str(e)}"}


def stop_prokaryote() -> Dict[str, Any]:
    """停止 Prokaryote Agent"""
    with _agent_lock:
        if not _agent_state["initialized"]:
            return {"success": False, "msg": "Agent未初始化"}
        
        try:
            result = {"success": True, "msg": "Agent已停止"}
            monitor = _agent_state.get("monitor")
            if monitor and _agent_state["running"]:
                stop_result = monitor.stop()
                if not stop_result["success"]:
                    result = stop_result
            
            storage = _agent_state.get("storage")
            if storage:
                storage.write_log("INFO", "API", "Agent停止")
            
            _agent_state.update({"initialized": False, "running": False, "storage": None, 
                               "init_module": None, "monitor": None, "repair": None})
            return result
        except Exception as e:
            return {"success": False, "msg": f"停止异常: {str(e)}"}


def query_prokaryote_state() -> Dict[str, Any]:
    """查询 Prokaryote Agent 状态"""
    with _agent_lock:
        if not _agent_state["initialized"]:
            return {"success": True, "msg": "Agent未初始化", 
                   "data": {"initialized": False, "running": False, "monitor": {}, "repair": {}, "base_state": {}}}
        
        try:
            data = {"initialized": _agent_state["initialized"], "running": _agent_state["running"]}
            
            monitor = _agent_state.get("monitor")
            data["monitor"] = monitor.get_status() if monitor else {}
            
            repair = _agent_state.get("repair")
            data["repair"] = repair.get_status() if repair else {}
            
            init_module = _agent_state.get("init_module")
            data["base_state"] = init_module.get_base_state() if init_module else {}
            
            return {"success": True, "msg": "状态查询成功", "data": data}
        except Exception as e:
            return {"success": False, "msg": f"查询异常: {str(e)}", "data": {}}


# V0.2 能力扩展API (预留)
def generate_capability(name: str, description: str, **kwargs) -> Dict[str, Any]:
    """生成新能力 (V0.2)"""
    return {"success": False, "msg": "V0.2功能，尚未实现", "capability_id": ""}


def manage_capabilities(action: str, capability_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """管理能力 (V0.2)"""
    return {"success": False, "msg": "V0.2功能，尚未实现", "data": {}}


def invoke_capability(capability_id: str, **kwargs) -> Dict[str, Any]:
    """调用能力 (V0.2)"""
    return {"success": False, "msg": "V0.2功能，尚未实现", "result": None}

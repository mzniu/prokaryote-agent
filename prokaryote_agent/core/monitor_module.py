"""
ProkaryoteMonitor - 监控模块
周期性监控进程状态、资源使用、文件权限、磁盘空间，发出异常事件
"""
import threading
import time
import logging
from typing import Dict, Any, List, Callable, Optional
from datetime import datetime
from enum import Enum

from .storage import StorageManager


class AnomalyLevel(Enum):
    """异常级别"""
    INFO = "INFO"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"


class Anomaly:
    """异常事件数据结构"""
    
    def __init__(self, level: AnomalyLevel, category: str, message: str, details: Dict[str, Any] = None):
        self.level = level
        self.category = category
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "level": self.level.value,
            "category": self.category,
            "message": self.message,
            "details": self.details,
            "timestamp": self.timestamp
        }


class ProkaryoteMonitor:
    """监控模块 - 周期性健康检查"""
    
    DEFAULT_INTERVAL = 1.0
    
    def __init__(self, storage: Optional[StorageManager] = None):
        self.storage = storage or StorageManager()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.interval = self.DEFAULT_INTERVAL
        self.anomaly_callbacks: List[Callable[[Anomaly], None]] = []
        self.config = {"disk_threshold_mb": 100, "check_permissions": True, "check_disk": True}
        self.last_check_time: Optional[str] = None
        self.check_count = 0
        self.anomaly_count = 0
        self.logger = logging.getLogger("ProkaryoteMonitor")
    
    def set_config(self, config: Dict[str, Any]) -> None:
        self.config.update(config)
        if "monitor_interval" in config:
            self.interval = config["monitor_interval"]
    
    def register_callback(self, callback: Callable[[Anomaly], None]) -> None:
        if callback not in self.anomaly_callbacks:
            self.anomaly_callbacks.append(callback)
    
    def _emit_anomaly(self, anomaly: Anomaly) -> None:
        self.anomaly_count += 1
        self.storage.write_log(anomaly.level.value, anomaly.category, anomaly.message)
        for callback in self.anomaly_callbacks:
            try:
                callback(anomaly)
            except Exception as e:
                self.logger.error(f"异常回调执行失败: {e}")
    
    def check_disk_space(self) -> Optional[Anomaly]:
        if not self.config.get("check_disk", True):
            return None
        result = self.storage.check_disk_space()
        if not result["success"]:
            return Anomaly(AnomalyLevel.WARNING, "DISK", result["msg"], {"free_mb": result.get("free_mb", 0)})
        return None
    
    def check_permissions(self) -> Optional[Anomaly]:
        if not self.config.get("check_permissions", True):
            return None
        result = self.storage.check_permissions()
        if not result["success"]:
            return Anomaly(AnomalyLevel.CRITICAL, "PERMISSION", result["msg"], result)
        return None
    
    def check_config_integrity(self) -> Optional[Anomaly]:
        result = self.storage.load_config()
        if not result["success"]:
            return Anomaly(AnomalyLevel.CRITICAL, "CONFIG", f"配置文件异常: {result['msg']}", result)
        return None
    
    def run_checks(self) -> List[Anomaly]:
        anomalies = []
        for check in [self.check_disk_space, self.check_permissions, self.check_config_integrity]:
            anomaly = check()
            if anomaly:
                anomalies.append(anomaly)
        self.last_check_time = datetime.now().isoformat()
        self.check_count += 1
        return anomalies
    
    def _monitor_loop(self) -> None:
        self.logger.info(f"监控循环启动, 间隔: {self.interval}秒")
        while self.running:
            try:
                anomalies = self.run_checks()
                for anomaly in anomalies:
                    self._emit_anomaly(anomaly)
            except Exception as e:
                self.logger.error(f"监控循环异常: {e}", exc_info=True)
            time.sleep(self.interval)
    
    def start(self) -> Dict[str, Any]:
        if self.running:
            return {"success": False, "msg": "监控已在运行中"}
        self.running = True
        self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.thread.start()
        self.storage.write_log("INFO", "MONITOR", "监控模块启动")
        return {"success": True, "msg": "监控已启动"}
    
    def stop(self) -> Dict[str, Any]:
        if not self.running:
            return {"success": False, "msg": "监控未在运行"}
        self.running = False
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=2.0)
        self.thread = None
        self.storage.write_log("INFO", "MONITOR", "监控模块停止")
        return {"success": True, "msg": "监控已停止"}
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "running": self.running,
            "interval": self.interval,
            "last_check_time": self.last_check_time,
            "check_count": self.check_count,
            "anomaly_count": self.anomaly_count,
            "config": self.config.copy()
        }

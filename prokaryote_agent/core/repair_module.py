"""
ProkaryoteRepair - 修复模块
读取本地备份、恢复配置或代码、调用monitor验证、3次失败触发紧急停止
"""
import logging
from typing import Dict, Any, Callable, Optional
from datetime import datetime

from .storage import StorageManager
from .monitor_module import ProkaryoteMonitor, Anomaly, AnomalyLevel


class ProkaryoteRepair:
    """修复模块 - 自动修复与恢复"""
    
    MAX_REPAIR_ATTEMPTS = 3
    
    def __init__(self, storage: Optional[StorageManager] = None, 
                 monitor: Optional[ProkaryoteMonitor] = None):
        self.storage = storage or StorageManager()
        self.monitor = monitor
        self.repair_count = 0
        self.last_repair_time: Optional[str] = None
        self.consecutive_failures = 0
        self.emergency_stopped = False
        self.emergency_callback: Optional[Callable[[str], None]] = None
        self.logger = logging.getLogger("ProkaryoteRepair")
    
    def set_emergency_callback(self, callback: Callable[[str], None]) -> None:
        self.emergency_callback = callback
    
    def restore_config(self) -> Dict[str, Any]:
        """从备份恢复配置文件"""
        try:
            backup_result = self.storage.load_backup_config()
            if not backup_result["success"]:
                return {"success": False, "msg": f"无可用备份: {backup_result['msg']}"}
            
            save_result = self.storage.save_config(backup_result["config"])
            if not save_result["success"]:
                return {"success": False, "msg": f"恢复配置失败: {save_result['msg']}"}
            
            self.storage.write_log("INFO", "REPAIR", "从备份恢复配置成功")
            return {"success": True, "msg": "配置恢复成功"}
        except Exception as e:
            return {"success": False, "msg": f"恢复配置异常: {str(e)}"}
    
    def verify_repair(self) -> Dict[str, Any]:
        """验证修复结果"""
        try:
            if self.monitor is None:
                config_result = self.storage.load_config()
                return {"success": config_result["success"], "msg": config_result["msg"], "anomalies": []}
            
            anomalies = self.monitor.run_checks()
            critical = [a for a in anomalies if a.level == AnomalyLevel.CRITICAL]
            
            if critical:
                return {"success": False, "msg": f"验证发现{len(critical)}个严重异常", 
                       "anomalies": [a.to_dict() for a in critical]}
            return {"success": True, "msg": "修复验证通过", "anomalies": [a.to_dict() for a in anomalies]}
        except Exception as e:
            return {"success": False, "msg": f"验证修复异常: {str(e)}", "anomalies": []}
    
    def trigger_emergency_stop(self, reason: str) -> None:
        """触发紧急停止"""
        self.emergency_stopped = True
        self.logger.critical(f"紧急停止: {reason}")
        self.storage.write_log("CRITICAL", "REPAIR", f"紧急停止: {reason}")
        if self.emergency_callback:
            try:
                self.emergency_callback(reason)
            except Exception as e:
                self.logger.error(f"紧急停止回调执行失败: {e}")
    
    def perform_repair(self, anomaly: Optional[Anomaly] = None) -> Dict[str, Any]:
        """执行修复流程"""
        if self.emergency_stopped:
            return {"success": False, "msg": "系统已紧急停止,无法执行修复"}
        
        self.repair_count += 1
        self.last_repair_time = datetime.now().isoformat()
        
        # 尝试恢复配置
        restore_result = self.restore_config()
        if not restore_result["success"]:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.MAX_REPAIR_ATTEMPTS:
                self.trigger_emergency_stop(f"连续{self.MAX_REPAIR_ATTEMPTS}次修复失败")
                return {"success": False, "msg": f"修复失败且触发紧急停止: {restore_result['msg']}"}
            return {"success": False, "msg": f"修复失败({self.consecutive_failures}/{self.MAX_REPAIR_ATTEMPTS}): {restore_result['msg']}"}
        
        # 验证修复
        verify_result = self.verify_repair()
        if not verify_result["success"]:
            self.consecutive_failures += 1
            if self.consecutive_failures >= self.MAX_REPAIR_ATTEMPTS:
                self.trigger_emergency_stop(f"连续{self.MAX_REPAIR_ATTEMPTS}次修复验证失败")
                return {"success": False, "msg": f"修复验证失败且触发紧急停止: {verify_result['msg']}"}
            return {"success": False, "msg": f"修复验证失败({self.consecutive_failures}/{self.MAX_REPAIR_ATTEMPTS}): {verify_result['msg']}"}
        
        self.consecutive_failures = 0
        self.storage.write_log("INFO", "REPAIR", "修复完成并验证通过")
        return {"success": True, "msg": "修复成功"}
    
    def handle_anomaly(self, anomaly: Anomaly) -> Dict[str, Any]:
        """处理异常事件"""
        if anomaly.level != AnomalyLevel.CRITICAL:
            return {"success": True, "msg": f"非严重异常,仅记录: [{anomaly.category}] {anomaly.message}"}
        return self.perform_repair(anomaly)
    
    def get_status(self) -> Dict[str, Any]:
        return {
            "repair_count": self.repair_count,
            "last_repair_time": self.last_repair_time,
            "consecutive_failures": self.consecutive_failures,
            "emergency_stopped": self.emergency_stopped,
            "max_attempts": self.MAX_REPAIR_ATTEMPTS
        }
    
    def reset(self) -> Dict[str, Any]:
        self.repair_count = 0
        self.last_repair_time = None
        self.consecutive_failures = 0
        self.emergency_stopped = False
        self.storage.write_log("INFO", "REPAIR", "修复模块状态已重置")
        return {"success": True, "msg": "修复模块已重置"}

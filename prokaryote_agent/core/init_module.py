"""
ProkaryoteInit - 初始化模块
内核启动入口，负责初始化配置、校验目录、加载备份、设置基准状态
"""
import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .storage import StorageManager


class ProkaryoteInit:
    """初始化模块 - 内核启动入口"""
    
    def __init__(self, config_path: Optional[str] = None):
        """
        初始化模块
        
        Args:
            config_path: 可选，自定义配置文件路径
        """
        self.config_path = config_path
        self.storage = StorageManager()
        self.base_state = {}
        self.initialized = False
        
        self.logger = logging.getLogger("ProkaryoteInit")
        
    def check_storage_dir(self) -> Dict[str, Any]:
        """校验本地存储目录"""
        return self.storage.ensure_directories()
    
    def load_config(self) -> Dict[str, Any]:
        """加载核心配置"""
        result = self.storage.load_config()
        if result["success"]:
            self.base_state["config"] = result["config"]
        return result
    
    def load_backup(self) -> Dict[str, Any]:
        """加载备份数据"""
        try:
            backup_result = self.storage.load_backup_config()
            self.base_state["backup_available"] = backup_result["success"]
            if backup_result["success"]:
                self.base_state["backup_config"] = backup_result["config"]
            
            return {
                "success": True,
                "msg": "备份数据检查完成",
                "backup_available": self.base_state.get("backup_available", False)
            }
        except Exception as e:
            self.logger.error(f"加载备份失败: {e}")
            return {"success": False, "msg": f"加载备份失败: {str(e)}"}
    
    def init_core(self) -> Dict[str, Any]:
        """
        执行完整初始化流程
        流程: 校验目录 → 加载配置 → 加载备份 → 设置基准状态
        """
        try:
            self.logger.info("开始初始化内核...")
            
            # 1. 校验存储目录
            dir_result = self.check_storage_dir()
            if not dir_result["success"]:
                return {"success": False, "msg": f"存储目录校验失败: {dir_result['msg']}", "data": {}}
            
            # 2. 检查文件权限
            perm_result = self.storage.check_permissions()
            
            # 3. 检查磁盘空间
            disk_result = self.storage.check_disk_space()
            
            # 4. 加载配置
            config_result = self.load_config()
            if not config_result["success"]:
                return {"success": False, "msg": f"配置加载失败: {config_result['msg']}", "data": {}}
            
            # 5. 加载备份
            self.load_backup()
            
            # 6. 设置基准状态
            self.base_state.update({
                "initialized": True,
                "initialized_at": datetime.now().isoformat(),
                "status": "initialized",
                "disk_free_mb": disk_result.get("free_mb", 0),
                "permissions_ok": perm_result["success"]
            })
            
            self.initialized = True
            self.storage.write_log("INFO", "INIT", "内核初始化成功")
            
            return {"success": True, "msg": "内核初始化成功", "data": self.base_state}
            
        except Exception as e:
            error_msg = f"初始化异常: {str(e)}"
            self.logger.error(error_msg, exc_info=True)
            return {"success": False, "msg": error_msg, "data": {}}
    
    def get_base_state(self) -> Dict[str, Any]:
        """获取基准状态"""
        return self.base_state.copy()

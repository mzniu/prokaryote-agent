"""
StorageManager - 本地存储管理
负责管理本地文件系统存储：目录创建、配置读写、权限检查、磁盘空间检查、日志写入
"""
import os
import json
import shutil
import logging
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path


class StorageManager:
    """本地存储管理器"""
    
    DEFAULT_ROOT = "./prokaryote_agent"
    
    def __init__(self, root_path: Optional[str] = None):
        """
        初始化存储管理器
        
        Args:
            root_path: 存储根目录，默认为 ./prokaryote_agent
        """
        self.root_path = Path(root_path or self.DEFAULT_ROOT).resolve()
        self.config_dir = self.root_path / "config"
        self.backup_dir = self.root_path / "backup"
        self.log_dir = self.root_path / "log"
        
        self.config_file = self.config_dir / "config.json"
        self.backup_config_file = self.config_dir / "config_backup.json"
        
        self.logger = logging.getLogger("StorageManager")
    
    def ensure_directories(self) -> Dict[str, Any]:
        """
        确保所有必要目录存在
        
        Returns:
            dict: {"success": bool, "msg": str, "created": list}
        """
        created = []
        try:
            for dir_path in [self.root_path, self.config_dir, self.backup_dir, self.log_dir]:
                if not dir_path.exists():
                    dir_path.mkdir(parents=True, exist_ok=True)
                    created.append(str(dir_path))
                    self.logger.info(f"创建目录: {dir_path}")
            
            return {
                "success": True,
                "msg": f"目录检查完成，新建{len(created)}个目录",
                "created": created
            }
        except Exception as e:
            self.logger.error(f"创建目录失败: {e}")
            return {
                "success": False,
                "msg": f"创建目录失败: {str(e)}",
                "created": created
            }
    
    def load_config(self) -> Dict[str, Any]:
        """
        加载配置文件
        
        Returns:
            dict: {"success": bool, "msg": str, "config": dict}
        """
        try:
            if not self.config_file.exists():
                # 创建默认配置
                default_config = self._get_default_config()
                self.save_config(default_config)
                return {
                    "success": True,
                    "msg": "使用默认配置",
                    "config": default_config
                }
            
            with open(self.config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return {
                "success": True,
                "msg": "配置加载成功",
                "config": config
            }
        except json.JSONDecodeError as e:
            self.logger.error(f"配置文件格式错误: {e}")
            return {
                "success": False,
                "msg": f"配置文件格式错误: {str(e)}",
                "config": {}
            }
        except Exception as e:
            self.logger.error(f"加载配置失败: {e}")
            return {
                "success": False,
                "msg": f"加载配置失败: {str(e)}",
                "config": {}
            }
    
    def save_config(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        保存配置文件
        
        Args:
            config: 配置字典
        
        Returns:
            dict: {"success": bool, "msg": str}
        """
        try:
            # 确保目录存在
            self.config_dir.mkdir(parents=True, exist_ok=True)
            
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            # 同时更新备份
            with open(self.backup_config_file, 'w', encoding='utf-8') as f:
                json.dump(config, f, indent=2, ensure_ascii=False)
            
            return {
                "success": True,
                "msg": "配置保存成功"
            }
        except Exception as e:
            self.logger.error(f"保存配置失败: {e}")
            return {
                "success": False,
                "msg": f"保存配置失败: {str(e)}"
            }
    
    def load_backup_config(self) -> Dict[str, Any]:
        """
        加载备份配置
        
        Returns:
            dict: {"success": bool, "msg": str, "config": dict}
        """
        try:
            if not self.backup_config_file.exists():
                return {
                    "success": False,
                    "msg": "备份配置不存在",
                    "config": {}
                }
            
            with open(self.backup_config_file, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            return {
                "success": True,
                "msg": "备份配置加载成功",
                "config": config
            }
        except Exception as e:
            self.logger.error(f"加载备份配置失败: {e}")
            return {
                "success": False,
                "msg": f"加载备份配置失败: {str(e)}",
                "config": {}
            }
    
    def check_permissions(self) -> Dict[str, Any]:
        """
        检查文件权限
        
        Returns:
            dict: {"success": bool, "msg": str, "readable": bool, "writable": bool}
        """
        try:
            # 检查根目录
            readable = os.access(self.root_path, os.R_OK) if self.root_path.exists() else True
            writable = os.access(self.root_path, os.W_OK) if self.root_path.exists() else True
            
            # 如果目录不存在，尝试创建测试
            if not self.root_path.exists():
                try:
                    self.root_path.mkdir(parents=True, exist_ok=True)
                    writable = True
                except:
                    writable = False
            
            if not readable or not writable:
                return {
                    "success": False,
                    "msg": f"权限不足: 读={readable}, 写={writable}",
                    "readable": readable,
                    "writable": writable
                }
            
            return {
                "success": True,
                "msg": "权限检查通过",
                "readable": readable,
                "writable": writable
            }
        except Exception as e:
            self.logger.error(f"权限检查失败: {e}")
            return {
                "success": False,
                "msg": f"权限检查失败: {str(e)}",
                "readable": False,
                "writable": False
            }
    
    def check_disk_space(self, min_mb: int = 100) -> Dict[str, Any]:
        """
        检查磁盘空间
        
        Args:
            min_mb: 最小可用空间(MB)
        
        Returns:
            dict: {"success": bool, "msg": str, "free_mb": int}
        """
        try:
            # 确保目录存在以检查磁盘空间
            check_path = self.root_path if self.root_path.exists() else Path.cwd()
            
            total, used, free = shutil.disk_usage(check_path)
            free_mb = free // (1024 * 1024)
            
            if free_mb < min_mb:
                return {
                    "success": False,
                    "msg": f"磁盘空间不足: {free_mb}MB < {min_mb}MB",
                    "free_mb": free_mb
                }
            
            return {
                "success": True,
                "msg": f"磁盘空间充足: {free_mb}MB",
                "free_mb": free_mb
            }
        except Exception as e:
            self.logger.error(f"磁盘空间检查失败: {e}")
            return {
                "success": False,
                "msg": f"磁盘空间检查失败: {str(e)}",
                "free_mb": 0
            }
    
    def write_log(self, level: str, module: str, message: str) -> Dict[str, Any]:
        """
        写入日志文件
        
        Args:
            level: 日志级别 (INFO, WARNING, ERROR, CRITICAL)
            module: 模块名称
            message: 日志消息
        
        Returns:
            dict: {"success": bool, "msg": str}
        """
        try:
            self.log_dir.mkdir(parents=True, exist_ok=True)
            
            log_file = self.log_dir / "prokaryote.log"
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            log_line = f"[{timestamp}] [{level}] [{module}] {message}\n"
            
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(log_line)
            
            return {
                "success": True,
                "msg": "日志写入成功"
            }
        except Exception as e:
            return {
                "success": False,
                "msg": f"日志写入失败: {str(e)}"
            }
    
    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            "version": "0.2.1",
            "monitor_interval": 1.0,
            "disk_threshold_mb": 100,
            "max_repair_attempts": 3,
            "log_retention_days": 7,
            "created_at": datetime.now().isoformat()
        }

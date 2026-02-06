# -*- coding: utf-8 -*-
"""
核心酶基类 (Core Enzyme Base)
============================

提供核心酶的基础设施：
- 不可变标记
- 完整性校验（防篡改）
- 版本管理
"""

import hashlib
import inspect
import logging
from abc import ABC, abstractmethod
from typing import Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class EnzymeSecurityError(Exception):
    """核心酶安全异常 - 检测到篡改或非法操作"""
    pass


class CoreEnzyme(ABC):
    """
    核心酶基类
    
    所有核心酶必须继承此类。提供以下保护机制：
    1. IS_IMMUTABLE 标记 - 声明不可被Agent修改
    2. 完整性校验 - 检测运行时篡改
    3. 版本追踪 - 记录人工更新历史
    
    ⚠️ 警告：此类及其子类只能由开发者（上帝视角）修改
    """
    
    # === 元数据（子类可覆盖） ===
    ENZYME_NAME: str = "CoreEnzyme"
    ENZYME_VERSION: str = "1.0.0"
    
    # === 保护标记（不可覆盖） ===
    IS_IMMUTABLE: bool = True       # 不可变标记
    REQUIRE_GODMODE: bool = True    # 修改需要上帝模式
    
    def __init__(self):
        """初始化核心酶，计算初始校验和"""
        self._creation_time = datetime.now()
        self._call_count = 0
        self._lock_checksum = self._compute_checksum()
        logger.debug(f"核心酶 {self.ENZYME_NAME} v{self.ENZYME_VERSION} 已初始化")
    
    def _compute_checksum(self) -> str:
        """
        计算核心酶代码的校验和
        
        通过对源代码计算SHA256，检测运行时篡改
        """
        try:
            source = inspect.getsource(self.__class__)
            return hashlib.sha256(source.encode('utf-8')).hexdigest()[:16]
        except (OSError, TypeError):
            # 无法获取源码时（如交互式环境），返回占位符
            return "no_source_check"
    
    def verify_integrity(self) -> bool:
        """
        验证核心酶完整性
        
        Returns:
            bool: True表示完整性正常，False表示可能被篡改
        """
        if self._lock_checksum == "no_source_check":
            return True  # 无法验证时跳过
        
        current = self._compute_checksum()
        is_valid = current == self._lock_checksum
        
        if not is_valid:
            logger.error(
                f"核心酶 {self.ENZYME_NAME} 完整性校验失败！"
                f"期望={self._lock_checksum}, 实际={current}"
            )
        
        return is_valid
    
    def __call__(self, *args, **kwargs) -> Any:
        """
        调用核心酶执行功能
        
        每次调用前会验证完整性
        """
        # 完整性检查
        if not self.verify_integrity():
            raise EnzymeSecurityError(
                f"核心酶 {self.ENZYME_NAME} 被篡改！需要上帝模式修复。"
            )
        
        # 记录调用
        self._call_count += 1
        logger.debug(f"核心酶 {self.ENZYME_NAME} 第{self._call_count}次调用")
        
        # 执行实际功能
        return self.execute(*args, **kwargs)
    
    @abstractmethod
    def execute(self, *args, **kwargs) -> Any:
        """
        执行核心酶功能（子类实现）
        
        这是核心酶的实际工作逻辑
        """
        raise NotImplementedError
    
    def get_stats(self) -> dict:
        """获取核心酶统计信息"""
        return {
            'name': self.ENZYME_NAME,
            'version': self.ENZYME_VERSION,
            'is_immutable': self.IS_IMMUTABLE,
            'call_count': self._call_count,
            'creation_time': self._creation_time.isoformat(),
            'checksum': self._lock_checksum[:8] + '...',
        }
    
    def __repr__(self) -> str:
        return f"<{self.ENZYME_NAME} v{self.ENZYME_VERSION} calls={self._call_count}>"

"""
Prokaryote Agent - 原核智能体

代际进化系统的核心API入口。
"""
__version__ = "0.2.1"

# 从 api.py 导入核心功能
from .api import (
    init_prokaryote,
    start_prokaryote,
    stop_prokaryote,
    query_prokaryote_state,
    generate_capability,
    manage_capabilities,
    invoke_capability
)

__all__ = [
    # V0.1 核心API
    'init_prokaryote',
    'start_prokaryote', 
    'stop_prokaryote',
    'query_prokaryote_state',
    # V0.2 能力扩展API
    'generate_capability',
    'manage_capabilities',
    'invoke_capability'
]


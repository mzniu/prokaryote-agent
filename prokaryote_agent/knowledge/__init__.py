"""
知识库模块 - Markdown 格式知识存储与检索

提供：
- 知识存储和搜索
- 智能搜索（本地优先 + 网络补充 + 自动固化）
- 知识统计
"""

from .knowledge_base import (
    MarkdownKnowledge, 
    Knowledge,
    get_knowledge_base,
    store_knowledge,
    search_knowledge,
    smart_search,
    get_knowledge_stats
)

__all__ = [
    'MarkdownKnowledge', 
    'Knowledge',
    'get_knowledge_base',
    'store_knowledge',
    'search_knowledge',
    'smart_search',
    'get_knowledge_stats'
]

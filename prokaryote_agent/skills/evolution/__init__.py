"""
技能进化模块

提供技能代码进化和自优化功能：
- SkillOptimizer: 分析训练失败原因，生成优化建议，AI自修复
- record_training_result: 记录训练结果，失败时触发分析
"""

from .skill_optimizer import (
    SkillOptimizer,
    get_skill_optimizer,
    record_training_result
)

__all__ = [
    'SkillOptimizer',
    'get_skill_optimizer',
    'record_training_result'
]

"""
技能训练评估模块

提供基于AI的通用技能训练评估能力，支持多维度评估和动态阈值。
"""

from .result import EvaluationResult
from .dimension_presets import DIMENSION_PRESETS, get_preset_dimensions
from .config_resolver import EvaluationConfigResolver
from .evaluator import TrainingEvaluator

__all__ = [
    'EvaluationResult',
    'DIMENSION_PRESETS',
    'get_preset_dimensions',
    'EvaluationConfigResolver',
    'TrainingEvaluator'
]

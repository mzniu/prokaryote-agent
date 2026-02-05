"""
技能库 - 存放Agent学习到的真实技能实现

技能结构：
- 每个技能是一个Python模块
- 技能元数据（版本、等级、描述）
- 技能执行接口

技能生命周期：
1. 学习 (learn) - 首次实现技能代码
2. 升级 (upgrade) - 优化或增强技能
3. 调用 (execute) - 使用技能完成任务
"""

from .skill_base import Skill, SkillMetadata, SkillLibrary
from .skill_executor import SkillExecutor
from .skill_generator import SkillGenerator

__all__ = ['Skill', 'SkillMetadata', 'SkillLibrary', 'SkillExecutor', 'SkillGenerator']

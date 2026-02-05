"""SkillNode - 技能节点定义"""
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Dict, Any

class SkillTier(Enum):
    """技能层级"""
    BASIC = 1  # 基础
    INTERMEDIATE = 2  # 中级
    ADVANCED = 3  # 高级
    EXPERT = 4  # 专家
    MASTER = 5  # 大师

class SkillCategory(Enum):
    """技能类别"""
    ANALYTICAL = "analytical"  # 分析型
    CREATIVE = "creative"  # 创造型
    TECHNICAL = "technical"  # 技术型
    COLLABORATIVE = "collaborative"  # 协作型
    PROBLEM_SOLVING = "problem_solving"
    CODE_GENERATION = "code_generation"
    DEBUGGING = "debugging"
    TESTING = "testing"
    REFACTORING = "refactoring"
    DOCUMENTATION = "documentation"
    ARCHITECTURE = "architecture"
    PERFORMANCE = "performance"

@dataclass
class SkillNode:
    """技能节点数据类"""
    id: str  # 主键，兼容skill_id
    name: str
    tier: SkillTier
    category: SkillCategory = SkillCategory.TECHNICAL  # 默认技术类
    description: str = ""
    level: int = 0  # 0-5
    proficiency: float = 0.0  # 0.0-1.0
    prerequisites: List[str] = field(default_factory=list)
    unlocked: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    @property
    def skill_id(self):
        """为兼容性提供skill_id别名"""
        return self.id
    
    def __post_init__(self):
        """验证数据"""
        # 确保枚举类型
        if isinstance(self.category, str):
            self.category = SkillCategory(self.category)
        if isinstance(self.tier, int):
            self.tier = SkillTier(self.tier)
        
        # 验证level范围
        if not (0 <= self.level <= 5):
            raise ValueError(f"Level must be 0-5, got {self.level}")
        
        # 验证proficiency范围
        if not (0.0 <= self.proficiency <= 1.0):
            raise ValueError(f"Proficiency must be 0.0-1.0, got {self.proficiency}")
    
    def to_dict(self):
        """转换为字典"""
        return {
            "id": self.id,
            "skill_id": self.id,  # 兼容性
            "name": self.name,
            "category": self.category.value,
            "tier": self.tier.value,
            "description": self.description,
            "level": self.level,
            "proficiency": self.proficiency,
            "prerequisites": self.prerequisites,
            "unlocked": self.unlocked,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data):
        """从字典创建"""
        # 兼容skill_id和id两种字段名
        skill_id = data.get("id") or data.get("skill_id")
        return cls(
            id=skill_id,
            name=data["name"],
            category=SkillCategory(data["category"]),
            tier=SkillTier(data["tier"]),
            description=data.get("description", ""),
            level=data.get("level", 0),
            proficiency=data.get("proficiency", 0.0),
            prerequisites=data.get("prerequisites", []),
            unlocked=data.get("unlocked", False),
            metadata=data.get("metadata", {})
        )

"""SkillTreeScorer - 技能树评分与专精识别"""
from collections import Counter
from typing import Dict, Optional, List, Tuple
from .skill_tree import SkillTree
from .skill_level_system import SkillLevelSystem

class SkillTreeScorer:
    def __init__(self, skill_tree: SkillTree, level_system: SkillLevelSystem):
        self.skill_tree = skill_tree
        self.level_system = level_system
    
    def calculate_tree_score(self) -> float:
        """计算技能树总分（0-100）"""
        if not self.skill_tree.skills:
            return 0.0
        
        unlocked_count = len(self.skill_tree.get_unlocked_skills())
        total_count = len(self.skill_tree.skills)
        
        # 解锁比例分（50分）
        unlock_ratio = unlocked_count / total_count
        unlock_score = unlock_ratio * 50
        
        # 战斗力分（50分）
        total_power = self.level_system.get_total_power()
        max_possible_power = len(self.skill_tree.skills) * 160  # 每个技能最大160分
        
        if max_possible_power > 0:
            power_ratio = min(1.0, total_power / max_possible_power)
            power_score = power_ratio * 50
        else:
            power_score = 0.0
        
        return unlock_score + power_score
    
    def identify_specialization(self) -> Optional[str]:
        """识别专精方向（最多技能的类别）"""
        unlocked_skills = self.skill_tree.get_unlocked_skills()
        
        if not unlocked_skills:
            return None
        
        # 统计各类别的技能数量
        categories = [
            self.skill_tree.skills[sid].category.value 
            for sid in unlocked_skills
        ]
        
        if not categories:
            return None
        
        # 找出最多的类别
        counter = Counter(categories)
        most_common = counter.most_common(1)
        
        return most_common[0][0] if most_common else None
    
    def is_specialist(self, threshold: float = 0.6) -> tuple:
        """判断是否为专家（某类别占比超过阈值），返回(bool, category)"""
        unlocked_skills = self.skill_tree.get_unlocked_skills()
        
        if len(unlocked_skills) < 3:
            return (False, None)
        
        categories = [
            self.skill_tree.skills[sid].category.value 
            for sid in unlocked_skills
        ]
        
        counter = Counter(categories)
        most_common = counter.most_common(1)
        
        if not most_common:
            return (False, None)
        
        category, count = most_common[0]
        ratio = count / len(unlocked_skills)
        
        return (ratio >= threshold, category if ratio >= threshold else None)
    
    def get_category_breakdown(self) -> Dict[str, int]:
        """获取各类别的技能数量统计"""
        unlocked_skills = self.skill_tree.get_unlocked_skills()
        
        breakdown = {}
        for sid in unlocked_skills:
            category = self.skill_tree.skills[sid].category.value
            breakdown[category] = breakdown.get(category, 0) + 1
        
        return breakdown
    
    def calculate_skill_score(self, skill_id: str) -> float:
        """计算单个技能的分数"""
        return self.level_system.get_skill_power(skill_id)
    
    def identify_specialization_direction(self) -> List[str]:
        """识别专精方向（返回类别列表，按数量排序）"""
        breakdown = self.get_category_breakdown()
        
        if not breakdown:
            return []
        
        # 按数量排序
        sorted_categories = sorted(breakdown.items(), key=lambda x: x[1], reverse=True)
        return [cat for cat, _ in sorted_categories]
    
    def calculate_specialization_depth(self) -> Dict[str, float]:
        """计算各类别的专精深度（平均等级）"""
        unlocked_skills = self.skill_tree.get_unlocked_skills()
        
        category_levels = {}
        category_counts = {}
        
        for sid in unlocked_skills:
            skill = self.skill_tree.skills[sid]
            cat = skill.category.value
            
            if cat not in category_levels:
                category_levels[cat] = 0
                category_counts[cat] = 0
            
            category_levels[cat] += skill.level
            category_counts[cat] += 1
        
        # 计算平均
        depths = {}
        for cat in category_levels:
            depths[cat] = category_levels[cat] / category_counts[cat] if category_counts[cat] > 0 else 0
        
        return depths
    
    def get_specialization_breadth(self) -> int:
        """获取专精广度（活跃类别数）"""
        return len(self.get_category_breakdown())
    
    def get_tier_distribution(self) -> Dict[str, int]:
        """获取层级分布统计"""
        unlocked_skills = self.skill_tree.get_unlocked_skills()
        
        distribution = {}
        for sid in unlocked_skills:
            tier = self.skill_tree.skills[sid].tier.name
            distribution[tier] = distribution.get(tier, 0) + 1
        
        return distribution
    
    def get_progression_summary(self) -> Dict:
        """获取综合进度摘要"""
        return {
            "tree_score": self.calculate_tree_score(),
            "specialization": self.identify_specialization(),
            "is_specialist": self.is_specialist(),
            "breadth": self.get_specialization_breadth(),
            "category_breakdown": self.get_category_breakdown(),
            "tier_distribution": self.get_tier_distribution(),
            "total_power": self.level_system.get_total_power()
        }

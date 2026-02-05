"""SkillTreeScorer - 技能树评分与专精识别"""
from collections import Counter
from typing import Dict, Optional
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
    
    def is_specialist(self, threshold: float = 0.6) -> bool:
        """判断是否为专家（某类别占比超过阈值）"""
        unlocked_skills = self.skill_tree.get_unlocked_skills()
        
        if len(unlocked_skills) < 3:
            return False
        
        categories = [
            self.skill_tree.skills[sid].category.value 
            for sid in unlocked_skills
        ]
        
        counter = Counter(categories)
        most_common_count = counter.most_common(1)[0][1]
        
        ratio = most_common_count / len(unlocked_skills)
        return ratio >= threshold
    
    def get_category_breakdown(self) -> Dict[str, int]:
        """获取各类别的技能数量统计"""
        unlocked_skills = self.skill_tree.get_unlocked_skills()
        
        breakdown = {}
        for sid in unlocked_skills:
            category = self.skill_tree.skills[sid].category.value
            breakdown[category] = breakdown.get(category, 0) + 1
        
        return breakdown

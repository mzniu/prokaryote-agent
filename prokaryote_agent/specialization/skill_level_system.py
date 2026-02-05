"""SkillLevelSystem - 技能等级与熟练度系统"""
from .skill_tree import SkillTree

class SkillLevelSystem:
    def __init__(self, skill_tree: SkillTree):
        self.skill_tree = skill_tree
    
    def gain_proficiency(self, skill_id: str, amount: float) -> bool:
        """增加技能熟练度"""
        if skill_id not in self.skill_tree.skills:
            return False
        
        skill = self.skill_tree.skills[skill_id]
        if not skill.unlocked:
            return False
        
        skill.proficiency = min(1.0, skill.proficiency + amount)
        
        # 熟练度达到1.0且未满级时自动升级
        if skill.proficiency >= 1.0 and skill.level < 5:
            self.level_up(skill_id)
        
        return True
    
    def level_up(self, skill_id: str) -> bool:
        """技能升级"""
        if skill_id not in self.skill_tree.skills:
            return False
        
        skill = self.skill_tree.skills[skill_id]
        
        if skill.level >= 5:
            return False  # 已满级
        
        if skill.proficiency < 1.0:
            return False  # 熟练度不足
        
        skill.level += 1
        skill.proficiency = 0.0  # 重置熟练度
        
        return True
    
    def get_skill_power(self, skill_id: str) -> float:
        """计算技能战斗力（0-300）"""
        if skill_id not in self.skill_tree.skills:
            return 0.0
        
        skill = self.skill_tree.skills[skill_id]
        
        if not skill.unlocked:
            return 0.0
        
        # 基础分：层级 * 20
        base_score = skill.tier.value * 20
        
        # 等级加成：level * 10
        level_bonus = skill.level * 10
        
        # 熟练度加成：proficiency * level * 2
        proficiency_bonus = skill.proficiency * skill.level * 2
        
        return base_score + level_bonus + proficiency_bonus
    
    def get_total_power(self) -> float:
        """计算所有技能的总战斗力"""
        total = 0.0
        for skill_id in self.skill_tree.skills:
            total += self.get_skill_power(skill_id)
        return total

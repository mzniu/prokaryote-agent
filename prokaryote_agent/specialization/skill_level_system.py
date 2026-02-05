"""SkillLevelSystem - 技能等级与熟练度系统"""
from typing import Dict, List
from .skill_tree import SkillTree

class SkillLevelSystem:
    def __init__(self, skill_tree: SkillTree):
        self.skill_tree = skill_tree
    
    def gain_proficiency(self, skill_id: str, amount: float) -> bool:
        """增加技能熟练度，返回是否触发升级"""
        if skill_id not in self.skill_tree.skills:
            return False
        
        skill = self.skill_tree.skills[skill_id]
        if not skill.unlocked:
            return False
        
        skill.proficiency = min(1.0, skill.proficiency + amount)
        
        # 熟练度达到1.0且未满级时自动升级
        leveled_up = False
        if skill.proficiency >= 1.0 and skill.level < 5:
            leveled_up = self.level_up(skill_id)
        
        return leveled_up
    
    def level_up(self, skill_id: str) -> bool:
        """技能升级（直接升级，不检查熟练度）"""
        if skill_id not in self.skill_tree.skills:
            return False
        
        skill = self.skill_tree.skills[skill_id]
        
        if skill.level >= 5:
            return False  # 已满级
        
        skill.level += 1
        skill.proficiency = 0.0  # 重置熟练度
        
        return True
    
    def get_skill_power(self, skill_id: str) -> float:
        """获取技能战斗力
        
        公式: level + proficiency
        例如: Level 3, proficiency 0.8 => power = 3.8
        """
        if skill_id not in self.skill_tree.skills:
            return 0.0
        
        skill = self.skill_tree.skills[skill_id]
        
        if not skill.unlocked:
            return 0.0
        
        # 简单相加: level + proficiency
        return skill.level + skill.proficiency
    
    def get_total_power(self) -> float:
        """计算所有技能的总战斗力"""
        total = 0.0
        for skill_id in self.skill_tree.skills:
            total += self.get_skill_power(skill_id)
        return total
    
    def batch_gain_proficiency(self, gains: Dict[str, float]) -> List[str]:
        """批量增加熟练度，返回升级的技能列表"""
        leveled_up = []
        
        for skill_id, amount in gains.items():
            if skill_id not in self.skill_tree.skills:
                continue
            
            skill = self.skill_tree.skills[skill_id]
            old_level = skill.level
            
            self.gain_proficiency(skill_id, amount)
            
            if skill.level > old_level:
                leveled_up.append(skill_id)
        
        return leveled_up
    
    def get_level_bonuses(self, skill_id: str) -> float:
        """获取技能等级加成倍数
        
        Level 1 = 1.0x (基础)
        Level 2 = 1.5x
        Level 3 = 2.0x
        Level 4 = 2.5x
        Level 5 = 3.0x
        公式: 1.0 + (level - 1) * 0.5
        """
        if skill_id not in self.skill_tree.skills:
            return 0.0
        
        skill = self.skill_tree.skills[skill_id]
        
        # 等级倍数: 1 + (level-1)*0.5
        return 1.0 + (skill.level - 1) * 0.5
    
    def get_progress_to_next_level(self, skill_id: str) -> Dict:
        """获取到下一级的进度信息"""
        if skill_id not in self.skill_tree.skills:
            return {}
        
        skill = self.skill_tree.skills[skill_id]
        
        if skill.level >= 5:
            return {
                "current_level": 5,
                "max_level": True,
                "proficiency": skill.proficiency,
                "required": 1.0,
                "percentage": 100.0,
                "next_level": 5
            }
        
        return {
            "current_level": skill.level,
            "proficiency": skill.proficiency,
            "required": 1.0,  # 每级需要1.0熟练度
            "percentage": skill.proficiency * 100,
            "next_level": skill.level + 1
        }

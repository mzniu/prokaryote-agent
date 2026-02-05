"""SkillUnlocker - 技能解锁评估"""
from typing import List, Dict, Optional
from .skill_tree import SkillTree
from .skill_node import SkillNode

class SkillUnlocker:
    def __init__(self, skill_tree: SkillTree):
        self.skill_tree = skill_tree
    
    def check_unlock_eligibility(self, skill_id: str, capabilities: Dict) -> bool:
        """检查是否有资格解锁某技能"""
        if skill_id not in self.skill_tree.skills:
            return False
        
        skill = self.skill_tree.skills[skill_id]
        
        # 已解锁则返回False
        if skill.unlocked:
            return False
        
        # 检查前置技能
        if not self.skill_tree.check_prerequisites(skill_id):
            return False
        
        # 检查能力要求（简单实现）
        required_capability_count = skill.tier.value
        if len(capabilities) < required_capability_count:
            return False
        
        return True
    
    def get_unlockable_skills(self, capabilities: Dict) -> List[str]:
        """获取当前可解锁的所有技能"""
        unlockable = []
        
        for skill_id in self.skill_tree.skills:
            if self.check_unlock_eligibility(skill_id, capabilities):
                unlockable.append(skill_id)
        
        return unlockable
    
    def suggest_next_skill(self, capabilities: Dict, 
                          focus_category: Optional[str] = None) -> Optional[str]:
        """推荐下一个要解锁的技能"""
        unlockable = self.get_unlockable_skills(capabilities)
        
        if not unlockable:
            return None
        
        # 如果指定了类别，优先推荐该类别的技能
        if focus_category:
            category_skills = [
                sid for sid in unlockable 
                if self.skill_tree.skills[sid].category.value == focus_category
            ]
            if category_skills:
                return category_skills[0]
        
        # 否则返回层级最低的技能（基础优先）
        unlockable.sort(key=lambda sid: self.skill_tree.skills[sid].tier.value)
        return unlockable[0]
    
    def unlock_skill(self, skill_id: str) -> bool:
        """解锁技能"""
        if skill_id not in self.skill_tree.skills:
            return False
        
        if not self.skill_tree.check_prerequisites(skill_id):
            return False
        
        self.skill_tree.skills[skill_id].unlocked = True
        return True

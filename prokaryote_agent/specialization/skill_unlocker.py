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
    
    def unlock_skill(self, skill_id: str, initial_proficiency: float = 0.0) -> bool:
        """解锁技能"""
        if skill_id not in self.skill_tree.skills:
            return False
        
        if not self.skill_tree.check_prerequisites(skill_id):
            return False
        
        skill = self.skill_tree.skills[skill_id]
        skill.unlocked = True
        if initial_proficiency > 0:
            skill.proficiency = min(1.0, initial_proficiency)
        return True
    
    def can_unlock(self, skill_id: str, capabilities: Dict) -> bool:
        """检查是否可以解锁技能（别名）"""
        return self.check_unlock_eligibility(skill_id, capabilities)
    
    def check_prerequisites(self, skill_id: str) -> bool:
        """检查前置技能是否满足"""
        return self.skill_tree.check_prerequisites(skill_id)
    
    def evaluate_unlock_condition(self, skill_id: str, context: Dict) -> bool:
        """评估解锁条件"""
        if skill_id not in self.skill_tree.skills:
            return False
        
        skill = self.skill_tree.skills[skill_id]
        
        # 如果没有条件，总是通过
        if not skill.unlock_condition:
            return True
        
        # 简单实现：评估条件字符串
        try:
            # 提供辅助函数
            def has_capability(cap_name):
                return cap_name in context.get("capabilities", [])
            
            capability_count = len(context.get("capabilities", []))
            
            # 安全地评估条件
            result = eval(skill.unlock_condition, {
                "__builtins__": {},
                "has_capability": has_capability,
                "capability_count": capability_count
            })
            return bool(result)
        except:
            return False
    
    def batch_check_unlockable(self, skill_ids: List[str], capabilities: Dict) -> Dict[str, bool]:
        """批量检查技能是否可解锁"""
        return {sid: self.check_unlock_eligibility(sid, capabilities) for sid in skill_ids}
    
    def get_unlock_progress(self, skill_id: str, capabilities: Dict) -> Dict:
        """获取解锁进度详情"""
        if skill_id not in self.skill_tree.skills:
            return {"error": "Skill not found"}
        
        skill = self.skill_tree.skills[skill_id]
        prereqs_met = self.skill_tree.check_prerequisites(skill_id)
        condition_met = self.evaluate_unlock_condition(skill_id, {"capabilities": capabilities})
        
        return {
            "skill_id": skill_id,
            "unlocked": skill.unlocked,
            "prerequisites_met": prereqs_met,
            "condition_met": condition_met,
            "can_unlock": prereqs_met and condition_met and not skill.unlocked
        }
    
    def unlock_all_available(self, capabilities: Dict) -> List[str]:
        """解锁所有可用技能"""
        unlockable = self.get_unlockable_skills(capabilities)
        unlocked = []
        
        for skill_id in unlockable:
            if self.unlock_skill(skill_id):
                unlocked.append(skill_id)
        
        return unlocked

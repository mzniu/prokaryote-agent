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
        
        # 检查解锁条件（如果有）
        if skill.unlock_condition:
            if not self.evaluate_unlock_condition(skill_id, capabilities):
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
    
    def unlock_skill(self, skill_id: str, context_or_proficiency=None, initial_proficiency: float = None) -> bool:
        """解锁技能
        
        支持多种调用方式：
        1. unlock_skill(skill_id, context) - 带条件检查
        2. unlock_skill(skill_id, initial_proficiency=0.3) - 直接解锁
        3. unlock_skill(skill_id, context, initial_proficiency=0.3) - 条件检查+设置熟练度
        """
        if skill_id not in self.skill_tree.skills:
            return False
        
        # 确定proficiency值
        prof = 0.0
        if initial_proficiency is not None:
            prof = initial_proficiency
        
        # 检查是否传入了context（字典）
        if isinstance(context_or_proficiency, dict):
            context = context_or_proficiency
            if not self.can_unlock(skill_id, context):
                return False
        elif isinstance(context_or_proficiency, (int, float)):
            prof = context_or_proficiency
        
        if not self.skill_tree.check_prerequisites(skill_id):
            return False
        
        skill = self.skill_tree.skills[skill_id]
        skill.unlocked = True
        skill.level = max(1, skill.level)  # 解锁时至少1级
        skill.proficiency = max(skill.proficiency, prof)  # 保留更高的熟练度
        return True
    
    def can_unlock(self, skill_id: str, capabilities: Dict) -> bool:
        """检查是否可以解锁技能（别名）"""
        return self.check_unlock_eligibility(skill_id, capabilities)
    
    def check_prerequisites(self, skill_id: str) -> bool:
        """检查前置技能是否满足"""
        return self.skill_tree.check_prerequisites(skill_id)
    
    def evaluate_unlock_condition(self, condition_or_skill_id: str, context: Dict) -> bool:
        """评估解锁条件
        
        支持两种调用方式：
        1. evaluate_unlock_condition(condition_string, context) - 直接评估条件
        2. evaluate_unlock_condition(skill_id, context) - 评估技能的unlock_condition
        """
        # 判断是condition还是skill_id
        if condition_or_skill_id in self.skill_tree.skills:
            # 是skill_id，获取其unlock_condition
            skill = self.skill_tree.skills[condition_or_skill_id]
            condition = skill.unlock_condition
        else:
            # 是condition字符串
            condition = condition_or_skill_id
        
        # 如果没有条件或条件为空，总是通过
        if not condition or condition.strip() == "":
            return True
        
        # 简单实现：评估条件字符串
        try:
            # 提供辅助函数
            def has_capability(cap_name):
                return cap_name in context.get("capabilities", [])
            
            # 准备上下文变量
            eval_context = {
                "__builtins__": {},
                "has_capability": has_capability,
            }
            # 添加context中的所有变量
            eval_context.update(context)
            
            # 安全地评估条件
            result = eval(condition, eval_context)
            return bool(result)
        except:
            return False
    
    def batch_check_unlockable(self, capabilities_or_ids, capabilities: Dict = None) -> Dict:
        """批量检查技能是否可解锁
        
        支持两种调用方式：
        1. batch_check_unlockable(context) - 检查所有技能
        2. batch_check_unlockable(skill_ids, capabilities) - 检查指定技能
        
        返回：{skill_id: can_unlock_bool} 字典，仅包含可解锁的技能
        """
        # 如果第一个参数是字典且没有第二个参数，则检查所有技能
        if isinstance(capabilities_or_ids, dict) and capabilities is None:
            context = capabilities_or_ids
            skill_ids = list(self.skill_tree.skills.keys())
            # 只返回可解锁的技能（值为True的）
            result = {}
            for sid in skill_ids:
                if not self.skill_tree.skills[sid].unlocked:
                    if self.can_unlock(sid, context):
                        result[sid] = True
            return result
        
        # 否则按原API：指定技能列表
        skill_ids = capabilities_or_ids
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
    
    def unlock_all_available(self, context: Dict) -> int:
        """解锁所有可用技能，返回解锁的数量"""
        unlockable_dict = self.batch_check_unlockable(context)
        unlockable = [sid for sid, can_unlock in unlockable_dict.items() if can_unlock]
        count = 0
        
        for skill_id in unlockable:
            if self.unlock_skill(skill_id, context):
                count += 1
        
        return count

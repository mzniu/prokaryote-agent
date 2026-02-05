"""EvolutionStrategy - 进化策略生成器"""
from typing import List, Dict, Optional
from .skill_tree import SkillTree
from .skill_unlocker import SkillUnlocker
from .skill_tree_scorer import SkillTreeScorer

class EvolutionStrategy:
    def __init__(self, skill_tree: SkillTree, unlocker: SkillUnlocker, scorer: SkillTreeScorer):
        self.skill_tree = skill_tree
        self.unlocker = unlocker
        self.scorer = scorer
    
    def recommend_next_skill(self, capabilities: Dict, 
                            strategy: str = "balanced") -> Optional[str]:
        """推荐下一个技能
        
        Args:
            capabilities: 当前能力集
            strategy: 策略类型 - balanced(均衡), specialist(专精), explorer(探索)
        """
        unlockable = self.unlocker.get_unlockable_skills(capabilities)
        
        if not unlockable:
            return None
        
        if strategy == "specialist":
            # 专精策略：优先当前专精方向
            specialization = self.scorer.identify_specialization()
            if specialization:
                return self.unlocker.suggest_next_skill(capabilities, specialization)
        
        elif strategy == "explorer":
            # 探索策略：优先未开发的类别
            breakdown = self.scorer.get_category_breakdown()
            all_categories = set(skill.category.value for skill in self.skill_tree.skills.values())
            unexplored = all_categories - set(breakdown.keys())
            
            if unexplored:
                target_category = list(unexplored)[0]
                return self.unlocker.suggest_next_skill(capabilities, target_category)
        
        # 默认均衡策略
        return self.unlocker.suggest_next_skill(capabilities)
    
    def generate_evolution_goals(self, current_score: float, 
                                target_score: float) -> List[Dict]:
        """生成进化目标"""
        goals = []
        score_gap = target_score - current_score
        
        if score_gap <= 0:
            return goals
        
        # 目标1：提升解锁数量
        unlocked_count = len(self.skill_tree.get_unlocked_skills())
        total_count = len(self.skill_tree.skills)
        
        if unlocked_count < total_count:
            goals.append({
                "type": "unlock_skills",
                "target_count": min(total_count, unlocked_count + 3),
                "priority": 0.8
            })
        
        # 目标2：提升技能等级
        low_level_skills = [
            sid for sid, skill in self.skill_tree.skills.items()
            if skill.unlocked and skill.level < 3
        ]
        
        if low_level_skills:
            goals.append({
                "type": "level_up_skills",
                "target_skills": low_level_skills[:2],
                "priority": 0.7
            })
        
        # 目标3：提升熟练度
        goals.append({
            "type": "improve_proficiency",
            "target_proficiency": 0.8,
            "priority": 0.6
        })
        
        return goals
    
    def detect_synergy(self, skill_ids: List[str]) -> float:
        """检测技能协同效应（0-1）"""
        if len(skill_ids) < 2:
            return 0.0
        
        # 检查是否属于相同类别
        categories = [
            self.skill_tree.skills[sid].category 
            for sid in skill_ids 
            if sid in self.skill_tree.skills
        ]
        
        if not categories:
            return 0.0
        
        # 相同类别的技能有协同
        same_category_count = sum(1 for i in range(len(categories)-1) 
                                  if categories[i] == categories[i+1])
        
        synergy_ratio = same_category_count / (len(categories) - 1)
        
        return synergy_ratio * 0.5  # 最高0.5协同加成

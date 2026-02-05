"""EvolutionStrategy - 进化策略生成器"""
from typing import List, Dict, Optional
from .skill_tree import SkillTree
from .skill_unlocker import SkillUnlocker
from .skill_tree_scorer import SkillTreeScorer

class EvolutionStrategy:
    def __init__(self, skill_tree: SkillTree, unlocker: SkillUnlocker, level_system=None, scorer: SkillTreeScorer = None):
        self.skill_tree = skill_tree
        self.unlocker = unlocker
        self.level_system = level_system  # 可选参数
        self.scorer = scorer or SkillTreeScorer(skill_tree, level_system)
    
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
    
    def recommend_next_skills(self, capabilities: Dict, count: int = 3) -> List[str]:
        """推荐多个下一步技能"""
        unlockable = self.unlocker.get_unlockable_skills(capabilities)
        
        if not unlockable:
            return []
        
        # 按层级和类别排序
        scored = []
        for skill_id in unlockable:
            skill = self.skill_tree.skills[skill_id]
            score = skill.tier.value * 10
            scored.append((skill_id, score))
        
        scored.sort(key=lambda x: x[1])
        return [sid for sid, _ in scored[:count]]
    
    def adjust_strategy_based_on_tree(self) -> str:
        """根据技能树状态调整策略"""
        is_specialist, category = self.scorer.is_specialist()
        
        if is_specialist:
            return "specialist"
        
        breadth = self.scorer.get_specialization_breadth()
        if breadth < 2:
            return "explorer"
        
        return "balanced"
    
    def detect_skill_synergy(self, skill_ids: List[str]) -> Dict:
        """检测技能协同详情"""
        synergy_value = self.detect_synergy(skill_ids)
        
        categories = {}
        for sid in skill_ids:
            if sid in self.skill_tree.skills:
                cat = self.skill_tree.skills[sid].category.value
                categories[cat] = categories.get(cat, 0) + 1
        
        return {
            "synergy_value": synergy_value,
            "category_distribution": categories,
            "is_cluster": len(categories) == 1,
            "is_combination": len(categories) > 1
        }
    
    def generate_evolution_goal(self, goal_type: str, context: Dict = None) -> Dict:
        """生成单个进化目标"""
        context = context or {}
        
        if goal_type == "unlock":
            capabilities = context.get("capabilities", {})
            next_skill = self.recommend_next_skill(capabilities)
            return {
                "type": "unlock_skill",
                "target": next_skill,
                "priority": 0.8
            }
        
        elif goal_type == "level_up":
            unlocked = self.skill_tree.get_unlocked_skills()
            low_level = [sid for sid in unlocked if self.skill_tree.skills[sid].level < 3]
            return {
                "type": "level_up_skill",
                "targets": low_level[:1],
                "priority": 0.7
            }
        
        elif goal_type == "specialize":
            specialization = self.scorer.identify_specialization()
            return {
                "type": "specialize",
                "target_category": specialization,
                "priority": 0.6
            }
        
        return {"type": goal_type, "priority": 0.5}
    
    def get_skill_priority_matrix(self) -> Dict[str, float]:
        """生成技能优先级矩阵"""
        matrix = {}
        
        for skill_id, skill in self.skill_tree.skills.items():
            if skill.unlocked:
                continue
            
            # 基础优先级
            priority = 0.5
            
            # 层级加分（低层级高优先级）
            priority += (6 - skill.tier.value) * 0.1
            
            # 前置满足加分
            if self.skill_tree.check_prerequisites(skill_id):
                priority += 0.2
            
            matrix[skill_id] = priority
        
        return matrix

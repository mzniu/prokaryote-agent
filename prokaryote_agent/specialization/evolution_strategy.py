"""EvolutionStrategy - 进化策略生成器"""
from typing import List, Dict, Optional, Tuple
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
    
    def recommend_next_skills(self, capabilities: Dict, count: int = 3, prefer_specialization: bool = False) -> List[Tuple[str, float]]:
        """推荐多个下一步技能，返回(skill_id, priority)元组列表"""
        # 使用batch_check_unlockable获取可解锁技能
        unlockable_dict = self.unlocker.batch_check_unlockable(capabilities)
        unlockable = [sid for sid, can in unlockable_dict.items() if can]
        
        if not unlockable:
            return []
        
        # 计算每个技能的优先级分数
        scored = []
        for skill_id in unlockable:
            skill = self.skill_tree.skills[skill_id]
            priority = skill.tier.value * 10  # 基础优先级
            
            # 如果prefer_specialization，增加主专精类别的权重
            if prefer_specialization and self.scorer:
                is_specialist, spec_category = self.scorer.is_specialist(threshold=0.5)
                if is_specialist and skill.category.value == spec_category:
                    priority += 20  # 专精加成
            
            scored.append((skill_id, float(priority)))
        
        # 按优先级降序排序
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:count]
    
    def adjust_strategy_based_on_tree(self) -> Dict:
        """根据技能树状态调整策略，返回包含建议的字典"""
        is_specialist, category = self.scorer.is_specialist()
        breadth = self.scorer.get_specialization_breadth()
        
        reasoning = []
        focus_breadth = False
        focus_leveling = False
        continue_specialization = False
        suggested_goal_type = "unlock"
        
        if is_specialist:
            reasoning.append(f"已专精于{category}类别")
            continue_specialization = True
            suggested_goal_type = "specialize"
        elif breadth < 2:
            reasoning.append("技能广度较窄，建议探索新类别")
            focus_breadth = True
            suggested_goal_type = "unlock"
        else:
            reasoning.append("技能分布较均衡，建议深度发展")
            focus_leveling = True
            suggested_goal_type = "level_up"
        
        return {
            "focus_breadth": focus_breadth,
            "focus_leveling": focus_leveling,
            "continue_specialization": continue_specialization,
            "suggested_goal_type": suggested_goal_type,
            "reasoning": reasoning
        }
        if breadth < 2:
            return "explorer"
        
        return "balanced"
    
    def detect_skill_synergy(self, skill_ids: List[str] = None) -> List[Dict]:
        """检测技能协同效应列表
        
        如果不提供skill_ids，则扫描所有已解锁技能找出协同
        """
        if skill_ids is None:
            # 扫描所有已解锁技能的协同
            synergies = []
            unlocked = self.skill_tree.get_unlocked_skills()
            
            # 检测组合技能协同
            for skill in self.skill_tree.skills.values():
                if skill.is_combination and not skill.unlocked:
                    prereq_unlocked = all(
                        self.skill_tree.skills[pid].unlocked 
                        for pid in skill.prerequisites 
                        if pid in self.skill_tree.skills
                    )
                    if prereq_unlocked:
                        synergies.append({
                            "type": "combination",
                            "skill_id": skill.id,
                            "value": 1.5
                        })
            
            # 检测类别聚类协同
            from collections import Counter
            high_level_skills = [s for s in unlocked if s.level >= 3]
            category_counts = Counter(s.category for s in high_level_skills)
            
            for category, count in category_counts.items():
                if count >= 3:
                    # 获取该类别下的所有高等级技能ID
                    skills_in_cluster = [s.id for s in high_level_skills if s.category == category]
                    synergies.append({
                        "type": "category_cluster",
                        "category": category.value,
                        "count": count,
                        "value": 1.2,
                        "skills": skills_in_cluster
                    })
            
            return synergies
        
        # 原有逻辑：详细分析特定技能组合
        synergy_value = self.detect_synergy(skill_ids)
        
        categories = {}
        for sid in skill_ids:
            if sid in self.skill_tree.skills:
                cat = self.skill_tree.skills[sid].category.value
                categories[cat] = categories.get(cat, 0) + 1
        
        return [{
            "synergy_value": synergy_value,
            "category_distribution": categories,
            "is_cluster": len(categories) == 1,
            "is_combination": len(categories) > 1
        }]
    
    def generate_evolution_goal(self, context: Dict = None, goal_type: str = "unlock") -> Dict:
        """生成单个进化目标
        
        参数顺序调整为context优先，以支持测试中的调用方式
        """
        context = context or {}
        
        if goal_type == "unlock":
            capabilities = context.get("capabilities", {})
            unlockable = self.unlocker.batch_check_unlockable(context)
            
            if not unlockable:
                return {"type": "unlock_skill", "target_skill_id": None}
            
            # unlockable 现在返回的是字典 {skill_id: bool}
            next_skill_id = next(iter(unlockable)) if unlockable else None
            if next_skill_id and next_skill_id in self.skill_tree.skills:
                skill = self.skill_tree.skills[next_skill_id]
                return {
                    "type": "unlock_skill",
                    "target_skill_id": skill.id,
                    "target_skill_name": skill.name,
                    "description": f"Unlock {skill.name}",
                    "priority": 0.8
                }
            
            return {"type": "unlock_skill", "target_skill_id": None}
        
        elif goal_type == "level_up":
            unlocked = self.skill_tree.get_unlocked_skills()
            if not unlocked:
                return {"type": "level_up_skill", "target_skill_id": None}
            
            # 选择等级最低的技能
            low_level = [s for s in unlocked if s.level < 3]
            if low_level:
                target = low_level[0]
                return {
                    "type": "level_up_skill",
                    "target_skill_id": target.id,
                    "current_level": target.level,
                    "priority": 0.7
                }
            
            return {"type": "level_up_skill", "target_skill_id": None}
        
        elif goal_type == "specialize":
            specializations = self.scorer.identify_specialization_direction()
            if specializations:
                category, score = specializations[0]
                return {
                    "type": "specialize",
                    "target_category": category,
                    "description": f"Focus on {category} specialization",
                    "priority": 0.6
                }
            return {"type": "specialize", "target_category": None, "description": "No specialization target"}
        
        return {"type": goal_type, "priority": 0.5}
    
    def get_skill_priority_matrix(self) -> Dict[str, Dict]:
        """生成技能优先级矩阵，返回详细因子"""
        matrix = {}
        
        for skill_id, skill in self.skill_tree.skills.items():
            if skill.unlocked:
                continue
            
            # 基础优先级
            priority = 0.5
            
            # 因子
            factors = {
                'tier_value': skill.tier.value,
                'is_combination': skill.is_combination,
                'num_capabilities': 0, # 这里没有上下文，暂时设为0
                'num_prerequisites': len(skill.prerequisites)
            }
            
            # 层级加分（低层级高优先级）
            priority += (6 - skill.tier.value) * 0.1
            
            # 前置满足加分
            if self.skill_tree.check_prerequisites(skill_id):
                priority += 0.2
            
            factors['total_priority'] = priority
            matrix[skill_id] = factors
        
        return matrix

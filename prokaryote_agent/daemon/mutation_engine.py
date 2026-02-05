"""MutationEngine - 变异引擎"""
import random
import json

class MutationEngine:
    def __init__(self, mutation_rate=0.1, config=None):
        self.config = config or {}
        self.mutation_rate = mutation_rate
        self.mutation_types = ["parameter_tuning", "new_goal_injection", "strategy_variation"]
        self.mutation_history = []
    
    def apply_mutations(self, genes, mutation_rate=None):
        """对基因应用变异"""
        rate = mutation_rate or genes.get("mutation_rate", 0.1)
        mutations = []
        
        # 参数调整变异
        if random.random() < rate:
            param_mutation = self._parameter_tuning(genes)
            if param_mutation:
                mutations.append(param_mutation)
        
        # 新目标注入
        if random.random() < rate * 0.5:
            goal_mutation = self._new_goal_injection(genes)
            if goal_mutation:
                mutations.append(goal_mutation)
        
        # 策略变化
        if random.random() < rate * 0.3:
            strategy_mutation = self._strategy_variation(genes)
            if strategy_mutation:
                mutations.append(strategy_mutation)
        
        self.mutation_history.extend(mutations)
        return mutations
    
    def _parameter_tuning(self, genes):
        """参数微调变异"""
        capabilities = genes.get("capabilities", [])
        if not capabilities:
            return None
        
        # 随机选择一个能力进行参数调整
        cap_index = random.randint(0, len(capabilities) - 1)
        mutation = {
            "type": "parameter_tuning",
            "target": f"capability_{cap_index}",
            "adjustment": random.uniform(-0.1, 0.1)
        }
        return mutation
    
    def _new_goal_injection(self, genes):
        """新目标注入变异"""
        new_goals = [
            "improve_error_handling",
            "optimize_performance",
            "enhance_logging",
            "add_validation"
        ]
        
        mutation = {
            "type": "new_goal_injection",
            "goal": random.choice(new_goals),
            "priority": random.uniform(0.3, 0.8)
        }
        return mutation
    
    def _strategy_variation(self, genes):
        """策略变化变异"""
        strategies = ["conservative", "aggressive", "balanced", "exploratory"]
        
        mutation = {
            "type": "strategy_variation",
            "new_strategy": random.choice(strategies),
            "confidence": random.uniform(0.5, 0.9)
        }
        return mutation
    
    def get_mutation_summary(self):
        """获取变异历史摘要"""
        summary = {
            "total_mutations": len(self.mutation_history),
            "by_type": {}
        }
        
        for mutation in self.mutation_history:
            mut_type = mutation.get("type", "unknown")
            summary["by_type"][mut_type] = summary["by_type"].get(mut_type, 0) + 1
        
        return summary

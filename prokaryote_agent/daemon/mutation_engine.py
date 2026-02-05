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
        
    def _mutate_random_innovation(self, genes):
        """随机创新变异：完全随机生成新特性"""
        mutated_genes = genes.copy()
        
        # 创新生成逻辑
        innovation = {
            "name": f"innovation_{random.randint(1000, 9999)}",
            "type": "random_innovation",
            "potential": random.uniform(0.1, 0.9)
        }
        
        # 添加到基因中
        if "innovations" not in mutated_genes:
            mutated_genes["innovations"] = []
        mutated_genes["innovations"].append(innovation)
        
        # 同时添加到innovation_suggestions以兼容测试
        if "innovation_suggestions" not in mutated_genes:
            mutated_genes["innovation_suggestions"] = []
        mutated_genes["innovation_suggestions"].append(innovation)
        
        description = f"Added random innovation: {innovation['name']}"
        return mutated_genes, description
        
    def _mutate_parameter_tuning(self, genes):
        """参数调整变异"""
        mutated_genes = genes.copy()
        if "config" not in mutated_genes:
            mutated_genes["config"] = {}
        
        # 随机调整一个参数
        param = f"param_{random.randint(1, 5)}"
        value = random.uniform(0.5, 1.5)
        mutated_genes["config"][param] = value
        
        description = f"Tuned parameter {param} to {value:.2f}"
        return mutated_genes, description

    def _mutate_new_goal_injection(self, genes):
        """新目标注入变异"""
        mutated_genes = genes.copy()
        if "goals" not in mutated_genes:
            mutated_genes["goals"] = []
            
        new_goal = {
            "type": "injected_goal",
            "target": f"target_{random.randint(1, 100)}",
            "priority": random.uniform(0.5, 1.0)
        }
        mutated_genes["goals"].append(new_goal)
        
        description = f"Injected new goal: {new_goal['target']}"
        return mutated_genes, description

    def _mutate_strategy_adjustment(self, genes):
        """策略调整变异"""
        mutated_genes = genes.copy()
        strategies = ["aggressive", "conservative", "balanced", "experimental"]
        new_strategy = random.choice(strategies)
        mutated_genes["strategy"] = new_strategy
        
        description = f"Adjusted strategy to {new_strategy}"
        return mutated_genes, description
        
    def _mutate_capability_combination(self, genes):
        """能力组合变异"""
        mutated_genes = genes.copy()
        capabilities = mutated_genes.get("capabilities", [])
        
        if len(capabilities) >= 2:
            # 随机选择两个能力组合
            c1, c2 = random.sample(capabilities, 2)
            c1_name = c1.get("name", "unknown") if isinstance(c1, dict) else str(c1)
            c2_name = c2.get("name", "unknown") if isinstance(c2, dict) else str(c2)
            
            new_cap = {
                "name": f"combo_{c1_name}_{c2_name}",
                "type": "combination",
                "parents": [c1_name, c2_name],
                "synergy": random.uniform(1.1, 1.5)
            }
            capabilities.append(new_cap)
            
        description = "Combined capabilities to form new trait"
        return mutated_genes, description

    def get_mutation_summary(self, mutation_history=None):
        """获取变异历史摘要"""
        summary = {
            "total_mutations": len(self.mutation_history),
            "by_type": {}
        }
        
        for mutation in self.mutation_history:
            mut_type = mutation.get("type", "unknown")
            summary["by_type"][mut_type] = summary["by_type"].get(mut_type, 0) + 1
        
        return summary

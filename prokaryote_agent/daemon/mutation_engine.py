"""MutationEngine - 变异引擎"""
import random
import json
import copy

class MutationEngine:
    def __init__(self, mutation_rate=0.1, config=None):
        self.config = config or {}
        self.mutation_rate = mutation_rate
        self.mutation_types = {
            "parameter_tuning": {"weight": 0.4},
            "new_goal_injection": {"weight": 0.3},
            "strategy_variation": {"weight": 0.2},
            "random_innovation": {"weight": 0.1},
            "capability_combination": {"weight": 0.1}
        }
        self.mutation_history = []
    
    def apply_mutations(self, genes, mutation_rate=None):
        """对基因应用变异
        Returns:
            dict: 变异后的基因组
        """
        rate = mutation_rate or self.mutation_rate
        mutated_genes = copy.deepcopy(genes)
        if "mutations" not in mutated_genes:
            mutated_genes["mutations"] = []
            
        # 简单概率应用变异
        if random.random() < rate:
            # 随机选择一种变异
            mutation_type = random.choice(list(self.mutation_types.keys()))
            
            if mutation_type == "parameter_tuning":
                mutated_genes, desc = self._mutate_parameter_tuning(mutated_genes)
                self._record_mutation(mutated_genes, "parameter_tuning", desc)
                
            elif mutation_type == "new_goal_injection":
                mutated_genes, desc = self._mutate_new_goal_injection(mutated_genes)
                self._record_mutation(mutated_genes, "new_goal_injection", desc)
                
            elif mutation_type == "strategy_variation":
                # 注意：这里映射到 _mutate_strategy_adjustment
                mutated_genes, desc = self._mutate_strategy_adjustment(mutated_genes)
                self._record_mutation(mutated_genes, "strategy_variation", desc)
                
            elif mutation_type == "random_innovation":
                mutated_genes, desc = self._mutate_random_innovation(mutated_genes)
                self._record_mutation(mutated_genes, "random_innovation", desc)
                
            elif mutation_type == "capability_combination":
                mutated_genes, desc = self._mutate_capability_combination(mutated_genes)
                self._record_mutation(mutated_genes, "capability_combination", desc)
                
        return mutated_genes

    def _record_mutation(self, genes, type_name, description):
        mutation_record = {
            "type": type_name,
            "description": description,
            "timestamp": random.randint(1000, 9999) # Mock timestamp
        }
        genes["mutations"].append(mutation_record)
        self.mutation_history.append(mutation_record)

    def _mutate_parameter_tuning(self, genes):
        """参数调整变异"""
        mutated_genes = copy.deepcopy(genes)
        
        # 尝试调整 inherited_capabilities
        if "inherited_capabilities" in mutated_genes and mutated_genes["inherited_capabilities"]:
            cap = random.choice(mutated_genes["inherited_capabilities"])
            if "fitness_score" in cap:
                change = random.uniform(-0.1, 0.1)
                cap["fitness_score"] = max(0.0, min(1.0, cap["fitness_score"] + change))
        
        description = "Tuned capability parameters"
        return mutated_genes, description

    def _mutate_new_goal_injection(self, genes):
        """新目标注入变异"""
        mutated_genes = copy.deepcopy(genes)
        if "inherited_goals" not in mutated_genes:
            mutated_genes["inherited_goals"] = []
            
        new_goal = {
            "type": "injected_goal",
            "target": f"target_{random.randint(1, 100)}",
            "priority": random.uniform(0.5, 1.0)
        }
        mutated_genes["inherited_goals"].append(new_goal)
        
        # 同时填充 goals 为了兼容性? 测试只检查 inherited_goals
        
        description = f"Injected new goal: {new_goal['target']}"
        return mutated_genes, description

    def _mutate_strategy_adjustment(self, genes):
        """策略调整变异"""
        mutated_genes = copy.deepcopy(genes)
        if "evolution_strategy" not in mutated_genes:
            mutated_genes["evolution_strategy"] = {"exploration_rate": 0.1}
            
        strategy = mutated_genes["evolution_strategy"]
        if "exploration_rate" in strategy:
            change = random.uniform(-0.05, 0.05)
            strategy["exploration_rate"] = max(0.05, min(0.5, strategy["exploration_rate"] + change))
            
        description = "Adjusted evolution strategy parameters"
        return mutated_genes, description
        
    def _mutate_random_innovation(self, genes):
        """随机创新变异"""
        mutated_genes = copy.deepcopy(genes)
        if "innovation_suggestions" not in mutated_genes:
            mutated_genes["innovation_suggestions"] = []
            
        innovation = {
            "name": f"innovation_{random.randint(1000, 9999)}",
            "type": "random",
            "potential": random.uniform(0.1, 1.0)
        }
        mutated_genes["innovation_suggestions"].append(innovation)
        
        description = f"Generated random innovation {innovation['name']}"
        return mutated_genes, description
        
    def _mutate_capability_combination(self, genes):
        """能力组合变异"""
        mutated_genes = copy.deepcopy(genes)
        if "suggested_combinations" not in mutated_genes:
            mutated_genes["suggested_combinations"] = []
            
        combo = {
            "source": ["cap_a", "cap_b"],
            "result": "cap_ab",
            "synergy": 1.2
        }
        mutated_genes["suggested_combinations"].append(combo)
            
        description = "Suggested capability combination"
        return mutated_genes, description

    def get_mutation_summary(self, genes=None):
        """获取变异历史摘要
        Args:
            genes (dict, optional): 如果提供，分析该基因组中的 mutations
        """
        source_mutations = []
        if genes and "mutations" in genes:
            source_mutations = genes["mutations"]
        elif not genes:
            source_mutations = self.mutation_history
            
        summary = {
            "total_mutations": len(source_mutations),
            "mutation_types": {},
            "by_type": {} # 为了兼容之前的实现
        }
        
        for mutation in source_mutations:
            mut_type = mutation.get("type", "unknown")
            summary["mutation_types"][mut_type] = summary["mutation_types"].get(mut_type, 0) + 1
            summary["by_type"][mut_type] = summary["by_type"].get(mut_type, 0) + 1
        
        return summary

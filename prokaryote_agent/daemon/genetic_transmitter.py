"""GeneticTransmitter - 基因选择与传递"""
import json
from pathlib import Path
from datetime import datetime

class GeneticTransmitter:
    def __init__(self, config=None):
        self.config = config or {}
        self.mutation_rate = self.config.get("mutation_rate", 0.1)
        self.selection_threshold = self.config.get("selection_threshold", 0.6)
    
    def generate_genes(self, generation, capabilities, lineage="main", skill_tree=None):
        """生成下一代的基因"""
        selection_result = self._select_capabilities(capabilities)
        genes = {
            "generation": generation + 1,
            "lineage": lineage,
            "timestamp": datetime.now().isoformat(),
            "capabilities": selection_result.get("keep", []),
            "mutation_rate": self.mutation_rate
        }
        
        # 提取技能树加成
        if skill_tree:
            genes["skill_bonuses"] = self._extract_skill_bonuses(skill_tree)
        
        return genes
    
    def _select_capabilities(self, capabilities):
        """选择要传递的能力"""
        if not capabilities:
            return {"keep": [], "drop": []}
        
        keep = []
        drop = []
        
        for cap in capabilities:
            # 简单选择逻辑：成功率高于阈值的能力
            if isinstance(cap, dict):
                success_rate = cap.get("success_rate", 0)
                fitness = cap.get("fitness", success_rate)
                if fitness >= self.selection_threshold:
                    keep.append(cap)
                else:
                    drop.append(cap)
            else:
                keep.append(cap)
        
        return {"keep": keep, "drop": drop}
    
    def _extract_skill_bonuses(self, skill_tree):
        """从技能树提取加成信息"""
        bonuses = {}
        
        # 从skill_tree对象提取已解锁技能的加成
        if hasattr(skill_tree, 'get_unlocked_skills'):
            unlocked = skill_tree.get_unlocked_skills()
            for skill_id in unlocked:
                if hasattr(skill_tree, 'skills') and skill_id in skill_tree.skills:
                    skill = skill_tree.skills[skill_id]
                    bonuses[skill_id] = {
                        "level": skill.level,
                        "proficiency": skill.proficiency
                    }
        
        return bonuses
    
    def _calculate_baseline(self, capabilities):
        """计算性能基线"""
        if not capabilities:
            return {"average_success_rate": 0.0, "total_capabilities": 0}
        
        success_rates = [cap.get("success_rate", 0) for cap in capabilities if isinstance(cap, dict)]
        
        if not success_rates:
            return {"average_success_rate": 0.0, "total_capabilities": len(capabilities)}
        
        avg_success = sum(success_rates) / len(success_rates)
        
        return {
            "average_success_rate": avg_success,
            "total_capabilities": len(capabilities),
            "max_success_rate": max(success_rates),
            "min_success_rate": min(success_rates)
        }
    
    def save_genes(self, genes, path):
        """保存基因文件 - 支持目录或文件路径"""
        path_obj = Path(path)
        
        # 如果是目录，生成文件名
        if path_obj.is_dir() or not path_obj.suffix:
            path_obj = path_obj / f"genes_gen_{genes.get('generation', 0):04d}.json"
        
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        
        with open(path_obj, 'w') as f:
            json.dump(genes, f, indent=2)
        
        return str(path_obj)
    
    def load_genes(self, path):
        """加载基因文件"""
        path_obj = Path(path)
        
        # 如果是目录，查找最新的genes文件
        if path_obj.is_dir():
            gene_files = sorted(path_obj.glob("genes_gen_*.json"))
            if not gene_files:
                raise FileNotFoundError(f"No genes files found in {path}")
            path_obj = gene_files[-1]
        
        with open(path_obj, 'r') as f:
            return json.load(f)

"""SkillTree - 技能树DAG结构"""
import json
from pathlib import Path
from typing import Dict, List, Set
from .skill_node import SkillNode, SkillTier, SkillCategory

class SkillTree:
    def __init__(self, tree_path=None):
        self.skills: Dict[str, SkillNode] = {}
        self.root_skills: List[str] = []
        
        if tree_path:
            self.load_from_file(tree_path)
    
    def add_skill(self, skill: SkillNode):
        """添加技能节点"""
        skill_id = skill.id
        if skill_id in self.skills:
            raise ValueError(f"Skill {skill_id} already exists")
        
        # 允许添加有缺失先决条件的技能，在validate_dag时检测
        self.skills[skill_id] = skill
        
        # 如果没有前置技能，加入根节点
        if not skill.prerequisites:
            self.root_skills.append(skill_id)
    
    def validate_dag(self) -> bool:
        """验证是否为有向无环图，并检查先决条件完整性"""
        # 首先检查所有先决条件是否存在
        for skill_id, skill in self.skills.items():
            for prereq_id in skill.prerequisites:
                if prereq_id not in self.skills:
                    return False  # 缺失先决条件
        
        # 检测循环
        visited = set()
        rec_stack = set()
        
        def has_cycle(skill_id):
            visited.add(skill_id)
            rec_stack.add(skill_id)
            
            # 检查所有依赖该技能的后继节点
            for other_id, other_skill in self.skills.items():
                if skill_id in other_skill.prerequisites:
                    if other_id not in visited:
                        if has_cycle(other_id):
                            return True
                    elif other_id in rec_stack:
                        return True
            
            rec_stack.remove(skill_id)
            return False
        
        for skill_id in self.skills:
            if skill_id not in visited:
                if has_cycle(skill_id):
                    return False
        
        return True
    
    def check_prerequisites(self, skill_id: str) -> bool:
        """检查技能的前置条件是否满足"""
        if skill_id not in self.skills:
            return False
        
        skill = self.skills[skill_id]
        
        for prereq_id in skill.prerequisites:
            if prereq_id not in self.skills:
                return False
            if not self.skills[prereq_id].unlocked:
                return False
        
        return True
    
    def get_unlocked_skills(self) -> List:
        """获取已解锁的技能列表（返回SkillNode对象）"""
        return [skill for skill in self.skills.values() if skill.unlocked]
    
    def get_locked_skills(self) -> List:
        """获取锁定的技能列表（返回SkillNode对象）"""
        return [skill for skill in self.skills.values() if not skill.unlocked]
    
    def get_skill(self, skill_id: str):
        """获取指定技能"""
        return self.skills.get(skill_id)
    
    def get_skills_by_tier(self, tier: SkillTier) -> List:
        """获取指定层级的技能（返回SkillNode对象）"""
        return [skill for skill in self.skills.values() if skill.tier == tier]
    
    def get_available_to_unlock(self) -> List:
        """获取可解锁的技能（前置条件满足但未解锁，返回SkillNode对象）"""
        available = []
        for skill in self.skills.values():
            if not skill.unlocked and self.check_prerequisites(skill.id):
                available.append(skill)
        return available
    
    def __contains__(self, skill_id: str) -> bool:
        """支持 'skill_id in tree' 语法"""
        return skill_id in self.skills
    
    def __len__(self) -> int:
        """返回技能总数"""
        return len(self.skills)
    
    def get_available_skills(self) -> List[str]:
        """获取可解锁的技能（前置条件满足但未解锁）"""
        available = []
        for skill_id, skill in self.skills.items():
            if not skill.unlocked and self.check_prerequisites(skill_id):
                available.append(skill_id)
        return available
    
    def save_to_file(self, path: str):
        """保存技能树到文件"""
        data = {
            "root_skills": self.root_skills,
            "skills": {sid: skill.to_dict() for sid, skill in self.skills.items()}
        }
        
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_from_file(self, path: str):
        """从文件加载技能树"""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        self.root_skills = data.get("root_skills", [])
        self.skills = {}
        
        for skill_id, skill_data in data.get("skills", {}).items():
            self.skills[skill_id] = SkillNode.from_dict(skill_data)
    
    def get_skill_path(self, skill_id: str) -> List[str]:
        """获取到达某技能的路径"""
        if skill_id not in self.skills:
            return []
        
        path = []
        def build_path(sid):
            skill = self.skills[sid]
            for prereq in skill.prerequisites:
                if prereq not in path:
                    build_path(prereq)
            if sid not in path:
                path.append(sid)
        
        build_path(skill_id)
        return path

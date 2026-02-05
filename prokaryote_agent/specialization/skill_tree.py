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
        if skill.skill_id in self.skills:
            raise ValueError(f"Skill {skill.skill_id} already exists")
        
        # 检查前置技能是否存在
        for prereq in skill.prerequisites:
            if prereq not in self.skills:
                raise ValueError(f"Prerequisite {prereq} not found")
        
        self.skills[skill.skill_id] = skill
        
        # 如果没有前置技能，加入根节点
        if not skill.prerequisites:
            self.root_skills.append(skill.skill_id)
        
        # 验证DAG
        if not self.validate_dag():
            del self.skills[skill.skill_id]
            if skill.skill_id in self.root_skills:
                self.root_skills.remove(skill.skill_id)
            raise ValueError("Adding this skill would create a cycle")
    
    def validate_dag(self) -> bool:
        """验证是否为有向无环图"""
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
    
    def get_unlocked_skills(self) -> List[str]:
        """获取已解锁的技能列表"""
        return [sid for sid, skill in self.skills.items() if skill.unlocked]
    
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

"""
技能执行器 - 调用和管理技能执行
"""

import json
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from .skill_base import Skill, SkillMetadata, SkillLibrary


class SkillExecutor:
    """
    技能执行器 - 负责调度和执行技能
    """
    
    def __init__(self, library: SkillLibrary = None):
        self.library = library or SkillLibrary()
        self.logger = logging.getLogger(__name__)
        self.execution_history: List[Dict[str, Any]] = []
    
    def execute(self, skill_id: str, **kwargs) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            skill_id: 技能ID
            **kwargs: 技能参数
        
        Returns:
            执行结果
        """
        self.logger.info(f"执行技能: {skill_id}")
        
        result = self.library.execute_skill(skill_id, **kwargs)
        
        # 记录历史
        self.execution_history.append({
            'skill_id': skill_id,
            'params': kwargs,
            'result': result,
        })
        
        if result.get('success'):
            self.logger.info(f"技能执行成功: {skill_id}")
        else:
            self.logger.warning(f"技能执行失败: {skill_id} - {result.get('error')}")
        
        return result
    
    def execute_chain(self, skill_chain: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        执行技能链（多个技能按顺序执行）
        
        Args:
            skill_chain: [{'skill_id': str, 'params': dict}, ...]
        
        Returns:
            各技能的执行结果列表
        """
        results = []
        context = {}  # 上下文，用于传递中间结果
        
        for step in skill_chain:
            skill_id = step['skill_id']
            params = step.get('params', {})
            
            # 合并上下文
            params['_context'] = context
            
            result = self.execute(skill_id, **params)
            results.append(result)
            
            # 更新上下文
            if result.get('success'):
                context[skill_id] = result.get('result')
            else:
                # 链中某个技能失败，可以选择中断或继续
                if step.get('required', True):
                    self.logger.error(f"技能链在 {skill_id} 处中断")
                    break
        
        return results
    
    def get_available_skills(self, domain: str = None) -> List[SkillMetadata]:
        """获取可用技能列表"""
        return self.library.list_skills(domain=domain)
    
    def get_skill_info(self, skill_id: str) -> Optional[Dict[str, Any]]:
        """获取技能详情"""
        skill = self.library.get_skill(skill_id)
        if not skill:
            return None
        
        return {
            'metadata': skill.metadata.to_dict(),
            'capabilities': skill.get_capabilities(),
            'examples': skill.get_usage_examples()
        }
    
    def suggest_skill(self, task_description: str) -> Optional[str]:
        """
        根据任务描述推荐技能
        
        Args:
            task_description: 任务描述
        
        Returns:
            推荐的技能ID
        """
        # TODO: 使用更智能的匹配算法（如向量相似度）
        # 目前简单实现：关键词匹配
        
        keywords = task_description.lower().split()
        best_match = None
        best_score = 0
        
        for skill_id, metadata in self.library.registry.items():
            score = 0
            skill_text = f"{metadata.name} {metadata.description}".lower()
            
            for keyword in keywords:
                if keyword in skill_text:
                    score += 1
            
            if score > best_score:
                best_score = score
                best_match = skill_id
        
        return best_match if best_score > 0 else None

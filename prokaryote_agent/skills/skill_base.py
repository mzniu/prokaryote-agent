"""
技能基础类 - 定义技能的结构和技能库
"""

import os
import json
import importlib
import importlib.util
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Callable
from enum import Enum


class SkillTier(Enum):
    """技能层级"""
    BASIC = "basic"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    MASTER = "master"
    EXPERT = "expert"


@dataclass
class SkillMetadata:
    """技能元数据"""
    skill_id: str                          # 技能唯一ID
    name: str                              # 技能名称
    version: str = "1.0.0"                 # 版本号
    tier: str = "basic"                    # 层级
    level: int = 0                         # 当前等级（从0开始，学习后升到1）
    description: str = ""                  # 技能描述
    domain: str = "general"                # 所属领域
    
    # 能力指标
    proficiency: float = 0.0               # 熟练度 0.0-1.0
    success_rate: float = 0.0              # 成功率
    total_executions: int = 0              # 总执行次数
    successful_executions: int = 0         # 成功次数
    
    # 时间戳
    created_at: str = ""                   # 创建时间
    updated_at: str = ""                   # 最后更新时间
    last_executed_at: str = ""             # 最后执行时间
    
    # 依赖关系
    prerequisites: List[str] = field(default_factory=list)  # 前置技能
    dependencies: List[str] = field(default_factory=list)   # 运行时依赖
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SkillMetadata':
        return cls(**data)


class Skill(ABC):
    """
    技能基类 - 所有技能必须继承此类
    
    每个技能需要实现：
    1. execute() - 执行技能的主逻辑
    2. validate_input() - 验证输入参数
    3. get_capabilities() - 返回技能能做什么
    """
    
    def __init__(self, metadata: SkillMetadata = None):
        self.metadata = metadata or SkillMetadata(
            skill_id=self.__class__.__name__.lower(),
            name=self.__class__.__name__
        )
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行技能
        
        Returns:
            {
                'success': bool,
                'result': Any,
                'error': str (if failed),
                'execution_time': float
            }
        """
        pass
    
    @abstractmethod
    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        pass
    
    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return []
    
    def upgrade(self, new_code: str = None) -> bool:
        """
        升级技能
        
        Args:
            new_code: 新的实现代码（可选）
        
        Returns:
            是否升级成功
        """
        self.metadata.level += 1
        self.metadata.updated_at = datetime.now().isoformat()
        self.metadata.version = self._increment_version(self.metadata.version)
        return True
    
    def _increment_version(self, version: str) -> str:
        """递增版本号"""
        parts = version.split('.')
        parts[-1] = str(int(parts[-1]) + 1)
        return '.'.join(parts)
    
    def record_execution(self, success: bool):
        """记录执行结果"""
        self.metadata.total_executions += 1
        if success:
            self.metadata.successful_executions += 1
        self.metadata.success_rate = (
            self.metadata.successful_executions / self.metadata.total_executions
        )
        self.metadata.last_executed_at = datetime.now().isoformat()


class SkillLibrary:
    """
    技能库 - 管理所有已学习的技能
    """
    
    def __init__(self, library_path: str = None):
        self.library_path = Path(library_path or "prokaryote_agent/skills/library")
        self.library_path.mkdir(parents=True, exist_ok=True)
        
        self.metadata_file = self.library_path / "skill_registry.json"
        self.skills: Dict[str, Skill] = {}
        self.registry: Dict[str, SkillMetadata] = {}
        
        self._load_registry()
    
    def _load_registry(self):
        """加载技能注册表"""
        if self.metadata_file.exists():
            with open(self.metadata_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                for skill_id, meta_dict in data.get('skills', {}).items():
                    self.registry[skill_id] = SkillMetadata.from_dict(meta_dict)
    
    def _save_registry(self):
        """保存技能注册表"""
        data = {
            'version': '1.0.0',
            'updated_at': datetime.now().isoformat(),
            'skills': {
                skill_id: meta.to_dict() 
                for skill_id, meta in self.registry.items()
            }
        }
        with open(self.metadata_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def register_skill(self, skill: Skill) -> bool:
        """
        注册新技能到库中
        
        Args:
            skill: 技能实例
        
        Returns:
            是否注册成功
        """
        skill_id = skill.metadata.skill_id
        
        # 保存技能代码
        skill_file = self.library_path / f"{skill_id}.py"
        
        # 更新注册表
        self.registry[skill_id] = skill.metadata
        self.skills[skill_id] = skill
        self._save_registry()
        
        return True
    
    def save_skill_code(self, skill_id: str, code: str) -> bool:
        """
        保存技能代码
        
        Args:
            skill_id: 技能ID
            code: Python代码
        
        Returns:
            是否保存成功
        """
        skill_file = self.library_path / f"{skill_id}.py"
        with open(skill_file, 'w', encoding='utf-8') as f:
            f.write(code)
        return True
    
    def load_skill(self, skill_id: str) -> Optional[Skill]:
        """
        从库中加载技能
        
        Args:
            skill_id: 技能ID
        
        Returns:
            技能实例，如果不存在返回None
        """
        if skill_id in self.skills:
            return self.skills[skill_id]
        
        skill_file = self.library_path / f"{skill_id}.py"
        if not skill_file.exists():
            return None
        
        # 动态加载技能模块
        try:
            spec = importlib.util.spec_from_file_location(skill_id, skill_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # 查找Skill子类
            for name, obj in vars(module).items():
                if (isinstance(obj, type) and 
                    issubclass(obj, Skill) and 
                    obj is not Skill):
                    
                    # 恢复元数据
                    metadata = self.registry.get(skill_id)
                    skill = obj(metadata)
                    self.skills[skill_id] = skill
                    return skill
                    
        except Exception as e:
            print(f"加载技能 {skill_id} 失败: {e}")
        
        return None
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """获取技能（先从缓存，再从文件）"""
        return self.skills.get(skill_id) or self.load_skill(skill_id)

    def reload_skill(self, skill_id: str) -> Optional['Skill']:
        """
        热重载技能 - 清除所有缓存后从磁盘重新加载

        用于技能代码被 AI 修复或手动编辑后，在不重启服务器的情况下
        让新代码立即生效。

        Args:
            skill_id: 技能ID

        Returns:
            重新加载的技能实例，失败返回 None
        """
        import sys
        import logging
        logger = logging.getLogger('prokaryote.skill_library')

        # 1. 清除实例缓存
        self.skills.pop(skill_id, None)

        # 2. 清除 sys.modules 中的旧模块缓存
        #    importlib.util 加载时可能用 skill_id 作为模块名
        modules_to_remove = [
            key for key in sys.modules
            if key == skill_id or key.endswith(f'.{skill_id}')
        ]
        for mod_key in modules_to_remove:
            del sys.modules[mod_key]

        # 3. 从磁盘重新加载
        reloaded = self.load_skill(skill_id)
        if reloaded:
            logger.info(f"✅ 技能热重载成功: {skill_id}")
        else:
            logger.warning(f"❌ 技能热重载失败: {skill_id}")

        return reloaded

    def list_skills(self, domain: str = None, tier: str = None) -> List[SkillMetadata]:
        """
        列出技能
        
        Args:
            domain: 按领域过滤
            tier: 按层级过滤
        
        Returns:
            技能元数据列表
        """
        skills = list(self.registry.values())
        
        if domain:
            skills = [s for s in skills if s.domain == domain]
        if tier:
            skills = [s for s in skills if s.tier == tier]
        
        return skills
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取技能库统计"""
        skills = list(self.registry.values())
        
        tier_counts = {}
        domain_counts = {}
        total_executions = 0
        
        for skill in skills:
            tier_counts[skill.tier] = tier_counts.get(skill.tier, 0) + 1
            domain_counts[skill.domain] = domain_counts.get(skill.domain, 0) + 1
            total_executions += skill.total_executions
        
        return {
            'total_skills': len(skills),
            'by_tier': tier_counts,
            'by_domain': domain_counts,
            'total_executions': total_executions
        }
    
    def upgrade_skill(self, skill_id: str, new_code: str = None) -> bool:
        """
        升级技能
        
        Args:
            skill_id: 技能ID
            new_code: 新代码（可选）
        
        Returns:
            是否升级成功
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return False
        
        # 升级技能
        skill.upgrade(new_code)
        
        # 如果有新代码，保存
        if new_code:
            self.save_skill_code(skill_id, new_code)
        
        # 更新注册表
        self.registry[skill_id] = skill.metadata
        self._save_registry()
        
        return True
    
    def execute_skill(self, skill_id: str, **kwargs) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            skill_id: 技能ID
            **kwargs: 技能参数
        
        Returns:
            执行结果
        """
        skill = self.get_skill(skill_id)
        if not skill:
            return {
                'success': False,
                'error': f'技能不存在: {skill_id}'
            }
        
        # 验证输入
        if not skill.validate_input(**kwargs):
            return {
                'success': False,
                'error': '输入参数无效'
            }
        
        # 执行
        import time
        start_time = time.time()
        
        try:
            result = skill.execute(**kwargs)
            success = result.get('success', False)
        except Exception as e:
            result = {'success': False, 'error': str(e)}
            success = False
        
        result['execution_time'] = time.time() - start_time
        
        # 记录执行
        skill.record_execution(success)
        self.registry[skill_id] = skill.metadata
        self._save_registry()
        
        return result

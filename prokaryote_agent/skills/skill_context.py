"""
技能执行上下文 - 为技能提供统一的能力访问接口

每个技能执行时都会获得一个SkillContext，通过它可以：
1. 访问知识库（查询/存储）
2. 调用其他技能
3. 保存产出物（自动存入Knowledge）
4. 记录日志

设计原则：
- 所有技能共享同一套知识库
- 技能之间可以互相调用，形成技能链
- 所有产出物都有迹可循，存储在Knowledge目录
"""

import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, List, Optional, TYPE_CHECKING
import json

if TYPE_CHECKING:
    from .skill_base import SkillLibrary


class SkillContext:
    """
    技能执行上下文

    为技能执行提供：
    - 知识库访问
    - 技能互调用
    - 产出物存储
    - 执行日志
    """

    def __init__(
        self,
        skill_id: str,
        skill_library: 'SkillLibrary' = None,
        domain: str = 'general',
        execution_id: str = None
    ):
        """
        初始化执行上下文

        Args:
            skill_id: 当前技能ID
            skill_library: 技能库实例（用于调用其他技能）
            domain: 领域
            execution_id: 执行ID（用于追踪）
        """
        self.skill_id = skill_id
        self.skill_library = skill_library
        self.domain = domain
        self.execution_id = execution_id or datetime.now().strftime('%Y%m%d_%H%M%S_%f')
        self.logger = logging.getLogger(f"skill.{skill_id}")

        # 执行追踪
        self._called_skills: List[str] = []  # 调用过的技能
        self._outputs: List[Dict[str, Any]] = []  # 产出物记录
        self._knowledge_queries: int = 0  # 知识库查询次数
        self._knowledge_stores: int = 0  # 知识库存储次数

        # 延迟加载知识库
        self._knowledge_base = None

    @property
    def knowledge(self):
        """获取知识库实例（延迟加载）"""
        if self._knowledge_base is None:
            from prokaryote_agent.knowledge import get_knowledge_base
            self._knowledge_base = get_knowledge_base()
        return self._knowledge_base

    # ==================== 知识库访问 ====================

    def search_knowledge(
        self,
        query: str,
        category: str = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        搜索知识库

        Args:
            query: 搜索关键词
            category: 知识类别（可选）
            limit: 返回数量限制

        Returns:
            知识条目列表
        """
        from prokaryote_agent.knowledge import search_knowledge

        self._knowledge_queries += 1
        self.logger.debug(f"搜索知识库: {query}")

        results = search_knowledge(
            query=query,
            domain=self.domain,
            category=category,
            limit=limit
        )

        return results

    def store_knowledge(
        self,
        title: str,
        content: str,
        category: str = 'general',
        source: str = None,
        tags: List[str] = None,
        metadata: Dict[str, Any] = None
    ) -> bool:
        """
        存储知识到知识库

        Args:
            title: 知识标题
            content: 知识内容
            category: 知识类别
            source: 来源
            tags: 标签列表
            metadata: 额外元数据

        Returns:
            是否存储成功
        """
        from prokaryote_agent.knowledge import store_knowledge

        try:
            # 添加来源信息
            full_metadata = metadata or {}
            full_metadata['produced_by'] = self.skill_id
            full_metadata['execution_id'] = self.execution_id
            full_metadata['stored_at'] = datetime.now().isoformat()

            store_knowledge(
                title=title,
                content=content,
                domain=self.domain,
                category=category,
                source=source or f"skill:{self.skill_id}",
                tags=tags or [],
                metadata=full_metadata
            )

            self._knowledge_stores += 1
            self.logger.debug(f"存储知识: {title}")
            return True

        except Exception as e:
            self.logger.error(f"存储知识失败: {e}")
            return False

    def smart_search(
        self,
        query: str,
        category: str = None,
        use_web: bool = True,
        auto_store: bool = True
    ) -> Dict[str, Any]:
        """
        智能搜索（本地优先 + 网络补充 + 自动固化）

        Args:
            query: 搜索关键词
            category: 知识类别
            use_web: 是否使用网络搜索
            auto_store: 是否自动存储新知识

        Returns:
            搜索结果
        """
        from prokaryote_agent.knowledge import smart_search

        self._knowledge_queries += 1

        result = smart_search(
            query=query,
            domain=self.domain,
            category=category,
            use_web=use_web,
            auto_store=auto_store
        )

        if auto_store:
            self._knowledge_stores += result.get('stored', 0)

        return result

    # ==================== 技能互调用 ====================

    def call_skill(
        self,
        skill_id: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        调用另一个技能

        Args:
            skill_id: 目标技能ID
            **kwargs: 技能参数

        Returns:
            技能执行结果
        """
        if not self.skill_library:
            return {
                'success': False,
                'error': '技能库未初始化，无法调用其他技能'
            }

        skill = self.skill_library.get_skill(skill_id)
        if not skill:
            return {
                'success': False,
                'error': f'技能不存在: {skill_id}'
            }

        self._called_skills.append(skill_id)
        self.logger.info(f"调用技能: {skill_id}")

        # 为被调用的技能创建子上下文
        sub_context = SkillContext(
            skill_id=skill_id,
            skill_library=self.skill_library,
            domain=self.domain,
            execution_id=f"{self.execution_id}_{skill_id}"
        )

        # 执行技能（传入上下文）
        try:
            result = skill.execute(context=sub_context, **kwargs)

            # 合并子上下文的统计
            self._knowledge_queries += sub_context._knowledge_queries
            self._knowledge_stores += sub_context._knowledge_stores
            self._outputs.extend(sub_context._outputs)

            return result

        except TypeError:
            # 如果技能不支持context参数，直接调用
            return skill.execute(**kwargs)

    def has_skill(self, skill_id: str) -> bool:
        """检查技能是否存在"""
        if not self.skill_library:
            return False
        return self.skill_library.get_skill(skill_id) is not None

    def list_available_skills(self, domain: str = None) -> List[str]:
        """列出可用技能"""
        if not self.skill_library:
            return []

        skills = self.skill_library.list_skills(domain=domain or self.domain)
        return [s.skill_id for s in skills]

    # ==================== 产出物管理 ====================

    def save_output(
        self,
        output_type: str,
        title: str,
        content: str,
        format: str = 'markdown',
        category: str = 'outputs',
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        保存产出物到Knowledge目录

        Args:
            output_type: 产出物类型（document/analysis/report/draft等）
            title: 产出物标题
            content: 产出物内容
            format: 格式（markdown/json/text）
            category: 存储类别
            metadata: 额外元数据

        Returns:
            保存路径
        """
        # 构建保存路径
        base_path = Path("prokaryote_agent/knowledge") / self.domain / category
        base_path.mkdir(parents=True, exist_ok=True)

        # 生成文件名
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = "".join(c if c.isalnum() or c in '-_' else '_' for c in title[:30])

        ext = {'markdown': 'md', 'json': 'json', 'text': 'txt'}.get(format, 'md')
        filename = f"{output_type}_{safe_title}_{timestamp}.{ext}"
        filepath = base_path / filename

        # 构建内容
        if format == 'markdown':
            # 添加YAML前言
            frontmatter = {
                'title': title,
                'type': output_type,
                'produced_by': self.skill_id,
                'execution_id': self.execution_id,
                'created_at': datetime.now().isoformat(),
                'domain': self.domain,
                **(metadata or {})
            }

            yaml_header = "---\n"
            for key, value in frontmatter.items():
                if isinstance(value, (list, dict)):
                    yaml_header += f"{key}: {json.dumps(value, ensure_ascii=False)}\n"
                else:
                    yaml_header += f"{key}: {value}\n"
            yaml_header += "---\n\n"

            full_content = yaml_header + f"# {title}\n\n{content}"

        elif format == 'json':
            full_content = json.dumps({
                'title': title,
                'type': output_type,
                'content': content,
                'metadata': {
                    'produced_by': self.skill_id,
                    'execution_id': self.execution_id,
                    'created_at': datetime.now().isoformat(),
                    **(metadata or {})
                }
            }, ensure_ascii=False, indent=2)
        else:
            full_content = f"[{output_type}] {title}\n" + "=" * 50 + f"\n\n{content}"

        # 保存文件
        filepath.write_text(full_content, encoding='utf-8')

        # 记录产出物
        output_record = {
            'type': output_type,
            'title': title,
            'path': str(filepath),
            'format': format,
            'size': len(content),
            'created_at': datetime.now().isoformat()
        }
        self._outputs.append(output_record)

        self.logger.info(f"产出物已保存: {filepath}")
        return str(filepath)

    def get_outputs(self) -> List[Dict[str, Any]]:
        """获取所有产出物记录"""
        return self._outputs.copy()

    # ==================== 执行统计 ====================

    def get_stats(self) -> Dict[str, Any]:
        """获取执行统计"""
        return {
            'skill_id': self.skill_id,
            'execution_id': self.execution_id,
            'domain': self.domain,
            'called_skills': self._called_skills,
            'knowledge_queries': self._knowledge_queries,
            'knowledge_stores': self._knowledge_stores,
            'outputs_count': len(self._outputs),
            'outputs': self._outputs
        }

    def log(self, message: str, level: str = 'info'):
        """记录日志"""
        log_func = getattr(self.logger, level, self.logger.info)
        log_func(f"[{self.skill_id}] {message}")


# 全局上下文管理（用于获取当前执行上下文）
_current_context: Optional[SkillContext] = None


def get_current_context() -> Optional[SkillContext]:
    """获取当前执行上下文"""
    return _current_context


def set_current_context(context: SkillContext):
    """设置当前执行上下文"""
    global _current_context
    _current_context = context


def clear_current_context():
    """清除当前执行上下文"""
    global _current_context
    _current_context = None

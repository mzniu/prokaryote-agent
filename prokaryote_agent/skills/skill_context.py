"""
技能执行上下文 - 为技能提供统一的能力访问接口

每个技能执行时都会获得一个SkillContext，通过它可以：
1. 访问知识库（查询/存储）
2. 调用其他技能
3. 保存产出物（自动存入Knowledge）
4. 记录日志
5. 调用AI大模型能力（文本生成/分析/推理）
6. 联网搜索（网页搜索/深度搜索/URL抓取）
7. 文件读写操作

设计原则：
- 所有技能共享同一套知识库
- 技能之间可以互相调用，形成技能链
- 所有产出物都有迹可循，存储在Knowledge目录
- 基础能力（AI/联网/文件）统一通过context访问，避免技能代码直接import
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
    - AI大模型调用（call_ai）
    - 联网搜索（web_search / deep_search / fetch_url）
    - 文件读写（read_file / write_file / list_files）
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

        # 延迟加载AI适配器
        self._ai_adapter = None

        # 延迟加载web工具
        self._web_searcher = None

    @property
    def knowledge(self):
        """获取知识库实例（延迟加载）"""
        if self._knowledge_base is None:
            from prokaryote_agent.knowledge import get_knowledge_base
            self._knowledge_base = get_knowledge_base()
        return self._knowledge_base

    @property
    def ai(self):
        """获取AI适配器实例（延迟加载）"""
        if self._ai_adapter is None:
            from prokaryote_agent.ai_adapter import AIAdapter
            self._ai_adapter = AIAdapter()
        return self._ai_adapter

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

        kwargs = dict(query=query, domain=self.domain, limit=limit)
        # category is accepted by SkillContext API but the underlying
        # search_knowledge() doesn't support it yet – pass only when
        # the function signature allows it.
        import inspect
        sig = inspect.signature(search_knowledge)
        if 'category' in sig.parameters and category:
            kwargs['category'] = category

        results = search_knowledge(**kwargs)

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

    # ==================== AI 大模型能力 ====================

    def call_ai(
        self,
        prompt: str,
        system_prompt: str = None,
        temperature: float = None,
        max_tokens: int = None
    ) -> Dict[str, Any]:
        """
        调用AI大模型

        这是技能使用AI能力的统一入口。可用于：
        - 文本生成、摘要、翻译
        - 内容分析、推理、判断
        - 格式转换、结构化提取

        Args:
            prompt: 用户提示词
            system_prompt: 系统提示词（可选）
            temperature: 温度参数（可选，覆盖默认值）
            max_tokens: 最大Token数（可选，覆盖默认值）

        Returns:
            {"success": bool, "content": str, "error": str}
        """
        self.logger.info(f"调用AI: {prompt[:80]}...")

        try:
            adapter = self.ai

            # 暂存并覆盖配置(如果有自定义参数)
            orig_temp = adapter.config.temperature
            orig_tokens = adapter.config.max_tokens
            if temperature is not None:
                adapter.config.temperature = temperature
            if max_tokens is not None:
                adapter.config.max_tokens = max_tokens

            try:
                if system_prompt:
                    # 拼接system prompt到prompt前面
                    full_prompt = f"[系统指令] {system_prompt}\n\n{prompt}"
                    result = adapter._call_ai(full_prompt)
                else:
                    result = adapter._call_ai(prompt)
            finally:
                # 恢复原始配置
                adapter.config.temperature = orig_temp
                adapter.config.max_tokens = orig_tokens

            return result

        except Exception as e:
            self.logger.error(f"AI调用失败: {e}")
            return {
                'success': False,
                'content': '',
                'error': str(e)
            }

    # ==================== 联网搜索能力 ====================

    def web_search(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        网页搜索

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果列表 [{"title": str, "url": str, "snippet": str}, ...]
        """
        self.logger.info(f"联网搜索: {query}")

        try:
            from prokaryote_agent.skills.web_tools import web_search
            return web_search(query, max_results=max_results)
        except Exception as e:
            self.logger.error(f"联网搜索失败: {e}")
            return []

    def deep_search(
        self,
        query: str,
        max_results: int = 5,
        fetch_content: bool = True
    ) -> List[Dict[str, Any]]:
        """
        深度搜索 - 搜索并抓取网页内容

        Args:
            query: 搜索关键词
            max_results: 最大结果数
            fetch_content: 是否抓取网页正文内容

        Returns:
            搜索结果列表（含content字段）
        """
        self.logger.info(f"深度搜索: {query}")

        try:
            from prokaryote_agent.skills.web_tools import deep_search
            return deep_search(
                query, max_results=max_results,
                fetch_content=fetch_content
            )
        except Exception as e:
            self.logger.error(f"深度搜索失败: {e}")
            return []

    def fetch_url(self, url: str) -> Dict[str, Any]:
        """
        抓取指定URL的网页内容

        Args:
            url: 目标网址

        Returns:
            {"success": bool, "content": str, "title": str, "error": str}
        """
        self.logger.info(f"抓取URL: {url}")

        try:
            from prokaryote_agent.skills.web_tools import fetch_webpage
            return fetch_webpage(url)
        except Exception as e:
            self.logger.error(f"URL抓取失败: {e}")
            return {'success': False, 'content': '', 'error': str(e)}

    def deep_search_by_categories(
        self,
        query: str,
        categories: Dict[str, str],
        category_filter: str = 'all',
        max_results: int = 5
    ) -> List[Dict[str, Any]]:
        """
        分类深度搜索

        Args:
            query: 搜索关键词
            categories: 类别配置 {类别名: 附加关键词}
            category_filter: 限定类别，'all' 搜索所有类别
            max_results: 每个类别的最大结果数

        Returns:
            搜索结果列表
        """
        self.logger.info(f"分类深度搜索: {query} (类别: {list(categories.keys())})")

        try:
            from prokaryote_agent.skills.web_tools import deep_search_by_categories
            return deep_search_by_categories(
                query, categories=categories,
                category_filter=category_filter,
                max_results=max_results
            )
        except Exception as e:
            self.logger.error(f"分类深度搜索失败: {e}")
            return []

    # ==================== 文件读写能力 ====================

    def read_file(
        self,
        path: str,
        encoding: str = 'utf-8'
    ) -> Dict[str, Any]:
        """
        读取文件内容

        安全限制: 只允许读取 prokaryote_agent/ 目录下的文件

        Args:
            path: 文件路径（相对于项目根目录或绝对路径）
            encoding: 编码，默认utf-8

        Returns:
            {"success": bool, "content": str, "path": str, "error": str}
        """
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path

            # 安全检查：只允许在工作目录下读取
            cwd = Path.cwd()
            try:
                file_path.resolve().relative_to(cwd.resolve())
            except ValueError:
                return {
                    'success': False,
                    'content': '',
                    'path': str(file_path),
                    'error': '安全限制：不允许读取工作目录之外的文件'
                }

            if not file_path.exists():
                return {
                    'success': False,
                    'content': '',
                    'path': str(file_path),
                    'error': f'文件不存在: {file_path}'
                }

            content = file_path.read_text(encoding=encoding)
            self.logger.debug(f"读取文件: {file_path} ({len(content)} 字符)")
            return {
                'success': True,
                'content': content,
                'path': str(file_path),
                'size': len(content)
            }

        except Exception as e:
            self.logger.error(f"读取文件失败: {e}")
            return {
                'success': False,
                'content': '',
                'path': str(path),
                'error': str(e)
            }

    def write_file(
        self,
        path: str,
        content: str,
        encoding: str = 'utf-8',
        mkdir: bool = True
    ) -> Dict[str, Any]:
        """
        写入文件

        安全限制: 只允许写入 prokaryote_agent/ 目录下的文件

        Args:
            path: 文件路径（相对于项目根目录或绝对路径）
            content: 文件内容
            encoding: 编码
            mkdir: 是否自动创建父目录

        Returns:
            {"success": bool, "path": str, "size": int, "error": str}
        """
        try:
            file_path = Path(path)
            if not file_path.is_absolute():
                file_path = Path.cwd() / file_path

            # 安全检查
            cwd = Path.cwd()
            try:
                file_path.resolve().relative_to(cwd.resolve())
            except ValueError:
                return {
                    'success': False,
                    'path': str(file_path),
                    'error': '安全限制：不允许写入工作目录之外的文件'
                }

            if mkdir:
                file_path.parent.mkdir(parents=True, exist_ok=True)

            file_path.write_text(content, encoding=encoding)
            self.logger.info(f"写入文件: {file_path} ({len(content)} 字符)")
            return {
                'success': True,
                'path': str(file_path),
                'size': len(content)
            }

        except Exception as e:
            self.logger.error(f"写入文件失败: {e}")
            return {
                'success': False,
                'path': str(path),
                'error': str(e)
            }

    def list_files(
        self,
        directory: str = '.',
        pattern: str = '*',
        recursive: bool = False
    ) -> List[str]:
        """
        列出目录下的文件

        Args:
            directory: 目录路径
            pattern: 文件匹配模式（如 '*.json', '*.md'）
            recursive: 是否递归子目录

        Returns:
            文件路径列表
        """
        try:
            dir_path = Path(directory)
            if not dir_path.is_absolute():
                dir_path = Path.cwd() / dir_path

            if not dir_path.exists():
                return []

            if recursive:
                files = list(dir_path.rglob(pattern))
            else:
                files = list(dir_path.glob(pattern))

            return [str(f) for f in files if f.is_file()]

        except Exception as e:
            self.logger.error(f"列出文件失败: {e}")
            return []

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

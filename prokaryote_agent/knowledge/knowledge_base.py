"""
Markdown 知识库 - 使用 Markdown 文件存储和检索知识

V0.1 特性:
- Markdown 文件存储，人类可读
- YAML frontmatter 元数据
- 简单关键词搜索
- 自动索引管理
- LLM 友好格式
"""

import os
import re
import hashlib
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


@dataclass
class Knowledge:
    """知识条目"""
    id: str                          # 唯一标识
    title: str                       # 标题
    content: str                     # 内容
    domain: str                      # 领域 (legal, software_dev, ...)
    category: str                    # 类别 (laws, cases, errors, ...)
    
    # 元数据
    keywords: List[str] = field(default_factory=list)  # 关键词
    source_url: str = ""             # 来源 URL
    source_type: str = "web_search"  # 来源类型
    acquired_by: str = ""            # 获取该知识的技能
    quality_score: float = 0.5       # 质量评分 0-1
    
    # 时间戳
    created_at: str = ""
    updated_at: str = ""
    
    # 使用统计
    access_count: int = 0
    last_accessed: str = ""
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.updated_at:
            self.updated_at = self.created_at


class MarkdownKnowledge:
    """
    Markdown 知识库管理器
    
    目录结构:
    knowledge/
    ├── _index.md          # 知识库索引
    ├── legal/             # 法律领域
    │   ├── laws/          # 法规
    │   ├── cases/         # 判例
    │   └── concepts/      # 概念
    └── software_dev/      # 软件开发领域
        ├── errors/        # 错误解决
        └── apis/          # API 文档
    """
    
    def __init__(self, base_path: str = "prokaryote_agent/knowledge"):
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger(__name__)
        
        # 内存缓存（加速搜索）
        self._cache: Dict[str, Knowledge] = {}
        self._cache_loaded = False
    
    def store(self, knowledge: Knowledge) -> str:
        """
        存储知识到 Markdown 文件
        
        Args:
            knowledge: 知识对象
            
        Returns:
            存储的文件路径
        """
        # 生成文件名（安全处理）
        safe_title = self._safe_filename(knowledge.title)
        file_path = self.base_path / knowledge.domain / knowledge.category / f"{safe_title}.md"
        
        # 检查是否已存在（去重）
        if file_path.exists():
            existing = self._read_knowledge_file(file_path)
            if existing and self._is_similar(existing, knowledge):
                self.logger.info(f"知识已存在，跳过: {knowledge.title}")
                # 更新访问统计
                self._update_access(file_path)
                return str(file_path)
        
        # 确保目录存在
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 生成 Markdown 内容
        md_content = self._generate_markdown(knowledge)
        
        # 写入文件
        file_path.write_text(md_content, encoding='utf-8')
        self.logger.info(f"知识已存储: {file_path}")
        
        # 更新缓存
        self._cache[knowledge.id] = knowledge
        
        # 更新索引
        self._update_index()
        
        return str(file_path)
    
    def store_from_search(self, title: str, content: str, domain: str, 
                          category: str, source_url: str = "",
                          acquired_by: str = "", keywords: List[str] = None) -> str:
        """
        从搜索结果存储知识（便捷方法）
        
        Args:
            title: 标题
            content: 内容
            domain: 领域
            category: 类别
            source_url: 来源URL
            acquired_by: 获取技能ID
            keywords: 关键词列表
        """
        # 生成唯一ID
        content_hash = hashlib.md5(f"{title}{content}".encode()).hexdigest()[:8]
        knowledge_id = f"kb_{domain}_{content_hash}"
        
        # 自动提取关键词
        if keywords is None:
            keywords = self._extract_keywords(title + " " + content)
        
        knowledge = Knowledge(
            id=knowledge_id,
            title=title,
            content=content,
            domain=domain,
            category=category,
            keywords=keywords,
            source_url=source_url,
            acquired_by=acquired_by,
            source_type="web_search"
        )
        
        return self.store(knowledge)
    
    def search(self, query: str, domain: str = None, 
               category: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        搜索知识库
        
        Args:
            query: 搜索查询
            domain: 限定领域（可选）
            category: 限定类别（可选）
            limit: 最大返回数量
            
        Returns:
            匹配的知识列表
        """
        results = []
        query_lower = query.lower()
        query_words = set(query_lower.split())
        
        # 确定搜索路径
        if domain:
            if category:
                search_path = self.base_path / domain / category
            else:
                search_path = self.base_path / domain
        else:
            search_path = self.base_path
        
        if not search_path.exists():
            return []
        
        # 遍历所有 Markdown 文件
        for md_file in search_path.rglob("*.md"):
            # 跳过索引文件
            if md_file.name.startswith("_"):
                continue
            
            try:
                content = md_file.read_text(encoding='utf-8')
                content_lower = content.lower()
                
                # 计算相关度分数
                score = 0
                
                # 标题匹配（权重高）
                title = self._extract_title(content)
                if query_lower in title.lower():
                    score += 10
                
                # 关键词匹配
                keywords = self._extract_frontmatter_field(content, 'keywords')
                if keywords:
                    for kw in keywords:
                        if kw.lower() in query_lower or query_lower in kw.lower():
                            score += 5
                
                # 内容匹配
                for word in query_words:
                    if word in content_lower:
                        score += 1
                
                # 完整查询匹配
                if query_lower in content_lower:
                    score += 3
                
                if score > 0:
                    results.append({
                        'path': str(md_file),
                        'title': title,
                        'domain': self._get_domain_from_path(md_file),
                        'category': self._get_category_from_path(md_file),
                        'score': score,
                        'snippet': self._extract_snippet(content, query)
                    })
                    
            except Exception as e:
                self.logger.warning(f"读取文件失败 {md_file}: {e}")
        
        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return results[:limit]
    
    def get(self, path_or_id: str) -> Optional[Knowledge]:
        """
        获取知识内容
        
        Args:
            path_or_id: 文件路径或知识ID
        """
        # 如果是ID，先查缓存
        if path_or_id.startswith("kb_"):
            if path_or_id in self._cache:
                return self._cache[path_or_id]
            # 搜索文件
            for md_file in self.base_path.rglob("*.md"):
                if md_file.name.startswith("_"):
                    continue
                knowledge = self._read_knowledge_file(md_file)
                if knowledge and knowledge.id == path_or_id:
                    self._cache[path_or_id] = knowledge
                    return knowledge
            return None
        
        # 如果是路径
        file_path = Path(path_or_id)
        if not file_path.exists():
            file_path = self.base_path / path_or_id
        
        if file_path.exists():
            return self._read_knowledge_file(file_path)
        
        return None
    
    def get_stats(self, domain: str = None) -> Dict[str, Any]:
        """
        获取知识库统计信息
        """
        stats = {
            'total': 0,
            'by_domain': {},
            'by_category': {},
            'recent': []
        }
        
        search_path = self.base_path / domain if domain else self.base_path
        
        if not search_path.exists():
            return stats
        
        files_with_time = []
        
        for md_file in search_path.rglob("*.md"):
            if md_file.name.startswith("_"):
                continue
            
            stats['total'] += 1
            
            # 按领域统计
            file_domain = self._get_domain_from_path(md_file)
            stats['by_domain'][file_domain] = stats['by_domain'].get(file_domain, 0) + 1
            
            # 按类别统计
            file_category = self._get_category_from_path(md_file)
            key = f"{file_domain}/{file_category}"
            stats['by_category'][key] = stats['by_category'].get(key, 0) + 1
            
            # 记录文件时间
            mtime = md_file.stat().st_mtime
            files_with_time.append((md_file, mtime))
        
        # 最近文件
        files_with_time.sort(key=lambda x: x[1], reverse=True)
        for md_file, _ in files_with_time[:5]:
            content = md_file.read_text(encoding='utf-8')
            stats['recent'].append({
                'path': str(md_file.relative_to(self.base_path)),
                'title': self._extract_title(content)
            })
        
        return stats
    
    def _generate_markdown(self, knowledge: Knowledge) -> str:
        """生成 Markdown 文件内容"""
        # YAML frontmatter
        frontmatter_lines = [
            "---",
            f"id: {knowledge.id}",
            f"title: \"{knowledge.title}\"",
            f"domain: {knowledge.domain}",
            f"category: {knowledge.category}",
            f"keywords: {knowledge.keywords}",
            f"source_url: \"{knowledge.source_url}\"",
            f"source_type: {knowledge.source_type}",
            f"acquired_by: {knowledge.acquired_by}",
            f"quality_score: {knowledge.quality_score}",
            f"created_at: {knowledge.created_at}",
            f"updated_at: {knowledge.updated_at}",
            f"access_count: {knowledge.access_count}",
            "---",
            ""
        ]
        
        # 正文内容
        content_lines = [
            f"# {knowledge.title}",
            "",
            "## 来源信息",
            "",
            f"- **获取时间**: {knowledge.created_at[:10]}",
            f"- **获取技能**: {knowledge.acquired_by or '手动添加'}",
            f"- **原始链接**: {knowledge.source_url or '无'}",
            "",
            "## 内容",
            "",
            knowledge.content,
            "",
            "## 关键词",
            "",
            ", ".join(knowledge.keywords) if knowledge.keywords else "无",
            ""
        ]
        
        return "\n".join(frontmatter_lines + content_lines)
    
    def _read_knowledge_file(self, file_path: Path) -> Optional[Knowledge]:
        """从文件读取知识"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # 解析 frontmatter
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = parts[1].strip()
                    body = parts[2].strip()
                    
                    # 简单解析 YAML
                    meta = {}
                    for line in frontmatter.split("\n"):
                        if ":" in line:
                            key, value = line.split(":", 1)
                            key = key.strip()
                            value = value.strip().strip('"\'')
                            
                            # 处理列表
                            if value.startswith("[") and value.endswith("]"):
                                value = [v.strip().strip('"\'') 
                                        for v in value[1:-1].split(",") if v.strip()]
                            # 处理数字
                            elif value.replace(".", "").isdigit():
                                value = float(value) if "." in value else int(value)
                            
                            meta[key] = value
                    
                    return Knowledge(
                        id=meta.get('id', ''),
                        title=meta.get('title', ''),
                        content=body,
                        domain=meta.get('domain', ''),
                        category=meta.get('category', ''),
                        keywords=meta.get('keywords', []),
                        source_url=meta.get('source_url', ''),
                        source_type=meta.get('source_type', ''),
                        acquired_by=meta.get('acquired_by', ''),
                        quality_score=meta.get('quality_score', 0.5),
                        created_at=meta.get('created_at', ''),
                        updated_at=meta.get('updated_at', ''),
                        access_count=meta.get('access_count', 0)
                    )
        except Exception as e:
            self.logger.warning(f"解析知识文件失败 {file_path}: {e}")
        
        return None
    
    def _update_index(self):
        """更新索引文件"""
        stats = self.get_stats()
        
        index_lines = [
            "# 知识库索引",
            "",
            f"> 更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"> 总知识数: {stats['total']}",
            "",
            "## 按领域统计",
            "",
            "| 领域 | 数量 |",
            "|------|------|",
        ]
        
        for domain, count in stats['by_domain'].items():
            index_lines.append(f"| {domain} | {count} |")
        
        index_lines.extend([
            "",
            "## 最近获取",
            ""
        ])
        
        for i, item in enumerate(stats['recent'], 1):
            index_lines.append(f"{i}. [{item['title']}]({item['path']})")
        
        index_content = "\n".join(index_lines)
        index_path = self.base_path / "_index.md"
        index_path.write_text(index_content, encoding='utf-8')
    
    def _safe_filename(self, title: str) -> str:
        """生成安全的文件名"""
        # 移除不安全字符
        safe = re.sub(r'[<>:"/\\|?*]', '', title)
        # 替换空格
        safe = safe.replace(' ', '_')
        # 限制长度
        if len(safe) > 50:
            safe = safe[:50]
        # 确保不为空
        if not safe:
            safe = hashlib.md5(title.encode()).hexdigest()[:8]
        return safe
    
    def _extract_keywords(self, text: str, max_keywords: int = 5) -> List[str]:
        """从文本提取关键词"""
        # 简单的关键词提取（中文分词简化版）
        # 提取2-4字的中文词
        chinese_words = re.findall(r'[\u4e00-\u9fa5]{2,4}', text)
        
        # 统计词频
        word_count = {}
        for word in chinese_words:
            word_count[word] = word_count.get(word, 0) + 1
        
        # 按词频排序
        sorted_words = sorted(word_count.items(), key=lambda x: x[1], reverse=True)
        
        # 过滤停用词
        stopwords = {'的', '是', '在', '和', '与', '了', '有', '被', '对', '等', '为', '以'}
        keywords = [w for w, _ in sorted_words if w not in stopwords]
        
        return keywords[:max_keywords]
    
    def _extract_title(self, content: str) -> str:
        """从内容提取标题"""
        # 先尝试从 frontmatter 提取
        title = self._extract_frontmatter_field(content, 'title')
        if title:
            return title
        
        # 尝试从 # 标题提取
        match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        
        # 返回前30个字符
        return content[:30].replace('\n', ' ').strip() + "..."
    
    def _extract_frontmatter_field(self, content: str, field: str) -> Any:
        """从 frontmatter 提取字段"""
        if not content.startswith("---"):
            return None
        
        parts = content.split("---", 2)
        if len(parts) < 3:
            return None
        
        frontmatter = parts[1]
        for line in frontmatter.split("\n"):
            if line.startswith(f"{field}:"):
                value = line.split(":", 1)[1].strip().strip('"\'')
                # 处理列表
                if value.startswith("["):
                    return [v.strip().strip('"\'') 
                           for v in value[1:-1].split(",") if v.strip()]
                return value
        
        return None
    
    def _extract_snippet(self, content: str, query: str, context_chars: int = 100) -> str:
        """提取包含查询词的片段"""
        # 跳过 frontmatter
        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                content = parts[2]
        
        query_lower = query.lower()
        content_lower = content.lower()
        
        pos = content_lower.find(query_lower)
        if pos == -1:
            # 尝试查找查询词的一部分
            for word in query_lower.split():
                pos = content_lower.find(word)
                if pos != -1:
                    break
        
        if pos == -1:
            return content[:context_chars * 2] + "..."
        
        start = max(0, pos - context_chars)
        end = min(len(content), pos + len(query) + context_chars)
        
        snippet = content[start:end]
        if start > 0:
            snippet = "..." + snippet
        if end < len(content):
            snippet = snippet + "..."
        
        return snippet.replace('\n', ' ').strip()
    
    def _get_domain_from_path(self, file_path: Path) -> str:
        """从路径获取领域"""
        try:
            rel_path = file_path.relative_to(self.base_path)
            parts = rel_path.parts
            if len(parts) >= 1:
                return parts[0]
        except ValueError:
            pass
        return "unknown"
    
    def _get_category_from_path(self, file_path: Path) -> str:
        """从路径获取类别"""
        try:
            rel_path = file_path.relative_to(self.base_path)
            parts = rel_path.parts
            if len(parts) >= 2:
                return parts[1]
        except ValueError:
            pass
        return "general"
    
    def _is_similar(self, existing: Knowledge, new: Knowledge) -> bool:
        """检查两条知识是否相似（去重用）"""
        # 标题完全相同
        if existing.title == new.title:
            return True
        # URL 相同
        if existing.source_url and existing.source_url == new.source_url:
            return True
        return False
    
    def _update_access(self, file_path: Path):
        """更新访问统计"""
        try:
            content = file_path.read_text(encoding='utf-8')
            
            # 更新 access_count
            content = re.sub(
                r'access_count: (\d+)',
                lambda m: f'access_count: {int(m.group(1)) + 1}',
                content
            )
            
            # 更新 last_accessed
            now = datetime.now().isoformat()
            if 'last_accessed:' in content:
                content = re.sub(
                    r'last_accessed: .*',
                    f'last_accessed: {now}',
                    content
                )
            
            file_path.write_text(content, encoding='utf-8')
        except Exception as e:
            self.logger.warning(f"更新访问统计失败: {e}")


# 便捷函数
_default_kb: Optional[MarkdownKnowledge] = None

def get_knowledge_base(base_path: str = "prokaryote_agent/knowledge") -> MarkdownKnowledge:
    """获取默认知识库实例"""
    global _default_kb
    if _default_kb is None:
        _default_kb = MarkdownKnowledge(base_path)
    return _default_kb

def store_knowledge(title: str, content: str, domain: str, category: str, 
                    source_url: str = "", acquired_by: str = "") -> str:
    """存储知识（便捷函数）"""
    kb = get_knowledge_base()
    return kb.store_from_search(title, content, domain, category, source_url, acquired_by)

def search_knowledge(query: str, domain: str = None, limit: int = 10) -> List[Dict]:
    """搜索知识（便捷函数）"""
    kb = get_knowledge_base()
    return kb.search(query, domain=domain, limit=limit)

"""
网络工具模块 - 用于技能访问外部世界

提供各种网络访问能力：
- 网页搜索
- 网页内容抓取
- API 调用
- 数据提取
"""

import json
import logging
import urllib.parse
import urllib.request
import re
from typing import Dict, Any, List, Optional
from datetime import datetime


logger = logging.getLogger(__name__)


class WebSearcher:
    """网页搜索器"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def search_duckduckgo(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        使用 DuckDuckGo 搜索

        Args:
            query: 搜索关键词
            max_results: 最大结果数

        Returns:
            搜索结果列表
        """
        try:
            # DuckDuckGo HTML 搜索
            encoded_query = urllib.parse.quote(query)
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}"

            request = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                html = response.read().decode('utf-8')

            # 简单解析结果
            results = self._parse_duckduckgo_html(html, max_results)
            return results

        except Exception as e:
            logger.error(f"DuckDuckGo 搜索失败: {e}")
            return []

    def _parse_duckduckgo_html(self, html: str, max_results: int) -> List[Dict[str, Any]]:
        """解析 DuckDuckGo HTML 结果"""
        results = []

        # 匹配结果链接和标题
        pattern = r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>([^<]*)</a>'
        matches = re.findall(pattern, html)

        for url, title in matches[:max_results]:
            if url and title:
                results.append({
                    'title': title.strip(),
                    'url': url,
                    'snippet': ''
                })

        # 如果正则没匹配到，尝试另一种模式
        if not results:
            # 匹配结果块
            result_pattern = r'<div class="result[^"]*"[^>]*>.*?<a[^>]*href="([^"]*)"[^>]*>([^<]*)</a>.*?<a class="result__snippet"[^>]*>([^<]*)</a>'
            matches = re.findall(result_pattern, html, re.DOTALL)

            for url, title, snippet in matches[:max_results]:
                results.append({
                    'title': title.strip(),
                    'url': url,
                    'snippet': snippet.strip()
                })

        return results

    def search_bing(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """
        使用 Bing 搜索（备用）
        """
        try:
            encoded_query = urllib.parse.quote(query)
            url = f"https://www.bing.com/search?q={encoded_query}"

            request = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                html = response.read().decode('utf-8')

            results = self._parse_bing_html(html, max_results)
            return results

        except Exception as e:
            logger.error(f"Bing 搜索失败: {e}")
            return []

    def _parse_bing_html(self, html: str, max_results: int) -> List[Dict[str, Any]]:
        """解析 Bing HTML 结果"""
        results = []

        # 简单匹配 Bing 结果
        pattern = r'<li class="b_algo"[^>]*>.*?<a href="([^"]*)"[^>]*>([^<]*)</a>'
        matches = re.findall(pattern, html, re.DOTALL)

        for url, title in matches[:max_results]:
            results.append({
                'title': title.strip(),
                'url': url,
                'snippet': ''
            })

        return results


class WebFetcher:
    """网页内容抓取器"""

    def __init__(self, timeout: int = 10):
        self.timeout = timeout
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

    def fetch_url(self, url: str) -> Dict[str, Any]:
        """
        获取网页内容

        Args:
            url: 网页 URL

        Returns:
            {
                'success': bool,
                'content': str,
                'title': str,
                'error': str
            }
        """
        try:
            request = urllib.request.Request(url, headers=self.headers)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                html = response.read().decode('utf-8', errors='ignore')

            # 提取标题
            title_match = re.search(r'<title>([^<]*)</title>', html, re.IGNORECASE)
            title = title_match.group(1) if title_match else ''

            # 提取正文（简单方式）
            text = self._extract_text(html)

            return {
                'success': True,
                'content': text,
                'title': title,
                'url': url
            }

        except Exception as e:
            logger.error(f"获取网页失败 {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }

    def _extract_text(self, html: str) -> str:
        """从 HTML 提取纯文本"""
        # 移除 script 和 style
        html = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.IGNORECASE)
        html = re.sub(r'<style[^>]*>.*?</style>', '', html, flags=re.DOTALL | re.IGNORECASE)

        # 移除 HTML 标签
        text = re.sub(r'<[^>]+>', ' ', html)

        # 清理空白
        text = re.sub(r'\s+', ' ', text)
        text = text.strip()

        # 限制长度（增大以支持法律文档）
        if len(text) > 150000:
            text = text[:150000] + '...'

        return text


class LegalDataSource:
    """法律数据源"""

    def __init__(self):
        self.searcher = WebSearcher()
        self.fetcher = WebFetcher()

    def search_laws(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索法律法规

        使用搜索引擎搜索法律相关内容
        """
        # 添加法律关键词
        search_query = f"{query} 法律法规 site:gov.cn OR site:court.gov.cn"

        results = self.searcher.search_duckduckgo(search_query, max_results=5)

        # 如果 DuckDuckGo 失败，尝试 Bing
        if not results:
            results = self.searcher.search_bing(search_query, max_results=5)

        # 标记来源
        for r in results:
            r['source'] = 'web_search'
            r['category'] = '法律法规'

        return results

    def search_cases(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索法律案例/判例
        """
        search_query = f"{query} 判例 案例 裁判文书"

        results = self.searcher.search_duckduckgo(search_query, max_results=5)

        if not results:
            results = self.searcher.search_bing(search_query, max_results=5)

        for r in results:
            r['source'] = 'web_search'
            r['category'] = '判例案例'

        return results

    def search_interpretations(self, query: str) -> List[Dict[str, Any]]:
        """
        搜索司法解释
        """
        search_query = f"{query} 司法解释 最高人民法院"

        results = self.searcher.search_duckduckgo(search_query, max_results=5)

        if not results:
            results = self.searcher.search_bing(search_query, max_results=5)

        for r in results:
            r['source'] = 'web_search'
            r['category'] = '司法解释'

        return results


class NewsSource:
    """新闻数据源"""

    def __init__(self):
        self.searcher = WebSearcher()

    def search_news(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        """搜索新闻"""
        search_query = f"{query} 新闻"

        results = self.searcher.search_duckduckgo(search_query, max_results)

        for r in results:
            r['source'] = 'news_search'
            r['timestamp'] = datetime.now().isoformat()

        return results


class WikipediaSource:
    """维基百科数据源"""

    def __init__(self):
        self.api_url = "https://zh.wikipedia.org/w/api.php"

    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """搜索维基百科"""
        try:
            params = {
                'action': 'opensearch',
                'search': query,
                'limit': limit,
                'namespace': 0,
                'format': 'json'
            }

            url = f"{self.api_url}?{urllib.parse.urlencode(params)}"

            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            results = []
            if len(data) >= 4:
                titles, descriptions, urls = data[1], data[2], data[3]
                for i in range(len(titles)):
                    results.append({
                        'title': titles[i],
                        'snippet': descriptions[i] if i < len(descriptions) else '',
                        'url': urls[i] if i < len(urls) else '',
                        'source': 'wikipedia'
                    })

            return results

        except Exception as e:
            logger.error(f"维基百科搜索失败: {e}")
            return []

    def get_summary(self, title: str) -> Dict[str, Any]:
        """获取维基百科摘要"""
        try:
            params = {
                'action': 'query',
                'prop': 'extracts',
                'exintro': True,
                'explaintext': True,
                'titles': title,
                'format': 'json'
            }

            url = f"{self.api_url}?{urllib.parse.urlencode(params)}"

            with urllib.request.urlopen(url, timeout=10) as response:
                data = json.loads(response.read().decode('utf-8'))

            pages = data.get('query', {}).get('pages', {})
            for page_id, page in pages.items():
                if page_id != '-1':
                    return {
                        'success': True,
                        'title': page.get('title', ''),
                        'extract': page.get('extract', ''),
                        'source': 'wikipedia'
                    }

            return {'success': False, 'error': '未找到页面'}

        except Exception as e:
            logger.error(f"获取维基百科摘要失败: {e}")
            return {'success': False, 'error': str(e)}


# 便捷函数
def web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """通用网页搜索"""
    searcher = WebSearcher()
    results = searcher.search_duckduckgo(query, max_results)
    if not results:
        results = searcher.search_bing(query, max_results)
    return results


def fetch_webpage(url: str) -> Dict[str, Any]:
    """获取网页内容"""
    fetcher = WebFetcher()
    return fetcher.fetch_url(url)


def deep_search(query: str, max_results: int = 3, fetch_content: bool = True) -> List[Dict[str, Any]]:
    """
    深度搜索 - 搜索并抓取网页内容

    Args:
        query: 搜索关键词
        max_results: 最大结果数
        fetch_content: 是否抓取网页内容

    Returns:
        包含完整内容的搜索结果列表
    """
    searcher = WebSearcher()
    fetcher = WebFetcher()

    # 1. 先进行搜索
    results = searcher.search_duckduckgo(query, max_results)
    if not results:
        results = searcher.search_bing(query, max_results)

    if not fetch_content:
        return results

    # 2. 深度抓取每个结果的内容
    enriched_results = []
    for result in results:
        url = result.get('url', '')

        # 解析 DuckDuckGo 重定向链接
        if 'duckduckgo.com/l/' in url:
            # 提取真实 URL
            match = re.search(r'uddg=([^&]+)', url)
            if match:
                url = urllib.parse.unquote(match.group(1))

        if not url or not url.startswith('http'):
            enriched_results.append(result)
            continue

        try:
            # 抓取网页内容
            page = fetcher.fetch_url(url)

            if page.get('success'):
                content = page.get('content', '')
                # 提取前 80000 字符（法律文档通常较长）
                if len(content) > 80000:
                    content = content[:80000] + '...'

                result['content'] = content
                result['url'] = url  # 使用真实 URL
                result['fetched'] = True
                logger.info(f"深度抓取成功: {result.get('title', '')[:30]}... ({len(content)} 字符)")
            else:
                result['content'] = result.get('snippet', '')
                result['fetched'] = False

        except Exception as e:
            logger.warning(f"深度抓取失败 {url}: {e}")
            result['content'] = result.get('snippet', '')
            result['fetched'] = False

        enriched_results.append(result)

    return enriched_results


def search_legal(query: str, category: str = 'all') -> List[Dict[str, Any]]:
    """搜索法律资料"""
    source = LegalDataSource()

    results = []
    if category in ['all', 'laws']:
        results.extend(source.search_laws(query))
    if category in ['all', 'cases']:
        results.extend(source.search_cases(query))
    if category in ['all', 'interpretations']:
        results.extend(source.search_interpretations(query))

    return results


def search_legal_deep(query: str, category: str = 'all', max_results: int = 3) -> List[Dict[str, Any]]:
    """
    深度搜索法律资料 - 会抓取网页内容

    Args:
        query: 搜索关键词
        category: 类别 ('laws', 'cases', 'interpretations', 'all')
        max_results: 每个类别的最大结果数

    Returns:
        包含完整内容的法律资料列表
    """
    # 根据类别构建搜索词
    search_queries = []

    if category in ['all', 'laws']:
        search_queries.append((f"{query} 法律法规 法条", 'laws'))
    if category in ['all', 'cases']:
        search_queries.append((f"{query} 判例 案例 裁判", 'cases'))
    if category in ['all', 'interpretations']:
        search_queries.append((f"{query} 司法解释 最高法", 'interpretations'))

    all_results = []

    for search_query, cat in search_queries:
        results = deep_search(search_query, max_results=max_results, fetch_content=True)

        for r in results:
            r['category'] = cat
            r['source'] = 'web_search_deep'

        all_results.extend(results)

    return all_results


def search_wikipedia(query: str) -> List[Dict[str, Any]]:
    """搜索维基百科"""
    source = WikipediaSource()
    return source.search(query)

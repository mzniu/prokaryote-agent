"""
网络工具模块 - 用于技能访问外部世界

提供各种网络访问能力：
- 网页搜索
- 网页内容抓取
- API 调用
- 数据提取
"""

import gzip
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
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

    def search_duckduckgo(self, query: str, max_results: int = 10, page: int = 1) -> List[Dict[str, Any]]:
        """
        使用 DuckDuckGo 搜索

        Args:
            query: 搜索关键词
            max_results: 最大结果数
            page: 页码（1开始）

        Returns:
            搜索结果列表
        """
        try:
            # DuckDuckGo HTML 搜索，支持分页
            encoded_query = urllib.parse.quote(query)
            # DuckDuckGo 使用 s 参数做偏移，每页约30条
            offset = (page - 1) * 30
            url = f"https://html.duckduckgo.com/html/?q={encoded_query}&s={offset}"

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

    def search_multi_page(self, query: str, max_results: int = 10, max_pages: int = 2) -> List[Dict[str, Any]]:
        """
        多页搜索 - 获取更多不重复的结果

        Args:
            query: 搜索关键词
            max_results: 总共需要的最大结果数
            max_pages: 最大搜索页数

        Returns:
            去重后的搜索结果列表
        """
        all_results = []
        seen_urls = set()

        for page in range(1, max_pages + 1):
            if len(all_results) >= max_results:
                break

            results = self.search_duckduckgo(query, max_results=15, page=page)

            for r in results:
                url = r.get('url', '')
                # URL 去重
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    all_results.append(r)

                    if len(all_results) >= max_results:
                        break

            # 如果这一页没有新结果，停止翻页
            if not results:
                break

        return all_results

    def search_bing(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
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

    # 需要特殊处理的严格反爬站点
    STRICT_SITES = ['zhihu.com', 'weixin.qq.com', 'mp.weixin.qq.com']

    def __init__(self, timeout: int = 15):
        self.timeout = timeout
        # 使用完整的浏览器请求头，模拟真实浏览器访问
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0',
        }

    def _is_strict_site(self, url: str) -> bool:
        """检查是否为严格反爬站点"""
        return any(site in url for site in self.STRICT_SITES)

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
            # 为特定站点添加 Referer
            headers = self.headers.copy()
            if 'zhihu.com' in url:
                headers['Referer'] = 'https://www.zhihu.com/'
            elif 'qq.com' in url:
                headers['Referer'] = 'https://news.qq.com/'

            # 严格反爬站点跳过，返回提示信息
            if self._is_strict_site(url):
                logger.warning(f"跳过严格反爬站点: {url}")
                return {
                    'success': False,
                    'error': '该站点有严格反爬限制，建议使用其他数据源',
                    'url': url,
                    'skip_reason': 'strict_anti_crawl'
                }

            request = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(request, timeout=self.timeout) as response:
                # 处理 gzip 压缩
                data = response.read()
                encoding = response.headers.get('Content-Encoding', '')
                if encoding == 'gzip':
                    data = gzip.decompress(data)
                html = data.decode('utf-8', errors='ignore')

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

    def fetch_via_jina(self, url: str) -> Dict[str, Any]:
        """
        使用 Jina Reader API 获取网页内容（可绑过大部分反爬）

        Jina Reader 是免费的网页阅读 API，会返回干净的 Markdown 格式内容
        """
        try:
            jina_url = f"https://r.jina.ai/{url}"
            request = urllib.request.Request(jina_url, headers={
                'User-Agent': 'Mozilla/5.0',
                'Accept': 'text/plain'
            })
            with urllib.request.urlopen(request, timeout=30) as response:
                content = response.read().decode('utf-8', errors='ignore')

            # Jina 返回的是 Markdown 格式，提取标题
            lines = content.split('\n')
            title = ''
            for line in lines:
                if line.startswith('# '):
                    title = line[2:].strip()
                    break

            return {
                'success': True,
                'content': content,
                'title': title,
                'url': url,
                'via': 'jina_reader'
            }

        except Exception as e:
            logger.error(f"Jina Reader 获取失败 {url}: {e}")
            return {
                'success': False,
                'error': str(e),
                'url': url
            }

    def fetch_smart(self, url: str) -> Dict[str, Any]:
        """
        智能获取网页内容

        对于严格反爬站点，自动使用 Jina Reader
        """
        if self._is_strict_site(url):
            logger.info(f"使用 Jina Reader 获取严格站点: {url}")
            return self.fetch_via_jina(url)
        else:
            result = self.fetch_url(url)
            # 如果直接获取失败，尝试 Jina Reader
            if not result.get('success') and 'HTTP Error 403' in str(result.get('error', '')):
                logger.info(f"403 错误，切换到 Jina Reader: {url}")
                return self.fetch_via_jina(url)
            return result

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
    """
    法律数据源

    已废弃：领域特定的数据源逻辑应该放在 skills 层
    请使用 deep_search_by_categories 或在 skill 中直接实现
    """

    def __init__(self):
        logger.warning("LegalDataSource 已废弃，请在 skill 层实现领域特定逻辑")
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
    # 使用多页搜索获取更多不重复结果
    results = searcher.search_multi_page(query, max_results, max_pages=2)
    if not results:
        results = searcher.search_bing(query, max_results)
    return results


def fetch_webpage(url: str) -> Dict[str, Any]:
    """获取网页内容（自动处理反爬站点）"""
    fetcher = WebFetcher()
    return fetcher.fetch_smart(url)


def deep_search(query: str, max_results: int = 5, fetch_content: bool = True) -> List[Dict[str, Any]]:
    """
    深度搜索 - 搜索并抓取网页内容

    Args:
        query: 搜索关键词
        max_results: 最大结果数（默认5条）
        fetch_content: 是否抓取网页内容

    Returns:
        包含完整内容的搜索结果列表
    """
    searcher = WebSearcher()
    fetcher = WebFetcher()

    # 1. 使用多页搜索获取更多不重复结果
    results = searcher.search_multi_page(query, max_results, max_pages=2)
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
            # 抓取网页内容（自动处理反爬站点）
            page = fetcher.fetch_smart(url)

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
    """
    搜索法律资料
    
    已废弃：请使用 deep_search 配合领域关键词，或在 skill 层实现领域特定逻辑
    """
    logger.warning("search_legal 已废弃，请使用 deep_search 配合领域关键词")
    # 添加法律关键词进行通用搜索
    legal_query = f"{query} 法律法规 法条"
    return deep_search(legal_query, max_results=5, fetch_content=True)


def search_legal_deep(query: str, category: str = 'all', max_results: int = 5) -> List[Dict[str, Any]]:
    """
    深度搜索法律资料 - 会抓取网页内容

    已废弃：请使用 deep_search_by_categories，或在 skill 层实现领域特定逻辑
    """
    logger.warning("search_legal_deep 已废弃，请使用 deep_search_by_categories")
    return deep_search_by_categories(
        query=query,
        categories={
            'laws': '法律法规 法条 条文',
            'cases': '判例 案例 裁判文书',
            'interpretations': '司法解释 最高法 最高检'
        },
        category_filter=category,
        max_results=max_results
    )


def deep_search_by_categories(
    query: str,
    categories: Dict[str, str],
    category_filter: str = 'all',
    max_results: int = 5
) -> List[Dict[str, Any]]:
    """
    通用的分类深度搜索

    Args:
        query: 搜索关键词
        categories: 类别配置 {类别名: 附加关键词}
                   例如: {'laws': '法律法规', 'cases': '判例案例'}
        category_filter: 限定类别，'all' 表示搜索所有类别
        max_results: 每个类别的最大结果数

    Returns:
        包含完整内容的搜索结果列表
    """
    all_results = []
    seen_urls = set()

    for cat_name, cat_keywords in categories.items():
        # 如果指定了类别过滤，只搜索匹配的类别
        if category_filter != 'all' and cat_name != category_filter:
            continue

        search_query = f"{query} {cat_keywords}"
        results = deep_search(search_query, max_results=max_results, fetch_content=True)

        for r in results:
            url = r.get('url', '')
            if url and url not in seen_urls:
                seen_urls.add(url)
                r['category'] = cat_name
                r['source'] = 'web_search_deep'
                all_results.append(r)

    return all_results


def search_wikipedia(query: str) -> List[Dict[str, Any]]:
    """搜索维基百科"""
    source = WikipediaSource()
    return source.search(query)

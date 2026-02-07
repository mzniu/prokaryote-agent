"""
技能: HTTP客户端
描述: 发起HTTP请求，与Web服务交互
领域: general
层级: basic
生成时间: 2026-02-07T16:13:16.596563

能力:
- HTTP客户端能力
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from prokaryote_agent.skills.skill_context import SkillContext
from typing import Dict, Any, List, Optional


class HttpClient(Skill):
    """
    HTTP客户端

    发起HTTP请求，与Web服务交互
    """

    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="http_client",
                name="HTTP客户端",
                tier="basic",
                domain="general",
                description="发起HTTP请求，与Web服务交互"
            )
        super().__init__(metadata)

    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return ['HTTP客户端能力']

    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        
        # 基本验证
        return True

    def execute(self, context: SkillContext = None, **kwargs) -> Dict[str, Any]:
        """
        执行技能

        Args:
            context: 技能执行上下文，提供知识库访问、技能互调用、产出物保存
        
        Args:
            input: 输入数据
            query: 搜索查询（可选）

        Returns:
            执行结果，包含网络搜索结果
        """
        try:
            
            from prokaryote_agent.skills.web_tools import web_search, search_wikipedia

            # 获取输入
            input_data = kwargs.get('input', {})
            query = kwargs.get('query', '')

            # 如果有查询，执行网络搜索
            search_results = []
            wiki_results = []

            if query:
                search_results = web_search(query, max_results=5)
                wiki_results = search_wikipedia(query)

            result = {
                'skill': "HTTP客户端",
                'input': input_data,
                'query': query,
                'search_results': search_results,
                'wiki_results': wiki_results,
                'output': '执行完成' if search_results or wiki_results else '未找到相关信息',
                'capabilities_used': ['HTTP客户端能力']
            }

            # 保存产出物到Knowledge（如果有context）
            if context and result:
                self._save_output(context, result)

            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    def _save_output(self, context: SkillContext, result: Dict[str, Any]):
        """保存产出物到Knowledge"""
        
        # 通用产出物保存
        import json
        context.save_output(
            output_type='generic',
            title=f"执行结果_{self.metadata.skill_id}",
            content=json.dumps(result, ensure_ascii=False, indent=2),
            format='json',
            category='generic_outputs'
        )

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [{'input': {}, 'description': '基本使用示例'}]

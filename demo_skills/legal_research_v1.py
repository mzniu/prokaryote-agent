"""
技能: 法律检索
描述: 从互联网检索相关法律法规、司法解释和判例
领域: legal
层级: basic
生成时间: 2026-02-06T00:32:36.207838

能力:
- 法规检索
- 判例搜索
- 司法解释查询
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from typing import Dict, Any, List


class LegalResearchV1(Skill):
    """
    法律检索
    
    从互联网检索相关法律法规、司法解释和判例
    """
    
    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="legal_research_v1",
                name="法律检索",
                tier="basic",
                domain="legal",
                description="从互联网检索相关法律法规、司法解释和判例"
            )
        super().__init__(metadata)
    
    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return ['法规检索', '判例搜索', '司法解释查询']
    
    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        
        query = kwargs.get('query')
        return query is not None and len(query.strip()) > 0
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行技能
        
        
        Args:
            query: 检索关键词
            sources: 检索源列表 ['法律法规', '司法解释', '判例']
        
        Returns:
            检索结果，包含标题、URL、来源等
        """
        try:
            
            from prokaryote_agent.skills.web_tools import search_legal, web_search
            
            query = kwargs.get('query', '')
            sources = kwargs.get('sources', ['法律法规', '司法解释', '判例'])
            
            # 使用真实网络搜索法律资料
            all_results = []
            
            # 根据 sources 决定搜索类别
            categories = []
            for src in sources:
                if '法规' in src or '法律' in src:
                    categories.append('laws')
                if '解释' in src:
                    categories.append('interpretations')
                if '判例' in src or '案例' in src:
                    categories.append('cases')
            
            if not categories:
                categories = ['all']
            
            # 执行搜索
            for category in set(categories):
                results = search_legal(query, category)
                all_results.extend(results)
            
            # 如果法律专业搜索没结果，用通用搜索
            if not all_results:
                all_results = web_search(f"{query} 法律", max_results=5)
            
            result = {
                'query': query,
                'sources': sources,
                'results': all_results,
                'total_found': len(all_results)
            }
            
            return {
                'success': True,
                'result': result
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }
    
    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [{'input': {'query': '劳动合同解除'}, 'description': '检索劳动合同相关法规'}, {'input': {'query': '知识产权侵权', 'sources': ['判例']}, 'description': '检索知识产权判例'}]

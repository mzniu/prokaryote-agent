"""
技能: 调试助手
描述: 帮助诊断和解决代码错误
领域: software_dev
层级: basic
生成时间: 2026-02-06T00:32:47.894443

能力:
- 错误诊断
- 解决方案搜索
- Stack Overflow查询
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from typing import Dict, Any, List


class DebugAssistantV1(Skill):
    """
    调试助手
    
    帮助诊断和解决代码错误
    """
    
    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="debug_assistant_v1",
                name="调试助手",
                tier="basic",
                domain="software_dev",
                description="帮助诊断和解决代码错误"
            )
        super().__init__(metadata)
    
    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return ['错误诊断', '解决方案搜索', 'Stack Overflow查询']
    
    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        
        error = kwargs.get('error')
        return error is not None and len(error.strip()) > 0
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        执行技能
        
        
        Args:
            error: 错误信息
            code: 相关代码上下文（可选）
            language: 编程语言
        
        Returns:
            调试建议和网络搜索到的解决方案
        """
        try:
            
            from prokaryote_agent.skills.web_tools import web_search
            
            error_message = kwargs.get('error', '')
            code_context = kwargs.get('code', '')
            language = kwargs.get('language', 'python')
            
            # 搜索错误解决方案
            search_query = f"{language} {error_message[:100]}"
            solutions = web_search(search_query, max_results=5)
            
            # 也搜索 Stack Overflow
            so_results = web_search(f"site:stackoverflow.com {error_message[:80]}", max_results=3)
            
            result = {
                'error': error_message,
                'language': language,
                'possible_solutions': solutions,
                'stackoverflow_refs': so_results,
                'analysis': f'搜索到 {len(solutions)} 个可能的解决方案'
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
        return [{'input': {}, 'description': '基本使用示例'}]

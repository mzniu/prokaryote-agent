"""
技能: 法律文书起草
描述: 起草基本法律文书（合同、声明等）
领域: legal
层级: basic
生成时间: 2026-02-06T21:45:22.942806

能力:
- 起草合同
- 生成文书模板
- 法律文书格式化
"""

from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from prokaryote_agent.skills.skill_context import SkillContext
from typing import Dict, Any, List, Optional


class DocumentDraftingBasic(Skill):
    """
    法律文书起草

    起草基本法律文书（合同、声明等）
    """

    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="document_drafting_basic",
                name="法律文书起草",
                tier="basic",
                domain="legal",
                description="起草基本法律文书（合同、声明等）"
            )
        super().__init__(metadata)

    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return ['起草合同', '生成文书模板', '法律文书格式化']

    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        
        doc_type = kwargs.get('doc_type')
        return doc_type is not None

    def execute(self, context: SkillContext = None, **kwargs) -> Dict[str, Any]:
        """
        执行技能

        Args:
            context: 技能执行上下文，提供知识库访问、技能互调用、产出物保存
        
        Args:
            doc_type: 文书类型（劳动合同、保密协议等）
            template: 模板（可选）
            data: 填充数据

        Returns:
            文书内容和参考资料
        """
        try:
            
            from prokaryote_agent.skills.web_tools import web_search, fetch_webpage

            doc_type = kwargs.get('doc_type', '合同')
            template = kwargs.get('template', None)
            data = kwargs.get('data', {})

            # 文书模板库
            doc_templates = {
                '劳动合同': ['合同双方', '工作内容', '工作时间', '劳动报酬', '社会保险', '劳动保护', '合同期限', '违约责任', '争议解决'],
                '保密协议': ['保密内容范围', '保密期限', '保密义务', '违约责任', '例外情况'],
                '租赁合同': ['租赁物描述', '租赁期限', '租金及支付', '押金', '维修责任', '违约责任'],
                'NDA': ['保密信息定义', '保密义务', '使用限制', '期限', '违约救济'],
                '起诉状': ['原告信息', '被告信息', '诉讼请求', '事实与理由', '证据清单'],
                '答辩状': ['答辩人信息', '答辩意见', '事实与理由', '证据清单'],
            }

            # 获取文书章节
            sections = doc_templates.get(doc_type, ['标题', '正文', '签章'])

            # 搜索相关模板和范例
            try:
                search_results = web_search(f"{doc_type} 模板 范本", max_results=3)
                references = [{'title': r.get('title', ''), 'url': r.get('url', '')} for r in search_results[:2]]
            except Exception:
                references = []

            # 生成文书框架
            content_lines = [f'【{doc_type}】', '']
            for i, section in enumerate(sections):
                content_lines.append(f'{i+1}. {section}')
                content_lines.append(f'   [请填写{section}内容]')
                content_lines.append('')

            result = {
                'doc_type': doc_type,
                'content': '\n'.join(content_lines),
                'sections': sections,
                'references': references,
                'warnings': ['请根据实际情况修改内容', '建议咨询专业律师审核']
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
        
        # 保存文书草稿
        context.save_output(
            output_type='document',
            title=f"{result.get('doc_type', '文书')}草稿",
            content=result.get('content', ''),
            category='drafts',
            metadata={'sections': result.get('sections', []), 'references': result.get('references', [])}
        )

    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return [{'input': {'doc_type': '劳动合同'}, 'description': '起草劳动合同'}, {'input': {'doc_type': '保密协议'}, 'description': '起草保密协议'}]

# -*- coding: utf-8 -*-
"""
代码合成酶 (Code Synthase)
==========================

负责调用LLM生成Python代码，是技能代码生成的核心酶。

功能：
- 接收技能规格（名称、描述、能力列表等）
- 构建代码生成提示词
- 调用LLM生成代码
- 返回格式化的代码字符串

⚠️ 核心酶警告：此代码只能由开发者（上帝视角）修改
"""

import logging
from typing import Dict, Any, Optional
from datetime import datetime

from .base import CoreEnzyme

logger = logging.getLogger(__name__)


# 技能代码模板（严格的结构约束）
SKILL_CODE_TEMPLATE = '''# -*- coding: utf-8 -*-
"""
技能: {skill_name}
描述: {description}
领域: {domain}
层级: {tier}
生成时间: {generated_at}
生成器: CodeSynthase v{enzyme_version}

架构: AI-first with hardcoded fallback

能力:
{capabilities_doc}
"""

from typing import Dict, Any, List, Optional
from prokaryote_agent.skills.skill_base import Skill, SkillMetadata
from prokaryote_agent.skills.skill_context import SkillContext
from prokaryote_agent.utils.json_utils import safe_json_loads


class {class_name}(Skill):
    """
    {skill_name}
    
    {description}
    """
    
    def __init__(self, metadata: SkillMetadata = None):
        if metadata is None:
            metadata = SkillMetadata(
                skill_id="{skill_id}",
                name="{skill_name}",
                tier="{tier}",
                domain="{domain}",
                description="{description}"
            )
        super().__init__(metadata)
    
    def get_capabilities(self) -> List[str]:
        """返回技能能力列表"""
        return {capabilities_list}
    
    def validate_input(self, **kwargs) -> bool:
        """验证输入参数"""
        {validate_code}
    
    def execute(self, context: SkillContext = None, **kwargs) -> Dict[str, Any]:
        """
        执行技能
        
        Args:
            context: 技能执行上下文
{execute_args_doc}
        
        Returns:
            Dict包含 success, result/error
        """
        try:
{execute_code}
            
            return {{
                'success': True,
                'result': result
            }}
        except Exception as e:
            return {{
                'success': False,
                'error': str(e)
            }}
    
    def get_usage_examples(self) -> List[Dict[str, Any]]:
        """返回使用示例"""
        return {examples}
'''


# LLM 代码生成提示词模板
CODE_GENERATION_PROMPT = '''你是一个专业的Python代码生成器，请为技能系统生成代码。

## 技能规格

- **技能ID**: {skill_id}
- **技能名称**: {skill_name}
- **描述**: {description}
- **领域**: {domain}
- **层级**: {tier}
- **能力列表**:
{capabilities}

## 核心设计模式: AI-first with hardcoded fallback

所有领域专业逻辑必须优先通过 context.call_ai() 实现，仅在 AI 不可用时回退到简单规则。
推荐模式：
```python
# AI 主路径
ai_result = context.call_ai(structured_prompt)
if ai_result.get('success') and ai_result.get('content'):
    data = safe_json_loads(ai_result['content'])
    ...使用 data...
else:
    # 简单规则回退
    data = basic_fallback(...)
```

## 代码生成要求

请生成以下三个部分的代码：

### 1. validate_input 方法体
验证输入参数的代码，不需要方法签名，只需要方法体。
必须返回 True 或 False。

### 2. execute 方法体
执行技能的核心代码，不需要方法签名，只需要方法体。
- 代码需要设置 `result` 变量存储执行结果
- 方法签名为 `execute(self, context: SkillContext = None, **kwargs)`:
  ▸ `context` 是 SkillContext 实例，提供以下能力：
    - `context.call_ai(prompt, system_prompt=None)` → {{"success": bool, "content": str}} AI大模型
    - `context.web_search(query, max_results=5)` → [results] 联网搜索
    - `context.deep_search(query, max_results=5, fetch_content=True)` → [results] 深度搜索
    - `context.fetch_url(url)` → {{"success": bool, "content": str}} URL抓取
    - `context.search_knowledge(query, category, limit)` → [results] 知识库搜索
    - `context.store_knowledge(title, content, category, source, tags)` → bool 知识库存储
    - `context.smart_search(query, category, use_web)` → dict 智能搜索
    - `context.call_skill(skill_id, **kwargs)` → dict 调用其他技能
    - `context.read_file(path)` / `context.write_file(path, content)` 文件操作
    - `context.save_output(output_type, title, content, category)` → path 保存产出物
    - `context.log(message, level)` 日志
  ▸ **禁止** 直接 import web_tools/ai_adapter，所有能力通过 context
  ▸ 可以使用 `safe_json_loads(text)` 解析 AI 返回的 JSON（已在文件顶部导入）

### 3. examples 列表
使用示例列表，每个示例是一个字典，包含 input 和 expected_output。

## 输出格式

请严格按照以下JSON格式输出：

```json
{{
  "validate_code": "验证代码（方法体，8空格缩进）",
  "execute_code": "执行代码（方法体，12空格缩进，设置result变量）",
  "execute_args_doc": "参数文档（每行12空格缩进）",
  "examples": [
    {{"input": {{"param": "value"}}, "expected_output": "描述"}}
  ]
}}
```

## 重要约束

1. 代码必须是有效的Python语法
2. 不要使用 eval、exec、__import__ 等危险函数
3. 领域专业逻辑用 context.call_ai() 实现，不要硬编码知识
4. execute方法的代码缩进必须是12个空格（因为在try块内）
5. validate方法的代码缩进必须是8个空格
6. 确保所有括号、引号配对正确

请直接输出JSON，不要有其他文字。'''


class CodeSynthase(CoreEnzyme):
    """
    代码合成酶 - 负责生成技能代码
    
    这是核心酶之一，调用LLM将技能规格转换为可执行的Python代码。
    
    ⚠️ 核心酶警告：此类只能由开发者修改
    """
    
    ENZYME_NAME = "CodeSynthase"
    ENZYME_VERSION = "1.0.0"
    
    def __init__(self, ai_adapter=None):
        """
        初始化代码合成酶
        
        Args:
            ai_adapter: AI适配器实例，如果为None则延迟加载
        """
        super().__init__()
        self._ai_adapter = ai_adapter
    
    @property
    def ai_adapter(self):
        """延迟加载AI适配器"""
        if self._ai_adapter is None:
            try:
                from prokaryote_agent.ai_adapter import AIAdapter
                self._ai_adapter = AIAdapter()
            except ImportError:
                logger.warning("[CodeSynthase] AI适配器不可用，将使用备用模板")
                self._ai_adapter = None
            except Exception as e:
                logger.warning(f"[CodeSynthase] AI适配器加载失败: {e}，将使用备用模板")
                self._ai_adapter = None
        return self._ai_adapter
    
    def execute(self, skill_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成技能代码
        
        Args:
            skill_spec: 技能规格字典
                {
                    'id': str,           # 技能ID
                    'name': str,         # 技能名称
                    'description': str,  # 描述
                    'domain': str,       # 领域
                    'tier': str,         # 层级
                    'capabilities': List[str]  # 能力列表
                }
        
        Returns:
            {
                'success': bool,
                'code': str,       # 生成的完整代码
                'error': str       # 错误信息（如果失败）
            }
        """
        skill_id = skill_spec.get('id', 'unknown')
        logger.info(f"[CodeSynthase] 开始生成技能代码: {skill_id}")
        
        try:
            # 1. 尝试使用LLM生成核心逻辑
            llm_result = self._generate_with_llm(skill_spec)
            
            if llm_result['success']:
                # 2. 组装完整代码
                code = self._assemble_code(skill_spec, llm_result['parts'])
                logger.info(f"[CodeSynthase] 代码生成成功: {skill_id}")
                return {
                    'success': True,
                    'code': code,
                    'error': ''
                }
            else:
                # 3. LLM失败，使用备用模板
                logger.warning(f"[CodeSynthase] LLM生成失败，使用备用模板: {llm_result['error']}")
                code = self._generate_fallback(skill_spec)
                return {
                    'success': True,
                    'code': code,
                    'error': '',
                    'fallback': True
                }
                
        except Exception as e:
            logger.error(f"[CodeSynthase] 代码生成异常: {e}")
            return {
                'success': False,
                'code': '',
                'error': str(e)
            }
    
    def _generate_with_llm(self, skill_spec: Dict[str, Any]) -> Dict[str, Any]:
        """使用LLM生成代码核心部分"""
        # 检查AI适配器是否可用
        if self.ai_adapter is None:
            return {
                'success': False,
                'error': 'AI适配器不可用',
                'parts': {}
            }
        
        # 构建提示词
        capabilities = skill_spec.get('capabilities', [])
        capabilities_str = '\n'.join(f"  - {cap}" for cap in capabilities)
        
        prompt = CODE_GENERATION_PROMPT.format(
            skill_id=skill_spec.get('id', 'unknown'),
            skill_name=skill_spec.get('name', '未命名技能'),
            description=skill_spec.get('description', ''),
            domain=skill_spec.get('domain', 'general'),
            tier=skill_spec.get('tier', 'basic'),
            capabilities=capabilities_str
        )
        
        # 如果有现有代码（进化模式），追加改进指令
        current_code = skill_spec.get('current_code')
        if current_code:
            level = skill_spec.get('level', 1)
            enhancements = skill_spec.get('enhancements', [])
            requirements = skill_spec.get('requirements', [])
            
            enhancements_str = '\n'.join(
                f"  - {e}" for e in enhancements
            ) if enhancements else '  （无）'
            requirements_str = '\n'.join(
                f"  - {r}" for r in requirements
            ) if requirements else '  （无）'
            
            # 截断过长代码防止超 token
            code_preview = current_code[:6000]
            if len(current_code) > 6000:
                code_preview += '\n\n# ... (代码过长，已截断) ...'
            
            prompt += f'''

## ⚡ 进化模式

这不是从零生成！请在以下现有代码基础上**改进**。

### 当前等级: {level}
### 本次增强:
{enhancements_str}
### 新能力要求:
{requirements_str}

### 现有代码:
```python
{code_preview}
```

### 改进指导:
1. **保留**现有的 AI-first 设计模式和整体结构
2. **改进** AI prompt 质量使分析更准确、更深入
3. **增加**新能力要求中列出的功能
4. **优化**回退逻辑，使其更智能
5. **不要降级**：确保所有现有功能都保留
6. 如果现有代码是纯硬编码的，将核心逻辑改为 AI-first 模式'''
        
        # 调用AI
        try:
            response = self.ai_adapter._call_ai(prompt)
        except Exception as e:
            return {
                'success': False,
                'error': f'AI调用异常: {e}',
                'parts': {}
            }
        
        if not response.get('success'):
            return {
                'success': False,
                'error': response.get('error', 'AI调用失败'),
                'parts': {}
            }
        
        # 解析JSON响应
        content = response.get('content', '')
        parts = self._parse_llm_response(content)
        
        if not parts:
            return {
                'success': False,
                'error': '无法解析AI响应',
                'parts': {}
            }
        
        return {
            'success': True,
            'error': '',
            'parts': parts
        }
    
    def _parse_llm_response(self, content: str) -> Optional[Dict[str, Any]]:
        """解析LLM返回的JSON"""
        import re
        from prokaryote_agent.utils.json_utils import safe_json_loads
        
        # 尝试提取JSON块
        json_match = re.search(
            r'```(?:json)?\s*(\{.*?\})\s*```', content, re.DOTALL
        )
        if json_match:
            try:
                return safe_json_loads(json_match.group(1))
            except Exception:
                pass
        
        # 尝试直接解析
        try:
            return safe_json_loads(content)
        except Exception:
            pass
        
        # 尝试找到最外层的花括号
        try:
            start = content.find('{')
            end = content.rfind('}')
            if start != -1 and end != -1:
                return safe_json_loads(content[start:end + 1])
        except Exception:
            pass
        
        return None
    
    def _assemble_code(self, skill_spec: Dict[str, Any], parts: Dict[str, Any]) -> str:
        """组装完整的技能代码"""
        skill_id = skill_spec.get('id', 'unknown')
        skill_name = skill_spec.get('name', '未命名技能')
        description = skill_spec.get('description', '')
        domain = skill_spec.get('domain', 'general')
        tier = skill_spec.get('tier', 'basic')
        capabilities = skill_spec.get('capabilities', [])
        
        # 生成类名
        class_name = self._to_class_name(skill_id)
        
        # 处理能力文档
        capabilities_doc = '\n'.join(f"- {cap}" for cap in capabilities)
        
        # 处理验证代码（确保缩进正确）
        validate_code = parts.get('validate_code', 'return True')
        validate_code = self._fix_indentation(validate_code, 8)
        
        # 处理执行代码（确保缩进正确）
        execute_code = parts.get('execute_code', 'result = {"message": "技能执行成功"}')
        execute_code = self._fix_indentation(execute_code, 12)
        
        # 处理参数文档
        execute_args_doc = parts.get('execute_args_doc', '            **kwargs: 关键字参数')
        
        # 处理示例
        examples = parts.get('examples', [])
        examples_str = repr(examples)
        
        # 组装代码
        code = SKILL_CODE_TEMPLATE.format(
            skill_id=skill_id,
            skill_name=skill_name,
            description=description,
            domain=domain,
            tier=tier,
            generated_at=datetime.now().isoformat(),
            enzyme_version=self.ENZYME_VERSION,
            capabilities_doc=capabilities_doc,
            class_name=class_name,
            capabilities_list=repr(capabilities),
            validate_code=validate_code,
            execute_args_doc=execute_args_doc,
            execute_code=execute_code,
            examples=examples_str
        )
        
        return code
    
    def _generate_fallback(self, skill_spec: Dict[str, Any]) -> str:
        """生成备用模板代码"""
        skill_id = skill_spec.get('id', 'unknown')
        skill_name = skill_spec.get('name', '未命名技能')
        description = skill_spec.get('description', '')
        domain = skill_spec.get('domain', 'general')
        tier = skill_spec.get('tier', 'basic')
        capabilities = skill_spec.get('capabilities', [])
        
        class_name = self._to_class_name(skill_id)
        capabilities_doc = '\n'.join(f"- {cap}" for cap in capabilities)
        
        # 备用的简单实现
        validate_code = "return True  # 备用模板：跳过验证"
        execute_code = '''# 备用模板：返回基本信息
            result = {
                'skill_id': self.metadata.skill_id,
                'skill_name': self.metadata.name,
                'message': '技能已执行（备用模板）',
                'input': kwargs
            }'''
        
        examples = [{'input': {}, 'expected_output': '技能执行结果'}]
        
        code = SKILL_CODE_TEMPLATE.format(
            skill_id=skill_id,
            skill_name=skill_name,
            description=description,
            domain=domain,
            tier=tier,
            generated_at=datetime.now().isoformat(),
            enzyme_version=self.ENZYME_VERSION,
            capabilities_doc=capabilities_doc,
            class_name=class_name,
            capabilities_list=repr(capabilities),
            validate_code=validate_code,
            execute_args_doc="            **kwargs: 关键字参数",
            execute_code=execute_code,
            examples=repr(examples)
        )
        
        return code
    
    def _to_class_name(self, skill_id: str) -> str:
        """将技能ID转换为类名"""
        # legal_research_basic -> LegalResearchBasic
        parts = skill_id.split('_')
        return ''.join(part.capitalize() for part in parts)
    
    def _fix_indentation(self, code: str, base_indent: int) -> str:
        """
        修复代码缩进
        
        将代码规范化为指定的基础缩进
        """
        if not code:
            return ' ' * base_indent + 'pass'
        
        lines = code.split('\n')
        result_lines = []
        
        # 找到最小的非空行缩进
        min_indent = float('inf')
        for line in lines:
            stripped = line.lstrip()
            if stripped:  # 非空行
                indent = len(line) - len(stripped)
                min_indent = min(min_indent, indent)
        
        if min_indent == float('inf'):
            min_indent = 0
        
        # 重新缩进
        for line in lines:
            stripped = line.lstrip()
            if stripped:
                current_indent = len(line) - len(stripped)
                new_indent = base_indent + (current_indent - min_indent)
                result_lines.append(' ' * new_indent + stripped)
            else:
                result_lines.append('')
        
        return '\n'.join(result_lines)

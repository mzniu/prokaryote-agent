# -*- coding: utf-8 -*-
"""
错误修复酶 (Error Repairase)
============================

负责自动修复代码中的常见错误，是代码质量的最后一道防线。

功能：
- 规则修复：基于规则的常见错误自动修复
- 缩进修复：修正缩进问题
- 括号修复：补全未闭合的括号
- LLM辅助修复：复杂错误调用LLM修复

⚠️ 核心酶警告：此代码只能由开发者（上帝视角）修改
"""

import re
import ast
import logging
from typing import Dict, Any, List, Optional, Tuple

from .base import CoreEnzyme
from .syntax_verifier import VerificationResult

logger = logging.getLogger(__name__)


class ErrorRepairase(CoreEnzyme):
    """
    错误修复酶 - 自动修复代码错误
    
    这是核心酶之一，尝试自动修复验证失败的代码。
    
    修复策略：
    1. 规则修复 - 基于模式匹配的自动修复
    2. 缩进修复 - 修正缩进问题
    3. 结构修复 - 补全缺失的代码结构
    4. LLM修复 - 复杂问题调用LLM辅助
    
    ⚠️ 核心酶警告：此类只能由开发者修改
    """
    
    ENZYME_NAME = "ErrorRepairase"
    ENZYME_VERSION = "1.0.0"
    
    def __init__(self, ai_adapter=None):
        """
        初始化错误修复酶
        
        Args:
            ai_adapter: AI适配器实例，用于复杂修复
        """
        super().__init__()
        self._ai_adapter = ai_adapter
        self._repair_history = []  # 记录修复历史
    
    @property
    def ai_adapter(self):
        """延迟加载AI适配器"""
        if self._ai_adapter is None:
            try:
                from prokaryote_agent.ai_adapter import AIAdapter
                self._ai_adapter = AIAdapter()
            except ImportError:
                logger.warning("[ErrorRepairase] AI适配器不可用，LLM修复功能禁用")
                self._ai_adapter = None
            except Exception as e:
                logger.warning(f"[ErrorRepairase] AI适配器加载失败: {e}")
                self._ai_adapter = None
        return self._ai_adapter
    
    def execute(self, code: str, errors: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        修复代码错误
        
        Args:
            code: 有错误的代码
            errors: 错误列表（来自SyntaxVerifier）
        
        Returns:
            {
                'success': bool,
                'code': str,          # 修复后的代码
                'repairs': List[str], # 修复说明列表
                'remaining_errors': List[Dict]  # 未修复的错误
            }
        """
        if not errors:
            return {
                'success': True,
                'code': code,
                'repairs': [],
                'remaining_errors': []
            }
        
        logger.info(f"[ErrorRepairase] 开始修复 {len(errors)} 个错误")
        
        repairs = []
        repaired_code = code
        
        # 1. 尝试规则修复
        for error in errors:
            error_type = error.get('type', '')
            repair_result = self._apply_rule_repair(repaired_code, error)
            
            if repair_result['fixed']:
                repaired_code = repair_result['code']
                repairs.append(repair_result['description'])
                logger.debug(f"[ErrorRepairase] 规则修复成功: {repair_result['description']}")
        
        # 2. 检查修复结果
        try:
            ast.parse(repaired_code)
            # 修复成功
            return {
                'success': True,
                'code': repaired_code,
                'repairs': repairs,
                'remaining_errors': []
            }
        except SyntaxError as e:
            # 仍有语法错误，尝试更多修复
            pass
        
        # 3. 尝试缩进修复
        indent_result = self._fix_indentation_issues(repaired_code)
        if indent_result['fixed']:
            repaired_code = indent_result['code']
            repairs.extend(indent_result['repairs'])
        
        # 4. 尝试结构修复
        struct_result = self._fix_structure_issues(repaired_code)
        if struct_result['fixed']:
            repaired_code = struct_result['code']
            repairs.extend(struct_result['repairs'])
        
        # 5. 最终检查
        try:
            ast.parse(repaired_code)
            return {
                'success': True,
                'code': repaired_code,
                'repairs': repairs,
                'remaining_errors': []
            }
        except SyntaxError as e:
            # 规则修复失败，尝试LLM修复
            llm_result = self._try_llm_repair(repaired_code, str(e))
            
            if llm_result['success']:
                repairs.append('LLM辅助修复')
                return {
                    'success': True,
                    'code': llm_result['code'],
                    'repairs': repairs,
                    'remaining_errors': []
                }
            else:
                return {
                    'success': False,
                    'code': repaired_code,
                    'repairs': repairs,
                    'remaining_errors': [{
                        'type': 'syntax_error',
                        'message': str(e),
                        'line': e.lineno
                    }]
                }
    
    def _apply_rule_repair(self, code: str, error: Dict[str, Any]) -> Dict[str, Any]:
        """应用规则修复"""
        error_type = error.get('type', '')
        message = error.get('message', '')
        line = error.get('line')
        suggestion = error.get('suggestion', '')
        
        lines = code.split('\n')
        fixed = False
        description = ''
        
        # 根据错误类型选择修复策略
        if error_type == 'unclosed_bracket':
            # 尝试补全括号
            result = self._fix_unclosed_bracket(lines, line, message)
            if result['fixed']:
                lines = result['lines']
                fixed = True
                description = result['description']
        
        elif error_type == 'mismatched_bracket':
            # 尝试修复括号不匹配
            result = self._fix_mismatched_bracket(lines, line, message)
            if result['fixed']:
                lines = result['lines']
                fixed = True
                description = result['description']
        
        elif error_type == 'syntax_error':
            # 根据消息内容尝试修复
            if 'expected' in message.lower() and ':' in message:
                # 缺少冒号
                result = self._fix_missing_colon(lines, line)
                if result['fixed']:
                    lines = result['lines']
                    fixed = True
                    description = result['description']
            
            elif 'except' in message.lower() or 'finally' in message.lower():
                # try块缺少except/finally
                result = self._fix_try_block(lines, line)
                if result['fixed']:
                    lines = result['lines']
                    fixed = True
                    description = result['description']
            
            elif 'indent' in message.lower():
                # 缩进问题
                result = self._fix_indent_at_line(lines, line)
                if result['fixed']:
                    lines = result['lines']
                    fixed = True
                    description = result['description']
        
        return {
            'fixed': fixed,
            'code': '\n'.join(lines) if fixed else code,
            'description': description
        }
    
    def _fix_unclosed_bracket(self, lines: List[str], line_num: int, 
                               message: str) -> Dict[str, Any]:
        """修复未闭合的括号"""
        if line_num is None or line_num > len(lines):
            return {'fixed': False, 'lines': lines, 'description': ''}
        
        # 确定括号类型
        bracket_map = {'(': ')', '[': ']', '{': '}'}
        open_bracket = None
        
        for b in bracket_map:
            if b in message:
                open_bracket = b
                break
        
        if not open_bracket:
            return {'fixed': False, 'lines': lines, 'description': ''}
        
        close_bracket = bracket_map[open_bracket]
        
        # 在行尾添加闭合括号
        idx = line_num - 1
        if idx < len(lines):
            lines[idx] = lines[idx].rstrip() + close_bracket
            return {
                'fixed': True,
                'lines': lines,
                'description': f'第{line_num}行添加闭合括号 {close_bracket}'
            }
        
        return {'fixed': False, 'lines': lines, 'description': ''}
    
    def _fix_mismatched_bracket(self, lines: List[str], line_num: int,
                                 message: str) -> Dict[str, Any]:
        """修复括号不匹配"""
        # 简单策略：尝试替换错误的闭合括号
        if line_num is None or line_num > len(lines):
            return {'fixed': False, 'lines': lines, 'description': ''}
        
        # 从消息中提取期望的括号
        match = re.search(r'期望\s*["\'](.)["\']', message)
        if not match:
            return {'fixed': False, 'lines': lines, 'description': ''}
        
        expected = match.group(1)
        idx = line_num - 1
        
        # 替换错误的闭合括号
        bracket_map = {')': ['(', ')'], ']': ['[', ']'], '}': ['{', '}']}
        for wrong, (_, close) in bracket_map.items():
            if wrong != expected and wrong in lines[idx]:
                lines[idx] = lines[idx].replace(wrong, expected, 1)
                return {
                    'fixed': True,
                    'lines': lines,
                    'description': f'第{line_num}行将 {wrong} 替换为 {expected}'
                }
        
        return {'fixed': False, 'lines': lines, 'description': ''}
    
    def _fix_missing_colon(self, lines: List[str], line_num: int) -> Dict[str, Any]:
        """修复缺少冒号"""
        if line_num is None or line_num > len(lines):
            return {'fixed': False, 'lines': lines, 'description': ''}
        
        idx = line_num - 1
        line = lines[idx].rstrip()
        
        # 检查是否是需要冒号的语句
        keywords = ['if', 'else', 'elif', 'for', 'while', 'def', 'class', 
                   'try', 'except', 'finally', 'with']
        
        stripped = line.strip()
        for kw in keywords:
            if stripped.startswith(kw + ' ') or stripped == kw:
                if not line.endswith(':'):
                    lines[idx] = line + ':'
                    return {
                        'fixed': True,
                        'lines': lines,
                        'description': f'第{line_num}行添加冒号'
                    }
        
        return {'fixed': False, 'lines': lines, 'description': ''}
    
    def _fix_try_block(self, lines: List[str], line_num: int) -> Dict[str, Any]:
        """修复try块缺少except/finally"""
        if line_num is None:
            return {'fixed': False, 'lines': lines, 'description': ''}
        
        # 向上查找try
        try_line = None
        try_indent = None
        
        for i in range(line_num - 1, -1, -1):
            stripped = lines[i].strip()
            if stripped.startswith('try:') or stripped == 'try':
                try_line = i
                try_indent = len(lines[i]) - len(lines[i].lstrip())
                break
        
        if try_line is None:
            return {'fixed': False, 'lines': lines, 'description': ''}
        
        # 查找try块的结束位置
        block_end = try_line + 1
        while block_end < len(lines):
            if lines[block_end].strip():
                current_indent = len(lines[block_end]) - len(lines[block_end].lstrip())
                if current_indent <= try_indent:
                    break
            block_end += 1
        
        # 插入except块
        except_line = ' ' * try_indent + 'except Exception as e:'
        pass_line = ' ' * (try_indent + 4) + 'raise'
        
        lines.insert(block_end, pass_line)
        lines.insert(block_end, except_line)
        
        return {
            'fixed': True,
            'lines': lines,
            'description': f'第{block_end+1}行添加except块'
        }
    
    def _fix_indent_at_line(self, lines: List[str], line_num: int) -> Dict[str, Any]:
        """修复特定行的缩进问题"""
        if line_num is None or line_num > len(lines):
            return {'fixed': False, 'lines': lines, 'description': ''}
        
        idx = line_num - 1
        line = lines[idx]
        
        # 查找上一个非空行的缩进
        prev_indent = 0
        for i in range(idx - 1, -1, -1):
            if lines[i].strip():
                prev_indent = len(lines[i]) - len(lines[i].lstrip())
                # 如果上一行以冒号结尾，缩进应该增加
                if lines[i].rstrip().endswith(':'):
                    prev_indent += 4
                break
        
        # 修正当前行缩进
        stripped = line.lstrip()
        if stripped:
            lines[idx] = ' ' * prev_indent + stripped
            return {
                'fixed': True,
                'lines': lines,
                'description': f'第{line_num}行修正缩进为{prev_indent}空格'
            }
        
        return {'fixed': False, 'lines': lines, 'description': ''}
    
    def _fix_indentation_issues(self, code: str) -> Dict[str, Any]:
        """全局缩进修复"""
        lines = code.split('\n')
        repairs = []
        fixed = False
        
        # 统一Tab为4空格
        new_lines = []
        for i, line in enumerate(lines):
            if '\t' in line:
                new_line = line.replace('\t', '    ')
                if new_line != line:
                    fixed = True
                    repairs.append(f'第{i+1}行Tab转换为空格')
                new_lines.append(new_line)
            else:
                new_lines.append(line)
        
        return {
            'fixed': fixed,
            'code': '\n'.join(new_lines),
            'repairs': repairs
        }
    
    def _fix_structure_issues(self, code: str) -> Dict[str, Any]:
        """修复代码结构问题"""
        lines = code.split('\n')
        repairs = []
        fixed = False
        
        # 检查每个代码块是否有内容
        i = 0
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            
            # 检查以冒号结尾的行
            if stripped.endswith(':'):
                indent = len(line) - len(line.lstrip())
                
                # 检查下一行
                next_i = i + 1
                while next_i < len(lines) and not lines[next_i].strip():
                    next_i += 1
                
                if next_i >= len(lines):
                    # 文件结束，添加pass
                    lines.insert(i + 1, ' ' * (indent + 4) + 'pass')
                    repairs.append(f'第{i+2}行添加pass')
                    fixed = True
                else:
                    next_indent = len(lines[next_i]) - len(lines[next_i].lstrip())
                    if next_indent <= indent:
                        # 下一行缩进不够，添加pass
                        lines.insert(i + 1, ' ' * (indent + 4) + 'pass')
                        repairs.append(f'第{i+2}行添加pass')
                        fixed = True
            
            i += 1
        
        return {
            'fixed': fixed,
            'code': '\n'.join(lines),
            'repairs': repairs
        }
    
    def _try_llm_repair(self, code: str, error_msg: str) -> Dict[str, Any]:
        """尝试LLM辅助修复"""
        if self.ai_adapter is None:
            return {'success': False, 'code': code}
        
        prompt = f'''请修复以下Python代码中的语法错误。

**错误信息**：
{error_msg}

**原始代码**：
```python
{code}
```

**要求**：
1. 只修复语法错误，不改变代码逻辑
2. 保持原有的代码风格和缩进
3. 直接输出修复后的完整代码，不要解释

**修复后的代码**：
```python
'''
        
        try:
            response = self.ai_adapter._call_ai(prompt)
            
            if response.get('success'):
                content = response.get('content', '')
                
                # 提取代码块
                code_match = re.search(r'```python\s*(.*?)\s*```', content, re.DOTALL)
                if code_match:
                    repaired = code_match.group(1)
                else:
                    # 尝试直接使用内容
                    repaired = content.strip()
                
                # 验证修复后的代码
                try:
                    ast.parse(repaired)
                    return {'success': True, 'code': repaired}
                except SyntaxError:
                    return {'success': False, 'code': code}
            
            return {'success': False, 'code': code}
            
        except Exception as e:
            logger.warning(f"[ErrorRepairase] LLM修复失败: {e}")
            return {'success': False, 'code': code}
    
    def get_repair_history(self) -> List[Dict[str, Any]]:
        """获取修复历史"""
        return self._repair_history.copy()

# -*- coding: utf-8 -*-
"""
语法校验酶 (Syntax Verifier)
============================

负责验证Python代码的语法正确性，是代码质量的第一道防线。

功能：
- AST语法解析检查
- 缩进一致性检查
- 括号/引号配对检查
- 常见错误模式检测
- 危险代码检测

⚠️ 核心酶警告：此代码只能由开发者（上帝视角）修改
"""

import ast
import re
import logging
from typing import Dict, Any, List, Tuple, Optional
from dataclasses import dataclass, field

from .base import CoreEnzyme

logger = logging.getLogger(__name__)


@dataclass
class VerificationResult:
    """验证结果"""
    passed: bool
    errors: List[Dict[str, Any]] = field(default_factory=list)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    
    def add_error(self, error_type: str, message: str, line: int = None, 
                  column: int = None, suggestion: str = None):
        """添加错误"""
        self.passed = False
        self.errors.append({
            'type': error_type,
            'message': message,
            'line': line,
            'column': column,
            'suggestion': suggestion
        })
    
    def add_warning(self, warning_type: str, message: str, line: int = None):
        """添加警告（不影响通过状态）"""
        self.warnings.append({
            'type': warning_type,
            'message': message,
            'line': line
        })
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'passed': self.passed,
            'errors': self.errors,
            'warnings': self.warnings,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }


class SyntaxVerifier(CoreEnzyme):
    """
    语法校验酶 - 验证代码语法正确性
    
    这是核心酶之一，在代码生成后检查语法有效性。
    
    检查项目：
    1. AST解析 - Python语法是否正确
    2. 缩进检查 - 缩进是否一致
    3. 括号配对 - 括号、引号是否配对
    4. 常见错误 - 常见的语法错误模式
    5. 安全检查 - 危险代码检测
    
    ⚠️ 核心酶警告：此类只能由开发者修改
    """
    
    ENZYME_NAME = "SyntaxVerifier"
    ENZYME_VERSION = "1.0.0"
    
    # 危险的内置函数
    DANGEROUS_BUILTINS = {'eval', 'exec', '__import__', 'compile'}
    
    # 危险的模块调用
    DANGEROUS_CALLS = {
        'os.system', 'os.popen', 'os.remove', 'os.rmdir',
        'subprocess.call', 'subprocess.run', 'subprocess.Popen',
        'shutil.rmtree'
    }
    
    def __init__(self):
        """初始化语法校验酶"""
        super().__init__()
    
    def execute(self, code: str) -> VerificationResult:
        """
        验证代码语法
        
        Args:
            code: 要验证的Python代码字符串
        
        Returns:
            VerificationResult: 验证结果
        """
        result = VerificationResult(passed=True)
        
        if not code or not code.strip():
            result.add_error('empty_code', '代码为空')
            return result
        
        logger.debug(f"[SyntaxVerifier] 开始验证代码 ({len(code)} 字符)")
        
        # 1. AST语法解析
        self._check_ast(code, result)
        
        # 如果AST解析失败，尝试更详细的诊断
        if not result.passed:
            self._diagnose_syntax_error(code, result)
        
        # 2. 缩进检查（即使AST通过也检查）
        self._check_indentation(code, result)
        
        # 3. 括号配对检查
        self._check_brackets(code, result)
        
        # 4. 常见错误检查
        self._check_common_errors(code, result)
        
        # 5. 安全检查（仅警告）
        self._check_safety(code, result)
        
        logger.info(
            f"[SyntaxVerifier] 验证完成: "
            f"{'通过' if result.passed else '失败'}, "
            f"{len(result.errors)}错误, {len(result.warnings)}警告"
        )
        
        return result
    
    def _check_ast(self, code: str, result: VerificationResult):
        """检查AST语法"""
        try:
            ast.parse(code)
        except SyntaxError as e:
            result.add_error(
                'syntax_error',
                str(e.msg) if hasattr(e, 'msg') else str(e),
                line=e.lineno,
                column=e.offset,
                suggestion=self._suggest_fix_for_syntax_error(e)
            )
    
    def _diagnose_syntax_error(self, code: str, result: VerificationResult):
        """诊断语法错误的具体原因"""
        lines = code.split('\n')
        
        # 检查常见问题
        for i, line in enumerate(lines, 1):
            # 检查未闭合的字符串
            if self._has_unclosed_string(line):
                result.errors[-1]['suggestion'] = f"第{i}行可能有未闭合的字符串"
            
            # 检查缺少冒号的情况
            stripped = line.strip()
            if stripped.startswith(('if ', 'else', 'elif ', 'for ', 'while ', 
                                    'def ', 'class ', 'try', 'except', 'finally',
                                    'with ')):
                if stripped and not stripped.endswith(':') and not stripped.endswith('\\'):
                    if 'suggestion' not in result.errors[-1] or not result.errors[-1]['suggestion']:
                        result.errors[-1]['suggestion'] = f"第{i}行可能缺少冒号(:)"
    
    def _has_unclosed_string(self, line: str) -> bool:
        """检查行内是否有未闭合的字符串"""
        in_single = False
        in_double = False
        in_triple_single = False
        in_triple_double = False
        i = 0
        
        while i < len(line):
            # 检查三引号
            if line[i:i+3] == '"""' and not in_single and not in_triple_single:
                in_triple_double = not in_triple_double
                i += 3
                continue
            if line[i:i+3] == "'''" and not in_double and not in_triple_double:
                in_triple_single = not in_triple_single
                i += 3
                continue
            
            # 检查转义
            if line[i] == '\\' and i + 1 < len(line):
                i += 2
                continue
            
            # 检查普通引号
            if line[i] == '"' and not in_single and not in_triple_single and not in_triple_double:
                in_double = not in_double
            elif line[i] == "'" and not in_double and not in_triple_single and not in_triple_double:
                in_single = not in_single
            
            i += 1
        
        return in_single or in_double  # 三引号可以跨行，这里不检查
    
    def _check_indentation(self, code: str, result: VerificationResult):
        """检查缩进一致性"""
        lines = code.split('\n')
        indent_chars = set()  # 记录使用的缩进字符
        
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            
            # 获取行首空白
            leading = len(line) - len(line.lstrip())
            if leading > 0:
                # 检查混合Tab和空格
                leading_chars = line[:leading]
                if '\t' in leading_chars and ' ' in leading_chars:
                    result.add_warning(
                        'mixed_indent',
                        f'第{i}行混合使用Tab和空格缩进',
                        line=i
                    )
                
                # 记录缩进字符
                if '\t' in leading_chars:
                    indent_chars.add('tab')
                if ' ' in leading_chars:
                    indent_chars.add('space')
        
        # 检查整体缩进一致性
        if len(indent_chars) > 1:
            result.add_warning(
                'inconsistent_indent',
                '代码中同时使用了Tab和空格缩进，建议统一使用空格'
            )
    
    def _check_brackets(self, code: str, result: VerificationResult):
        """检查括号配对"""
        brackets = {'(': ')', '[': ']', '{': '}'}
        stack = []
        
        # 跳过字符串和注释
        in_string = None
        i = 0
        line_num = 1
        
        while i < len(code):
            char = code[i]
            
            # 跟踪行号
            if char == '\n':
                line_num += 1
                i += 1
                continue
            
            # 处理注释
            if char == '#' and in_string is None:
                # 跳到行尾
                while i < len(code) and code[i] != '\n':
                    i += 1
                continue
            
            # 处理字符串
            if char in '"\'':
                if code[i:i+3] in ('"""', "'''"):
                    if in_string == code[i:i+3]:
                        in_string = None
                    elif in_string is None:
                        in_string = code[i:i+3]
                    i += 3
                    continue
                else:
                    if in_string == char:
                        in_string = None
                    elif in_string is None:
                        in_string = char
            
            # 在字符串外检查括号
            if in_string is None:
                if char in brackets:
                    stack.append((char, line_num))
                elif char in brackets.values():
                    if not stack:
                        result.add_error(
                            'unmatched_bracket',
                            f'第{line_num}行有多余的闭合括号 "{char}"',
                            line=line_num,
                            suggestion='检查是否有多余的闭合括号'
                        )
                    else:
                        open_bracket, open_line = stack.pop()
                        if brackets[open_bracket] != char:
                            result.add_error(
                                'mismatched_bracket',
                                f'第{line_num}行的 "{char}" 与第{open_line}行的 "{open_bracket}" 不匹配',
                                line=line_num,
                                suggestion=f'期望 "{brackets[open_bracket]}"'
                            )
            
            i += 1
        
        # 检查未闭合的括号
        for open_bracket, open_line in stack:
            result.add_error(
                'unclosed_bracket',
                f'第{open_line}行的 "{open_bracket}" 未闭合',
                line=open_line,
                suggestion=f'添加对应的 "{brackets[open_bracket]}"'
            )
    
    def _check_common_errors(self, code: str, result: VerificationResult):
        """检查常见错误模式"""
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 检查 = 和 == 混淆
            if re.search(r'\bif\b.*[^=!<>]=[^=]', line):
                # 排除 f-string 和字典
                if not re.search(r'[{\'"].*=.*[}\'\"]', line):
                    result.add_warning(
                        'assignment_in_condition',
                        f'第{i}行条件语句中使用了赋值运算符(=)，是否应该用(==)?',
                        line=i
                    )
            
            # 检查缺少 self 的方法定义
            if re.match(r'\s*def\s+\w+\s*\(\s*\)', stripped):
                # 检查是否在类内部（简单启发式）
                for j in range(i-1, max(0, i-20), -1):
                    if lines[j-1].strip().startswith('class '):
                        result.add_warning(
                            'missing_self',
                            f'第{i}行的方法定义可能缺少 self 参数',
                            line=i
                        )
                        break
    
    def _check_safety(self, code: str, result: VerificationResult):
        """检查危险代码（仅警告）"""
        # 检查危险的内置函数
        for builtin in self.DANGEROUS_BUILTINS:
            if re.search(r'\b' + builtin + r'\s*\(', code):
                result.add_warning(
                    'dangerous_builtin',
                    f'检测到危险函数调用: {builtin}()',
                )
        
        # 检查危险的模块调用
        for call in self.DANGEROUS_CALLS:
            if call in code:
                result.add_warning(
                    'dangerous_call',
                    f'检测到危险调用: {call}',
                )
    
    def _suggest_fix_for_syntax_error(self, error: SyntaxError) -> str:
        """为语法错误提供修复建议"""
        msg = str(error.msg) if hasattr(error, 'msg') else str(error)
        msg_lower = msg.lower()
        
        suggestions = {
            'expected an indented block': '检查缩进，可能需要添加 pass 或实际代码',
            'unexpected indent': '检查缩进级别是否正确',
            'invalid syntax': '检查语法，可能缺少冒号、括号或引号',
            'unexpected eof': '检查是否有未闭合的括号、字符串或代码块',
            "expected ':'": '在语句末尾添加冒号(:)',
            'expected except': '在 try 块后添加 except 或 finally',
            'expected finally': '在 try-except 后可选添加 finally',
            'unterminated string': '检查字符串引号是否配对',
            'unmatched': '检查括号是否配对',
        }
        
        for pattern, suggestion in suggestions.items():
            if pattern in msg_lower:
                return suggestion
        
        return '检查语法错误附近的代码'
    
    def quick_check(self, code: str) -> Tuple[bool, str]:
        """
        快速检查 - 仅返回是否通过和第一个错误
        
        Args:
            code: 代码字符串
        
        Returns:
            (passed, first_error_message)
        """
        result = self.execute(code)
        if result.passed:
            return True, ''
        else:
            first_error = result.errors[0] if result.errors else {'message': '未知错误'}
            return False, first_error.get('message', '未知错误')

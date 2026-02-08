"""
鲁棒的 JSON 解析工具

处理 AI（如 DeepSeek）返回内容中常见的 JSON 格式问题：
- 尾随逗号 (trailing commas)       → ,} / ,]
- 单行注释                          → // ...
- 多行注释                          → /* ... */
- 被 Markdown 代码块包裹的 JSON     → ```json ... ```
- JSON 前后有多余文字
"""

import json
import re
from typing import Any


def safe_json_loads(text: str) -> Any:
    """
    鲁棒的 JSON 解析，依次尝试多种修复策略。

    Args:
        text: 可能包含 JSON 的字符串

    Returns:
        解析后的 Python 对象

    Raises:
        json.JSONDecodeError: 所有策略均失败时抛出
    """
    if not text or not text.strip():
        raise json.JSONDecodeError("空文本", text or "", 0)

    # 1. 直接解析
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2. 从 Markdown 代码块中提取
    code_match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', text)
    if code_match:
        try:
            return json.loads(code_match.group(1))
        except json.JSONDecodeError:
            pass

    # 3. 清理常见问题
    cleaned = _clean_json_string(text)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 4. 提取 {...} 或 [...] 部分
    for pattern in [r'\{[\s\S]*\}', r'\[[\s\S]*\]']:
        brace_match = re.search(pattern, cleaned)
        if brace_match:
            extracted = _clean_json_string(brace_match.group())
            try:
                return json.loads(extracted)
            except json.JSONDecodeError:
                continue

    # 5. 从 Markdown 代码块提取后再清理
    if code_match:
        cleaned_block = _clean_json_string(code_match.group(1))
        try:
            return json.loads(cleaned_block)
        except json.JSONDecodeError:
            pass

    # 全部失败
    raise json.JSONDecodeError(
        "所有 JSON 解析策略均失败", text[:200], 0
    )


def _clean_json_string(text: str) -> str:
    """
    清理 JSON 字符串中的常见格式问题。
    """
    cleaned = text.strip()

    # 移除单行注释 // ...（但不破坏 URL 中的 //）
    cleaned = re.sub(r'(?<!:)//[^\n]*', '', cleaned)

    # 移除多行注释 /* ... */
    cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)

    # 移除尾随逗号: ,} → }  和  ,] → ]
    for _ in range(10):
        prev = cleaned
        cleaned = re.sub(r',\s*([}\]])', r'\1', cleaned)
        if cleaned == prev:
            break

    return cleaned

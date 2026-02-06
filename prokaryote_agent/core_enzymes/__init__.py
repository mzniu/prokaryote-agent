# -*- coding: utf-8 -*-
"""
核心酶层 (Core Enzymes)
======================

核心酶是原核生物Agent的"DNA转录机制"，是最原始、最核心的能力。
这些酶负责生成、验证、修复所有其他技能的代码。

⚠️ 安全警告 ⚠️
- 核心酶代码由开发者（上帝视角）手工编写和维护
- Agent 不得自主修改核心酶代码
- 修改核心酶需要人工审核

三大核心酶：
- CodeSynthase: 代码合成酶 - 调用LLM生成Python代码
- SyntaxVerifier: 语法校验酶 - 验证代码语法正确性
- ErrorRepairase: 错误修复酶 - 自动修复常见代码错误

技能生成管线：
  需求 → CodeSynthase → SyntaxVerifier → [ErrorRepairase] → 技能代码
"""

from .base import CoreEnzyme, EnzymeSecurityError
from .code_synthase import CodeSynthase
from .syntax_verifier import SyntaxVerifier, VerificationResult
from .error_repairase import ErrorRepairase
from .pipeline import SkillPipeline, PipelineError

__all__ = [
    # 基类
    'CoreEnzyme',
    'EnzymeSecurityError',
    # 三大核心酶
    'CodeSynthase',
    'SyntaxVerifier',
    'VerificationResult',
    'ErrorRepairase',
    # 管线
    'SkillPipeline',
    'PipelineError',
]

# 核心酶版本（整体版本，人工更新）
CORE_ENZYME_VERSION = "1.0.0"

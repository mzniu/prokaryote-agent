# -*- coding: utf-8 -*-
"""
核心酶测试
==========

测试三大核心酶的功能：
- CoreEnzyme 基类
- CodeSynthase 代码合成酶
- SyntaxVerifier 语法校验酶
- ErrorRepairase 错误修复酶
- SkillPipeline 技能生成管线
"""

import pytest
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent.core_enzymes import (
    CoreEnzyme, 
    EnzymeSecurityError,
    CodeSynthase, 
    SyntaxVerifier, 
    VerificationResult,
    ErrorRepairase,
    SkillPipeline,
    PipelineError
)


class TestCoreEnzymeBase:
    """测试 CoreEnzyme 基类"""
    
    def test_enzyme_immutable_flag(self):
        """测试不可变标记"""
        verifier = SyntaxVerifier()
        assert verifier.IS_IMMUTABLE is True
        assert verifier.REQUIRE_GODMODE is True
    
    def test_enzyme_integrity_check(self):
        """测试完整性校验"""
        verifier = SyntaxVerifier()
        assert verifier.verify_integrity() is True
    
    def test_enzyme_stats(self):
        """测试统计信息"""
        verifier = SyntaxVerifier()
        stats = verifier.get_stats()
        
        assert 'name' in stats
        assert 'version' in stats
        assert 'call_count' in stats
        assert stats['name'] == 'SyntaxVerifier'


class TestSyntaxVerifier:
    """测试 SyntaxVerifier 语法校验酶"""
    
    def test_valid_code(self):
        """测试有效代码"""
        verifier = SyntaxVerifier()
        code = '''
def hello():
    print("Hello, World!")
    return True
'''
        result = verifier(code)
        assert result.passed is True
        assert len(result.errors) == 0
    
    def test_syntax_error(self):
        """测试语法错误检测"""
        verifier = SyntaxVerifier()
        code = '''
def hello()  # 缺少冒号
    print("Hello")
'''
        result = verifier(code)
        assert result.passed is False
        assert len(result.errors) > 0
        assert result.errors[0]['type'] == 'syntax_error'
    
    def test_unclosed_bracket(self):
        """测试未闭合括号检测"""
        verifier = SyntaxVerifier()
        code = '''
def hello():
    data = [1, 2, 3
    return data
'''
        result = verifier(code)
        assert result.passed is False
    
    def test_try_without_except(self):
        """测试try块缺少except"""
        verifier = SyntaxVerifier()
        code = '''
def hello():
    try:
        x = 1
    # 缺少except或finally
    return x
'''
        result = verifier(code)
        assert result.passed is False
    
    def test_quick_check(self):
        """测试快速检查"""
        verifier = SyntaxVerifier()
        
        # 有效代码
        passed, error = verifier.quick_check('x = 1 + 2')
        assert passed is True
        assert error == ''
        
        # 无效代码
        passed, error = verifier.quick_check('x = ')
        assert passed is False
        assert error != ''
    
    def test_dangerous_code_warning(self):
        """测试危险代码警告"""
        verifier = SyntaxVerifier()
        code = '''
def dangerous():
    result = eval("1+1")
    return result
'''
        result = verifier(code)
        # 语法正确，但有安全警告
        assert result.passed is True
        assert len(result.warnings) > 0
        assert any('eval' in w.get('message', '') for w in result.warnings)


class TestErrorRepairase:
    """测试 ErrorRepairase 错误修复酶"""
    
    def test_fix_missing_colon(self):
        """测试修复缺少冒号"""
        repairase = ErrorRepairase()
        code = '''
def hello()
    return True
'''
        errors = [{'type': 'syntax_error', 'message': "expected ':'", 'line': 2}]
        result = repairase(code, errors)
        
        # 检查是否尝试了修复
        assert 'code' in result
    
    def test_fix_try_block(self):
        """测试修复try块"""
        repairase = ErrorRepairase()
        code = '''
def hello():
    try:
        x = 1
'''
        errors = [{'type': 'syntax_error', 'message': 'expected except', 'line': 4}]
        result = repairase(code, errors)
        
        # 检查修复结果
        assert 'code' in result
        if result['success']:
            assert 'except' in result['code']
    
    def test_fix_indentation(self):
        """测试修复缩进"""
        repairase = ErrorRepairase()
        # 使用Tab的代码
        code = "def hello():\n\treturn True"
        
        result = repairase._fix_indentation_issues(code)
        
        # Tab应该被转换为空格
        if result['fixed']:
            assert '\t' not in result['code']


class TestCodeSynthase:
    """测试 CodeSynthase 代码合成酶"""
    
    def test_fallback_generation(self):
        """测试备用模板生成"""
        synthase = CodeSynthase(ai_adapter=None)
        
        skill_spec = {
            'id': 'test_skill',
            'name': '测试技能',
            'description': '这是一个测试技能',
            'domain': 'test',
            'tier': 'basic',
            'capabilities': ['测试能力1', '测试能力2']
        }
        
        # 使用备用模板（因为没有AI适配器）
        result = synthase._generate_fallback(skill_spec)
        
        assert 'class TestSkill' in result
        assert 'def execute' in result
        assert '测试技能' in result
    
    def test_class_name_conversion(self):
        """测试类名转换"""
        synthase = CodeSynthase()
        
        assert synthase._to_class_name('test_skill') == 'TestSkill'
        assert synthase._to_class_name('legal_research_basic') == 'LegalResearchBasic'
        assert synthase._to_class_name('hello') == 'Hello'
    
    def test_fix_indentation(self):
        """测试缩进修复"""
        synthase = CodeSynthase()
        
        code = "line1\n  line2\n    line3"
        fixed = synthase._fix_indentation(code, 8)
        
        lines = fixed.split('\n')
        assert lines[0].startswith(' ' * 8)


class TestSkillPipeline:
    """测试 SkillPipeline 技能生成管线"""
    
    def test_pipeline_initialization(self):
        """测试管线初始化"""
        pipeline = SkillPipeline()
        
        assert pipeline.synthase is not None
        assert pipeline.verifier is not None
        assert pipeline.repairase is not None
    
    def test_enzyme_verification(self):
        """测试核心酶完整性验证"""
        pipeline = SkillPipeline()
        
        integrity = pipeline.verify_enzymes()
        
        assert integrity['CodeSynthase'] is True
        assert integrity['SyntaxVerifier'] is True
        assert integrity['ErrorRepairase'] is True
    
    def test_pipeline_stats(self):
        """测试管线统计"""
        pipeline = SkillPipeline()
        
        stats = pipeline.get_stats()
        
        assert 'pipeline_version' in stats
        assert 'total_generations' in stats
        assert 'enzymes' in stats
        assert 'CodeSynthase' in stats['enzymes']
    
    def test_generate_with_fallback(self):
        """测试生成（使用备用模板）"""
        pipeline = SkillPipeline(ai_adapter=None)
        
        skill_spec = {
            'id': 'simple_test',
            'name': '简单测试',
            'description': '测试技能',
            'domain': 'test',
            'tier': 'basic',
            'capabilities': ['测试']
        }
        
        result = pipeline.generate(skill_spec)
        
        # 备用模板应该成功
        assert result['skill_id'] == 'simple_test'
        # 结果应该包含代码（即使是备用模板）
        assert 'code' in result


class TestIntegration:
    """集成测试"""
    
    def test_verifier_to_repairase_flow(self):
        """测试验证器到修复器的流程"""
        verifier = SyntaxVerifier()
        repairase = ErrorRepairase()
        
        # 有问题的代码
        code = '''
def hello():
    try:
        x = 1
'''
        
        # 验证
        verify_result = verifier(code)
        assert verify_result.passed is False
        
        # 修复
        repair_result = repairase(code, verify_result.errors)
        
        # 检查修复结果
        assert 'code' in repair_result
    
    def test_full_pipeline_flow(self):
        """测试完整管线流程"""
        pipeline = SkillPipeline()
        
        # 简单的技能定义
        skill_spec = {
            'id': 'hello_world',
            'name': 'Hello World',
            'description': '打印Hello World',
            'domain': 'test',
            'tier': 'basic',
            'capabilities': ['打印信息']
        }
        
        # 生成
        result = pipeline.generate(skill_spec)
        
        # 检查结果结构
        assert 'success' in result
        assert 'code' in result
        assert 'skill_id' in result
        assert 'attempts' in result


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])

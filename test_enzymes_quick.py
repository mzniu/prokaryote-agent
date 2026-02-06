# -*- coding: utf-8 -*-
"""快速测试核心酶功能"""

import sys
sys.path.insert(0, '.')

def main():
    # 测试导入
    print('=== 测试导入 ===')
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
    print('✓ 所有核心酶导入成功')

    # 测试 SyntaxVerifier
    print('\n=== 测试 SyntaxVerifier ===')
    verifier = SyntaxVerifier()
    print(f'  版本: {verifier.ENZYME_VERSION}')
    print(f'  不可变: {verifier.IS_IMMUTABLE}')

    # 测试有效代码
    result = verifier('def hello(): return True')
    print(f'  有效代码测试: passed={result.passed}')
    assert result.passed, "有效代码应该通过验证"

    # 测试无效代码
    result = verifier('def hello() return True')  # 缺少冒号
    print(f'  无效代码测试: passed={result.passed}, errors={len(result.errors)}')
    assert not result.passed, "无效代码不应该通过验证"

    # 测试 ErrorRepairase
    print('\n=== 测试 ErrorRepairase ===')
    repairase = ErrorRepairase()
    print(f'  版本: {repairase.ENZYME_VERSION}')
    print(f'  不可变: {repairase.IS_IMMUTABLE}')

    # 测试 CodeSynthase
    print('\n=== 测试 CodeSynthase ===')
    synthase = CodeSynthase()
    print(f'  版本: {synthase.ENZYME_VERSION}')

    # 测试备用模板
    fallback = synthase._generate_fallback({
        'id': 'test_skill',
        'name': '测试技能',
        'description': '测试',
        'domain': 'test',
        'tier': 'basic',
        'capabilities': ['测试']
    })
    print(f'  备用模板生成: {len(fallback)} 字符')
    has_class = 'class TestSkill' in fallback
    print(f'  包含类定义: {has_class}')
    assert has_class, "备用模板应该包含类定义"

    # 验证生成的代码
    result = verifier(fallback)
    print(f'  备用模板语法检查: passed={result.passed}')
    assert result.passed, "备用模板应该通过语法检查"

    # 测试 SkillPipeline
    print('\n=== 测试 SkillPipeline ===')
    pipeline = SkillPipeline()
    print(f'  管线版本: {pipeline.PIPELINE_VERSION}')

    # 验证核心酶完整性
    integrity = pipeline.verify_enzymes()
    print(f'  核心酶完整性: {integrity}')
    assert all(integrity.values()), "所有核心酶完整性应该为True"

    # 测试生成
    print('\n=== 测试技能生成 ===')
    result = pipeline.generate({
        'id': 'hello_test',
        'name': 'Hello Test',
        'description': '一个简单测试',
        'domain': 'test',
        'tier': 'basic',
        'capabilities': ['打印', '返回']
    })

    print(f'  生成结果: success={result["success"]}')
    print(f'  尝试次数: {result["attempts"]}')
    print(f'  代码长度: {len(result.get("code", ""))} 字符')

    if result['success']:
        # 验证生成的代码
        verify_result = verifier(result['code'])
        print(f'  代码语法检查: passed={verify_result.passed}')
        
        if verify_result.passed:
            print('\n  --- 生成的代码片段 ---')
            lines = result['code'].split('\n')
            for line in lines[:20]:
                print(f'  | {line}')
            if len(lines) > 20:
                print(f'  | ... ({len(lines) - 20} more lines)')
    else:
        print(f'  错误: {result.get("error", "未知错误")}')

    print('\n' + '='*50)
    print('✓ 核心酶测试完成!')
    print('='*50)

if __name__ == '__main__':
    main()

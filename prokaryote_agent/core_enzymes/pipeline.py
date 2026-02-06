# -*- coding: utf-8 -*-
"""
技能生成管线 (Skill Pipeline)
==============================

串联三大核心酶，实现完整的技能代码生成流程。

流程：
  技能规格 → CodeSynthase → SyntaxVerifier → [ErrorRepairase] → 技能代码
              (生成)          (验证)           (修复)

特性：
- 最多重试N次修复
- 记录生成历史
- 支持批量生成

⚠️ 核心酶警告：此代码只能由开发者（上帝视角）修改
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

from .base import CoreEnzyme, EnzymeSecurityError
from .code_synthase import CodeSynthase
from .syntax_verifier import SyntaxVerifier, VerificationResult
from .error_repairase import ErrorRepairase

logger = logging.getLogger(__name__)


class PipelineError(Exception):
    """管线执行错误"""
    pass


class SkillPipeline:
    """
    技能生成管线
    
    这是核心酶的协调器，按顺序调用三大核心酶完成技能代码生成。
    
    工作流程：
    1. CodeSynthase 生成代码
    2. SyntaxVerifier 验证语法
    3. 如果验证失败，ErrorRepairase 尝试修复
    4. 重复步骤2-3直到成功或达到最大重试次数
    
    ⚠️ 此类是核心酶的协调层，同样遵循不可自主修改原则
    """
    
    # 管线配置
    MAX_REPAIR_ATTEMPTS = 3     # 最大修复尝试次数
    PIPELINE_VERSION = "1.0.0"  # 管线版本
    
    def __init__(self, ai_adapter=None):
        """
        初始化技能生成管线
        
        Args:
            ai_adapter: AI适配器实例，共享给需要的核心酶
        """
        # 初始化三大核心酶
        self.synthase = CodeSynthase(ai_adapter=ai_adapter)
        self.verifier = SyntaxVerifier()
        self.repairase = ErrorRepairase(ai_adapter=ai_adapter)
        
        # 管线状态
        self._generation_count = 0
        self._success_count = 0
        self._history = []
        
        logger.info(f"[SkillPipeline] 初始化完成 v{self.PIPELINE_VERSION}")
        logger.info(f"  - CodeSynthase v{self.synthase.ENZYME_VERSION}")
        logger.info(f"  - SyntaxVerifier v{self.verifier.ENZYME_VERSION}")
        logger.info(f"  - ErrorRepairase v{self.repairase.ENZYME_VERSION}")
    
    def generate(self, skill_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        生成技能代码
        
        这是管线的主入口，完成从规格到代码的完整流程。
        
        Args:
            skill_spec: 技能规格
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
                'code': str,             # 生成的代码
                'skill_id': str,         # 技能ID
                'attempts': int,         # 尝试次数
                'repairs': List[str],    # 修复记录
                'error': str             # 错误信息（如果失败）
            }
        """
        skill_id = skill_spec.get('id', 'unknown')
        self._generation_count += 1
        
        start_time = datetime.now()
        logger.info(f"[SkillPipeline] ===== 开始生成技能: {skill_id} =====")
        
        result = {
            'success': False,
            'code': '',
            'skill_id': skill_id,
            'attempts': 0,
            'repairs': [],
            'error': ''
        }
        
        try:
            # Step 1: 代码合成
            logger.info(f"[SkillPipeline] Step 1: 调用 CodeSynthase")
            synth_result = self.synthase(skill_spec)
            
            if not synth_result.get('success'):
                result['error'] = f"代码合成失败: {synth_result.get('error', '未知错误')}"
                self._record_history(skill_id, result, start_time)
                return result
            
            code = synth_result['code']
            result['attempts'] = 1
            
            # Step 2: 验证-修复循环
            for attempt in range(self.MAX_REPAIR_ATTEMPTS + 1):
                logger.info(f"[SkillPipeline] Step 2: 验证尝试 {attempt + 1}/{self.MAX_REPAIR_ATTEMPTS + 1}")
                
                # 验证
                verify_result = self.verifier(code)
                
                if verify_result.passed:
                    # 验证通过！
                    result['success'] = True
                    result['code'] = code
                    result['attempts'] = attempt + 1
                    
                    # 记录警告
                    if verify_result.warnings:
                        for w in verify_result.warnings:
                            logger.warning(f"[SkillPipeline] 警告: {w.get('message', '')}")
                    
                    self._success_count += 1
                    logger.info(f"[SkillPipeline] ✓ 技能生成成功: {skill_id}")
                    self._record_history(skill_id, result, start_time)
                    return result
                
                # 验证失败
                if attempt >= self.MAX_REPAIR_ATTEMPTS:
                    # 达到最大重试次数
                    errors_str = '; '.join(e.get('message', '') for e in verify_result.errors)
                    result['error'] = f"修复{self.MAX_REPAIR_ATTEMPTS}次后仍有错误: {errors_str}"
                    logger.error(f"[SkillPipeline] ✗ 达到最大修复次数")
                    break
                
                # Step 3: 尝试修复
                logger.info(f"[SkillPipeline] Step 3: 调用 ErrorRepairase")
                repair_result = self.repairase(code, verify_result.errors)
                
                if repair_result.get('success'):
                    code = repair_result['code']
                    result['repairs'].extend(repair_result.get('repairs', []))
                    logger.info(f"[SkillPipeline] 修复完成: {repair_result.get('repairs', [])}")
                else:
                    # 修复失败
                    remaining = repair_result.get('remaining_errors', [])
                    errors_str = '; '.join(e.get('message', '') for e in remaining)
                    result['error'] = f"修复失败: {errors_str}"
                    logger.error(f"[SkillPipeline] 修复失败: {errors_str}")
                    break
                
                result['attempts'] = attempt + 2
            
        except EnzymeSecurityError as e:
            result['error'] = f"核心酶安全错误: {e}"
            logger.error(f"[SkillPipeline] 安全错误: {e}")
        except Exception as e:
            result['error'] = f"管线异常: {e}"
            logger.exception(f"[SkillPipeline] 异常: {e}")
        
        self._record_history(skill_id, result, start_time)
        return result
    
    def generate_batch(self, skill_specs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        批量生成技能代码
        
        Args:
            skill_specs: 技能规格列表
        
        Returns:
            生成结果列表
        """
        results = []
        total = len(skill_specs)
        
        logger.info(f"[SkillPipeline] 批量生成 {total} 个技能")
        
        for i, spec in enumerate(skill_specs, 1):
            logger.info(f"[SkillPipeline] 处理 {i}/{total}: {spec.get('id', 'unknown')}")
            result = self.generate(spec)
            results.append(result)
        
        success_count = sum(1 for r in results if r['success'])
        logger.info(f"[SkillPipeline] 批量生成完成: {success_count}/{total} 成功")
        
        return results
    
    def _record_history(self, skill_id: str, result: Dict[str, Any], 
                        start_time: datetime):
        """记录生成历史"""
        end_time = datetime.now()
        duration = (end_time - start_time).total_seconds()
        
        record = {
            'skill_id': skill_id,
            'success': result['success'],
            'attempts': result['attempts'],
            'repairs': result['repairs'],
            'error': result.get('error', ''),
            'start_time': start_time.isoformat(),
            'end_time': end_time.isoformat(),
            'duration_seconds': duration
        }
        
        self._history.append(record)
        
        # 保持历史记录在合理范围内
        if len(self._history) > 100:
            self._history = self._history[-100:]
    
    def get_stats(self) -> Dict[str, Any]:
        """获取管线统计信息"""
        return {
            'pipeline_version': self.PIPELINE_VERSION,
            'total_generations': self._generation_count,
            'successful_generations': self._success_count,
            'success_rate': self._success_count / max(1, self._generation_count),
            'enzymes': {
                'CodeSynthase': self.synthase.get_stats(),
                'SyntaxVerifier': self.verifier.get_stats(),
                'ErrorRepairase': self.repairase.get_stats(),
            },
            'recent_history': self._history[-10:] if self._history else []
        }
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """获取最近的生成历史"""
        return self._history[-limit:] if self._history else []
    
    def verify_enzymes(self) -> Dict[str, bool]:
        """验证所有核心酶的完整性"""
        return {
            'CodeSynthase': self.synthase.verify_integrity(),
            'SyntaxVerifier': self.verifier.verify_integrity(),
            'ErrorRepairase': self.repairase.verify_integrity(),
        }


# 便捷函数：获取全局管线实例
_global_pipeline: Optional[SkillPipeline] = None


def get_skill_pipeline(ai_adapter=None) -> SkillPipeline:
    """
    获取全局技能生成管线实例
    
    Args:
        ai_adapter: AI适配器（仅在首次调用时使用）
    
    Returns:
        SkillPipeline 实例
    """
    global _global_pipeline
    if _global_pipeline is None:
        _global_pipeline = SkillPipeline(ai_adapter=ai_adapter)
    return _global_pipeline


def generate_skill_code(skill_spec: Dict[str, Any]) -> Dict[str, Any]:
    """
    便捷函数：生成技能代码
    
    Args:
        skill_spec: 技能规格
    
    Returns:
        生成结果
    """
    pipeline = get_skill_pipeline()
    return pipeline.generate(skill_spec)

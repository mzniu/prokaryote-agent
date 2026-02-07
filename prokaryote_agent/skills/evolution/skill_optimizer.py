"""
技能自优化器 - 当训练失败时自动分析原因并优化技能实现

设计思路：
1. 检测连续训练失败（如连续3次失败）
2. 分析失败原因（产出物太小、知识存储为0、分析深度不足等）
3. 生成优化建议或自动优化技能代码
4. 重新训练验证优化效果

核心流程：
  train() → fail → analyze_failure() → optimize_skill() → retrain()
"""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class SkillOptimizer:
    """技能自优化器"""

    # 失败原因类型
    FAILURE_TYPES = {
        'output_too_small': '产出物体量过小',
        'no_knowledge_stored': '知识存储量为0',
        'low_analysis_depth': '分析深度不足',
        'missing_legal_refs': '缺少法律引用',
        'low_relevance': '相关性不足',
        'timeout': '执行超时',
        'error': '执行错误',
    }

    # 每种失败类型对应的优化策略
    OPTIMIZATION_STRATEGIES = {
        'output_too_small': [
            'increase_analysis_length',
            'add_more_sections',
            'use_ai_generation',
        ],
        'no_knowledge_stored': [
            'fix_storage_logic',
            'enable_web_search',
            'lower_storage_threshold',
        ],
        'low_analysis_depth': [
            'add_ai_analysis',
            'increase_search_keywords',
            'add_context_integration',
        ],
        'missing_legal_refs': [
            'add_law_search',
            'add_case_search',
            'expand_legal_categories',
        ],
        'low_relevance': [
            'improve_keyword_extraction',
            'add_semantic_search',
            'filter_irrelevant_results',
        ],
    }

    def __init__(self, max_failures: int = 3, auto_optimize: bool = False):
        """
        初始化优化器

        Args:
            max_failures: 触发优化的最大失败次数
            auto_optimize: 是否自动优化（False时只生成建议）
        """
        self.max_failures = max_failures
        self.auto_optimize = auto_optimize
        self.failure_history: Dict[str, List[Dict]] = {}

    def record_failure(
        self,
        skill_id: str,
        level: int,
        eval_result: Dict[str, Any],
        execution_result: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        记录训练失败

        Args:
            skill_id: 技能ID
            level: 当前技能等级
            eval_result: 评估结果（包含分数、详细反馈等）
            execution_result: 执行结果（包含产出物等）

        Returns:
            包含连续失败次数、是否需要优化、失败分析
        """
        if skill_id not in self.failure_history:
            self.failure_history[skill_id] = []

        failure_record = {
            'timestamp': datetime.now().isoformat(),
            'level': level,
            'score': eval_result.get('score', 0),
            'feedback': eval_result.get('feedback', ''),
            'dimensions': eval_result.get('dimensions', {}),
            'execution_result': self._extract_key_info(execution_result),
        }

        self.failure_history[skill_id].append(failure_record)

        # 统计连续失败次数
        consecutive = self._count_consecutive_failures(skill_id)

        # 分析失败原因
        failure_analysis = self.analyze_failures(skill_id)

        should_optimize = consecutive >= self.max_failures

        result = {
            'consecutive_failures': consecutive,
            'should_optimize': should_optimize,
            'failure_analysis': failure_analysis,
        }

        if should_optimize:
            logger.warning(
                "技能 %s 连续失败 %d 次，建议进行优化",
                skill_id, consecutive
            )
            result['optimization_suggestions'] = \
                self.generate_optimization_suggestions(skill_id, failure_analysis)

        return result

    def record_success(self, skill_id: str):
        """记录训练成功，清空失败历史"""
        if skill_id in self.failure_history:
            self.failure_history[skill_id] = []

    def _extract_key_info(self, execution_result: Dict) -> Dict:
        """提取执行结果的关键信息"""
        result = execution_result.get('result', {})
        return {
            'output_size': len(str(result)),
            'knowledge_stats': result.get('knowledge_stats', {}),
            'has_analysis': bool(result.get('analysis', '')),
            'analysis_length': len(result.get('analysis', '')),
            'legal_refs_count': len(result.get('applicable_laws', [])),
            'key_facts_count': len(result.get('key_facts', [])),
        }

    def _count_consecutive_failures(self, skill_id: str) -> int:
        """统计连续失败次数"""
        failures = self.failure_history.get(skill_id, [])
        return len(failures)  # 成功时会清空，所以长度即连续失败次数

    def analyze_failures(self, skill_id: str) -> Dict[str, Any]:
        """
        分析失败原因

        Returns:
            包含主要原因、原因列表、模式统计
        """
        failures = self.failure_history.get(skill_id, [])
        if not failures:
            return {'primary_cause': 'unknown', 'causes': []}

        causes = []
        recent_failures = failures[-3:]
        num_failures = len(recent_failures)

        # 1. 检查产出物大小
        avg_output_size = sum(
            f['execution_result'].get('output_size', 0)
            for f in recent_failures
        ) / num_failures

        if avg_output_size < 500:
            causes.append({
                'type': 'output_too_small',
                'confidence': min(1.0, (500 - avg_output_size) / 500),
                'evidence': '平均产出物大小: %.0f 字符' % avg_output_size,
            })

        # 2. 检查知识存储
        avg_stored = sum(
            f['execution_result'].get('knowledge_stats', {}).get('stored', 0)
            for f in recent_failures
        ) / num_failures

        if avg_stored == 0:
            causes.append({
                'type': 'no_knowledge_stored',
                'confidence': 1.0,
                'evidence': '最近训练均未存储新知识',
            })

        # 3. 检查分析深度
        avg_analysis_len = sum(
            f['execution_result'].get('analysis_length', 0)
            for f in recent_failures
        ) / num_failures

        if avg_analysis_len < 200:
            causes.append({
                'type': 'low_analysis_depth',
                'confidence': min(1.0, (200 - avg_analysis_len) / 200),
                'evidence': '平均分析长度: %.0f 字符' % avg_analysis_len,
            })

        # 4. 检查法律引用
        avg_refs = sum(
            f['execution_result'].get('legal_refs_count', 0)
            for f in recent_failures
        ) / num_failures

        if avg_refs < 2:
            causes.append({
                'type': 'missing_legal_refs',
                'confidence': min(1.0, (2 - avg_refs) / 2),
                'evidence': '平均法律引用数: %.1f' % avg_refs,
            })

        # 5. 从评估反馈中提取
        for f in recent_failures:
            feedback = f.get('feedback', '').lower()
            if '相关' in feedback and ('不' in feedback or '低' in feedback):
                causes.append({
                    'type': 'low_relevance',
                    'confidence': 0.7,
                    'evidence': '评估反馈提及相关性问题',
                })
                break

        # 按置信度排序
        causes.sort(key=lambda x: x['confidence'], reverse=True)
        primary_cause = causes[0]['type'] if causes else 'unknown'

        return {
            'primary_cause': primary_cause,
            'primary_cause_desc': self.FAILURE_TYPES.get(primary_cause, '未知原因'),
            'causes': causes,
            'patterns': {
                'avg_output_size': avg_output_size,
                'avg_knowledge_stored': avg_stored,
                'avg_analysis_length': avg_analysis_len,
                'avg_legal_refs': avg_refs,
            }
        }

    def generate_optimization_suggestions(
        self,
        skill_id: str,
        failure_analysis: Dict
    ) -> List[Dict]:
        """生成优化建议"""
        suggestions = []
        causes = failure_analysis.get('causes', [])

        for cause in causes[:3]:
            cause_type = cause['type']
            strategies = self.OPTIMIZATION_STRATEGIES.get(cause_type, [])

            for strategy in strategies:
                suggestion = self._create_suggestion(cause_type, strategy, cause)
                if suggestion:
                    suggestions.append(suggestion)

        suggestions.sort(key=lambda x: x.get('priority', 99))
        return suggestions

    def _create_suggestion(
        self,
        cause_type: str,
        strategy: str,
        cause_info: Dict
    ) -> Optional[Dict]:
        """创建具体的优化建议"""
        suggestion_templates = {
            ('output_too_small', 'increase_analysis_length'): {
                'description': '增加分析内容的长度要求，使用更详细的分析模板',
                'priority': 1,
                'implementation': 'modify_analysis_template',
            },
            ('output_too_small', 'add_more_sections'): {
                'description': '添加更多分析维度（如风险分析、时间线分析等）',
                'priority': 2,
                'implementation': 'add_sections',
            },
            ('output_too_small', 'use_ai_generation'): {
                'description': '使用 AI 生成更丰富的分析内容',
                'priority': 3,
                'implementation': 'enable_ai_analysis',
            },
            ('no_knowledge_stored', 'fix_storage_logic'): {
                'description': '检查并修复知识存储逻辑，确保搜索结果被正确存储',
                'priority': 1,
                'implementation': 'fix_store_knowledge_call',
            },
            ('no_knowledge_stored', 'enable_web_search'): {
                'description': '启用网络搜索并存储搜索结果到知识库',
                'priority': 2,
                'implementation': 'add_web_search_and_store',
            },
            ('no_knowledge_stored', 'lower_storage_threshold'): {
                'description': '降低知识存储的内容长度阈值',
                'priority': 3,
                'implementation': 'adjust_storage_threshold',
            },
            ('low_analysis_depth', 'add_ai_analysis'): {
                'description': '添加 AI 驱动的深度分析功能',
                'priority': 1,
                'implementation': 'integrate_ai_analysis',
            },
            ('low_analysis_depth', 'increase_search_keywords'): {
                'description': '增加搜索关键词数量以获取更多背景信息',
                'priority': 2,
                'implementation': 'expand_keyword_extraction',
            },
            ('low_analysis_depth', 'add_context_integration'): {
                'description': '整合更多上下文信息到分析中',
                'priority': 3,
                'implementation': 'enhance_context_usage',
            },
            ('missing_legal_refs', 'add_law_search'): {
                'description': '添加专门的法律法规搜索',
                'priority': 1,
                'implementation': 'add_law_database_search',
            },
            ('missing_legal_refs', 'add_case_search'): {
                'description': '添加相关案例搜索',
                'priority': 2,
                'implementation': 'add_case_search',
            },
            ('low_relevance', 'improve_keyword_extraction'): {
                'description': '改进关键词提取算法，使用 NLP 或 AI',
                'priority': 1,
                'implementation': 'enhance_keyword_extraction',
            },
            ('low_relevance', 'add_semantic_search'): {
                'description': '添加语义搜索以提高结果相关性',
                'priority': 2,
                'implementation': 'add_semantic_search',
            },
        }

        template = suggestion_templates.get((cause_type, strategy))
        if not template:
            return None

        return {
            'cause_type': cause_type,
            'strategy': strategy,
            'description': template['description'],
            'priority': template['priority'],
            'implementation': template['implementation'],
            'evidence': cause_info.get('evidence', ''),
            'confidence': cause_info.get('confidence', 0),
        }

    def apply_optimization(
        self,
        skill_id: str,
        suggestion: Dict
    ) -> Dict[str, Any]:
        """
        应用优化建议（仅在 auto_optimize=True 时可用）

        目前实现为生成优化提示，供人工审核。
        """
        if not self.auto_optimize:
            return {
                'success': False,
                'error': 'auto_optimize is disabled',
                'suggestion': suggestion,
                'requires_review': True,
            }

        # TODO: 实现自动代码修改
        return {
            'success': False,
            'error': 'Auto-optimization not yet implemented',
            'suggestion': suggestion,
            'requires_review': True,
        }

    def ai_repair_skill(
        self,
        skill_id: str,
        failure_analysis: Dict[str, Any],
        suggestions: List[Dict],
    ) -> Dict[str, Any]:
        """
        使用 LLM 修复连续失败的技能脚本

        流程：
        1. 读取技能当前源码
        2. 整合失败分析 + 优化建议 → 构造 prompt
        3. 调用 LLM 生成修复版代码
        4. 语法验证
        5. 备份原文件 → 写入新代码
        6. 重新加载技能

        Args:
            skill_id: 技能ID
            failure_analysis: 来自 analyze_failures 的失败分析
            suggestions: 来自 generate_optimization_suggestions 的建议列表

        Returns:
            {success, skill_id, backup_path, changes_summary, error}
        """
        from pathlib import Path

        logger.info(f"🔧 开始 AI 自修复技能: {skill_id}")

        # 1. 读取技能当前源码
        library_path = Path("prokaryote_agent/skills/library")
        skill_file = library_path / f"{skill_id}.py"

        if not skill_file.exists():
            return {
                'success': False,
                'skill_id': skill_id,
                'error': f'技能文件不存在: {skill_file}',
            }

        original_code = skill_file.read_text(encoding='utf-8')
        logger.info(f"   原始代码: {len(original_code)} 字符")

        # 2. 构造修复 prompt
        prompt = self._build_repair_prompt(
            skill_id, original_code, failure_analysis, suggestions
        )

        # 3. 调用 LLM
        try:
            from prokaryote_agent.ai_adapter import AIAdapter
            ai = AIAdapter()

            if not ai.config.api_key:
                return {
                    'success': False,
                    'skill_id': skill_id,
                    'error': 'AI API Key 未配置',
                }

            response = ai._call_ai(prompt)

            if not response.get('success'):
                return {
                    'success': False,
                    'skill_id': skill_id,
                    'error': f"AI 调用失败: {response.get('error')}",
                }

            new_code = self._extract_code_from_response(response['content'])

            if not new_code:
                return {
                    'success': False,
                    'skill_id': skill_id,
                    'error': 'AI 返回内容中未找到有效 Python 代码',
                }

            logger.info(f"   AI 生成修复代码: {len(new_code)} 字符")

        except Exception as e:
            logger.error(f"   AI 修复调用异常: {e}")
            return {
                'success': False,
                'skill_id': skill_id,
                'error': str(e),
            }

        # 4. 语法验证
        try:
            compile(new_code, f'{skill_id}.py', 'exec')
        except SyntaxError as e:
            logger.error(f"   修复代码语法错误: {e}")
            return {
                'success': False,
                'skill_id': skill_id,
                'error': f'修复代码语法错误: {e}',
            }

        # 5. 备份原文件
        versions_dir = library_path / ".versions"
        versions_dir.mkdir(exist_ok=True)

        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f"{skill_id}_pre_repair_{timestamp}.py"
        backup_path = versions_dir / backup_name
        backup_path.write_text(original_code, encoding='utf-8')
        logger.info(f"   已备份: {backup_path}")

        # 写入修复后的代码
        skill_file.write_text(new_code, encoding='utf-8')
        logger.info(f"   已写入修复代码: {skill_file}")

        # 6. 尝试重新加载
        reload_ok = self._try_reload_skill(skill_id, library_path)

        if not reload_ok:
            # 加载失败，回滚
            logger.warning(f"   修复代码加载失败，回滚到原版本")
            skill_file.write_text(original_code, encoding='utf-8')
            return {
                'success': False,
                'skill_id': skill_id,
                'error': '修复代码无法加载（已回滚）',
                'backup_path': str(backup_path),
            }

        # 清空失败历史（给修复后的版本一个干净的开始）
        self.record_success(skill_id)

        # 生成变更摘要
        changes = self._summarize_changes(original_code, new_code)

        logger.info(f"✅ 技能 {skill_id} AI 自修复成功")
        for ch in changes[:5]:
            logger.info(f"   - {ch}")

        return {
            'success': True,
            'skill_id': skill_id,
            'backup_path': str(backup_path),
            'changes_summary': changes,
            'code_size_before': len(original_code),
            'code_size_after': len(new_code),
        }

    def _build_repair_prompt(
        self,
        skill_id: str,
        source_code: str,
        failure_analysis: Dict,
        suggestions: List[Dict],
    ) -> str:
        """构造 LLM 修复 prompt"""
        # 失败原因描述
        causes_text = ""
        for cause in failure_analysis.get('causes', []):
            desc = self.FAILURE_TYPES.get(cause['type'], cause['type'])
            causes_text += f"- {desc} (置信度: {cause['confidence']:.0%})\n"
            causes_text += f"  证据: {cause.get('evidence', '')}\n"

        # 优化建议描述
        suggestions_text = ""
        for s in suggestions[:5]:
            suggestions_text += f"- [{s.get('strategy')}] {s.get('description')}\n"

        # 模式统计
        patterns = failure_analysis.get('patterns', {})
        patterns_text = ""
        if patterns:
            patterns_text = (
                f"- 平均产出物大小: {patterns.get('avg_output_size', 0):.0f} 字符\n"
                f"- 平均知识存储量: {patterns.get('avg_knowledge_stored', 0):.1f} 条\n"
                f"- 平均分析长度: {patterns.get('avg_analysis_length', 0):.0f} 字符\n"
                f"- 平均法律引用数: {patterns.get('avg_legal_refs', 0):.1f}\n"
            )

        prompt = f"""你是一个 Python 技能代码优化专家。请修复以下技能代码，使其能通过训练评估。

## 技能 ID
{skill_id}

## 当前源码
```python
{source_code}
```

## 连续失败分析
{causes_text}

## 统计数据
{patterns_text}

## 优化建议
{suggestions_text}

## 修复要求
1. 保持类名、方法签名和继承关系不变（必须继承 Skill 基类）
2. 保持 `__init__`, `get_capabilities`, `validate_input`, `execute`, `_save_output`, `get_usage_examples` 方法签名不变
3. 重点修复 `execute` 方法的实际逻辑
4. 确保 execute 返回格式为 {{'success': True/False, 'result': {{...}}}}
5. 如果使用 web_search，确保处理搜索失败的情况（try/except）
6. 产出物应该更丰富和完整，不只是模板框架
7. 如果有 AI 适配器可用（from prokaryote_agent.ai_adapter import AIAdapter），可以用它来增强分析质量
8. 如果有 SkillContext，确保通过 context.save_output() 保存产出物到知识库
9. 不要引入新的外部依赖（可用标准库 + prokaryote_agent 模块内的）

## 输出格式
只输出修复后的完整 Python 文件内容，放在 ```python ... ``` 代码块中。
不要输出解释或注释，只要代码。"""

        return prompt

    def _extract_code_from_response(self, content: str) -> Optional[str]:
        """从 LLM 响应中提取 Python 代码块"""
        if not content:
            return None

        # 查找 ```python ... ``` 代码块
        import re
        pattern = r'```python\s*\n(.*?)```'
        matches = re.findall(pattern, content, re.DOTALL)

        if matches:
            # 取最长的代码块（通常是完整文件）
            code = max(matches, key=len).strip()
            if len(code) > 50:  # 最小合理长度
                return code

        # 备选：尝试提取所有 ``` 代码块
        pattern2 = r'```\s*\n(.*?)```'
        matches2 = re.findall(pattern2, content, re.DOTALL)
        if matches2:
            code = max(matches2, key=len).strip()
            if len(code) > 50 and 'class ' in code and 'def execute' in code:
                return code

        # 最后手段：如果整个 content 看起来像 Python 代码
        if 'class ' in content and 'def execute' in content and 'import' in content:
            return content.strip()

        return None

    def _try_reload_skill(self, skill_id: str, library_path) -> bool:
        """尝试重新加载技能模块"""
        import importlib
        import importlib.util
        import sys

        skill_file = library_path / f"{skill_id}.py"

        try:
            # 清除旧的缓存模块
            if skill_id in sys.modules:
                del sys.modules[skill_id]

            spec = importlib.util.spec_from_file_location(
                skill_id, str(skill_file))
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # 检查是否有 Skill 子类
            from prokaryote_agent.skills.skill_base import Skill
            found = False
            for name, obj in vars(module).items():
                if (isinstance(obj, type)
                        and issubclass(obj, Skill)
                        and obj is not Skill):
                    found = True
                    break

            return found
        except Exception as e:
            logger.error(f"重新加载技能失败: {e}")
            return False

    def _summarize_changes(
        self, old_code: str, new_code: str
    ) -> List[str]:
        """简要总结代码变更"""
        changes = []

        old_lines = old_code.splitlines()
        new_lines = new_code.splitlines()

        # 行数变化
        diff = len(new_lines) - len(old_lines)
        if diff > 0:
            changes.append(f"代码增加了 {diff} 行 ({len(old_lines)} → {len(new_lines)})")
        elif diff < 0:
            changes.append(f"代码减少了 {abs(diff)} 行 ({len(old_lines)} → {len(new_lines)})")
        else:
            changes.append(f"代码行数不变 ({len(new_lines)} 行)")

        # 检查关键变更
        old_text = old_code.lower()
        new_text = new_code.lower()

        if 'aiAdapter' in new_code or 'ai_adapter' in new_code:
            if 'ai_adapter' not in old_text:
                changes.append("新增: AI 适配器集成")

        if 'web_search' in new_text and 'web_search' not in old_text:
            changes.append("新增: 网络搜索功能")

        if 'context.save_output' in new_text:
            if 'context.save_output' not in old_text:
                changes.append("新增: 知识库产出物保存")
            elif new_text.count('context.save_output') > old_text.count('context.save_output'):
                changes.append("增强: 更多产出物保存到知识库")

        if 'try:' in new_text:
            old_try = old_text.count('try:')
            new_try = new_text.count('try:')
            if new_try > old_try:
                changes.append(f"增强: 错误处理 ({old_try} → {new_try} 个 try 块)")

        if not changes[1:]:
            changes.append("代码逻辑已重构优化")

        return changes


# 全局优化器实例
_optimizer: Optional[SkillOptimizer] = None


def get_skill_optimizer(
    max_failures: int = 3,
    auto_optimize: bool = False
) -> SkillOptimizer:
    """获取或创建技能优化器实例"""
    global _optimizer
    if _optimizer is None:
        _optimizer = SkillOptimizer(max_failures, auto_optimize)
    return _optimizer


def record_training_result(
    skill_id: str,
    level: int,
    success: bool,
    eval_result: Dict = None,
    execution_result: Dict = None
) -> Optional[Dict]:
    """
    记录训练结果，失败时触发分析

    Args:
        skill_id: 技能ID
        level: 当前等级
        success: 是否成功
        eval_result: 评估结果
        execution_result: 执行结果

    Returns:
        失败时返回优化建议，成功时返回 None
    """
    optimizer = get_skill_optimizer()

    if success:
        optimizer.record_success(skill_id)
        return None
    else:
        return optimizer.record_failure(
            skill_id, level,
            eval_result or {},
            execution_result or {}
        )

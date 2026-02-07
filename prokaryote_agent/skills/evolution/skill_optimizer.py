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
            'reason': eval_result.get('reason', ''),
            'summary': eval_result.get('summary', ''),
            'dimension_scores': eval_result.get('dimension_scores', []),
            'improvement_suggestions': eval_result.get(
                'improvement_suggestions', []),
            'method': eval_result.get('method', ''),
            'execution_result': self._extract_key_info(execution_result),
        }

        self.failure_history[skill_id].append(failure_record)

        # 统计连续失败次数
        consecutive = self._count_consecutive_failures(skill_id)

        # 分析失败原因
        failure_analysis = self.analyze_failures(skill_id)

        # 灾难性失败检测：得分极低说明技能代码有根本性问题
        score = eval_result.get('score', 0)
        is_catastrophic = score <= 1.0

        should_optimize = (
            consecutive >= self.max_failures
            or is_catastrophic
        )

        result = {
            'consecutive_failures': consecutive,
            'should_optimize': should_optimize,
            'failure_analysis': failure_analysis,
        }

        if should_optimize:
            if is_catastrophic:
                logger.warning(
                    "技能 %s 灾难性失败 (得分 %.1f)，"
                    "立即触发 AI 修复",
                    skill_id, score
                )
            else:
                logger.warning(
                    "技能 %s 连续失败 %d 次，建议进行优化",
                    skill_id, consecutive
                )
            result['optimization_suggestions'] = (
                self.generate_optimization_suggestions(
                    skill_id, failure_analysis
                )
            )

        return result

    def record_success(self, skill_id: str):
        """记录训练成功，清空失败历史"""
        if skill_id in self.failure_history:
            self.failure_history[skill_id] = []

    def _extract_key_info(self, execution_result: Dict) -> Dict:
        """提取执行结果的关键信息（通用，不依赖特定领域字段）"""
        result = execution_result.get('result', {})
        info: Dict[str, Any] = {
            'success': execution_result.get('success', False),
            'output_size': len(str(result)),
        }

        # 动态提取结果中的关键统计
        if isinstance(result, dict):
            for key, val in result.items():
                if key in ('success',):
                    continue
                if isinstance(val, str):
                    info[f'{key}_length'] = len(val)
                elif isinstance(val, (list, tuple)):
                    info[f'{key}_count'] = len(val)
                elif isinstance(val, dict):
                    info[f'{key}_keys'] = list(val.keys())[:5]

        return info

    def _count_consecutive_failures(self, skill_id: str) -> int:
        """统计连续失败次数"""
        failures = self.failure_history.get(skill_id, [])
        return len(failures)  # 成功时会清空，所以长度即连续失败次数

    def analyze_failures(self, skill_id: str) -> Dict[str, Any]:
        """
        分析失败原因

        基于 AI 评估的真实反馈（维度得分、改进建议）进行分析，
        而非使用硬编码的领域特定指标。

        Returns:
            包含评估反馈摘要、薄弱维度、改进建议
        """
        failures = self.failure_history.get(skill_id, [])
        if not failures:
            return {'causes': [], 'eval_feedback': ''}

        recent = failures[-3:]
        num = len(recent)

        # 1. 汇总评估反馈
        reasons = [f.get('reason', '') for f in recent if f.get('reason')]
        summaries = [
            f.get('summary', '') for f in recent if f.get('summary')
        ]

        # 2. 聚合维度得分，找出薄弱项
        dim_totals: Dict[str, List[float]] = {}
        for f in recent:
            for dim in f.get('dimension_scores', []):
                name = dim.get('name', dim.get('dimension', ''))
                score = dim.get('score', dim.get('weighted_score', 0))
                if name:
                    dim_totals.setdefault(name, []).append(score)

        weak_dimensions = []
        for name, scores in dim_totals.items():
            avg = sum(scores) / len(scores)
            if avg < 6.0:  # 低于及格线
                weak_dimensions.append({
                    'dimension': name,
                    'avg_score': round(avg, 1),
                    'detail': f'{name} 平均得分 {avg:.1f}/10',
                })
        weak_dimensions.sort(key=lambda x: x['avg_score'])

        # 3. 汇总 AI 评估的改进建议
        all_suggestions = []
        seen = set()
        for f in recent:
            for s in f.get('improvement_suggestions', []):
                text = s if isinstance(s, str) else str(s)
                if text and text not in seen:
                    seen.add(text)
                    all_suggestions.append(text)

        # 4. 基础统计
        avg_score = sum(
            f.get('score', 0) for f in recent
        ) / num
        avg_output = sum(
            f['execution_result'].get('output_size', 0)
            for f in recent
        ) / num

        return {
            'avg_score': round(avg_score, 1),
            'avg_output_size': round(avg_output, 0),
            'eval_feedback': '\n'.join(reasons[-2:]),
            'eval_summary': '\n'.join(summaries[-2:]),
            'weak_dimensions': weak_dimensions,
            'improvement_suggestions': all_suggestions[:5],
            'causes': weak_dimensions,  # 兼容旧接口
        }

    def generate_optimization_suggestions(
        self,
        skill_id: str,
        failure_analysis: Dict
    ) -> List[Dict]:
        """
        基于实际评估反馈生成上下文相关的优化建议

        不再使用硬编码的 cause→strategy 映射表，
        而是直接使用 AI 评估器给出的改进建议和薄弱维度。
        """
        suggestions = []

        # 1. 来自 AI 评估的改进建议（最有针对性）
        for i, text in enumerate(
            failure_analysis.get('improvement_suggestions', [])[:5]
        ):
            suggestions.append({
                'strategy': 'eval_suggestion',
                'description': text,
                'priority': i + 1,
                'source': 'ai_evaluation',
            })

        # 2. 来自薄弱维度的针对性建议
        for dim in failure_analysis.get('weak_dimensions', [])[:3]:
            suggestions.append({
                'strategy': 'fix_dimension',
                'description': (
                    f"提升 {dim['dimension']} "
                    f"(当前 {dim['avg_score']}/10)"
                ),
                'priority': 10,
                'source': 'weak_dimension',
            })

        # 3. 通用兜底（仅当以上都没有时）
        if not suggestions:
            suggestions.append({
                'strategy': 'general_improve',
                'description': '增强 execute() 方法的实际处理逻辑',
                'priority': 99,
                'source': 'fallback',
            })

        suggestions.sort(key=lambda x: x.get('priority', 99))
        return suggestions

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
        """构造 LLM 修复 prompt，使用实际评估反馈"""
        # 评估反馈
        eval_feedback = failure_analysis.get(
            'eval_feedback', '无具体反馈')
        eval_summary = failure_analysis.get('eval_summary', '')

        # 薄弱维度
        weak_dims_text = ""
        for dim in failure_analysis.get('weak_dimensions', []):
            weak_dims_text += (
                f"- {dim['dimension']}: "
                f"{dim['avg_score']}/10\n"
            )
        if not weak_dims_text:
            weak_dims_text = "无具体维度数据\n"

        # 来自评估的改进建议
        suggestions_text = ""
        for s in suggestions[:5]:
            suggestions_text += f"- {s.get('description')}\n"
        if not suggestions_text:
            suggestions_text = "无具体建议\n"

        # 基础统计
        avg_score = failure_analysis.get('avg_score', 0)
        avg_output = failure_analysis.get('avg_output_size', 0)

        prompt = f"""你是一个 Python 技能代码优化专家。请修复以下技能代码，使其能通过训练评估。

## 技能 ID
{skill_id}

## 当前源码
```python
{source_code}
```

## 训练评估反馈（来自 AI 评估器的真实反馈）
{eval_feedback}

## 评估摘要
{eval_summary}

## 薄弱维度得分
{weak_dims_text}

## 统计数据
- 平均评估得分: {avg_score}/10
- 平均产出物大小: {avg_output:.0f} 字符

## 针对性改进建议
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

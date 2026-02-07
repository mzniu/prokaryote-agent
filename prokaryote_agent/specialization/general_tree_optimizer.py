"""
通用技能树AI优化器

职责：
1. 分析进化后的能力变化
2. 发现潜在的新技能
3. 调整技能优先级
4. 更新解锁条件
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)


class GeneralTreeOptimizer:
    """通用技能树AI优化器"""

    def __init__(self, tree: Dict):
        """
        初始化优化器

        Args:
            tree: 通用技能树
        """
        self.tree = tree
        self.changes = []

    def optimize(
        self,
        trigger_skill: str,
        trigger_level: int,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        执行优化

        Args:
            trigger_skill: 触发优化的技能
            trigger_level: 技能新等级
            context: 进化上下文

        Returns:
            优化结果
        """
        self.changes = []

        # 1. 分析新能力
        new_capabilities = self._analyze_capabilities(trigger_skill, trigger_level)

        # 2. 检查协同效应
        synergies = self._find_synergies(trigger_skill, context)

        # 3. 发现潜在新技能（使用AI）
        if context.get('total_level', 0) >= 50:  # 到一定等级才发现新技能
            potential_skills = self._discover_skills(
                trigger_skill, new_capabilities, context
            )
            if potential_skills:
                self._add_potential_skills(potential_skills)

        # 4. 调整优先级
        self._adjust_priorities(trigger_skill, synergies, context)

        # 5. 记录优化历史
        self._record_optimization(trigger_skill, trigger_level)

        return {
            'success': True,
            'tree': self.tree,
            'changes': self.changes,
            'summary': self._generate_summary()
        }

    def _analyze_capabilities(
        self,
        skill_id: str,
        level: int
    ) -> List[str]:
        """分析技能带来的新能力"""
        skill = self.tree.get('skills', {}).get(skill_id, {})
        capabilities = skill.get('capabilities', [])

        # 根据等级解锁不同能力
        unlocked = []
        for i, cap in enumerate(capabilities):
            # 假设每5级解锁一个能力
            if level >= (i + 1) * 5:
                unlocked.append(cap)

        return unlocked

    def _find_synergies(
        self,
        skill_id: str,
        context: Dict
    ) -> List[Dict]:
        """发现与其他技能的协同效应"""
        synergies = []
        skill = self.tree.get('skills', {}).get(skill_id, {})
        skill_category = skill.get('category', '')

        general_skills = context.get('general_skills', {})

        for other_id, other_info in general_skills.items():
            if other_id == skill_id:
                continue
            if not other_info.get('unlocked', False):
                continue

            other_skill = self.tree.get('skills', {}).get(other_id, {})
            other_category = other_skill.get('category', '')

            # 同类别技能有协同
            if skill_category == other_category:
                synergies.append({
                    'skill': other_id,
                    'type': 'same_category',
                    'strength': 0.3
                })

            # 前置/后置关系有强协同
            if skill_id in other_skill.get('prerequisites', []):
                synergies.append({
                    'skill': other_id,
                    'type': 'enables',
                    'strength': 0.5
                })

        return synergies

    def _discover_skills(
        self,
        trigger_skill: str,
        capabilities: List[str],
        context: Dict
    ) -> List[Dict]:
        """使用AI发现潜在新技能"""
        try:
            from prokaryote_agent.ai_adapter import AIAdapter

            # 构建当前能力描述
            current_skills = []
            for skill_id, info in context.get('general_skills', {}).items():
                if info.get('level', 0) > 0:
                    skill = self.tree.get('skills', {}).get(skill_id, {})
                    current_skills.append(
                        f"- {skill.get('name', skill_id)} (Lv.{info['level']})"
                    )

            prompt = f"""作为Agent能力规划专家，分析以下情况：

## 当前通用技能
{chr(10).join(current_skills) if current_skills else '暂无'}

## 刚刚进化的技能
{trigger_skill}: {capabilities}

## 任务
基于当前能力，建议1-2个可以添加的新通用技能，要求：
1. 与现有能力有协同效应
2. 属于以下方向之一：
   - 知识获取：扩展获取信息的渠道和方式
   - 外界交互：增强与真实世界交互的能力
   - 自我进化：提升自我改进能力

返回JSON格式：
{{
  "suggestions": [
    {{
      "id": "skill_id",
      "name": "技能名称",
      "category": "knowledge_acquisition|world_interaction|self_evolution",
      "description": "技能描述",
      "capabilities": ["能力1", "能力2"],
      "prerequisites": ["前置技能ID"],
      "reason": "建议原因"
    }}
  ]
}}

只返回JSON，不要其他内容。如果没有好的建议，返回空数组。"""

            ai = AIAdapter()
            response = ai._call_ai(prompt)

            # 解析响应
            import json
            import re

            # 提取JSON
            json_match = re.search(r'\{[\s\S]*\}', response)
            if json_match:
                result = json.loads(json_match.group())
                return result.get('suggestions', [])

        except Exception as e:
            logger.debug("AI发现技能失败: %s", e)

        return []

    def _add_potential_skills(self, skills: List[Dict]):
        """添加潜在新技能到技能树"""
        existing = self.tree.get('skills', {})

        for skill in skills:
            skill_id = skill.get('id', '')
            if not skill_id or skill_id in existing:
                continue

            # 添加新技能
            new_skill = {
                'name': skill.get('name', skill_id),
                'category': skill.get('category', 'knowledge_acquisition'),
                'tier': 'basic',
                'level': 0,
                'max_level': 20,
                'proficiency': 0.0,
                'description': skill.get('description', ''),
                'capabilities': skill.get('capabilities', []),
                'prerequisites': skill.get('prerequisites', []),
                'unlocked': False,
                'ai_generated': True,
                'generated_at': datetime.now().isoformat()
            }

            # 设置解锁条件
            prereqs = skill.get('prerequisites', [])
            if prereqs:
                new_skill['unlock_condition'] = ' AND '.join(
                    f"{p} >= 5" for p in prereqs
                )

            self.tree['skills'][skill_id] = new_skill
            self.changes.append({
                'type': 'add_skill',
                'skill_id': skill_id,
                'reason': skill.get('reason', 'AI建议')
            })

            logger.info("AI建议新技能: %s - %s", skill_id, skill.get('name'))

    def _adjust_priorities(
        self,
        trigger_skill: str,
        synergies: List[Dict],
        context: Dict
    ):
        """调整技能优先级"""
        # 目前通过 category priority 实现
        # 未来可以给每个技能加 priority 字段
        pass

    def _record_optimization(self, skill_id: str, level: int):
        """记录优化历史"""
        history = self.tree.get('optimization_history', [])
        history.append({
            'timestamp': datetime.now().isoformat(),
            'trigger_skill': skill_id,
            'trigger_level': level,
            'changes': self.changes
        })
        # 只保留最近20条
        self.tree['optimization_history'] = history[-20:]
        self.tree['last_optimized'] = datetime.now().isoformat()

    def _generate_summary(self) -> str:
        """生成优化摘要"""
        if not self.changes:
            return "无变更"

        parts = []
        for change in self.changes:
            if change['type'] == 'add_skill':
                parts.append(f"新增技能: {change['skill_id']}")
            elif change['type'] == 'adjust_priority':
                parts.append(f"调整优先级: {change['skill_id']}")

        return "; ".join(parts)

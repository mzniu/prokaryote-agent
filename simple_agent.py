#!/usr/bin/env python
"""
Prokaryote Agent - 简化版进化脚本
由 daemon 启动，执行进化循环

进化优先级：
1. 有明确目标 → 执行目标
2. 没有目标 → 根据技能树自动进化技能
"""

import os
import sys
import time
import signal
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, List, Any

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent))

from prokaryote_agent import (
    init_prokaryote,
    start_prokaryote,
    stop_prokaryote,
    query_prokaryote_state
)
from prokaryote_agent.goal_manager import EvolutionGoalManager, GoalStatus
from prokaryote_agent.skills.skill_base import SkillLibrary
from prokaryote_agent.skills.skill_generator import SkillGenerator
from prokaryote_agent.skills.skill_context import SkillContext


class SkillTreeManager:
    """技能树管理器"""

    def __init__(self, skill_tree_path: str):
        self.skill_tree_path = Path(skill_tree_path)
        self.skill_tree: Dict[str, Any] = {}
        self.load_skill_tree()

    def load_skill_tree(self) -> bool:
        """加载技能树"""
        if not self.skill_tree_path.exists():
            return False

        with open(self.skill_tree_path, 'r', encoding='utf-8') as f:
            self.skill_tree = json.load(f)
        return True

    def save_skill_tree(self):
        """保存技能树"""
        with open(self.skill_tree_path, 'w', encoding='utf-8') as f:
            json.dump(self.skill_tree, f, ensure_ascii=False, indent=2)

    def get_next_skill_to_evolve(self) -> Optional[Dict[str, Any]]:
        """
        获取下一个要进化的技能

        优先级：
        1. 已解锁但未满级的技能（按tier升序，level降序）
        2. 可解锁的新技能（前置条件满足）
        """
        skills = self.skill_tree.get('skills', {})

        # 1. 找已解锁但未满级的技能
        unlocked_skills = []
        for skill_id, skill in skills.items():
            if skill.get('unlocked', False):
                level = skill.get('level', 0)
                max_level = self._get_max_level_for_tier(skill.get('tier', 'basic'))
                if level < max_level:
                    unlocked_skills.append({
                        'id': skill_id,
                        **skill,
                        'max_level': max_level
                    })

        if unlocked_skills:
            # 按 tier 优先级排序（basic > intermediate > advanced > master > expert）
            tier_order = {'basic': 0, 'intermediate': 1, 'advanced': 2, 'master': 3, 'expert': 4}
            unlocked_skills.sort(key=lambda s: (tier_order.get(s.get('tier', 'basic'), 0), -s.get('level', 0)))
            return unlocked_skills[0]

        # 2. 找可解锁的新技能
        for skill_id, skill in skills.items():
            if not skill.get('unlocked', False):
                if self._can_unlock(skill_id, skill, skills):
                    return {'id': skill_id, **skill, 'needs_unlock': True}

        return None

    def _get_max_level_for_tier(self, tier: str) -> int:
        """获取各层级的最大等级"""
        max_levels = {
            'basic': 20,
            'intermediate': 30,
            'advanced': 40,
            'master': 50,
            'expert': 100
        }
        return max_levels.get(tier, 20)

    def _can_unlock(self, skill_id: str, skill: Dict, all_skills: Dict) -> bool:
        """检查技能是否可以解锁"""
        prerequisites = skill.get('prerequisites', [])
        if not prerequisites:
            return True

        # 检查所有前置技能是否达标
        for prereq_id in prerequisites:
            prereq = all_skills.get(prereq_id)
            if not prereq:
                return False
            if not prereq.get('unlocked', False):
                return False
            # 前置技能需要达到一定等级（根据unlock_condition判断）
            prereq_level = prereq.get('level', 0)
            required_level = self._parse_required_level(skill.get('unlock_condition', ''))
            if prereq_level < required_level:
                return False

        return True

    def _parse_required_level(self, condition: str) -> int:
        """解析解锁条件中的等级要求"""
        # 例如 "前置技能达到10级" -> 10
        import re
        match = re.search(r'(\d+)级', condition)
        if match:
            return int(match.group(1))
        return 10  # 默认10级

    def level_up_skill(self, skill_id: str, amount: int = 1) -> bool:
        """提升技能等级"""
        skills = self.skill_tree.get('skills', {})
        if skill_id not in skills:
            return False

        skill = skills[skill_id]
        if not skill.get('unlocked', False):
            return False

        current_level = skill.get('level', 0)
        max_level = self._get_max_level_for_tier(skill.get('tier', 'basic'))

        new_level = min(current_level + amount, max_level)
        skill['level'] = new_level
        skill['proficiency'] = new_level / max_level

        self.save_skill_tree()
        return True

    def unlock_skill(self, skill_id: str) -> bool:
        """解锁技能"""
        skills = self.skill_tree.get('skills', {})
        if skill_id not in skills:
            return False

        skill = skills[skill_id]
        if skill.get('unlocked', False):
            return True  # 已解锁

        if not self._can_unlock(skill_id, skill, skills):
            return False

        skill['unlocked'] = True
        skill['level'] = 1
        skill['proficiency'] = 0.0

        self.save_skill_tree()
        return True

    def get_statistics(self) -> Dict[str, Any]:
        """获取技能树统计"""
        skills = self.skill_tree.get('skills', {})
        total = len(skills)
        unlocked = sum(1 for s in skills.values() if s.get('unlocked', False))

        # 按tier统计
        tier_stats = {}
        for skill in skills.values():
            tier = skill.get('tier', 'basic')
            if tier not in tier_stats:
                tier_stats[tier] = {'total': 0, 'unlocked': 0, 'total_level': 0}
            tier_stats[tier]['total'] += 1
            if skill.get('unlocked', False):
                tier_stats[tier]['unlocked'] += 1
                tier_stats[tier]['total_level'] += skill.get('level', 0)

        return {
            'total': total,
            'unlocked': unlocked,
            'locked': total - unlocked,
            'tier_stats': tier_stats
        }

    def add_skill(self, skill_definition: Dict[str, Any]) -> bool:
        """
        动态添加新技能到技能树

        Args:
            skill_definition: 技能定义
                {
                    'id': 'new_skill_id',
                    'name': '新技能',
                    'tier': 'basic',
                    'description': '...',
                    'prerequisites': ['existing_skill_id'],
                    'category': 'analytical'
                }
        """
        skills = self.skill_tree.get('skills', {})
        skill_id = skill_definition['id']

        if skill_id in skills:
            return False  # 已存在

        # 构建完整的技能节点
        new_skill = {
            'id': skill_id,
            'name': skill_definition.get('name', skill_id),
            'tier': skill_definition.get('tier', 'basic'),
            'category': skill_definition.get('category', 'technical'),
            'description': skill_definition.get('description', ''),
            'level': 0,
            'proficiency': 0.0,
            'prerequisites': skill_definition.get('prerequisites', []),
            'unlocked': False,
            'unlock_condition': skill_definition.get('unlock_condition', '前置技能达到10级'),
            'is_combination': skill_definition.get('is_combination', False),
            'metadata': {
                'domain': skill_definition.get('domain', 'general'),
                'added_dynamically': True,
                'added_at': datetime.now().isoformat()
            }
        }

        skills[skill_id] = new_skill
        self.save_skill_tree()
        return True

    def get_skill_by_name(self, name: str) -> Optional[Dict[str, Any]]:
        """通过名称查找技能"""
        skills = self.skill_tree.get('skills', {})
        for skill_id, skill in skills.items():
            if skill.get('name') == name or skill_id == name:
                return {'id': skill_id, **skill}
        return None

    def find_or_suggest_skill(self, capability: str) -> Dict[str, Any]:
        """
        查找匹配能力的技能，如果不存在则返回建议的新技能定义

        Args:
            capability: 所需能力描述

        Returns:
            {'found': True, 'skill': ...} 或 {'found': False, 'suggested': ...}
        """
        skills = self.skill_tree.get('skills', {})

        # 尝试通过关键词匹配现有技能
        keywords = capability.lower().split()
        for skill_id, skill in skills.items():
            skill_name = skill.get('name', '').lower()
            skill_desc = skill.get('description', '').lower()

            # 检查关键词是否匹配
            if any(kw in skill_name or kw in skill_desc for kw in keywords):
                return {'found': True, 'skill': {'id': skill_id, **skill}}

        # 没找到，生成建议的新技能定义
        suggested_id = '_'.join(keywords[:3]) + '_skill'
        suggested = {
            'id': suggested_id,
            'name': capability,
            'tier': 'basic',
            'description': f'自动生成：{capability}',
            'prerequisites': [],  # 稍后由AI分析填充
            'category': 'technical',
            'domain': self.skill_tree.get('domain', 'general')
        }

        return {'found': False, 'suggested': suggested}


class SimpleEvolutionAgent:
    """简化版进化Agent"""

    def __init__(self, goal_file: str = None, interval: int = 30, config_path: str = None):
        """
        初始化

        Args:
            goal_file: 目标文件路径
            interval: 检查间隔（秒）
            config_path: daemon配置文件路径
        """
        self.goal_file = goal_file or "evolution_goals.md"
        self.interval = interval
        self.running = False
        self.evolution_count = 0
        self.skill_evolution_count = 0

        # 加载配置获取技能树路径
        self.config_path = config_path or "prokaryote_agent/daemon_config.json"
        self.config = self._load_config()

        # 技能树管理器
        self.skill_tree_manager: Optional[SkillTreeManager] = None

        # 技能库和生成器（用于真正实现技能）
        self.skill_library: Optional[SkillLibrary] = None
        self.skill_generator: Optional[SkillGenerator] = None

        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)

        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)

    def _load_config(self) -> Dict[str, Any]:
        """加载配置"""
        config_path = Path(self.config_path)
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def _signal_handler(self, signum, frame):
        """信号处理"""
        print("\n⚠️  收到停止信号，正在关闭...")
        self.running = False

    def initialize(self) -> bool:
        """初始化系统"""
        print("=" * 50)
        print("🧬 Prokaryote Agent - 进化系统")
        print("=" * 50)

        # 初始化核心系统
        print("\n[1/3] 初始化核心系统...")
        result = init_prokaryote()
        if not result.get('success'):
            print(f"❌ 初始化失败: {result.get('msg')}")
            return False
        print("✅ 核心系统初始化成功")

        # 加载目标
        print("\n[2/4] 加载进化目标...")
        self.goal_manager = EvolutionGoalManager(self.goal_file)
        goals = self.goal_manager.load_goals()

        stats = self.goal_manager.get_statistics()
        print(f"✅ 已加载 {stats['total']} 个目标")
        print(f"   - 待执行: {stats['pending']}")
        print(f"   - 已完成: {stats['completed']}")

        # 加载技能树
        print("\n[3/4] 加载技能树...")
        skill_tree_path = self.config.get('specialization', {}).get('skill_tree_path')
        if skill_tree_path:
            # 处理相对路径（配置中可能是 ./xxx 或 xxx 形式）
            if skill_tree_path.startswith('./'):
                full_path = Path(skill_tree_path[2:])
            else:
                full_path = Path(skill_tree_path)

            if full_path.exists():
                self.skill_tree_manager = SkillTreeManager(str(full_path))
                tree_stats = self.skill_tree_manager.get_statistics()
                domain = self.config.get('specialization', {}).get('domain', 'unknown')
                print(f"✅ 技能树已加载: {domain}")
                print(f"   - 总技能: {tree_stats['total']}")
                print(f"   - 已解锁: {tree_stats['unlocked']}")
                print(f"   - 待解锁: {tree_stats['locked']}")
            else:
                print(f"⚠️  技能树文件不存在: {full_path}")
        else:
            print("⚠️  未配置技能树路径")

        # 初始化技能库和生成器
        print("\n[4/4] 初始化技能库...")
        self.skill_library = SkillLibrary()
        self.skill_generator = SkillGenerator(self.skill_library)
        lib_stats = self.skill_library.get_statistics()
        print(f"✅ 技能库已加载")
        print(f"   - 已学习技能: {lib_stats['total_skills']}")
        print(f"   - 总执行次数: {lib_stats['total_executions']}")

        return True

    def run(self):
        """运行进化循环"""
        if not self.initialize():
            return

        print(f"\n🚀 开始进化循环 (间隔: {self.interval}秒)")
        print("按 Ctrl+C 停止\n")

        self.running = True

        while self.running:
            try:
                self._evolution_cycle()

                # 等待下一轮
                for _ in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)

            except Exception as e:
                self.logger.error(f"进化循环错误: {e}")
                time.sleep(5)

        print("\n👋 进化系统已停止")
        print(f"   - 目标完成: {self.evolution_count}")
        print(f"   - 技能进化: {self.skill_evolution_count}")

    def _evolution_cycle(self):
        """单次进化循环"""
        # 优先执行明确的目标
        goal = self.goal_manager.get_next_goal()

        if goal:
            self._execute_goal_evolution(goal)
        else:
            # 没有目标时，根据技能树自动进化
            self._execute_skill_evolution()

    def _execute_goal_evolution(self, goal):
        """执行目标进化"""
        self.logger.info(f"🎯 处理目标: {goal.title}")

        # 标记为进行中
        self.goal_manager.mark_goal_in_progress(goal)

        try:
            # 执行进化
            success = self._execute_goal(goal)

            if success:
                self.goal_manager.mark_goal_completed(goal)
                self.evolution_count += 1
                self.logger.info(f"✅ 目标完成: {goal.title}")
            else:
                self.goal_manager.mark_goal_failed(goal, "执行失败")
                self.logger.warning(f"❌ 目标失败: {goal.title}")

        except Exception as e:
            self.goal_manager.mark_goal_failed(goal, str(e))
            self.logger.error(f"❌ 目标异常: {e}")

    def _execute_skill_evolution(self):
        """根据技能树执行技能进化"""
        if not self.skill_tree_manager:
            self.logger.info("📋 没有待执行的目标，也没有技能树配置")
            return

        # 获取下一个要进化的技能
        skill = self.skill_tree_manager.get_next_skill_to_evolve()

        if not skill:
            self.logger.info("🏆 所有技能已达到最高等级!")
            return

        skill_id = skill['id']
        skill_name = skill.get('name', skill_id)
        current_level = skill.get('level', 0)
        max_level = skill.get('max_level', 20)
        needs_unlock = skill.get('needs_unlock', False)

        if needs_unlock:
            # 解锁新技能
            self.logger.info(f"🔓 解锁新技能: {skill_name}")
            self.logger.info(f"   描述: {skill.get('description', '')}")

            success = self._train_skill_unlock(skill)

            if success:
                self.skill_tree_manager.unlock_skill(skill_id)
                self.skill_evolution_count += 1
                self.logger.info(f"✅ 技能已解锁: {skill_name} (Lv.1)")
            else:
                self.logger.warning(f"❌ 解锁失败: {skill_name}")
        else:
            # 提升已有技能
            self.logger.info(f"📈 提升技能: {skill_name} (Lv.{current_level} → Lv.{current_level + 1})")
            self.logger.info(f"   层级: {skill.get('tier', 'basic').capitalize()}")
            self.logger.info(f"   进度: {current_level}/{max_level}")

            success = self._train_skill_level_up(skill)

            if success:
                self.skill_tree_manager.level_up_skill(skill_id, 1)
                self.skill_evolution_count += 1
                self.logger.info(f"✅ 技能提升: {skill_name} (Lv.{current_level + 1})")
            else:
                self.logger.warning(f"❌ 提升失败: {skill_name}")

    def _train_skill_unlock(self, skill: Dict) -> bool:
        """
        训练解锁技能 - 学习一个新技能

        这会调用技能生成器，生成技能的实际代码实现
        """
        if not self.skill_generator:
            self.logger.warning("技能生成器未初始化")
            return False

        skill_id = skill['id']

        # 检查是否已经学习过
        existing = self.skill_library.get_skill(skill_id)
        if existing:
            self.logger.info(f"   技能已存在于库中: {skill_id}")
            return True

        # 构建技能定义
        skill_definition = {
            'id': skill_id,
            'name': skill.get('name', skill_id),
            'tier': skill.get('tier', 'basic'),
            'domain': skill.get('metadata', {}).get('domain', 'general'),
            'description': skill.get('description', ''),
            'capabilities': self._extract_capabilities(skill),
            'prerequisites': skill.get('prerequisites', [])
        }

        self.logger.info(f"   正在生成技能代码...")

        # 调用技能生成器学习技能
        result = self.skill_generator.learn_skill(skill_definition)

        if result['success']:
            self.logger.info(f"   ✓ 技能代码已保存: {result['code_path']}")
            return True
        else:
            self.logger.error(f"   ✗ 技能生成失败: {result.get('error')}")
            return False

    def _train_skill_level_up(self, skill: Dict) -> bool:
        """
        训练提升技能等级 - 增强已有技能

        技能等级提升意味着：
        - 增加熟练度
        - 可能增加新功能
        - 优化性能
        """
        if not self.skill_generator:
            self.logger.warning("技能生成器未初始化")
            return False

        skill_id = skill['id']
        current_level = skill.get('level', 0)
        target_level = current_level + 1

        # 检查技能是否存在
        existing = self.skill_library.get_skill(skill_id)
        if not existing:
            # 如果技能不存在，先学习
            self.logger.info(f"   技能未学习，先进行学习...")
            if not self._train_skill_unlock(skill):
                return False

        self.logger.info(f"   开始训练...")

        # 调用技能生成器升级技能（包含训练任务）
        result = self.skill_generator.upgrade_skill(skill_id, target_level)

        if result['success']:
            # 显示训练任务
            training_task = result.get('training_task', '')
            if training_task:
                self.logger.info(f"   ✓ 训练任务: {training_task}")

            # 显示训练结果
            training_result = result.get('training_result', {})
            if training_result.get('reason'):
                self.logger.info(f"   ✓ {training_result['reason']}")

            # 显示知识固化统计
            knowledge_stored = result.get('knowledge_stored', 0)
            if knowledge_stored > 0:
                self.logger.info(f"   💾 知识固化: {knowledge_stored} 条新知识")

            # 显示代码进化
            code_evolved = result.get('code_evolved', False)
            if code_evolved:
                self.logger.info(f"   🧬 代码进化: 技能能力已增强")

            # 显示增强
            enhancements = result.get('enhancements', [])
            for enhancement in enhancements:
                self.logger.info(f"   ★ {enhancement}")
            return True
        else:
            # 训练失败
            self.logger.warning(f"   ✗ {result.get('error')}")
            training_task = result.get('training_task', '')
            if training_task:
                self.logger.info(f"   需要重新练习: {training_task}")
            return False

    def _extract_capabilities(self, skill: Dict) -> List[str]:
        """从技能定义中提取能力列表"""
        # 尝试从描述中提取能力
        description = skill.get('description', '')
        capabilities = []

        # 根据技能名称和描述推断能力
        name = skill.get('name', '')
        if '检索' in name or 'research' in skill.get('id', ''):
            capabilities.extend(['检索法条', '查找判例', '搜索法规'])
        if '起草' in name or '文书' in name or 'drafting' in skill.get('id', ''):
            capabilities.extend(['起草文书', '格式规范', '内容组织'])
        if '分析' in name or 'analysis' in skill.get('id', ''):
            capabilities.extend(['案例分析', '事实提取', '法律适用分析'])
        if '审查' in name or 'review' in skill.get('id', ''):
            capabilities.extend(['条款审查', '风险识别', '合规检查'])
        if '推理' in name or 'reasoning' in skill.get('id', ''):
            capabilities.extend(['法律推理', '逻辑论证', '结论推导'])

        if not capabilities:
            capabilities = [f'{name}能力']

        return capabilities

    def _execute_goal(self, goal) -> bool:
        """执行目标（简化版）"""
        # 这里应该集成实际的能力生成逻辑
        # 目前只是模拟

        self.logger.info(f"   执行: {goal.description or goal.title}")

        # 检查验收标准
        if goal.acceptance_criteria:
            for criterion in goal.acceptance_criteria:
                self.logger.info(f"   验收: {criterion}")

        # 模拟执行时间
        time.sleep(2)

        # 简化版：总是成功
        return True


def main():
    """主入口"""
    import argparse

    parser = argparse.ArgumentParser(description='Prokaryote Agent 进化系统')
    parser.add_argument('--mode', default='iterative', help='进化模式')
    parser.add_argument('--interval', type=int, default=30, help='检查间隔（秒）')
    parser.add_argument('--goals', default='evolution_goals.md', help='目标文件')

    args = parser.parse_args()

    agent = SimpleEvolutionAgent(
        goal_file=args.goals,
        interval=args.interval
    )
    agent.run()


if __name__ == "__main__":
    main()

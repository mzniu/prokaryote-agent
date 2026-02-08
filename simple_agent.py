#!/usr/bin/env python
"""
Prokaryote Agent - 简化版进化脚本
由 daemon 启动，执行进化循环

进化优先级：
1. 有明确目标 → 执行目标
2. 没有目标 → 根据技能树自动进化技能
   - 萌芽期(总等级<30)：80%通用技能，20%专业技能
   - 成长期(30-100)：60%通用，40%专业
   - 成熟期(100-300)：40%通用，60%专业
   - 专精期(>=300)：25%通用，75%专业
"""

import os
import sys
import time
import signal
import logging
import json
import threading
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
from prokaryote_agent.specialization.skill_coordinator import SkillEvolutionCoordinator
from prokaryote_agent.specialization.general_tree_optimizer import GeneralTreeOptimizer


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
            tier_order = {
                'basic': 0, 'intermediate': 1, 'advanced': 2, 'master': 3, 'expert': 4
            }
            unlocked_skills.sort(
                key=lambda s: (tier_order.get(s.get('tier', 'basic'), 0), -s.get('level', 0))
            )
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

        # 技能树管理器（单树模式，用于向后兼容）
        self.skill_tree_manager: Optional[SkillTreeManager] = None

        # 技能进化协调器（双树模式，推荐）
        self.skill_coordinator: Optional[SkillEvolutionCoordinator] = None
        self.general_tree_optimizer: Optional[GeneralTreeOptimizer] = None

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

        # 信号处理（仅主线程可注册）
        if threading.current_thread() is threading.main_thread():
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
        self.logger.warning("⚠️  收到停止信号，正在关闭...")
        self.running = False

    def _init_skill_trees(self):
        """初始化技能树（支持双树模式）"""
        specialization = self.config.get('specialization', {})
        domain_tree_path = specialization.get('skill_tree_path')
        general_tree_path = specialization.get('general_tree_path')

        # 处理路径
        def resolve_path(path_str):
            if not path_str:
                return None
            if path_str.startswith('./'):
                return Path(path_str[2:])
            return Path(path_str)

        domain_path = resolve_path(domain_tree_path)
        general_path = resolve_path(general_tree_path)

        # 检查通用技能树默认路径
        if not general_path or not general_path.exists():
            default_general = Path(
                "prokaryote_agent/specialization/domains/general_tree.json"
            )
            if default_general.exists():
                general_path = default_general

        # 双树模式：同时有通用树和领域树
        if general_path and general_path.exists() and domain_path and domain_path.exists():  # noqa: E501
            self._init_dual_tree_mode(general_path, domain_path, specialization)
        # 单树模式：只有领域树（向后兼容）
        elif domain_path and domain_path.exists():
            self._init_single_tree_mode(domain_path, specialization)
        else:
            self.logger.warning("⚠️  未配置有效的技能树路径")

    def _init_dual_tree_mode(self, general_path: Path, domain_path: Path, config: dict):  # noqa: E501
        """初始化双树模式（推荐）"""
        domain = config.get('domain', 'unknown')

        # 创建协调器
        self.skill_coordinator = SkillEvolutionCoordinator(
            general_tree_path=str(general_path),
            domain_tree_path=str(domain_path)
        )

        # 创建通用树优化器
        self.general_tree_optimizer = GeneralTreeOptimizer(
            tree=self.skill_coordinator.general_tree
        )

        # 同时创建单树管理器（向后兼容）
        self.skill_tree_manager = SkillTreeManager(str(domain_path))

        # 获取统计信息（从树字典中计算）
        general_tree = self.skill_coordinator.general_tree
        domain_tree = self.skill_coordinator.domain_tree

        general_skills = general_tree.get('skills', {})
        domain_skills = domain_tree.get('skills', {})

        general_unlocked = sum(
            1 for s in general_skills.values() if s.get('unlocked', False)
        )
        domain_unlocked = sum(
            1 for s in domain_skills.values() if s.get('unlocked', False)
        )

        # 计算总等级
        total_level = self.skill_coordinator.get_total_level()
        stage = self.skill_coordinator.get_current_stage()
        priority = self.skill_coordinator.get_current_priority()

        # 阶段名称映射
        stage_names = {
            'sprouting': '萌芽期',
            'growing': '成长期',
            'maturing': '成熟期',
            'specializing': '专精期'
        }
        stage_name_cn = stage_names.get(stage, stage)
        general_pct = int(priority['general'] * 100)
        domain_pct = int(priority['domain'] * 100)

        self.logger.info(f"✅ 双树进化模式已启用: {domain}")
        self.logger.info(f"   📚 通用技能树: {general_unlocked}/{len(general_skills)} 已解锁")
        self.logger.info(f"   🎯 领域技能树: {domain_unlocked}/{len(domain_skills)} 已解锁")
        self.logger.info(f"   📊 当前阶段: {stage}({stage_name_cn})")
        self.logger.info(f"   ⚖️  进化优先级: 通用{general_pct}% / 领域{domain_pct}%")
        self.logger.info(f"   📈 总技能等级: {total_level}")

    def _init_single_tree_mode(self, domain_path: Path, config: dict):
        """初始化单树模式（向后兼容）"""
        domain = config.get('domain', 'unknown')
        self.skill_tree_manager = SkillTreeManager(str(domain_path))
        tree_stats = self.skill_tree_manager.get_statistics()

        self.logger.info(f"✅ 技能树已加载: {domain}")
        self.logger.info(f"   - 总技能: {tree_stats['total']}")
        self.logger.info(f"   - 已解锁: {tree_stats['unlocked']}")
        self.logger.info(f"   - 待解锁: {tree_stats['locked']}")

    def initialize(self) -> bool:
        """初始化系统"""
        self.logger.info("=" * 50)
        self.logger.info("🧬 Prokaryote Agent - 进化系统")
        self.logger.info("=" * 50)

        # 初始化核心系统
        self.logger.info("[1/4] 初始化核心系统...")
        result = init_prokaryote()
        if not result.get('success'):
            self.logger.error(f"❌ 初始化失败: {result.get('msg')}")
            return False
        self.logger.info("✅ 核心系统初始化成功")

        # 加载目标
        self.logger.info("[2/4] 加载进化目标...")
        self.goal_manager = EvolutionGoalManager(self.goal_file)
        goals = self.goal_manager.load_goals()

        stats = self.goal_manager.get_statistics()
        self.logger.info(f"✅ 已加载 {stats['total']} 个目标")
        self.logger.info(f"   - 待执行: {stats['pending']}")
        self.logger.info(f"   - 已完成: {stats['completed']}")

        # 加载技能树（支持双树模式）
        self.logger.info("[3/4] 加载技能树...")
        self._init_skill_trees()

        # 初始化技能库和生成器
        self.logger.info("[4/4] 初始化技能库...")
        self.skill_library = SkillLibrary()
        self.skill_generator = SkillGenerator(self.skill_library)
        lib_stats = self.skill_library.get_statistics()
        self.logger.info("✅ 技能库已加载")
        self.logger.info(f"   - 已学习技能: {lib_stats['total_skills']}")
        self.logger.info(f"   - 总执行次数: {lib_stats['total_executions']}")

        return True

    def run(self):
        """运行进化循环"""
        if not self.initialize():
            return

        self.logger.info(f"🚀 开始进化循环 (间隔: {self.interval}秒)")

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

        # 清理核心系统状态，允许下次重新初始化
        try:
            stop_prokaryote()
        except Exception:
            pass

        self.logger.info("👋 进化系统已停止")
        self.logger.info(f"   - 目标完成: {self.evolution_count}")
        self.logger.info(f"   - 技能进化: {self.skill_evolution_count}")

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
        # 优先使用 AI 训练规划器
        if self.skill_coordinator:
            plan = self._get_ai_training_plan()
            if plan and plan.get("plan"):
                self._execute_planned_evolution(plan)
                return
            # AI 规划不可用，回退到协调器
            self._execute_coordinated_evolution()
            return

        # 降级到单树模式
        if self.skill_tree_manager:
            self._execute_single_tree_evolution()
            return

        self.logger.info("📋 没有待执行的目标，也没有技能树配置")

    def _get_ai_training_plan(self):
        """获取 AI 训练计划"""
        try:
            from prokaryote_agent.skills.evolution.training_archive import (
                analyze_global, analyze_skill,
            )
            from prokaryote_agent.skills.evolution.training_planner import (
                create_training_plan,
            )
            from prokaryote_agent.ai_adapter import AIAdapter

            # 收集已学技能状态
            skill_stats = []
            all_skills = {}
            if self.skill_coordinator:
                for tree_dict in [
                    self.skill_coordinator.general_tree,
                    self.skill_coordinator.domain_tree,
                ]:
                    for sid, info in tree_dict.get(
                        "skills", {}
                    ).items():
                        if info.get("unlocked"):
                            all_skills[sid] = info

            for sid, info in all_skills.items():
                # 从训练档案拿分析数据
                analysis = analyze_skill(sid, days=14)
                skill_stats.append({
                    "skill_id": sid,
                    "name": info.get("name", sid),
                    "level": info.get("level", 0),
                    "domain": info.get("domain", "unknown"),
                    "tier": info.get("tier", "basic"),
                    "success_rate": analysis.get(
                        "success_rate", 1.0
                    ),
                    "avg_score": analysis.get("avg_score", 0),
                    "total_trainings": analysis.get(
                        "total_trainings", 0
                    ),
                    "weak_dims": analysis.get(
                        "weak_dimensions", {}
                    ),
                })

            # 收集未学习技能
            available = []
            if self.skill_coordinator:
                for tree_dict in [
                    self.skill_coordinator.general_tree,
                    self.skill_coordinator.domain_tree,
                ]:
                    for sid, info in tree_dict.get(
                        "skills", {}
                    ).items():
                        if not info.get("unlocked"):
                            available.append({
                                "skill_id": sid,
                                "name": info.get("name", sid),
                                "domain": info.get(
                                    "domain", "unknown"
                                ),
                            })

            # 全局档案分析
            global_analysis = analyze_global(days=14)

            # 生成计划
            adapter = AIAdapter()
            plan = create_training_plan(
                skill_stats=skill_stats,
                archive_analysis=global_analysis,
                available_skills=available,
                max_picks=1,  # 每轮进化处理1个
                ai_adapter=adapter,
            )
            return plan

        except Exception as e:
            self.logger.debug("AI训练规划跳过: %s", e)
            return None

    def _execute_planned_evolution(self, plan):
        """执行 AI 规划的训练计划"""
        summary = plan.get("analysis_summary", "")
        method = plan.get("method", "unknown")
        self.logger.info(
            "🧠 训练规划 (%s): %s", method, summary[:120],
        )

        for item in plan["plan"]:
            action = item.get("action", "train")
            skill_id = item.get("skill_id", "")
            reason = item.get("reason", "")
            focus = item.get("focus_dimensions", [])
            hint = item.get("task_hint", "")

            self.logger.info(
                "📋 计划: %s %s — %s",
                action, skill_id, reason[:80],
            )
            if focus:
                self.logger.info(
                    "   侧重维度: %s", ", ".join(focus),
                )
            if hint:
                self.logger.info(
                    "   训练提示: %s", hint[:100],
                )

            # 查找技能在哪个树里
            skill_info = None
            skill_tree = None
            if self.skill_coordinator:
                for tree_name, tree_dict in [
                    ("general",
                     self.skill_coordinator.general_tree),
                    ("domain",
                     self.skill_coordinator.domain_tree),
                ]:
                    if skill_id in tree_dict.get("skills", {}):
                        skill_info = tree_dict["skills"][skill_id]
                        skill_info["id"] = skill_id
                        skill_tree = tree_name
                        break

            if not skill_info:
                self.logger.warning(
                    "⚠️ 规划的技能 %s 不在技能树中，跳过",
                    skill_id,
                )
                continue

            # 将规划器提示注入 skill_generator
            if self.skill_generator and (focus or hint):
                self.skill_generator.training_hints[skill_id] = {
                    "focus_dimensions": focus,
                    "task_hint": hint,
                }

            current_level = skill_info.get("level", 0)

            if action == "unlock" or current_level == 0:
                self.logger.info(
                    "🔓 解锁新技能: %s", skill_id,
                )
                success = self._train_skill_unlock(skill_info)
                if success:
                    tree_dict = (
                        self.skill_coordinator.general_tree
                        if skill_tree == "general"
                        else self.skill_coordinator.domain_tree
                    )
                    if skill_id in tree_dict.get("skills", {}):
                        tree_dict["skills"][skill_id][
                            "unlocked"
                        ] = True
                        tree_dict["skills"][skill_id][
                            "level"
                        ] = 1
                    self.skill_coordinator.record_evolution_success(
                        skill_tree, skill_id, 1,
                    )
                    self._check_and_unlock_new_skills()
                    self.skill_evolution_count += 1
                    self.logger.info(
                        "✅ 技能已解锁: %s (Lv.1)", skill_id,
                    )
                else:
                    self.logger.warning(
                        "❌ 解锁失败: %s", skill_id,
                    )

            else:  # train / repair
                self.logger.info(
                    "📈 提升技能: %s Lv.%d → Lv.%d",
                    skill_id, current_level, current_level + 1,
                )
                success = self._train_skill_level_up(skill_info)
                if success:
                    new_level = current_level + 1
                    tree_dict = (
                        self.skill_coordinator.general_tree
                        if skill_tree == "general"
                        else self.skill_coordinator.domain_tree
                    )
                    if skill_id in tree_dict.get("skills", {}):
                        tree_dict["skills"][skill_id][
                            "level"
                        ] = new_level
                    self.skill_coordinator.record_evolution_success(
                        skill_tree, skill_id, new_level,
                    )
                    self._check_and_unlock_new_skills()
                    self.skill_evolution_count += 1
                    self.logger.info(
                        "✅ 技能提升: %s (Lv.%d)",
                        skill_id, new_level,
                    )
                    if skill_tree == "general":
                        self._try_optimize_general_tree(
                            skill_id, new_level,
                        )
                else:
                    self.logger.warning(
                        "❌ 提升失败: %s", skill_id,
                    )

    def _execute_coordinated_evolution(self):
        """使用协调器执行双树进化"""
        # 显示当前进化阶段
        stage = self.skill_coordinator.get_current_stage()
        priority = self.skill_coordinator.get_current_priority()
        total_level = self.skill_coordinator.get_total_level()

        # 阶段名称映射
        stage_names = {
            'sprouting': '萌芽期',
            'growing': '成长期',
            'maturing': '成熟期',
            'specializing': '专精期'
        }
        stage_name_cn = stage_names.get(stage, stage)
        general_pct = int(priority['general'] * 100)
        domain_pct = int(priority['domain'] * 100)

        self.logger.info(f"🌱 进化阶段: {stage_name_cn} (总等级: {total_level})")
        self.logger.info(f"   优先级: 通用{general_pct}% / 领域{domain_pct}%")

        # 从协调器获取下一个要进化的技能
        skill_tree, skill = self.skill_coordinator.select_next_skill()

        if skill_tree == 'none' or skill is None:
            self.logger.info("🏆 所有技能已达到最高等级!")

            # 尝试优化通用技能树
            if self.general_tree_optimizer:
                self.logger.info("🧬 尝试优化通用技能树...")
                result = self.general_tree_optimizer.optimize()
                if result.get('success'):
                    new_skills = result.get('new_skills', [])
                    if new_skills:
                        self.logger.info(f"   发现 {len(new_skills)} 个新技能!")
                        for ns in new_skills[:3]:
                            self.logger.info(f"   - {ns['name']}")
            return

        skill_id = skill['id']
        skill_name = skill.get('name', skill_id)
        current_level = skill.get('level', 0)
        max_level = skill.get('max_level', 20)
        needs_unlock = current_level == 0

        tree_emoji = "📚" if skill_tree == 'general' else "🎯"
        tree_label = "通用" if skill_tree == 'general' else "领域"

        if needs_unlock:
            # 解锁新技能
            self.logger.info(f"🔓 解锁新技能: {skill_name} [{tree_label}]")
            self.logger.info(f"   描述: {skill.get('description', '')}")

            success = self._train_skill_unlock(skill)

            if success:
                # 在对应的树上解锁技能
                if skill_tree == 'general':
                    tree = self.skill_coordinator.general_tree
                    if skill_id in tree.get('skills', {}):
                        tree['skills'][skill_id]['unlocked'] = True
                        tree['skills'][skill_id]['level'] = 1
                else:
                    tree = self.skill_coordinator.domain_tree
                    if skill_id in tree.get('skills', {}):
                        tree['skills'][skill_id]['unlocked'] = True
                        tree['skills'][skill_id]['level'] = 1

                # 记录进化成功
                self.skill_coordinator.record_evolution_success(
                    skill_tree, skill_id, 1
                )

                # 检查解锁新技能
                self._check_and_unlock_new_skills()

                self.skill_evolution_count += 1
                self.logger.info(f"✅ {tree_emoji} 技能已解锁: {skill_name} (Lv.1)")

                # 尝试优化通用技能树（只有通用技能才触发优化）
                if skill_tree == 'general':
                    self._try_optimize_general_tree(skill_id, 1)
            else:
                self.logger.warning(f"❌ 解锁失败: {skill_name}")
        else:
            # 提升已有技能
            self.logger.info(f"📈 提升技能: {skill_name} [{tree_label}]")
            self.logger.info(f"   (Lv.{current_level} → Lv.{current_level + 1})")
            self.logger.info(f"   进度: {current_level}/{max_level}")

            success = self._train_skill_level_up(skill)

            if success:
                # 在对应的树上提升技能等级
                new_level = current_level + 1
                if skill_tree == 'general':
                    tree = self.skill_coordinator.general_tree
                    if skill_id in tree.get('skills', {}):
                        tree['skills'][skill_id]['level'] = new_level
                else:
                    tree = self.skill_coordinator.domain_tree
                    if skill_id in tree.get('skills', {}):
                        tree['skills'][skill_id]['level'] = new_level

                # 记录进化成功
                self.skill_coordinator.record_evolution_success(
                    skill_tree, skill_id, new_level
                )

                # 检查解锁新技能
                self._check_and_unlock_new_skills()

                self.skill_evolution_count += 1
                self.logger.info(
                    f"✅ {tree_emoji} 技能提升: {skill_name} (Lv.{new_level})"
                )

                # 尝试优化通用技能树（只有通用技能才触发优化）
                if skill_tree == 'general':
                    self._try_optimize_general_tree(skill_id, new_level)
            else:
                self.logger.warning(f"❌ 提升失败: {skill_name}")

    def _check_and_unlock_new_skills(self):
        """检查并自动解锁满足前置条件的技能"""
        if not self.skill_coordinator:
            return

        newly_unlocked = self.skill_coordinator.check_and_unlock_all_skills()
        for unlock_info in newly_unlocked:
            skill_id = unlock_info['skill_id']
            tree_type = unlock_info['tree']
            tree_emoji = "📚" if tree_type == 'general' else "🎯"
            self.logger.info(f"   {tree_emoji} 自动解锁: {skill_id}")

    def _try_optimize_general_tree(
        self,
        evolved_skill_id: str = None,
        evolved_skill_level: int = 0
    ):
        """
        尝试优化通用技能树

        触发条件：
        1. 每5次进化自动触发
        2. 通用技能达到特定里程碑（5/10/15/20级）

        优化内容：
        1. AI发现新技能并添加到技能树
        2. 检测技能协同效应
        3. 调整技能优先级
        """
        if not self.general_tree_optimizer:
            return

        # 判断是否应该触发优化
        should_optimize = False
        trigger_reason = ""

        # 条件1：每5次进化
        if self.skill_evolution_count > 0 and self.skill_evolution_count % 5 == 0:
            should_optimize = True
            trigger_reason = f"进化里程碑(第{self.skill_evolution_count}次)"

        # 条件2：通用技能达到特定等级
        if evolved_skill_level in [5, 10, 15, 20]:
            should_optimize = True
            trigger_reason = f"技能里程碑({evolved_skill_id} Lv.{evolved_skill_level})"

        if not should_optimize:
            return

        self.logger.info(f"🧬 触发通用技能树优化: {trigger_reason}")

        try:
            # 构建完整的优化上下文
            context = self.skill_coordinator.get_evolution_context()

            # 执行优化
            result = self.general_tree_optimizer.optimize(
                trigger_skill=evolved_skill_id or 'evolution_milestone',
                trigger_level=evolved_skill_level or self.skill_evolution_count,
                context=context
            )

            # 处理优化结果
            changes = result.get('changes', [])
            new_skills_added = [c for c in changes if c.get('type') == 'add_skill']

            if new_skills_added:
                self.logger.info(f"   💡 AI发现并添加 {len(new_skills_added)} 个新技能:")
                for change in new_skills_added:
                    skill_id = change.get('skill_id', '')
                    skill = self.skill_coordinator.general_tree.get('skills', {}).get(skill_id, {})  # noqa: E501
                    self.logger.info(f"      + {skill.get('name', skill_id)}")
                    self.logger.info(f"        原因: {change.get('reason', '')}")

                # 持久化更新后的技能树
                self._save_general_tree()
                self.logger.info("   💾 技能树已更新并保存")

            # 显示协同效应
            synergies = result.get('synergies', [])
            if synergies:
                self.logger.info(f"   🔗 发现 {len(synergies)} 个技能协同效应")

        except Exception as e:
            self.logger.warning(f"   ⚠️ 优化过程出错: {e}")

    def _save_general_tree(self):
        """保存更新后的通用技能树"""
        if not self.skill_coordinator:
            return

        try:
            import json
            tree_path = self.skill_coordinator.general_tree_path
            tree_data = self.skill_coordinator.general_tree

            with open(tree_path, 'w', encoding='utf-8') as f:
                json.dump(tree_data, f, ensure_ascii=False, indent=2)

        except Exception as e:
            self.logger.error(f"保存通用技能树失败: {e}")

    def _execute_single_tree_evolution(self):
        """单树模式进化（向后兼容）"""
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
            self.logger.info(f"📈 提升技能: {skill_name}")
            self.logger.info(f"   (Lv.{current_level} → Lv.{current_level + 1})")
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

            # 检查是否进行了 AI 自修复
            opt_info = result.get('optimization_info', {})
            repair = opt_info.get('repair_result', {})
            if repair.get('success'):
                self.logger.info("   🔄 AI 已修复技能代码，立即重试训练...")
                # 重试一次训练
                retry_result = self.skill_generator.upgrade_skill(
                    skill_id, target_level
                )
                if retry_result['success']:
                    self.logger.info(f"   ✅ 修复后训练通过!")
                    return True
                else:
                    self.logger.warning(
                        f"   修复后仍未通过: "
                        f"{retry_result.get('error')}"
                    )

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

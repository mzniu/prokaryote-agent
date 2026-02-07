"""
技能进化协调器 - 统筹通用技能和专业技能的进化

核心职责：
1. 管理通用技能树和专业技能树
2. 根据Agent发展阶段决定进化优先级
3. 协调通用/专业技能的选择
4. 触发AI优化通用技能树
"""

import json
import logging
import random
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple
# datetime 保留备用

logger = logging.getLogger(__name__)


class EvolutionStage:
    """进化阶段"""
    SPROUTING = "sprouting"      # 萌芽期：总等级 < 30
    GROWING = "growing"          # 成长期：30 <= 总等级 < 100
    MATURING = "maturing"        # 成熟期：100 <= 总等级 < 300
    SPECIALIZING = "specializing"  # 专精期：总等级 >= 300


class SkillEvolutionCoordinator:
    """技能进化协调器"""

    # 各阶段的优先级配置
    STAGE_PRIORITIES = {
        EvolutionStage.SPROUTING: {'general': 0.80, 'domain': 0.20},
        EvolutionStage.GROWING: {'general': 0.60, 'domain': 0.40},
        EvolutionStage.MATURING: {'general': 0.40, 'domain': 0.60},
        EvolutionStage.SPECIALIZING: {'general': 0.25, 'domain': 0.75},
    }

    # 阶段边界
    STAGE_THRESHOLDS = {
        EvolutionStage.SPROUTING: 0,
        EvolutionStage.GROWING: 30,
        EvolutionStage.MATURING: 100,
        EvolutionStage.SPECIALIZING: 300,
    }

    def __init__(
        self,
        general_tree_path: str,
        domain_tree_path: str,
        enable_ai_optimization: bool = True
    ):
        """
        初始化协调器

        Args:
            general_tree_path: 通用技能树路径
            domain_tree_path: 专业技能树路径
            enable_ai_optimization: 是否启用AI优化
        """
        self.general_tree_path = Path(general_tree_path)
        self.domain_tree_path = Path(domain_tree_path)
        self.enable_ai_optimization = enable_ai_optimization

        # 加载技能树
        self.general_tree = self._load_tree(self.general_tree_path)
        self.domain_tree = self._load_tree(self.domain_tree_path)

        # 统计
        self.evolution_count = {'general': 0, 'domain': 0}

        logger.info(
            "协调器初始化: 通用技能 %d 个, 专业技能 %d 个",
            len(self.general_tree.get('skills', {})),
            len(self.domain_tree.get('skills', {}))
        )

    def _load_tree(self, path: Path) -> Dict:
        """加载技能树"""
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'skills': {}}

    def _save_tree(self, tree: Dict, path: Path):
        """保存技能树"""
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(tree, f, ensure_ascii=False, indent=2)

    def get_general_level_sum(self) -> int:
        """获取通用技能总等级"""
        return sum(
            s.get('level', 0)
            for s in self.general_tree.get('skills', {}).values()
        )

    def get_domain_level_sum(self) -> int:
        """获取专业技能总等级"""
        return sum(
            s.get('level', 0)
            for s in self.domain_tree.get('skills', {}).values()
        )

    def get_total_level(self) -> int:
        """获取总等级"""
        return self.get_general_level_sum() + self.get_domain_level_sum()

    def get_current_stage(self) -> str:
        """获取当前进化阶段"""
        total = self.get_total_level()

        if total >= self.STAGE_THRESHOLDS[EvolutionStage.SPECIALIZING]:
            return EvolutionStage.SPECIALIZING
        elif total >= self.STAGE_THRESHOLDS[EvolutionStage.MATURING]:
            return EvolutionStage.MATURING
        elif total >= self.STAGE_THRESHOLDS[EvolutionStage.GROWING]:
            return EvolutionStage.GROWING
        else:
            return EvolutionStage.SPROUTING

    def get_current_priority(self) -> Dict[str, float]:
        """获取当前优先级"""
        stage = self.get_current_stage()
        return self.STAGE_PRIORITIES[stage]

    def get_unlocked_skills(self, tree: Dict) -> List[Dict]:
        """获取已解锁的技能"""
        skills = []
        for skill_id, skill in tree.get('skills', {}).items():
            if skill.get('unlocked', False):
                skill_copy = skill.copy()
                skill_copy['id'] = skill_id
                skills.append(skill_copy)
        return skills

    def get_evolvable_skills(self, tree: Dict) -> List[Dict]:
        """获取可进化的技能（已解锁且未满级）"""
        max_levels = {'basic': 20, 'intermediate': 30, 'advanced': 50}
        skills = []

        for skill_id, skill in tree.get('skills', {}).items():
            if not skill.get('unlocked', False):
                continue

            tier = skill.get('tier', 'basic')
            max_level = skill.get('max_level', max_levels.get(tier, 20))
            current_level = skill.get('level', 0)

            if current_level < max_level:
                skill_copy = skill.copy()
                skill_copy['id'] = skill_id
                skill_copy['max_level'] = max_level
                skills.append(skill_copy)

        return skills

    def check_and_unlock_all_skills(self) -> List[Dict]:
        """
        检查并解锁两棵技能树中满足条件的技能

        Returns:
            解锁的技能列表，每个元素包含 skill_id 和 tree 字段
        """
        result = []

        # 检查通用技能树
        general_unlocked = self.check_and_unlock_skills(self.general_tree)
        for skill_id in general_unlocked:
            result.append({'skill_id': skill_id, 'tree': 'general'})

        # 检查领域技能树
        domain_unlocked = self.check_and_unlock_skills(self.domain_tree)
        for skill_id in domain_unlocked:
            result.append({'skill_id': skill_id, 'tree': 'domain'})

        return result

    def check_and_unlock_skills(self, tree: Dict) -> List[str]:
        """检查并解锁满足条件的技能"""
        unlocked = []
        skills = tree.get('skills', {})

        for skill_id, skill in skills.items():
            if skill.get('unlocked', False):
                continue

            # 检查前置条件
            prerequisites = skill.get('prerequisites', [])
            if not prerequisites:
                skill['unlocked'] = True
                unlocked.append(skill_id)
                continue

            # 检查解锁条件表达式
            unlock_condition = skill.get('unlock_condition', '')
            if unlock_condition:
                if self._evaluate_condition(unlock_condition, skills):
                    skill['unlocked'] = True
                    unlocked.append(skill_id)
            else:
                # 默认：所有前置技能等级 >= 5
                all_met = all(
                    skills.get(p, {}).get('level', 0) >= 5
                    for p in prerequisites
                )
                if all_met:
                    skill['unlocked'] = True
                    unlocked.append(skill_id)

        return unlocked

    def _evaluate_condition(self, condition: str, skills: Dict) -> bool:
        """评估解锁条件表达式"""
        try:
            # 简单的条件解析：skill_id >= N AND skill_id >= M
            condition = condition.replace(' AND ', ' and ').replace(' OR ', ' or ')

            # 替换技能名为等级值
            for skill_id in skills:
                level = skills[skill_id].get('level', 0)
                condition = condition.replace(skill_id, str(level))

            return eval(condition)
        except Exception:
            return False

    def select_next_skill(self) -> Tuple[str, Optional[Dict]]:
        """
        选择下一个要进化的技能

        Returns:
            (skill_type, skill) - skill_type: 'general' 或 'domain'
        """
        priority = self.get_current_priority()

        # 检查解锁
        self.check_and_unlock_skills(self.general_tree)
        self.check_and_unlock_skills(self.domain_tree)

        # 获取可进化技能
        general_candidates = self.get_evolvable_skills(self.general_tree)
        domain_candidates = self.get_evolvable_skills(self.domain_tree)

        # 如果一方没有可进化技能，选择另一方
        if not general_candidates and not domain_candidates:
            return ('none', None)
        if not general_candidates:
            return ('domain', self._select_best_candidate(domain_candidates))
        if not domain_candidates:
            return ('general', self._select_best_candidate(general_candidates))

        # 按优先级随机选择类别
        if random.random() < priority['general']:
            return ('general', self._select_best_candidate(general_candidates))
        else:
            return ('domain', self._select_best_candidate(domain_candidates))

    def _select_best_candidate(self, candidates: List[Dict]) -> Dict:
        """
        从候选技能中选择最佳

        选择策略：
        1. 优先低等级技能
        2. 同等级优先基础技能
        3. 考虑类别优先级
        """
        if not candidates:
            return None

        # 按等级排序，同等级按tier排序
        tier_order = {'basic': 0, 'intermediate': 1, 'advanced': 2}

        candidates.sort(key=lambda s: (
            s.get('level', 0),
            tier_order.get(s.get('tier', 'basic'), 0)
        ))

        # 取前3个低等级技能随机选一个（避免太固定）
        top_candidates = candidates[:min(3, len(candidates))]
        return random.choice(top_candidates)

    def record_evolution_success(
        self,
        skill_type: str,
        skill_id: str,
        new_level: int
    ):
        """
        记录进化成功

        Args:
            skill_type: 'general' 或 'domain'
            skill_id: 技能ID
            new_level: 新等级
        """
        self.evolution_count[skill_type] = \
            self.evolution_count.get(skill_type, 0) + 1

        # 更新技能树
        if skill_type == 'general':
            tree = self.general_tree
            path = self.general_tree_path
        else:
            tree = self.domain_tree
            path = self.domain_tree_path

        if skill_id in tree.get('skills', {}):
            tree['skills'][skill_id]['level'] = new_level
            self._save_tree(tree, path)

        # 检查解锁新技能
        unlocked = self.check_and_unlock_skills(tree)
        if unlocked:
            logger.info("解锁新技能: %s", unlocked)
            self._save_tree(tree, path)

        # 触发AI优化（通用技能）
        if skill_type == 'general' and self.enable_ai_optimization:
            self._trigger_ai_optimization(skill_id, new_level)

    def _trigger_ai_optimization(self, skill_id: str, new_level: int):
        """触发AI优化通用技能树"""
        # 每5次进化触发一次优化
        if self.evolution_count['general'] % 5 != 0:
            return

        try:
            from .general_tree_optimizer import GeneralTreeOptimizer

            optimizer = GeneralTreeOptimizer(self.general_tree)
            result = optimizer.optimize(
                trigger_skill=skill_id,
                trigger_level=new_level,
                context=self.get_evolution_context()
            )

            if result.get('changes'):
                self.general_tree = result['tree']
                self._save_tree(self.general_tree, self.general_tree_path)
                logger.info("AI优化完成: %s", result.get('summary', ''))

        except ImportError:
            logger.debug("AI优化模块未加载")
        except Exception as e:
            logger.warning("AI优化失败: %s", e)

    def get_evolution_context(self) -> Dict[str, Any]:
        """获取进化上下文"""
        return {
            'general_level': self.get_general_level_sum(),
            'domain_level': self.get_domain_level_sum(),
            'total_level': self.get_total_level(),
            'stage': self.get_current_stage(),
            'priority': self.get_current_priority(),
            'evolution_count': self.evolution_count,
            'general_skills': {
                k: {'level': v.get('level', 0), 'unlocked': v.get('unlocked', False)}
                for k, v in self.general_tree.get('skills', {}).items()
            },
            'domain_skills': {
                k: {'level': v.get('level', 0), 'unlocked': v.get('unlocked', False)}
                for k, v in self.domain_tree.get('skills', {}).items()
            }
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stage = self.get_current_stage()
        stage_names = {
            EvolutionStage.SPROUTING: "萌芽期",
            EvolutionStage.GROWING: "成长期",
            EvolutionStage.MATURING: "成熟期",
            EvolutionStage.SPECIALIZING: "专精期",
        }

        general_unlocked = len(self.get_unlocked_skills(self.general_tree))
        general_total = len(self.general_tree.get('skills', {}))
        domain_unlocked = len(self.get_unlocked_skills(self.domain_tree))
        domain_total = len(self.domain_tree.get('skills', {}))

        return {
            'stage': stage,
            'stage_name': stage_names.get(stage, stage),
            'total_level': self.get_total_level(),
            'general': {
                'level_sum': self.get_general_level_sum(),
                'unlocked': general_unlocked,
                'total': general_total,
                'evolutions': self.evolution_count.get('general', 0)
            },
            'domain': {
                'level_sum': self.get_domain_level_sum(),
                'unlocked': domain_unlocked,
                'total': domain_total,
                'evolutions': self.evolution_count.get('domain', 0)
            },
            'priority': self.get_current_priority()
        }

    def print_status(self):
        """打印状态"""
        stats = self.get_stats()
        priority = stats['priority']

        print(f"\n{'='*50}")
        print(f"进化阶段: {stats['stage_name']} (总等级: {stats['total_level']})")
        print(f"当前优先级: 通用 {priority['general']:.0%} / 专业 {priority['domain']:.0%}")
        print(f"{'='*50}")
        print(f"通用技能: Lv.{stats['general']['level_sum']} "
              f"({stats['general']['unlocked']}/{stats['general']['total']} 已解锁)")
        print(f"专业技能: Lv.{stats['domain']['level_sum']} "
              f"({stats['domain']['unlocked']}/{stats['domain']['total']} 已解锁)")
        print(f"{'='*50}\n")

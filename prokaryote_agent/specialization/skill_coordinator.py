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

logger = logging.getLogger(__name__)


class EvolutionStage:
    """进化阶段（由多维进化指数决定）"""
    SPROUTING = "sprouting"        # 萌芽期
    GROWING = "growing"            # 成长期
    MATURING = "maturing"          # 成熟期
    SPECIALIZING = "specializing"  # 专精期


class SkillEvolutionCoordinator:
    """技能进化协调器"""

    # 各阶段的优先级配置
    STAGE_PRIORITIES = {
        EvolutionStage.SPROUTING: {'general': 0.80, 'domain': 0.20},
        EvolutionStage.GROWING: {'general': 0.60, 'domain': 0.40},
        EvolutionStage.MATURING: {'general': 0.40, 'domain': 0.60},
        EvolutionStage.SPECIALIZING: {'general': 0.25, 'domain': 0.75},
    }

    # 阶段边界（基于进化指数 0-100）
    STAGE_THRESHOLDS = {
        EvolutionStage.SPROUTING: 0,
        EvolutionStage.GROWING: 15,
        EvolutionStage.MATURING: 40,
        EvolutionStage.SPECIALIZING: 70,
    }

    # 各层级默认最大等级
    DEFAULT_MAX_LEVELS = {
        'basic': 20,
        'intermediate': 30,
        'advanced': 50,
        'expert': 50,
        'master': 50,
    }

    # 层级权重（用于 tier_score 计算）
    TIER_WEIGHTS = {
        'basic': 1,
        'intermediate': 2,
        'advanced': 3,
        'expert': 4,
        'master': 5,
    }

    # 失败回退参数
    COOLDOWN_SHORT = 3     # 连续失败3次 → 冷却轮数
    COOLDOWN_LONG = 10     # 连续失败5次 → 冷却轮数
    FAILURE_PENALTY_STEP = 0.2   # 每次连续失败的降权
    FAILURE_PENALTY_MAX = 0.8    # 最大降权
    PREREQ_BONUS_DIRECT = 0.3   # 直接前置加成
    PREREQ_BONUS_INDIRECT = 0.15  # 间接前置加成

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

        # 失败追踪（持久化）
        self._tracker_path = (
            self.general_tree_path.parent.parent
            / 'config' / 'failure_tracker.json'
        )
        self._failure_tracker = self._load_failure_tracker()

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

    # --------------------------------------------------
    # 失败追踪持久化
    # --------------------------------------------------

    def _load_failure_tracker(self) -> Dict:
        """加载失败追踪数据"""
        if self._tracker_path.exists():
            try:
                with open(
                    self._tracker_path, 'r', encoding='utf-8'
                ) as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("失败追踪文件损坏, 重置")
        return {'evolution_round': 0, 'skills': {}}

    def _save_failure_tracker(self):
        """保存失败追踪数据"""
        self._tracker_path.parent.mkdir(
            parents=True, exist_ok=True
        )
        with open(
            self._tracker_path, 'w', encoding='utf-8'
        ) as f:
            json.dump(
                self._failure_tracker, f,
                ensure_ascii=False, indent=2,
            )

    @property
    def evolution_round(self) -> int:
        return self._failure_tracker.get(
            'evolution_round', 0
        )

    @evolution_round.setter
    def evolution_round(self, value: int):
        self._failure_tracker['evolution_round'] = value

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
        """获取当前进化阶段（基于多维进化指数）"""
        index = self.calculate_evolution_index()['index']

        if index >= self.STAGE_THRESHOLDS[EvolutionStage.SPECIALIZING]:
            return EvolutionStage.SPECIALIZING
        elif index >= self.STAGE_THRESHOLDS[EvolutionStage.MATURING]:
            return EvolutionStage.MATURING
        elif index >= self.STAGE_THRESHOLDS[EvolutionStage.GROWING]:
            return EvolutionStage.GROWING
        else:
            return EvolutionStage.SPROUTING

    def calculate_evolution_index(self) -> Dict[str, Any]:
        """
        计算多维进化指数

        四个维度:
        - breadth (广度): 已解锁技能数 / 技能树总数
        - depth   (深度): Σ技能等级 / Σ最大等级(已解锁)
        - tier    (层次): 已解锁层级的加权覆盖率
        - mastery (实战): 达到50%等级上限的技能数 / 已解锁数

        Returns:
            包含 index(0-100) 和各维度分数的字典
        """
        all_skills = self._collect_all_skills()

        total_count = len(all_skills)
        if total_count == 0:
            return self._empty_index()

        unlocked = [
            s for s in all_skills if s['unlocked']
        ]
        unlocked_count = len(unlocked)

        # --- 广度 breadth ---
        breadth = unlocked_count / total_count

        # --- 深度 depth ---
        level_sum = 0
        max_level_sum = 0
        for s in unlocked:
            level_sum += s['level']
            max_level_sum += s['max_level']
        depth = (
            level_sum / max_level_sum
            if max_level_sum > 0 else 0.0
        )

        # --- 层次 tier ---
        # 已解锁技能中各层级的加权得分
        total_possible_weight = sum(
            self.TIER_WEIGHTS.get(s['tier'], 1)
            for s in all_skills
        )
        unlocked_weight = sum(
            self.TIER_WEIGHTS.get(s['tier'], 1)
            for s in unlocked
        )
        tier_score = (
            unlocked_weight / total_possible_weight
            if total_possible_weight > 0 else 0.0
        )

        # --- 实战 mastery ---
        # 达到 50% 最大等级的技能数
        mastered = sum(
            1 for s in unlocked
            if s['level'] >= s['max_level'] * 0.5
        )
        mastery = (
            mastered / unlocked_count
            if unlocked_count > 0 else 0.0
        )

        # 加权合成
        index = (
            breadth * 0.25
            + depth * 0.35
            + tier_score * 0.20
            + mastery * 0.20
        ) * 100

        return {
            'index': round(index, 1),
            'breadth': round(breadth, 3),
            'depth': round(depth, 3),
            'tier': round(tier_score, 3),
            'mastery': round(mastery, 3),
            'detail': {
                'total_skills': total_count,
                'unlocked_skills': unlocked_count,
                'level_sum': level_sum,
                'max_level_sum': max_level_sum,
                'mastered_skills': mastered,
            }
        }

    def _collect_all_skills(self) -> List[Dict]:
        """汇总两棵树的全部技能信息"""
        result = []
        for tree in (self.general_tree, self.domain_tree):
            for sid, s in tree.get('skills', {}).items():
                tier = s.get('tier', 'basic')
                max_lvl = s.get(
                    'max_level',
                    self.DEFAULT_MAX_LEVELS.get(tier, 20)
                )
                result.append({
                    'id': sid,
                    'tier': tier,
                    'level': s.get('level', 0),
                    'max_level': max_lvl,
                    'unlocked': s.get('unlocked', False),
                })
        return result

    @staticmethod
    def _empty_index() -> Dict[str, Any]:
        """空技能树时的默认指数"""
        return {
            'index': 0.0,
            'breadth': 0.0,
            'depth': 0.0,
            'tier': 0.0,
            'mastery': 0.0,
            'detail': {
                'total_skills': 0,
                'unlocked_skills': 0,
                'level_sum': 0,
                'max_level_sum': 0,
                'mastered_skills': 0,
            },
        }

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
        """获取可进化的技能（已解锁且未满级，排除冷却中的）"""
        skills = []
        current_round = self.evolution_round
        tracker_skills = self._failure_tracker.get(
            'skills', {}
        )

        for skill_id, skill in tree.get('skills', {}).items():
            if not skill.get('unlocked', False):
                continue

            tier = skill.get('tier', 'basic')
            max_level = skill.get(
                'max_level',
                self.DEFAULT_MAX_LEVELS.get(tier, 20),
            )
            current_level = skill.get('level', 0)

            if current_level >= max_level:
                continue

            # 冷却过滤
            ft = tracker_skills.get(skill_id, {})
            cooldown_until = ft.get('cooldown_until', 0)
            if cooldown_until > current_round:
                continue

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
        # 递增进化轮次
        self.evolution_round += 1
        self._save_failure_tracker()

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
        基于多因子评分选择最佳进化候选

        score = base_priority - failure_penalty + prereq_bonus
        """
        if not candidates:
            return None

        tracker_skills = self._failure_tracker.get(
            'skills', {}
        )
        boost_targets = self._get_boost_targets()

        scored = []
        for c in candidates:
            sid = c.get('id', '')
            level = c.get('level', 0)
            max_lvl = c.get('max_level', 20)
            tier = c.get('tier', 'basic')
            tier_order = {
                'basic': 0, 'intermediate': 1,
                'advanced': 2, 'expert': 3, 'master': 4,
            }

            # 基础分（低等级优先 0~1）
            base = 1.0 - (level / max_lvl if max_lvl else 0)
            base += (4 - tier_order.get(tier, 0)) * 0.05

            # 失败惩罚
            ft = tracker_skills.get(sid, {})
            consec = ft.get('consecutive_failures', 0)
            penalty = min(
                consec * self.FAILURE_PENALTY_STEP,
                self.FAILURE_PENALTY_MAX,
            )

            # 前置加成
            bonus = boost_targets.get(sid, 0.0)

            score = base - penalty + bonus
            scored.append((score, c))

        scored.sort(key=lambda x: x[0], reverse=True)

        # top-3 随机选择
        top = scored[:min(3, len(scored))]
        return random.choice(top)[1]

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

        # 清除失败记录
        tracker_skills = self._failure_tracker.setdefault(
            'skills', {}
        )
        if skill_id in tracker_skills:
            del tracker_skills[skill_id]
            self._save_failure_tracker()
            logger.info("清除 %s 的失败记录", skill_id)

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

    # --------------------------------------------------
    # 失败记录 & 回退策略
    # --------------------------------------------------

    def record_evolution_failure(
        self,
        skill_type: str,
        skill_id: str,
        level: int,
        reason: str = '',
    ) -> Dict[str, Any]:
        """
        记录进化失败并触发回退策略

        Returns:
            回退策略信息: {
                'action': 'cooldown'|'boost_prereqs'|'create_prereqs'|'none',
                'details': ...
            }
        """
        tracker_skills = self._failure_tracker.setdefault(
            'skills', {}
        )
        rec = tracker_skills.setdefault(skill_id, {
            'consecutive_failures': 0,
            'total_failures': 0,
            'cooldown_until': 0,
            'last_failed_level': 0,
            'failure_reasons': [],
            'boost_prerequisites': {},
        })

        rec['consecutive_failures'] += 1
        rec['total_failures'] += 1
        rec['last_failed_level'] = level
        if reason and reason not in rec['failure_reasons']:
            rec['failure_reasons'].append(reason)
        # 只保留最近 5 条原因
        rec['failure_reasons'] = rec['failure_reasons'][-5:]

        consec = rec['consecutive_failures']
        current_round = self.evolution_round
        result = {'action': 'none', 'details': {}}

        if consec >= 5:
            # 长期冷却
            rec['cooldown_until'] = (
                current_round + self.COOLDOWN_LONG
            )
            result['action'] = 'long_cooldown'
            result['details'] = {
                'cooldown_rounds': self.COOLDOWN_LONG,
                'until_round': rec['cooldown_until'],
            }
            logger.warning(
                "技能 %s 连续失败 %d 次, 长期冷却 %d 轮",
                skill_id, consec, self.COOLDOWN_LONG,
            )
        elif consec >= 3:
            # 短期冷却 + 尝试提升前置
            rec['cooldown_until'] = (
                current_round + self.COOLDOWN_SHORT
            )
            boost = self._find_prerequisite_boost_targets(
                skill_type, skill_id
            )
            rec['boost_prerequisites'] = dict(boost)
            result['action'] = 'boost_prereqs'
            result['details'] = {
                'cooldown_rounds': self.COOLDOWN_SHORT,
                'until_round': rec['cooldown_until'],
                'boost_targets': boost,
            }
            logger.info(
                "技能 %s 连续失败 %d 次, 冷却 %d 轮,"
                " 提升前置: %s",
                skill_id, consec, self.COOLDOWN_SHORT,
                list(boost.keys()),
            )
        else:
            # 降权但不冷却
            result['action'] = 'deprioritize'
            result['details'] = {
                'penalty': min(
                    consec * self.FAILURE_PENALTY_STEP,
                    self.FAILURE_PENALTY_MAX,
                ),
            }

        self._save_failure_tracker()
        return result

    def _find_prerequisite_boost_targets(
        self,
        skill_type: str,
        skill_id: str,
    ) -> Dict[str, float]:
        """
        查找失败技能的前置技能中值得提升的目标

        Returns:
            {skill_id: bonus} — 直接前置 0.3, 间接前置 0.15
        """
        tree = (
            self.general_tree
            if skill_type == 'general'
            else self.domain_tree
        )
        skills = tree.get('skills', {})
        target_skill = skills.get(skill_id, {})
        prereqs = target_skill.get('prerequisites', [])

        boost = {}

        for pid in prereqs:
            prereq = skills.get(pid)
            if prereq is None:
                continue
            tier = prereq.get('tier', 'basic')
            max_lvl = prereq.get(
                'max_level',
                self.DEFAULT_MAX_LEVELS.get(tier, 20)
            )
            lvl = prereq.get('level', 0)
            # 前置技能尚未达到 50% 上限 → 值得提升
            if lvl < max_lvl * 0.5:
                boost[pid] = self.PREREQ_BONUS_DIRECT

            # 沿链向上：前置的前置
            for ppid in prereq.get('prerequisites', []):
                pp = skills.get(ppid)
                if pp is None:
                    continue
                pp_tier = pp.get('tier', 'basic')
                pp_max = pp.get(
                    'max_level',
                    self.DEFAULT_MAX_LEVELS.get(pp_tier, 20)
                )
                if pp.get('level', 0) < pp_max * 0.5:
                    if ppid not in boost:
                        boost[ppid] = self.PREREQ_BONUS_INDIRECT

        return boost

    def _get_boost_targets(self) -> Dict[str, float]:
        """汇总所有失败技能的前置提升目标"""
        boost = {}
        for rec in self._failure_tracker.get(
            'skills', {}
        ).values():
            bp = rec.get('boost_prerequisites', {})
            if isinstance(bp, list):
                # 兼容旧格式
                for pid in bp:
                    old = boost.get(pid, 0.0)
                    boost[pid] = max(
                        old, self.PREREQ_BONUS_DIRECT
                    )
            else:
                for pid, val in bp.items():
                    old = boost.get(pid, 0.0)
                    boost[pid] = max(old, val)
        return boost

    def get_failure_summary(self) -> Dict[str, Any]:
        """获取失败追踪摘要"""
        tracker_skills = self._failure_tracker.get(
            'skills', {}
        )
        current_round = self.evolution_round
        cooling = []
        struggling = []
        for sid, rec in tracker_skills.items():
            if rec.get('cooldown_until', 0) > current_round:
                cooling.append({
                    'skill_id': sid,
                    'remaining': (
                        rec['cooldown_until'] - current_round
                    ),
                    'consecutive_failures': rec.get(
                        'consecutive_failures', 0
                    ),
                })
            elif rec.get('consecutive_failures', 0) > 0:
                struggling.append({
                    'skill_id': sid,
                    'consecutive_failures': rec[
                        'consecutive_failures'
                    ],
                })
        return {
            'evolution_round': current_round,
            'cooling_skills': cooling,
            'struggling_skills': struggling,
            'boost_targets': self._get_boost_targets(),
        }

    def get_evolution_context(self) -> Dict[str, Any]:
        """获取进化上下文"""
        evo = self.calculate_evolution_index()
        return {
            'general_level': self.get_general_level_sum(),
            'domain_level': self.get_domain_level_sum(),
            'total_level': self.get_total_level(),
            'evolution_index': evo,
            'stage': self.get_current_stage(),
            'priority': self.get_current_priority(),
            'evolution_count': self.evolution_count,
            'evolution_round': self.evolution_round,
            'failure_summary': self.get_failure_summary(),
            'general_skills': {
                k: {
                    'level': v.get('level', 0),
                    'unlocked': v.get('unlocked', False),
                }
                for k, v in self.general_tree.get(
                    'skills', {}
                ).items()
            },
            'domain_skills': {
                k: {
                    'level': v.get('level', 0),
                    'unlocked': v.get('unlocked', False),
                }
                for k, v in self.domain_tree.get(
                    'skills', {}
                ).items()
            },
        }

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        stage = self.get_current_stage()
        evo = self.calculate_evolution_index()
        stage_names = {
            EvolutionStage.SPROUTING: "萌芽期",
            EvolutionStage.GROWING: "成长期",
            EvolutionStage.MATURING: "成熟期",
            EvolutionStage.SPECIALIZING: "专精期",
        }

        general_unlocked = len(
            self.get_unlocked_skills(self.general_tree)
        )
        general_total = len(
            self.general_tree.get('skills', {})
        )
        domain_unlocked = len(
            self.get_unlocked_skills(self.domain_tree)
        )
        domain_total = len(
            self.domain_tree.get('skills', {})
        )

        return {
            'stage': stage,
            'stage_name': stage_names.get(stage, stage),
            'evolution_index': evo['index'],
            'dimensions': {
                'breadth': evo['breadth'],
                'depth': evo['depth'],
                'tier': evo['tier'],
                'mastery': evo['mastery'],
            },
            'total_level': self.get_total_level(),
            'total_skills': evo['detail']['total_skills'],
            'unlocked_skills': evo['detail']['unlocked_skills'],
            'mastered_skills': evo['detail']['mastered_skills'],
            'general': {
                'level_sum': self.get_general_level_sum(),
                'unlocked': general_unlocked,
                'total': general_total,
                'evolutions': self.evolution_count.get(
                    'general', 0
                ),
            },
            'domain': {
                'level_sum': self.get_domain_level_sum(),
                'unlocked': domain_unlocked,
                'total': domain_total,
                'evolutions': self.evolution_count.get(
                    'domain', 0
                ),
            },
            'priority': self.get_current_priority(),
            'failure_summary': self.get_failure_summary(),
        }

    def print_status(self):
        """打印状态"""
        stats = self.get_stats()
        priority = stats['priority']
        dims = stats['dimensions']

        print(f"\n{'='*50}")
        print(
            f"进化阶段: {stats['stage_name']}"
            f" (进化指数: {stats['evolution_index']:.1f})"
        )
        print(
            f"  广度={dims['breadth']:.0%}"
            f" 深度={dims['depth']:.0%}"
            f" 层次={dims['tier']:.0%}"
            f" 实战={dims['mastery']:.0%}"
        )
        print(
            f"技能: {stats['unlocked_skills']}"
            f"/{stats['total_skills']} 已解锁"
            f" | 精通: {stats['mastered_skills']}"
            f" | 总等级: {stats['total_level']}"
        )
        print(
            f"优先级: 通用 {priority['general']:.0%}"
            f" / 专业 {priority['domain']:.0%}"
        )
        print(f"{'='*50}")
        print(
            f"通用: Lv.{stats['general']['level_sum']}"
            f" ({stats['general']['unlocked']}"
            f"/{stats['general']['total']} 解锁)"
        )
        print(
            f"专业: Lv.{stats['domain']['level_sum']}"
            f" ({stats['domain']['unlocked']}"
            f"/{stats['domain']['total']} 解锁)"
        )

        # 失败回退信息
        fs = stats.get('failure_summary', {})
        cooling = fs.get('cooling_skills', [])
        struggling = fs.get('struggling_skills', [])
        if cooling or struggling:
            print(f"{'- '*25}")
            if cooling:
                names = [
                    f"{c['skill_id']}({c['remaining']}轮)"
                    for c in cooling
                ]
                print(f"冷却中: {', '.join(names)}")
            if struggling:
                names = [
                    f"{s['skill_id']}(×{s['consecutive_failures']})"
                    for s in struggling
                ]
                print(f"困难: {', '.join(names)}")
            boost = fs.get('boost_targets', {})
            if boost:
                print(f"优先提升: {', '.join(boost.keys())}")

        print(f"{'='*50}\n")

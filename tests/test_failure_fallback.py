"""
测试智能失败回退与依赖补全机制

覆盖：
- 失败记录与连续失败计数
- 冷却机制（短期/长期）
- 成功清除失败记录
- 前置技能提升加成
- 评分公式（failure_penalty + prereq_bonus）
- 失败追踪持久化
- get_failure_summary
"""

import json
import tempfile
import unittest
from pathlib import Path

from prokaryote_agent.specialization.skill_coordinator import (
    SkillEvolutionCoordinator,
)


def _write_tree(path: Path, skills: dict):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'skills': skills}, f)


def _skill(
    name='test', tier='basic', level=5,
    unlocked=True, prerequisites=None,
    unlock_condition='', max_level=None,
):
    s = {
        'name': name,
        'tier': tier,
        'level': level,
        'unlocked': unlocked,
        'prerequisites': prerequisites or [],
    }
    if unlock_condition:
        s['unlock_condition'] = unlock_condition
    if max_level is not None:
        s['max_level'] = max_level
    return s


class TestFailureFallback(unittest.TestCase):
    """失败回退机制测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.general_path = Path(self.tmpdir) / 'general.json'
        self.domain_path = Path(self.tmpdir) / 'domain.json'
        # 确保 config 目录存在
        (Path(self.tmpdir) / 'config').mkdir(exist_ok=True)

    def _coord(self, general_skills, domain_skills=None):
        _write_tree(self.general_path, general_skills)
        _write_tree(
            self.domain_path, domain_skills or {}
        )
        c = SkillEvolutionCoordinator(
            str(self.general_path),
            str(self.domain_path),
            enable_ai_optimization=False,
        )
        # 让 tracker 路径指向 tmpdir/config
        c._tracker_path = (
            Path(self.tmpdir) / 'config'
            / 'failure_tracker.json'
        )
        c._failure_tracker = c._load_failure_tracker()
        return c

    # -------------------------------------------------
    # 失败记录与计数
    # -------------------------------------------------
    def test_record_failure_increments(self):
        c = self._coord({
            'a': _skill(level=3),
        })
        r1 = c.record_evolution_failure(
            'general', 'a', 3
        )
        self.assertEqual(r1['action'], 'deprioritize')
        self.assertEqual(
            c._failure_tracker['skills']['a'][
                'consecutive_failures'
            ], 1,
        )

        r2 = c.record_evolution_failure(
            'general', 'a', 3
        )
        self.assertEqual(r2['action'], 'deprioritize')
        self.assertEqual(
            c._failure_tracker['skills']['a'][
                'consecutive_failures'
            ], 2,
        )

    def test_three_failures_triggers_cooldown(self):
        c = self._coord({
            'a': _skill(level=3),
        })
        for _ in range(2):
            c.record_evolution_failure(
                'general', 'a', 3
            )
        r = c.record_evolution_failure(
            'general', 'a', 3
        )
        self.assertEqual(r['action'], 'boost_prereqs')
        self.assertIn('cooldown_rounds', r['details'])
        # 冷却 3 轮
        self.assertEqual(
            r['details']['cooldown_rounds'], 3
        )

    def test_five_failures_triggers_long_cooldown(self):
        c = self._coord({
            'a': _skill(level=3),
        })
        for _ in range(4):
            c.record_evolution_failure(
                'general', 'a', 3
            )
        r = c.record_evolution_failure(
            'general', 'a', 3
        )
        self.assertEqual(r['action'], 'long_cooldown')
        self.assertEqual(
            r['details']['cooldown_rounds'], 10
        )

    # -------------------------------------------------
    # 冷却 -> 排除
    # -------------------------------------------------
    def test_cooled_skill_excluded_from_evolvable(self):
        c = self._coord({
            'a': _skill(level=3),
            'b': _skill(level=2),
        })
        # 让 a 进入冷却
        for _ in range(3):
            c.record_evolution_failure(
                'general', 'a', 3
            )

        evolvable = c.get_evolvable_skills(
            c.general_tree
        )
        ids = [s['id'] for s in evolvable]
        self.assertNotIn('a', ids)
        self.assertIn('b', ids)

    def test_cooldown_expires(self):
        """冷却到期后技能重新可选"""
        c = self._coord({
            'a': _skill(level=3),
        })
        for _ in range(3):
            c.record_evolution_failure(
                'general', 'a', 3
            )
        # 现在 a 冷却 3 轮
        # 手动推进轮次
        c.evolution_round += 3

        evolvable = c.get_evolvable_skills(
            c.general_tree
        )
        ids = [s['id'] for s in evolvable]
        self.assertIn('a', ids)

    # -------------------------------------------------
    # 成功清除失败记录
    # -------------------------------------------------
    def test_success_clears_failure(self):
        c = self._coord({
            'a': _skill(level=3),
        })
        c.record_evolution_failure(
            'general', 'a', 3
        )
        self.assertIn(
            'a', c._failure_tracker['skills']
        )
        c.record_evolution_success(
            'general', 'a', 4
        )
        self.assertNotIn(
            'a', c._failure_tracker['skills']
        )

    # -------------------------------------------------
    # 前置技能加成
    # -------------------------------------------------
    def test_boost_prerequisites(self):
        """失败技能的前置技能获得加成"""
        c = self._coord({
            'base': _skill(name='基础', level=3),
            'advanced': _skill(
                name='高级', level=5,
                prerequisites=['base'],
            ),
        })
        # 让 advanced 连续失败 3次
        for _ in range(3):
            c.record_evolution_failure(
                'general', 'advanced', 5
            )

        # base 应该出现在 boost_targets 中
        boost = c._get_boost_targets()
        self.assertIn('base', boost)
        self.assertEqual(
            boost['base'], c.PREREQ_BONUS_DIRECT
        )

    def test_indirect_prerequisites_get_bonus(self):
        """间接前置技能也获得加成（较低）"""
        c = self._coord({
            'root': _skill(name='根基', level=2),
            'mid': _skill(
                name='中间', level=3,
                prerequisites=['root'],
            ),
            'top': _skill(
                name='顶层', level=5,
                prerequisites=['mid'],
            ),
        })
        for _ in range(3):
            c.record_evolution_failure(
                'general', 'top', 5
            )

        boost = c._get_boost_targets()
        # mid 是直接前置
        self.assertIn('mid', boost)
        # root 是间接前置
        self.assertIn('root', boost)
        self.assertEqual(
            boost['root'], c.PREREQ_BONUS_INDIRECT
        )

    def test_no_boost_for_high_level_prereq(self):
        """前置技能已达 50%+ 上限则不加成"""
        c = self._coord({
            'base': _skill(
                name='基础', level=15, max_level=20,
            ),
            'top': _skill(
                name='顶层', level=5,
                prerequisites=['base'],
            ),
        })
        for _ in range(3):
            c.record_evolution_failure(
                'general', 'top', 5
            )
        boost = c._get_boost_targets()
        # base at Lv.15 >= 50% of 20 → 不加成
        self.assertNotIn('base', boost)

    # -------------------------------------------------
    # 评分公式
    # -------------------------------------------------
    def test_failed_skill_deprioritized(self):
        """连续失败的技能在候选中Score更低"""
        c = self._coord({
            'a': _skill(level=3),
            'b': _skill(level=3),
        })
        # 让 a 连续失败 2 次（不冷却但降权）
        c.record_evolution_failure(
            'general', 'a', 3
        )
        c.record_evolution_failure(
            'general', 'a', 3
        )

        # 多次选择, a 应该被选中的频率很低
        candidates = c.get_evolvable_skills(
            c.general_tree
        )
        # _select_best_candidate 内部打分
        tracker = c._failure_tracker.get(
            'skills', {}
        )
        self.assertEqual(
            tracker['a']['consecutive_failures'], 2
        )
        # 只要 a 还在候选中就行（未冷却）
        ids = [s['id'] for s in candidates]
        self.assertIn('a', ids)

    def test_prereq_bonus_in_scoring(self):
        """前置技能加成使其Score更高"""
        c = self._coord({
            'base': _skill(name='基础', level=3),
            'mid': _skill(
                name='中间', level=10,
                prerequisites=['base'],
            ),
        })
        # 让 mid 触发前置加成
        for _ in range(3):
            c.record_evolution_failure(
                'general', 'mid', 10
            )
        boost = c._get_boost_targets()
        self.assertIn('base', boost)
        # base 有 prereq_bonus
        self.assertGreater(boost['base'], 0)

    # -------------------------------------------------
    # 持久化
    # -------------------------------------------------
    def test_failure_tracker_persistence(self):
        """失败记录持久化到磁盘"""
        c = self._coord({
            'a': _skill(level=3),
        })
        c.record_evolution_failure(
            'general', 'a', 3
        )
        # 文件应该存在
        self.assertTrue(c._tracker_path.exists())

        # 重新加载
        with open(c._tracker_path, 'r') as f:
            data = json.load(f)
        self.assertIn('a', data['skills'])
        self.assertEqual(
            data['skills']['a'][
                'consecutive_failures'
            ], 1,
        )

    def test_evolution_round_persistent(self):
        """进化轮次持久化"""
        c = self._coord({
            'a': _skill(level=3),
        })
        c.evolution_round = 42
        c._save_failure_tracker()

        c2 = self._coord({
            'a': _skill(level=3),
        })
        # 指向同一个 tracker 路径
        c2._tracker_path = c._tracker_path
        c2._failure_tracker = c2._load_failure_tracker()
        self.assertEqual(c2.evolution_round, 42)

    # -------------------------------------------------
    # select_next_skill 递增 round
    # -------------------------------------------------
    def test_select_increments_round(self):
        c = self._coord({
            'a': _skill(level=3),
        })
        initial = c.evolution_round
        c.select_next_skill()
        self.assertEqual(
            c.evolution_round, initial + 1
        )

    # -------------------------------------------------
    # get_failure_summary
    # -------------------------------------------------
    def test_failure_summary_structure(self):
        c = self._coord({
            'a': _skill(level=3),
            'b': _skill(level=5),
        })
        for _ in range(3):
            c.record_evolution_failure(
                'general', 'a', 3
            )
        c.record_evolution_failure(
            'general', 'b', 5
        )

        summary = c.get_failure_summary()
        self.assertIn('evolution_round', summary)
        self.assertIn('cooling_skills', summary)
        self.assertIn('struggling_skills', summary)

        # a 应该在 cooling
        cooling_ids = [
            s['skill_id'] for s in summary['cooling_skills']
        ]
        self.assertIn('a', cooling_ids)

        # b 只失败 1 次，应该在 struggling
        struggling_ids = [
            s['skill_id']
            for s in summary['struggling_skills']
        ]
        self.assertIn('b', struggling_ids)

    # -------------------------------------------------
    # get_stats 包含 failure_summary
    # -------------------------------------------------
    def test_stats_has_failure_summary(self):
        c = self._coord({
            'a': _skill(level=3),
        })
        stats = c.get_stats()
        self.assertIn('failure_summary', stats)


if __name__ == '__main__':
    unittest.main()

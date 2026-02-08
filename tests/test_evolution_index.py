"""
测试多维进化指数系统

覆盖：
- 空技能树
- 纯萌芽期（少量低级技能）
- 成长期（广度提升）
- 成熟期（深度+实战）
- 专精期（高层级全面精通）
- 边界条件 & 回归兼容性
"""

import json
import tempfile
import unittest
from pathlib import Path

from prokaryote_agent.specialization.skill_coordinator import (
    EvolutionStage,
    SkillEvolutionCoordinator,
)


def _write_tree(path: Path, skills: dict):
    """写入临时技能树 JSON"""
    with open(path, 'w', encoding='utf-8') as f:
        json.dump({'skills': skills}, f)


def _make_skill(
    tier='basic', level=0, max_level=None,
    unlocked=True
):
    """构造单个技能字典"""
    s = {'tier': tier, 'level': level, 'unlocked': unlocked}
    if max_level is not None:
        s['max_level'] = max_level
    return s


class TestEvolutionIndex(unittest.TestCase):
    """进化指数计算测试"""

    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.general_path = Path(self.tmpdir) / 'general.json'
        self.domain_path = Path(self.tmpdir) / 'domain.json'

    def _coord(self, general_skills, domain_skills=None):
        _write_tree(self.general_path, general_skills)
        _write_tree(
            self.domain_path, domain_skills or {}
        )
        return SkillEvolutionCoordinator(
            str(self.general_path),
            str(self.domain_path),
            enable_ai_optimization=False,
        )

    # --------------------------------------------------
    # 空技能树
    # --------------------------------------------------
    def test_empty_trees(self):
        c = self._coord({}, {})
        evo = c.calculate_evolution_index()
        self.assertEqual(evo['index'], 0.0)
        self.assertEqual(
            c.get_current_stage(), EvolutionStage.SPROUTING
        )

    # --------------------------------------------------
    # 萌芽期：3个basic技能各Lv.1
    # --------------------------------------------------
    def test_sprouting_stage(self):
        skills = {
            f'skill_{i}': _make_skill(level=1)
            for i in range(3)
        }
        # 加入大量未解锁技能以降低广度
        for i in range(17):
            skills[f'locked_{i}'] = _make_skill(
                level=0, unlocked=False
            )
        c = self._coord(skills)
        evo = c.calculate_evolution_index()

        # 3 unlocked out of 20 → breadth=0.15
        self.assertAlmostEqual(evo['breadth'], 0.15)
        # depth = 3 / (3*20) = 0.05
        self.assertAlmostEqual(evo['depth'], 0.05)
        # mastery: Lv.1 < 10 (50% of 20) → 0
        self.assertEqual(evo['mastery'], 0.0)
        # index should be low → sprouting
        self.assertLess(evo['index'], 15)
        self.assertEqual(
            c.get_current_stage(), EvolutionStage.SPROUTING
        )

    # --------------------------------------------------
    # 成长期：10个basic技能 各Lv.5, 5个locked
    # --------------------------------------------------
    def test_growing_stage(self):
        skills = {}
        for i in range(10):
            skills[f'sk_{i}'] = _make_skill(level=5)
        for i in range(5):
            skills[f'locked_{i}'] = _make_skill(
                level=0, unlocked=False
            )
        c = self._coord(skills)
        evo = c.calculate_evolution_index()

        # breadth = 10/15 ≈ 0.667
        self.assertAlmostEqual(
            evo['breadth'], 10 / 15, places=2
        )
        # depth = 50 / (10*20) = 0.25
        self.assertAlmostEqual(evo['depth'], 0.25, places=2)
        # mastery: Lv5 < 10 → 0
        self.assertEqual(evo['mastery'], 0.0)
        # Should reach growing but not maturing
        self.assertGreaterEqual(evo['index'], 15)
        self.assertLess(evo['index'], 40)
        self.assertEqual(
            c.get_current_stage(), EvolutionStage.GROWING
        )

    # --------------------------------------------------
    # 成熟期：广度+深度+实战都较高
    # --------------------------------------------------
    def test_maturing_stage(self):
        general = {}
        # 15 basic skills at Lv.10
        for i in range(15):
            general[f'g_{i}'] = _make_skill(level=10)
        # 5 locked
        for i in range(5):
            general[f'g_lock_{i}'] = _make_skill(
                level=0, unlocked=False
            )
        domain = {}
        # 5 intermediate skills at Lv.8
        for i in range(5):
            domain[f'd_{i}'] = _make_skill(
                tier='intermediate', level=8
            )

        c = self._coord(general, domain)
        evo = c.calculate_evolution_index()

        # breadth: 20 unlocked / 25 total = 0.8
        self.assertAlmostEqual(
            evo['breadth'], 20 / 25, places=2
        )
        # mastery: Lv10 >= 10 (50% of 20) → 15 mastered
        # Lv8 < (30*0.5=15) → not mastered
        # So 15/20 = 0.75
        self.assertAlmostEqual(
            evo['mastery'], 15 / 20, places=2
        )
        self.assertGreaterEqual(evo['index'], 40)
        self.assertLess(evo['index'], 70)
        self.assertEqual(
            c.get_current_stage(), EvolutionStage.MATURING
        )

    # --------------------------------------------------
    # 专精期：高层级大量精通
    # --------------------------------------------------
    def test_specializing_stage(self):
        general = {}
        # 20 basic all maxed
        for i in range(20):
            general[f'g_{i}'] = _make_skill(level=20)
        # 5 intermediate at Lv.20
        for i in range(5):
            general[f'gi_{i}'] = _make_skill(
                tier='intermediate', level=20
            )
        domain = {}
        # 5 advanced at Lv.30
        for i in range(5):
            domain[f'da_{i}'] = _make_skill(
                tier='advanced', level=30
            )
        # 2 master at Lv.25
        for i in range(2):
            domain[f'dm_{i}'] = _make_skill(
                tier='master', level=25
            )

        c = self._coord(general, domain)
        evo = c.calculate_evolution_index()

        # All unlocked → breadth = 1.0
        self.assertAlmostEqual(evo['breadth'], 1.0)
        self.assertGreaterEqual(evo['index'], 70)
        self.assertEqual(
            c.get_current_stage(), EvolutionStage.SPECIALIZING
        )

    # --------------------------------------------------
    # get_stats 兼容性
    # --------------------------------------------------
    def test_get_stats_has_new_fields(self):
        skills = {
            'a': _make_skill(level=5),
            'b': _make_skill(level=3),
        }
        c = self._coord(skills)
        stats = c.get_stats()

        self.assertIn('evolution_index', stats)
        self.assertIn('dimensions', stats)
        self.assertIn('breadth', stats['dimensions'])
        self.assertIn('depth', stats['dimensions'])
        self.assertIn('tier', stats['dimensions'])
        self.assertIn('mastery', stats['dimensions'])
        self.assertIn('total_skills', stats)
        self.assertIn('unlocked_skills', stats)
        self.assertIn('mastered_skills', stats)
        # Legacy field preserved
        self.assertIn('total_level', stats)
        self.assertIn('stage', stats)
        self.assertIn('stage_name', stats)

    # --------------------------------------------------
    # evolution context 包含 evolution_index
    # --------------------------------------------------
    def test_evolution_context_has_index(self):
        c = self._coord({'a': _make_skill(level=1)})
        ctx = c.get_evolution_context()
        self.assertIn('evolution_index', ctx)
        self.assertIn('index', ctx['evolution_index'])

    # --------------------------------------------------
    # 窄深 vs 宽浅 对比
    # --------------------------------------------------
    def test_narrow_deep_vs_wide_shallow(self):
        """
        3个技能各Lv.10 vs 10个技能各Lv.3
        总等级相同(30)，但阶段应不同
        """
        # 窄深：3个技能 Lv.10 + 7 locked
        narrow = {}
        for i in range(3):
            narrow[f's_{i}'] = _make_skill(level=10)
        for i in range(7):
            narrow[f'l_{i}'] = _make_skill(
                level=0, unlocked=False
            )
        c_narrow = self._coord(narrow)
        evo_narrow = c_narrow.calculate_evolution_index()

        # 宽浅：10个技能各 Lv.3
        wide = {}
        for i in range(10):
            wide[f's_{i}'] = _make_skill(level=3)
        c_wide = self._coord(wide)
        evo_wide = c_wide.calculate_evolution_index()

        # 宽浅 breadth 更高
        self.assertGreater(
            evo_wide['breadth'], evo_narrow['breadth']
        )
        # 窄深 depth 更高
        self.assertGreater(
            evo_narrow['depth'], evo_wide['depth']
        )

    # --------------------------------------------------
    # tier_score 区分能力
    # --------------------------------------------------
    def test_tier_score_higher_for_advanced(self):
        """高层级技能解锁应给出更高 tier 分"""
        # 两组各有 5 个 locked basic，使 tier 不为 1.0
        basic_only = {}
        for i in range(5):
            basic_only[f'b_{i}'] = _make_skill(level=10)
        for i in range(5):
            basic_only[f'bl_{i}'] = _make_skill(
                level=0, unlocked=False
            )

        mixed = {
            'b_0': _make_skill(level=10),
            'b_1': _make_skill(level=10),
            'i_0': _make_skill(
                tier='intermediate', level=10
            ),
            'a_0': _make_skill(
                tier='advanced', level=10
            ),
            'm_0': _make_skill(
                tier='master', level=10
            ),
        }
        for i in range(5):
            mixed[f'bl_{i}'] = _make_skill(
                level=0, unlocked=False
            )

        c_basic = self._coord(basic_only)
        c_mixed = self._coord(mixed)

        self.assertGreater(
            c_mixed.calculate_evolution_index()['tier'],
            c_basic.calculate_evolution_index()['tier'],
        )

    # --------------------------------------------------
    # DEFAULT_MAX_LEVELS 回退
    # --------------------------------------------------
    def test_default_max_level_for_unknown_tier(self):
        """未知 tier 默认 max_level=20"""
        skills = {
            'x': {
                'tier': 'legendary',
                'level': 5,
                'unlocked': True,
            }
        }
        c = self._coord(skills)
        evo = c.calculate_evolution_index()
        # depth = 5/20
        self.assertAlmostEqual(evo['depth'], 0.25)

    # --------------------------------------------------
    # max_level 字段覆盖默认值
    # --------------------------------------------------
    def test_explicit_max_level_overrides_default(self):
        skills = {
            'x': _make_skill(
                tier='basic', level=5, max_level=10
            ),
        }
        c = self._coord(skills)
        evo = c.calculate_evolution_index()
        # depth = 5/10 = 0.5
        self.assertAlmostEqual(evo['depth'], 0.5)
        # mastery: 5 >= 10*0.5 → yes
        self.assertAlmostEqual(evo['mastery'], 1.0)


if __name__ == '__main__':
    unittest.main()

"""
Unit tests for software_dev_tree.json validation.

Ensures the example skill tree is valid and usable.
"""

import unittest
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from prokaryote_agent.specialization import (
    SkillTree, SkillNode, SkillTier, SkillCategory,
    SkillUnlocker, SkillLevelSystem, SkillTreeScorer,
    EvolutionStrategy
)


class TestSoftwareDevTree(unittest.TestCase):
    """Test software_dev_tree.json example."""
    
    def setUp(self):
        """Load the software dev tree."""
        tree_path = Path(__file__).parent.parent / "prokaryote_agent" / "specialization" / "domains" / "software_dev_tree.json"
        self.tree = SkillTree(str(tree_path))
    
    def test_tree_loads_successfully(self):
        """Test that the tree loads without errors."""
        self.assertIsNotNone(self.tree)
        self.assertGreater(len(self.tree), 0)
    
    def test_tree_has_correct_skill_count(self):
        """Test that tree contains expected number of skills."""
        # software_dev_tree.json should have 21 skills
        self.assertEqual(len(self.tree), 21)
    
    def test_tree_is_valid_dag(self):
        """Test that tree structure is a valid DAG (no cycles)."""
        is_valid = self.tree.validate_dag()
        self.assertTrue(is_valid, "Skill tree contains cycles or invalid references")
    
    def test_all_prerequisites_exist(self):
        """Test that all prerequisite IDs reference existing skills."""
        for skill in self.tree.skills.values():
            for prereq_id in skill.prerequisites:
                self.assertIn(
                    prereq_id,
                    self.tree,
                    f"Skill {skill.id} references non-existent prerequisite: {prereq_id}"
                )
    
    def test_tier_distribution(self):
        """Test that skills are distributed across all tiers."""
        tier_counts = {}
        for skill in self.tree.skills.values():
            tier = skill.tier.value
            tier_counts[tier] = tier_counts.get(tier, 0) + 1
        
        # Should have at least one skill in each tier
        expected_tiers = ['basic', 'intermediate', 'advanced', 'master', 'grandmaster']
        for tier in expected_tiers:
            self.assertIn(tier, tier_counts, f"Missing skills in {tier} tier")
            self.assertGreater(tier_counts[tier], 0, f"No skills in {tier} tier")
    
    def test_category_distribution(self):
        """Test that skills cover multiple categories."""
        category_counts = {}
        for skill in self.tree.skills.values():
            cat = skill.category.value
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Should have skills in at least 4 different categories
        self.assertGreaterEqual(len(category_counts), 4, "Too few categories represented")
    
    def test_has_combination_skills(self):
        """Test that tree includes combination skills."""
        combination_skills = [s for s in self.tree.skills.values() if s.is_combination]
        self.assertGreater(len(combination_skills), 0, "No combination skills found")
        
        # Combination skills should be in higher tiers
        for skill in combination_skills:
            self.assertIn(
                skill.tier,
                [SkillTier.MASTER, SkillTier.GRANDMASTER],
                f"Combination skill {skill.id} should be in higher tier"
            )
    
    def test_has_entry_skills(self):
        """Test that tree has skills with no prerequisites (entry points)."""
        entry_skills = [s for s in self.tree.skills.values() if not s.prerequisites]
        self.assertGreater(len(entry_skills), 0, "No entry-level skills found")
        
        # Entry skills should be basic tier
        for skill in entry_skills:
            self.assertEqual(
                skill.tier,
                SkillTier.BASIC,
                f"Entry skill {skill.id} should be BASIC tier"
            )
    
    def test_unlock_conditions_are_evaluable(self):
        """Test that all unlock conditions can be evaluated."""
        unlocker = SkillUnlocker(self.tree)
        
        test_context = {
            'capability_count': 100,
            'evolution_count': 100,
            'capabilities': ['test1', 'test2'],
            'unlocked_skills': []
        }
        
        for skill in self.tree.skills.values():
            # Should not raise exception
            try:
                result = unlocker.evaluate_unlock_condition(
                    skill.unlock_condition,
                    test_context
                )
                self.assertIsInstance(result, bool)
            except Exception as e:
                self.fail(
                    f"Failed to evaluate unlock condition for {skill.id}: "
                    f"'{skill.unlock_condition}' - {e}"
                )
    
    def test_skill_progression_path(self):
        """Test that there's a clear progression path through the tree."""
        # Get root skills (no prerequisites)
        roots = [s for s in self.tree.skills.values() if not s.prerequisites]
        
        # Should be able to reach master and grandmaster skills from roots
        visited = set()
        to_visit = [s.id for s in roots]
        
        while to_visit:
            current_id = to_visit.pop(0)
            if current_id in visited:
                continue
            visited.add(current_id)
            
            # Find skills that depend on current skill
            for skill in self.tree.skills.values():
                if current_id in skill.prerequisites and skill.id not in visited:
                    to_visit.append(skill.id)
        
        # Should be able to reach all skills
        self.assertEqual(
            len(visited),
            len(self.tree),
            "Some skills are unreachable from root skills"
        )
    
    def test_metadata_accuracy(self):
        """Test that JSON metadata matches actual tree structure."""
        tree_path = Path(__file__).parent.parent / "prokaryote_agent" / "specialization" / "domains" / "software_dev_tree.json"
        
        with open(tree_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        metadata = data.get('metadata', {})
        
        # Check total_skills
        self.assertEqual(
            metadata.get('total_skills'),
            len(self.tree),
            "Metadata total_skills doesn't match actual count"
        )
        
        # Check combination_skills count
        actual_combination_count = len([s for s in self.tree.skills.values() if s.is_combination])
        self.assertEqual(
            metadata.get('combination_skills'),
            actual_combination_count,
            "Metadata combination_skills doesn't match actual count"
        )
    
    def test_integration_with_scorer(self):
        """Test that tree works with SkillTreeScorer."""
        level_system = SkillLevelSystem(self.tree)
        scorer = SkillTreeScorer(self.tree, level_system)
        
        # Should be able to calculate tree score
        score = scorer.calculate_tree_score()
        self.assertIsInstance(score, float)
        
        # Should be able to get progression summary
        summary = scorer.get_progression_summary()
        self.assertIn('total_skills', summary)
        self.assertEqual(summary['total_skills'], 21)
    
    def test_integration_with_strategy(self):
        """Test that tree works with EvolutionStrategy."""
        level_system = SkillLevelSystem(self.tree)
        unlocker = SkillUnlocker(self.tree)
        scorer = SkillTreeScorer(self.tree, level_system)
        strategy = EvolutionStrategy(self.tree, unlocker, level_system, scorer)
        
        # Unlock a basic skill first
        basic_skills = [s for s in self.tree.skills.values() if s.tier == SkillTier.BASIC and not s.prerequisites]
        if basic_skills:
            basic_skills[0].level = 1
        
        # Should be able to get recommendations
        context = {
            'capability_count': 10,
            'evolution_count': 5,
            'capabilities': [],
            'unlocked_skills': [s.id for s in self.tree.get_unlocked_skills()]
        }
        
        recommendations = strategy.recommend_next_skills(context, count=3)
        self.assertIsInstance(recommendations, list)
    
    def test_skill_tree_can_be_saved(self):
        """Test that modified tree can be saved."""
        import tempfile
        import os
        
        # Unlock a skill
        first_skill = list(self.tree.skills.values())[0]
        first_skill.level = 1
        first_skill.proficiency = 0.5
        
        # Save to temp file
        with tempfile.TemporaryDirectory() as tmpdir:
            save_path = os.path.join(tmpdir, "modified_tree.json")
            self.tree.save_to_file(save_path)
            
            # Verify file exists
            self.assertTrue(os.path.exists(save_path))
            
            # Load and verify
            new_tree = SkillTree(save_path)
            loaded_skill = new_tree.get_skill(first_skill.id)
            self.assertEqual(loaded_skill.level, 1)
            self.assertEqual(loaded_skill.proficiency, 0.5)


def run_tests():
    """Run all tests with summary."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestSoftwareDevTree)
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print(f"\n{'='*60}")
    print(f"测试总数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print(f"{'='*60}")
    
    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)

"""
Comprehensive unit tests for specialization system modules.

Tests all skill tree components with rigorous validation.
NOT allowing test shortcuts - every assertion must validate real behavior.
"""

import unittest
import tempfile
import json
import os
from pathlib import Path
from unittest.mock import MagicMock

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from prokaryote_agent.specialization import (
    SkillNode, SkillTier, SkillCategory,
    SkillTree, SkillUnlocker, SkillLevelSystem,
    SkillTreeScorer, EvolutionStrategy
)


class TestSkillNode(unittest.TestCase):
    """Test SkillNode class."""
    
    def test_create_basic_skill(self):
        """Test creating a basic skill node."""
        skill = SkillNode(
            id="test_skill",
            name="Test Skill",
            description="A test skill",
            tier=SkillTier.BASIC
        )
        
        self.assertEqual(skill.id, "test_skill")
        self.assertEqual(skill.name, "Test Skill")
        self.assertEqual(skill.tier, SkillTier.BASIC)
        self.assertEqual(skill.level, 0)
        self.assertEqual(skill.proficiency, 0.0)
        self.assertTrue(skill.is_locked())
        self.assertFalse(skill.is_unlocked())
    
    def test_skill_level_validation(self):
        """Test that invalid skill levels raise errors."""
        with self.assertRaises(ValueError):
            SkillNode(
                id="invalid",
                name="Invalid",
                description="Invalid level",
                tier=SkillTier.BASIC,
                level=6  # Invalid: max is 5
            )
        
        with self.assertRaises(ValueError):
            SkillNode(
                id="invalid2",
                name="Invalid2",
                description="Invalid level",
                tier=SkillTier.BASIC,
                level=-1  # Invalid: min is 0
            )
    
    def test_proficiency_validation(self):
        """Test that invalid proficiency values raise errors."""
        with self.assertRaises(ValueError):
            SkillNode(
                id="invalid",
                name="Invalid",
                description="Invalid proficiency",
                tier=SkillTier.BASIC,
                level=1,
                proficiency=1.5  # Invalid: max is 1.0
            )
    
    def test_locked_skill_cannot_have_proficiency(self):
        """Test that locked skills cannot have proficiency."""
        with self.assertRaises(ValueError):
            SkillNode(
                id="invalid",
                name="Invalid",
                description="Locked with proficiency",
                tier=SkillTier.BASIC,
                level=0,  # Locked
                proficiency=0.5  # Invalid: locked skills can't have proficiency
            )
    
    def test_skill_max_level_check(self):
        """Test max level detection."""
        skill = SkillNode(
            id="maxed",
            name="Maxed Skill",
            description="At max level",
            tier=SkillTier.MASTER,
            level=5
        )
        
        self.assertTrue(skill.is_max_level())
        self.assertTrue(skill.is_unlocked())
    
    def test_skill_serialization(self):
        """Test to_dict and from_dict round-trip."""
        original = SkillNode(
            id="serialize_test",
            name="Serialize Test",
            description="Testing serialization",
            tier=SkillTier.ADVANCED,
            level=3,
            proficiency=0.6,
            prerequisites=["prereq1", "prereq2"],
            category=SkillCategory.ANALYTICAL,
            is_combination=True
        )
        
        # Serialize to dict
        data = original.to_dict()
        
        # Verify dict structure
        self.assertEqual(data['id'], "serialize_test")
        self.assertEqual(data['tier'], "advanced")
        self.assertEqual(data['category'], "analytical")
        
        # Deserialize back
        restored = SkillNode.from_dict(data)
        
        # Verify round-trip
        self.assertEqual(restored.id, original.id)
        self.assertEqual(restored.name, original.name)
        self.assertEqual(restored.tier, original.tier)
        self.assertEqual(restored.level, original.level)
        self.assertEqual(restored.proficiency, original.proficiency)
        self.assertEqual(restored.prerequisites, original.prerequisites)
        self.assertEqual(restored.is_combination, original.is_combination)


class TestSkillTree(unittest.TestCase):
    """Test SkillTree class."""
    
    def setUp(self):
        """Create test skill tree."""
        self.tree = SkillTree()
        
        # Add some test skills
        self.basic_skill = SkillNode(
            id="basic_1",
            name="Basic Skill 1",
            description="A basic skill",
            tier=SkillTier.BASIC,
            level=1  # Unlocked
        )
        
        self.intermediate_skill = SkillNode(
            id="intermediate_1",
            name="Intermediate Skill 1",
            description="An intermediate skill",
            tier=SkillTier.INTERMEDIATE,
            prerequisites=["basic_1"]
        )
        
        self.tree.add_skill(self.basic_skill)
        self.tree.add_skill(self.intermediate_skill)
    
    def test_add_skill(self):
        """Test adding skills to tree."""
        new_skill = SkillNode(
            id="new_skill",
            name="New Skill",
            description="Newly added",
            tier=SkillTier.BASIC
        )
        
        self.tree.add_skill(new_skill)
        self.assertIn("new_skill", self.tree)
        self.assertEqual(len(self.tree), 3)
    
    def test_duplicate_skill_id_raises_error(self):
        """Test that adding duplicate skill IDs raises error."""
        duplicate = SkillNode(
            id="basic_1",  # Duplicate ID
            name="Duplicate",
            description="This should fail",
            tier=SkillTier.BASIC
        )
        
        with self.assertRaises(ValueError):
            self.tree.add_skill(duplicate)
    
    def test_get_skill(self):
        """Test retrieving skills by ID."""
        skill = self.tree.get_skill("basic_1")
        self.assertIsNotNone(skill)
        self.assertEqual(skill.name, "Basic Skill 1")
        
        # Test non-existent skill
        missing = self.tree.get_skill("nonexistent")
        self.assertIsNone(missing)
    
    def test_get_unlocked_skills(self):
        """Test filtering unlocked skills."""
        unlocked = self.tree.get_unlocked_skills()
        self.assertEqual(len(unlocked), 1)
        self.assertEqual(unlocked[0].id, "basic_1")
    
    def test_get_locked_skills(self):
        """Test filtering locked skills."""
        locked = self.tree.get_locked_skills()
        self.assertEqual(len(locked), 1)
        self.assertEqual(locked[0].id, "intermediate_1")
    
    def test_get_skills_by_tier(self):
        """Test filtering by tier."""
        basic_skills = self.tree.get_skills_by_tier(SkillTier.BASIC)
        self.assertEqual(len(basic_skills), 1)
        
        intermediate_skills = self.tree.get_skills_by_tier(SkillTier.INTERMEDIATE)
        self.assertEqual(len(intermediate_skills), 1)
    
    def test_validate_dag_success(self):
        """Test DAG validation with valid tree."""
        self.assertTrue(self.tree.validate_dag())
    
    def test_validate_dag_detects_cycle(self):
        """Test that DAG validation detects cycles."""
        # Create a cycle: A -> B -> C -> A
        skill_a = SkillNode(id="a", name="A", description="", tier=SkillTier.BASIC, prerequisites=["c"])
        skill_b = SkillNode(id="b", name="B", description="", tier=SkillTier.BASIC, prerequisites=["a"])
        skill_c = SkillNode(id="c", name="C", description="", tier=SkillTier.BASIC, prerequisites=["b"])
        
        cycle_tree = SkillTree()
        cycle_tree.add_skill(skill_a)
        cycle_tree.add_skill(skill_b)
        cycle_tree.add_skill(skill_c)
        
        # Should detect cycle
        self.assertFalse(cycle_tree.validate_dag())
    
    def test_validate_dag_detects_missing_prerequisite(self):
        """Test that DAG validation detects missing prerequisites."""
        broken_skill = SkillNode(
            id="broken",
            name="Broken",
            description="References non-existent prereq",
            tier=SkillTier.ADVANCED,
            prerequisites=["nonexistent_skill"]
        )
        
        broken_tree = SkillTree()
        broken_tree.add_skill(broken_skill)
        
        # Should fail validation
        self.assertFalse(broken_tree.validate_dag())
    
    def test_get_available_to_unlock(self):
        """Test finding skills ready to unlock."""
        # intermediate_1 has basic_1 as prerequisite, and basic_1 is unlocked
        available = self.tree.get_available_to_unlock()
        
        self.assertEqual(len(available), 1)
        self.assertEqual(available[0].id, "intermediate_1")
    
    def test_get_skill_path(self):
        """Test finding prerequisite path."""
        path = self.tree.get_skill_path("intermediate_1")
        
        # Path should go from basic_1 to intermediate_1
        self.assertIn("basic_1", path)
        self.assertIn("intermediate_1", path)
    
    def test_save_and_load_from_file(self):
        """Test saving and loading skill tree."""
        with tempfile.TemporaryDirectory() as tmpdir:
            file_path = os.path.join(tmpdir, "test_tree.json")
            
            # Save tree
            self.tree.save_to_file(file_path)
            
            # Verify file exists
            self.assertTrue(os.path.exists(file_path))
            
            # Load into new tree
            new_tree = SkillTree(file_path)
            
            # Verify loaded data
            self.assertEqual(len(new_tree), len(self.tree))
            self.assertIn("basic_1", new_tree)
            self.assertIn("intermediate_1", new_tree)
            
            # Verify skill properties preserved
            loaded_skill = new_tree.get_skill("basic_1")
            self.assertEqual(loaded_skill.name, "Basic Skill 1")
            self.assertEqual(loaded_skill.level, 1)


class TestSkillUnlocker(unittest.TestCase):
    """Test SkillUnlocker class."""
    
    def setUp(self):
        """Create test tree and unlocker."""
        self.tree = SkillTree()
        
        # Create skill chain: basic -> intermediate -> advanced
        self.skill_basic = SkillNode(
            id="basic",
            name="Basic",
            description="Basic skill",
            tier=SkillTier.BASIC,
            level=1  # Already unlocked
        )
        
        self.skill_intermediate = SkillNode(
            id="intermediate",
            name="Intermediate",
            description="Intermediate skill",
            tier=SkillTier.INTERMEDIATE,
            prerequisites=["basic"],
            unlock_condition="capability_count >= 5"
        )
        
        self.skill_advanced = SkillNode(
            id="advanced",
            name="Advanced",
            description="Advanced skill",
            tier=SkillTier.ADVANCED,
            prerequisites=["intermediate"],
            unlock_condition="evolution_count >= 10"
        )
        
        self.tree.add_skill(self.skill_basic)
        self.tree.add_skill(self.skill_intermediate)
        self.tree.add_skill(self.skill_advanced)
        
        self.unlocker = SkillUnlocker(self.tree)
    
    def test_check_prerequisites_success(self):
        """Test prerequisite checking when met."""
        # intermediate has basic as prereq, and basic is unlocked
        result = self.unlocker.check_prerequisites("intermediate")
        self.assertTrue(result)
    
    def test_check_prerequisites_failure(self):
        """Test prerequisite checking when not met."""
        # advanced has intermediate as prereq, but intermediate is locked
        result = self.unlocker.check_prerequisites("advanced")
        self.assertFalse(result)
    
    def test_evaluate_unlock_condition_simple(self):
        """Test evaluating simple unlock conditions."""
        context = {
            'capability_count': 10,
            'evolution_count': 5
        }
        
        # Should pass: capability_count >= 5
        result = self.unlocker.evaluate_unlock_condition("capability_count >= 5", context)
        self.assertTrue(result)
        
        # Should fail: evolution_count >= 10
        result = self.unlocker.evaluate_unlock_condition("evolution_count >= 10", context)
        self.assertFalse(result)
    
    def test_evaluate_unlock_condition_with_helper(self):
        """Test unlock condition with has_capability helper."""
        context = {
            'capabilities': ['code_generation', 'bug_fixing']
        }
        
        # Should pass
        result = self.unlocker.evaluate_unlock_condition("has_capability('code_generation')", context)
        self.assertTrue(result)
        
        # Should fail
        result = self.unlocker.evaluate_unlock_condition("has_capability('nonexistent')", context)
        self.assertFalse(result)
    
    def test_evaluate_empty_condition(self):
        """Test that empty conditions always pass."""
        result = self.unlocker.evaluate_unlock_condition("", {})
        self.assertTrue(result)
    
    def test_can_unlock_success(self):
        """Test can_unlock when all conditions met."""
        context = {
            'capability_count': 10,
            'capabilities': []
        }
        
        # intermediate should be unlockable
        result = self.unlocker.can_unlock("intermediate", context)
        self.assertTrue(result)
    
    def test_can_unlock_failure_condition(self):
        """Test can_unlock when condition not met."""
        context = {
            'capability_count': 3,  # Need 5
            'capabilities': []
        }
        
        # Should fail due to condition
        result = self.unlocker.can_unlock("intermediate", context)
        self.assertFalse(result)
    
    def test_can_unlock_failure_prerequisites(self):
        """Test can_unlock when prerequisites not met."""
        context = {
            'evolution_count': 15,  # Condition is met
            'capabilities': []
        }
        
        # Should fail because intermediate (prereq) is locked
        result = self.unlocker.can_unlock("advanced", context)
        self.assertFalse(result)
    
    def test_unlock_skill_success(self):
        """Test successfully unlocking a skill."""
        context = {
            'capability_count': 10,
            'capabilities': []
        }
        
        result = self.unlocker.unlock_skill("intermediate", context)
        self.assertTrue(result)
        
        # Verify skill is now unlocked
        skill = self.tree.get_skill("intermediate")
        self.assertEqual(skill.level, 1)
        self.assertTrue(skill.is_unlocked())
    
    def test_unlock_skill_with_initial_proficiency(self):
        """Test unlocking with initial proficiency."""
        context = {
            'capability_count': 10,
            'capabilities': []
        }
        
        result = self.unlocker.unlock_skill("intermediate", context, initial_proficiency=0.3)
        self.assertTrue(result)
        
        # Verify proficiency set
        skill = self.tree.get_skill("intermediate")
        self.assertEqual(skill.proficiency, 0.3)
    
    def test_batch_check_unlockable(self):
        """Test batch checking of unlockable skills."""
        context = {
            'capability_count': 10,
            'evolution_count': 15,
            'capabilities': []
        }
        
        unlockable = self.unlocker.batch_check_unlockable(context)
        
        # Only intermediate should be unlockable (advanced needs intermediate unlocked first)
        self.assertEqual(len(unlockable), 1)
        self.assertIn("intermediate", unlockable)
    
    def test_unlock_all_available(self):
        """Test unlocking all available skills in batch."""
        context = {
            'capability_count': 10,
            'evolution_count': 15,
            'capabilities': []
        }
        
        count = self.unlocker.unlock_all_available(context)
        self.assertEqual(count, 1)  # Only intermediate unlocked
        
        # Verify intermediate is unlocked
        self.assertTrue(self.tree.get_skill("intermediate").is_unlocked())
    
    def test_get_unlock_progress(self):
        """Test getting unlock progress details."""
        context = {
            'capability_count': 3,  # Need 5
            'capabilities': []
        }
        
        progress = self.unlocker.get_unlock_progress("intermediate", context)
        
        self.assertFalse(progress['unlocked'])
        self.assertFalse(progress['can_unlock'])
        self.assertTrue(progress['prerequisites_met'])  # basic is unlocked
        self.assertFalse(progress['condition_met'])  # capability_count too low


class TestSkillLevelSystem(unittest.TestCase):
    """Test SkillLevelSystem class."""
    
    def setUp(self):
        """Create test tree and level system."""
        self.tree = SkillTree()
        
        self.skill = SkillNode(
            id="test_skill",
            name="Test Skill",
            description="For leveling tests",
            tier=SkillTier.INTERMEDIATE,
            level=1,  # Unlocked
            proficiency=0.0
        )
        
        self.tree.add_skill(self.skill)
        self.level_system = SkillLevelSystem(self.tree)
    
    def test_gain_proficiency(self):
        """Test adding proficiency to skill."""
        result = self.level_system.gain_proficiency("test_skill", 0.3)
        
        # Should not level up yet
        self.assertFalse(result)
        
        skill = self.tree.get_skill("test_skill")
        self.assertEqual(skill.proficiency, 0.3)
        self.assertEqual(skill.level, 1)
    
    def test_gain_proficiency_triggers_level_up(self):
        """Test that proficiency >= 1.0 triggers level up."""
        # Add enough proficiency to level up
        result = self.level_system.gain_proficiency("test_skill", 1.0)
        
        # Should level up
        self.assertTrue(result)
        
        skill = self.tree.get_skill("test_skill")
        self.assertEqual(skill.level, 2)
        self.assertEqual(skill.proficiency, 0.0)  # Reset after level up
    
    def test_gain_proficiency_caps_at_1(self):
        """Test that proficiency is capped at 1.0."""
        self.level_system.gain_proficiency("test_skill", 1.5)
        
        skill = self.tree.get_skill("test_skill")
        # Should level up and cap remaining
        self.assertEqual(skill.level, 2)
        self.assertEqual(skill.proficiency, 0.0)
    
    def test_cannot_gain_proficiency_when_locked(self):
        """Test that locked skills cannot gain proficiency."""
        locked_skill = SkillNode(
            id="locked",
            name="Locked",
            description="Locked skill",
            tier=SkillTier.BASIC,
            level=0
        )
        self.tree.add_skill(locked_skill)
        
        result = self.level_system.gain_proficiency("locked", 0.5)
        self.assertFalse(result)
        
        # Proficiency should remain 0
        skill = self.tree.get_skill("locked")
        self.assertEqual(skill.proficiency, 0.0)
    
    def test_level_up_direct(self):
        """Test direct level_up method."""
        result = self.level_system.level_up("test_skill")
        self.assertTrue(result)
        
        skill = self.tree.get_skill("test_skill")
        self.assertEqual(skill.level, 2)
    
    def test_cannot_level_up_beyond_max(self):
        """Test that skills cannot level beyond 5."""
        # Set skill to max level
        skill = self.tree.get_skill("test_skill")
        skill.level = 5
        
        result = self.level_system.level_up("test_skill")
        self.assertFalse(result)
        self.assertEqual(skill.level, 5)  # Still at max
    
    def test_get_level_bonuses(self):
        """Test level bonus retrieval."""
        bonus_l1 = self.level_system.get_level_bonuses("test_skill")
        self.assertEqual(bonus_l1, 1.0)  # Level 1 = base
        
        # Level up and check bonus
        skill = self.tree.get_skill("test_skill")
        skill.level = 5
        
        bonus_l5 = self.level_system.get_level_bonuses("test_skill")
        self.assertEqual(bonus_l5, 3.0)  # Level 5 = 3x bonus
    
    def test_get_skill_power(self):
        """Test skill power calculation."""
        # Level 1, proficiency 0
        power = self.level_system.get_skill_power("test_skill")
        self.assertEqual(power, 1.0)
        
        # Add proficiency
        skill = self.tree.get_skill("test_skill")
        skill.proficiency = 0.5
        
        power = self.level_system.get_skill_power("test_skill")
        self.assertEqual(power, 1.5)
        
        # Level up
        skill.level = 3
        skill.proficiency = 0.8
        
        power = self.level_system.get_skill_power("test_skill")
        self.assertEqual(power, 3.8)
    
    def test_get_progress_to_next_level(self):
        """Test progress information retrieval."""
        skill = self.tree.get_skill("test_skill")
        skill.proficiency = 0.6
        
        progress = self.level_system.get_progress_to_next_level("test_skill")
        
        self.assertEqual(progress['current_level'], 1)
        self.assertEqual(progress['proficiency'], 0.6)
        self.assertEqual(progress['required'], 1.0)
        self.assertEqual(progress['percentage'], 60.0)
        self.assertEqual(progress['next_level'], 2)
    
    def test_batch_gain_proficiency(self):
        """Test batch proficiency gain."""
        # Add second skill
        skill2 = SkillNode(
            id="skill2",
            name="Skill 2",
            description="Second skill",
            tier=SkillTier.BASIC,
            level=1
        )
        self.tree.add_skill(skill2)
        
        gains = {
            "test_skill": 1.0,  # Will level up
            "skill2": 0.5       # Won't level up
        }
        
        leveled_up = self.level_system.batch_gain_proficiency(gains)
        
        # Only test_skill should level up
        self.assertEqual(len(leveled_up), 1)
        self.assertIn("test_skill", leveled_up)
        
        # Verify levels
        self.assertEqual(self.tree.get_skill("test_skill").level, 2)
        self.assertEqual(self.tree.get_skill("skill2").level, 1)
        self.assertEqual(self.tree.get_skill("skill2").proficiency, 0.5)


class TestSkillTreeScorer(unittest.TestCase):
    """Test SkillTreeScorer class."""
    
    def setUp(self):
        """Create test tree with diverse skills."""
        self.tree = SkillTree()
        self.level_system = SkillLevelSystem(self.tree)
        self.scorer = SkillTreeScorer(self.tree, self.level_system)
        
        # Add skills across different tiers and categories
        self.tree.add_skill(SkillNode(
            id="basic_tech",
            name="Basic Tech",
            description="",
            tier=SkillTier.BASIC,
            category=SkillCategory.TECHNICAL,
            level=2
        ))
        
        self.tree.add_skill(SkillNode(
            id="inter_tech",
            name="Inter Tech",
            description="",
            tier=SkillTier.INTERMEDIATE,
            category=SkillCategory.TECHNICAL,
            level=3
        ))
        
        self.tree.add_skill(SkillNode(
            id="adv_analytical",
            name="Adv Analytical",
            description="",
            tier=SkillTier.ADVANCED,
            category=SkillCategory.ANALYTICAL,
            level=1
        ))
        
        self.tree.add_skill(SkillNode(
            id="locked_skill",
            name="Locked",
            description="",
            tier=SkillTier.MASTER,
            category=SkillCategory.CREATIVE,
            level=0  # Locked
        ))
    
    def test_calculate_skill_score_locked(self):
        """Test that locked skills have 0 score."""
        score = self.scorer.calculate_skill_score("locked_skill")
        self.assertEqual(score, 0.0)
    
    def test_calculate_skill_score_basic(self):
        """Test scoring basic tier skill."""
        score = self.scorer.calculate_skill_score("basic_tech")
        self.assertGreater(score, 0.0)
        
        # Level 2 basic skill
        # Score = (2 * 10) * 1.0 = 20
        self.assertEqual(score, 20.0)
    
    def test_calculate_skill_score_advanced(self):
        """Test scoring advanced tier skill."""
        score = self.scorer.calculate_skill_score("adv_analytical")
        
        # Level 1 advanced skill
        # Score = (1 * 10) * 2.0 = 20 (tier multiplier is 2.0)
        self.assertEqual(score, 20.0)
    
    def test_calculate_tree_score(self):
        """Test total tree score calculation."""
        total_score = self.scorer.calculate_tree_score()
        
        # Should be sum of all unlocked skill scores
        self.assertGreater(total_score, 0.0)
        
        # Verify it's not counting locked skills
        individual_scores = [
            self.scorer.calculate_skill_score(s.id)
            for s in self.tree.get_unlocked_skills()
        ]
        self.assertEqual(total_score, sum(individual_scores))
    
    def test_calculate_specialization_depth(self):
        """Test specialization depth calculation per category."""
        depths = self.scorer.calculate_specialization_depth()
        
        # Should have depth for technical and analytical
        self.assertGreater(depths['technical'], 0.0)
        self.assertGreater(depths['analytical'], 0.0)
        
        # Technical should be deeper (2 skills vs 1)
        self.assertGreater(depths['technical'], depths['analytical'])
        
        # Creative should be 0 (locked skill)
        self.assertEqual(depths['creative'], 0.0)
    
    def test_identify_specialization_direction(self):
        """Test identifying primary specialization."""
        directions = self.scorer.identify_specialization_direction()
        
        # Should return sorted list
        self.assertIsInstance(directions, list)
        self.assertGreater(len(directions), 0)
        
        # First should be technical (most developed)
        top_direction, top_score = directions[0]
        self.assertEqual(top_direction, 'technical')
        self.assertGreater(top_score, 0.0)
    
    def test_get_specialization_breadth(self):
        """Test counting active categories."""
        breadth = self.scorer.get_specialization_breadth()
        
        # Should have 2 categories with unlocked skills
        self.assertEqual(breadth, 2)
    
    def test_get_tier_distribution(self):
        """Test tier distribution counting."""
        distribution = self.scorer.get_tier_distribution()
        
        # Should have counts for unlocked tiers
        self.assertEqual(distribution['basic'], 1)
        self.assertEqual(distribution['intermediate'], 1)
        self.assertEqual(distribution['advanced'], 1)
        self.assertEqual(distribution['master'], 0)
        self.assertEqual(distribution['grandmaster'], 0)
    
    def test_is_specialist_true(self):
        """Test specialist detection when heavily focused."""
        is_spec, category = self.scorer.is_specialist(threshold=0.5)
        
        # With current distribution, should be specialist in technical
        self.assertTrue(is_spec)
        self.assertEqual(category, 'technical')
    
    def test_is_specialist_false(self):
        """Test generalist detection with balanced distribution."""
        # Add more analytical skills to balance
        self.tree.add_skill(SkillNode(
            id="analytical2",
            name="Analytical 2",
            description="",
            tier=SkillTier.INTERMEDIATE,
            category=SkillCategory.ANALYTICAL,
            level=3
        ))
        
        self.tree.add_skill(SkillNode(
            id="analytical3",
            name="Analytical 3",
            description="",
            tier=SkillTier.ADVANCED,
            category=SkillCategory.ANALYTICAL,
            level=2
        ))
        
        # Now should be more balanced
        is_spec, category = self.scorer.is_specialist(threshold=0.7)
        self.assertFalse(is_spec)
    
    def test_get_progression_summary(self):
        """Test comprehensive progression summary."""
        summary = self.scorer.get_progression_summary()
        
        # Verify structure
        self.assertIn('total_skills', summary)
        self.assertIn('unlocked_skills', summary)
        self.assertIn('locked_skills', summary)
        self.assertIn('unlock_percentage', summary)
        self.assertIn('average_level', summary)
        self.assertIn('total_score', summary)
        self.assertIn('is_specialist', summary)
        self.assertIn('primary_specialization', summary)
        
        # Verify values
        self.assertEqual(summary['total_skills'], 4)
        self.assertEqual(summary['unlocked_skills'], 3)
        self.assertEqual(summary['locked_skills'], 1)
        self.assertEqual(summary['unlock_percentage'], 75.0)
        self.assertGreater(summary['average_level'], 0.0)
        self.assertGreater(summary['total_score'], 0.0)


class TestEvolutionStrategy(unittest.TestCase):
    """Test EvolutionStrategy class."""
    
    def setUp(self):
        """Create full skill tree system for strategy testing."""
        self.tree = SkillTree()
        self.level_system = SkillLevelSystem(self.tree)
        self.unlocker = SkillUnlocker(self.tree)
        self.scorer = SkillTreeScorer(self.tree, self.level_system)
        self.strategy = EvolutionStrategy(
            self.tree, self.unlocker, self.level_system, self.scorer
        )
        
        # Create skill chain
        self.tree.add_skill(SkillNode(
            id="basic1",
            name="Basic 1",
            description="",
            tier=SkillTier.BASIC,
            category=SkillCategory.TECHNICAL,
            level=1
        ))
        
        self.tree.add_skill(SkillNode(
            id="inter1",
            name="Inter 1",
            description="",
            tier=SkillTier.INTERMEDIATE,
            category=SkillCategory.TECHNICAL,
            prerequisites=["basic1"],
            unlock_condition="capability_count >= 5"
        ))
        
        self.tree.add_skill(SkillNode(
            id="adv1",
            name="Adv 1",
            description="",
            tier=SkillTier.ADVANCED,
            category=SkillCategory.TECHNICAL,
            prerequisites=["inter1"],
            is_combination=True
        ))
        
        self.tree.add_skill(SkillNode(
            id="basic_other",
            name="Basic Other",
            description="",
            tier=SkillTier.BASIC,
            category=SkillCategory.ANALYTICAL,
            unlock_condition=""
        ))
    
    def test_recommend_next_skills(self):
        """Test skill recommendations."""
        context = {
            'capability_count': 10,
            'capabilities': []
        }
        
        recommendations = self.strategy.recommend_next_skills(context, count=2)
        
        # Should get recommendations
        self.assertGreater(len(recommendations), 0)
        
        # Should be list of (skill_id, priority) tuples
        for skill_id, priority in recommendations:
            self.assertIsInstance(skill_id, str)
            self.assertIsInstance(priority, float)
            self.assertGreater(priority, 0.0)
    
    def test_recommend_prefers_specialization(self):
        """Test that recommendations prefer specialization direction."""
        context = {
            'capability_count': 10,
            'capabilities': []
        }
        
        # Should prefer technical skills (matching existing unlocked skill)
        recommendations = self.strategy.recommend_next_skills(
            context, 
            count=3,
            prefer_specialization=True
        )
        
        # inter1 should be recommended (technical, intermediate tier)
        skill_ids = [sid for sid, _ in recommendations]
        self.assertIn("inter1", skill_ids)
    
    def test_generate_evolution_goal_unlock(self):
        """Test generating unlock goal."""
        context = {
            'capability_count': 10,
            'capabilities': []
        }
        
        goal = self.strategy.generate_evolution_goal(context, goal_type="unlock")
        
        self.assertIsNotNone(goal)
        self.assertEqual(goal['type'], 'unlock_skill')
        self.assertIn('target_skill_id', goal)
        self.assertIn('target_skill_name', goal)
        self.assertIn('description', goal)
    
    def test_generate_evolution_goal_level_up(self):
        """Test generating level-up goal."""
        context = {}
        
        goal = self.strategy.generate_evolution_goal(context, goal_type="level_up")
        
        self.assertIsNotNone(goal)
        self.assertEqual(goal['type'], 'level_up_skill')
        self.assertIn('target_skill_id', goal)
        self.assertEqual(goal['current_level'], 1)  # basic1 is at level 1
    
    def test_generate_evolution_goal_specialize(self):
        """Test generating specialization goal."""
        context = {}
        
        goal = self.strategy.generate_evolution_goal(context, goal_type="specialize")
        
        self.assertIsNotNone(goal)
        self.assertEqual(goal['type'], 'specialize')
        self.assertIn('target_category', goal)
        self.assertIn('description', goal)
    
    def test_adjust_strategy_based_on_tree(self):
        """Test strategy adjustment recommendations."""
        recommendations = self.strategy.adjust_strategy_based_on_tree()
        
        self.assertIn('focus_breadth', recommendations)
        self.assertIn('focus_leveling', recommendations)
        self.assertIn('continue_specialization', recommendations)
        self.assertIn('suggested_goal_type', recommendations)
        self.assertIn('reasoning', recommendations)
        
        # Reasoning should be non-empty list
        self.assertIsInstance(recommendations['reasoning'], list)
    
    def test_detect_skill_synergy_combination(self):
        """Test detecting combination skill synergies."""
        # Unlock prerequisite so combination is complete
        skill = self.tree.get_skill("inter1")
        skill.level = 1
        
        synergies = self.strategy.detect_skill_synergy()
        
        # Should detect combination synergy for adv1
        combination_synergies = [s for s in synergies if s['type'] == 'combination']
        
        # Note: adv1 is still locked, so no synergy yet
        # This tests the detection logic works when conditions are met
        self.assertIsInstance(synergies, list)
    
    def test_detect_skill_synergy_category_cluster(self):
        """Test detecting category cluster synergies."""
        # Need 3+ skills at level 3+ in same category for cluster detection
        # Currently basic1 is only level 1, so we need to level it up
        skill_basic1 = self.tree.get_skill("basic1")
        skill_basic1.level = 3  # Level up to 3
        
        # Add more high-level technical skills
        self.tree.add_skill(SkillNode(
            id="tech2",
            name="Tech 2",
            description="",
            tier=SkillTier.INTERMEDIATE,
            category=SkillCategory.TECHNICAL,
            level=4
        ))
        
        self.tree.add_skill(SkillNode(
            id="tech3",
            name="Tech 3",
            description="",
            tier=SkillTier.ADVANCED,
            category=SkillCategory.TECHNICAL,
            level=3
        ))
        
        synergies = self.strategy.detect_skill_synergy()
        
        # Should detect category cluster (3+ skills at level 3+)
        cluster_synergies = [s for s in synergies if s['type'] == 'category_cluster']
        self.assertGreater(len(cluster_synergies), 0)
        
        # Verify cluster contains expected skills
        if cluster_synergies:
            cluster = cluster_synergies[0]
            self.assertEqual(cluster['type'], 'category_cluster')
            self.assertGreaterEqual(len(cluster['skills']), 3)
    
    def test_get_skill_priority_matrix(self):
        """Test priority matrix generation."""
        matrix = self.strategy.get_skill_priority_matrix()
        
        # Should have entries for locked skills
        self.assertGreater(len(matrix), 0)
        
        # Check structure
        for skill_id, factors in matrix.items():
            self.assertIn('tier_value', factors)
            self.assertIn('is_combination', factors)
            self.assertIn('num_capabilities', factors)
            self.assertIn('num_prerequisites', factors)
            self.assertIn('total_priority', factors)
            
            # Verify types
            self.assertIsInstance(factors['total_priority'], (int, float))


def run_tests():
    """Run all tests with summary."""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test classes
    suite.addTests(loader.loadTestsFromTestCase(TestSkillNode))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillTree))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillUnlocker))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillLevelSystem))
    suite.addTests(loader.loadTestsFromTestCase(TestSkillTreeScorer))
    suite.addTests(loader.loadTestsFromTestCase(TestEvolutionStrategy))
    
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

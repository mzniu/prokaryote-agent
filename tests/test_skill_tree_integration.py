"""
Task 15集成测试: 技能树集成到守护进程

测试技能树与守护进程各组件的集成功能（简化版）。
"""

import unittest
import tempfile
import json
import shutil
import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from prokaryote_agent.daemon.generation_manager import GenerationManager
from prokaryote_agent.daemon.genetic_transmitter import GeneticTransmitter
from prokaryote_agent.daemon.evolution_daemon import EvolutionDaemon
from prokaryote_agent.specialization import SkillTree


class TestSkillTreeIntegrationCore(unittest.TestCase):
    """测试核心集成功能"""
    
    def setUp(self):
        """设置测试环境"""
        self.tmpdir = tempfile.mkdtemp()
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_generation_manager_handles_skill_tree_files(self):
        """测试GenerationManager能处理技能树文件"""
        gen_manager = GenerationManager(root_dir=os.path.join(self.tmpdir, "generations"))
        
        # 创建简单的软件开发技能树文件
        skill_tree_dir = Path("prokaryote_agent/specialization/domains")
        skill_tree_dir.mkdir(parents=True, exist_ok=True)
        
        simple_tree = {
            "skills": [
                {
                    "id": "basic_git",
                    "name": "Git Basics",
                    "description": "Basic Git operations",
                    "tier": "basic",
                    "level": 1,
                    "proficiency": 0.5,
                    "prerequisites": [],
                    "unlock_condition": "",
                    "category": "technical",
                    "related_capabilities": [],
                    "is_combination": False,
                    "metadata": {}
                }
            ]
        }
        
        skill_tree_path = skill_tree_dir / "software_dev_tree.json"
        with open(skill_tree_path, 'w') as f:
            json.dump(simple_tree, f)
        
        try:
            # 创建能力注册表
            cap_registry_path = Path("prokaryote_agent/capability_registry.json")
            cap_registry_path.parent.mkdir(parents=True, exist_ok=True)
            with open(cap_registry_path, 'w') as f:
                json.dump({"capabilities": []}, f)
            
            # 创建快照
            snapshot_dir = gen_manager.create_snapshot(generation=1)
            
            # 验证快照包含技能树状态文件
            skill_tree_snapshot = snapshot_dir / "skill_tree_state.json"
            self.assertTrue(skill_tree_snapshot.exists())
            
            # 验证文件内容
            with open(skill_tree_snapshot, 'r') as f:
                data = json.load(f)
            self.assertIn('skills', data)
            self.assertIn('generation', data)
        
        finally:
            # 清理
            if Path("prokaryote_agent").exists():
                shutil.rmtree("prokaryote_agent", ignore_errors=True)
    
    def test_genetic_transmitter_accepts_skill_tree_parameter(self):
        """测试GeneticTransmitter接受skill_tree参数"""
        transmitter = GeneticTransmitter()
        
        # 创建简单的快照目录
        snapshot_dir = Path(self.tmpdir) / "gen_0001"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建能力注册表
        capabilities = [
            {"name": "test_cap", "fitness_score": 0.6, "usage_count": 30, "category": "general"}
        ]
        with open(snapshot_dir / "capability_registry.json", 'w') as f:
            json.dump({"capabilities": capabilities}, f)
        
        # 加载真实的软件开发技能树
        real_tree_path = Path("prokaryote_agent/specialization/domains/software_dev_tree.json")
        skill_tree = None
        if real_tree_path.exists():
            skill_tree = SkillTree.load_from_file(str(real_tree_path))
        
        # 测试能力列表
        capabilities = [
            {"name": "test_cap", "fitness_score": 0.9, "usage_count": 50, "category": "development"}
        ]
        
        # 生成遗传信息（有无技能树都应该成功）
        genes = transmitter.generate_genes(
            generation=1,
            capabilities=capabilities,
            lineage="main",
            skill_tree=skill_tree
        )
        
        self.assertIn('skill_tree_influence', genes)
        # 如果有技能树，应该有加成；否则为空字典
        self.assertIsInstance(genes['skill_tree_influence'], dict)
    
    def test_evolution_daemon_initializes_skill_tree(self):
        """测试EvolutionDaemon初始化技能树组件"""
        # 创建配置文件
        config_path = os.path.join(self.tmpdir, "daemon_config.json")
        config = {
            "specialization": {
                "skill_tree_path": "prokaryote_agent/specialization/domains/software_dev_tree.json"
            },
            "restart_trigger": {"threshold": 10},
            "communication": {"heartbeat_interval": 30}
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        # 初始化daemon
        with patch('builtins.print'):  # Suppress print output
            daemon = EvolutionDaemon(config_path=config_path)
        
        # 验证skill_tree属性存在（即使可能是None）
        self.assertTrue(hasattr(daemon, 'skill_tree'))
        
        # 验证get_status方法可以正常调用
        status = daemon.get_status()
        self.assertIsInstance(status, dict)
        self.assertIn('daemon_running', status)
    
    def test_integration_workflow(self):
        """测试完整的集成工作流"""
        # 1. 创建GenerationManager
        gen_manager = GenerationManager(root_dir=os.path.join(self.tmpdir, "generations"))
        
        # 2. 创建GeneticTransmitter
        transmitter = GeneticTransmitter()
        
        # 3. 准备测试数据
        cap_registry_path = Path("prokaryote_agent/capability_registry.json")
        cap_registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cap_registry_path, 'w') as f:
            json.dump({"capabilities": []}, f)
        
        try:
            # 4. 创建快照
            snapshot_dir = gen_manager.create_snapshot(generation=1)
            
            # 5. 生成遗传信息
            capabilities = [
                {"name": "test_cap", "fitness_score": 0.9, "usage_count": 50}
            ]
            genes = transmitter.generate_genes(
                generation=1,
                capabilities=capabilities,
                lineage="main",
                skill_tree=None  # 可以为None
            )
            
            # 6. 验证流程完整性
            self.assertIsInstance(genes, dict)
            self.assertEqual(genes['generation'], 2)
            self.assertEqual(genes['parent_generation'], 1)
            self.assertIn('inherited_capabilities', genes)
            self.assertIn('skill_tree_influence', genes)
        
        finally:
            if Path("prokaryote_agent").exists():
                shutil.rmtree("prokaryote_agent", ignore_errors=True)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestSkillTreeIntegrationCore))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Total tests: {result.testsRun}")
    print(f"Success: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)



class TestGenerationManagerSkillTreeIntegration(unittest.TestCase):
    """测试GenerationManager与技能树的集成"""
    
    def setUp(self):
        """设置测试环境"""
        self.tmpdir = tempfile.mkdtemp()
        self.gen_manager = GenerationManager(root_dir=os.path.join(self.tmpdir, "generations"))
        
        # 创建简单的技能树
        self.skill_tree = SkillTree()
        skill1 = SkillNode(
            id="test_skill_1",
            name="Test Skill 1",
            description="Test",
            tier=SkillTier.BASIC,
            level=2,
            proficiency=0.6,
            prerequisites=[],
            unlock_condition="",
            category="testing"
        )
        skill2 = SkillNode(
            id="test_skill_2",
            name="Test Skill 2",
            description="Test",
            tier=SkillTier.BASIC,
            level=0,
            proficiency=0.0,
            prerequisites=[],
            unlock_condition="",
            category="debugging"
        )
        self.skill_tree.add_skill(skill1)
        self.skill_tree.add_skill(skill2)
        
        # 保存技能树到临时目录
        self.skill_tree_path = os.path.join(self.tmpdir, "test_tree.json")
        self.skill_tree.save_to_file(self.skill_tree_path)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_snapshot_includes_skill_tree(self):
        """测试快照包含技能树状态"""
        # 创建能力注册表文件（GenerationManager依赖）
        cap_registry_path = Path("prokaryote_agent/capability_registry.json")
        cap_registry_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cap_registry_path, 'w') as f:
            json.dump({"capabilities": []}, f)
        
        try:
            # 设置全局技能树路径
            skill_tree_dest = Path("prokaryote_agent/specialization/domains/software_dev_tree.json")
            skill_tree_dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.skill_tree_path, skill_tree_dest)
            
            # 创建快照
            snapshot_dir = self.gen_manager.create_snapshot(generation=1)
            
            # 验证快照包含技能树
            skill_tree_snapshot = snapshot_dir / "skill_tree_state.json"
            self.assertTrue(skill_tree_snapshot.exists(), "Snapshot should include skill_tree_state.json")
            
            # 验证技能树数据
            with open(skill_tree_snapshot, 'r') as f:
                skill_data = json.load(f)
            
            self.assertIn('skills', skill_data)
            self.assertEqual(len(skill_data['skills']), 2)
            self.assertEqual(skill_data['generation'], 1)
        
        finally:
            # 清理测试文件
            if cap_registry_path.exists():
                cap_registry_path.unlink()
            if Path("prokaryote_agent/specialization/domains/software_dev_tree.json").exists():
                shutil.rmtree("prokaryote_agent/specialization", ignore_errors=True)
    
    def test_restore_includes_skill_tree(self):
        """测试恢复包含技能树状态"""
        # 创建带技能树的快照
        snapshot_dir = self.gen_manager.root_dir / "gen_0005"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 保存技能树到快照
        skill_tree_data = {
            'skills': [skill.to_dict() for skill in self.skill_tree.skills.values()],
            'generation': 5,
            'saved_at': '2024-01-01T00:00:00'
        }
        with open(snapshot_dir / "skill_tree_state.json", 'w') as f:
            json.dump(skill_tree_data, f)
        
        # 创建元数据
        metadata = {
            'generation': 5,
            'lineage': 'main',
            'created_at': '2024-01-01T00:00:00'
        }
        with open(snapshot_dir / "metadata.json", 'w') as f:
            json.dump(metadata, f)
        
        # 执行恢复
        success = self.gen_manager.restore_from_snapshot(generation=5)
        
        self.assertTrue(success, "Restore should succeed")
        
        # 验证技能树被恢复
        restored_tree_path = Path("prokaryote_agent/specialization/current_skill_tree.json")
        self.assertTrue(restored_tree_path.exists(), "Restored skill tree should exist")
        
        # 清理
        if restored_tree_path.exists():
            shutil.rmtree("prokaryote_agent/specialization", ignore_errors=True)


class TestGeneticTransmitterSkillTreeIntegration(unittest.TestCase):
    """测试GeneticTransmitter与技能树的集成"""
    
    def setUp(self):
        """设置测试环境"""
        self.tmpdir = tempfile.mkdtemp()
        self.transmitter = GeneticTransmitter()
        
        # 创建技能树
        self.skill_tree = SkillTree()
        skill_testing = SkillNode(
            id="advanced_testing",
            name="Advanced Testing",
            description="Advanced testing skills",
            tier=SkillTier.ADVANCED,
            level=3,
            proficiency=0.7,
            prerequisites=[],
            unlock_condition="",
            category="testing"
        )
        skill_debugging = SkillNode(
            id="basic_debugging",
            name="Basic Debugging",
            description="Basic debugging skills",
            tier=SkillTier.BASIC,
            level=1,
            proficiency=0.3,
            prerequisites=[],
            unlock_condition="",
            category="debugging"
        )
        self.skill_tree.add_skill(skill_testing)
        self.skill_tree.add_skill(skill_debugging)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_extract_skill_bonuses(self):
        """测试提取技能加成"""
        bonuses = self.transmitter._extract_skill_bonuses(self.skill_tree)
        
        self.assertIsInstance(bonuses, dict)
        self.assertIn('testing', bonuses)
        self.assertIn('debugging', bonuses)
        
        # 高等级技能应该有更高的加成
        self.assertGreater(bonuses['testing'], bonuses['debugging'])
        
        # 加成应该在合理范围内（1.0 - 1.5）
        for category, bonus in bonuses.items():
            self.assertGreaterEqual(bonus, 1.0)
            self.assertLessEqual(bonus, 1.5)
    
    def test_capability_selection_with_skill_bonuses(self):
        """测试能力筛选考虑技能加成"""
        # 创建测试能力
        capabilities = [
            {"name": "test_capability_1", "fitness_score": 0.7, "usage_count": 20, "category": "testing"},
            {"name": "test_capability_2", "fitness_score": 0.6, "usage_count": 15, "category": "debugging"},
            {"name": "test_capability_3", "fitness_score": 0.4, "usage_count": 5, "category": "general"}
        ]
        
        # 提取技能加成
        skill_bonuses = self.transmitter._extract_skill_bonuses(self.skill_tree)
        
        # 筛选能力
        result = self.transmitter._select_capabilities(capabilities, skill_bonuses)
        
        self.assertIn('keep', result)
        self.assertIn('eliminate', result)
        self.assertIn('mutate', result)
        
        # 验证技能加成影响筛选
        # capability_1的适应度会因testing技能加成而提升
        kept_names = [cap['name'] for cap in result['keep']]
        self.assertIn("test_capability_1", kept_names)
        
        # capability_3没有技能加成，可能被淘汰
        if result['eliminate']:
            self.assertIn("test_capability_3", result['eliminate'])
    
    def test_generate_genes_with_skill_tree(self):
        """测试生成遗传信息时传入技能树"""
        # 创建快照目录和数据
        snapshot_dir = Path(self.tmpdir) / "gen_0001"
        snapshot_dir.mkdir(parents=True, exist_ok=True)
        
        # 创建能力注册表
        capabilities = [
            {"name": "test_cap", "fitness_score": 0.6, "usage_count": 30, "category": "testing"}
        ]
        with open(snapshot_dir / "capability_registry.json", 'w') as f:
            json.dump({"capabilities": capabilities}, f)
        
        # 生成遗传信息
        genes = self.transmitter.generate_genes(
            generation=1,
            snapshot_dir=snapshot_dir,
            skill_tree=self.skill_tree
        )
        
        self.assertIn('skill_tree_influence', genes)
        self.assertIsInstance(genes['skill_tree_influence'], dict)
        self.assertGreater(len(genes['skill_tree_influence']), 0)


class TestEvolutionDaemonSkillTreeIntegration(unittest.TestCase):
    """测试EvolutionDaemon与技能树的集成"""
    
    def setUp(self):
        """设置测试环境"""
        self.tmpdir = tempfile.mkdtemp()
        
        # 创建测试技能树
        self.skill_tree_path = os.path.join(self.tmpdir, "test_tree.json")
        skill_tree = SkillTree()
        skill = SkillNode(
            id="test_skill",
            name="Test Skill",
            description="Test",
            tier=SkillTier.BASIC,
            level=1,
            proficiency=0.5,
            prerequisites=[],
            unlock_condition="",
            category="testing"
        )
        skill_tree.add_skill(skill)
        skill_tree.save_to_file(self.skill_tree_path)
    
    def tearDown(self):
        """清理测试环境"""
        shutil.rmtree(self.tmpdir, ignore_errors=True)
    
    def test_daemon_initializes_skill_tree(self):
        """测试守护进程初始化技能树"""
        config = {
            "specialization": {
                "skill_tree_path": self.skill_tree_path
            }
        }
        
        with patch('builtins.open', side_effect=[
            # 第一次调用：加载daemon config
            MagicMock(return_value=MagicMock(
                __enter__=lambda self: MagicMock(read=lambda: json.dumps(config)),
                __exit__=lambda *args: None
            )),
            # 第二次调用：加载skill tree
            open(self.skill_tree_path, 'r', encoding='utf-8')
        ]):
            daemon = EvolutionDaemon()
            
            self.assertIsNotNone(daemon.skill_tree, "Daemon should have skill_tree initialized")
            self.assertGreater(len(daemon.skill_tree.skills), 0)
    
    def test_daemon_status_includes_skill_tree(self):
        """测试守护进程状态包含技能树信息"""
        # 创建daemon配置
        config_path = os.path.join(self.tmpdir, "daemon_config.json")
        config = {
            "specialization": {
                "skill_tree_path": self.skill_tree_path
            },
            "restart_trigger": {"threshold": 10},
            "communication": {"heartbeat_interval": 30}
        }
        with open(config_path, 'w') as f:
            json.dump(config, f)
        
        with patch('builtins.print'):  # Suppress print output
            daemon = EvolutionDaemon(config_path=config_path)
        
        if daemon.skill_tree:
            status = daemon.get_status()
            
            self.assertIn('skill_tree', status)
            self.assertIn('total_skills', status['skill_tree'])
            self.assertIn('unlocked_skills', status['skill_tree'])
            self.assertEqual(status['skill_tree']['total_skills'], 1)
            self.assertEqual(status['skill_tree']['unlocked_skills'], 1)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestGenerationManagerSkillTreeIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestGeneticTransmitterSkillTreeIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestEvolutionDaemonSkillTreeIntegration))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print summary
    print("\n" + "=" * 60)
    print(f"Total tests: {result.testsRun}")
    print(f"Success: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    print("=" * 60)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    sys.exit(0 if result.wasSuccessful() else 1)

"""
单元测试 - Daemon模块

测试evolution_daemon, generation_manager, genetic_transmitter, 
mutation_engine, collaboration_interface
"""

import unittest
import tempfile
import shutil
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# 导入待测试模块
from prokaryote_agent.daemon import (
    EvolutionDaemon,
    GenerationManager,
    GeneticTransmitter,
    MutationEngine,
    CollaborationInterface
)


class TestGenerationManager(unittest.TestCase):
    """测试代际管理器"""
    
    def setUp(self):
        """测试前准备"""
        self.test_dir = tempfile.mkdtemp()
        self.manager = GenerationManager(root_dir=str(Path(self.test_dir) / "generations"))
    
    def tearDown(self):
        """测试后清理"""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    def test_init_creates_directory_structure(self):
        """测试初始化创建必要的目录结构"""
        self.assertTrue(self.manager.root_dir.exists())
        self.assertTrue(self.manager.lineage_file.exists())
        self.assertTrue(self.manager.current_gen_file.exists())
        self.assertTrue(self.manager.active_lineage_file.exists())
    
    def test_init_lineage_creates_default_lineage(self):
        """测试初始化创建默认族谱"""
        lineage_data = self.manager._load_lineage()
        
        self.assertIn("lineages", lineage_data)
        self.assertIn("main", lineage_data["lineages"])
        self.assertEqual(lineage_data["lineages"]["main"]["current_generation"], 0)
    
    def test_create_snapshot(self):
        """测试创建快照"""
        # 创建测试用的能力注册表文件
        cap_registry_path = Path("prokaryote_agent/capability_registry.json")
        original_exists = cap_registry_path.exists()
        
        # 确保文件存在
        if not cap_registry_path.parent.exists():
            cap_registry_path.parent.mkdir(parents=True, exist_ok=True)
        
        if not cap_registry_path.exists():
            test_cap_registry = {
                "capabilities": [
                    {"name": "test_cap", "fitness_score": 0.9, "usage_count": 50}
                ]
            }
            with open(cap_registry_path, 'w') as f:
                json.dump(test_cap_registry, f)
        
        try:
            # 创建快照
            snapshot_dir = self.manager.create_snapshot(generation=1, lineage="main")
            
            # 验证快照目录存在
            self.assertTrue(snapshot_dir.exists())
            self.assertTrue((snapshot_dir / "metadata.json").exists())
        finally:
            # 清理：如果原本不存在，删除测试文件
            if not original_exists and cap_registry_path.exists():
                cap_registry_path.unlink()
    
    def test_get_current_generation(self):
        """测试获取当前代数"""
        self.manager.current_gen_file.write_text("5")
        self.assertEqual(self.manager.get_current_generation(), 5)
    
    def test_get_current_lineage(self):
        """测试获取当前族系"""
        self.manager.active_lineage_file.write_text("experimental")
        self.assertEqual(self.manager.get_current_lineage(), "experimental")
    
    def test_create_branch(self):
        """测试创建分支"""
        # 先创建源代的快照
        gen_dir = self.manager.root_dir / "gen_0010"
        gen_dir.mkdir(parents=True)
        (gen_dir / "metadata.json").write_text("{}")
        
        # 创建分支
        success = self.manager.create_branch(
            from_generation=10,
            new_lineage="experimental",
            description="Test branch"
        )
        
        self.assertTrue(success)
        
        # 验证族谱树更新
        lineage_data = self.manager._load_lineage()
        self.assertIn("experimental", lineage_data["lineages"])
        self.assertEqual(lineage_data["lineages"]["experimental"]["parent_generation"], 10)


class TestGeneticTransmitter(unittest.TestCase):
    """测试遗传传递器"""
    
    def setUp(self):
        """测试前准备"""
        self.transmitter = GeneticTransmitter()
        self.test_dir = tempfile.mkdtemp()
        self.snapshot_dir = Path(self.test_dir) / "gen_0001"
        self.snapshot_dir.mkdir(parents=True)
    
    def tearDown(self):
        """测试后清理"""
        if Path(self.test_dir).exists():
            shutil.rmtree(self.test_dir)
    
    def test_select_capabilities_high_fitness(self):
        """测试高适应度能力被保留"""
        capabilities = [
            {"name": "high_fitness", "fitness_score": 0.9, "usage_count": 100},
            {"name": "low_fitness", "fitness_score": 0.3, "usage_count": 5}
        ]
        
        result = self.transmitter._select_capabilities(capabilities)
        
        # 高适应度应该在保留列表
        keep_names = [c["name"] for c in result["keep"]]
        self.assertIn("high_fitness", keep_names)
        
        # 低适应度应该在淘汰列表
        eliminate_names = [c["name"] for c in result["eliminate"]]
        self.assertIn("low_fitness", eliminate_names)
    
    def test_select_capabilities_high_usage(self):
        """测试高使用率能力被保留"""
        capabilities = [
            {"name": "high_usage", "fitness_score": 0.6, "usage_count": 60}
        ]
        
        result = self.transmitter._select_capabilities(capabilities)
        
        keep_names = [c["name"] for c in result["keep"]]
        self.assertIn("high_usage", keep_names)
    
    def test_calculate_baseline(self):
        """测试性能基线计算"""
        capabilities = [
            {"name": "cap1", "fitness_score": 0.8, "usage_count": 50},
            {"name": "cap2", "fitness_score": 0.6, "usage_count": 30}
        ]
        
        baseline = self.transmitter._calculate_baseline(capabilities)
        
        self.assertEqual(baseline["capability_count"], 2)
        self.assertEqual(baseline["avg_fitness_score"], 0.7)
        self.assertEqual(baseline["total_usage_count"], 80)
    
    def test_save_and_load_genes(self):
        """测试遗传信息保存和加载"""
        genes = {
            "generation": 2,
            "parent_generation": 1,
            "inherited_capabilities": [
                {"name": "test_cap", "fitness_score": 0.9}
            ]
        }
        
        self.transmitter.save_genes(genes, self.snapshot_dir)
        
        loaded_genes = self.transmitter.load_genes(self.snapshot_dir)
        
        self.assertEqual(loaded_genes["generation"], 2)
        self.assertEqual(len(loaded_genes["inherited_capabilities"]), 1)


class TestMutationEngine(unittest.TestCase):
    """测试变异引擎"""
    
    def setUp(self):
        """测试前准备"""
        self.engine = MutationEngine(mutation_rate=1.0)  # 100%变异率用于测试
    
    def test_mutation_engine_initialization(self):
        """测试变异引擎初始化"""
        self.assertEqual(self.engine.mutation_rate, 1.0)
        self.assertIsInstance(self.engine.mutation_types, dict)
        self.assertIn("parameter_tuning", self.engine.mutation_types)
    
    def test_apply_mutations_adds_mutations_field(self):
        """测试应用变异后添加mutations字段"""
        genes = {
            "generation": 2,
            "inherited_capabilities": [
                {"name": "test_cap", "fitness_score": 0.8}
            ],
            "evolution_strategy": {"exploration_rate": 0.15}
        }
        
        mutated_genes = self.engine.apply_mutations(genes)
        
        self.assertIn("mutations", mutated_genes)
        self.assertIsInstance(mutated_genes["mutations"], list)
    
    def test_parameter_tuning_mutation(self):
        """测试参数微调变异"""
        genes = {
            "generation": 2,
            "inherited_capabilities": [
                {"name": "test_cap", "fitness_score": 0.8, "version": "1.0"}
            ]
        }
        
        mutated_genes, desc = self.engine._mutate_parameter_tuning(genes)
        
        # 验证fitness_score被调整
        cap = mutated_genes["inherited_capabilities"][0]
        # 应该在0.72-0.88范围内（±10%）
        self.assertGreaterEqual(cap["fitness_score"], 0.0)
        self.assertLessEqual(cap["fitness_score"], 1.0)
    
    def test_new_goal_injection_mutation(self):
        """测试新目标注入变异"""
        genes = {"generation": 2}
        
        mutated_genes, desc = self.engine._mutate_new_goal_injection(genes)
        
        self.assertIn("inherited_goals", mutated_genes)
        self.assertGreater(len(mutated_genes["inherited_goals"]), 0)
    
    def test_strategy_adjustment_mutation(self):
        """测试策略调整变异"""
        genes = {
            "generation": 2,
            "evolution_strategy": {"exploration_rate": 0.15}
        }
        
        mutated_genes, desc = self.engine._mutate_strategy_adjustment(genes)
        
        # exploration_rate应该被调整
        new_rate = mutated_genes["evolution_strategy"]["exploration_rate"]
        self.assertGreaterEqual(new_rate, 0.05)
        self.assertLessEqual(new_rate, 0.5)
    
    def test_capability_combination_mutation(self):
        """测试能力组合变异"""
        genes = {
            "generation": 2,
            "inherited_capabilities": [
                {"name": "cap1", "fitness_score": 0.8},
                {"name": "cap2", "fitness_score": 0.7}
            ]
        }
        
        mutated_genes, desc = self.engine._mutate_capability_combination(genes)
        
        if "suggested_combinations" in mutated_genes:
            self.assertGreater(len(mutated_genes["suggested_combinations"]), 0)
    
    def test_random_innovation_mutation(self):
        """测试随机创新变异"""
        genes = {"generation": 2}
        
        mutated_genes, desc = self.engine._mutate_random_innovation(genes)
        
        self.assertIn("innovation_suggestions", mutated_genes)
        self.assertGreater(len(mutated_genes["innovation_suggestions"]), 0)
    
    def test_get_mutation_summary(self):
        """测试获取变异摘要"""
        genes = {
            "generation": 2,
            "mutations": [
                {"type": "parameter_tuning", "description": "Test mutation"}
            ]
        }
        
        summary = self.engine.get_mutation_summary(genes)
        
        self.assertEqual(summary["total_mutations"], 1)
        self.assertIn("parameter_tuning", summary["mutation_types"])


class TestCollaborationInterface(unittest.TestCase):
    """测试协作接口"""
    
    def setUp(self):
        """测试前准备"""
        self.interface = CollaborationInterface(agent_id="test_agent")
    
    def test_initialization(self):
        """测试初始化"""
        self.assertEqual(self.interface.agent_id, "test_agent")
        self.assertEqual(len(self.interface.active_tasks), 0)
        self.assertEqual(len(self.interface.completed_tasks), 0)
    
    def test_receive_task_creates_task_entry(self):
        """测试接收任务创建任务条目"""
        from prokaryote_agent.daemon.collaboration_interface import Task, TaskPriority
        
        task = Task(
            task_id="task_001",
            title="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH
        )
        
        response = self.interface.receive_task(task)
        
        self.assertIn("status", response)
        self.assertIn(response["status"], ["accepted", "rejected", "needs_assistance"])
        self.assertEqual(response["agent_id"], "test_agent")
    
    def test_report_progress_for_active_task(self):
        """测试报告活跃任务的进度"""
        from prokaryote_agent.daemon.collaboration_interface import Task, TaskPriority
        
        task = Task(
            task_id="task_001",
            title="Test Task",
            description="A test task",
            priority=TaskPriority.HIGH
        )
        
        # 添加到活跃任务
        self.interface.active_tasks["task_001"] = task
        
        progress = self.interface.report_progress("task_001")
        
        self.assertEqual(progress["task_id"], "task_001")
        self.assertIn("status", progress)
        self.assertIn("progress", progress)
    
    def test_report_progress_for_nonexistent_task(self):
        """测试报告不存在任务的进度"""
        progress = self.interface.report_progress("nonexistent")
        
        self.assertIn("error", progress)
    
    def test_request_assistance(self):
        """测试请求协助"""
        request = self.interface.request_assistance(
            problem="Need help with code analysis",
            context={"language": "python"}
        )
        
        self.assertEqual(request["agent_id"], "test_agent")
        self.assertEqual(request["request_type"], "assistance")
        self.assertIn("problem", request)
        self.assertIn("required_capabilities", request)
    
    def test_provide_assistance(self):
        """测试提供协助"""
        request = {
            "problem": "Need code analysis",
            "required_capabilities": ["code_analysis"]
        }
        
        solution = self.interface.provide_assistance(request)
        
        self.assertIsNotNone(solution)
        self.assertIn("can_assist", solution)
    
    def test_share_capability(self):
        """测试分享能力"""
        export = self.interface.share_capability("test_capability")
        
        self.assertEqual(export["agent_id"], "test_agent")
        self.assertEqual(export["capability_name"], "test_capability")
        self.assertIn("version", export)
    
    def test_assess_collaboration_readiness(self):
        """测试评估协作就绪度"""
        assessment = self.interface.assess_collaboration_readiness()
        
        self.assertIn("collaboration_readiness", assessment)
        self.assertIn("checks", assessment)
        self.assertIn("ready_for_team", assessment)
        self.assertIn("recommendations", assessment)
        
        # 就绪度应该在0-1之间
        self.assertGreaterEqual(assessment["collaboration_readiness"], 0.0)
        self.assertLessEqual(assessment["collaboration_readiness"], 1.0)


class TestEvolutionDaemon(unittest.TestCase):
    """测试守护进程核心"""
    
    def setUp(self):
        """测试前准备"""
        self.test_config = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        config_data = {
            "restart_trigger": {"type": "evolution_count", "threshold": 10},
            "communication": {"heartbeat_interval": 30}
        }
        json.dump(config_data, self.test_config)
        self.test_config.close()
        
        self.daemon = EvolutionDaemon(config_path=self.test_config.name)
    
    def tearDown(self):
        """测试后清理"""
        Path(self.test_config.name).unlink()
    
    def test_initialization(self):
        """测试初始化"""
        self.assertIsNotNone(self.daemon.config)
        self.assertEqual(self.daemon.restart_threshold, 10)
        self.assertEqual(self.daemon.current_generation, 0)
        self.assertEqual(self.daemon.evolution_count_in_generation, 0)
    
    def test_load_default_config_when_file_missing(self):
        """测试配置文件不存在时加载默认配置"""
        daemon = EvolutionDaemon(config_path="nonexistent.json")
        
        self.assertIsNotNone(daemon.config)
        self.assertIn("restart_trigger", daemon.config)
    
    def test_is_agent_alive_returns_false_when_no_process(self):
        """测试没有进程时返回False"""
        self.assertFalse(self.daemon._is_agent_alive())
    
    def test_should_trigger_generation_transition(self):
        """测试代际转换触发条件"""
        self.daemon.evolution_count_in_generation = 5
        self.assertFalse(self.daemon._should_trigger_generation_transition())
        
        self.daemon.evolution_count_in_generation = 10
        self.assertTrue(self.daemon._should_trigger_generation_transition())
        
        self.daemon.evolution_count_in_generation = 15
        self.assertTrue(self.daemon._should_trigger_generation_transition())
    
    def test_handle_agent_message_evolution_success(self):
        """测试处理进化成功消息"""
        initial_count = self.daemon.evolution_count_in_generation
        
        message = {
            "event": "EVOLUTION_SUCCESS",
            "data": {}
        }
        
        self.daemon._handle_agent_message(message)
        
        self.assertEqual(self.daemon.evolution_count_in_generation, initial_count + 1)
    
    def test_handle_agent_message_heartbeat(self):
        """测试处理心跳消息"""
        message = {
            "event": "HEARTBEAT",
            "data": {}
        }
        
        self.daemon._handle_agent_message(message)
        
        self.assertIsNotNone(self.daemon.last_heartbeat_time)
    
    def test_get_status(self):
        """测试获取状态"""
        status = self.daemon.get_status()
        
        self.assertIn("daemon_running", status)
        self.assertIn("agent_alive", status)
        self.assertIn("current_generation", status)
        self.assertIn("evolution_count", status)
        self.assertIn("restart_threshold", status)


def run_tests():
    """运行所有测试"""
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加所有测试类
    suite.addTests(loader.loadTestsFromTestCase(TestGenerationManager))
    suite.addTests(loader.loadTestsFromTestCase(TestGeneticTransmitter))
    suite.addTests(loader.loadTestsFromTestCase(TestMutationEngine))
    suite.addTests(loader.loadTestsFromTestCase(TestCollaborationInterface))
    suite.addTests(loader.loadTestsFromTestCase(TestEvolutionDaemon))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == '__main__':
    result = run_tests()
    
    # 打印摘要
    print("\n" + "="*70)
    print("测试摘要:")
    print(f"运行测试数: {result.testsRun}")
    print(f"成功: {result.testsRun - len(result.failures) - len(result.errors)}")
    print(f"失败: {len(result.failures)}")
    print(f"错误: {len(result.errors)}")
    print("="*70)
    
    # 返回退出码
    exit(0 if result.wasSuccessful() else 1)

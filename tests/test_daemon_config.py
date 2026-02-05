"""
Unit tests for daemon_config.json validation.

Ensures configuration file is valid and contains all required settings.
"""

import unittest
import json
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))


class TestDaemonConfig(unittest.TestCase):
    """Test daemon_config.json."""
    
    def setUp(self):
        """Load daemon configuration."""
        config_path = Path(__file__).parent.parent / "prokaryote_agent" / "daemon_config.json"
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
    
    def test_config_loads_successfully(self):
        """Test that config loads without errors."""
        self.assertIsNotNone(self.config)
        self.assertIsInstance(self.config, dict)
    
    def test_has_restart_trigger_section(self):
        """Test restart_trigger section exists and has required keys."""
        self.assertIn('restart_trigger', self.config)
        restart = self.config['restart_trigger']
        
        self.assertIn('evolution_count_threshold', restart)
        self.assertIsInstance(restart['evolution_count_threshold'], int)
        self.assertGreater(restart['evolution_count_threshold'], 0)
        self.assertEqual(restart['evolution_count_threshold'], 10)
    
    def test_has_generation_management_section(self):
        """Test generation_management section exists and has required keys."""
        self.assertIn('generation_management', self.config)
        gen_mgmt = self.config['generation_management']
        
        required_keys = ['snapshot_dir', 'lineage_file', 'max_generations']
        for key in required_keys:
            self.assertIn(key, gen_mgmt, f"Missing key: {key}")
        
        self.assertIsInstance(gen_mgmt['max_generations'], int)
        self.assertGreater(gen_mgmt['max_generations'], 0)
    
    def test_has_mutation_section(self):
        """Test mutation section exists with valid rates."""
        self.assertIn('mutation', self.config)
        mutation = self.config['mutation']
        
        rate_keys = [
            'parameter_tuning_rate',
            'new_goal_injection_rate',
            'strategy_adjustment_rate',
            'capability_combination_rate',
            'random_innovation_rate'
        ]
        
        for key in rate_keys:
            self.assertIn(key, mutation, f"Missing mutation rate: {key}")
            rate = mutation[key]
            self.assertIsInstance(rate, (int, float))
            self.assertGreaterEqual(rate, 0.0)
            self.assertLessEqual(rate, 1.0)
        
        # Check that rates sum to approximately 1.0
        total_rate = sum(mutation[key] for key in rate_keys)
        self.assertAlmostEqual(total_rate, 1.0, places=2,
                              msg="Mutation rates should sum to 1.0")
    
    def test_has_genetic_transmission_section(self):
        """Test genetic_transmission section with threshold values."""
        self.assertIn('genetic_transmission', self.config)
        genetics = self.config['genetic_transmission']
        
        # Check fitness thresholds
        self.assertIn('fitness_score_keep_threshold', genetics)
        self.assertIn('fitness_score_eliminate_threshold', genetics)
        
        keep_threshold = genetics['fitness_score_keep_threshold']
        eliminate_threshold = genetics['fitness_score_eliminate_threshold']
        
        self.assertGreater(keep_threshold, eliminate_threshold,
                          "Keep threshold should be higher than eliminate threshold")
        
        # Check usage count thresholds
        self.assertIn('usage_count_keep_threshold', genetics)
        self.assertIn('usage_count_eliminate_threshold', genetics)
    
    def test_has_specialization_section(self):
        """Test specialization section with skill tree path."""
        self.assertIn('specialization', self.config)
        spec = self.config['specialization']
        
        self.assertIn('skill_tree_path', spec)
        self.assertIn('default_domain', spec)
        self.assertIn('enable_skill_tree', spec)
        
        # Verify skill tree path references real domain
        self.assertEqual(spec['default_domain'], 'software_development')
        self.assertIn('software_dev_tree.json', spec['skill_tree_path'])
    
    def test_has_communication_section(self):
        """Test communication section with protocol settings."""
        self.assertIn('communication', self.config)
        comm = self.config['communication']
        
        self.assertIn('protocol', comm)
        self.assertIn('pipe_name', comm)
        self.assertIn('heartbeat_interval_seconds', comm)
        self.assertIn('heartbeat_timeout_seconds', comm)
        
        # Verify heartbeat timeout > interval
        interval = comm['heartbeat_interval_seconds']
        timeout = comm['heartbeat_timeout_seconds']
        self.assertGreater(timeout, interval,
                          "Heartbeat timeout should be greater than interval")
        
        # Verify Windows named pipe format
        if comm['protocol'] == 'named_pipe':
            self.assertTrue(comm['pipe_name'].startswith('\\\\.\\pipe\\'))
    
    def test_has_agent_parameters_section(self):
        """Test agent_parameters section with Agent launch settings."""
        self.assertIn('agent_parameters', self.config)
        agent = self.config['agent_parameters']
        
        required_keys = ['python_executable', 'agent_entry_script', 'default_interval']
        for key in required_keys:
            self.assertIn(key, agent, f"Missing agent parameter: {key}")
        
        # Verify interval is positive
        self.assertGreater(agent['default_interval'], 0)
    
    def test_has_monitoring_section(self):
        """Test monitoring section with threshold values."""
        self.assertIn('monitoring', self.config)
        mon = self.config['monitoring']
        
        threshold_keys = ['cpu_threshold_percent', 'memory_threshold_mb', 'disk_space_threshold_mb']
        for key in threshold_keys:
            self.assertIn(key, mon, f"Missing monitoring threshold: {key}")
            self.assertGreater(mon[key], 0)
    
    def test_has_logging_section(self):
        """Test logging section with file and level settings."""
        self.assertIn('logging', self.config)
        log = self.config['logging']
        
        self.assertIn('log_file', log)
        self.assertIn('log_level', log)
        
        # Verify log level is valid
        valid_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']
        self.assertIn(log['log_level'], valid_levels)
    
    def test_has_collaboration_section(self):
        """Test collaboration section for multi-Agent features."""
        self.assertIn('collaboration', self.config)
        collab = self.config['collaboration']
        
        self.assertIn('enable_collaboration', collab)
        self.assertIn('collaboration_port', collab)
        self.assertIn('max_team_members', collab)
        
        # Verify port is valid
        port = collab['collaboration_port']
        self.assertGreater(port, 1024)
        self.assertLess(port, 65536)
    
    def test_has_recovery_section(self):
        """Test recovery section with resilience settings."""
        self.assertIn('recovery', self.config)
        recovery = self.config['recovery']
        
        self.assertIn('auto_restart_on_crash', recovery)
        self.assertIn('max_restart_attempts', recovery)
        self.assertIn('emergency_stop_failure_threshold', recovery)
        
        # Verify restart attempts is reasonable
        attempts = recovery['max_restart_attempts']
        self.assertGreater(attempts, 0)
        self.assertLessEqual(attempts, 10)
    
    def test_has_performance_section(self):
        """Test performance section with optimization flags."""
        self.assertIn('performance', self.config)
        perf = self.config['performance']
        
        self.assertIn('enable_async_snapshot', perf)
        self.assertIn('cache_skill_tree', perf)
    
    def test_has_experimental_section(self):
        """Test experimental section exists."""
        self.assertIn('experimental', self.config)
        exp = self.config['experimental']
        
        # Verify experimental features are disabled by default
        self.assertFalse(exp.get('enable_cross_generation_learning', False))
        self.assertFalse(exp.get('enable_branching', False))
    
    def test_version_present(self):
        """Test that config has version field."""
        self.assertIn('version', self.config)
        self.assertIsInstance(self.config['version'], str)
        self.assertRegex(self.config['version'], r'^\d+\.\d+\.\d+$')
    
    def test_all_sections_have_descriptions(self):
        """Test that all major sections have description fields."""
        major_sections = [
            'restart_trigger', 'generation_management', 'mutation',
            'genetic_transmission', 'specialization', 'communication',
            'agent_parameters', 'monitoring', 'logging', 'collaboration',
            'recovery', 'performance', 'experimental'
        ]
        
        for section in major_sections:
            self.assertIn(section, self.config, f"Missing section: {section}")
            self.assertIn('description', self.config[section],
                         f"Section {section} missing description")


def run_tests():
    """Run all tests with summary."""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestDaemonConfig)
    
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

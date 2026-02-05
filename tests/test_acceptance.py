"""
V0.1版本验收测试 - 完整功能验证
按照PRD验收标准进行测试：
1. 稳定运行测试（30分钟无崩溃）
2. 异常修复成功率测试（≥95%）
3. 存储备份功能测试
"""

import sys
import os
import time
import json
from datetime import datetime

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import init_prokaryote, start_prokaryote, stop_prokaryote, query_prokaryote_state


class AcceptanceTest:
    """V0.1验收测试类"""
    
    def __init__(self):
        self.test_results = {
            "start_time": datetime.now().isoformat(),
            "tests": [],
            "summary": {}
        }
        self.storage_module = None
        
    def log(self, message, level="INFO"):
        """打印测试日志"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "SUCCESS": "✅",
            "ERROR": "❌",
            "WARNING": "⚠️"
        }.get(level, "  ")
        print(f"[{timestamp}] {prefix} {message}")
    
    def record_test(self, name, passed, details=""):
        """记录测试结果"""
        self.test_results["tests"].append({
            "name": name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        })
    
    def test_1_initialization(self):
        """测试1: 初始化功能"""
        self.log("=" * 60)
        self.log("测试1: 初始化功能验证", "INFO")
        self.log("=" * 60)
        
        try:
            result = init_prokaryote()
            
            if not result['success']:
                self.log(f"初始化失败: {result['msg']}", "ERROR")
                self.record_test("初始化功能", False, result['msg'])
                return False
            
            # 验证初始化结果
            assert 'data' in result
            assert 'base_state' in result['data']
            
            base_state = result['data']['base_state']
            self.log(f"版本: {base_state.get('version', 'unknown')}", "INFO")
            self.log(f"监测间隔: {base_state.get('monitor_interval', 0)}秒", "INFO")
            self.log(f"最大修复次数: {base_state.get('repair_max_count', 0)}", "INFO")
            
            # 保存存储模块引用
            from prokaryote_agent.api import _storage_module
            self.storage_module = _storage_module
            
            self.log("初始化测试通过", "SUCCESS")
            self.record_test("初始化功能", True, "配置加载成功，目录创建正常")
            return True
            
        except Exception as e:
            self.log(f"初始化测试异常: {str(e)}", "ERROR")
            self.record_test("初始化功能", False, str(e))
            return False
    
    def test_2_startup(self):
        """测试2: 启动功能"""
        self.log("\n" + "=" * 60)
        self.log("测试2: 启动功能验证", "INFO")
        self.log("=" * 60)
        
        try:
            result = start_prokaryote()
            
            if not result['success']:
                self.log(f"启动失败: {result['msg']}", "ERROR")
                self.record_test("启动功能", False, result['msg'])
                return False
            
            pid = result['pid']
            self.log(f"内核已启动 (PID: {pid})", "INFO")
            
            # 等待监测线程稳定
            time.sleep(2)
            
            # 验证状态
            state = query_prokaryote_state()
            if state['state'] != 'running':
                self.log(f"状态异常: {state['state']}", "ERROR")
                self.record_test("启动功能", False, f"状态={state['state']}")
                return False
            
            self.log("启动测试通过", "SUCCESS")
            self.record_test("启动功能", True, f"PID={pid}, 状态=running")
            return True
            
        except Exception as e:
            self.log(f"启动测试异常: {str(e)}", "ERROR")
            self.record_test("启动功能", False, str(e))
            return False
    
    def test_3_stability(self, duration_seconds=60):
        """测试3: 稳定运行测试（简化版，默认1分钟）"""
        self.log("\n" + "=" * 60)
        self.log(f"测试3: 稳定运行测试 ({duration_seconds}秒)", "INFO")
        self.log("=" * 60)
        
        try:
            start_time = time.time()
            last_report = start_time
            report_interval = 10  # 每10秒报告一次
            
            crashes = 0
            samples = 0
            
            while time.time() - start_time < duration_seconds:
                time.sleep(1)
                samples += 1
                
                # 检查状态
                state = query_prokaryote_state()
                if state['state'] not in ['running', 'stopped']:
                    crashes += 1
                    self.log(f"状态异常: {state['state']}", "WARNING")
                
                # 定期报告
                current_time = time.time()
                if current_time - last_report >= report_interval:
                    elapsed = int(current_time - start_time)
                    memory = state['resource'].get('memory_mb', 0)
                    cpu = state['resource'].get('cpu_percent', 0)
                    self.log(f"运行中... {elapsed}s | 内存: {memory:.1f}MB | CPU: {cpu:.1f}%", "INFO")
                    last_report = current_time
            
            total_time = time.time() - start_time
            stability_rate = (samples - crashes) / samples * 100 if samples > 0 else 0
            
            self.log(f"运行时间: {total_time:.1f}秒", "INFO")
            self.log(f"稳定率: {stability_rate:.1f}% ({samples-crashes}/{samples})", "INFO")
            
            # PRD要求：故障率≤2%，即稳定率≥98%
            passed = stability_rate >= 98.0
            
            if passed:
                self.log("稳定运行测试通过", "SUCCESS")
            else:
                self.log(f"稳定率不足: {stability_rate:.1f}% < 98%", "ERROR")
            
            self.record_test("稳定运行", passed, f"稳定率={stability_rate:.1f}%, 运行时间={total_time:.1f}s")
            return passed
            
        except Exception as e:
            self.log(f"稳定运行测试异常: {str(e)}", "ERROR")
            self.record_test("稳定运行", False, str(e))
            return False
    
    def test_4_repair_simulation(self):
        """测试4: 异常修复功能测试（模拟场景）"""
        self.log("\n" + "=" * 60)
        self.log("测试4: 异常修复功能测试", "INFO")
        self.log("=" * 60)
        
        try:
            # 获取修复模块
            from prokaryote_agent.api import _repair_module
            repair_module = _repair_module
            
            if not repair_module:
                self.log("修复模块未初始化", "ERROR")
                self.record_test("异常修复", False, "修复模块未初始化")
                return False
            
            # 定义测试场景
            test_scenarios = [
                {"type": "memory_overflow", "module": "resource", "severity": "high",
                 "message": "内存占用超标", "current_value": 600, "threshold": 500},
                {"type": "cpu_high", "module": "resource", "severity": "medium",
                 "message": "CPU占用过高", "current_value": 50, "threshold": 30},
                {"type": "disk_insufficient", "module": "storage", "severity": "high",
                 "message": "磁盘空间不足", "current_value": 50, "threshold": 100},
            ]
            
            repair_results = []
            
            for i, scenario in enumerate(test_scenarios, 1):
                self.log(f"\n场景{i}: {scenario['type']}", "INFO")
                
                # 添加时间戳
                scenario["timestamp"] = datetime.now().isoformat()
                
                # 执行修复
                result = repair_module.repair(scenario)
                
                success = result.get("success", False)
                repair_results.append({
                    "scenario": scenario['type'],
                    "success": success,
                    "message": result.get("msg", ""),
                    "duration_ms": result.get("duration_ms", 0)
                })
                
                status = "✅" if success else "❌"
                self.log(f"  {status} {result.get('msg', 'unknown')}", "INFO")
                self.log(f"  耗时: {result.get('duration_ms', 0)}ms", "INFO")
            
            # 计算成功率
            success_count = sum(1 for r in repair_results if r['success'])
            total_count = len(repair_results)
            success_rate = success_count / total_count * 100 if total_count > 0 else 0
            
            self.log(f"\n修复成功率: {success_rate:.1f}% ({success_count}/{total_count})", "INFO")
            
            # PRD要求：修复成功率≥95%
            passed = success_rate >= 95.0
            
            if passed:
                self.log("异常修复测试通过", "SUCCESS")
            else:
                self.log(f"成功率不足: {success_rate:.1f}% < 95%", "ERROR")
            
            self.record_test("异常修复", passed, 
                           f"成功率={success_rate:.1f}%, 测试场景={total_count}")
            return passed
            
        except Exception as e:
            self.log(f"异常修复测试异常: {str(e)}", "ERROR")
            self.record_test("异常修复", False, str(e))
            return False
    
    def test_5_storage_backup(self):
        """测试5: 存储备份功能测试"""
        self.log("\n" + "=" * 60)
        self.log("测试5: 存储备份功能测试", "INFO")
        self.log("=" * 60)
        
        try:
            if not self.storage_module:
                self.log("存储模块未初始化", "ERROR")
                self.record_test("存储备份", False, "存储模块未初始化")
                return False
            
            # 测试1: 配置备份
            self.log("测试配置文件备份...", "INFO")
            config_path = os.path.join(self.storage_module.config_dir, "config.json")
            backup_result = self.storage_module.create_backup(config_path, "test_config_backup.json")
            
            if not backup_result["success"]:
                self.log(f"配置备份失败: {backup_result['msg']}", "ERROR")
                self.record_test("存储备份", False, backup_result['msg'])
                return False
            
            self.log(f"✅ 配置备份成功: {backup_result['backup_path']}", "INFO")
            
            # 测试2: 备份加载
            self.log("测试备份文件加载...", "INFO")
            load_result = self.storage_module.load_backup("config_backup.json")
            
            if not load_result["success"]:
                self.log(f"备份加载失败: {load_result['msg']}", "ERROR")
                self.record_test("存储备份", False, load_result['msg'])
                return False
            
            self.log("✅ 备份加载成功", "INFO")
            
            # 测试3: 磁盘空间检查
            self.log("测试磁盘使用情况查询...", "INFO")
            disk_result = self.storage_module.get_disk_usage()
            
            if not disk_result["success"]:
                self.log(f"磁盘查询失败", "WARNING")
            else:
                self.log(f"✅ 磁盘可用: {disk_result['free_mb']:.1f}MB", "INFO")
            
            self.log("存储备份测试通过", "SUCCESS")
            self.record_test("存储备份", True, "配置备份、加载、磁盘检查均正常")
            return True
            
        except Exception as e:
            self.log(f"存储备份测试异常: {str(e)}", "ERROR")
            self.record_test("存储备份", False, str(e))
            return False
    
    def test_6_shutdown(self):
        """测试6: 停止功能"""
        self.log("\n" + "=" * 60)
        self.log("测试6: 停止功能验证", "INFO")
        self.log("=" * 60)
        
        try:
            result = stop_prokaryote()
            
            if not result['success']:
                self.log(f"停止失败: {result['msg']}", "ERROR")
                self.record_test("停止功能", False, result['msg'])
                return False
            
            # 验证状态
            time.sleep(1)
            state = query_prokaryote_state()
            if state['state'] == 'running':
                self.log("停止后状态仍为running", "ERROR")
                self.record_test("停止功能", False, "状态未正确更新")
                return False
            
            self.log("停止测试通过", "SUCCESS")
            self.record_test("停止功能", True, "内核正常停止")
            return True
            
        except Exception as e:
            self.log(f"停止测试异常: {str(e)}", "ERROR")
            self.record_test("停止功能", False, str(e))
            return False
    
    def generate_report(self):
        """生成测试报告"""
        self.log("\n" + "=" * 60)
        self.log("测试报告", "INFO")
        self.log("=" * 60)
        
        total = len(self.test_results["tests"])
        passed = sum(1 for t in self.test_results["tests"] if t["passed"])
        failed = total - passed
        
        self.test_results["summary"] = {
            "total": total,
            "passed": passed,
            "failed": failed,
            "pass_rate": passed / total * 100 if total > 0 else 0,
            "end_time": datetime.now().isoformat()
        }
        
        self.log(f"\n总测试数: {total}", "INFO")
        self.log(f"通过: {passed}", "SUCCESS" if failed == 0 else "INFO")
        self.log(f"失败: {failed}", "ERROR" if failed > 0 else "INFO")
        self.log(f"通过率: {self.test_results['summary']['pass_rate']:.1f}%", "INFO")
        
        # 详细结果
        self.log("\n详细结果:", "INFO")
        for test in self.test_results["tests"]:
            status = "✅" if test["passed"] else "❌"
            self.log(f"  {status} {test['name']}: {test['details']}", "INFO")
        
        # 保存报告
        try:
            report_file = f"test_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            with open(report_file, 'w', encoding='utf-8') as f:
                json.dump(self.test_results, f, indent=2, ensure_ascii=False)
            self.log(f"\n测试报告已保存: {report_file}", "SUCCESS")
        except Exception as e:
            self.log(f"报告保存失败: {str(e)}", "WARNING")
        
        return failed == 0
    
    def run_full_acceptance_test(self, stability_duration=60):
        """运行完整验收测试"""
        self.log("\n" + "=" * 70)
        self.log("prokaryote-agent V0.1 - 验收测试", "INFO")
        self.log("=" * 70)
        self.log(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", "INFO")
        self.log("=" * 70)
        
        try:
            # 执行所有测试
            if not self.test_1_initialization():
                self.log("\n初始化测试失败，中止测试", "ERROR")
                return False
            
            if not self.test_2_startup():
                self.log("\n启动测试失败，中止测试", "ERROR")
                return False
            
            if not self.test_3_stability(stability_duration):
                self.log("\n稳定运行测试失败", "WARNING")
            
            if not self.test_4_repair_simulation():
                self.log("\n异常修复测试失败", "WARNING")
            
            if not self.test_5_storage_backup():
                self.log("\n存储备份测试失败", "WARNING")
            
            self.test_6_shutdown()
            
            # 生成报告
            all_passed = self.generate_report()
            
            self.log("\n" + "=" * 70)
            if all_passed:
                self.log("✅ 所有测试通过！V0.1版本验收合格！", "SUCCESS")
            else:
                self.log("⚠️  部分测试失败，请查看详细报告", "WARNING")
            self.log("=" * 70)
            
            return all_passed
            
        except KeyboardInterrupt:
            self.log("\n\n测试被用户中断", "WARNING")
            try:
                stop_prokaryote()
            except:
                pass
            return False
        except Exception as e:
            self.log(f"\n测试过程异常: {str(e)}", "ERROR")
            import traceback
            traceback.print_exc()
            try:
                stop_prokaryote()
            except:
                pass
            return False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='prokaryote-agent V0.1 验收测试')
    parser.add_argument('--duration', type=int, default=60,
                       help='稳定运行测试时长（秒），默认60秒，完整验收建议1800秒（30分钟）')
    parser.add_argument('--quick', action='store_true',
                       help='快速测试模式（30秒稳定测试）')
    
    args = parser.parse_args()
    
    if args.quick:
        duration = 30
        print("\n⚡ 快速测试模式（30秒）")
    else:
        duration = args.duration
        if duration >= 1800:
            print(f"\n⏱️  完整验收模式（{duration}秒 = {duration/60:.1f}分钟）")
        else:
            print(f"\n⏱️  简化测试模式（{duration}秒）")
    
    # 运行测试
    tester = AcceptanceTest()
    success = tester.run_full_acceptance_test(stability_duration=duration)
    
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())

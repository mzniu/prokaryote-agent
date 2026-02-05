#!/usr/bin/env python
"""
Prokaryote Agent - 目标驱动进化模式
根据 evolution_goals.md 中定义的目标自动进化
"""

import os
import sys
import time
import signal
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import (
    init_prokaryote,
    start_prokaryote,
    stop_prokaryote,
    generate_capability
)
from prokaryote_agent.goal_manager import EvolutionGoalManager, GoalStatus
from prokaryote_agent.iterative_evolver import IterativeEvolver
from prokaryote_agent.storage import StorageManager
from prokaryote_agent.capability_generator import CapabilityGenerator
from prokaryote_agent.ai_adapter import AIAdapter, AIConfig


class GoalDrivenAgent:
    """目标驱动进化Agent"""
    
    def __init__(self, goal_file: str = None, interval: int = 10, evolution_mode: str = None):
        """
        初始化目标驱动Agent
        
        Args:
            goal_file: 目标文件路径，默认为 evolution_goals.md
            interval: 进化间隔（秒），默认10秒
            evolution_mode: 进化模式，"simple" 或 "iterative"，默认从配置读取
        """
        self.goal_manager = EvolutionGoalManager(goal_file)
        self.interval = interval
        self.running = False
        self.initialized = False
        
        # 加载配置
        self.storage = StorageManager()
        self.config = self._load_config()
        
        # 确定进化模式
        self.evolution_mode = evolution_mode or self.config.get('evolution', {}).get('mode', 'simple')
        
        # 初始化进化器
        self.capability_generator = None
        self.iterative_evolver = None
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] [%(levelname)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _load_config(self) -> dict:
        """加载配置文件"""
        try:
            result = self.storage.load_config()
            if isinstance(result, dict) and 'config' in result:
                return result['config']
            return result if isinstance(result, dict) else {}
        except Exception as e:
            self.logger.warning(f"加载配置失败: {e}，使用默认配置")
            return {}
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print("\n\n⚠️  收到停止信号，正在关闭...")
        self.shutdown()
        sys.exit(0)
    
    def initialize(self) -> bool:
        """初始化系统"""
        self._print_header()
        
        # 加载进化目标
        print("\n[1/3] 加载进化目标...")
        result = self.goal_manager.load_goals()
        
        if not result["success"]:
            print(f"✗ 加载目标失败: {result['error']}")
            return False
        
        summary = self.goal_manager.get_summary()
        print(f"✓ 已加载 {summary['total']} 个目标")
        print(f"  - 待执行: {summary['pending']}")
        print(f"  - 已完成: {summary['completed']}")
        print(f"  - 失败: {summary['failed']}")
        
        if summary['pending'] == 0:
            print("\n✓ 所有目标已完成！")
            print("🔍 将扫描现有能力寻找优化机会...")
            # 不直接返回False，让系统继续运行以寻找优化机会
        
        # 初始化系统（不启动监控，进化过程不需要自我监控）
        print("\n[2/2] 初始化系统...")
        init_result = init_prokaryote()
        
        if not init_result['success']:
            print(f"✗ 系统初始化失败: {init_result['msg']}")
            return False
        
        print("✓ 系统初始化成功")
        
        # 初始化进化器
        self._initialize_evolver()
        
        self.initialized = True
        return True
    
    def _initialize_evolver(self):
        """初始化进化器"""
        # 从配置中创建AIAdapter（使用capability_config，兼容旧版ai_config）
        ai_config_dict = self.config.get('capability_config', self.config.get('ai_config', {}))
        ai_config = AIConfig(
            provider=ai_config_dict.get('ai_provider', 'deepseek'),
            api_key=ai_config_dict.get('api_key', ''),
            api_base=ai_config_dict.get('api_base', 'https://api.deepseek.com/v1'),
            model=ai_config_dict.get('model', 'deepseek-reasoner'),
            max_tokens=ai_config_dict.get('max_tokens', 40000),
            temperature=ai_config_dict.get('temperature', 0.7),
            timeout=ai_config_dict.get('timeout', 60),
            max_retries=ai_config_dict.get('max_retries', 3),
            retry_delay=ai_config_dict.get('retry_delay', 2)
        )
        ai_adapter = AIAdapter(ai_config)
        
        self.capability_generator = CapabilityGenerator(self.storage, ai_adapter)
        
        if self.evolution_mode == 'iterative':
            iterative_config = self.config.get('evolution', {}).get('iterative_config', {})
            self.iterative_evolver = IterativeEvolver(self.capability_generator, iterative_config)
            print(f"\n⚙️  进化模式: 迭代式 (Iterative)")
            print(f"   最大迭代次数: {iterative_config.get('max_iterations_per_goal', 15)}")
            print(f"   每阶段最大尝试: {iterative_config.get('max_attempts_per_stage', 3)}")
        else:
            print(f"\n⚙️  进化模式: 简单模式 (Simple)")
    
    def _find_optimization_opportunity(self):
        """查找需要优化的能力"""
        try:
            import os
            import json
            from prokaryote_agent.goal_manager import EvolutionGoal, GoalPriority
            
            # 扫描已生成的能力
            capabilities_dir = "./prokaryote_agent/capabilities/generated_code"
            if not os.path.exists(capabilities_dir):
                return None
            
            capabilities_to_optimize = []
            
            for filename in os.listdir(capabilities_dir):
                if not filename.endswith('.py'):
                    continue
                
                filepath = os.path.join(capabilities_dir, filename)
                try:
                    with open(filepath, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    # 提取能力元数据
                    cap_name = filename.replace('.py', '')
                    
                    # 查找测试文件
                    tests_dir = "./prokaryote_agent/capabilities/tests"
                    test_files = [f for f in os.listdir(tests_dir) if f.endswith('.py')] if os.path.exists(tests_dir) else []
                    
                    # 简单评估：如果代码较短或包含TODO/FIXME注释
                    code_length = len(content)
                    has_todo = 'TODO' in content or 'FIXME' in content or 'BUG' in content
                    has_error_handling = 'try:' in content and 'except' in content
                    
                    # 评分：代码质量问题
                    issues = []
                    score = 100
                    
                    if code_length < 500:
                        issues.append("代码过于简单")
                        score -= 20
                    
                    if has_todo:
                        issues.append("包含待办事项")
                        score -= 30
                    
                    if not has_error_handling:
                        issues.append("缺少错误处理")
                        score -= 25
                    
                    # 如果有明显问题，加入优化列表
                    if score < 80:
                        capabilities_to_optimize.append({
                            'name': cap_name,
                            'score': score,
                            'issues': issues,
                            'filepath': filepath
                        })
                        
                except Exception as e:
                    self.logger.debug(f"分析能力失败 {filename}: {e}")
                    continue
            
            if not capabilities_to_optimize:
                return None
            
            # 选择得分最低的能力进行优化
            capabilities_to_optimize.sort(key=lambda x: x['score'])
            target = capabilities_to_optimize[0]
            
            # 创建优化目标
            optimization_goal = EvolutionGoal(
                title=f"优化能力: {target['name']}",
                description=f"当前质量评分: {target['score']}/100\n问题: {', '.join(target['issues'])}\n\n请基于现有代码进行优化改进，保留核心功能的同时提升代码质量。",
                priority=GoalPriority.MEDIUM,
                acceptance_criteria=[
                    "改善代码结构和可读性",
                    "增强错误处理机制",
                    "提高测试覆盖率",
                    "优化性能和资源使用"
                ],
                max_attempts=3
            )
            
            return optimization_goal
            
        except Exception as e:
            self.logger.error(f"查找优化机会失败: {e}")
            return None
    
    def _print_header(self):
        """打印头部信息"""
        print("=" * 70)
        print("  Prokaryote Agent - 目标驱动进化模式")
        print("  根据 evolution_goals.md 自动进化")
        print("=" * 70)
    
    def run(self):
        """运行目标驱动进化循环"""
        if not self.initialized:
            if not self.initialize():
                return
        
        self.running = True
        
        print("\n" + "=" * 70)
        print("  开始目标驱动进化")
        print("  按 Ctrl+C 停止")
        print("=" * 70)
        
        while self.running:
            # 获取下一个目标
            goal = self.goal_manager.get_next_goal()
            
            if not goal:
                # 没有新目标时，尝试优化已有能力
                print("\n" + "=" * 70)
                print("  没有待执行的进化目标")
                print("  🔍 扫描已有能力，寻找优化机会...")
                print("=" * 70)
                
                optimization_goal = self._find_optimization_opportunity()
                if optimization_goal:
                    print(f"\n💡 发现优化机会: {optimization_goal.title}")
                    print(f"   当前测试通过率: {optimization_goal.description}")
                    self._execute_goal(optimization_goal)
                    continue
                else:
                    print("\n✓ 所有能力状态良好，无需优化")
                    self._print_completion_summary()
                    break
            
            # 执行目标
            self._execute_goal(goal)
            
            # 检查是否还有目标
            remaining = len(self.goal_manager.get_pending_goals())
            if remaining == 0:
                self._print_completion_summary()
                break
            
            # 等待间隔
            print(f"\n⏱️  等待 {self.interval} 秒后继续下一个目标...")
            print(f"   剩余目标: {remaining} 个")
            time.sleep(self.interval)
        
        self.shutdown()
    
    def _execute_goal(self, goal):
        """执行单个目标（支持简单模式和迭代模式）"""
        print("\n" + "=" * 70)
        print(f"📎 目标: {goal.title}")
        print(f"   优先级: {goal.priority.value}")
        
        if self.evolution_mode == 'iterative':
            self._execute_goal_iterative(goal)
        else:
            self._execute_goal_simple(goal)
    
    def _execute_goal_simple(self, goal):
        """简单模式：原有的一次性进化逻辑"""
        print(f"   尝试次数: {goal.attempts + 1}/{goal.max_attempts}")
        print("=" * 70)
        
        # 标记为进行中
        self.goal_manager.mark_goal_in_progress(goal)
        
        # 生成指导语
        guidance = self.goal_manager.generate_guidance_from_goal(goal)
        print(f"\n📝 指导语:\n{guidance}\n")
        
        # 调用能力生成
        print("🧬 开始进化...")
        result = generate_capability(guidance)
        
        if result['success']:
            capability_id = result.get('capability_id', 'unknown')
            print(f"\n✅ 进化成功!")
            print(f"   能力ID: {capability_id}")
            print(f"   测试通过: {result.get('test_passed', False)}")
            
            # 标记目标完成
            self.goal_manager.mark_goal_completed(goal, [capability_id])
            
            # 显示生成的代码信息
            if result.get('code'):
                print(f"   代码长度: {len(result['code'])} 字符")
        else:
            error_msg = result.get('error', '未知错误')
            print(f"\n❌ 进化失败: {error_msg}")
            
            # 标记失败
            self.goal_manager.mark_goal_failed(goal, error_msg)
            
            if goal.attempts >= goal.max_attempts:
                print(f"   已达到最大尝试次数 ({goal.max_attempts})，放弃此目标")
            else:
                print(f"   将在下次循环中重试")
    
    def _execute_goal_iterative(self, goal):
        """迭代模式：分阶段渐进式进化"""
        print("=" * 70)
        
        # 标记为进行中
        self.goal_manager.mark_goal_in_progress(goal)
        
        # 使用迭代进化器
        print("\n🔄 使用迭代式进化系统...")
        result = self.iterative_evolver.evolve_with_iterations(goal)
        
        if result['success']:
            summary = result.get('summary', {})
            print(f"\n✅ 迭代进化成功!")
            print(f"   能力ID: {result.get('capability_id')}")
            print(f"   总迭代次数: {summary.get('total_iterations', 0)}")
            print(f"   成功率: {summary.get('success_rate', 0):.0%}")
            print(f"   测试通过率: {result.get('test_pass_rate', 0):.0%}")
            print(f"   完成阶段: {summary.get('completed_stages', 0)}/{summary.get('total_stages', 0)}")
            
            if result.get('warning'):
                print(f"   ⚠️  {result['warning']}")
            
            # 标记目标完成
            self.goal_manager.mark_goal_completed(goal, [result['capability_id']])
            
            # 显示迭代历史
            if goal.iteration_history:
                print(f"\n📊 迭代历史:")
                for i, record in enumerate(goal.iteration_history[-3:], 1):  # 显示最后3次
                    status = "✅" if record.success else "❌"
                    print(f"     {status} 迭代{record.iteration_number}: 阶段{record.stage_number}, 尝试{record.attempt_within_stage}")
        else:
            error_msg = result.get('error', '未知错误')
            print(f"\n❌ 迭代进化失败: {error_msg}")
            
            summary = result.get('summary', {})
            print(f"   尝试了 {summary.get('total_iterations', 0)} 次迭代")
            
            # 标记失败
            self.goal_manager.mark_goal_failed(goal, error_msg)
    
    def _print_completion_summary(self):
        """打印完成摘要"""
        print("\n" + "=" * 70)
        print("  进化完成!")
        print("=" * 70)
        
        summary = self.goal_manager.get_summary()
        
        print(f"\n📊 最终统计:")
        print(f"   - 总目标数: {summary['total']}")
        print(f"   - 已完成: {summary['completed']} ✅")
        print(f"   - 失败: {summary['failed']} ❌")
        print(f"   - 待执行: {summary['pending']} ⏳")
        
        # 显示完成的目标
        completed = self.goal_manager.get_completed_goals()
        if completed:
            print(f"\n✅ 已完成的目标:")
            for g in completed:
                caps = ', '.join(g.generated_capabilities) if g.generated_capabilities else '无'
                print(f"   - {g.title} (能力: {caps})")
        
        # 显示失败的目标
        failed = self.goal_manager.get_failed_goals()
        if failed:
            print(f"\n❌ 失败的目标:")
            for g in failed:
                print(f"   - {g.title}: {g.error_message}")
    
    def shutdown(self):
        """关闭Agent"""
        self.running = False
        
        if self.initialized:
            print("\n[关闭] 进化循环已停止")
            # 进化过程没有启动监控模块，无需调用 stop_prokaryote()


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prokaryote Agent - 目标驱动进化模式')
    parser.add_argument('--goal-file', '-g', type=str, default=None,
                        help='进化目标文件路径 (默认: evolution_goals.md)')
    parser.add_argument('--interval', '-i', type=int, default=10,
                        help='进化间隔秒数 (默认: 10)')
    parser.add_argument('--mode', '-m', type=str, choices=['simple', 'iterative'], default=None,
                        help='进化模式: simple=简单模式, iterative=迭代模式 (默认: 从配置读取)')
    
    args = parser.parse_args()
    
    agent = GoalDrivenAgent(
        goal_file=args.goal_file,
        interval=args.interval,
        evolution_mode=args.mode
    )
    
    agent.run()


if __name__ == "__main__":
    main()

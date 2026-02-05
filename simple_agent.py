#!/usr/bin/env python
"""
Prokaryote Agent - 简化版进化脚本
由 daemon 启动，执行进化循环
"""

import os
import sys
import time
import signal
import logging
import json
from datetime import datetime
from pathlib import Path

# 确保能找到模块
sys.path.insert(0, str(Path(__file__).parent))

from prokaryote_agent import (
    init_prokaryote,
    start_prokaryote,
    stop_prokaryote,
    query_prokaryote_state
)
from prokaryote_agent.goal_manager import EvolutionGoalManager, GoalStatus


class SimpleEvolutionAgent:
    """简化版进化Agent"""
    
    def __init__(self, goal_file: str = None, interval: int = 30):
        """
        初始化
        
        Args:
            goal_file: 目标文件路径
            interval: 检查间隔（秒）
        """
        self.goal_file = goal_file or "evolution_goals.md"
        self.interval = interval
        self.running = False
        self.evolution_count = 0
        
        # 设置日志
        logging.basicConfig(
            level=logging.INFO,
            format='[%(asctime)s] %(message)s',
            datefmt='%H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # 信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理"""
        print("\n⚠️  收到停止信号，正在关闭...")
        self.running = False
    
    def initialize(self) -> bool:
        """初始化系统"""
        print("=" * 50)
        print("🧬 Prokaryote Agent - 进化系统")
        print("=" * 50)
        
        # 初始化核心系统
        print("\n[1/2] 初始化核心系统...")
        result = init_prokaryote()
        if not result.get('success'):
            print(f"❌ 初始化失败: {result.get('msg')}")
            return False
        print("✅ 核心系统初始化成功")
        
        # 加载目标
        print("\n[2/2] 加载进化目标...")
        self.goal_manager = EvolutionGoalManager(self.goal_file)
        goals = self.goal_manager.load_goals()
        
        stats = self.goal_manager.get_statistics()
        print(f"✅ 已加载 {stats['total']} 个目标")
        print(f"   - 待执行: {stats['pending']}")
        print(f"   - 已完成: {stats['completed']}")
        
        return True
    
    def run(self):
        """运行进化循环"""
        if not self.initialize():
            return
        
        print(f"\n🚀 开始进化循环 (间隔: {self.interval}秒)")
        print("按 Ctrl+C 停止\n")
        
        self.running = True
        
        while self.running:
            try:
                self._evolution_cycle()
                
                # 等待下一轮
                for _ in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
            except Exception as e:
                self.logger.error(f"进化循环错误: {e}")
                time.sleep(5)
        
        print("\n👋 进化系统已停止")
    
    def _evolution_cycle(self):
        """单次进化循环"""
        # 获取下一个目标
        goal = self.goal_manager.get_next_goal()
        
        if not goal:
            self.logger.info("📋 没有待执行的目标")
            return
        
        self.logger.info(f"🎯 处理目标: {goal.title}")
        
        # 标记为进行中
        self.goal_manager.mark_goal_in_progress(goal)
        
        try:
            # 执行进化（这里是简化版，实际应该调用能力生成器）
            success = self._execute_goal(goal)
            
            if success:
                self.goal_manager.mark_goal_completed(goal)
                self.evolution_count += 1
                self.logger.info(f"✅ 目标完成: {goal.title}")
            else:
                self.goal_manager.mark_goal_failed(goal, "执行失败")
                self.logger.warning(f"❌ 目标失败: {goal.title}")
                
        except Exception as e:
            self.goal_manager.mark_goal_failed(goal, str(e))
            self.logger.error(f"❌ 目标异常: {e}")
    
    def _execute_goal(self, goal) -> bool:
        """执行目标（简化版）"""
        # 这里应该集成实际的能力生成逻辑
        # 目前只是模拟
        
        self.logger.info(f"   执行: {goal.description or goal.title}")
        
        # 检查验收标准
        if goal.acceptance_criteria:
            for criterion in goal.acceptance_criteria:
                self.logger.info(f"   验收: {criterion}")
        
        # 模拟执行时间
        time.sleep(2)
        
        # 简化版：总是成功
        return True


def main():
    """主入口"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prokaryote Agent 进化系统')
    parser.add_argument('--mode', default='iterative', help='进化模式')
    parser.add_argument('--interval', type=int, default=30, help='检查间隔（秒）')
    parser.add_argument('--goals', default='evolution_goals.md', help='目标文件')
    
    args = parser.parse_args()
    
    agent = SimpleEvolutionAgent(
        goal_file=args.goals,
        interval=args.interval
    )
    agent.run()


if __name__ == "__main__":
    main()

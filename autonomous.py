#!/usr/bin/env python
"""
Prokaryote Agent - 自主进化模式
程序自动生成新能力，无需人工干预
"""

import os
import sys
import time
import signal
import logging
import random
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import (
    init_prokaryote,
    start_prokaryote,
    stop_prokaryote,
    query_prokaryote_state,
    generate_capability,
    manage_capabilities,
    invoke_capability
)


class AutonomousAgent:
    """自主进化Agent"""
    
    # 预定义的进化方向（能力池）
    CAPABILITY_IDEAS = [
        "创建一个读取文本文件的函数，支持UTF-8编码",
        "创建一个统计文本中单词数量的函数",
        "创建一个计算字符串长度的函数",
        "创建一个将字符串转换为大写的函数",
        "创建一个将字符串转换为小写的函数",
        "创建一个反转字符串的函数",
        "创建一个去除字符串首尾空格的函数",
        "创建一个统计文本行数的函数",
        "创建一个查找字符串中特定字符出现次数的函数",
        "创建一个将列表转换为逗号分隔字符串的函数",
        "创建一个生成随机数的函数",
        "创建一个计算两个数之和的函数",
        "创建一个判断数字是奇数还是偶数的函数",
        "创建一个获取当前时间戳的函数",
        "创建一个将秒数转换为时分秒格式的函数",
    ]
    
    def __init__(self, interval: int = 30, max_capabilities: int = 10, auto_enable: bool = False):
        """
        初始化自主Agent
        
        Args:
            interval: 进化间隔（秒）
            max_capabilities: 最大能力数量限制
            auto_enable: 是否自动启用生成的能力
        """
        self.interval = interval
        self.max_capabilities = max_capabilities
        self.auto_enable = auto_enable
        self.running = False
        self.initialized = False
        self.evolution_count = 0
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器"""
        print("\n\n⚠️  收到停止信号，正在关闭...")
        self.shutdown()
        sys.exit(0)
    
    def initialize(self):
        """初始化系统"""
        print("="*70)
        print("  Prokaryote Agent - 自主进化模式")
        print("  AI驱动的自动能力生成")
        print("="*70)
        
        # 检查API密钥
        if not os.environ.get("DEEPSEEK_API_KEY"):
            print("\n✗ 错误: 未设置 DEEPSEEK_API_KEY 环境变量")
            print("  自主进化模式需要DeepSeek API密钥")
            print("  请设置: set DEEPSEEK_API_KEY=your_key")
            return False
        
        print("\n[初始化] 正在初始化系统...")
        result = init_prokaryote()
        
        if not result['success']:
            print(f"✗ 初始化失败: {result['msg']}")
            return False
        
        print("✓ 系统初始化成功")
        
        print("\n[启动] 正在启动核心监控...")
        start_result = start_prokaryote()
        
        if not start_result['success']:
            print(f"✗ 启动失败: {start_result['msg']}")
            return False
        
        print(f"✓ 核心监控已启动 (PID: {start_result.get('pid', 'N/A')})")
        
        self.initialized = True
        self.running = True
        
        # 显示配置
        print(f"\n[配置]")
        print(f"  进化间隔: {self.interval} 秒")
        print(f"  能力上限: {self.max_capabilities}")
        print(f"  自动启用: {'是' if self.auto_enable else '否'}")
        
        # 显示初始状态
        self._show_status()
        
        return True
    
    def _show_status(self):
        """显示系统状态"""
        state = query_prokaryote_state()
        result = manage_capabilities("list")
        
        print(f"\n[状态] 第 {self.evolution_count} 次进化")
        print(f"  系统: 运行中")
        print(f"  内存: {state['resource'].get('memory_mb', 0):.2f} MB")
        print(f"  CPU: {state['resource'].get('cpu_percent', 0):.2f}%")
        
        if result["success"]:
            print(f"  能力: {result['total_count']} 个 " +
                  f"(启用: {result['enabled_count']}, 禁用: {result['disabled_count']})")
    
    def _select_evolution_target(self):
        """选择进化目标（从能力池随机选择）"""
        # 检查当前能力数量
        result = manage_capabilities("list")
        if result["success"] and result['total_count'] >= self.max_capabilities:
            print(f"  已达到能力上限 ({self.max_capabilities})，暂停生成")
            return None
        
        # 随机选择一个未实现的能力
        return random.choice(self.CAPABILITY_IDEAS)
    
    def _evolve_once(self):
        """执行一次进化"""
        self.evolution_count += 1
        
        print("\n" + "="*70)
        print(f"  第 {self.evolution_count} 次进化循环")
        print("="*70)
        
        # 选择进化目标
        target = self._select_evolution_target()
        
        if not target:
            return
        
        print(f"\n[进化目标] {target}")
        print("  正在调用AI生成代码...")
        
        # 生成能力
        result = generate_capability(target)
        
        if result["success"]:
            print(f"\n✓ 能力生成成功!")
            print(f"  ID: {result['capability_id']}")
            print(f"  名称: {result['capability_name']}")
            print(f"  描述: {result['description']}")
            print(f"  安全等级: {result['safety_level']}")
            
            if result.get('safety_issues'):
                print(f"  ⚠️  安全提示:")
                for issue in result['safety_issues']:
                    print(f"    - {issue}")
            
            # 自动启用
            if self.auto_enable and result['safety_level'] == 'safe':
                enable_result = manage_capabilities("enable", capability_id=result['capability_id'])
                if enable_result["success"]:
                    print(f"  ✓ 已自动启用")
                else:
                    print(f"  ✗ 自动启用失败: {enable_result.get('error', 'Unknown')}")
            else:
                print(f"  状态: 已生成但未启用 (需手动启用)")
        else:
            print(f"\n✗ 能力生成失败")
            print(f"  错误: {result.get('error', 'Unknown')}")
            print(f"  将在下次循环重试其他能力...")
    
    def run_autonomous_loop(self):
        """运行自主循环"""
        print("\n" + "="*70)
        print("  自主进化模式已启动")
        print(f"  系统将每 {self.interval} 秒自动生成一个新能力")
        print("  按 Ctrl+C 停止")
        print("="*70)
        
        while self.running:
            try:
                # 执行一次进化
                self._evolve_once()
                
                # 显示状态
                self._show_status()
                
                # 等待下一次进化
                print(f"\n等待 {self.interval} 秒后进行下次进化...")
                
                for i in range(self.interval):
                    if not self.running:
                        break
                    time.sleep(1)
                    
                    # 每10秒显示一次倒计时
                    remaining = self.interval - i - 1
                    if remaining > 0 and remaining % 10 == 0:
                        print(f"  ({remaining} 秒后继续...)")
            
            except KeyboardInterrupt:
                print("\n\n⚠️  用户中断")
                break
            except Exception as e:
                print(f"\n✗ 进化循环异常: {e}")
                logging.error(f"自主进化异常: {e}", exc_info=True)
                print("  等待 10 秒后继续...")
                time.sleep(10)
    
    def shutdown(self):
        """关闭系统"""
        if self.initialized:
            print("\n[关闭] 正在停止系统...")
            stop_prokaryote()
            print("✓ 系统已停止")
            
            # 显示最终统计
            result = manage_capabilities("list")
            if result["success"]:
                print(f"\n[最终统计]")
                print(f"  进化次数: {self.evolution_count}")
                print(f"  生成能力: {result['total_count']} 个")
                print(f"  启用能力: {result['enabled_count']} 个")
        
        self.running = False


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Prokaryote Agent - 自主进化模式')
    parser.add_argument('--interval', type=int, default=30,
                       help='进化间隔（秒），默认30秒')
    parser.add_argument('--max-capabilities', type=int, default=10,
                       help='最大能力数量，默认10个')
    parser.add_argument('--auto-enable', action='store_true',
                       help='自动启用安全的能力')
    
    args = parser.parse_args()
    
    agent = AutonomousAgent(
        interval=args.interval,
        max_capabilities=args.max_capabilities,
        auto_enable=args.auto_enable
    )
    
    # 初始化
    if not agent.initialize():
        print("\n✗ 初始化失败，无法启动")
        return 1
    
    # 运行自主循环
    try:
        agent.run_autonomous_loop()
    except Exception as e:
        print(f"\n✗ 运行异常: {e}")
        logging.error(f"主循环异常: {e}", exc_info=True)
        return 1
    finally:
        agent.shutdown()
    
    print("\n" + "="*70)
    print("  自主进化模式已退出")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

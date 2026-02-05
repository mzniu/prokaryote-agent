#!/usr/bin/env python
"""
Prokaryote Agent - 主程序入口
持续运行，接受用户指令，实现AI驱动的自我进化
"""

import os
import sys
import signal
import logging
from datetime import datetime

# 添加项目根目录到路径
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


class ProkaryoteAgent:
    """Prokaryote Agent 主控制器"""
    
    def __init__(self):
        self.running = False
        self.initialized = False
        
        # 注册信号处理
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理器（Ctrl+C等）"""
        print("\n\n⚠️  收到停止信号，正在关闭...")
        self.shutdown()
        sys.exit(0)
    
    def initialize(self):
        """初始化系统"""
        print("="*70)
        print("  Prokaryote Agent V0.2")
        print("  AI驱动的自我进化Agent")
        print("="*70)
        
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
        
        # 显示系统状态
        self._show_status()
        
        return True
    
    def _show_status(self):
        """显示系统状态"""
        state = query_prokaryote_state()
        
        print(f"\n[状态] 系统运行中")
        print(f"  内存: {state['resource'].get('memory_mb', 0):.2f} MB")
        print(f"  CPU: {state['resource'].get('cpu_percent', 0):.2f}%")
        print(f"  磁盘: {state['resource'].get('disk_free_mb', 0):.0f} MB 可用")
    
    def _show_capabilities(self):
        """显示能力列表"""
        result = manage_capabilities("list")
        
        if not result["success"]:
            print(f"✗ 获取能力列表失败: {result.get('error', 'Unknown')}")
            return
        
        total = result['total_count']
        enabled = result['enabled_count']
        disabled = result['disabled_count']
        
        print(f"\n[能力] 当前能力统计")
        print(f"  总数: {total} | 启用: {enabled} | 禁用: {disabled}")
        
        if result["capabilities"]:
            print(f"\n  能力列表:")
            for i, cap in enumerate(result["capabilities"], 1):
                status_icon = "✓" if cap['status'] == 'enabled' else "✗"
                safety_icon = "🔒" if cap['safety_level'] == 'safe' else "⚠️"
                print(f"    {i}. {status_icon} {safety_icon} {cap['name']}")
                print(f"       {cap['description'][:60]}...")
                
                perf = cap.get('performance', {})
                if perf.get('total_invocations', 0) > 0:
                    print(f"       调用{perf['total_invocations']}次, " +
                          f"平均{perf['avg_execution_time_ms']:.1f}ms, " +
                          f"成功率{perf['success_rate']*100:.0f}%")
    
    def _evolve(self, guidance: str):
        """生成新能力（进化）"""
        print(f"\n[进化] 正在生成新能力...")
        print(f"  用户指引: {guidance}")
        
        # 检查API密钥
        if not os.environ.get("DEEPSEEK_API_KEY"):
            print("\n✗ 错误: 未设置 DEEPSEEK_API_KEY 环境变量")
            print("  请先设置API密钥: set DEEPSEEK_API_KEY=your_key")
            return
        
        print("  正在调用AI生成代码...")
        
        result = generate_capability(guidance)
        
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
            
            # 询问是否启用
            try:
                choice = input(f"\n是否启用该能力? (y/n): ").strip().lower()
                if choice == 'y':
                    enable_result = manage_capabilities("enable", capability_id=result['capability_id'])
                    if enable_result["success"]:
                        print(f"✓ 能力已启用: {result['capability_name']}")
                    else:
                        print(f"✗ 启用失败: {enable_result.get('error', 'Unknown')}")
            except (EOFError, KeyboardInterrupt):
                print("\n已取消")
        else:
            print(f"\n✗ 能力生成失败")
            print(f"  错误: {result.get('error', 'Unknown')}")
    
    def _show_help(self):
        """显示帮助信息"""
        print("\n" + "="*70)
        print("  命令列表")
        print("="*70)
        print("\n  evolve <描述>  - 生成新能力（AI驱动的进化）")
        print("                   例: evolve 创建一个读取JSON文件的函数")
        print("\n  list           - 列出所有能力")
        print("  enable <ID>    - 启用能力")
        print("  disable <ID>   - 禁用能力")
        print("  info <ID>      - 查看能力详情")
        print("  status         - 查看系统状态")
        print("\n  help           - 显示此帮助")
        print("  quit/exit      - 退出程序")
        print("="*70)
    
    def run_command_loop(self):
        """运行命令循环"""
        print("\n" + "="*70)
        print("  系统已就绪，等待指令...")
        print("  输入 'help' 查看命令列表")
        print("  输入 'evolve <描述>' 开始进化")
        print("="*70)
        
        while self.running:
            try:
                # 读取用户输入
                cmd_input = input("\nprokaryote> ").strip()
                
                if not cmd_input:
                    continue
                
                # 解析命令
                parts = cmd_input.split(maxsplit=1)
                cmd = parts[0].lower()
                args = parts[1] if len(parts) > 1 else ""
                
                # 执行命令
                if cmd in ['quit', 'exit', 'q']:
                    print("正在退出...")
                    break
                
                elif cmd == 'help' or cmd == 'h':
                    self._show_help()
                
                elif cmd == 'status':
                    self._show_status()
                
                elif cmd == 'list' or cmd == 'ls':
                    self._show_capabilities()
                
                elif cmd == 'evolve' or cmd == 'gen':
                    if not args:
                        print("✗ 用法: evolve <功能描述>")
                        print("  例: evolve 创建一个计算字符串长度的函数")
                    else:
                        self._evolve(args)
                
                elif cmd == 'enable':
                    if not args:
                        print("✗ 用法: enable <能力ID>")
                    else:
                        result = manage_capabilities("enable", capability_id=args)
                        if result["success"]:
                            print(f"✓ {result.get('message', '已启用')}")
                        else:
                            print(f"✗ {result.get('error', 'Unknown')}")
                
                elif cmd == 'disable':
                    if not args:
                        print("✗ 用法: disable <能力ID>")
                    else:
                        result = manage_capabilities("disable", capability_id=args)
                        if result["success"]:
                            print(f"✓ {result.get('message', '已禁用')}")
                        else:
                            print(f"✗ {result.get('error', 'Unknown')}")
                
                elif cmd == 'info':
                    if not args:
                        print("✗ 用法: info <能力ID>")
                    else:
                        result = manage_capabilities("info", capability_id=args)
                        if result["success"]:
                            cap = result["capability"]
                            print(f"\n[能力详情]")
                            print(f"  ID: {cap['id']}")
                            print(f"  名称: {cap['name']}")
                            print(f"  版本: {cap['version']}")
                            print(f"  状态: {cap['status']}")
                            print(f"  描述: {cap['description']}")
                            print(f"  入口函数: {cap['entry_function']}")
                            print(f"  依赖: {cap['dependencies'] or '无'}")
                            print(f"  安全等级: {cap['safety_level']}")
                            print(f"  创建时间: {cap['created_at']}")
                            
                            perf = cap.get('performance', {})
                            if perf.get('total_invocations', 0) > 0:
                                print(f"\n  性能统计:")
                                print(f"    总调用: {perf['total_invocations']} 次")
                                print(f"    平均耗时: {perf['avg_execution_time_ms']:.2f} ms")
                                print(f"    平均内存: {perf['memory_usage_mb']:.2f} MB")
                                print(f"    成功率: {perf['success_rate']*100:.1f}%")
                        else:
                            print(f"✗ {result.get('error', 'Unknown')}")
                
                else:
                    print(f"✗ 未知命令: {cmd}")
                    print("  输入 'help' 查看可用命令")
            
            except KeyboardInterrupt:
                print("\n(使用 'quit' 退出)")
                continue
            except EOFError:
                print("\n正在退出...")
                break
            except Exception as e:
                print(f"\n✗ 命令执行出错: {e}")
                logging.error(f"命令执行异常: {e}", exc_info=True)
    
    def shutdown(self):
        """关闭系统"""
        if self.initialized:
            print("\n[关闭] 正在停止系统...")
            stop_prokaryote()
            print("✓ 系统已停止")
        
        self.running = False


def main():
    """主函数"""
    agent = ProkaryoteAgent()
    
    # 初始化
    if not agent.initialize():
        print("\n✗ 初始化失败，无法启动")
        return 1
    
    # 运行命令循环
    try:
        agent.run_command_loop()
    except Exception as e:
        print(f"\n✗ 运行异常: {e}")
        logging.error(f"主循环异常: {e}", exc_info=True)
        return 1
    finally:
        agent.shutdown()
    
    print("\n" + "="*70)
    print("  Prokaryote Agent 已退出")
    print("="*70)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

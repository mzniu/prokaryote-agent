"""
原智 (YuanZhi) - 交互式使用示例
演示如何使用原智Agent与用户进行对话
"""

from prokaryote_agent import AgentLoop
import logging

# 配置日志
logging.basicConfig(
    level=logging.WARNING,
    format='[%(levelname)s] %(message)s'
)

def main():
    print("=" * 60)
    print("原智 (YuanZhi) - 类生物原始进化型智能助手")
    print("=" * 60)
    print()
    
    # 初始化原智
    print("正在初始化原智...")
    agent = AgentLoop()
    
    tools = agent.get_available_tools()
    print(f"✓ 原智已就绪，当前具备 {len(tools)} 项能力")
    print(f"  能力示例: {', '.join(tools[:5])}...")
    print()
    print("输入你的问题，原智会自动选择合适的工具来帮助你。")
    print("输入 'quit' 或 'exit' 退出，输入 'clear' 清空历史")
    print("-" * 60)
    print()
    
    # 交互循环
    while True:
        try:
            user_input = input("你: ").strip()
            
            if not user_input:
                continue
            
            if user_input.lower() in ['quit', 'exit', '退出']:
                print("\n原智: 再见！👋")
                break
            
            if user_input.lower() in ['clear', '清空']:
                agent.clear_history()
                print("原智: 对话历史已清空。\n")
                continue
            
            # 调用原智
            print()
            response = agent.run(user_input)
            print(f"原智: {response}")
            print()
            
        except KeyboardInterrupt:
            print("\n\n原智: 再见！👋")
            break
        except Exception as e:
            print(f"\n原智: 抱歉，处理时遇到错误: {e}\n")

if __name__ == "__main__":
    main()

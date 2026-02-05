"""
基础使用示例 - 演示如何使用prokaryote-agent
"""

import sys
import os
import time

# 添加父目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import init_prokaryote, start_prokaryote, stop_prokaryote, query_prokaryote_state


def main():
    """基础使用流程"""
    
    print("=" * 60)
    print("prokaryote-agent V0.1 - 基础使用示例")
    print("=" * 60)
    print()
    
    # 步骤1: 初始化内核
    print("步骤1: 初始化内核...")
    result = init_prokaryote()
    
    if not result['success']:
        print(f"❌ 初始化失败: {result['msg']}")
        return
    
    print(f"✅ 初始化成功")
    print(f"   - 创建目录: {len(result['data'].get('created_dirs', []))} 个")
    print(f"   - 备份文件: {len(result['data'].get('backup_files', []))} 个")
    print()
    
    # 步骤2: 启动内核
    print("步骤2: 启动内核...")
    result = start_prokaryote()
    
    if not result['success']:
        print(f"❌ 启动失败: {result['msg']}")
        return
    
    print(f"✅ 启动成功")
    print(f"   - 进程ID: {result['pid']}")
    print(f"   - 监测间隔: 1秒")
    print()
    
    # 步骤3: 运行并监测
    print("步骤3: 运行并监测状态...")
    print("内核将运行10秒，每2秒查询一次状态")
    print()
    
    for i in range(5):
        time.sleep(2)
        
        # 查询状态
        state = query_prokaryote_state()
        
        print(f"[{i+1}/5] 状态查询:")
        print(f"   - 运行状态: {state['state']}")
        print(f"   - 内存占用: {state['resource'].get('memory_mb', 0)} MB")
        print(f"   - CPU占用: {state['resource'].get('cpu_percent', 0)} %")
        print(f"   - 磁盘可用: {state['resource'].get('disk_free_mb', 0)} MB")
        print(f"   - 修复次数: {len(state.get('repair_history', []))}")
        print()
    
    # 步骤4: 停止内核
    print("步骤4: 停止内核...")
    result = stop_prokaryote()
    
    if result['success']:
        print(f"✅ 停止成功")
    else:
        print(f"❌ 停止失败: {result['msg']}")
    
    print()
    print("=" * 60)
    print("示例运行完成")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n用户中断，正在停止...")
        stop_prokaryote()
    except Exception as e:
        print(f"\n\n发生异常: {str(e)}")
        stop_prokaryote()

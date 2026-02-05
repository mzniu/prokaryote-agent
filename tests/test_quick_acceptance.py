"""
快速验收测试 - 5分钟完整验证
"""

import sys
import os
import time
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from prokaryote_agent import init_prokaryote, start_prokaryote, stop_prokaryote, query_prokaryote_state


def run_quick_test():
    """运行快速验收测试"""
    print("=" * 70)
    print("prokaryote-agent V0.1 - 快速验收测试（5分钟）")
    print("=" * 70)
    print()
    
    results = []
    
    # 测试1: 初始化
    print("【测试1/6】初始化...")
    result = init_prokaryote()
    test1 = result['success']
    results.append(("初始化", test1))
    print(f"  {'✅ 通过' if test1 else '❌ 失败'}\n")
    
    if not test1:
        print("❌ 初始化失败，终止测试")
        return False
    
    # 测试2: 启动
    print("【测试2/6】启动...")
    result = start_prokaryote()
    test2 = result['success']
    results.append(("启动", test2))
    print(f"  {'✅ 通过' if test2 else '❌ 失败'}")
    print(f"  PID: {result.get('pid', 0)}\n")
    
    if not test2:
        print("❌ 启动失败，终止测试")
        return False
    
    # 测试3: 稳定运行（2分钟）
    print("【测试3/6】稳定运行测试（2分钟）...")
    duration = 120
    start_time = time.time()
    samples = 0
    errors = 0
    
    try:
        while time.time() - start_time < duration:
            time.sleep(5)
            samples += 1
            
            state = query_prokaryote_state()
            if state['state'] != 'running':
                errors += 1
            
            elapsed = int(time.time() - start_time)
            if elapsed % 30 == 0:  # 每30秒报告
                mem = state['resource'].get('memory_mb', 0)
                cpu = state['resource'].get('cpu_percent', 0)
                print(f"  {elapsed}s: 内存={mem:.1f}MB, CPU={cpu:.1f}%")
    except KeyboardInterrupt:
        print("\n  测试被中断")
        stop_prokaryote()
        return False
    
    stability = (samples - errors) / samples * 100 if samples > 0 else 0
    test3 = stability >= 98.0
    results.append(("稳定运行", test3))
    print(f"  {'✅ 通过' if test3 else '❌ 失败'} (稳定率: {stability:.1f}%)\n")
    
    # 测试4: 修复模拟
    print("【测试4/6】异常修复模拟...")
    from prokaryote_agent.api import _repair_module
    
    scenarios = [
        {"type": "memory_overflow", "module": "resource", "severity": "high",
         "message": "内存超标", "timestamp": datetime.now().isoformat()},
        {"type": "cpu_high", "module": "resource", "severity": "medium",
         "message": "CPU过高", "timestamp": datetime.now().isoformat()},
        {"type": "disk_insufficient", "module": "storage", "severity": "high",
         "message": "磁盘不足", "timestamp": datetime.now().isoformat()},
    ]
    
    success_count = 0
    for sc in scenarios:
        result = _repair_module.repair(sc)
        if result.get("success", False):
            success_count += 1
        print(f"  {sc['type']}: {'✅' if result.get('success') else '❌'}")
    
    repair_rate = success_count / len(scenarios) * 100
    test4 = repair_rate >= 95.0
    results.append(("异常修复", test4))
    print(f"  {'✅ 通过' if test4 else '❌ 失败'} (成功率: {repair_rate:.0f}%)\n")
    
    # 测试5: 存储备份
    print("【测试5/6】存储备份...")
    from prokaryote_agent.api import _storage_module
    
    config_path = os.path.join(_storage_module.config_dir, "config.json")
    backup_result = _storage_module.create_backup(config_path, "test_backup.json")
    load_result = _storage_module.load_backup("config_backup.json")
    
    test5 = backup_result["success"] and load_result["success"]
    results.append(("存储备份", test5))
    print(f"  {'✅ 通过' if test5 else '❌ 失败'}\n")
    
    # 测试6: 停止
    print("【测试6/6】停止...")
    result = stop_prokaryote()
    test6 = result['success']
    results.append(("停止", test6))
    print(f"  {'✅ 通过' if test6 else '❌ 失败'}\n")
    
    # 汇总
    print("=" * 70)
    print("测试汇总")
    print("=" * 70)
    
    passed = sum(1 for _, p in results if p)
    total = len(results)
    
    for name, passed_flag in results:
        print(f"  {'✅' if passed_flag else '❌'} {name}")
    
    print()
    print(f"通过率: {passed}/{total} = {passed/total*100:.0f}%")
    
    all_passed = passed == total
    print()
    if all_passed:
        print("✅ 所有测试通过！V0.1版本验收合格！")
    else:
        print(f"⚠️  {total-passed}个测试失败")
    
    print("=" * 70)
    
    return all_passed


if __name__ == "__main__":
    try:
        success = run_quick_test()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
        try:
            stop_prokaryote()
        except:
            pass
        sys.exit(1)

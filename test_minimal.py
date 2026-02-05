#!/usr/bin/env python
"""最小化测试：验证API调用是否正常返回"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from prokaryote_agent import init_prokaryote, start_prokaryote

print("1. 初始化...")
result1 = init_prokaryote()
print(f"   结果: {result1}")

print("\n2. 启动...")
result2 = start_prokaryote()
print(f"   结果: {result2}")

print("\n3. 完成！")
print("程序正常结束")

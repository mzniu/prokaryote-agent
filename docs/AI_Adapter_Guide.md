# AI Adapter 快速使用指南

## 安装依赖

```bash
pip install -r requirements.txt
```

## 配置 API 密钥

### Windows (PowerShell)
```powershell
$env:DEEPSEEK_API_KEY="your_api_key_here"
```

### Windows (CMD)
```cmd
set DEEPSEEK_API_KEY=your_api_key_here
```

### Linux/Mac
```bash
export DEEPSEEK_API_KEY=your_api_key_here
```

## 基础使用

### 1. 简单调用

```python
from prokaryote_agent.ai_adapter import AIAdapter

# 创建适配器
adapter = AIAdapter()

# 生成代码
result = adapter.generate_code("创建一个读取文本文件的函数")

if result["success"]:
    print(f"生成成功！")
    print(f"功能: {result['description']}")
    print(f"函数名: {result['entry_function']}")
    print(f"代码:\n{result['code']}")
else:
    print(f"生成失败: {result['error']}")
```

### 2. 自定义配置

```python
from prokaryote_agent.ai_adapter import AIAdapter, AIConfig

config = AIConfig(
    api_key="your_api_key",
    model="deepseek-reasoner",
    max_tokens=3000,
    temperature=0.7,
    timeout=60
)

adapter = AIAdapter(config)
result = adapter.generate_code("你的需求描述")
```

### 3. 带上下文生成

```python
context = {
    "existing_capabilities": [
        {"name": "file_reader", "description": "读取文件"},
        {"name": "json_parser", "description": "解析JSON"}
    ]
}

result = adapter.generate_code(
    "基于已有的文件读取和JSON解析能力，创建一个读取JSON配置文件的函数",
    context=context
)
```

## 测试

### 运行完整测试
```bash
python tests/test_ai_adapter.py
```

### 测试单个功能
```python
from prokaryote_agent.ai_adapter import test_ai_adapter

test_ai_adapter()
```

## 注意事项

1. **API密钥安全**: 不要将API密钥硬编码到代码中，使用环境变量
2. **费用控制**: DeepSeek API调用会产生费用，注意控制调用频率
3. **错误处理**: 建议始终检查 `result["success"]` 判断是否成功
4. **网络超时**: 默认超时60秒，可根据需要调整
5. **重试机制**: 内置3次重试，自动处理网络波动

## 返回值格式

### 成功时
```python
{
    "success": True,
    "code": "生成的完整Python代码",
    "description": "功能描述",
    "entry_function": "主函数名",
    "dependencies": ["依赖库1", "依赖库2"],
    "error": ""
}
```

### 失败时
```python
{
    "success": False,
    "code": "",
    "description": "",
    "entry_function": "",
    "dependencies": [],
    "error": "错误信息"
}
```

## 常见问题

### Q1: 提示 "requests库未安装"
```bash
pip install requests
```

### Q2: 提示 "未设置API密钥"
请按照上方配置API密钥的说明设置环境变量

### Q3: API调用失败
- 检查API密钥是否正确
- 检查网络连接
- 查看错误信息中的具体原因
- 确认 DeepSeek API 服务是否正常

### Q4: 生成的代码无法解析
- 检查返回值中的 `error` 字段
- 降级处理会尝试提取代码块
- 可能需要调整 `temperature` 参数使输出更稳定

## 示例：完整工作流

```python
import os
from prokaryote_agent.ai_adapter import AIAdapter

# 1. 设置API密钥（如果环境变量未设置）
# os.environ["DEEPSEEK_API_KEY"] = "your_key"

# 2. 创建适配器
adapter = AIAdapter()

# 3. 生成代码
result = adapter.generate_code(
    "创建一个函数，统计文本文件中的单词数量"
)

# 4. 处理结果
if result["success"]:
    # 保存生成的代码
    with open("generated_function.py", "w", encoding="utf-8") as f:
        f.write(result["code"])
    
    print(f"✓ 代码已保存到 generated_function.py")
    print(f"  函数名: {result['entry_function']}")
    print(f"  依赖: {result['dependencies']}")
    
    # 可以进一步测试生成的代码
    # ...
else:
    print(f"✗ 生成失败: {result['error']}")
```

## 下一步

- 查看 [V0.2 设计文档](../docs/V0.2_Design.md) 了解完整架构
- 等待 `capability_generator.py` 模块实现更高级的能力管理
- 等待 `sandbox.py` 模块实现安全的代码执行环境

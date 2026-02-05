# 设计方案：将能力作为Agent Tools使用

> **状态：✅ 已实施完成**

## 1. 背景与目标

### 1.1 背景
当前系统已具备：
- **能力生成**：AI生成代码 → 测试 → 保存
- **能力注册**：capability_registry.json 存储元数据
- **能力调用**：call_capability() 运行时调用

### 1.2 目标
将所有已进化的能力转换为标准的 **Tool 格式**，让 Agent 可以：
1. 通过 LLM 自动选择合适的 Tool
2. 自动解析参数并执行
3. 获取执行结果并继续推理

---

## 2. 设计方案

### 2.1 Tool Schema 格式

采用类似 OpenAI Function Calling 的标准格式：

```json
{
  "type": "function",
  "function": {
    "name": "add_numbers",
    "description": "将两个数字相加并返回结果",
    "parameters": {
      "type": "object",
      "properties": {
        "num1": {
          "type": "number",
          "description": "第一个数字"
        },
        "num2": {
          "type": "number",
          "description": "第二个数字"
        }
      },
      "required": ["num1", "num2"]
    }
  }
}
```

### 2.2 架构设计

```
┌─────────────────────────────────────────────────────────────────┐
│                         Agent Loop                               │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐  │
│  │  用户输入 │ -> │ LLM推理   │ -> │ Tool调用  │ -> │ 返回结果  │  │
│  └──────────┘    └──────────┘    └──────────┘    └──────────┘  │
│                        ↓                  ↓                      │
│                  ┌──────────┐      ┌──────────┐                 │
│                  │ Tools列表 │      │ 执行引擎  │                 │
│                  └──────────┘      └──────────┘                 │
└─────────────────────────────────────────────────────────────────┘
                         ↑                  ↑
                   ┌─────┴─────┐     ┌──────┴───────┐
                   │ ToolManager │     │ CapabilityRuntime │
                   └───────────┘     └──────────────┘
                         ↑
              ┌──────────┴──────────┐
              │ capability_registry.json │
              └─────────────────────────┘
```

### 2.3 核心模块

#### 2.3.1 ToolSchema（工具模式定义）
```python
@dataclass
class ToolParameter:
    name: str
    type: str  # "string", "number", "boolean", "object", "array"
    description: str
    required: bool = True
    default: Any = None
    enum: List[str] = None

@dataclass
class ToolSchema:
    name: str
    description: str
    parameters: List[ToolParameter]
    capability_id: str  # 对应的能力ID
    entry_function: str
```

#### 2.3.2 ToolManager（工具管理器）
```python
class ToolManager:
    def __init__(self):
        self.tools: Dict[str, ToolSchema] = {}
        self.runtime = CapabilityRuntime()
    
    def load_tools(self) -> int:
        """从能力注册表加载所有工具"""
        
    def get_tool(self, name: str) -> ToolSchema:
        """获取单个工具"""
        
    def list_tools(self) -> List[ToolSchema]:
        """列出所有工具"""
        
    def get_tools_for_llm(self) -> List[Dict]:
        """生成LLM可用的工具列表（OpenAI格式）"""
        
    def execute_tool(self, name: str, arguments: Dict) -> Dict:
        """执行工具并返回结果"""
```

#### 2.3.3 ParameterExtractor（参数提取器）
```python
class ParameterExtractor:
    def extract_from_code(self, code: str, entry_function: str) -> List[ToolParameter]:
        """从代码中提取参数信息"""
        # 解析函数签名
        # 解析docstring
        # 解析类型注解
        
    def extract_from_docstring(self, docstring: str) -> List[ToolParameter]:
        """从docstring中提取参数信息"""
```

#### 2.3.4 AgentLoop（Agent循环）
```python
class AgentLoop:
    def __init__(self):
        self.tool_manager = ToolManager()
        self.ai_adapter = AIAdapter()
        self.conversation_history = []
    
    def run(self, user_input: str) -> str:
        """运行Agent主循环"""
        # 1. 获取可用工具
        tools = self.tool_manager.get_tools_for_llm()
        
        # 2. 调用LLM（带工具）
        response = self.ai_adapter.chat_with_tools(
            messages=self.conversation_history,
            tools=tools
        )
        
        # 3. 处理工具调用
        while response.has_tool_calls:
            for tool_call in response.tool_calls:
                result = self.tool_manager.execute_tool(
                    tool_call.name,
                    tool_call.arguments
                )
                self.add_tool_result(tool_call.id, result)
            
            response = self.ai_adapter.continue_with_results()
        
        return response.content
```

---

## 3. 实施步骤

### Phase 1: 基础架构 ✅ 已完成

| 步骤 | 任务 | 产出文件 |
|------|------|----------|
| 1.1 | 定义数据结构 | `prokaryote_agent/tool_schema.py` ✅ |
| 1.2 | 实现参数提取器 | `prokaryote_agent/parameter_extractor.py` ✅ |
| 1.3 | 实现工具管理器 | `prokaryote_agent/tool_manager.py` ✅ |

### Phase 2: LLM集成 ✅ 已完成

| 步骤 | 任务 | 产出文件 |
|------|------|----------|
| 2.1 | 实现Agent循环 | `prokaryote_agent/agent_loop.py` ✅ |
| 2.2 | 更新导出 | 修改 `prokaryote_agent/__init__.py` ✅ |

---

## 4. 关键代码示例

### 4.1 工具格式转换

```python
def capability_to_tool_schema(capability: Dict) -> Dict:
    """将能力转换为OpenAI Tool格式"""
    code = read_capability_code(capability["code_path"])
    params = extract_parameters(code, capability["entry_function"])
    
    return {
        "type": "function",
        "function": {
            "name": capability["name"],
            "description": capability["description"],
            "parameters": {
                "type": "object",
                "properties": {
                    p.name: {
                        "type": p.type,
                        "description": p.description
                    } for p in params
                },
                "required": [p.name for p in params if p.required]
            }
        }
    }
```

### 4.2 LLM调用示例

```python
# DeepSeek API 支持 function calling
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=messages,
    tools=tools,  # 工具列表
    tool_choice="auto"  # 自动选择工具
)

# 处理工具调用
if response.choices[0].message.tool_calls:
    for tool_call in response.choices[0].message.tool_calls:
        function_name = tool_call.function.name
        arguments = json.loads(tool_call.function.arguments)
        result = tool_manager.execute_tool(function_name, arguments)
```

### 4.3 Agent循环示例

```python
# 用户使用示例
agent = AgentLoop()

# 用户请求
response = agent.run("帮我把数字3和5相加")
# Agent自动识别并调用 add_numbers 工具
# 返回: "3 + 5 = 8"

response = agent.run("读取config.json文件内容")
# Agent自动识别并调用 file_operation 工具
# 返回: 文件内容
```

---

## 5. 参数提取策略

### 5.1 从类型注解提取
```python
def add_numbers(num1: int, num2: int) -> int:
    # 类型 -> JSON Schema类型
    # int, float -> "number"
    # str -> "string"
    # bool -> "boolean"
    # list -> "array"
    # dict -> "object"
```

### 5.2 从Docstring提取
```python
def add_numbers(num1, num2):
    """
    将两个数字相加
    
    Args:
        num1: 第一个数字 (int)
        num2: 第二个数字 (int)
    
    Returns:
        int: 两数之和
    """
```

### 5.3 从函数签名推断
```python
def add_numbers(num1=0, num2=0):
    # 有默认值 -> required=False
    # 从默认值类型推断参数类型
```

---

## 6. 扩展能力元数据

建议在能力生成时，增加 `tool_schema` 字段：

```json
{
  "id": "cap_xxx",
  "name": "add_numbers",
  "tool_schema": {
    "parameters": [
      {"name": "num1", "type": "number", "description": "第一个数字", "required": true},
      {"name": "num2", "type": "number", "description": "第二个数字", "required": true}
    ],
    "returns": {"type": "number", "description": "两数之和"}
  }
}
```

---

## 7. 文件结构

```
prokaryote_agent/
├── tool_schema.py          # ✅ 工具模式定义
├── parameter_extractor.py  # ✅ 参数提取器
├── tool_manager.py         # ✅ 工具管理器
├── agent_loop.py           # ✅ Agent主循环
├── capability_runtime.py   # ✅ 工具执行支持
└── __init__.py             # ✅ 导出更新
```

---

## 8. 验收标准

1. ✅ 能够自动将能力转换为Tool格式
2. ✅ LLM能够理解并选择正确的Tool
3. ✅ Tool调用能够正确执行并返回结果
4. ✅ Agent能够基于Tool结果继续推理
5. ⏸️ CLI交互界面（可选，未实施）
6. ✅ 完善的错误处理和日志

---

## 9. 风险与应对

| 风险 | 影响 | 应对措施 |
|------|------|----------|
| 参数提取不准确 | Tool无法正确调用 | 生成能力时要求AI输出参数schema |
| LLM选择错误Tool | 执行失败 | 优化Tool描述，增加示例 |
| 执行超时 | 用户体验差 | 设置超时限制，异步执行 |
| 循环调用 | 死循环 | 设置最大迭代次数 |

---

## 10. 使用示例

### Python代码调用

```python
from prokaryote_agent import AgentLoop, chat

# 方式1：使用AgentLoop类
agent = AgentLoop()
result = agent.run("帮我查看系统CPU使用情况")
print(result)

# 方式2：使用便捷函数
response = chat("帮我把3和5相加")
print(response)
```

### 测试结果

```
=== 测试: 查看系统CPU和内存使用情况 ===
结果:
根据系统监控结果，以下是当前系统的使用情况：

## CPU使用情况：
- **CPU使用率：24.3%** - 系统CPU使用率正常

## 内存使用情况：
- **总内存：68.35 GB**
- **可用内存：37.53 GB**
- **内存使用率：45.1%** - 内存使用情况良好
...
```

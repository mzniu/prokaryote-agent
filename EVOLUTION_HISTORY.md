# 进化历史追溯系统

## 概述

每次进化（成功或失败）都会被记录到 `prokaryote_agent/evolution_history.json` 文件中，形成可追溯的进化路径。

## 历史文件结构

```json
{
  "evolution_history": [
    {
      "timestamp": "2026-02-03T08:30:15.123456",
      "capability_id": "cap_20260203_001",
      "capability_name": "http_client_module",
      "description": "HTTP客户端模块（支持GET/POST请求和JSON解析）",
      "evolution_reason": "扩展网络访问能力，获取外部数据资源",
      "success": true
    },
    {
      "timestamp": "2026-02-03T08:35:20.456789",
      "capability_id": "cap_20260203_002",
      "capability_name": "sqlite_database_module",
      "description": "本地SQLite数据库操作模块（创建表、增删改查）",
      "evolution_reason": "建立数据持久化能力，存储网络获取的数据",
      "success": true
    }
  ],
  "total_evolutions": 2,
  "successful_evolutions": 2,
  "failed_evolutions": 0
}
```

## 字段说明

### 记录字段
- `timestamp` - 进化发生的时间戳（ISO格式）
- `capability_id` - 生成的能力ID（失败时为"failed"）
- `capability_name` - 能力名称
- `description` - 能力描述或错误信息
- `evolution_reason` - 进化原因/目标（AI决策的依据）
- `success` - 是否成功（true/false）

### 统计字段
- `total_evolutions` - 总进化次数
- `successful_evolutions` - 成功次数
- `failed_evolutions` - 失败次数

## AI决策流程

### 1. 加载历史
```python
history = self._load_evolution_history()
recent_evolutions = history["evolution_history"][-10:]  # 最近10次
```

### 2. 构建上下文
AI会接收到完整的历史信息：
- 最近10次进化记录（时间、能力、原因）
- 总体统计数据（成功率、总次数）
- 当前能力列表

### 3. 智能决策
AI基于历史信息做出更好的决策：
- 避免重复已尝试过的方向
- 识别进化模式和趋势
- 基于成功/失败经验调整策略
- 确保进化路径的连贯性

### 4. 记录结果
```python
self._add_evolution_record(
    capability_id=result['capability_id'],
    capability_name=result['capability_name'],
    description=result['description'],
    evolution_reason=guidance,  # AI决策时的原因
    success=True
)
```

## 优势

### 1. 可追溯性
- 完整记录每一次进化尝试
- 可以回顾系统的成长路径
- 便于分析进化策略的有效性

### 2. AI学习能力
- AI可以从历史中学习
- 避免重复失败的尝试
- 识别成功的进化模式

### 3. 进化连贯性
- 每次决策都基于历史上下文
- 确保能力之间的协同效应
- 形成清晰的能力扩展路径

### 4. 调试与优化
- 分析失败原因
- 识别瓶颈和问题
- 优化进化策略

## 示例：进化路径分析

```json
[
  {
    "timestamp": "2026-02-03T08:00:00",
    "capability_name": "file_system_module",
    "evolution_reason": "建立基础的文件访问能力"
  },
  {
    "timestamp": "2026-02-03T08:15:00",
    "capability_name": "http_client_module",
    "evolution_reason": "扩展网络访问能力，获取远程数据"
  },
  {
    "timestamp": "2026-02-03T08:30:00",
    "capability_name": "json_xml_parser_module",
    "evolution_reason": "解析网络API返回的数据格式"
  },
  {
    "timestamp": "2026-02-03T08:45:00",
    "capability_name": "sqlite_database_module",
    "evolution_reason": "持久化存储从网络获取的数据"
  }
]
```

**可以看到清晰的进化逻辑**：
1. 建立文件访问基础
2. 扩展到网络访问
3. 增加数据解析能力
4. 建立数据存储能力

每一步都是基于前一步的延伸，形成完整的资源获取→处理→存储闭环。

## 查看历史

### 命令行
```bash
# 查看完整历史
cat prokaryote_agent/evolution_history.json

# 查看最近10条（Linux/Mac）
cat prokaryote_agent/evolution_history.json | jq '.evolution_history[-10:]'

# 查看统计（Windows PowerShell）
Get-Content prokaryote_agent\evolution_history.json | ConvertFrom-Json | Select-Object total_evolutions, successful_evolutions, failed_evolutions
```

### Python
```python
import json

with open('prokaryote_agent/evolution_history.json', 'r') as f:
    history = json.load(f)
    
print(f"总进化次数: {history['total_evolutions']}")
print(f"成功率: {history['successful_evolutions'] / history['total_evolutions'] * 100:.1f}%")

print("\n最近5次进化:")
for record in history['evolution_history'][-5:]:
    status = "✓" if record['success'] else "✗"
    print(f"{status} [{record['timestamp'][:19]}] {record['capability_name']}")
    print(f"  原因: {record['evolution_reason']}")
```

## 注意事项

1. **文件位置** - `prokaryote_agent/evolution_history.json`
2. **自动创建** - 首次运行时自动创建空历史
3. **持久化** - 历史记录永久保存，除非手动删除
4. **格式化** - 使用缩进的JSON格式，便于阅读
5. **编码** - UTF-8编码，支持中文

---

**现在，系统的每一次进化都有迹可循！** 📚🧬

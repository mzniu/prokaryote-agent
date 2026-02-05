# Prokaryote Agent - 快速开始

## 运行主程序

```bash
python main.py
```

## 基本使用

### 1. 系统会自动启动并进入命令模式

```
======================================================================
  Prokaryote Agent V0.2
  AI驱动的自我进化Agent
======================================================================

[初始化] 正在初始化系统...
✓ 系统初始化成功

[启动] 正在启动核心监控...
✓ 核心监控已启动 (PID: 12345)

======================================================================
  系统已就绪，等待指令...
  输入 'help' 查看命令列表
  输入 'evolve <描述>' 开始进化
======================================================================

prokaryote>
```

### 2. 主要命令

#### 让Agent进化（生成新能力）

```bash
prokaryote> evolve 创建一个读取文本文件的函数
```

系统会调用DeepSeek AI生成代码，安全检查后询问是否启用。

#### 查看所有能力

```bash
prokaryote> list
```

#### 查看系统状态

```bash
prokaryote> status
```

#### 启用/禁用能力

```bash
prokaryote> enable cap_abc123
prokaryote> disable cap_abc123
```

#### 查看能力详情

```bash
prokaryote> info cap_abc123
```

#### 退出

```bash
prokaryote> quit
```

## 完整命令列表

```
evolve <描述>  - 生成新能力（AI驱动的进化）
                 例: evolve 创建一个读取JSON文件的函数

list           - 列出所有能力
enable <ID>    - 启用能力
disable <ID>   - 禁用能力
info <ID>      - 查看能力详情
status         - 查看系统状态

help           - 显示帮助
quit/exit      - 退出程序
```

## 环境准备

### 必需：设置DeepSeek API密钥

**Windows PowerShell:**
```powershell
$env:DEEPSEEK_API_KEY="your_api_key_here"
python main.py
```

**Windows CMD:**
```cmd
set DEEPSEEK_API_KEY=your_api_key_here
python main.py
```

**Linux/Mac:**
```bash
export DEEPSEEK_API_KEY=your_api_key_here
python main.py
```

### 可选：安装依赖

```bash
pip install -r requirements.txt
```

- `psutil` - 更精准的资源监控
- `requests` - AI API调用
- `filelock` - 文件锁

## 使用场景

### 场景1：让Agent学会文件操作

```bash
prokaryote> evolve 创建一个读取文本文件的函数，支持UTF-8编码
# AI生成代码 -> 安全检查 -> 询问启用 -> 完成

prokaryote> list
# 查看新生成的能力

prokaryote> enable cap_xxxxx
# 启用能力
```

### 场景2：让Agent学会数据处理

```bash
prokaryote> evolve 创建一个统计文本中单词数量和行数的函数

prokaryote> evolve 创建一个解析JSON字符串的函数

prokaryote> list
# 查看所有已学会的能力
```

### 场景3：持续进化

保持程序运行，随时输入新的能力需求，Agent会：
1. 调用AI生成代码
2. 自动安全检查
3. 在沙箱中测试
4. 询问是否启用
5. 记录性能数据

## 进化能力示例

```bash
# 文件操作
prokaryote> evolve 读取文本文件内容
prokaryote> evolve 统计文件行数
prokaryote> evolve 解析CSV文件

# 数据处理
prokaryote> evolve 计算字符串长度
prokaryote> evolve 统计单词频率
prokaryote> evolve JSON格式化输出

# 实用工具
prokaryote> evolve 生成随机密码
prokaryote> evolve 计算文件MD5
prokaryote> evolve Base64编解码
```

## 安全机制

- ✓ 代码自动安全检查（禁止eval/exec/subprocess等）
- ✓ 沙箱隔离执行（进程隔离，资源限制）
- ✓ 默认生成的能力为禁用状态
- ✓ 需要手动启用才能使用
- ✓ 自动性能监控和统计

## 故障排除

### Q: 提示"未设置 DEEPSEEK_API_KEY"

请先设置环境变量后再运行程序。

### Q: AI生成失败

检查：
1. API密钥是否正确
2. 网络连接是否正常
3. DeepSeek API服务是否可用

### Q: 能力生成后无法启用

查看安全等级和安全问题，如果是"danger"级别，说明包含危险操作，已被拒绝。

## 架构说明

```
main.py
  ├─ V0.1 核心功能
  │   ├─ 初始化 (init_prokaryote)
  │   ├─ 监控 (start_prokaryote)
  │   └─ 修复 (自动)
  │
  └─ V0.2 能力扩展
      ├─ AI适配器 (DeepSeek)
      ├─ 能力生成器 (代码生成+安全检查)
      ├─ 沙箱环境 (隔离执行)
      └─ 能力管理器 (注册/启用/调用)
```

## 文件结构

```
prokaryote-agent/
├── main.py                          # 主程序入口
├── prokaryote_agent/
│   ├── api.py                       # 外部接口
│   ├── ai_adapter.py                # AI适配器
│   ├── capability_generator.py      # 能力生成器
│   ├── capability_manager.py        # 能力管理器
│   ├── sandbox.py                   # 沙箱环境
│   ├── capabilities/                # 能力存储目录
│   │   ├── capability_registry.json # 能力注册表
│   │   └── generated_code/          # 生成的代码
│   └── ...
└── ...
```

## 下一步

- 保持程序运行
- 输入 `help` 查看所有命令
- 输入 `evolve <描述>` 开始让Agent进化
- 使用 `list` 查看Agent已经学会的所有能力

# prokaryote-agent 原智

**类生物原始进化型Agent内核**

原智（YuanZhi）- 受原核生物启发的自主进化Agent内核，具备"感知-修复-变异-筛选-复制"完整进化闭环，以人类预设要求为进化指引。

## 当前版本

**V0.1 - 原始存活版本**

核心功能：
- ✅ 状态感知：实时监测内核自身运行状态与环境状态
- ✅ 自我修复：异常检测与自动修复，维持稳定运行
- ✅ 本地存储：基于文件系统的轻量化存储方案
- ✅ 极简接口：4个核心API，简单易用

## 快速开始

### 安装

```bash
# 克隆仓库
git clone <repository-url>
cd prokaryote-agent

# 安装依赖（可选）
pip install -r requirements.txt
```

### 启动原智（推荐方式）⭐

```bash
# 启动原智 - 后台自动进化 + 交互式命令
python start.py

# 自定义配置
python start.py --interval 30 --mode iterative --auto-enable
```

**特性**：
- 🔄 后台持续自动进化（默认60秒间隔）
- 💬 交互式命令界面（status/goals/list/evolve等）
- 📝 完整日志记录（终端 + 文件）
- 🎯 基于 evolution_goals.md 的目标驱动
- 🔁 迭代式多阶段进化（默认模式）
- 🛠️ 实时能力管理和系统监控

**启动后可用命令**：
```
goals           - 查看进化目标状态
evolve <描述>   - 立即生成新能力
list            - 列出所有能力
status          - 查看系统状态
pause/resume    - 暂停/恢复后台进化
help            - 查看所有命令
quit            - 退出程序
```

详见 [启动说明文档](docs/启动说明.md)

### 基础API使用（编程方式）

```python
from prokaryote_agent import init_prokaryote, start_prokaryote, stop_prokaryote, query_prokaryote_state

# 1. 初始化内核
result = init_prokaryote()
if result['success']:
    print("初始化成功")
    
# 2. 启动内核
result = start_prokaryote()
if result['success']:
    print(f"内核启动成功，进程ID: {result['pid']}")
    
# 3. 查询状态
state = query_prokaryote_state()
print(f"当前状态: {state['state']}")

# 4. 停止内核
stop_prokaryote()
```

## 项目结构

```
prokaryote-agent/
├── prokaryote_agent/        # 核心代码包
│   ├── config/              # 配置文件目录
│   │   └── config.json      # 核心配置
│   ├── backup/              # 备份文件目录
│   ├── log/                 # 日志文件目录
│   ├── storage.py           # 存储层（待实现）
│   ├── init_module.py       # 初始化模块（待实现）
│   ├── monitor_module.py    # 状态感知模块（待实现）
│   ├── repair_module.py     # 自我修复模块（待实现）
│   └── api.py               # 外部接口层（待实现）
├── docs/                    # 设计文档
│   ├── PRD.md              # 产品需求文档
│   └── 概要设计.md          # 技术设计文档
└── tests/                   # 测试代码（待实现）
```

## 设计理念

类比原核生物"极简结构、存活优先"的特性：
- **极简架构**：3层设计（存储→核心模块→接口），无复杂中间件
- **存活优先**：V0.1聚焦状态监测与异常修复，确保内核稳定运行
- **轻量可落地**：标准库优先，本地文件存储，目标代码量~500行
- **渐进进化**：V0.2+将引入变异、筛选、复制等进化能力

## 核心指标（V0.1目标）

- 稳定运行故障率 ≤ 2%
- 自我修复成功率 ≥ 95%
- 监测频率：1次/秒
- 修复响应时间 ≤ 500ms

## 开发进度

**V0.1版本（原始存活版）- ✅ 已完成**

- [x] 项目基础结构搭建
- [x] 核心存储层实现
- [x] 初始化模块实现
- [x] 状态感知模块实现
- [x] 自我修复模块实现
- [x] 外部接口层实现
- [x] 集成测试
- [x] 文档完善
- [x] **验收测试通过** ✅

**V0.2版本（AI进化版）- ✅ 核心完成**

- [x] AI适配器（DeepSeek API集成）
- [x] 能力生成器（代码生成+安全检查）
- [x] 测试验证（自动生成测试+沙箱执行）
- [x] 目标驱动进化模式
- [x] **迭代式进化系统**（多阶段渐进式开发）
- [x] **混合进化模式**（后台自动 + 人工指引）
- [x] 能力复用机制
- [x] 自动优化现有能力
- [ ] 能力评估与淘汰

查看 [V0.1验收报告](tests/V0.1_ACCEPTANCE_REPORT.md)

## 进化系统

### 统一入口：start.py ⭐ 推荐

原智现在使用统一的 `start.py` 作为主入口，集成了：
- 后台持续进化线程
- 交互式命令界面
- 迭代式多阶段进化
- 完整日志记录

```bash
# 启动原智（默认迭代模式）
python start.py

# 查看所有选项
python start.py --help
```

### 进化模式

#### 迭代式进化（Iterative）- 默认推荐

多阶段渐进式开发，适合复杂功能：

- **简单功能**：1个阶段（直接完成）
- **中等功能**：3个阶段（基础→核心→扩展）
- **复杂功能**：4个阶段（基础→核心→扩展→完善）

**优势**：
- ✅ 成功率显著提升（复杂功能从0%→67%）
- ✅ 自动分阶段执行
- ✅ 每阶段独立验证和反馈
- ✅ 支持复用已有能力

#### 简单模式（Simple）

传统一次性生成，适合简单明确的功能。

### 定义目标

编辑项目根目录下的 `evolution_goals.md` 文件：

```markdown
# 我的能力目标

**状态**: pending  
**优先级**: high  
**描述**: 详细描述你想要的能力

**验收标准**:
- [ ] 需求1
- [ ] 需求2
- [ ] 需求3
```

### 运行方式

**方式1：混合模式（推荐）**

```bash
python start.py
# 后台自动执行 + 随时手动控制
prokaryote> goals      # 查看进度
prokaryote> evolve 实现JSON解析  # 插队任务
prokaryote> pause      # 暂停后台
```

**方式2：纯自动模式**

```bash
python goal_evolution.py --mode iterative
# 按顺序执行所有目标直到完成
```

## 文档

- [启动说明文档](docs/启动说明.md) ⭐ **推荐阅读**
- [系统合并说明](docs/系统合并说明.md) - 新旧系统对比
- [迭代式进化设计](docs/迭代式进化设计.md) - 技术架构
- [产品需求文档 (PRD)](docs/PRD.md)
- [概要设计文档](docs/概要设计.md)
- [AI编码规范](.github/copilot-instructions.md)

## 技术栈

- Python 3.8+（推荐3.13）
- 标准库：os, sys, threading, json, logging
- 可选库：psutil（资源监控），filelock（文件锁）

## 许可证

待定

## 联系方式

待定

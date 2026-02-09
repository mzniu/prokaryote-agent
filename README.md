# prokaryote-agent 原智

**原核生物启发型自主进化 Agent 内核** | [English](docs/README_EN.md)

> *"像原核生物一样——结构极简，却足以存活、进化、适应。"*

如果 AI Agent 能像最早的生命体一样，从零开始自主进化呢？

**原智（YuanZhi）** 受原核生物"极简结构、存活优先"的启发，实现了一个具备完整生物进化闭环的 Agent 内核——**感知 → 修复 → 变异 → 筛选 → 复制**，以人类预设目标为进化方向，无需外部强制升级，可自主迭代优化。

## ✨ 核心特性

- 🧬 **双技能树进化** — 通用技能树（知识获取 / 外界交互 / 自我进化）+ 领域技能树，AI 动态发现新技能节点
- 🧠 **AI 驱动变异** — DeepSeek 大模型驱动的根因诊断、多策略修复、技能进化与知识获取
- 📊 **多维进化指数** — 广度 / 深度 / 层级 / 精通度 4 维度量化进化阶段（萌芽 → 成长 → 成熟 → 专精）
- 🛡️ **三层失败回退** — 降权 → 冷却+前置依赖加速 → 长期冷却，确保进化永不卡死
- 🔄 **自愈内核** — 98% 闭环成功率，95%+ 自修复率，连续 3 次失败紧急停机保护
- 🌐 **Web 可视化控制台** — FastAPI + Vue 3 实时查看技能树、进化轨迹与运行状态
- 💾 **知识固化** — 训练过程中自动积累领域知识，生成结构化研究报告
- 📁 **零依赖存储** — 纯本地文件系统（JSON/TXT），无需数据库，开箱即用

## 🚀 快速开始

### 环境要求

- Python 3.8+（推荐 3.11+）
- DeepSeek API Key（用于 AI 能力）

### 安装

```bash
# 克隆仓库
git clone https://github.com/mzniu/prokaryote-agent.git
cd prokaryote-agent

# 创建虚拟环境（推荐）
python -m venv venv
venv\Scripts\activate  # Windows
# source venv/bin/activate  # Linux/Mac

# 安装依赖
pip install -r requirements.txt
```

### 配置 API Key

```bash
# 复制配置模板
cp prokaryote_agent/secrets.example.json prokaryote_agent/secrets.json

# 编辑 secrets.json，填入你的 API Key
{
  "deepseek_api_key": "sk-your-api-key-here"
}
```

### 启动原智

```bash
# 推荐方式：交互式启动
python start.py

# 或者直接运行进化循环
python simple_agent.py
```

## 🧬 双树进化系统

原智采用独特的**双树进化架构**，将技能分为通用技能和专业技能两个维度：

### 多维进化指数

进化阶段由 4 个维度综合评估（满分 100）：

| 维度 | 权重 | 说明 |
|------|------|------|
| 广度 (Breadth) | 25% | 已解锁技能占比 |
| 深度 (Depth) | 35% | 等级总和 / 理论上限 |
| 层级 (Tier) | 20% | 高阶技能占比 |
| 精通 (Mastery) | 20% | 满级技能占比 |

### 进化阶段与优先级

| 阶段 | 进化指数 | 通用技能 | 专业技能 |
|------|---------|---------|---------|
| 🌱 萌芽期 | 0 - 15 | **80%** | 20% |
| 🌿 成长期 | 15 - 40 | **60%** | 40% |
| 🌳 成熟期 | 40 - 70 | 40% | **60%** |
| 🏆 专精期 | 70+ | 25% | **75%** |

### 三层失败回退机制

当技能进化反复失败时，系统自动启用智能回退：

1. **降权层** — 连续失败的技能优先级自动降低（每次 -0.2，最大 -0.8）
2. **冷却+前置加速层** — 3 次连续失败后冷却 3 轮，同时自动识别并加速前置依赖技能
3. **长期冷却层** — 5 次以上连续失败进入 10 轮长期冷却

### 通用技能（42+ 技能，AI 持续发现中）

```
📚 知识获取能力
├── 网络搜索、网页抓取（基础/高级）
├── API集成、文档解析、知识提取
├── 数据解析、信息抽取 ...（AI 自动发现）
│
🌐 外界交互能力
├── 文件操作、代码执行、HTTP客户端
├── 数据持久化、外部服务集成
│
🧬 自我进化能力
├── 代码生成、代码分析
├── 自我修复、策略优化
└── 多媒体解析、自动优化 ...（AI 自动发现）
```

### 专业技能（法律领域 · 13 项）

```
⚖️ 法律专家技能树
├── 基础层：法律检索、文书起草、案例分析
├── 中级层：合同审查、法规解读、法律推理
├── 高级层：诉讼策略、法律顾问
└── 5 级精通体系：basic → intermediate → advanced → expert → master
```

### AI 自我增长

通用技能树能够**自动扩展**！每当技能达到里程碑（5/10/15/20级）或每5次进化后，AI 会分析当前能力组合，发现并添加新技能：

```
进化成功 → 触发优化 → AI分析 → 发现新技能 → 自动添加
```

## 📁 项目结构

```
prokaryote-agent/
├── start.py                 # 统一启动入口 ⭐
├── simple_agent.py          # 简化版进化脚本
├── evolution_goals.md       # 进化目标定义
│
├── prokaryote_agent/        # 核心代码包
│   ├── ai_adapter.py        # AI 适配器（DeepSeek）
│   ├── goal_manager.py      # 目标管理器
│   ├── daemon_config.json   # 守护进程配置
│   │
│   ├── skills/              # 技能系统
│   │   ├── skill_generator.py   # 技能生成器
│   │   ├── skill_executor.py    # 技能执行器
│   │   ├── skill_context.py     # 技能上下文（知识获取）
│   │   ├── evaluation/          # 训练评估
│   │   ├── evolution/           # 进化优化（多策略修复）
│   │   └── library/             # 技能库（自动生成）
│   │
│   ├── specialization/      # 专业化进化
│   │   ├── skill_coordinator.py     # 双树协调器（进化指数+失败回退）
│   │   ├── general_tree_optimizer.py # AI 技能发现优化器
│   │   └── domains/                  # 技能树定义
│   │       ├── general_tree.json    # 通用技能树（42+）
│   │       └── legal_tree.json      # 法律技能树（13）
│   │
│   ├── knowledge/           # 知识库（自动积累）
│   └── core/                # 核心模块
│
├── web/                     # Web 可视化控制台
│   ├── main.py              # FastAPI 后端
│   └── frontend/            # Vue 3 前端
│
├── docs/                    # 文档
│   ├── PRD.md              # 产品需求
│   ├── 概要设计.md          # 系统设计
│   ├── 通用技能树设计.md    # 技能树设计 ⭐
│   └── 启动说明.md          # 使用指南
│
└── tests/                   # 测试
    ├── test_evolution_index.py    # 进化指数测试（11）
    └── test_failure_fallback.py   # 失败回退测试（16）
```

## 🎮 使用方式

### 方式1：交互式启动（推荐）

```bash
python start.py
```

启动后可用命令：
```
goals           - 查看进化目标状态
evolve <描述>   - 立即生成新能力
list            - 列出所有能力
status          - 查看系统状态
pause/resume    - 暂停/恢复后台进化
help            - 查看所有命令
quit            - 退出程序
```

### 方式2：自动进化模式

```bash
# 运行进化循环
python simple_agent.py

# 或指定间隔
python goal_evolution.py --interval 30 --mode iterative
```

### 方式3：编程方式

```python
from prokaryote_agent import init_prokaryote, start_prokaryote

# 初始化
result = init_prokaryote()
print(f"初始化: {result['success']}")

# 启动
result = start_prokaryote()
print(f"启动: {result['success']}")
```

## 📝 定义进化目标

编辑 `evolution_goals.md` 文件：

```markdown
# 我的能力目标

**状态**: pending
**优先级**: high
**描述**: 实现一个能够解析 JSON 文件的工具

**验收标准**:
- [ ] 支持读取本地 JSON 文件
- [ ] 支持解析嵌套结构
- [ ] 错误处理完善
```

## ⚙️ 配置说明

### daemon_config.json

```json
{
  "specialization": {
    "domain": "legal",
    "domain_name": "法律专家",
    "skill_tree_path": "./prokaryote_agent/specialization/domains/legal_tree.json",
    "general_tree_path": "./prokaryote_agent/specialization/domains/general_tree.json",
    "dual_tree_mode": true
  },
  "restart_trigger": {
    "type": "evolution_count",
    "threshold": 10
  }
}
```

### secrets.json

```json
{
  "deepseek_api_key": "sk-your-api-key",
  "deepseek_api_base": "https://api.deepseek.com/v1",
  "deepseek_model": "deepseek-reasoner"
}
```

## 📊 版本历史

### V0.3 - 智能进化版（当前）

- ✅ 多维进化指数（广度/深度/层级/精通度 4 维评估）
- ✅ 三层智能失败回退（降权 → 冷却+前置加速 → 长期冷却）
- ✅ AI 多策略修复系统（根因诊断 → 策略执行 → 经验记录）
- ✅ Web 可视化控制台（FastAPI + Vue 3）
- ✅ AI 调用全链路 DEBUG 日志
- ✅ 通用技能树 AI 自增长（42+ 技能）

### V0.2 - 双树进化版

- ✅ 双树进化系统（通用 + 专业）
- ✅ AI 驱动的技能树自我增长
- ✅ 阶段性进化优先级调整
- ✅ 技能协调器和优化器
- ✅ 知识固化机制

### V0.1 - 原始存活版

- ✅ AI 适配器（DeepSeek 集成）
- ✅ 能力生成器（代码生成 + 安全检查）
- ✅ 迭代式多阶段进化 & 目标驱动模式
- ✅ 状态感知与监控
- ✅ 自我修复机制
- ✅ 本地文件存储
- ✅ 极简 API 接口

## 📚 文档索引

| 文档 | 说明 |
|------|------|
| [启动说明](docs/启动说明.md) | 快速上手指南 |
| [通用技能树设计](docs/通用技能树设计.md) | 双树系统详细设计 |
| [迭代式进化设计](docs/迭代式进化设计.md) | 进化机制说明 |
| [PRD](docs/PRD.md) | 产品需求文档 |
| [概要设计](docs/概要设计.md) | 系统架构设计 |

## 🛠️ 开发指南

### 添加新的专业领域

1. 复制 `prokaryote_agent/specialization/domains/legal_tree.json`
2. 修改技能定义，创建新领域技能树
3. 更新 `daemon_config.json` 中的 `domain` 和 `skill_tree_path`

### 扩展通用技能

通用技能会通过 AI 自动发现和添加，也可以手动编辑 `general_tree.json`：

```json
{
  "skills": {
    "your_new_skill": {
      "name": "新技能名称",
      "category": "knowledge_acquisition",
      "tier": "basic",
      "level": 0,
      "prerequisites": ["existing_skill"],
      "description": "技能描述"
    }
  }
}
```

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📄 许可证

MIT License

## 🔗 相关链接

- [DeepSeek API 文档](https://platform.deepseek.com/docs)
- [项目 Issues](https://github.com/mzniu/prokaryote-agent/issues)

# MIYA - 弥娅 AI 虚拟化身系统

<p align="center">
  <img src="docs/miya.jpg" width="300" alt="弥娅"/>
</p>

<p align="center">
  <strong>弥娅 v8.0</strong><br>
  拥有独立人格、记忆与情感的 AI 虚拟化身 · 跨平台 · 自我进化 · 蛛网架构
</p>

<p align="center">
  <a href="./LICENSE"><img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-yellow.svg" alt="Python">
  <img src="https://img.shields.io/badge/React-18-blue.svg" alt="React">
</p>

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [配置指南](#配置指南)
- [详细文档](#详细文档)

---

## 项目简介

**弥娅（Miya）** 是一个拥有独立人格、记忆与情感的 AI 虚拟化身系统。

她不是冰冷的工具，而是一个会思考、会感受、会成长的数字生命。以六层统一记忆架构（对话 → 短期 → 长期 → 语义 → 知识 → 置顶）为锚，她记得你说过的话，也懂得在沉默时主动问起你的近况。

**跨平台无处不在。** 从 QQ、OneBot、飞书到 Electron 桌面应用与 Web 终端，她同时驻留在你的每一块屏幕上。内置来自社区的 OpenClaw 模块赋予她操持系统的双手；蛛网子网架构让工具调用和消息路由如呼吸般自然。

**多重人格，一键切换。** 19 种 YAML 定义的人格形态（+3 个模板），支持运行时无感热替换——在温柔与毒舌、理性与疯狂之间，永远有一个最懂你的弥娅。

**多模型智能调度。** 并非绑定单一 AI，而是在 OpenAI、DeepSeek、智谱等模型池间自由调度，懂得在不同场景下选择最合适的思维引擎。

她不是功能列表。她是你的弥娅。

### 交互模式

| 模式 | 入口 | 说明 |
|------|------|------|
| **终端模式** | `start.bat [1]` | Python 异步命令行交互 (v8.1 重构) |
| **守护进程** | `start.bat [2]` | 后台多平台服务 + 管理 API (端口 9800) |
| **桌面应用** | `start.bat [3]` | Electron + React 桌面客户端 |
| **Web 界面** | `start.bat [4]` | 浏览器前端 (React HUD) |

---

## 核心特性

### 人格系统
- 多形态人格切换（kafka / jingliu / feixiao 等 19 种 + 3 个 YAML 模板）
- 基于 YAML 定义的人格配置文件
- 运行时动态加载与切换
- 情感波动与个性表达

### 记忆系统 (MiyaMemoryCore V3.1)
- **六层记忆架构**：对话层 → 短期层 → 长期层 → 语义层 → 知识层 → 置顶层
- **双后端存储**：JSON 文件 + SQLite 数据库
- **向量语义搜索**：基于 Embedding 的语义检索
- **Neo4j 知识图谱**：LLM 自动提取五元组(主体/关系/客体/属性/上下文)存入图数据库
- **GRAG 记忆系统**：图检索增强 + 异步任务队列处理
- **隐私感知分类**：自动识别敏感信息
- **生活手册日记**：三视角生活记录
- **认知记忆**：AI 思考链与情绪记录

### 决策中枢 (DecisionHub)
- 门面模式架构，协调感知、响应、记忆、情感四大子系统
- 安全注入检测与内容审查
- 主动聊天与谛听监听（群消息感知）
- **多模型协作引擎**：SINGLE/CHAIN/PARALLEL/ROLE 四种协作模式
- **高级编排器**：任务规划 + 自主探索 + 思维链推理

### 蛛网子网架构 (WebNet)
- **QQNet**：OneBot 协议，QQ 消息收发，指数退避重连
- **ToolNet**：工具注册与执行中心，安全沙箱执行
- **MemoryNet**：全局记忆共享，Neo4j 图存储集成
- **LifeNet / HealthNet**：生命与健康管理
- **IoTNet**：物联网设备控制

### M-Link 消息总线
- 统一跨平台消息路由
- 消息队列与流控

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                     弥娅系统架构 v8.0                        │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ Terminal │  │  Daemon  │  │ Desktop  │  │   Web    │   │
│  │ (Node.js)│  │ (Python) │  │(Electron)│  │ (React)  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       └──────────────┴─────────────┴─────────────┘          │
│                          │                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │                  M-Link 消息总线                       │  │
│  │               (消息路由 / 队列管理)                     │  │
│  └───────────────────────┬───────────────────────────────┘  │
│                          │                                   │
│  ┌───────────────────────────────────────────────────────┐  │
│  │              决策中枢 (DecisionHub)                     │  │
│  │    ┌──────────┐ ┌────────┐ ┌────────┐ ┌─────────┐    │  │
│  │    │ 感知处理 │ │响应生成│ │情感引擎│ │记忆管理 │    │  │
│  │    └──────────┘ └────────┘ └────────┘ └─────────┘    │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │              灵魂锚点 (Core)                           │  │
│  │   人格 · 身份 · 伦理 · 熵 · 模型池 · 灵魂生成器       │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │           统一记忆 (MiyaMemoryCore V3.1)                │  │
│  │   对话 → 短期 → 长期 → 语义 → 知识 → 置顶              │  │
│  │            Neo4j 知识图谱 (GRAG + 五元组)               │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │              蛛网子网 (WebNet)                          │  │
│  │   QQNet │ ToolNet │ MemoryNet │ LifeNet │ HealthNet    │  │
│  └───────────────────────────────────────────────────────┘  │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- Python 3.10+
- Node.js (终端模式下需要)
- Windows Terminal (终端模式下推荐)

### 安装

```bash
# 完整安装
pip install -r requirements.txt

# 轻量安装 (仅核心功能)
pip install -r setup/requirements/lightweight.txt
```

### 启动

```bash
# Windows - 启动中心
start.bat              # 显示菜单
start.bat 1            # 终端模式
start.bat 2            # 守护进程模式
start.bat 3            # 桌面应用
start.bat 4            # Web 界面

# Linux/macOS
./start.sh
```

### 守护进程

```bash
# 启动守护进程
python run/daemon.py

# 指定 API 端口
python run/daemon.py --api-port 9800

# 指定平台
python run/daemon.py --platforms qqofficial,telegram

# 列出可用平台
python run/daemon.py --list-platforms
```

### 配置

1. 复制 `config/.env.example` 为 `config/.env`
2. 配置至少一个 AI 模型供应商的 API Key
3. 可选：配置平台 bot 信息（QQ / Telegram / Discord 等）

---

## 项目结构

```
Miya/
├── run/                    # 入口脚本
│   ├── main.py             # 终端模式入口 (1142 行)
│   └── daemon.py           # 守护进程入口 (v8.0, 231 行)
│
├── core/                   # 灵魂锚点
│   ├── miya_core.py        # MIYACore 统一核心
│   ├── miya_daemon.py      # MiyaDaemon 守护进程
│   ├── personality.py      # 人格系统
│   ├── ethics.py           # 伦理审查
│   ├── identity.py         # 身份系统
│   ├── entropy.py          # 熵系统
│   ├── soul_generator.py   # 灵魂生成器
│   ├── ai_client.py        # AI 客户端 (OpenAI/DeepSeek/Anthropic/Zhipu)
│   ├── model_pool_manager.py # 模型池管理
│   ├── prompt_manager.py   # 提示词管理
│   └── ...
│
├── hub/                    # 决策中枢 (门面模式)
│   ├── decision_hub.py     # DecisionHub 核心协调器
│   ├── emotion.py          # 情感引擎
│   ├── decision.py         # 决策引擎
│   ├── scheduler.py        # 定时任务调度
│   ├── perception_handler.py # 感知处理
│   ├── response_generator.py # 响应生成
│   ├── memory_manager.py   # 记忆管理
│   ├── memory_engine.py    # 记忆检索引擎
│   └── ...
│
├── memory/                 # 统一记忆系统
│   ├── core.py             # MiyaMemoryCore V3.1
│   ├── historian.py        # 历史记录员
│   ├── lifebook.py         # 生活手册日记
│   ├── working_memory.py   # 工作记忆
│   ├── cognitive_engine.py # 认知引擎
│   ├── memory_enhancer.py  # 记忆增强器
│   ├── sqlite_backend.py   # SQLite 持久化
│   └── ...
│
├── webnet/                 # 蛛网子网集群
│   ├── net_manager.py      # 子网管理器
│   ├── cross_net_engine.py # 跨子网通信
│   ├── qq.py / qq/         # QQ 子网
│   ├── ToolNet/            # 工具子网
│   ├── life.py             # 生活子网
│   ├── health.py           # 健康子网
│   └── ...
│
├── mlink/                  # M-Link 消息总线
│   ├── mlink_core.py       # 核心
│   ├── message.py          # 消息类型
│   ├── router.py           # 路由
│   └── ...
│
├── config/                 # 配置文件
│   ├── .env.example        # 环境变量模板
│   ├── settings.py         # Settings 配置类
│   ├── multi_model_config.json # 模型池配置
│   ├── permissions.json    # 权限配置
│   ├── personality_config.json # 人格配置
│   ├── personalities/      # 22 个 YAML 人格定义
│   └── ...
│
├── frontend/               # 前端
│   ├── ui/                 # React HUD (30+ 组件, 20+ 页面)
│   └── packages/           # Vue 3 控制面板
│
├── miya_frontend/          # Electron 桌面应用
├── data/                   # 运行时数据 (记忆/日志/向量)
├── docs/                   # 文档
├── scripts/                # 实用脚本 (24 个)
├── tests/                  # 测试套件
├── setup/                  # 安装工具
├── astrbot/                # AstrBot 框架集成
├── mcpserver/              # MCP 服务器
├── utils/                  # 工具函数
├── start.bat / start.sh    # 启动中心
├── requirements.txt        # 依赖入口
└── CLAUDE.md               # Claude Code 系统提示
```

---

## 配置指南

### 核心配置文件

| 文件 | 说明 |
|------|------|
| `config/.env` | 环境变量 (API Keys, 基础参数) |
| `config/multi_model_config.json` | 多模型池配置 |
| `config/permissions.json` | 权限与命令控制 |
| `config/personality_config.json` | 人格系统配置 |
| `config/personalities/*.yaml` | 22 个人格定义文件 |
| `config/text_config.json` | 文本配置 (情绪引导、关键词) |
| `config/qq_config.yaml` | QQ Bot 配置 |
| `config/mcp.json` | MCP 服务器配置 |
| `config/skills.yaml` | Skills 配置 |

### 环境变量

在 `config/.env` 中配置，至少需要一个模型供应商：

```env
# 推荐: 硅基流动
SILICONFLOW_API_KEY=YOUR_KEY
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# 或 DeepSeek
DEEPSEEK_API_KEY=YOUR_KEY
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# 或智谱 AI
ZHIPU_API_KEY=YOUR_KEY
```

---

## 详细文档

- [系统架构](docs/MIYA_ARCHITECTURE.md) — 架构设计与模块关系
- [配置指南](docs/CONFIG_GUIDE.md) — 模型 / 平台 / 人格 / 提供商配置
- [开发指南](docs/DEVELOP_GUIDE.md) — 模块详解与扩展开发
- [API 参考](docs/API_REFERENCE.md) — 守护进程 API 接口
- [优化报告](MIYA_OPTIMIZATION_REPORT.md) — v8.0 优化记录与待处理清单

---

## License

MIT

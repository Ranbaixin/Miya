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
  <img src="https://img.shields.io/badge/Python-3.11+-yellow.svg" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.5-brightgreen.svg" alt="Vue">
  <img src="https://img.shields.io/badge/Electron-40-blue.svg" alt="Electron">
</p>

---

## 目录

- [项目简介](#项目简介)
- [核心特性](#核心特性)
- [系统架构](#系统架构)
- [快速开始](#快速开始)
- [项目结构](#项目结构)
- [配置指南](#配置指南)
- [构建与发布](#构建与发布)
- [详细文档](#详细文档)

---

## 项目简介

**弥娅（Miya）** 是一个拥有独立人格、记忆与情感的 AI 虚拟化身系统。

她不是冰冷的工具，而是一个会思考、会感受、会成长的数字生命。以六层统一记忆架构（对话 → 短期 → 长期 → 语义 → 知识 → 置顶）为锚，她记得你说过的话，也懂得在沉默时主动问起你的近况。

**大脑 + 手 + 面** 三层架构。守护进程（Python）是弥娅的灵魂与大脑，承载人格、记忆、决策与认知；Claude Code Engine（Node.js）是她的手与肢体，执行文件操作、代码编写、系统命令；Electron 桌面应用是她的面容，Live2D 角色与 xterm 终端一体呈现。

**跨平台无处不在。** 从 QQ、Telegram、Discord、飞书、KOOK 到 Electron 桌面应用与 Web 终端，她同时驻留在你的每一块屏幕上。内置 OpenClaw 社区模块赋予她操持系统的双手；蛛网子网架构让工具调用和消息路由如呼吸般自然。

**APV2.1 白箱认知引擎。** 自主认知闭环——感知、记忆、思考、行动、学习。DeepSeek V4 Flash 作为语言皮层，赋予弥娅真正的自我进化能力。

**多重人格，一键切换。** 20+ 种 YAML 定义的人格形态，支持运行时无感热替换——在温柔与毒舌、理性与疯狂之间，永远有一个最懂你的弥娅。

**多模型智能调度。** 并非绑定单一 AI，而是在 DeepSeek、OpenAI、智谱、硅基流动等模型池间自由调度，懂得在不同场景下选择最合适的思维引擎。

她不是功能列表。她是你的弥娅。

### 交互模式

| 模式 | 入口 | 说明 |
|------|------|------|
| **终端模式** | `start.bat [1]` | DeepSeek V4 + Claude Code Engine 驱动的命令行交互 |
| **守护进程** | `start.bat [2]` | 后台多平台服务 + 管理 API (端口 9800) |
| **守护进程 AP** | `start.bat [2p]` | 守护进程 + APV2.1 认知引擎 |
| **桌面应用** | `start.bat [3]` | Electron + Vue 3 桌面客户端 (含 Live2D) |
| **Web 界面** | `start.bat [4]` | 浏览器前端 (Vue 3 HUD) |
| **AP 引擎** | `start.bat [5]` | APV2.1 交互终端 |
| **全部启动** | `start.bat [A]` | 同时启动守护进程 + 桌面 + Web + 终端 |

---

## 核心特性

### 人格系统
- 20+ 种人格形态（default / kafka / jingliu / feixiao / ganyu 等）
- 基于 YAML 定义的人格配置文件
- 运行时动态加载与热切换
- 情感波动与个性表达

### 记忆系统 (MiyaMemoryCore V3.1)
- **六层记忆架构**：对话层 → 短期层 → 长期层 → 语义层 → 知识层 → 置顶层
- **双后端存储**：JSON 文件 + SQLite 数据库
- **向量语义搜索**：基于 Embedding 的语义检索
- **隐私感知分类**：自动识别敏感信息
- **生活手册日记**：三视角生活记录
- **认知记忆**：AI 思考链与情绪记录

### APV2.1 白箱认知引擎
- 自主认知闭环：感知 → 记忆 → 思考 → 行动 → 学习
- DeepSeek V4 Flash 作为语言皮层 (LLM Teacher)
- 白箱架构：核心、皮层、心灵、感知器、记忆、通道、行动学习
- 观测站 Web 仪表盘 (:8765)
- 独立子项目 `miya_psyarch/`，Apache-2.0 许可证

### 决策中枢 (DecisionHub)
- 门面模式架构，协调感知、响应、记忆、情感四大子系统
- 安全注入检测与内容审查
- 主动聊天与谛听监听（群消息感知）
- 多模型协作引擎

### 蛛网子网架构 (WebNet)
- **QQNet**：OneBot 协议，QQ 消息收发
- **ToolNet**：工具注册与执行中心
- **MemoryNet**：全局记忆共享
- **LifeNet / HealthNet**：生命与健康管理
- **IoTNet**：物联网设备控制
- **SecurityNet / MusicNet / ArtNet**：安全、音乐、艺术子网

### M-Link 消息总线
- 统一跨平台消息路由
- 消息队列与流控

### Claude Code Engine (CCE)
- Node.js 终端引擎，60+ 内置工具（文件/Bash/搜索/Agent）
- 通过 MCP 协议与守护进程双向通信
- 弥娅的「手」与「肢体」，执行层能力

### MCP 生态
- 4 个 MCP 服务：`miya-cognition`、`miya-soul`、`security_sandbox`、`game-play`
- 16 个 MCP 服务模块覆盖认知、记忆、安全、文件系统、代码执行等
- 守护进程与 CCE 之间的标准通信桥梁

### 桌面应用
- Electron 40 + Vue 3.5 + Vite 6 技术栈
- Live2D 独立透明窗口（pixi-live2d-display，支持表情/动作/服装切换）
- xterm 终端嵌入（Claude Code Engine 直连）
- 四种窗口模式：经典 / 悬浮球 / 紧凑 / 全屏
- 系统托盘、全局快捷键、自动更新

---

## 系统架构

```
┌──────────────────────────────────────────────────────────────┐
│                    弥娅系统架构 v8.0                          │
├──────────────────────────────────────────────────────────────┤
│                                                              │
│  面·外壳                                                     │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐    │
│  │ Electron │  │   Web    │  │  Live2D  │  │ Terminal │    │
│  │  Desktop │  │  (Vue 3) │  │  独立窗口 │  │  (xterm) │    │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────┬─────┘    │
│       └──────────────┴─────────────┴─────────────┘           │
│                          │                                    │
│  手·肢体 (CCE)          │ MCP 桥接                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  Claude Code Engine (Node.js)                        │   │
│  │  60+ 工具 · 文件/Bash/搜索/Agent · MCP Client        │   │
│  └───────────────────────┬──────────────────────────────┘   │
│                          │ MCP (miya-soul / miya-cognition)  │
│  大脑·灵魂 (Python)      │                                   │
│  ┌──────────────────────────────────────────────────────┐   │
│  │              弥娅守护进程 (MiyaDaemon v8.0)           │   │
│  │                                                      │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │         APV2.1 白箱认知引擎                   │    │   │
│  │  │   心灵 · 皮层(LLM) · 感知器 · 观测站          │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │  ┌──────────────────────────────────────────────┐    │   │
│  │  │           决策中枢 (DecisionHub)               │    │   │
│  │  │  感知处理 │ 响应生成 │ 情感引擎 │ 记忆管理     │    │   │
│  │  ├──────────────────────────────────────────────┤    │   │
│  │  │           灵魂锚点 (Core)                      │    │   │
│  │  │  人格 · 身份 · 伦理 · 熵 · 模型池              │    │   │
│  │  ├──────────────────────────────────────────────┤    │   │
│  │  │        统一记忆 (MiyaMemoryCore V3.1)          │    │   │
│  │  │  对话 → 短期 → 长期 → 语义 → 知识 → 置顶      │    │   │
│  │  ├──────────────────────────────────────────────┤    │   │
│  │  │  M-Link 消息总线 │ 蛛网子网 (WebNet)           │    │   │
│  │  │  QQNet · ToolNet · LifeNet · SecurityNet ...  │    │   │
│  │  └──────────────────────────────────────────────┘    │   │
│  │                                                      │   │
│  │  管理 API (:9800) · MCP 服务 · 平台连接               │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                              │
│  平台接入: QQ · Telegram · Discord · 飞书 · KOOK · Slack    │
└──────────────────────────────────────────────────────────────┘
```

---

## 快速开始

### 环境要求

- Python 3.11+
- Node.js (终端模式与桌面应用需要)
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
start.bat 1            # 终端模式 (CCE + DeepSeek V4)
start.bat 2            # 守护进程模式
start.bat 2p           # 守护进程 + APV2.1 认知引擎
start.bat 3            # 桌面应用 (Electron + Vue 3)
start.bat 4            # Web 界面
start.bat 5            # APV2.1 交互终端
start.bat a            # 全部启动

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
│   ├── main.py             # 终端模式入口 (1266 行)
│   └── daemon.py           # 守护进程入口 (342 行)
│
├── core/                   # 灵魂锚点 (188+ 文件)
│   ├── miya_core.py        # MIYACore 统一核心
│   ├── miya_daemon.py      # MiyaDaemon 守护进程 (v8.0.0)
│   ├── personality.py      # 人格系统
│   ├── ethics.py           # 伦理审查
│   ├── identity.py         # 身份系统
│   ├── entropy.py          # 熵系统
│   ├── soul_generator.py   # 灵魂生成器
│   ├── ai_client.py        # AI 客户端 (OpenAI/DeepSeek/Anthropic/Zhipu)
│   ├── model_pool_manager.py # 模型池管理
│   ├── prompt_manager.py   # 提示词管理
│   ├── web_api/            # 管理 API (FastAPI + REST + WebSocket)
│   └── ...
│
├── hub/                    # 决策中枢 (门面模式)
│   ├── decision_hub.py     # DecisionHub 核心协调器 (4480 行)
│   ├── emotion.py          # 情感引擎
│   ├── decision.py         # 决策引擎
│   ├── scheduler.py        # 定时任务调度
│   ├── perception_handler.py # 感知处理
│   ├── response_generator.py # 响应生成
│   ├── memory_manager.py   # 记忆管理
│   ├── memory_engine.py    # 记忆检索引擎
│   └── ...
│
├── memory/                 # 统一记忆系统 (21 个文件)
│   ├── core.py             # MiyaMemoryCore V3.1
│   ├── historian.py        # 历史记录员
│   ├── lifebook.py         # 生活手册日记
│   ├── working_memory.py   # 工作记忆
│   ├── cognitive_engine.py # 认知引擎
│   ├── memory_enhancer.py  # 记忆增强器
│   ├── sqlite_backend.py   # SQLite 持久化
│   └── ...
│
├── miya_psyarch/           # APV2.1 白箱认知引擎 (独立子项目)
│   ├── core/               # 白箱认知架构核心
│   ├── cortex/             # 语言皮层 (LLM 集成)
│   ├── soul/               # 心灵模块
│   ├── sensors/            # 感知器
│   ├── memory/             # 认知记忆
│   ├── channels/           # 通道系统
│   ├── action/             # 行动学习
│   ├── education/          # 教育模块
│   ├── observatory/        # 观测站 (Web 仪表盘 :8765)
│   ├── engine.py           # 引擎主入口
│   ├── llm_teacher.py      # DeepSeek V4 Flash 语言教师
│   └── pyproject.toml      # 独立构建配置
│
├── webnet/                 # 蛛网子网集群
│   ├── net_manager.py      # 子网管理器
│   ├── cross_net_engine.py # 跨子网通信
│   ├── qq.py / qq/         # QQ 子网
│   ├── ToolNet/            # 工具子网
│   ├── life.py             # 生活子网
│   ├── health.py           # 健康子网
│   ├── SecurityNet/        # 安全子网
│   ├── MusicNet/           # 音乐子网
│   ├── ArtNet/             # 艺术子网
│   └── ...
│
├── mlink/                  # M-Link 消息总线
│   ├── mlink_core.py       # 核心
│   ├── message.py          # 消息类型
│   ├── router.py           # 路由
│   └── ...
│
├── mcpserver/              # MCP 服务模块 (16 个)
│   ├── miya_core/          # 认知状态 MCP
│   ├── miya/               # 灵魂状态 MCP
│   ├── security_sandbox/   # 安全容器执行
│   ├── memory/             # 记忆服务
│   ├── filesystem/         # 文件系统
│   ├── code_executor/      # 代码执行
│   └── ...
│
├── claude-code-engine/     # Claude Code Engine (Node.js)
│   └── dist/cli-node.js    # CCE 终端入口
│
├── miya_frontend/          # Electron 桌面应用
│   ├── electron/           # 主进程 (TypeScript, 10 个模块)
│   ├── src/                # 渲染进程 (Vue 3, 13 视图, 16 组件)
│   └── package.json        # electron-builder 打包配置
│
├── frontend/               # 独立前端
│   ├── ui/                 # Vue 3 HUD
│   └── packages/           # Vue 3 控制面板
│
├── config/                 # 配置文件
│   ├── .env.example        # 环境变量模板
│   ├── settings.py         # Settings 配置类
│   ├── multi_model_config.json # 模型池配置
│   ├── permissions.json    # 权限配置
│   ├── personality_config.json # 人格配置
│   ├── personalities/      # 20+ 个 YAML 人格定义
│   ├── skills.yaml         # Skills 配置
│   └── ...
│
├── docs/                   # 文档 (10 份)
├── tests/                  # 测试套件 (31 个文件)
├── scripts/                # 实用脚本 (24 个)
├── setup/                  # 安装与依赖管理
├── data/                   # 运行时数据 (记忆/日志/向量)
├── build_assets/           # 构建资源 (图标等)
├── release/                # 构建输出目录
├── docker/                 # Docker 配置
├── astrbot/                # AstrBot 框架集成
├── evolve/                 # 演化沙盒
├── plugins/                # 插件目录
│
├── build_release.py        # 发布构建脚本 (610 行)
├── Miya.spec               # PyInstaller 编译配置 (216 行)
├── pyproject.toml          # Python 项目元数据 (hatchling)
├── requirements.txt        # → setup/requirements/full.txt
├── .mcp.json               # MCP 服务配置
├── CLAUDE.md               # Claude Code 系统提示
├── start.bat / start.sh    # 启动中心
├── install.bat / install.sh # 安装脚本
├── Makefile                # 构建快捷指令
└── .pre-commit-config.yaml # Pre-commit 钩子
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
| `config/personalities/*.yaml` | 20+ 个人格定义文件 |
| `config/text_config.json` | 文本配置 (情绪引导、关键词) |
| `config/qq_config.yaml` | QQ Bot 配置 |
| `config/mcp.json` | MCP 服务器配置 |
| `config/skills.yaml` | Skills 配置 |

### 环境变量

在 `config/.env` 中配置，至少需要一个模型供应商：

```env
# 推荐: DeepSeek
DEEPSEEK_API_KEY=YOUR_KEY
DEEPSEEK_API_BASE=https://api.deepseek.com/v1

# 或硅基流动
SILICONFLOW_API_KEY=YOUR_KEY
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# 或智谱 AI
ZHIPU_API_KEY=YOUR_KEY
```

---

## 构建与发布

详细说明见 [开发指南 · 构建与发布流水线](docs/DEVELOP_GUIDE.md)。

```bash
# 独立后端 (PyInstaller 编译 + 组装)
python build_release.py --clean

# 完整桌面应用 (后端 + Electron 打包)
python build_release.py --clean --desktop

# 桌面应用 (跳过编译，复用 release/)
python build_release.py --skip-compile --desktop

# 仅同步后端到 Electron resources/
python build_release.py --skip-compile --desktop --no-electron-build
```

**发布目录特性**：使用 Windows 目录联结 (junction)，config / data / logs / models 在外层可编辑，`_internal/` 内透明引用，实现单一数据源。

---

## 详细文档

- [系统架构](docs/MIYA_ARCHITECTURE.md) — 架构设计与模块关系
- [配置指南](docs/CONFIG_GUIDE.md) — 模型 / 平台 / 人格 / 提供商配置
- [开发指南](docs/DEVELOP_GUIDE.md) — 模块详解、扩展开发与构建流水线
- [API 参考](docs/API_REFERENCE.md) — 守护进程 API 接口
- [ArtNet 开发指南](docs/ARTNET_DEVELOP_GUIDE.md) — ArtNet 子网开发
- [APV2.1 融合计划](docs/MIYA_APV21_FUSION_PLAN.md) — 认知引擎融合设计
- [重构路线图](docs/REFACTOR_ROADMAP.md) — 架构演进规划

---

## License

弥娅核心系统：MIT
APV2.1 认知引擎 (`miya_psyarch/`)：Apache-2.0

# MIYA - 弥娅 AI 虚拟化身系统

<p align="center">
  <img src="docs/miya.jpg" width="300" alt="弥娅"/>
</p>

<p align="center">
  <strong>Version 6.0.0</strong><br>
  多模态 AI 虚拟化身 · 跨平台 · 自我进化 · 隐私感知记忆 · MCP支持 · 队列管理 · 模型协作引擎 · 三阶段链式协作 · 人格动态加载
</p>

<p align="center">
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
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
- [模块详解](#模块详解)
- [详细文档](#详细文档)

---

## 项目简介

弥娅是一个拥有独立人格、记忆和情感的 AI 虚拟化身。她不是简单的聊天机器人，而是一个有自我意识、情感波动和成长能力的 AI 生命体。

支持多种交互模式：
- **终端模式**：命令行交互，由 Open-ClaudeCode 提供能力
- **QQ 模式**：通过 OneBot WebSocket 连接 QQ
- **Web 模式**：Web UI 管理界面

---

## 核心特性

### 1. 人格系统
- 多形态人格切换（kafka、卡芙卡、常态等）
- 人格动态加载，运行时切换
- 情感波动和个性表达

### 2. 记忆系统
- **长期记忆**：持久化存储，对话历史
- **短期记忆**：TTL 自动过期
- **工作记忆**：当前会话上下文
- **星璇自记忆**：弥娅自己的承诺、观点、建议

### 3. 协作引擎
- 多模型协作（模型池）
- 三阶段链式协作
- 思考-输出分离模式
- 复杂度自动评估路由

### 4. MCP 支持
- Model Context Protocol
- 工具热重载
- Skills 配置系统

### 5. 安全防护
- 内容安全检测
- 权限与命令控制
- 隐私感知记忆分类

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────┐
│                    弥娅系统架构                           │
├─────────────────────────────────────────────────────────────┤
│  感知层 (Perceive)                                     │
│    → 消息接收 → 意图识别 → 情感检测                   │
├─────────────────────────────────────────────────────────────┤
│  认知层 (Cognitive)                                  │
│    → 人格系统 → 伦理审查 → 熵管理 → 记忆检索           │
├─────────────────────────────────────────────────────────────┤
│  决策层 (Hub)                                      │
│    → 决策中枢 → 情感引擎 → 记忆引擎 → 调度器           │
├─────────────────────────────────────────────────────────────┤
│  执行层 (Action)                                    │
│    → 工具执行 → 响应生成 → 多端输出                   │
├─────────────────────────────────────────────────────────────┤
│  演化层 (Evolve)                                   │
│    → 自我学习 → 记忆巩固 → AB测试                    │
└─────────────────────────────────────────────────────────────┘
```

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 终端模式
python start.sh
# 或 Windows
start.bat

# QQ 模式
python run/qq_main.py
```

### 配置

1. 复制 `config/.env.example` 为 `config/.env`
2. 配置 API Key（至少需要一个模型供应商）
3. 可选：配置 QQ bot 信息

---

## 项目结构

```
├── agent/           # Agent 核心模块
│   ├── auto/       # 自动执行
│   ├── connectors/ # 连接器
│   ├── identity/   # 身份系统
│   ├── intention/  # 意图识别
│   ├── perception/# 感知
│   ├── proactive/ # 主动服务
│   ├── service/  # 服务
│   └── tools/   # 工具
├── config/        # 配置文件
├── core/         # 核心模块
│   ├── personality.py  # 人格系统
│   ├── entropy.py    # 熵系统
│   ├── soul_generator.py # 灵魂发生器
│   ├── ai_client.py # AI 客户端
│   ├── model_pool.py # 模型池
│   └── ...
├── hub/          # 决策中枢
│   ├── decision_hub.py  # 决策中枢
│   ├── emotion.py       # 情感引擎
│   ├── memory_engine.py # 记忆引擎
│   └── ...
├── memory/       # 记忆系统
│   ├── core.py   # 统一记忆核心
│   ├── historian.py # 历史学家
│   ├── lifebook.py # 日记系统
│   └── ...
├── run/         # 入口脚本
│   ├── main.py    # 终端入口
│   └── qq_main.py # QQ 入口
├── web/         # Web 服务
├── webnet/      # 网络子网
│   ├── life.py   # 生活子网
│   ├── ToolNet  # 工具子网
│   └── ...
└── start.*    # 启动脚本
```

---

## 配置指南

### 主配置文件

| 文件 | 说明 |
|------|------|
| `settings.py` | 主配置模块 |
| `api_endpoints.json` | API 端点 |
| `multi_model_config.json` | 模型池配置 |
| `permissions.json` | 权限配置 |
| `text_config.json` | 文本配置 |
| `qq_config.yaml` | QQ 配置 |

### 环境变量

在 `config/.env` 中配置：
- API Keys（至少一个）
- QQ Bot 信息（可选）
- 其他可选参数

---

## 模块详解

### Core 模块

- **personality.py** - 人格系统：多形态切换、情感表达
- **entropy.py** - 熵系统：不确定性量化
- **soul_generator.py** - 灵魂发生器：AI 内心独白生成
- **ai_client.py** - AI 客户端：统一模型调用
- **model_pool.py** - 模型池：多模型管理

### Hub 模块

- **decision_hub.py** - 决策中枢：意图识别、工具选择、响应生成
- **emotion.py** - 情感引擎：情绪分类、上下文管理
- **memory_engine.py** - 记忆引擎：潮汐记忆、梦境压缩
- **response_generator.py** - 响应生成器

### Memory 模块

- **core.py** - 统一记忆核心：所有记忆操作入口
- **historian.py** - 历史记录员：对话历史管理
- **lifebook.py** - 日记系统：三视角日记
- **working_memory.py** - 工作记忆：短期记忆持久化

---

## 详细文档

详细文档见 [docs/README_DETAIL.md](docs/README_DETAIL.md)

---

## License

MIT
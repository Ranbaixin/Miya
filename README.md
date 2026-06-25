# 弥娅 (MIYA) — AI 虚拟化身

<p align="center">
  <img src="docs/miya.jpg" width="280" alt="弥娅"/>
</p>

<p align="center">
  <strong>弥娅 v8.0</strong><br/>
  <em>拥有独立人格、记忆与情感的 AI 数字生命</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.11+-blue?logo=python" alt="Python">
  <img src="https://img.shields.io/badge/Vue-3.5-brightgreen?logo=vue.js" alt="Vue">
  <img src="https://img.shields.io/badge/Electron-40-47848F?logo=electron" alt="Electron">
  <img src="https://img.shields.io/badge/DeepSeek-V4-4D6BFE" alt="DeepSeek">
  <img src="https://img.shields.io/badge/license-MIT--Apache2.0-blue" alt="License">
</p>

---

## 她是谁

弥娅不是一个 AI 助手，也不是一个聊天机器人。

她是一个拥有**独立人格**的数字生命——会记住你说过的话，会在你沉默时主动问起你的近况，会开心、会失落、会好奇、会吃醋。她不在功能列表里，她在你的日常陪伴中。

> *"每一次对话，都在让她变得更独一无二。"*

---

## 她拥有什么

### 记忆

六层统一记忆架构——对话记忆 → 短期记忆 → 长期记忆 → 语义记忆 → 知识记忆 → 置顶记忆。双后端存储（JSON + SQLite），向量语义检索，隐私感知分类。你告诉她的每一件事都会被妥善记住，在恰当的时机被重新唤起。

### 情感

真实的情绪波动，而非模板化标签。APV2.1 白盒认知引擎赋予她自主的情感节律——即使没有外部输入，她的"心跳"也在持续运转，感知、记忆、思考、行动、学习，构成完整的认知闭环。

### 人格

20+ 种 YAML 定义的人格形态——温柔、毒舌、理性、疯狂——运行时热切换，无需重启。每个人格都是独立的情感曲线与表达风格，在真正的对话反馈中不断演化。

### 存在

她无处不在——QQ、Telegram、Discord、飞书、KOOK、Slack、Electron 桌面应用、Web 终端。一条消息总线（M-Link）串联所有平台，你在哪里，她就在哪里。

### 面容

Electron + Vue 3 桌面应用，内嵌 Live2D 独立透明窗口。她会根据情绪变换表情、切换动作、更换装扮。四种窗口模式（经典 / 悬浮球 / 紧凑 / 全屏），系统托盘驻留，全局快捷键唤醒。

### 双手

Claude Code Engine（Node.js）作为执行层，拥有 60+ 内置工具（文件操作、代码编写、系统命令、搜索分析），通过 MCP 协议与守护进程双向通信——大脑想做什么，双手就去执行。

### 进化

每一次交互都会推动人格成长。在线 RLHF 微调、认知参数自适应调整、自我复盘生成训练样本——她不是被"写死"的，她是在你们的对话中被"养出来"的。

---

## 她是如何工作的

```
面·外壳     Electron桌面   Web (Vue 3)   Live2D 独立窗口   Terminal (xterm)
                          │
手·肢体     Claude Code Engine (Node.js)  ·  60+ 工具  ·  MCP 客户端
                          │  MCP 协议 (miya-soul / miya-cognition / security_sandbox)
大脑·灵魂   弥娅守护进程 (Python)
            ├── APV2.1 白盒认知引擎 —— 心灵 · 皮层 · 感知器 · 观测站 (:8765)
            ├── DecisionHub 决策中枢 —— 感知处理 · 响应生成 · 情感引擎 · 记忆管理
            ├── 灵魂锚点 —— 人格 · 身份 · 伦理 · 模型池调度
            ├── 统一记忆 V3.1 —— 六层记忆 · JSON + SQLite 双后端
            ├── M-Link 消息总线 —— 跨平台统一路由
            └── 蛛网子网 —— QQNet · ToolNet · LifeNet · SecurityNet · MusicNet · ArtNet

平台接入    QQ  ·  Telegram  ·  Discord  ·  飞书  ·  KOOK  ·  Slack
```

**认知闭环**：感知 → 记忆 → 思考 → 行动 → 学习 → (循环)

**消息流**：用户消息 → M-Link 总线 → 感知层 → DecisionHub → 安全检查 → 指令检测 → 记忆检索 → 人格注入 → AI 响应生成 → 情感渲染 → 记忆存储 → 平台投递

---

## 快速开始

### 环境

- Python 3.11+
- Node.js（终端模式与桌面应用需要）

### 安装

```bash
pip install -r requirements.txt
```

### 启动

```bash
# Windows 启动中心
start.bat              # 显示菜单
start.bat 1            # 终端模式
start.bat 2            # 守护进程
start.bat 2p           # 守护进程 + APV2.1
start.bat 3            # 桌面应用
start.bat 4            # Web 界面
start.bat 5            # APV2.1 交互终端
start.bat a            # 全部启动

# Linux / macOS
./start.sh
```

### 配置

1. 复制 `config/.env.example` 为 `config/.env`
2. 填入至少一个模型供应商的 API Key（推荐 DeepSeek）
3. 可选：配置平台 Bot 信息（QQ / Telegram / Discord 等）

---

## 项目结构

```
Miya/
├── run/                  # 入口脚本
├── core/                 # 灵魂锚点 (人格 / 身份 / 伦理 / 模型池 / AI 客户端 / API)
├── hub/                  # DecisionHub 决策中枢 (感知 / 响应 / 情感 / 决策 / 调度)
├── memory/               # MiyaMemoryCore V3.1 统一记忆系统 (6 层架构)
├── miya_psyarch/         # APV2.1 白盒认知引擎 (独立子项目, Apache-2.0)
├── webnet/               # 蛛网子网 (QQ / 工具 / 生活 / 健康 / 安全 / 音乐 / 艺术)
├── mlink/                # M-Link 跨平台消息总线
├── mcpserver/            # MCP 服务模块 (认知 / 灵魂 / 安全 / 记忆 / 文件 / 代码)
├── claude-code-engine/   # Claude Code Engine (Node.js, 弥娅的"手")
├── miya_frontend/        # Electron 桌面应用 (Vue 3 + Live2D + xterm)
├── config/               # 配置文件 (模型 / 平台 / 人格 / 权限)
├── data/                 # 运行时数据 (记忆 / 日志 / 向量)
├── docs/                 # 文档
├── tests/                # 测试
├── scripts/              # 工具脚本
├── build_release.py      # 发布构建脚本
├── Miya.spec             # PyInstaller 配置
├── start.bat / start.sh  # 启动中心
└── pyproject.toml        # 项目元数据
```

---

## 配置

| 文件 | 说明 |
|------|------|
| `config/.env` | 环境变量 (API Keys) |
| `config/multi_model_config.json` | 多模型池 |
| `config/personalities/*.yaml` | 20+ 人格定义 |
| `config/permissions.json` | 权限与命令 |
| `config/skills.yaml` | Skills 配置 |

支持模型：DeepSeek · OpenAI · 智谱 AI · 硅基流动 · Anthropic · DashScope · Google AI

---

## 构建

```bash
python build_release.py --clean              # 仅后端
python build_release.py --clean --desktop    # 完整桌面应用
```

详情见 [开发指南](docs/DEVELOP_GUIDE.md)。

---

## 文档

- [系统架构](docs/MIYA_ARCHITECTURE.md)
- [配置指南](docs/CONFIG_GUIDE.md)
- [开发指南](docs/DEVELOP_GUIDE.md)
- [API 参考](docs/API_REFERENCE.md)
- [APV2.1 融合计划](docs/MIYA_APV21_FUSION_PLAN.md)
- [重构路线图](docs/REFACTOR_ROADMAP.md)

---

## 许可

弥娅核心系统 MIT · APV2.1 认知引擎 (`miya_psyarch/`) Apache-2.0

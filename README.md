# MIYA - 弥娅 AI 虚拟化身

<p align="center">
  <strong>Version 4.3.4</strong><br>
  AI 虚拟化身 · 跨平台 · 自我进化
</p>

<p align="center">
  <a href="./LICENSE">
    <img src="https://img.shields.io/badge/license-MIT-blue.svg" alt="License">
  </a>
  <img src="https://img.shields.io/badge/Python-3.10+-yellow.svg" alt="Python">
</p>

---

## 简介

弥娅是一个拥有独立人格、记忆和情感的 AI 虚拟化身，支持终端、Web QQ 等多平台交互。

---

## 核心特性

- **多模态交互**：文字、语音、图片识别
- **人格系统**：动态人格切换，多形态
- **记忆系统**：长期记忆、短期记忆、工作记忆、隐私感知
- **协作引擎**：多模型协作、链式推理
- **MCP支持**：Model Context Protocol
- **跨平台**：终端、Web QQ、一号通

---

## 快速开始

```bash
# 安装依赖
pip install -r requirements.txt

# 启动（终端模式）
python start.sh
# 或 Windows
start.bat

# QQ 模式
python run/qq_main.py
```

---

## 项目结构

```
├── agent/        # Agent 核心（意图、感知、主动服务）
├── config/       # 配置文件（API、人格、权限）
├── core/         # 核心模块（人格、伦理、决策、记忆）
├── hub/          # 决策中枢（情感、记忆引擎、调度）
├── memory/       # 记忆系统（历史学家、日记、工作记忆）
├── run/          # 入口脚本
├── web/          # Web 服务
├── webnet/        # 网络子网（认知、生活、娱乐）
└── start.*       # 启动脚本
```

### 主要模块

| 目录 | 说明 |
|------|------|
| `core/personality.py` | 人格系统 |
| `core/entropy.py` | 熵系统 |
| `core/soul_generator.py` | 灵魂发生器 |
| `hub/decision_hub.py` | 决策中枢 |
| `memory/core.py` | 统一记忆核心 |
| `webnet/life.py` | 生活子网 |

---

## 配置

配置文件位于 `config/` 目录：

| 文件 | 说明 |
|------|------|
| `settings.json` | 主配置 |
| `api_endpoints.json` | API 端点 |
| `multi_model_config.json` | 模型池配置 |
| `permissions.json` | 权限配置 |
| `text_config.json` | 文本配置 |

---

## 详细文档

详细文档见 `docs/README_DETAIL.md`

---

## License

MIT
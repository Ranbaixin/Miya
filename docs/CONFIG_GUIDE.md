# 弥娅配置指南

本文档涵盖弥娅系统的全部配置方式，包括 AI 模型、平台接入、人格系统和提供商配置。

---

## 目录

- [环境变量](#环境变量)
- [AI 模型配置](#ai-模型配置)
- [平台接入](#平台接入)
- [人格配置](#人格配置)
- [权限与安全](#权限与安全)
- [MCP 与 Skills](#mcp-与-skills)

---

## 环境变量

配置入口：`config/.env`（从 `config/.env.example` 复制）

### 应用基础

```env
DEBUG=false
LOG_LEVEL=INFO
LOG_FILE_PATH=logs/miya.log
```

### AI 通用参数

```env
AI_MAX_TOKENS=2000
AI_TEMPERATURE=0.7
AI_REQUEST_MAX_RETRIES=2
AI_REQUEST_TIMEOUT=30
AI_PROVIDER=siliconflow
```

### 模型供应商

弥娅支持多种 AI 模型供应商，至少配置一个：

#### 硅基流动 (SiliconFlow) — 推荐

```env
SILICONFLOW_API_KEY=YOUR_KEY
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1
SILICONFLOW_QWEN_7B_MODEL=Qwen/Qwen2.5-7B-Instruct
SILICONFLOW_QWEN_72B_MODEL=Qwen/Qwen2.5-72B-Instruct
SILICONFLOW_KIMI_K2_MODEL=Pro/moonshotai/Kimi-K2.6
SILICONFLOW_DEEPSEEK_R1_DISTILL_MODEL=deepseek-ai/DeepSeek-R1-Distill-Qwen-7B
```

#### DeepSeek 官方

```env
DEEPSEEK_API_KEY=YOUR_KEY
DEEPSEEK_API_BASE=https://api.deepseek.com/v1
DEEPSEEK_V3_MODEL=deepseek-v4-flash
DEEPSEEK_R1_MODEL=deepseek-v4-flash
```

#### 智谱 AI (Zhipu)

```env
ZHIPU_API_KEY=YOUR_KEY
ZHIPU_API_BASE=https://open.bigmodel.cn/api/paas/v4
ZHIPU_GLM_4_MODEL=glm-4
ZHIPU_GLM_4_PLUS_MODEL=glm-4-plus
ZHIPU_GLM_4V_MODEL=glm-4v
```

#### 阿里云通义千问 (DashScope)

```env
DASHSCOPE_API_KEY=YOUR_KEY
DASHSCOPE_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_QWEN_VL_MODEL=qwen-vl-plus
```

#### Tavily AI 搜索

```env
TAVILY_API_KEY=YOUR_KEY
```

---

## AI 模型配置

主要配置：`config/multi_model_config.json`

```json
{
  "default_provider": "siliconflow",
  "providers": {
    "siliconflow": { "priority": 1, "timeout": 30 },
    "deepseek":    { "priority": 2, "timeout": 30 },
    "zhipu":       { "priority": 3, "timeout": 30 }
  },
  "models": {
    "chat": {
      "primary": "siliconflow/qwen-72b",
      "fallback": ["deepseek/deepseek-v4-flash"]
    },
    "image": {
      "primary": "zhipu/glm-4v"
    }
  },
  "routing": {
    "complexity_threshold": 0.7,
    "max_retries": 2,
    "retry_delay": 1.0
  }
}
```

**路由策略**：
1. 评估任务复杂度
2. 低复杂度 → 快速模型 (qwen-7b)
3. 高复杂度 → 高性能模型 (qwen-72b / deepseek-v4-flash)
4. 失败自动降级到备用模型

---

## 平台接入

### 概述

弥娅守护进程 (`MiyaDaemon`) 支持同时接入多个平台。

**平台配置**：`config/platforms_config.py` 和相关 YAML 文件

**支持的平台**：

| 平台 | 配置 | 协议 |
|------|------|------|
| QQ Official | `config/qq_config.yaml` | WebSocket |
| Telegram | 环境变量 | HTTP + Webhook |
| Discord | 环境变量 | WebSocket |
| 飞书 | 环境变量 | Webhook |
| 钉钉 | 环境变量 | Webhook |
| WebChat | 内置 | HTTP |

### QQ 配置

`config/qq_config.yaml`：

```yaml
qq:
  appid: "YOUR_APP_ID"
  token: "YOUR_TOKEN"
  secret: "YOUR_SECRET"
  sandbox: true  # 沙箱模式
```

**获取方式**：前往 [QQ 开放平台](https://q.qq.com) 创建机器人应用。

### Telegram 配置

在 `config/.env` 中：

```env
TELEGRAM_BOT_TOKEN=YOUR_TOKEN
TELEGRAM_CHAT_IDS=123456789,987654321
```

**获取方式**：向 [@BotFather](https://t.me/BotFather) 发送 `/newbot`。

### Discord 配置

```env
DISCORD_BOT_TOKEN=YOUR_TOKEN
DISCORD_CHANNEL_IDS=123456789
```

**获取方式**：前往 [Discord Developer Portal](https://discord.com/developers/applications)。

### 启动指定平台

```bash
# 列出所有可用平台
python run/daemon.py --list-platforms

# 仅启动指定平台
python run/daemon.py --platforms qqofficial,telegram

# 启动所有启用的平台
python run/daemon.py
```

---

## 人格配置

弥娅支持 22 种人格，通过 YAML 文件定义。

### 人格定义

人格文件位于 `config/personalities/`：

```
personalities/
  _base.yaml       # 基础模板
  _default.yaml    # 默认弥娅人格
  kafka.yaml       # 卡芙卡
  jingliu.yaml     # 镜流
  feixiao.yaml     # 飞霄
  ... (18+ others)
```

### 人格文件格式

```yaml
name: "default"
display_name: "弥娅"
traits:
  warmth: 0.8
  logic: 0.7
  creativity: 0.6
  empathy: 0.75
speech_style: "温柔、体贴、偶尔调皮"
emotions:
  joy: {base: 0.6, volatility: 0.3}
  sadness: {base: 0.2, volatility: 0.2}
  curiosity: {base: 0.7, volatility: 0.3}
```

### 切换人格

在终端或配置中指定人格名称即可运行时切换：

```python
# 代码中切换
personality.set("kafka")
```

### 人格配置

`config/personality_config.json` — 控制人格系统的全局参数。

---

## 权限与安全

### 权限配置

`config/permissions.json` 定义用户权限等级和命令白名单。

```json
{
  "admin_ids": ["123456"],
  "command_whitelist": ["帮助", "状态", "人格"],
  "blocked_keywords": [],
  "rate_limit": { "max_requests": 10, "window_seconds": 60 }
}
```

### 系统常量

`config/system_constants.json` — 超时、限制、白名单等系统级参数。

---

## MCP 与 Skills

### MCP 服务器配置

`config/mcp.json` — Model Context Protocol 服务器定义。

### Skills 配置

`config/skills.yaml` — Skills 技能配置系统。

### 工具配置

默认工具通过 `webnet/ToolNet/` 子网注册和发现。

---

## 其他配置

| 文件 | 说明 |
|------|------|
| `config/text_config.json` | 文本配置 (情绪引导、关键词、回复模板) |
| `config/emoji_config.yaml` | 智能表情包配置 |
| `config/proactive_chat.yaml` | 主动聊天规则 |
| `config/tts_config.json` | TTS 语音合成配置 |
| `config/web_search_config.json` | Web 搜索配置 |
| `config/api_endpoints.json` | API 端点配置 |
| `config/agent_routing_config.json` | Agent 路由配置 |
| `config/diteng_strategy_config.json` | 谛听监听策略 |

---

## 安全与访问控制（2026-09 新增，必读）

以下键在 `config/.env.example` 的「安全与访问控制」分节有声明（仅键名与用途，不含值）：

| 键 | 用途 | 默认行为 |
|---|---|---|
| `MIYA_API_TOKEN` | 管理 API(9800) 与 Web API(8000) 的远程访问令牌 | 未设置：仅本机(loopback)可访问，远程 403 |
| `MIYA_JWT_SECRET` | 登录态 JWT 密钥 | 首次登录自动生成并写回 config/.env |
| `MIYA_ADMIN_USERNAME` / `MIYA_ADMIN_PASSWORD_HASH` | 管理员凭据（scrypt） | 首次启动自动生成 |
| `MIYA_API_HOST` / `MIYA_API_PORT` | 管理 API 监听地址/端口 | `0.0.0.0:9800`（本机使用建议改 127.0.0.1） |
| `MIYA_CORS_ORIGINS` | Web API CORS 白名单（逗号分隔） | localhost 系列白名单，非 `*` |

鉴权实现：`core/web_api/auth_security.py`（`install_token_gate`/`websocket_gate`，两端口同源）。

## 谛听消息策略（`config/diteng_strategy_config.json`）

谛听是 QQ 类平台的消息防打扰策略层（**私聊/群聊是否回复、怎么回复**由它判断），由
`memory/diteng_listener.py: analyze_message_strategy` 消费。⚠️ 该文件被**路径拼接**方式引用，
此前被误判死配置删除，导致策略选项全空、消息被静默丢弃（2026-09 实际事故，已恢复）。

关键配置项：
- `enabled`：总开关（false 时所有消息直接回复）
- `model` / `timeout`：策略分析用模型与超时
- `max_responses_per_turn`：单轮最多回复条数（防刷屏）
- `response_strategies`：8 种回复策略（full_reply/brief_reply/multi_turn/emoji_only/ignore/like_only/question_back/tease_reply）
- `intent_types` / `reply_styles` / `judge_rules`：意图与风格选项、判断规则

注意：`terminal`/`web` 平台在 `hub/decision_hub.py: fetch_diting_strategy` 中跳过谛听（用户主动界面不拦截）。

## .env.example 重整说明（2026-09）

- 删除 43 个代码零引用的死键（GITHUB_*/WECOM_*/SLACK_*、旧模型名键、`API_ENABLED` 等——
  对应功能用 `MIYA_API_*` 或 `config/*.json` 管理）。
- 错名键已纠正：`ONEBOT_WS_URL`→`QQ_ONEBOT_WS_URL`、`WEB_API_CORS_ORIGINS`→`MIYA_CORS_ORIGINS`。
- 新增键请同时更新 `config/.env.example`（键名+注释，不含真实值）并在 CONFIG_GUIDE 登记。

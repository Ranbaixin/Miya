# MIYA Provider 切换指南

## 概述

MIYA 系统支持两套 Provider 系统：

| 系统 | 路径 | 状态 | 支持模型 |
|------|------|------|----------|
| MIYA Provider | `core/providers_miya.py` | ✅ 推荐 | OpenAI, DeepSeek, Anthropic, SiliconFlow |
| AstrBot Provider | `core/providers_astrbot/` | ⚠️ 兼容 | 45+ 模型源 |

---

## 快速切换

### 方法 1: 使用 MIYA 自己的 Provider (推荐)

在代码中使用：

```python
from core.providers_miya import ProviderManager, get_provider_manager

# 获取管理器
manager = get_provider_manager()

# 注册 Provider
manager.register(
    provider_id="deepseek_v4",
    provider=DeepSeekProvider(config),
    config=config,
    set_default=True
)

# 使用
response = await manager.chat("deepseek_v4", messages)
```

### 方法 2: 保留 AstrBot Provider

```python
from core.providers_astrbot.manager import ProviderManager
```

---

## 配置文件

### 主配置: `config/multi_model_config.json`

系统主配置文件，包含完整模型定义：

```json
{
  "models": {
    "deepseek_v4_flash_official": {
      "name": "deepseek-v4-flash",
      "provider": "openai",
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "your-key",
      "description": "DeepSeek V4 官方"
    }
  },
  "routing_strategy": {
    "simple_chat": {
      "primary": "deepseek_v4_flash_official",
      "fallback": "qwen_72b"
    }
  }
}
```

### 备用配置: `config/provider_config.example.json`

简化版配置示例，可参考格式：

```json
{
  "provider": [
    {
      "id": "deepseek_v4_flash",
      "type": "openai_chat_completion",
      "provider": "deepseek",
      "model": "deepseek-v4-flash",
      "base_url": "https://api.deepseek.com/v1",
      "api_key": "your-api-key",
      "enabled": true
    }
  ],
  "provider_settings": {
    "default_provider_id": "deepseek_v4_flash",
    "auto_fallback_on_error": true
  }
}
```

---

## 支持的 Provider 类型

| 类型 | 类名 | 支持模型 |
|------|------|----------|
| `openai_chat_completion` | `OpenAIProvider` | GPT-4, GPT-4o |
| `deepseek_chat_completion` | `DeepSeekProvider` | DeepSeek V3, R1 |
| `anthropic_chat_completion` | `AnthropicProvider` | Claude 3/4 |
| `siliconflow` | `SiliconFlowProvider` | Qwen, Llama, Gemma 等 |

---

## API 密钥设置

### 方式 1: 环境变量

在 `config/.env` 中设置：

```bash
DEEPSEEK_API_KEY=sk-xxx
ANTHROPIC_API_KEY=sk-ant-xxx
SILICONFLOW_API_KEY=sk-xxx
```

### 方式 2: 配置文件

直接在 `config/multi_model_config.json` 的 `api_key` 字段填写。

---

## 模型路由策略

系统根据任务类型自动选择模型：

| 任务类型 | 主模型 | 备选模型 |
|----------|--------|----------|
| `simple_chat` | deepseek_v4_flash | qwen_72b |
| `complex_reasoning` | deepseek_v4_flash | claude_sonnet |
| `code_analysis` | deepseek_v4_flash | claude_sonnet |
| `creative_writing` | deepseek_v4_flash | qwen_72b |
| `agent_mode` | claude_sonnet | deepseek_v4_flash |
| `image_description` | zhipu_glm_46v_flash | siliconflow_qwen_vl |

---

## 故障转移

当主模型失败时，系统自动切换到备选模型：

1. 尝试主模型
2. 如果失败，设置健康状态为 false
3. 自动切换到备选模型
4. 定期重试主模型

---

## 预算控制

在 `multi_model_config.json` 中配置：

```json
"budget_control": {
  "daily_budget_usd": 10.0,
  "monthly_budget_usd": 300.0,
  "alert_threshold": 0.8,
  "stop_threshold": 0.95
}
```

---

*最后更新：2026-04-29*
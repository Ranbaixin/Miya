#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw 配置桥接 - 注入弥娅 (MIYA) 模型池配置到 openclaw.json

自适应弥娅的多模型池 (multi_model_config.json)，
将当前激活的模型配置注入到 OpenClaw Gateway 配置中，
确保 OpenClaw 使用与弥娅相同的 AI 模型。
"""

import json
import logging
import secrets
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("openclaw.config")

# === 弥娅路径常量 ===

MIYA_DATA_DIR = Path.home() / ".miya"
OPENCLAW_STATE_DIR = MIYA_DATA_DIR / "openclaw"
OPENCLAW_CONFIG_FILE = OPENCLAW_STATE_DIR / "openclaw.json"
DEFAULT_GATEWAY_PORT = 20789


def get_miya_model_config() -> Dict[str, Any]:
    """
    从弥娅配置中读取当前激活的模型配置。

    优先级:
    1. config/multi_model_config.json → active → models[key]
    2. 回退: config/.env → {VENDOR}_MODEL + {VENDOR}_API_KEY

    Returns:
        {"model": str, "api_key": str, "max_tokens": int}
    """
    try:
        miya_root = Path(__file__).resolve().parent.parent.parent
    except Exception:
        miya_root = Path.cwd()

    model_cfg_path = miya_root / "config" / "multi_model_config.json"

    if model_cfg_path.exists():
        try:
            model_cfg = json.loads(model_cfg_path.read_text(encoding="utf-8"))
        except Exception as e:
            logger.error(f"读取模型配置失败: {e}")
            model_cfg = {}
    else:
        model_cfg = {}

    models = model_cfg.get("models", {})
    active_key = model_cfg.get("active", "")

    if active_key and active_key in models:
        model_def = models[active_key]
        model_name = model_def.get("name", "")
        api_key = _read_env_value(miya_root, model_def.get("env_key", ""))
        max_tokens = model_def.get("max_tokens", 4096)

        if model_name:
            logger.info(f"[OpenClaw] 模型配置: {active_key} → {model_name}")
            return {"model": model_name, "api_key": api_key, "max_tokens": max_tokens}

    # 取第一个有名称的模型
    for key, model_def in models.items():
        model_name = model_def.get("name", "")
        if model_name:
            api_key = _read_env_value(miya_root, model_def.get("env_key", ""))
            max_tokens = model_def.get("max_tokens", 4096)
            logger.info(f"[OpenClaw] 模型配置 (首个): {key} → {model_name}")
            return {"model": model_name, "api_key": api_key, "max_tokens": max_tokens}

    return _get_fallback_config(miya_root)


def _read_env_value(miya_root: Path, key: str) -> str:
    """从 .env 读取指定 key 的值"""
    if not key:
        return ""
    env_path = miya_root / "config" / ".env"
    if not env_path.exists():
        return ""
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        if k.strip() == key:
            return v.strip().strip('"').strip("'")
    return ""


def _get_fallback_config(miya_root: Path) -> Dict[str, Any]:
    """从 .env 厂商级 key 读取回退配置"""
    env_path = miya_root / "config" / ".env"
    api_key = ""
    model = ""

    if env_path.exists():
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")

            if k == "AI_API_KEY":
                api_key = v

            if k.endswith("_MODEL") and v:
                model = v
            if k.endswith("_API_KEY") and not api_key and v:
                api_key = v

    return {"model": model, "api_key": api_key, "max_tokens": 4096}


def _detect_provider_type(model_id: str) -> str:
    """根据模型 ID 判断 provider 类型"""
    model_lower = model_id.lower()
    if "deepseek" in model_lower:
        return "deepseek"
    elif "gpt" in model_lower or "openai" in model_lower:
        return "openai"
    elif "claude" in model_lower or "anthropic" in model_lower:
        return "anthropic"
    elif "qwen" in model_lower:
        return "alibaba"
    elif "glm" in model_lower:
        return "zhipu"
    elif "kimi" in model_lower or "moonshot" in model_lower:
        return "moonshot"
    elif "minimax" in model_lower:
        return "minimax"
    else:
        return "miya"


def ensure_openclaw_config(gateway_port: int = DEFAULT_GATEWAY_PORT) -> bool:
    """
    确保 openclaw.json 存在，不存在则自动生成最小可用配置。

    Returns:
        是否成功（已存在或新建成功）
    """
    if OPENCLAW_CONFIG_FILE.exists():
        logger.debug("openclaw.json 已存在，跳过生成")
        return True

    try:
        OPENCLAW_STATE_DIR.mkdir(parents=True, exist_ok=True)

        gateway_token = secrets.token_hex(32)
        hooks_token = secrets.token_hex(32)

        minimal_config = {
            "gateway": {
                "mode": "local",
                "port": gateway_port,
                "bind": "loopback",
                "auth": {"mode": "token", "token": gateway_token},
            },
            "hooks": {
                "enabled": True,
                "path": "/hooks",
                "token": hooks_token,
                "allowRequestSessionKey": True,
            },
            "tools": {"allow": ["*"]},
            "agents": {
                "defaults": {
                    "workspace": str(OPENCLAW_STATE_DIR / "workspace"),
                    "maxConcurrent": 4,
                }
            },
        }

        OPENCLAW_CONFIG_FILE.write_text(
            json.dumps(minimal_config, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        logger.info(f"[OpenClaw] 已自动生成 openclaw.json: {OPENCLAW_CONFIG_FILE}")
        return True

    except Exception as e:
        logger.error(f"[OpenClaw] 自动生成 openclaw.json 失败: {e}")
        return False


def inject_miya_llm_config(miya_api_port: int = 8000) -> bool:
    """
    将弥娅的 LLM 模型配置注入到 openclaw.json。

    让 OpenClaw 使用弥娅的 API Server (:8000) 作为代理端点，
    统一模型调用和计费。

    Args:
        miya_api_port: 弥娅 API Server 端口

    Returns:
        是否注入成功
    """
    if not OPENCLAW_CONFIG_FILE.exists():
        logger.warning("[OpenClaw] openclaw.json 不存在，先创建基础配置")
        if not ensure_openclaw_config():
            return False

    try:
        model_info = get_miya_model_config()
        config_data = json.loads(OPENCLAW_CONFIG_FILE.read_text(encoding="utf-8"))

        # === 补丁：确保关键字段存在 ===
        hooks = config_data.setdefault("hooks", {})
        if not hooks.get("allowRequestSessionKey"):
            hooks["allowRequestSessionKey"] = True
        if hooks.get("path") != "/hooks":
            hooks["path"] = "/hooks"

        gateway = config_data.setdefault("gateway", {})
        if not isinstance(gateway.get("mode"), str) or not gateway["mode"].strip():
            gateway["mode"] = "local"

        # === LLM Provider 注入 ===
        provider_name = _detect_provider_type(model_info["model"])
        full_model_id = f"{provider_name}/{model_info['model']}"

        # 使用弥娅 API Server 作为代理端点
        base_url = f"http://127.0.0.1:{miya_api_port}/v1"
        logger.info(f"[OpenClaw] 使用弥娅代理端点: {base_url}")

        models_config = config_data.setdefault("models", {})
        models_config["mode"] = "merge"
        models_config["providers"] = {
            provider_name: {
                "baseUrl": base_url,
                "apiKey": model_info.get("api_key", ""),
                "auth": "api-key",
                "api": "openai-completions",
                "models": [
                    {
                        "id": model_info["model"],
                        "name": model_info["model"],
                        "reasoning": False,
                        "input": ["text"],
                        "cost": {
                            "input": 0,
                            "output": 0,
                            "cacheRead": 0,
                            "cacheWrite": 0,
                        },
                        "contextWindow": 128000,
                        "maxTokens": model_info.get("max_tokens", 4096),
                    }
                ],
            }
        }

        # 设置为默认模型
        agents = config_data.setdefault("agents", {})
        agents.setdefault("defaults", {}).setdefault("model", {})["primary"] = (
            full_model_id
        )

        # === 搜索 / 循环检测 ===
        tools_section = config_data.setdefault("tools", {})
        if "loopDetection" not in tools_section:
            tools_section["loopDetection"] = {
                "enabled": True,
                "historySize": 20,
                "warningThreshold": 4,
                "criticalThreshold": 6,
                "globalCircuitBreakerThreshold": 8,
                "detectors": {
                    "genericRepeat": True,
                    "knownPollNoProgress": True,
                    "pingPong": True,
                },
            }

        OPENCLAW_CONFIG_FILE.write_text(
            json.dumps(config_data, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        # 创建 auth-profiles.json
        auth_profiles_path = (
            OPENCLAW_STATE_DIR / "agents" / "main" / "agent" / "auth-profiles.json"
        )
        auth_profiles_path.parent.mkdir(parents=True, exist_ok=True)
        auth_profiles = {
            f"{provider_name}:default": {
                "provider": provider_name,
                "mode": "api_key",
                "apiKey": model_info.get("api_key", ""),
            }
        }
        auth_profiles_path.write_text(
            json.dumps(auth_profiles, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )

        logger.info(f"[OpenClaw] 已注入弥娅模型配置: model={full_model_id}")
        return True

    except Exception as e:
        logger.error(f"[OpenClaw] 注入配置失败: {e}")
        return False


def get_config_tokens() -> Optional[Dict[str, str]]:
    """从 openclaw.json 读取认证 token"""
    if not OPENCLAW_CONFIG_FILE.exists():
        return None
    try:
        cfg = json.loads(OPENCLAW_CONFIG_FILE.read_text(encoding="utf-8"))
        return {
            "gateway_token": cfg.get("gateway", {}).get("auth", {}).get("token", ""),
            "hooks_token": cfg.get("hooks", {}).get("token", ""),
            "gateway_port": cfg.get("gateway", {}).get("port", DEFAULT_GATEWAY_PORT),
            "hooks_path": cfg.get("hooks", {}).get("path", "/hooks"),
        }
    except Exception as e:
        logger.error(f"[OpenClaw] 读取 token 失败: {e}")
        return None

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIYA 配置加载器

统一从 .env 加载配置，自动注入到各 Provider
支持多配置源：
1. 环境变量 (.env)
2. JSON 配置文件
3. 默认值
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

# 加载 .env
load_dotenv(CONFIG_DIR / ".env")


# ==================== 配置加载器 ====================


class ConfigLoader:
    """配置加载器 - 自动从环境变量加载"""

    _instance: Optional["ConfigLoader"] = None
    _cache: Dict[str, Any] = {}

    def __init__(self):
        self._load_all()

    @classmethod
    def get_instance(cls) -> "ConfigLoader":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    def _load_all(self):
        """加载所有配置"""
        self._load_ai_config()
        self._load_platform_config()

    def _load_ai_config(self):
        """加载 AI 配置"""
        self._cache["ai"] = {
            "max_tokens": int(os.getenv("AI_MAX_TOKENS", "2000")),
            "temperature": float(os.getenv("AI_TEMPERATURE", "0.7")),
            "max_retries": int(os.getenv("AI_REQUEST_MAX_RETRIES", "2")),
            "timeout": int(os.getenv("AI_REQUEST_TIMEOUT", "30")),
            "provider": os.getenv("AI_PROVIDER", "siliconflow"),
            # 密钥
            "siliconflow_api_key": os.getenv("SILICONFLOW_API_KEY", ""),
            "deepseek_api_key": os.getenv("DEEPSEEK_API_KEY", ""),
            "zhipu_api_key": os.getenv("ZHIPU_API_KEY", ""),
            "dashscope_api_key": os.getenv("DASHSCOPE_API_KEY", ""),
            "grok_api_key": os.getenv("GROK_API_KEY", ""),
            "anthropic_api_key": os.getenv("ANTHROPIC_API_KEY", ""),
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            # Base URLs
            "siliconflow_base_url": os.getenv(
                "SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"
            ),
            "deepseek_base_url": os.getenv(
                "DEEPSEEK_API_BASE", "https://api.deepseek.com/v1"
            ),
            "zhipu_base_url": os.getenv(
                "ZHIPU_API_BASE", "https://open.bigmodel.cn/api/paas/v4"
            ),
            "dashscope_base_url": os.getenv(
                "DASHSCOPE_API_BASE",
                "https://dashscope.aliyuncs.com/compatible-mode/v1",
            ),
        }

    def _load_platform_config(self):
        """加载平台配置"""
        self._cache["platform"] = {
            "qq": {
                "onebot_ws_url": os.getenv("QQ_ONEBOT_WS_URL", "ws://localhost:3001"),
                "onebot_token": os.getenv("QQ_ONEBOT_TOKEN", ""),
                "bot_qq": os.getenv("QQ_BOT_QQ", ""),
                "superadmin_qq": os.getenv("QQ_SUPERADMIN_QQ", ""),
            },
            "telegram": {
                "bot_token": os.getenv("TELEGRAM_BOT_TOKEN", ""),
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 尝试从嵌套键获取
        keys = key.split(".")
        value = self._cache
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def get_api_key(self, provider: str) -> str:
        """获取 Provider API 密钥"""
        key_map = {
            "siliconflow": "siliconflow_api_key",
            "deepseek": "deepseek_api_key",
            "zhipu": "zhipu_api_key",
            "dashscope": "dashscope_api_key",
            "grok": "grok_api_key",
            "anthropic": "anthropic_api_key",
            "openai": "openai_api_key",
        }
        env_key = key_map.get(provider, f"{provider}_api_key")
        return os.getenv(env_key.upper(), "")

    def get_base_url(self, provider: str) -> str:
        """获取 Provider Base URL"""
        key_map = {
            "siliconflow": "siliconflow_base_url",
            "deepseek": "deepseek_base_url",
            "zhipu": "zhipu_base_url",
            "dashscope": "dashscope_base_url",
        }
        env_key = key_map.get(provider, f"{provider}_base_url")
        return os.getenv(env_key.upper(), "")


# ==================== 便捷函数 ====================


_config_loader: Optional[ConfigLoader] = None


def get_config() -> ConfigLoader:
    """获取配置加载器"""
    global _config_loader
    if _config_loader is None:
        _config_loader = ConfigLoader()
    return _config_loader


def get_api_key(provider: str) -> str:
    """获取 API 密钥的便捷函数"""
    return get_config().get_api_key(provider)


def get_base_url(provider: str) -> str:
    """获取 Base URL 的便捷函数"""
    return get_config().get_base_url(provider)


# ==================== text_config.json 加载 ====================

# text_config.json 缓存
_text_config_cache: Optional[Dict[str, Any]] = None


def load_text_config(force_reload: bool = False) -> Dict[str, Any]:
    """
    加载 text_config.json 配置（带缓存）

    Args:
        force_reload: 是否强制重新加载

    Returns:
        text_config 配置字典
    """
    global _text_config_cache

    if not force_reload and _text_config_cache is not None:
        return _text_config_cache

    config_path = CONFIG_DIR / "text_config.json"

    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                _text_config_cache = json.load(f)
            logger.debug(f"加载 text_config.json: {config_path}")
            return _text_config_cache
        else:
            logger.warning(f"text_config.json 不存在: {config_path}")
            return {}
    except Exception as e:
        logger.error(f"加载 text_config.json 失败: {e}")
        return {}


def get_text_config_value(key: str, default: Any = None) -> Any:
    """
    获取 text_config.json 中的配置值

    Args:
        key: 配置键（支持点号分隔的嵌套键）
        default: 默认值

    Returns:
        配置值
    """
    config = load_text_config()

    # 支持嵌套键
    keys = key.split(".")
    value = config

    for k in keys:
        if isinstance(value, dict):
            value = value.get(k)
        else:
            return default

    return value if value is not None else default


def get_safety_config() -> Dict[str, Any]:
    """获取安全配置"""
    return load_text_config().get("safety", {})


def get_command_config() -> Dict[str, Any]:
    """获取命令配置"""
    return load_text_config().get("commands", {})


def get_prompt_config() -> Dict[str, Any]:
    """获取提示词配置"""
    return load_text_config().get("prompts", {})


def reload_text_config():
    """重新加载 text_config.json"""
    global _text_config_cache
    _text_config_cache = None
    logger.info("已清除 text_config.json 缓存")


__all__ = [
    "ConfigLoader",
    "get_config",
    "get_api_key",
    "get_base_url",
    "load_text_config",
    "get_text_config_value",
    "get_safety_config",
    "get_command_config",
    "get_prompt_config",
    "reload_text_config",
]

"""统一配置加载器 — 所有模块从此读取 config/text_config.json"""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from core.path_resolver import get_config_dir

logger = logging.getLogger(__name__)

_CONFIG_CACHE: dict[str, Any] | None = None
_CONFIG_PATH = get_config_dir() / "text_config.json"
_JSON_CACHE: dict[str, Any] = {}


def _load_config() -> dict[str, Any]:
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        _CONFIG_CACHE = json.loads(_CONFIG_PATH.read_text(encoding="utf-8")) if _CONFIG_PATH.exists() else {}
    except Exception as e:
        logger.warning("加载 text_config.json 失败: %s", e)
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE


def reload_config() -> dict[str, Any]:
    global _CONFIG_CACHE
    _CONFIG_CACHE = None
    return _load_config()


# ---------- 通用访问 ----------


def get_section(section: str | None = None, default: Any = None) -> Any:
    if section is None:
        return _load_config()
    return _load_config().get(section, default)


def get_value(key: str, default: Any = None) -> Any:
    """支持点号分隔的嵌套键"""
    config = _load_config()
    for k in key.split("."):
        if isinstance(config, dict):
            config = config.get(k)
        else:
            return default
    return config if config is not None else default


# ---------- 模块配置 ----------


def get_emoji_config() -> dict[str, Any]:
    return get_section("emoji_settings", {})


# ---------- JSON 文件加载 ----------


def load_json_config(filename: str, section: str | None = None) -> dict[str, Any]:
    """加载 config/ 目录下的任意 JSON 配置文件"""
    cache_key = f"{filename}:{section or 'all'}"
    if cache_key in _JSON_CACHE:
        return _JSON_CACHE[cache_key]

    path = get_config_dir() / filename
    try:
        if path.exists():
            config = json.loads(path.read_text(encoding="utf-8"))
            result = config.get(section, {}) if section else config
            _JSON_CACHE[cache_key] = result
            return result
    except Exception as e:
        logger.warning("加载 %s 失败: %s", filename, e)
    return {}


def clear_cache(filename: str = "") -> None:
    global _CONFIG_CACHE
    if filename:
        keys = [k for k in _JSON_CACHE if k.startswith(filename)]
        for k in keys:
            del _JSON_CACHE[k]
    else:
        _CONFIG_CACHE = None
        _JSON_CACHE.clear()
    logger.info("配置缓存已清除")

"""
弥娅全局配置缓存 — miya_config.yaml 单例加载

消除 5 个模块重复读取+解析同一文件的性能瓶颈。
所有模块通过此模块获取配置，文件仅读取+解析一次。
"""

from __future__ import annotations

import threading
from pathlib import Path


_CFG_CACHE: dict | None = None
_CFG_CACHE_LOCK = threading.Lock()
_CONFIG_PATH: Path | None = None


def _resolve_config_path() -> Path:
    global _CONFIG_PATH
    if _CONFIG_PATH is None:
        from pathlib import Path as _Path

        _CONFIG_PATH = _Path(__file__).resolve().parent.parent / "config" / "miya_config.yaml"
    return _CONFIG_PATH


def get_miya_config(force_reload: bool = False) -> dict:
    global _CFG_CACHE
    if _CFG_CACHE is not None and not force_reload:
        return _CFG_CACHE

    with _CFG_CACHE_LOCK:
        if _CFG_CACHE is not None and not force_reload:
            return _CFG_CACHE

        import yaml as _yaml

        cfg_path = _resolve_config_path()
        try:
            _CFG_CACHE = _yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        except Exception:
            _CFG_CACHE = {}
        return _CFG_CACHE


def get_config_section(section: str, default: dict | None = None) -> dict:
    cfg = get_miya_config()
    return cfg.get(section, default or {})


def get_config_value(section: str, key: str, default=None):
    section_data = get_config_section(section)
    return section_data.get(key, default)


def clear_config_cache():
    global _CFG_CACHE
    with _CFG_CACHE_LOCK:
        _CFG_CACHE = None

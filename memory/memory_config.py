"""
弥娅记忆系统 — 统一配置加载器

替代各模块独立的 text_config.json 读取，启动时加载一次，内存共享。
消除 9 个模块各自 I/O + JSON parse 的重复开销。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict

logger = logging.getLogger(__name__)

_CONFIG_PATH = None
_CACHE: Dict[str, Any] = {}


def _get_config_path() -> Path:
    global _CONFIG_PATH
    if _CONFIG_PATH is None:
        _CONFIG_PATH = Path(__file__).parent.parent / "config" / "text_config.json"
    return _CONFIG_PATH


def load_memory_config(force_reload: bool = False) -> Dict[str, Any]:
    """加载 text_config.json 的 memory 相关配置（带进程级缓存）"""
    global _CACHE
    if _CACHE and not force_reload:
        return _CACHE

    config_path = _get_config_path()
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                _CACHE = json.load(f)
            logger.debug(f"[MemoryConfig] 配置已加载: {config_path}")
        else:
            logger.warning(f"[MemoryConfig] 配置文件不存在: {config_path}")
            _CACHE = {}
    except Exception as e:
        logger.error(f"[MemoryConfig] 加载失败: {e}")
        _CACHE = {}

    return _CACHE


def get_memory_section(section: str, default: Dict = None) -> Dict:
    """获取 text_config.json 中的指定 memory 配置段（带缓存）

    使用方式替代原来的：
        config = json.load(open("config/text_config.json"))
        section_cfg = config.get("working_memory", {})

    改为：
        section_cfg = get_memory_section("working_memory")
    """
    if default is None:
        default = {}
    config = load_memory_config()
    return config.get(section, default)


def get_text_config_value(*keys: str, default: Any = None) -> Any:
    """深层获取配置值：get_text_config_value('cognitive_engine', 'topic_keywords')

    如果 keys 为空，返回整个配置。
    """
    config = load_memory_config()
    current = config
    for key in keys:
        if isinstance(current, dict):
            current = current.get(key)
        else:
            return default
        if current is None:
            return default
    return current


def reload_config() -> Dict[str, Any]:
    """强制重载配置（用于热更新）"""
    return load_memory_config(force_reload=True)

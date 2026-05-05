"""公共配置加载工具 — 委托到 config.config_utils（单一缓存）"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

from config.config_utils import (
    _load_config,
    reload_config as _shared_reload,
    get_section,
    get_value,
    load_json_config as _shared_load_json,
    clear_cache,
    get_chatbot_keywords,
    get_emotion_keywords,
    get_working_memory_config,
    get_lifebook_config,
    get_historian_config,
    get_cognitive_engine_config,
    get_search_strategy_config,
    get_security_config,
)

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"


def load_text_config(section: Optional[str] = None, use_cache: bool = True) -> Dict:
    return get_section(section, {}) if section else _load_config()


def load_json_config(
    filename: str, section: Optional[str] = None, use_cache: bool = True
) -> Dict:
    return _shared_load_json(filename, section)


def get_config_value(
    key: str, default: Any = None, section: Optional[str] = None
) -> Any:
    if section:
        return get_section(section, {}).get(key, default)
    return get_value(key, default)


def clear_config_cache():
    clear_cache()


def reload_config(filename: str = "text_config.json"):
    if filename == "text_config.json":
        _shared_reload()
    else:
        clear_cache(filename)

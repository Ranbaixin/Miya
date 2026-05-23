"""
弥娅系统 - 配置管理
"""

import json
from pathlib import Path
from typing import Any, Dict


def get_miya_root() -> Path:
    """获取 Miya 根目录"""
    return Path(__file__).parent.parent


def get_data_dir() -> Path:
    """获取数据目录"""
    return get_miya_root() / "data"


def get_config_path() -> Path:
    """获取配置路径"""
    return get_data_dir() / "config"


# 默认配置
DEFAULT_CONFIG = {
    "version": "6.0.0",
    "dashboard": {
        "enable": True,
        "username": "miya",
        "password": "miya",
        "host": "0.0.0.0",
        "port": 6185,
    },
    "provider": [],
    "platform": [],
    "log_level": "INFO",
}


def get_miya_config() -> Dict[str, Any]:
    """获取弥娅配置"""
    config_path = get_config_path() / "config.json"

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            pass

    return DEFAULT_CONFIG.copy()


def save_miya_config(config: Dict[str, Any]):
    """保存配置"""
    config_path = get_config_path() / "config.json"
    config_path.parent.mkdir(exist_ok=True)

    with open(config_path, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


__all__ = ["get_miya_config", "save_miya_config", "DEFAULT_CONFIG"]

"""
公共配置加载工具
统一加载 text_config.json 和其他配置文件，避免重复读取磁盘
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
CONFIG_DIR = PROJECT_ROOT / "config"

# 配置缓存
_config_cache: Dict[str, Dict] = {}


def load_text_config(section: Optional[str] = None, use_cache: bool = True) -> Dict:
    """
    加载 text_config.json 配置

    Args:
        section: 配置节名称，如果为None则返回整个配置
        use_cache: 是否使用缓存

    Returns:
        配置字典
    """
    cache_key = f"text_config:{section or 'all'}"

    if use_cache and cache_key in _config_cache:
        return _config_cache[cache_key]

    config_path = CONFIG_DIR / "text_config.json"
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            if section:
                result = config.get(section, {})
            else:
                result = config

            if use_cache:
                _config_cache[cache_key] = result

            return result
    except Exception as e:
        logger.warning(f"[配置加载] 加载 text_config.json 失败: {e}")

    return {}


def load_json_config(
    filename: str, section: Optional[str] = None, use_cache: bool = True
) -> Dict:
    """
    加载指定的JSON配置文件

    Args:
        filename: 配置文件名（不含路径）
        section: 配置节名称，如果为None则返回整个配置
        use_cache: 是否使用缓存

    Returns:
        配置字典
    """
    cache_key = f"{filename}:{section or 'all'}"

    if use_cache and cache_key in _config_cache:
        return _config_cache[cache_key]

    config_path = CONFIG_DIR / filename
    try:
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            if section:
                result = config.get(section, {})
            else:
                result = config

            if use_cache:
                _config_cache[cache_key] = result

            return result
    except Exception as e:
        logger.warning(f"[配置加载] 加载 {filename} 失败: {e}")

    return {}


def get_config_value(
    key: str, default: Any = None, section: Optional[str] = None
) -> Any:
    """
    获取配置值

    Args:
        key: 配置键
        default: 默认值
        section: 配置节名称

    Returns:
        配置值
    """
    config = load_text_config(section)
    return config.get(key, default)


def clear_config_cache():
    """清除配置缓存"""
    global _config_cache
    _config_cache.clear()
    logger.info("[配置加载] 配置缓存已清除")


def reload_config(filename: str = "text_config.json"):
    """
    重新加载指定配置文件

    Args:
        filename: 配置文件名
    """
    # 清除相关缓存
    keys_to_remove = [k for k in _config_cache if k.startswith(filename)]
    for key in keys_to_remove:
        del _config_cache[key]

    logger.info(f"[配置加载] 已清除 {filename} 的缓存")


# 便捷函数
def get_chatbot_keywords() -> list:
    """获取聊天机器人关键词"""
    return get_config_value("auto_respond", [], "chatbot_keywords")


def get_emotion_keywords() -> Dict[str, list]:
    """获取情绪关键词"""
    return load_text_config("emotion_keywords")


def get_working_memory_config() -> Dict:
    """获取工作记忆配置"""
    return load_text_config("working_memory")


def get_lifebook_config() -> Dict:
    """获取LifeBook配置"""
    return load_text_config("lifebook")


def get_historian_config() -> Dict:
    """获取历史记录配置"""
    return load_text_config("historian")


def get_cognitive_engine_config() -> Dict:
    """获取认知引擎配置"""
    return load_text_config("cognitive_engine")


def get_search_strategy_config() -> Dict:
    """获取搜索策略配置"""
    return load_text_config("search_strategy")


def get_security_config() -> Dict:
    """获取安全配置"""
    return load_text_config("security")

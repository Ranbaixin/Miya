"""
弥娅配置读取辅助工具

统一从 text_config.json 和 qq_config.yaml 读取配置，
提供带默认值的 getter 函数，避免在代码中硬编码。
"""

from __future__ import annotations

import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parent


def reload_config() -> None:
    """清除配置缓存（热重载时调用）——兼容旧版 reload_config 导入"""
    _load_text_config.cache_clear()
    _load_qq_config.cache_clear()
    logger.info("配置缓存已清除")


def get_section(section: str = "", default: Any = None) -> Any:
    """从 text_config.json 读取整个配置节 ——兼容旧版无参调用"""
    if not section:
        return _load_text_config()
    return get_text(section, default=default)


def _load_config(config_path: str = "") -> dict:
    """兼容旧版 tests/conftest.py 导入"""
    return _load_text_config()


def get_value(section: str, key: str, default: Any = None) -> Any:
    """从 text_config.json 按节+键读取值 ——兼容旧版导入"""
    return get_text(section, key, default=default)


@lru_cache(maxsize=1)
def _load_text_config() -> dict:
    path = _CONFIG_DIR / "text_config.json"
    if path.exists():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as e:
            logger.warning(f"读取 text_config.json 失败: {e}")
    return {}


@lru_cache(maxsize=1)
def _load_qq_config() -> dict:
    path = _CONFIG_DIR / "qq_config.yaml"
    if path.exists():
        try:
            import yaml

            return yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        except Exception as e:
            logger.warning(f"读取 qq_config.yaml 失败: {e}")
    return {}


def get_text(*keys: str, default: Any = None) -> Any:
    """从 text_config.json 按路径读取值，支持默认值"""
    cfg = _load_text_config()
    node = cfg
    for k in keys:
        if isinstance(node, dict):
            node = node.get(k)
            if node is None:
                return default
        else:
            return default
    return node


def get_text_message(section: str, key: str, **kwargs) -> str:
    """读取 text_config.json 中的消息模板并格式化，优先查找 section.messages.key，回退到 section.key"""
    template = get_text(section, "messages", key, default=None)
    if template is None:
        template = get_text(section, key, default="")
    if template and kwargs:
        try:
            return template.format(**kwargs)
        except KeyError:
            return template
    return str(template)


def get_qq_config(*keys: str, default: Any = None) -> Any:
    """从 qq_config.yaml 按路径读取值"""
    cfg = _load_qq_config()
    node = cfg
    for k in keys:
        if isinstance(node, dict):
            node = node.get(k)
            if node is None:
                return default
        else:
            return default
    return node


def get_knowledge_config(key: str = "", default: Any = None) -> Any:
    """读取知识库配置"""
    if key:
        return get_qq_config("knowledge_base", key, default=default)
    return get_qq_config("knowledge_base", default={})


def get_pipeline_config(key: str = "", default: Any = None) -> Any:
    """读取管线配置"""
    if key:
        return get_qq_config("pipelines", key, default=default)
    return get_qq_config("pipelines", default={})


def get_cognitive_config(key: str = "", default: Any = None) -> Any:
    """读取认知侧写配置"""
    if key:
        return get_qq_config("cognitive", key, default=default)
    return get_qq_config("cognitive", default={})


def get_file_analysis_config(key: str = "", default: Any = None) -> Any:
    """读取文件分析配置"""
    if key:
        return get_qq_config("file_analysis", key, default=default)
    return get_qq_config("file_analysis", default={})


def get_github_config(key: str = "", default: Any = None) -> Any:
    """读取 GitHub 配置"""
    if key:
        return get_qq_config("github", key, default=default)
    return get_qq_config("github", default={})


def get_command_message(key: str, **kwargs) -> str:
    """读取新版斜杠命令系统的消息模板（来自 command_responses 节）"""
    return get_text_message("command_responses", key, **kwargs)

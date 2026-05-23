#!/usr/bin/env python3
"""
统一QQ配置加载器
使用弥娅的统一配置系统，从.env文件加载QQ配置
"""

import logging
import os
import sys
from typing import Any, Dict, Optional

# 添加项目根目录到Python路径
project_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
sys.path.insert(0, project_root)

logger = logging.getLogger(__name__)


class UnifiedQQConfig:
    """统一QQ配置管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._config = None
        self._settings = None
        self._initialized = True

    def initialize(self):
        """初始化配置"""
        try:
            # 尝试导入Settings类
            from config.settings import Settings

            self._settings = Settings()
            logger.info("[UnifiedQQConfig] 使用统一的Settings配置系统")

            # 获取QQ配置
            self._config = self._settings.get("qq", {})

            # 如果没有QQ配置，使用默认值
            if not self._config:
                logger.warning("[UnifiedQQConfig] 未找到QQ配置，使用默认值")
                self._config = self._get_default_config()
            else:
                # 确保配置有完整的结构
                self._config = self._apply_defaults(self._config)
                logger.info("[UnifiedQQConfig] 配置加载成功")

        except ImportError as e:
            logger.warning(f"[UnifiedQQConfig] 无法导入Settings: {e}")
            # 使用环境变量直接加载
            self._load_from_env()
        except Exception as e:
            logger.error(f"[UnifiedQQConfig] 配置初始化失败: {e}")
            self._config = self._get_default_config()

    def _load_from_env(self):
        """直接从环境变量加载配置"""
        logger.info("[UnifiedQQConfig] 从环境变量直接加载配置")

        import os

        from dotenv import load_dotenv

        # 优先使用 config/.env（统一配置位置）
        env_path = os.path.join(project_root, "config", ".env")

        if os.path.exists(env_path):
            load_dotenv(env_path, override=True)
            logger.info(f"[UnifiedQQConfig] 从 {env_path} 加载环境变量")
        else:
            # 备选：项目根目录
            env_path = os.path.join(project_root, ".env")
            if os.path.exists(env_path):
                load_dotenv(env_path, override=True)
                logger.info(f"[UnifiedQQConfig] 从 {env_path} 加载环境变量")
            else:
                logger.warning("[UnifiedQQConfig] 未找到.env文件，使用默认配置")

        self._config = {
            # 基础连接配置
            "onebot_ws_url": os.getenv("QQ_ONEBOT_WS_URL", "ws://localhost:3001"),
            "onebot_token": os.getenv("QQ_ONEBOT_TOKEN", ""),
            "bot_qq": int(os.getenv("QQ_BOT_QQ", 0)),
            "superadmin_qq": int(os.getenv("QQ_SUPERADMIN_QQ", 0)),
            "group_whitelist": os.getenv("QQ_GROUP_WHITELIST", ""),
            "group_blacklist": os.getenv("QQ_GROUP_BLACKLIST", ""),
            "user_whitelist": os.getenv("QQ_USER_WHITELIST", ""),
            "user_blacklist": os.getenv("QQ_USER_BLACKLIST", ""),
            # 连接设置
            "reconnect_interval": float(os.getenv("QQ_RECONNECT_INTERVAL", "5.0")),
            "ping_interval": int(os.getenv("QQ_PING_INTERVAL", "20")),
            "ping_timeout": int(os.getenv("QQ_PING_TIMEOUT", "30")),
            "max_message_size": int(os.getenv("QQ_MAX_MESSAGE_SIZE", "104857600")),
        }

        # 应用默认值
        self._config = self._apply_defaults(self._config)

    def _get_default_config(self) -> Dict[str, Any]:
        """获取默认配置"""
        return {
            # 基础连接配置
            "onebot_ws_url": "ws://localhost:3001",
            "onebot_token": "",
            "bot_qq": 0,
            "superadmin_qq": 0,
            "group_whitelist": "",
            "group_blacklist": "",
            "user_whitelist": "",
            "user_blacklist": "",
            # 连接设置
            "reconnect_interval": 5.0,
            "ping_interval": 20,
            "ping_timeout": 30,
            "max_message_size": 104857600,
            # 多媒体功能配置
            "multimedia": {
                "image": {
                    "max_size": 10485760,  # 10MB
                    "allowed_formats": [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".gif",
                        ".bmp",
                        ".webp",
                    ],
                },
                "file": {
                    "max_size": 52428800,  # 50MB
                },
            },
            # 图片识别配置
            "image_recognition": {
                "ocr_enabled": True,
                "ocr_engine": "auto",
            },
            # 主动聊天配置
            "active_chat": {
                "enabled": True,
                "max_daily_messages": 10,
                "min_interval": 300,
            },
            # 任务调度配置
            "task_scheduler": {
                "enabled": True,
            },
        }

    def _apply_defaults(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """应用默认值到配置"""
        defaults = self._get_default_config()

        def _merge_dict(dest: Dict, src: Dict) -> Dict:
            for key, value in src.items():
                if key not in dest:
                    dest[key] = value
                elif isinstance(value, dict) and isinstance(dest.get(key), dict):
                    dest[key] = _merge_dict(dest[key], value)
            return dest

        return _merge_dict(config, defaults)

    def get_config(self) -> Dict[str, Any]:
        """获取完整配置"""
        if self._config is None:
            self.initialize()
        return self._config

    def get(self, key: str, default: Any = None) -> Any:
        """获取配置值，支持点分路径"""
        config = self.get_config()

        if "." in key:
            parts = key.split(".")
            value = config
            for part in parts:
                if isinstance(value, dict):
                    value = value.get(part, {})
                else:
                    return default
            return value if value != {} else default
        else:
            return config.get(key, default)

    def get_connection_config(self) -> Dict[str, Any]:
        """获取连接配置"""
        return {
            "onebot_ws_url": self.get("onebot_ws_url"),
            "onebot_token": self.get("onebot_token"),
            "bot_qq": self.get("bot_qq"),
            "superadmin_qq": self.get("superadmin_qq"),
            "reconnect_interval": self.get("reconnect_interval"),
            "ping_interval": self.get("ping_interval"),
            "ping_timeout": self.get("ping_timeout"),
            "max_message_size": self.get("max_message_size"),
        }

    def get_multimedia_config(self) -> Dict[str, Any]:
        """获取多媒体配置"""
        return self.get("multimedia", {})

    def get_image_recognition_config(self) -> Dict[str, Any]:
        """获取图片识别配置"""
        return self.get("image_recognition", {})

    def get_active_chat_config(self) -> Dict[str, Any]:
        """获取主动聊天配置"""
        return self.get("active_chat", {})

    def get_task_scheduler_config(self) -> Dict[str, Any]:
        """获取任务调度配置"""
        return self.get("task_scheduler", {})

    def validate_config(self) -> tuple[bool, list[str]]:
        """验证配置有效性"""
        errors = []
        config = self.get_config()

        # 检查OneBot配置
        if not config.get("onebot_ws_url"):
            errors.append("OneBot WebSocket地址未配置")
        elif not config["onebot_ws_url"].startswith("ws://") and not config[
            "onebot_ws_url"
        ].startswith("wss://"):
            errors.append("OneBot WebSocket地址格式不正确，必须以ws://或wss://开头")

        # 检查连接配置
        if config.get("reconnect_interval", 0) <= 0:
            errors.append("重连间隔配置不正确")
        if config.get("ping_interval", 0) <= 0:
            errors.append("心跳间隔配置不正确")

        # 检查多媒体配置
        multimedia_config = config.get("multimedia", {})
        image_config = multimedia_config.get("image", {})
        file_config = multimedia_config.get("file", {})

        if image_config.get("max_size", 0) <= 0:
            errors.append("图片最大大小配置不正确")
        if file_config.get("max_size", 0) <= 0:
            errors.append("文件最大大小配置不正确")

        return len(errors) == 0, errors

    def reload(self) -> bool:
        """重新加载配置"""
        try:
            if self._settings:
                self._settings.reload()
                self._config = self._settings.get("qq", {})
                self._config = self._apply_defaults(self._config)
            else:
                self._load_from_env()

            logger.info("[UnifiedQQConfig] 配置重新加载成功")
            return True
        except Exception as e:
            logger.error(f"[UnifiedQQConfig] 配置重新加载失败: {e}")
            return False


# 全局配置实例
_global_unified_config: Optional[UnifiedQQConfig] = None


def get_unified_config() -> UnifiedQQConfig:
    """获取全局统一配置实例"""
    global _global_unified_config
    if _global_unified_config is None:
        _global_unified_config = UnifiedQQConfig()
        _global_unified_config.initialize()
    return _global_unified_config


def get_qq_config(key: Optional[str] = None, default: Any = None) -> Any:
    """获取QQ配置（快捷函数）"""
    config = get_unified_config()
    if key is None:
        return config.get_config()
    return config.get(key, default)


def get_connection_config() -> Dict[str, Any]:
    """获取连接配置（快捷函数）"""
    return get_unified_config().get_connection_config()


def get_multimedia_config() -> Dict[str, Any]:
    """获取多媒体配置（快捷函数）"""
    return get_unified_config().get_multimedia_config()


def validate_config() -> tuple[bool, list[str]]:
    """验证配置（快捷函数）"""
    return get_unified_config().validate_config()

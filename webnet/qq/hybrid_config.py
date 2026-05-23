#!/usr/bin/env python3
"""
弥娅QQ端混合配置加载器

设计原则：
1. 敏感配置从.env文件加载 (连接信息、API密钥等)
2. 功能配置从qq_config.yaml文件加载 (详细设置、规则等)
3. 提供统一的配置访问接口
4. 支持配置验证和默认值
5. 保持向后兼容性
"""

import builtins
import contextlib
import logging
import os
from pathlib import Path
from typing import Dict

import yaml

logger = logging.getLogger(__name__)


class QQHybridConfig:
    """QQ混合配置管理器"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, cache_manager=None):
        if self._initialized:
            return

        self.cache_manager = cache_manager  # 缓存管理器(可选)
        # 注释: 配置缓存已迁移到QQCacheManager
        # 旧实现: self._cached_full_config = None (手动缓存)
        # 新实现: 使用 cache_manager.set_config() 和 get_config()

        self._project_root = Path(__file__).parent.parent.parent.parent
        self._env_config = {}
        self._yaml_config = {}
        self._initialized = False

        self._load_configs()
        self._initialized = True

    def _load_configs(self):
        """加载所有配置源"""
        try:
            # 1. 从.env文件加载敏感配置
            self._load_env_config()

            # 2. 从YAML文件加载功能配置
            self._load_yaml_config()

            # 3. 合并配置并验证
            self._merge_and_validate()

            logger.info("[QQHybridConfig] 混合配置加载成功")

        except Exception as e:
            logger.error(f"[QQHybridConfig] 配置加载失败: {e}")
            self._set_defaults()

    def _load_env_config(self):
        """从.env文件加载敏感配置"""
        try:
            from dotenv import load_dotenv

            # 尝试多个可能的.env文件位置
            env_paths = [
                self._project_root / ".env",
                self._project_root / "config" / ".env",
            ]

            env_loaded = False
            for env_path in env_paths:
                if env_path.exists():
                    load_dotenv(env_path, override=True)
                    logger.info(f"[QQHybridConfig] 从 {env_path} 加载环境变量")
                    env_loaded = True
                    break

            if not env_loaded:
                logger.warning("[QQHybridConfig] 未找到.env文件，使用默认配置")

            # 从环境变量提取QQ配置
            self._env_config = {
                "onebot_ws_url": os.getenv("QQ_ONEBOT_WS_URL", "ws://localhost:3001"),
                "onebot_token": os.getenv("QQ_ONEBOT_TOKEN", ""),
                "bot_qq": int(os.getenv("QQ_BOT_QQ", 0) or 0),
                "superadmin_qq": int(os.getenv("QQ_SUPERADMIN_QQ", 0) or 0),
                "group_whitelist": os.getenv("QQ_GROUP_WHITELIST", ""),
                "group_blacklist": os.getenv("QQ_GROUP_BLACKLIST", ""),
                "user_whitelist": os.getenv("QQ_USER_WHITELIST", ""),
                "user_blacklist": os.getenv("QQ_USER_BLACKLIST", ""),
                # 连接设置
                "reconnect_interval": float(os.getenv("QQ_RECONNECT_INTERVAL", "5.0")),
                "ping_interval": int(os.getenv("QQ_PING_INTERVAL", "20")),
                "ping_timeout": int(os.getenv("QQ_PING_TIMEOUT", "30")),
                "max_message_size": int(os.getenv("QQ_MAX_MESSAGE_SIZE", "104857600")),
                # 基础功能开关
                "ocr_enabled": os.getenv("QQ_OCR_ENABLED", "true").lower() == "true",
                "active_chat_enabled": os.getenv(
                    "QQ_ACTIVE_CHAT_ENABLED", "true"
                ).lower()
                == "true",
                "task_scheduler_enabled": os.getenv(
                    "QQ_TASK_SCHEDULER_ENABLED", "true"
                ).lower()
                == "true",
            }

        except Exception as e:
            logger.error(f"[QQHybridConfig] 加载.env配置失败: {e}")
            self._env_config = {}

    def _load_yaml_config(self):
        """从YAML文件加载功能配置"""
        try:
            # 尝试多个可能的YAML文件位置
            yaml_paths = [
                self._project_root / "config" / "qq_config.yaml",
                self._project_root / "qq_config.yaml",
            ]

            yaml_path = None
            for path in yaml_paths:
                if path.exists():
                    yaml_path = path
                    break

            if not yaml_path:
                logger.warning(
                    "[QQHybridConfig] 未找到qq_config.yaml文件，使用默认功能配置"
                )
                self._yaml_config = {}
                return

            with open(yaml_path, "r", encoding="utf-8") as f:
                self._yaml_config = yaml.safe_load(f) or {}

            logger.info(f"[QQHybridConfig] 从 {yaml_path} 加载YAML配置")

        except Exception as e:
            logger.error(f"[QQHybridConfig] 加载YAML配置失败: {e}")
            self._yaml_config = {}

    def _merge_and_validate(self):
        """合并并验证配置"""
        try:
            # 从YAML配置中提取QQ配置部分
            yaml_qq_config = self._yaml_config.get("qq", {})

            # 创建合并配置
            merged_config = {
                # 1. 敏感配置优先从.env获取
                "onebot_ws_url": self._env_config.get("onebot_ws_url"),
                "onebot_token": self._env_config.get("onebot_token"),
                "bot_qq": self._env_config.get("bot_qq"),
                "superadmin_qq": self._env_config.get("superadmin_qq"),
                # 2. 连接设置
                "connection": {
                    "reconnect_interval": self._env_config.get("reconnect_interval"),
                    "ping_interval": self._env_config.get("ping_interval"),
                    "ping_timeout": self._env_config.get("ping_timeout"),
                    "max_message_size": self._env_config.get("max_message_size"),
                },
                # 3. 访问控制
                "access_control": {
                    "group_whitelist": self._parse_qq_list(
                        self._env_config.get("group_whitelist", "")
                    ),
                    "group_blacklist": self._parse_qq_list(
                        self._env_config.get("group_blacklist", "")
                    ),
                    "user_whitelist": self._parse_qq_list(
                        self._env_config.get("user_whitelist", "")
                    ),
                    "user_blacklist": self._parse_qq_list(
                        self._env_config.get("user_blacklist", "")
                    ),
                    "enabled": False,  # 默认禁用，除非配置了列表
                },
                # 4. 从YAML获取详细功能配置
                "multimedia": yaml_qq_config.get("multimedia", {}),
                "image_recognition": yaml_qq_config.get("image_recognition", {}),
                "active_chat": yaml_qq_config.get("active_chat", {}),
                "task_scheduler": yaml_qq_config.get("task_scheduler", {}),
                "performance": yaml_qq_config.get("performance", {}),
                "logging": yaml_qq_config.get("logging", {}),
                "debug": yaml_qq_config.get("debug", {}),
            }

            # 5. 覆盖YAML中的基础开关
            if "image_recognition" in merged_config:
                # 确保ocr配置存在
                if "ocr" not in merged_config["image_recognition"]:
                    merged_config["image_recognition"]["ocr"] = {}

                merged_config["image_recognition"]["ocr"]["enabled"] = (
                    self._env_config.get("ocr_enabled", True)
                )

            if "active_chat" in merged_config:
                merged_config["active_chat"]["enabled"] = self._env_config.get(
                    "active_chat_enabled", True
                )

            if "task_scheduler" in merged_config:
                merged_config["task_scheduler"]["enabled"] = self._env_config.get(
                    "task_scheduler_enabled", True
                )

            # 6. 验证必填配置
            self._validate_config(merged_config)

            # 7. 设置默认值
            self._set_default_values(merged_config)

            # 8. 缓存配置到QQCacheManager
            if self.cache_manager:
                try:
                    self.cache_manager.set_config("qq_hybrid_config", merged_config)
                except Exception as e:
                    logger.warning(f"[QQHybridConfig] 缓存配置失败: {e}")

        except Exception as e:
            logger.error(f"[QQHybridConfig] 合并配置失败: {e}")

            # 8. 缓存默认配置
            default_config = self._get_default_config()
            if self.cache_manager:
                with contextlib.suppress(builtins.BaseException):
                    self.cache_manager.set_config("qq_hybrid_config", default_config)

    def _parse_qq_list(self, list_str: str) -> list:
        """解析逗号分隔的QQ列表"""
        if not list_str:
            return []

        try:
            return [int(qq.strip()) for qq in list_str.split(",") if qq.strip()]
        except ValueError:
            logger.warning(f"[QQHybridConfig] 无法解析QQ列表: {list_str}")
            return []

    def _validate_config(self, config: Dict):
        """验证配置"""
        # 验证WebSocket地址
        ws_url = config.get("onebot_ws_url")
        if ws_url and not (ws_url.startswith("ws://") or ws_url.startswith("wss://")):
            logger.warning(f"[QQHybridConfig] WebSocket地址格式可能不正确: {ws_url}")

        # 验证数字类型配置
        connection = config.get("connection", {})
        if connection.get("reconnect_interval", 0) <= 0:
            logger.warning("[QQHybridConfig] 重连间隔应为正数")

        # 验证功能配置
        self._validate_feature_configs(config)

    def _validate_feature_configs(self, config: Dict):
        """验证功能配置"""
        # 验证多媒体配置
        multimedia = config.get("multimedia", {})
        if "image" in multimedia:
            image_config = multimedia["image"]
            if image_config.get("max_size", 0) <= 0:
                logger.warning("[QQHybridConfig] 图片最大大小应大于0")

        # 验证主动聊天配置
        active_chat = config.get("active_chat", {})
        limits = active_chat.get("limits", {})
        if limits.get("max_daily_messages", 0) < 0:
            logger.warning("[QQHybridConfig] 每天最多消息数不能为负数")

    def _set_default_values(self, config: Dict):
        """设置缺失的默认值"""
        # 连接配置默认值
        if "connection" not in config:
            config["connection"] = {}

        connection = config["connection"]
        connection.setdefault("reconnect_interval", 5.0)
        connection.setdefault("ping_interval", 20)
        connection.setdefault("ping_timeout", 30)
        connection.setdefault("max_message_size", 104857600)

        # 访问控制默认值
        if "access_control" not in config:
            config["access_control"] = {}

        access_control = config["access_control"]
        access_control.setdefault("enabled", False)
        access_control.setdefault("group_whitelist", [])
        access_control.setdefault("group_blacklist", [])
        access_control.setdefault("user_whitelist", [])
        access_control.setdefault("user_blacklist", [])

        # 多媒体配置默认值
        if "multimedia" not in config:
            config["multimedia"] = {
                "image": {
                    "max_size": 10485760,
                    "allowed_formats": [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".gif",
                        ".bmp",
                        ".webp",
                    ],
                    "auto_resize": True,
                    "max_width": 1920,
                    "max_height": 1080,
                    "quality": 85,
                },
                "file": {
                    "max_size": 52428800,
                    "allowed_formats": {
                        "text": [".txt", ".log", ".md", ".json", ".xml", ".html"],
                        "document": [".pdf", ".doc", ".docx"],
                    },
                },
            }

    def _set_defaults(self):
        """设置完全默认配置"""
        self._cached_full_config = self._get_default_config()
        logger.warning("[QQHybridConfig] 使用完全默认配置")

    def _get_default_config(self) -> Dict:
        """获取完全默认配置"""
        return {
            "onebot_ws_url": "ws://localhost:3001",
            "onebot_token": "",
            "bot_qq": 0,
            "superadmin_qq": 0,
            "connection": {
                "reconnect_interval": 5.0,
                "ping_interval": 20,
                "ping_timeout": 30,
                "max_message_size": 104857600,
            },
            "access_control": {
                "enabled": False,
                "group_whitelist": [],
                "group_blacklist": [],
                "user_whitelist": [],
                "user_blacklist": [],
            },
            "multimedia": {
                "image": {
                    "max_size": 10485760,
                    "allowed_formats": [
                        ".jpg",
                        ".jpeg",
                        ".png",
                        ".gif",
                        ".bmp",
                        ".webp",
                    ],
                    "auto_resize": True,
                    "max_width": 1920,
                    "max_height": 1080,
                    "quality": 85,
                },
                "file": {
                    "max_size": 52428800,
                    "allowed_formats": {
                        "text": [".txt", ".log", ".md", ".json", ".xml", ".html"],
                        "document": [".pdf", ".doc", ".docx"],
                    },
                },
            },
            "image_recognition": {
                "ocr": {
                    "enabled": True,
                    "engine": "auto",
                    "languages": ["chi_sim", "eng"],
                    "confidence_threshold": 0.7,
                }
            },
            "active_chat": {
                "enabled": True,
                "limits": {
                    "max_daily_messages": 10,
                    "min_interval": 300,
                },
            },
            "task_scheduler": {
                "enabled": True,
            },
        }

    def get_config(self) -> Dict:
        """获取完整配置

        优先次序:
        1. 先会qcache_manager获取 (如果可用)
        2. 没有的情况下调用_get_default_config()
        3. 之后缓存结果
        """
        # 尝试从缓存获取
        if self.cache_manager:
            try:
                cached_config = self.cache_manager.get_config("qq_hybrid_config")
                if cached_config is not None:
                    return cached_config.copy()
            except Exception as e:
                logger.debug(f"[QQHybridConfig] 从缓存获取配置失败: {e}")

        # 从默认配置获取
        config = self._get_default_config()

        # 将配置缓存起来
        if self.cache_manager:
            try:
                self.cache_manager.set_config("qq_hybrid_config", config)
            except Exception as e:
                logger.debug(f"[QQHybridConfig] 缓存配置失败: {e}")

        return config.copy()

    def get_sensitive_config(self) -> Dict:
        """仅获取敏感配置（来自.env）"""
        return {
            "onebot_ws_url": self._env_config.get("onebot_ws_url"),
            "onebot_token": self._env_config.get("onebot_token"),
            "bot_qq": self._env_config.get("bot_qq"),
            "superadmin_qq": self._env_config.get("superadmin_qq"),
        }

    def get_feature_config(self, feature: str) -> Dict:
        """获取特定功能的配置"""
        config = self.get_config()

        feature_map = {
            "multimedia": config.get("multimedia", {}),
            "image_recognition": config.get("image_recognition", {}),
            "active_chat": config.get("active_chat", {}),
            "task_scheduler": config.get("task_scheduler", {}),
            "performance": config.get("performance", {}),
            "logging": config.get("logging", {}),
            "debug": config.get("debug", {}),
        }

        return feature_map.get(feature, {})

    def get_model_config(self, model_type: str = None) -> Dict:
        """获取模型配置

        参数:
            model_type: 模型类型 (chat, ocr, vision, safety)
            如果为None，返回所有模型配置
        """
        try:
            # 尝试从统一模型池获取配置
            from core.model_pool_manager import get_model_pool, select_model_for_task

            pool = get_model_pool()

            if model_type:
                # 获取特定类型的模型
                model = pool.select_model_for_task(
                    self._get_task_type(model_type), "qq"
                )
                if model:
                    return self._model_config_to_dict(model)
                else:
                    # 回退到本地配置
                    return self._get_local_model_config(model_type)
            else:
                # 返回所有QQ端模型
                qq_models = {}
                for model_type in ["chat", "ocr", "vision", "safety"]:
                    model = pool.select_model_for_task(
                        self._get_task_type(model_type), "qq"
                    )
                    if model:
                        qq_models[model_type] = self._model_config_to_dict(model)

                return qq_models

        except ImportError:
            logger.warning("[QQHybridConfig] 模型池未找到，使用本地配置")
            return self._get_local_model_config(model_type)
        except Exception as e:
            logger.error(f"[QQHybridConfig] 获取模型配置失败: {e}")
            return self._get_local_model_config(model_type)

    def _get_task_type(self, model_type: str) -> str:
        """将模型类型映射到任务类型"""
        mapping = {
            "chat": "simple_chat",
            "ocr": "text_extraction",
            "vision": "image_description",
            "safety": "nsfw_detection",
        }
        return mapping.get(model_type, "simple_chat")

    def _model_config_to_dict(self, model_config) -> Dict:
        """将模型配置对象转换为字典"""
        if hasattr(model_config, "__dict__"):
            return model_config.__dict__.copy()
        elif isinstance(model_config, dict):
            return model_config.copy()
        else:
            return {"id": str(model_config)}

    def _get_local_model_config(self, model_type: str = None) -> Dict:
        """获取本地模型配置"""
        config = self.get_config()

        local_models = {
            "chat": {
                "provider": "openai",
                "model": config.get("onebot_ws_url", "")
                .replace("ws://", "http://")
                .replace("wss://", "https://"),
                "api_key": config.get("onebot_token", ""),
            },
            "ocr": config.get("image_recognition", {}).get("ocr", {}),
            "vision": config.get("image_recognition", {}).get("ai_analysis", {}),
            "safety": config.get("image_recognition", {}).get("safety", {}),
        }

        if model_type:
            return local_models.get(model_type, {})
        else:
            return local_models

    def reload(self):
        """重新加载配置"""
        logger.info("[QQHybridConfig] 重新加载配置...")

        # 需要清除的是阿隔缓存中的配置，辅詨指南下次加载是新點
        if self.cache_manager:
            try:
                self.cache_manager.invalidate_config("qq_hybrid_config")
            except Exception as e:
                logger.debug(f"[QQHybridConfig] 清除缓存失败: {e}")

        # 重新加载配置
        self._load_configs()


# 全局实例和便捷函数
_hybrid_config_instance = None


def get_hybrid_config() -> QQHybridConfig:
    """获取混合配置实例"""
    global _hybrid_config_instance
    if _hybrid_config_instance is None:
        _hybrid_config_instance = QQHybridConfig()
    return _hybrid_config_instance


def get_qq_config() -> Dict:
    """获取QQ配置（兼容性函数）"""
    return get_hybrid_config().get_config()


def get_connection_config() -> Dict:
    """获取连接配置"""
    config = get_hybrid_config().get_config()
    return config.get("connection", {})


def get_multimedia_config() -> Dict:
    """获取多媒体配置"""
    config = get_hybrid_config().get_config()
    return config.get("multimedia", {})


def get_image_recognition_config() -> Dict:
    """获取图片识别配置"""
    config = get_hybrid_config().get_config()
    return config.get("image_recognition", {})


def get_active_chat_config() -> Dict:
    """获取主动聊天配置"""
    config = get_hybrid_config().get_config()
    return config.get("active_chat", {})


def get_model_config(model_type: str = None) -> Dict:
    """获取模型配置"""
    return get_hybrid_config().get_model_config(model_type)


def get_qq_model(model_type: str) -> Dict:
    """获取QQ端特定模型配置（便捷函数）"""
    return get_hybrid_config().get_model_config(model_type)


def reload_config():
    """重新加载配置"""
    get_hybrid_config().reload()


if __name__ == "__main__":
    # 测试代码
    import sys

    logging.basicConfig(level=logging.INFO)

    config = get_hybrid_config()
    full_config = config.get_config()

    print("混合配置加载测试:")
    print(f"WebSocket地址: {full_config.get('onebot_ws_url')}")
    print(f"Bot QQ: {full_config.get('bot_qq')}")
    print(f"重连间隔: {full_config.get('connection', {}).get('reconnect_interval')}")
    print(
        f"OCR启用: {full_config.get('image_recognition', {}).get('ocr', {}).get('enabled')}"
    )
    print(f"主动聊天启用: {full_config.get('active_chat', {}).get('enabled')}")

    sys.exit(0)

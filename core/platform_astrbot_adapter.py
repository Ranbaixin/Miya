"""
AstrBot 平台适配器

将 AstrBot 的平台适配器集成到弥娅系统。
"""

import logging
from abc import ABC
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class AstrBotPlatformAdapter(ABC):
    """
    AstrBot 平台适配器基类

    将 AstrBot 的平台适配器接口适配到弥娅系统。
    """

    def __init__(self, astrbot_adapter, config: Dict[str, Any]):
        self._astrbot_adapter = astrbot_adapter
        self._config = config
        self._initialized = False
        self._connected = False
        self._message_handler: Optional[Callable] = None

    @property
    def platform_name(self) -> str:
        """获取平台名称"""
        return self._config.get("name", "unknown")

    @property
    def platform_type(self) -> str:
        """获取平台类型"""
        return self._config.get("type", "unknown")

    async def initialize(self) -> bool:
        """初始化适配器"""
        try:
            if hasattr(self._astrbot_adapter, "initialize"):
                await self._astrbot_adapter.initialize()
            self._initialized = True
            return True
        except Exception as e:
            logger.error(f"[{self.platform_name}] 初始化失败: {e}")
            return False

    async def connect(self) -> bool:
        """连接到平台"""
        try:
            if hasattr(self._astrbot_adapter, "connect"):
                await self._astrbot_adapter.connect()
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"[{self.platform_name}] 连接失败: {e}")
            return False

    async def disconnect(self) -> None:
        """断开连接"""
        try:
            if hasattr(self._astrbot_adapter, "disconnect"):
                await self._astrbot_adapter.disconnect()
            self._connected = False
        except Exception as e:
            logger.error(f"[{self.platform_name}] 断开连接失败: {e}")

    def is_connected(self) -> bool:
        """检查是否已连接"""
        return self._connected

    def set_message_handler(self, handler: Callable) -> None:
        """设置消息处理器"""
        self._message_handler = handler

        # 设置 AstrBot 适配器的消息处理器
        if hasattr(self._astrbot_adapter, "set_message_handler"):
            self._astrbot_adapter.set_message_handler(self._wrap_handler(handler))

    def _wrap_handler(self, handler: Callable) -> Callable:
        """包装消息处理器"""

        async def wrapped_handler(event):
            # 转换 AstrBot 事件为弥娅消息
            message = self._convert_event(event)
            if message:
                await handler(message)

        return wrapped_handler

    def _convert_event(self, event) -> Optional[Dict[str, Any]]:
        """转换 AstrBot 事件为弥娅消息"""
        try:
            # 提取基本信息
            message = {
                "platform": self.platform_type,
                "message_id": getattr(event, "message_id", ""),
                "user_id": getattr(event, "user_id", ""),
                "user_name": getattr(event, "user_name", ""),
                "group_id": getattr(event, "group_id", None),
                "content": getattr(event, "content", ""),
                "raw": event,
            }
            return message
        except Exception as e:
            logger.error(f"[{self.platform_name}] 事件转换失败: {e}")
            return None

    async def send_message(self, target: str, message: str, **kwargs) -> bool:
        """发送消息"""
        try:
            if hasattr(self._astrbot_adapter, "send_message"):
                await self._astrbot_adapter.send_message(target, message, **kwargs)
                return True
            return False
        except Exception as e:
            logger.error(f"[{self.platform_name}] 发送消息失败: {e}")
            return False

    async def send_image(self, target: str, image_path: str, **kwargs) -> bool:
        """发送图片"""
        try:
            if hasattr(self._astrbot_adapter, "send_image"):
                await self._astrbot_adapter.send_image(target, image_path, **kwargs)
                return True
            return False
        except Exception as e:
            logger.error(f"[{self.platform_name}] 发送图片失败: {e}")
            return False


class PlatformAdapterFactory:
    """
    平台适配器工厂

    根据平台类型创建对应的适配器。
    """

    # 适配器映射表
    ADAPTER_MAP = {
        "aiocqhttp": AstrBotPlatformAdapter,
        "qqofficial": AstrBotPlatformAdapter,
        "telegram": AstrBotPlatformAdapter,
        "discord": AstrBotPlatformAdapter,
        "slack": AstrBotPlatformAdapter,
        "line": AstrBotPlatformAdapter,
        "lark": AstrBotPlatformAdapter,
        "dingtalk": AstrBotPlatformAdapter,
        "wecom": AstrBotPlatformAdapter,
        "weixin_oc": AstrBotPlatformAdapter,
        "weixin_official_account": AstrBotPlatformAdapter,
        "misskey": AstrBotPlatformAdapter,
        "mattermost": AstrBotPlatformAdapter,
        "satori": AstrBotPlatformAdapter,
        "kook": AstrBotPlatformAdapter,
        "webchat": AstrBotPlatformAdapter,
        "default": AstrBotPlatformAdapter,
    }

    @classmethod
    def create_adapter(
        cls,
        astrbot_adapter,
        config: Dict[str, Any],
    ) -> AstrBotPlatformAdapter:
        """
        创建适配器

        Args:
            astrbot_adapter: AstrBot 平台适配器实例
            config: 平台配置

        Returns:
            适配器实例
        """
        platform_type = config.get("type", "default").lower()
        adapter_class = cls.ADAPTER_MAP.get(platform_type, cls.ADAPTER_MAP["default"])

        return adapter_class(astrbot_adapter, config)

    @classmethod
    def register_adapter(cls, platform_type: str, adapter_class: type):
        """
        注册适配器

        Args:
            platform_type: 平台类型
            adapter_class: 适配器类
        """
        cls.ADAPTER_MAP[platform_type.lower()] = adapter_class


# 导出
__all__ = [
    "AstrBotPlatformAdapter",
    "PlatformAdapterFactory",
]

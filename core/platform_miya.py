"""
MIYA Platform Adapter (独立版本)

多平台适配系统 - 支持 QQ, Telegram, 飞书等
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


from core.unified_platform.platform_type import MiyaPlatform as PlatformType


@dataclass
class Message:
    """消息"""

    message_id: str
    platform: PlatformType
    message_type: str  # private, group
    user_id: str
    user_name: str
    group_id: Optional[str] = None
    content: str = ""
    raw: Any = None


@dataclass
class User:
    """用户"""

    user_id: str
    user_name: str
    platform: PlatformType
    avatar: Optional[str] = None


@dataclass
class Group:
    """群组"""

    group_id: str
    group_name: str
    platform: PlatformType
    members: List[str] = field(default_factory=list)


class PlatformAdapter(ABC):
    """
    平台适配器基类

    使用方式:
    class MyAdapter(PlatformAdapter):
        name = "my_platform"
        platform_type = PlatformType.QQ

        async def send_message(self, target: str, message: str):
            pass
    """

    name: str = ""
    platform_type: PlatformType = PlatformType.QQ
    enabled: bool = True

    _client: Optional[Any] = None
    _config: Dict[str, Any] = field(default_factory=dict)
    _message_handler: Optional[Callable] = None
    _connected: bool = False

    @abstractmethod
    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """连接"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开"""
        pass

    @abstractmethod
    async def send_message(self, target: str, message: str) -> bool:
        """发送消息"""
        pass

    @abstractmethod
    async def send_image(self, target: str, image_url: str) -> bool:
        """发送图片"""
        pass

    @abstractmethod
    async def send_voice(self, target: str, voice_url: str) -> bool:
        """发送语音"""
        pass

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        pass

    def set_message_handler(self, handler: Callable):
        """设置消息处理器"""
        self._message_handler = handler

    async def handle_message(self, message: Message):
        """处理接收的消息"""
        if self._message_handler:
            await self._message_handler(message)

    def is_connected(self) -> bool:
        return self._connected


class QQAdapter(PlatformAdapter):
    """QQ 平台适配器 (OneBot v11)"""

    name = "qq"
    platform_type = PlatformType.QQ

    def __init__(self):
        super().__init__()
        self._onebot_url = ""

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化"""
        self._config = config
        self._onebot_url = config.get("onebot_url", "http://127.0.0.1:3000")
        logger.info("[QQAdapter] 初始化完成")
        return True

    async def connect(self) -> bool:
        """连接"""
        try:
            self._connected = True
            logger.info("[QQAdapter] 已连接")
            return True
        except Exception as e:
            logger.error(f"[QQAdapter] 连接失败: {e}")
            return False

    async def disconnect(self):
        """断开"""
        self._connected = False

    async def send_message(self, target: str, message: str) -> bool:
        """发送消息"""
        try:
            async with httpx.AsyncClient() as client:
                # 发送私聊
                if target.isdigit():
                    await client.post(
                        f"{self._onebot_url}/send_private_msg",
                        json={"user_id": int(target), "message": message},
                    )
                # 发送群消息
                else:
                    await client.post(
                        f"{self._onebot_url}/send_group_msg",
                        json={"group_id": int(target), "message": message},
                    )
            return True
        except Exception as e:
            logger.error(f"[QQAdapter] 发送消息失败: {e}")
            return False

    async def send_image(self, target: str, image_url: str) -> bool:
        """发送图片"""
        try:
            async with httpx.AsyncClient() as client:
                msg = f"[CQ:image,file={image_url}]"
                if target.isdigit():
                    await client.post(
                        f"{self._onebot_url}/send_private_msg",
                        json={"user_id": int(target), "message": msg},
                    )
                else:
                    await client.post(
                        f"{self._onebot_url}/send_group_msg",
                        json={"group_id": int(target), "message": msg},
                    )
            return True
        except Exception as e:
            logger.error(f"[QQAdapter] 发送图片失败: {e}")
            return False

    async def send_voice(self, target: str, voice_url: str) -> bool:
        """发送语音"""
        try:
            async with httpx.AsyncClient() as client:
                msg = f"[CQ:record,file={voice_url}]"
                if target.isdigit():
                    await client.post(
                        f"{self._onebot_url}/send_private_msg",
                        json={"user_id": int(target), "message": msg},
                    )
                else:
                    await client.post(
                        f"{self._onebot_url}/send_group_msg",
                        json={"group_id": int(target), "message": msg},
                    )
            return True
        except Exception as e:
            logger.error(f"[QQAdapter] 发送语音失败: {e}")
            return False

    async def get_user_info(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(
                    f"{self._onebot_url}/get_stranger_info",
                    params={"user_id": int(user_id)},
                )
                data = resp.json()
                if data.get("status") == "ok":
                    return User(
                        user_id=user_id,
                        user_name=data["data"].get("nickname", ""),
                        platform=self.platform_type,
                    )
        except Exception as e:
            logger.error(f"[QQAdapter] 获取用户信息失败: {e}")
        return None


class TelegramAdapter(PlatformAdapter):
    """Telegram 平台适配器"""

    name = "telegram"
    platform_type = PlatformType.TELEGRAM

    def __init__(self):
        super().__init__()
        self._bot_token = ""
        self._api_url = "https://api.telegram.org"

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化"""
        self._config = config
        self._bot_token = config.get("bot_token", "")
        if not self._bot_token:
            logger.warning("[TelegramAdapter] 未配置 bot_token")
            return False
        self._api_url = config.get("api_url", "https://api.telegram.org")
        logger.info("[TelegramAdapter] 初始化完成")
        return True

    async def connect(self) -> bool:
        """连接"""
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(f"{self._api_url}/bot{self._bot_token}/getMe")
                if resp.status_code == 200:
                    self._connected = True
                    logger.info("[TelegramAdapter] 已连接")
                    return True
        except Exception as e:
            logger.error(f"[TelegramAdapter] 连接失败: {e}")
        return False

    async def disconnect(self):
        """断开"""
        self._connected = False

    async def _call_api(self, method: str, **kwargs) -> Dict:
        """调用 Telegram API"""
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{self._api_url}/bot{self._bot_token}/{method}", json=kwargs
            )
            return resp.json()

    async def send_message(self, target: str, message: str) -> bool:
        """发送消息"""
        try:
            await self._call_api("sendMessage", chat_id=target, text=message)
            return True
        except Exception as e:
            logger.error(f"[TelegramAdapter] 发送消息失败: {e}")
            return False

    async def send_image(self, target: str, image_url: str) -> bool:
        """发送图片"""
        try:
            await self._call_api("sendPhoto", chat_id=target, photo=image_url)
            return True
        except Exception as e:
            logger.error(f"[TelegramAdapter] 发送图片失败: {e}")
            return False

    async def send_voice(self, target: str, voice_url: str) -> bool:
        """发送语音"""
        try:
            await self._call_api("sendVoice", chat_id=target, voice=voice_url)
            return True
        except Exception as e:
            logger.error(f"[TelegramAdapter] 发送语音失败: {e}")
            return False

    async def get_user_info(self, user_id: str) -> Optional[User]:
        """获取用户信息"""
        try:
            resp = await self._call_api("getChat", chat_id=user_id)
            return User(
                user_id=user_id,
                user_name=resp.get("first_name", ""),
                platform=self.platform_type,
            )
        except Exception as e:
            logger.error(f"[TelegramAdapter] 获取用���信���失败: {e}")
        return None


class PlatformManager:
    """
    MIYA 平台管理器

    功能:
    - 平台适配器注册
    - 消息路由
    - 统一接口
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._adapters: Dict[PlatformType, PlatformAdapter] = {}
        self._active_platform: Optional[PlatformType] = None
        self._message_router: Dict[PlatformType, Callable] = {}
        self._initialized = True

        # 注册内置适配器
        self._register_builtin_adapters()

        logger.info("[PlatformManager] 初始化完成")

    def _register_builtin_adapters(self):
        """注册内置适配器"""
        self._adapters[PlatformType.QQ] = QQAdapter()
        self._adapters[PlatformType.TELEGRAM] = TelegramAdapter()

    async def create_adapter(
        self, platform: PlatformType, config: Dict[str, Any]
    ) -> Optional[PlatformAdapter]:
        """创建适配器"""
        adapter_classes = {
            PlatformType.QQ: QQAdapter,
            PlatformType.TELEGRAM: TelegramAdapter,
        }

        adapter_cls = adapter_classes.get(platform)
        if not adapter_cls:
            logger.warning(f"[PlatformManager] 不支持的平台: {platform}")
            return None

        adapter = adapter_cls()
        if await adapter.initialize(config):
            self._adapters[platform] = adapter
            logger.info(f"[PlatformManager] 创建适配器: {platform}")
            return adapter

        return None

    async def connect(self, platform: PlatformType) -> bool:
        """连接平台"""
        adapter = self._adapters.get(platform)
        if adapter:
            return await adapter.connect()
        return False

    async def disconnect(self, platform: PlatformType):
        """断开平台"""
        adapter = self._adapters.get(platform)
        if adapter:
            await adapter.disconnect()

    def get_adapter(self, platform: PlatformType) -> Optional[PlatformAdapter]:
        """获取适配器"""
        return self._adapters.get(platform)

    def get_active_platform(self) -> Optional[PlatformType]:
        """获取当前活跃平台"""
        return self._active_platform

    async def send_message(
        self, platform: PlatformType, target: str, message: str
    ) -> bool:
        """发送消息"""
        adapter = self.get_adapter(platform)
        if adapter and adapter.is_connected():
            return await adapter.send_message(target, message)
        return False

    def list_platforms(self) -> List[Dict]:
        """列出平台"""
        return [
            {
                "type": p.value,
                "name": p.value.upper(),
                "enabled": a.enabled if a else False,
                "connected": a.is_connected() if a else False,
            }
            for p, a in self._adapters.items()
        ]


# 全局实例
_platform_manager = None


def get_platform_manager() -> PlatformManager:
    """获取平台管理器"""
    global _platform_manager
    if _platform_manager is None:
        _platform_manager = PlatformManager()
    return _platform_manager


def get_adapter(platform: PlatformType) -> Optional[PlatformAdapter]:
    """获取适配器便捷函数"""
    return get_platform_manager().get_adapter(platform)


async def send_message(platform: PlatformType, target: str, message: str) -> bool:
    """发送消息便捷函数"""
    return await get_platform_manager().send_message(platform, target, message)


__all__ = [
    "PlatformAdapter",
    "QQAdapter",
    "TelegramAdapter",
    "PlatformManager",
    "PlatformType",
    "Message",
    "User",
    "Group",
    "get_platform_manager",
    "get_adapter",
    "send_message",
]

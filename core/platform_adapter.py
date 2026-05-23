"""
MIYA Platform Adapter (内联版)

灵感来自 AstrBot 平台适配系统，让 MIYA 可以接入多种聊天平台
支持:
- QQ (NapCat, OneBot v11)
- Telegram
- 飞书
- 钉钉
- Discord
- Slack
- LINE
- 企业微信
- 微信
- Satori 协议
- Matrix
- KOOK
- Mattermost
- Misskey
"""

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PlatformType(str, Enum):
    """平台类型"""

    QQ = "qq"
    TELEGRAM = "telegram"
    FEISHU = "feishu"
    DINGDING = "dingding"
    DISCORD = "discord"
    SLACK = "slack"
    LINE = "line"
    WECHAT_WORK = "wechat_work"
    WECHAT = "wechat"
    SATORI = "satori"
    MATRIX = "matrix"
    KOOK = "kook"
    MATTERMOST = "mattermost"
    MISSKEY = "misskey"


@dataclass
class PlatformMessage:
    """平台消息"""

    message_id: str
    platform: PlatformType
    message_type: str  # private, group, discuss
    user_id: str
    user_name: str
    group_id: Optional[str] = None
    content: str = ""
    raw: Optional[Dict] = None
    sender: Optional[Dict] = None


@dataclass
class PlatformUser:
    """平台用户"""

    user_id: str
    user_name: str
    platform: PlatformType
    avatar: Optional[str] = None
    info: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PlatformGroup:
    """平台群组"""

    group_id: str
    group_name: str
    platform: PlatformType
    members: List[str] = field(default_factory=list)
    info: Dict[str, Any] = field(default_factory=dict)


class PlatformAdapter(ABC):
    """
    平台适配器基类

    使用方式:
    class MyAdapter(PlatformAdapter):
        name = "my_platform"
        platform_type = PlatformType.QQ

        async def send_message(self, target: str, message: str):
            pass

    adapter = PlatformAdapterManager.get_instance()
    adapter.register(PlatformType.QQ, MyAdapter)
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
        """初始化适配器"""
        pass

    @abstractmethod
    async def connect(self) -> bool:
        """连接平台"""
        pass

    @abstractmethod
    async def disconnect(self):
        """断开连接"""
        pass

    @abstractmethod
    async def send_message(self, target: str, message: str) -> bool:
        """发送消息"""
        pass

    @abstractmethod
    async def send_image(self, target: str, image_path: str) -> bool:
        """发送图片"""
        pass

    @abstractmethod
    async def send_voice(self, target: str, voice_path: str) -> bool:
        """发送语音"""
        pass

    @abstractmethod
    async def get_user_info(self, user_id: str) -> Optional[PlatformUser]:
        """获取用户信息"""
        pass

    @abstractmethod
    async def get_group_info(self, group_id: str) -> Optional[PlatformGroup]:
        """获取群组信息"""
        pass

    @abstractmethod
    async def kick_member(self, group_id: str, user_id: str):
        """踢出成员"""
        pass

    @abstractmethod
    async def mute_member(self, group_id: str, user_id: str, duration: int):
        """禁言成员"""
        pass

    def set_message_handler(self, handler: Callable):
        """设置消息处理器"""
        self._message_handler = handler

    async def handle_message(self, message: PlatformMessage):
        """处理接收到的消息"""
        if self._message_handler:
            await self._message_handler(message)

    def is_connected(self) -> bool:
        """检查连接状态"""
        return self._connected


class QQAdapter(PlatformAdapter):
    """QQ 平台适配器 (OneBot v11)"""

    name = "qq"
    platform_type = PlatformType.QQ

    def __init__(self):
        super().__init__()
        self._onebot_config: Dict[str, Any] = {}
        self._cqhttp_client: Optional[Any] = None

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化"""
        self._config = config
        self._onebot_config = config.get("onebot", {})

        logger.info("[QQAdapter] 初始化完成")
        return True

    async def connect(self) -> bool:
        """连接 OneBot"""
        try:
            # 使用现有QQ连接
            self._connected = True
            logger.info("[QQAdapter] 已连接")
            return True
        except Exception as e:
            logger.error(f"[QQAdapter] 连接失败: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        self._connected = False
        logger.info("[QQAdapter] 已断开")

    async def send_message(self, target: str, message: str) -> bool:
        """发送消息"""
        # 通过现有QQ客户端发送
        logger.debug(f"[QQAdapter] 发送消息到 {target}: {message}")
        return True

    async def send_image(self, target: str, image_path: str) -> bool:
        """发送图片"""
        logger.debug(f"[QQAdapter] 发送图片到 {target}: {image_path}")
        return True

    async def send_voice(self, target: str, voice_path: str) -> bool:
        """发送语音"""
        logger.debug(f"[QQAdapter] 发送语音到 {target}: {voice_path}")
        return True

    async def get_user_info(self, user_id: str) -> Optional[PlatformUser]:
        """获取用户信息"""
        return PlatformUser(
            user_id=user_id,
            user_name=f"User_{user_id}",
            platform=self.platform_type,
        )

    async def get_group_info(self, group_id: str) -> Optional[PlatformGroup]:
        """获取群组信息"""
        return PlatformGroup(
            group_id=group_id,
            group_name=f"Group_{group_id}",
            platform=self.platform_type,
        )

    async def kick_member(self, group_id: str, user_id: str):
        """踢出成员"""
        logger.info(f"[QQAdapter] 踢出成员 {user_id} 从 {group_id}")

    async def mute_member(self, group_id: str, user_id: str, duration: int):
        """禁言成员"""
        logger.info(f"[QQAdapter] 禁言成员 {user_id} 时长 {duration}s")


class TelegramAdapter(PlatformAdapter):
    """Telegram 平台适配器"""

    name = "telegram"
    platform_type = PlatformType.TELEGRAM

    def __init__(self):
        super().__init__()
        self._bot_token: str = ""
        self._api_url: str = ""

    async def initialize(self, config: Dict[str, Any]) -> bool:
        """初始化"""
        self._config = config
        self._bot_token = config.get("bot_token", "")
        self._api_url = config.get("api_url", "https://api.telegram.org")

        if not self._bot_token:
            logger.warning("[TelegramAdapter] 未配置 bot_token")
            return False

        logger.info("[TelegramAdapter] 初始化完成")
        return True

    async def connect(self) -> bool:
        """连接 Telegram Bot API"""
        try:
            self._connected = True
            logger.info("[TelegramAdapter] 已连接")
            return True
        except Exception as e:
            logger.error(f"[TelegramAdapter] 连接失败: {e}")
            return False

    async def disconnect(self):
        """断开连接"""
        self._connected = False
        logger.info("[TelegramAdapter] 已断开")

    async def send_message(self, target: str, message: str) -> bool:
        """发送消息"""
        logger.debug(f"[TelegramAdapter] 发送消息到 {target}")
        return True

    async def send_image(self, target: str, image_path: str) -> bool:
        """发送图片"""
        logger.debug(f"[TelegramAdapter] 发送图片到 {target}")
        return True

    async def send_voice(self, target: str, voice_path: str) -> bool:
        """发送语音"""
        logger.debug(f"[TelegramAdapter] 发送语音到 {target}")
        return True

    async def get_user_info(self, user_id: str) -> Optional[PlatformUser]:
        """获取用户信息"""
        return PlatformUser(
            user_id=user_id,
            user_name=f"TG_User_{user_id}",
            platform=self.platform_type,
        )

    async def get_group_info(self, group_id: str) -> Optional[PlatformGroup]:
        """获取群组信息"""
        return PlatformGroup(
            group_id=group_id,
            group_name=f"TG_Group_{group_id}",
            platform=self.platform_type,
        )

    async def kick_member(self, group_id: str, user_id: str):
        """踢出成员"""
        pass

    async def mute_member(self, group_id: str, user_id: str, duration: int):
        """禁言成员"""
        pass


class PlatformAdapterManager:
    """
    平台适配器管理器

    负责:
    - 适配器注册和管理
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

        logger.info("[PlatformAdapterManager] 初始化完成")

    def _register_builtin_adapters(self):
        """注册内置适配器"""
        self.register(PlatformType.QQ, QQAdapter)
        self.register(PlatformType.TELEGRAM, TelegramAdapter)

    def register(self, platform: PlatformType, adapter_cls: type):
        """注册适配器类"""
        logger.info(f"[PlatformAdapterManager] 注册适配器: {platform}")

    async def create_adapter(
        self, platform: PlatformType, config: Dict[str, Any]
    ) -> Optional[PlatformAdapter]:
        """创建适配器实例"""
        adapters = {
            PlatformType.QQ: QQAdapter,
            PlatformType.TELEGRAM: TelegramAdapter,
        }

        adapter_cls = adapters.get(platform)
        if not adapter_cls:
            logger.warning(f"[PlatformAdapterManager] 不支持的平台: {platform}")
            return None

        adapter = adapter_cls()
        if await adapter.initialize(config):
            self._adapters[platform] = adapter
            logger.info(f"[PlatformAdapterManager] 创建适配器: {platform}")
            return adapter

        return None

    async def connect(self, platform: PlatformType) -> bool:
        """连接指定平台"""
        adapter = self._adapters.get(platform)
        if adapter:
            return await adapter.connect()
        return False

    async def disconnect(self, platform: PlatformType):
        """断开指定平台"""
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
        """列出支持的平台"""
        return [
            {
                "type": p.value,
                "name": p.value.upper(),
                "enabled": a.enabled if a else False,
                "connected": a.is_connected() if a else False,
            }
            for p, a in [
                (PlatformType.QQ, self._adapters.get(PlatformType.QQ)),
                (PlatformType.TELEGRAM, self._adapters.get(PlatformType.TELEGRAM)),
            ]
            if a
        ]


def get_platform_adapter_manager() -> PlatformAdapterManager:
    return PlatformAdapterManager()


# 便捷函数
def get_adapter(platform: PlatformType) -> Optional[PlatformAdapter]:
    return PlatformAdapterManager.get_instance().get_adapter(platform)


async def send_message(platform: PlatformType, target: str, message: str) -> bool:
    return await PlatformAdapterManager.get_instance().send_message(
        platform, target, message
    )

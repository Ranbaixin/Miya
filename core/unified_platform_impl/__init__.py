"""
弥娅统一平台实现包

所有平台适配器的命名空间包。
"""

from .qq_official_platform import QQOfficialPlatform
from .telegram_platform import TelegramPlatform
from .discord_platform import DiscordPlatform
from .onebot_platform import OneBotPlatform
from .generic_platform import GenericPlatform, WebChatPlatform

__all__ = [
    "QQOfficialPlatform",
    "TelegramPlatform",
    "DiscordPlatform",
    "OneBotPlatform",
    "GenericPlatform",
    "WebChatPlatform",
]

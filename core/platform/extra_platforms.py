"""
更多 Platform 适配器

添加: 飞书, 钉钉, 企业微信, KOOK, Line 等
"""

import asyncio
import logging
from typing import Any

from miya.core.platform import (
    Platform,
    PlatformMetadata,
    MiyaMessageEvent,
    register_platform_adapter,
    PlatformStatus,
)

logger = logging.getLogger("miya.platform.extra")


@register_platform_adapter("lark", "飞书 (Lark) 适配器")
class LarkPlatformAdapter(Platform):
    """飞书平台适配器"""

    def __init__(self, config: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(config, event_queue)
        self._platform_id = "lark"
        self._platform_name = "Lark"
        self._platform_description = "飞书平台适配器"

        self._app_id = config.get("lark_app_id", "")
        self._app_secret = config.get("lark_app_secret", "")

    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            id=self._platform_id,
            name=self._platform_name,
            adapter_display_name="飞书",
            description=self._platform_description,
        )

    async def run(self) -> None:
        logger.info("[飞书] 适配器初始化...")
        self.status = PlatformStatus.RUNNING

    def get_client(self) -> None:
        return None


@register_platform_adapter("dingtalk", "钉钉适配器")
class DingTalkPlatformAdapter(Platform):
    """钉钉平台适配器"""

    def __init__(self, config: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(config, event_queue)
        self._platform_id = "dingtalk"
        self._platform_name = "DingTalk"
        self._platform_description = "钉钉平台适配器"

        self._app_key = config.get("dingtalk_app_key", "")
        self._app_secret = config.get("dingtalk_app_secret", "")

    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            id=self._platform_id,
            name=self._platform_name,
            adapter_display_name="钉钉",
            description=self._platform_description,
        )

    async def run(self) -> None:
        logger.info("[钉钉] 适配器初始化...")
        self.status = PlatformStatus.RUNNING


@register_platform_adapter("wecom", "企业微信适配器")
class WecomPlatformAdapter(Platform):
    """企业微信平台适配器"""

    def __init__(self, config: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(config, event_queue)
        self._platform_id = "wecom"
        self._platform_name = "WeCom"
        self._platform_description = "企业微信平台适配器"

        self._corp_id = config.get("wecom_corp_id", "")
        self._agent_id = config.get("wecom_agent_id", "")
        self._secret = config.get("wecom_secret", "")

    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            id=self._platform_id,
            name=self._platform_name,
            adapter_display_name="企业微信",
            description=self._platform_description,
        )

    async def run(self) -> None:
        logger.info("[企业微信] 适配器初始化...")
        self.status = PlatformStatus.RUNNING


@register_platform_adapter("kook", "KOOK 适配器")
class KookPlatformAdapter(Platform):
    """KOOK 平台适配器"""

    def __init__(self, config: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(config, event_queue)
        self._platform_id = "kook"
        self._platform_name = "KOOK"
        self._platform_description = "KOOK 平台适配器"

        self._token = config.get("kook_token", "")

    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            id=self._platform_id,
            name=self._platform_name,
            adapter_display_name="KOOK",
            description=self._platform_description,
        )

    async def run(self) -> None:
        logger.info("[KOOK] 适配器初始化...")
        self.status = PlatformStatus.RUNNING


@register_platform_adapter("line", "LINE 适配器")
class LinePlatformAdapter(Platform):
    """LINE 平台适配器"""

    def __init__(self, config: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(config, event_queue)
        self._platform_id = "line"
        self._platform_name = "LINE"
        self._platform_description = "LINE 平台适配器"

        self._channel_token = config.get("line_channel_token", "")

    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            id=self._platform_id,
            name=self._platform_name,
            adapter_display_name="LINE",
            description=self._platform_description,
        )

    async def run(self) -> None:
        logger.info("[LINE] 适配器初始化...")
        self.status = PlatformStatus.RUNNING


@register_platform_adapter("satori", "Satori 适配器")
class SatoriPlatformAdapter(Platform):
    """Satori 协议适配器"""

    def __init__(self, config: dict, event_queue: asyncio.Queue) -> None:
        super().__init__(config, event_queue)
        self._platform_id = "satori"
        self._platform_name = "Satori"
        self._platform_description = "Satori 协议适配器"

        self._api_url = config.get("satori_api_url", "")
        self._token = config.get("satori_token", "")

    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            id=self._platform_id,
            name=self._platform_name,
            adapter_display_name="Satori",
            description=self._platform_description,
        )

    async def run(self) -> None:
        logger.info("[Satori] 适配器初始化...")
        self.status = PlatformStatus.RUNNING


# 预留 - 需要安装对应库
# aiocqhttp, slack_sdk 等

__all__ = [
    "LarkPlatformAdapter",
    "DingTalkPlatformAdapter",
    "WecomPlatformAdapter",
    "KookPlatformAdapter",
    "LinePlatformAdapter",
    "SatoriPlatformAdapter",
]

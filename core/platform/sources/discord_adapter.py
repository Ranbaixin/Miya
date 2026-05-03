"""
Discord 平台适配器

支持 Discord Bot API
"""

import asyncio
import logging
from typing import Any, cast

import discord
from discord.abc import GuildChannel, Messageable

from miya.core.platform import (
    Platform,
    PlatformMetadata,
    MiyaMessageEvent,
    register_platform_adapter,
    PlatformStatus,
)

logger = logging.getLogger("miya.platform.discord")


@register_platform_adapter("discord", "Discord 适配器")
class DiscordPlatformAdapter(Platform):
    def __init__(
        self,
        config: dict,
        event_queue: asyncio.Queue,
    ) -> None:
        super().__init__(config, event_queue)
        self._platform_id = "discord"
        self._platform_name = "Discord"
        self._platform_description = "Discord Bot 适配器"

        self._token = config.get("discord_token", "")
        self._intents = config.get("discord_intents", [])
        self._client: discord.Client | None = None

    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            id=self._platform_id,
            name=self._platform_name,
            adapter_display_name="Discord Bot",
            description=self._platform_description,
            support_streaming_message=False,
            support_proactive_message=True,
        )

    async def run(self) -> None:
        """运行 Discord Bot"""
        if not self._token:
            logger.error("[Discord] Bot token 未配置")
            self.status = PlatformStatus.ERROR
            return

        try:
            intents = discord.Intents.default()
            intents.message_content = True

            self._client = discord.Client(intents=intents)

            @self._client.event
            async def on_message(message: discord.Message) -> None:
                if message.author == self._client.user:
                    return

                # 构建消息事件
                session_id = str(message.channel.id)
                group_id = None
                if isinstance(message.channel, GuildChannel):
                    group_id = str(message.guild.id)

                event = MiyaMessageEvent(
                    message_str=message.content,
                    user_id=str(message.author.id),
                    platform_id="discord",
                    session_id=session_id,
                    group_id=group_id,
                    message_type="group" if group_id else "private",
                    sender_name=message.author.display_name,
                    channel_name=message.channel.name,
                )

                self.commit_event(event)

            await self._client.start(self._token)
            self.status = PlatformStatus.RUNNING

        except Exception as e:
            logger.error(f"[Discord] 启动失败: {e}")
            self.record_error(str(e))
            self.status = PlatformStatus.ERROR

    async def terminate(self) -> None:
        """终止平台"""
        if self._client:
            await self._client.close()
        self.status = PlatformStatus.STOPPED
        logger.info("[Discord] Bot 已停止")

    def get_client(self) -> discord.Client | None:
        return self._client


__all__ = ["DiscordPlatformAdapter"]

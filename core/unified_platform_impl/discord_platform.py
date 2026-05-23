"""
Discord 平台适配器

基于 discord.py SDK，支持私聊、服务器频道。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from core.unified_platform.base import BasePlatform

from .message_mixin import MessageMixin

logger = logging.getLogger("Miya.Platform.Discord")


class DiscordPlatform(MessageMixin, BasePlatform):
    """Discord 平台"""

    platform_id = "discord"
    platform_name = "Discord"
    health_check_interval = 30.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BasePlatform.__init__(self, config)
        self._client: Any = None
        self._token = self.config.get("bot_token", "")

    async def _do_connect(self) -> bool:
        if not self._token:
            logger.error(f"[{self.platform_id}] 缺少 bot_token")
            return False

        try:
            import discord

            intents = discord.Intents.default()
            intents.message_content = True
            self._client = discord.Client(intents=intents)

            @self._client.event
            async def on_ready():
                logger.info(f"[{self.platform_id}] Bot 已上线: {self._client.user}")

            @self._client.event
            async def on_message(message):
                if message.author == self._client.user:
                    return
                content = message.content.strip()
                if not content:
                    return

                user_id = str(message.author.id)
                user_name = str(message.author)
                msg_type = "group" if message.guild else "private"
                group_id = str(message.guild.id) if message.guild else ""
                group_name = str(message.guild.name) if message.guild else ""

                logger.debug(f"[{self.platform_id}] 收到消息: {content[:50]}")

                response = await self.route_to_decision_hub(
                    content=content,
                    user_id=user_id,
                    user_name=user_name,
                    message_type=msg_type,
                    group_id=group_id,
                    group_name=group_name,
                )
                await message.reply(response)

            async def start_client():
                await self._client.start(self._token)

            logger.info(f"[{self.platform_id}] Bot 已初始化，正在连接...")
            self._tasks.append(asyncio.create_task(start_client()))
            await asyncio.sleep(1)
            return True

        except ImportError:
            logger.error(f"[{self.platform_id}] 请安装 discord.py")
            return False
        except Exception as e:
            logger.error(f"[{self.platform_id}] 连接异常: {e}", exc_info=True)
            return False

    async def _do_disconnect(self):
        if self._client:
            try:
                await self._client.close()
            except Exception as e:
                logger.warning(f"[{self.platform_id}] 断开异常: {e}")
        self._client = None

    async def _do_health_check(self) -> bool:
        return self._client is not None and hasattr(self._client, "is_ready")

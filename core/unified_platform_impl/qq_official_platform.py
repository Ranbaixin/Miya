"""
QQ 官方机器人平台 (从旧代码迁移)
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from core.unified_platform.base import BasePlatform
from .message_mixin import MessageMixin

logger = logging.getLogger("Miya.Platform.QQOfficial")


class QQOfficialPlatform(MessageMixin, BasePlatform):
    """QQ 官方机器人平台"""

    platform_id = "qqofficial"
    platform_name = "QQ 官方机器人"
    health_check_interval = 30.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BasePlatform.__init__(self, config)
        self._bot_client = None
        self._bot_task: Optional[asyncio.Task] = None

        self.appid = self.config.get("appid", "")
        self.secret = self.config.get("secret", "")
        self.bot_qq = self.config.get("bot_qq", "")
        self.sandbox = self.config.get("sandbox", False)

    async def _do_connect(self) -> bool:
        if not self.appid or not self.secret:
            logger.error(f"[{self.platform_id}] 缺少 appid 或 secret")
            return False

        try:
            import botpy
            from botpy.flags import Intents

            platform = self

            intents = Intents(
                public_messages=True,
                public_guild_messages=True,
                direct_message=True,
            )

            class _MiyaBotClient(botpy.Client):
                async def on_ready(self):
                    logger.info(f"[qqofficial] Bot 已上线 (QQ: {platform.bot_qq})")

                async def on_at_message_create(self, message):
                    await _do_handle(message, "channel")

                async def on_group_at_message_create(self, message):
                    await _do_handle_group(message)

                async def on_direct_message_create(self, message):
                    await _do_handle(message, "private")

                async def on_c2c_message_create(self, message):
                    await _do_handle(message, "c2c")

            async def _do_handle(msg, msg_type):
                try:
                    user_id = str(
                        getattr(msg.author, "id", None)
                        or getattr(msg.author, "member_openid", None)
                        or getattr(msg.author, "user_openid", None)
                        or ""
                    )
                    user_name = getattr(msg.author, "username", user_id)
                    content = msg.content.strip() if msg.content else ""
                    response = await platform.route_to_decision_hub(
                        content=content,
                        user_id=user_id,
                        user_name=user_name,
                        message_type=msg_type,
                        is_at_bot=True,
                    )
                    await msg.reply(content=response or "弥娅暂无回复")
                except Exception as e:
                    logger.error(f"[qqofficial] 消息处理异常: {e}")

            async def _do_handle_group(msg):
                try:
                    user_id = str(msg.author.member_openid)
                    content = msg.content.strip() if msg.content else ""
                    response = await platform.route_to_decision_hub(
                        content=content,
                        user_id=user_id,
                        message_type="group",
                        group_id=msg.group_openid,
                        is_at_bot=True,
                    )
                    await msg._api.post_group_message(
                        group_openid=msg.group_openid,
                        msg_type=0,
                        msg_id=msg.id,
                        content=response or "弥娅暂无回复",
                    )
                except Exception as e:
                    logger.error(f"[qqofficial] 群消息处理异常: {e}")

            self._bot_client = _MiyaBotClient(intents=intents, is_sandbox=self.sandbox)

            async def run_bot():
                params = {"appid": self.appid, "secret": self.secret}
                if self.sandbox:
                    params["sandbox"] = True
                try:
                    await self._bot_client.start(**params)
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"[qqofficial] Bot 运行异常: {e}")

            self._bot_task = asyncio.create_task(run_bot())
            await asyncio.sleep(0.5)
            return True

        except ImportError:
            logger.error(f"[{self.platform_id}] 请安装 qq-botpy")
            return False
        except Exception as e:
            logger.error(f"[{self.platform_id}] 连接异常: {e}", exc_info=True)
            return False

    async def _do_disconnect(self):
        if self._bot_task and not self._bot_task.done():
            self._bot_task.cancel()
            try:
                await self._bot_task
            except asyncio.CancelledError:
                pass
        self._bot_client = None
        self._bot_task = None

    async def _do_health_check(self) -> bool:
        if not self._bot_task:
            return False
        return not self._bot_task.done()

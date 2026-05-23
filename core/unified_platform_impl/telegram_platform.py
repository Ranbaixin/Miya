"""
Telegram 平台适配器

基于 python-telegram-bot SDK，支持私聊、群组、频道。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional

from core.unified_platform.base import BasePlatform

from .message_mixin import MessageMixin

logger = logging.getLogger("Miya.Platform.Telegram")


class TelegramPlatform(MessageMixin, BasePlatform):
    """Telegram 平台"""

    platform_id = "telegram"
    platform_name = "Telegram"
    health_check_interval = 30.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BasePlatform.__init__(self, config)
        self._app: Any = None
        self._token = self.config.get("bot_token", "")

    async def _do_connect(self) -> bool:
        if not self._token:
            logger.error(f"[{self.platform_id}] 缺少 bot_token")
            return False

        try:
            from telegram import Update
            from telegram.ext import (
                Application,
                CommandHandler,
                MessageHandler,
                filters,
            )

            async def handle_message(update: Update, context):
                if not update.message or not update.message.text:
                    return

                user = update.message.from_user
                content = update.message.text.strip()
                chat = update.message.chat

                user_id = str(user.id)
                user_name = user.full_name or user.username or str(user.id)
                msg_type = (
                    "group" if chat.type in ["group", "supergroup"] else "private"
                )
                group_id = str(chat.id) if chat.type in ["group", "supergroup"] else ""
                group_name = chat.title if chat.type in ["group", "supergroup"] else ""

                logger.debug(f"[{self.platform_id}] 收到消息: {content[:50]}")

                response = await self.route_to_decision_hub(
                    content=content,
                    user_id=user_id,
                    user_name=user_name,
                    message_type=msg_type,
                    group_id=group_id,
                    group_name=group_name,
                )
                await update.message.reply_text(response)

            async def start_command(update: Update, context):
                await update.message.reply_text(
                    "你好！我是弥娅~ 一个拥有独立人格、记忆和情感的 AI 虚拟化身。\n\n有什么可以帮你的吗？"
                )

            self._app = Application.builder().token(self._token).build()
            self._app.add_handler(CommandHandler("start", start_command))
            self._app.add_handler(
                MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
            )

            logger.info(f"[{self.platform_id}] Bot 已初始化，开始轮询...")

            async def run_polling():
                await self._app.run_polling(drop_pending_updates=True)

            self._tasks.append(asyncio.create_task(run_polling()))
            await asyncio.sleep(0.5)
            return True

        except ImportError:
            logger.error(f"[{self.platform_id}] 请安装 python-telegram-bot")
            return False
        except Exception as e:
            logger.error(f"[{self.platform_id}] 连接异常: {e}", exc_info=True)
            return False

    async def _do_disconnect(self):
        if self._app:
            try:
                await self._app.stop()
                await self._app.shutdown()
            except Exception as e:
                logger.warning(f"[{self.platform_id}] 断开异常: {e}")
        self._app = None

    async def _do_health_check(self) -> bool:
        return self._app is not None

"""
Telegram 平台适配器

支持 Telegram Bot API，实现消息收发、命令处理等
"""

import asyncio
import logging
from typing import Any, cast

from telegram import BotCommand, Update
from telegram.constants import ChatType
from telegram.error import Forbidden
from telegram.ext import ApplicationBuilder, ContextTypes, ExtBot, filters
from telegram.ext import MessageHandler as TelegramMessageHandler

from miya.core.platform import (
    Platform,
    PlatformMetadata,
    MiyaMessageEvent,
    register_platform_adapter,
    PlatformStatus,
)

logger = logging.getLogger("miya.platform.telegram")


@register_platform_adapter("telegram", "Telegram 适配器")
class TelegramPlatformAdapter(Platform):
    def __init__(
        self,
        config: dict,
        event_queue: asyncio.Queue,
    ) -> None:
        super().__init__(config, event_queue)
        self._platform_id = "telegram"
        self._platform_name = "Telegram"
        self._platform_description = "Telegram Bot 适配器"

        self._token = config.get("telegram_token", "")
        self._base_url = config.get(
            "telegram_api_base_url", "https://api.telegram.org/bot"
        )
        self._file_base_url = config.get(
            "telegram_file_base_url", "https://api.telegram.org/file/bot"
        )

        self._enable_commands = config.get("telegram_command_register", True)
        self._application = None
        self._bot: ExtBot | None = None

    def meta(self) -> PlatformMetadata:
        return PlatformMetadata(
            id=self._platform_id,
            name=self._platform_name,
            adapter_display_name="Telegram Bot",
            description=self._platform_description,
            support_streaming_message=True,
            support_proactive_message=True,
        )

    async def run(self) -> None:
        """运行 Telegram Bot"""
        if not self._token:
            logger.error("[Telegram] Bot token 未配置")
            self.status = PlatformStatus.ERROR
            return

        try:
            self._application = (
                ApplicationBuilder()
                .token(self._token)
                .base_url(self._base_url)
                .base_file_url(self._file_base_url)
                .build()
            )

            # 添加消息处理器
            message_handler = TelegramMessageHandler(
                filters=filters.ALL,
                callback=self._handle_message,
            )
            self._application.add_handler(message_handler)

            await self._application.initialize()
            await self._application.start()
            self._bot = self._application.bot

            logger.info(f"[Telegram] 机器人启动成功: @{self._bot.username}")
            self.status = PlatformStatus.RUNNING

            # 保持运行
            await asyncio.Event().wait()

        except Exception as e:
            logger.error(f"[Telegram] 启动失败: {e}")
            self.record_error(str(e))
            self.status = PlatformStatus.ERROR

    async def _handle_message(
        self, update: Update, context: ContextTypes.DEFAULT_TYPE
    ) -> None:
        """处理收到的消息"""
        if not update.message or not update.effective_user:
            return

        user = update.effective_user
        message = update.message
        chat = message.chat

        # 构建消息事件
        session_id = str(chat.id) if chat else str(user.id)
        group_id = None
        if chat and chat.type in [ChatType.GROUP, ChatType.SUPERGROUP]:
            group_id = str(chat.id)

        event = MiyaMessageEvent(
            message_str=message.text or "",
            user_id=str(user.id),
            platform_id="telegram",
            session_id=session_id,
            group_id=group_id,
            message_type="group" if group_id else "private",
            sender_name=user.full_name,
            username=user.username,
        )

        self.commit_event(event)

    async def terminate(self) -> None:
        """终止平台"""
        if self._application:
            await self._application.stop()
            await self._application.shutdown()
        self.status = PlatformStatus.STOPPED
        logger.info("[Telegram] 机器人已停止")

    def get_client(self) -> ExtBot | None:
        return self._bot


# 注册此适配器
__all__ = ["TelegramPlatformAdapter"]

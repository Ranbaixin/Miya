"""
OneBot / NapCat 平台适配器

基于 OneBot v11 反向 WebSocket 协议。
支持 QQ (NapCat、LLOneBot、Lagrange 等)。
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Dict, Any, Optional

from core.unified_platform.base import BasePlatform
from .message_mixin import MessageMixin

logger = logging.getLogger("Miya.Platform.OneBot")


class OneBotPlatform(MessageMixin, BasePlatform):
    """OneBot / NapCat 平台"""

    platform_id = "aiocqhttp"
    platform_name = "OneBot/NapCat"
    health_check_interval = 30.0
    auto_reconnect = False  # OneBot 监听循环自带重连，不触发系统级重连

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BasePlatform.__init__(self, config)
        self._ws_url = self.config.get("ws_url", "ws://127.0.0.1:3001")
        self._bot_qq = self.config.get("bot_qq", "")
        self._ws: Optional[Any] = None
        self._connected = False

    async def _do_connect(self) -> bool:
        try:
            import aiohttp

            # 如果已有后台任务在运行，不重复创建
            existing_tasks = [t for t in self._tasks if not t.done()]
            if existing_tasks:
                self._connected = True
                return True

            self._ws = None
            self._connected = True  # 乐观标记，实际连接由后台任务管理

            async def listen_loop():
                retry_delay = 1
                while self._connected is not False:
                    try:
                        async with aiohttp.ClientSession() as session:
                            async with session.ws_connect(self._ws_url) as ws:
                                self._ws = ws
                                self._connected = True
                                logger.info(
                                    f"[{self.platform_id}] 已连接到 {self._ws_url}"
                                )
                                retry_delay = 1

                                async for msg in ws:
                                    if msg.type == aiohttp.WSMsgType.TEXT:
                                        await self._handle_onebot_message(
                                            json.loads(msg.data)
                                        )
                                    elif msg.type == aiohttp.WSMsgType.ERROR:
                                        logger.error(
                                            f"[{self.platform_id}] WebSocket 错误"
                                        )
                                        break

                    except Exception as e:
                        logger.warning(
                            f"[{self.platform_id}] 连接断开: {e}, {retry_delay}s 后重连"
                        )
                        self._connected = False
                        self._ws = None
                        await asyncio.sleep(retry_delay)
                        retry_delay = min(retry_delay * 2, 30)

            self._tasks.append(asyncio.create_task(listen_loop()))
            await asyncio.sleep(0.5)
            return True

        except ImportError:
            logger.error(f"[{self.platform_id}] 请安装 aiohttp")
            return False
        except Exception as e:
            logger.error(f"[{self.platform_id}] 连接异常: {e}", exc_info=True)
            return False

    async def _handle_onebot_message(self, data: Dict):
        """处理 OneBot 消息"""
        try:
            post_type = data.get("post_type", "")
            if post_type == "message":
                await self._handle_chat_message(data)
            elif post_type == "notice":
                logger.debug(f"[{self.platform_id}] 通知: {data.get('notice_type')}")
            elif post_type == "request":
                logger.debug(f"[{self.platform_id}] 请求: {data.get('request_type')}")
        except Exception as e:
            logger.error(f"[{self.platform_id}] 消息处理异常: {e}")

    async def _handle_chat_message(self, data: Dict):
        """处理聊天消息"""
        msg_type = data.get("message_type", "private")
        sender = data.get("sender", {})
        raw_message = data.get("raw_message", data.get("message", ""))

        if isinstance(raw_message, list):
            text_parts = [
                p.get("data", {}).get("text", "")
                for p in raw_message
                if p.get("type") == "text"
            ]
            content = "".join(text_parts)
        else:
            content = str(raw_message)

        if not content.strip():
            return

        user_id = str(sender.get("user_id", ""))
        user_name = sender.get("nickname", user_id)
        group_id = str(data.get("group_id", ""))

        logger.debug(f"[{self.platform_id}] 收到消息: {content[:50]}")

        response = await self.route_to_decision_hub(
            content=content,
            user_id=user_id,
            user_name=user_name,
            message_type=msg_type,
            group_id=group_id,
        )

        await self._send_onebot_reply(data, response)

    async def _send_onebot_reply(self, original: Dict, text: str):
        """发送 OneBot 回复"""
        if not self._ws or not self._connected:
            return

        msg_type = original.get("message_type", "private")
        reply_data = {
            "action": "send_msg",
            "params": {
                "message_type": msg_type,
                "message": text,
            },
        }

        if msg_type == "private":
            reply_data["params"]["user_id"] = original.get("sender", {}).get("user_id")
        elif msg_type == "group":
            reply_data["params"]["group_id"] = original.get("group_id")
            reply_data["params"]["message"] = text

        try:
            await self._ws.send_str(json.dumps(reply_data))
        except Exception as e:
            logger.error(f"[{self.platform_id}] 发送回复异常: {e}")

    async def _do_disconnect(self):
        self._connected = False
        if self._ws:
            try:
                await self._ws.close()
            except Exception:
                pass
        self._ws = None

    async def _do_health_check(self) -> bool:
        return self._connected and self._ws is not None

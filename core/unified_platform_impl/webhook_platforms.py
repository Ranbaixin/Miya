"""
飞书 / KOOK / Slack / LINE / 钉钉 / Satori — Webhook 平台实现

所有 webhook 平台共享 FastAPI 路由，通过 management_api 动态注册。
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging

from .webhook_base import WebhookPlatform

logger = logging.getLogger("Miya.Platform.Webhooks")


class LarkPlatform(WebhookPlatform):
    """飞书 (Lark) — SDK 长连接"""

    platform_id = "lark"
    platform_name = "飞书"
    health_check_interval = 120.0

    def __init__(self, config=None):
        super().__init__(config)
        import os

        self._app_id = (config.get("app_id", "") if config else "") or os.environ.get(
            "LARK_APP_ID", ""
        )
        self._app_secret = (
            config.get("app_secret", "") if config else ""
        ) or os.environ.get("LARK_APP_SECRET", "")
        self._ws_client = None

    async def _do_connect(self) -> bool:
        if not self._app_id or not self._app_secret:
            logger.error("[lark] 缺少 app_id 或 app_secret")
            return False
        try:
            from lark_oapi.api.im.v1.model.p2_im_message_receive_v1 import (
                P2ImMessageReceiveV1,
            )
            from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
            from lark_oapi.ws import Client

            platform = self

            def on_message(data: P2ImMessageReceiveV1):
                try:
                    event = data.event
                    msg = event.message
                    content = (
                        json.loads(msg.content).get("text", "") if msg.content else ""
                    )
                    user_id = event.sender.sender_id.user_id if event.sender else ""
                    chat_id = msg.chat_id or ""
                    msg_type = "group" if msg.chat_type == "group" else "private"
                    if content.strip():
                        asyncio.create_task(
                            platform._handle_lark_message(
                                content, user_id, chat_id, msg_type
                            )
                        )
                except Exception as e:
                    logger.warning(f"[lark] 消息异常: {e}")

            handler = (
                EventDispatcherHandler.builder("", "")
                .register_p2_im_message_receive_v1(on_message)
                .build()
            )
            self._ws_client = Client(
                app_id=self._app_id,
                app_secret=self._app_secret,
                event_handler=handler,
            )

            async def run_lark_ws():
                await self._ws_client._connect()
                await self._ws_client._ping_loop()
                await self._ws_client._receive_message_loop()

            self._tasks.append(asyncio.create_task(run_lark_ws()))
            logger.info("[lark] 飞书长连接已启动")
            return True
        except ImportError:
            logger.error("[lark] 请安装 lark-oapi")
            return False
        except Exception as e:
            logger.error(f"[lark] 连接失败: {e}", exc_info=True)
            return False

    async def _handle_lark_message(self, content, user_id, chat_id, msg_type):
        response = await self.route_to_decision_hub(
            content=content,
            user_id=str(user_id),
            user_name=str(user_id),
            message_type=msg_type,
            group_id=chat_id,
            is_at_bot="@_all" in content or "@全员" in content,
        )
        if response:
            try:
                import lark_oapi as lark
                from lark_oapi.api.im.v1 import (
                    CreateMessageRequest,
                    CreateMessageRequestBody,
                )

                body = (
                    CreateMessageRequestBody.builder()
                    .receive_id(chat_id)
                    .msg_type("text")
                    .content(json.dumps({"text": response}))
                    .build()
                )
                req = (
                    CreateMessageRequest.builder()
                    .receive_id_type("chat_id")
                    .request_body(body)
                    .build()
                )
                client = (
                    lark.Client.builder()
                    .app_id(self._app_id)
                    .app_secret(self._app_secret)
                    .build()
                )
                client.im.v1.message.create(req)
            except Exception as e:
                logger.warning(f"[lark] 回复失败: {e}")

    async def send_private_message(self, user_id: str, message: str) -> bool:
        """发送主动私聊消息 (v8.1)"""
        if not self._app_id or not self._app_secret:
            logger.debug("[lark] 主动消息跳过: 未配置 app_id/app_secret")
            return False
        try:
            import json

            import lark_oapi as lark
            from lark_oapi.api.im.v1 import (
                CreateMessageRequest,
                CreateMessageRequestBody,
            )

            body = (
                CreateMessageRequestBody.builder()
                .receive_id(str(user_id))
                .msg_type("text")
                .content(json.dumps({"text": message}))
                .build()
            )
            req = (
                CreateMessageRequest.builder()
                .receive_id_type("user_id")  # v8.2: 修复 — 入站 user_id 不能当 open_id 用
                .request_body(body)
                .build()
            )
            client = (
                lark.Client.builder()
                .app_id(self._app_id)
                .app_secret(self._app_secret)
                .build()
            )
            client.im.v1.message.create(req)
            logger.debug("[lark] 主动消息已发送: %s → %s", user_id, message[:30])
            return True
        except Exception as e:
            logger.error("[lark] 主动消息发送失败: %s", e)
            return False

    async def _do_disconnect(self):
        if self._ws_client:
            with contextlib.suppress(Exception):
                await self._ws_client._disconnect()
        self._ws_client = None

    async def _do_health_check(self) -> bool:
        return self._ws_client is not None


class KOOKPlatform(WebhookPlatform):
    """KOOK (开黑啦) 平台"""

    platform_id = "kook"
    platform_name = "KOOK"
    health_check_interval = 120.0

    def __init__(self, config=None):
        super().__init__(config)
        self._token = config.get("token", "") if config else ""
        self._verify_token = config.get("verify_token", "") if config else ""

    def get_webhook_routes(self) -> dict:
        async def webhook_handler(request):
            try:
                body = await request.json()
                d = body.get("d", {})
                challenge = d.get("challenge")
                if challenge:
                    return {"challenge": challenge}

                channel_type = d.get("channel_type", "")
                author = d.get("extra", {}).get("author", {})
                content = d.get("content", "")
                user_id = d.get("author_id", "") or author.get("id", "")

                if content.strip():
                    await self.route_to_decision_hub(
                        content=content,
                        user_id=str(user_id),
                        message_type=channel_type if channel_type else "private",
                    )
                    return {"code": 0}
            except Exception as e:
                logger.warning(f"[kook] webhook error: {e}")
            return {"code": 0}

        return {"prefix": "/webhook/kook", "routes": [("POST", "", webhook_handler)]}


class SlackPlatform(WebhookPlatform):
    """Slack 平台"""

    platform_id = "slack"
    platform_name = "Slack"
    health_check_interval = 120.0

    def __init__(self, config=None):
        super().__init__(config)
        self._signing_secret = config.get("signing_secret", "") if config else ""

    def get_webhook_routes(self) -> dict:
        async def webhook_handler(request):
            try:
                body = await request.json()
                event_type = body.get("type", "")

                if event_type == "url_verification":
                    return {"challenge": body.get("challenge", "")}

                event = body.get("event", {})
                if (
                    event.get("type") != "app_mention"
                    and event.get("type") != "message"
                ):
                    return {"ok": True}

                text = event.get("text", "")
                user_id = event.get("user", "")
                channel = event.get("channel", "")

                if text.strip():
                    await self.route_to_decision_hub(
                        content=text,
                        user_id=str(user_id),
                        message_type="group",
                        group_id=channel,
                    )
                return {"ok": True}
            except Exception as e:
                logger.warning(f"[slack] webhook error: {e}")
                return {"ok": True}

        return {"prefix": "/webhook/slack", "routes": [("POST", "", webhook_handler)]}


class LINEPlatform(WebhookPlatform):
    """LINE 平台"""

    platform_id = "line"
    platform_name = "LINE"
    health_check_interval = 120.0

    def __init__(self, config=None):
        super().__init__(config)
        self._channel_secret = config.get("channel_secret", "") if config else ""

    def get_webhook_routes(self) -> dict:
        async def webhook_handler(request):
            try:
                body = await request.json()
                events = body.get("events", [])
                for event in events:
                    if event.get("type") != "message":
                        continue
                    message = event.get("message", {})
                    text = message.get("text", "")
                    user_id = event.get("source", {}).get("userId", "")
                    msg_type = (
                        "group"
                        if event.get("source", {}).get("type") == "group"
                        else "private"
                    )

                    if text.strip():
                        await self.route_to_decision_hub(
                            content=text,
                            user_id=str(user_id),
                            message_type=msg_type,
                        )
            except Exception as e:
                logger.warning(f"[line] webhook error: {e}")
            return {"status": "ok"}

        return {"prefix": "/webhook/line", "routes": [("POST", "", webhook_handler)]}


class DingTalkPlatform(WebhookPlatform):
    """钉钉 平台"""

    platform_id = "dingtalk"
    platform_name = "钉钉"
    health_check_interval = 120.0

    def __init__(self, config=None):
        super().__init__(config)
        self._app_key = config.get("app_key", "") if config else ""
        self._app_secret = config.get("app_secret", "") if config else ""

    def get_webhook_routes(self) -> dict:
        async def webhook_handler(request):
            try:
                body = await request.json()
                text = (
                    body.get("text", {}).get("content", "")
                    if isinstance(body, dict)
                    else ""
                )
                sender_id = body.get("senderId", "") if isinstance(body, dict) else ""

                if text.strip():
                    response = await self.route_to_decision_hub(
                        content=text,
                        user_id=str(sender_id),
                        message_type="private",
                    )
                    return {"msgtype": "text", "text": {"content": response}}
            except Exception as e:
                logger.warning(f"[dingtalk] webhook error: {e}")
            return {"errcode": 0}

        return {
            "prefix": "/webhook/dingtalk",
            "routes": [("POST", "", webhook_handler)],
        }


class SatoriPlatform(WebhookPlatform):
    """Satori 统一协议平台"""

    platform_id = "satori"
    platform_name = "Satori"
    health_check_interval = 120.0

    def __init__(self, config=None):
        super().__init__(config)

    def get_webhook_routes(self) -> dict:
        async def webhook_handler(request):
            try:
                body = await request.json()
                op = body.get("op", "")
                if op != "message_create":
                    return {"code": 0}

                msg = body.get("message", body.get("payload", {}).get("message", {}))
                content = msg.get("content", "")
                user = body.get("user", body.get("payload", {}).get("user", {}))
                user_id = user.get("id", "")
                body.get(
                    "channel", body.get("payload", {}).get("channel", {})
                )

                if content.strip():
                    await self.route_to_decision_hub(
                        content=content,
                        user_id=str(user_id),
                        message_type="private",
                    )
            except Exception as e:
                logger.warning(f"[satori] webhook error: {e}")
            return {"code": 0}

        return {"prefix": "/webhook/satori", "routes": [("POST", "", webhook_handler)]}

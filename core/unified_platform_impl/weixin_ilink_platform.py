"""
弥娅微信 iLink 平台接入 (BasePlatform 方式)

直接使用 weixin-ilink-client SDK，通过 MessageMixin 路由到 DecisionHub。
"""

from __future__ import annotations

import asyncio
import logging
import time
from pathlib import Path
from typing import Any, Dict, Optional

from core.unified_platform.base import BasePlatform

from .message_mixin import MessageMixin

logger = logging.getLogger("Miya.Platform.WeixinIlink")


class WeixinIlinkPlatform(MessageMixin, BasePlatform):
    platform_id = "weixin_ilink"
    platform_name = "微信 iLink"

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BasePlatform.__init__(self, config)

        self._base_url = str(
            self.config.get("base_url", "https://ilinkai.weixin.qq.com")
        ).rstrip("/")
        self._cdn_base_url = str(
            self.config.get("cdn_base_url", "https://novac2c.cdn.weixin.qq.com/c2c")
        ).rstrip("/")
        self._account_id: str | None = (
            str(self.config.get("account_id", "")).strip() or None
        )
        self._token: str | None = (
            str(self.config.get("bot_token", "")).strip() or None
        )
        self._user_id: str | None = (
            str(self.config.get("user_id", "")).strip() or None
        )

        self._client = None
        self._client_ready = False
        self._shutdown_event = asyncio.Event()
        self._message_task: asyncio.Task | None = None

    async def _do_connect(self) -> bool:
        try:
            from weixin_ilink_client import (
                AsyncWeixinIlinkClient,
                ClientOptions,
                JsonCredentialStore,
                MemoryStateStore,
                WeixinCredentials,
                default_state_dir,
            )

            state_dir = str(self.config.get("state_dir", "")).strip()
            store_dir = Path(state_dir) if state_dir else default_state_dir()
            store_dir.mkdir(parents=True, exist_ok=True)

            credential_store = JsonCredentialStore(store_dir / "credentials.json")

            if not self._token or not self._account_id:
                try:
                    saved = await credential_store.get("weixin_ilink")
                    if saved:
                        self._account_id = saved.account_id
                        self._token = saved.bot_token
                        self._user_id = saved.user_id
                        if saved.base_url:
                            self._base_url = saved.base_url.rstrip("/")
                        logger.info(
                            "[weixin_ilink] 从缓存加载凭据: account=%s", self._account_id
                        )
                except Exception as e:
                    logger.debug("[weixin_ilink] 无缓存凭据: %s", e)

                if not self._token:
                    acc_id, token, uid, url = self._load_fallback_credentials(store_dir)
                    if token:
                        self._account_id = acc_id
                        self._token = token
                        self._user_id = uid
                        if url:
                            self._base_url = url.rstrip("/")
                        logger.info(
                            "[weixin_ilink] 兜底凭据加载成功: account=%s",
                            self._account_id,
                        )

            if not self._token or not self._account_id or not self._user_id:
                logger.warning(
                    "[weixin_ilink] 未登录，请先运行: python scripts/weixin_ilink_login.py"
                )
                return False

            credentials = WeixinCredentials(
                account_id=self._account_id,
                bot_token=self._token,
                base_url=self._base_url,
                user_id=self._user_id,
            )

            state_store = MemoryStateStore()

            options = ClientOptions(cdn_base_url=self._cdn_base_url)

            self._client = AsyncWeixinIlinkClient(
                credentials,
                state_store=state_store,
                options=options,
            )

            self._shutdown_event.clear()
            self._client_ready = False
            self._message_task = asyncio.create_task(self._run_message_loop())

            logger.info("[weixin_ilink] 已连接, account=%s", self._account_id)
            return True

        except Exception as e:
            logger.error("[weixin_ilink] 连接失败: %s", e, exc_info=True)
            return False

    async def _run_message_loop(self):
        from weixin_ilink_client.errors import SessionPausedError, WeixinIlinkError

        if not self._client:
            return

        async def on_message(msg):
            await self._handle_inbound_message(msg)

        while not self._shutdown_event.is_set():
            try:
                self._client_ready = True
                await self._client.run(on_message, stop_event=self._shutdown_event)
            except asyncio.CancelledError:
                break
            except SessionPausedError:
                logger.warning("[weixin_ilink] 会话暂停，等待恢复...")
                await asyncio.sleep(10)
            except WeixinIlinkError as e:
                logger.error("[weixin_ilink] iLink 错误: %s，5秒后重试", e)
                await asyncio.sleep(5)
            except Exception as e:
                logger.error("[weixin_ilink] 消息循环异常: %s，5秒后重试", e)
                await asyncio.sleep(5)
            finally:
                self._client_ready = False

    async def _handle_inbound_message(self, msg):
        from weixin_ilink_client import MessageItemType

        from_user_id = msg.from_user_id
        if not from_user_id:
            return

        text = msg.text or ""

        logger.debug("[weixin_ilink] 收到消息: %s → %s", from_user_id, text[:50])

        response = await self.route_to_decision_hub(
            content=text,
            user_id=from_user_id,
            user_name=from_user_id,
            message_type="private",
            is_at_bot=True,
        )

        if response and self._client and self._client_ready:
            try:
                await self._client.send_text(from_user_id, response)
            except Exception as e:
                logger.error("[weixin_ilink] 发送回复失败: %s", e)

    async def send_private_message(self, user_id: str, message: str) -> bool:
        """发送主动私聊消息 (v8.1: 含诊断日志 + 重试)"""
        if not self._client or not self._client_ready:
            logger.warning(
                "[weixin_ilink] 主动消息拒绝: client=%s, ready=%s",
                self._client is not None,
                self._client_ready,
            )
            return False
        uid = str(user_id)
        msg_preview = message[:60]
        logger.info(
            "[weixin_ilink] 主动消息发送中: uid=%s, msg_len=%d, preview=%s",
            uid,
            len(message),
            msg_preview,
        )
        for attempt in range(2):
            try:
                await self._client.send_text(uid, message)
                logger.info("[weixin_ilink] 主动消息已发送 (attempt=%d): %s → %s", attempt + 1, uid, msg_preview)
                return True
            except Exception as e:
                logger.warning(
                    "[weixin_ilink] 主动消息发送失败 (attempt=%d/%d): uid=%s, error=%s",
                    attempt + 1,
                    2,
                    uid,
                    e,
                )
                if attempt == 0:
                    await asyncio.sleep(1.0)
        return False

    async def _do_disconnect(self):
        self._shutdown_event.set()
        if self._message_task and not self._message_task.done():
            self._message_task.cancel()
            try:
                await self._message_task
            except asyncio.CancelledError:
                pass
        if self._client:
            try:
                await self._client.aclose()
            except Exception:
                pass
            self._client = None
        self._client_ready = False
        logger.info("[weixin_ilink] 已断开")

    async def _do_health_check(self) -> bool:
        return self._client_ready

    @staticmethod
    def _load_fallback_credentials(store_dir: Path):
        import json

        fallback = store_dir / "credentials_fallback.json"
        if not fallback.exists():
            return
        try:
            data = json.loads(fallback.read_text())
            accounts = data.get("accounts", {})
            for alias, acc in accounts.items():
                logger.info(
                    "[weixin_ilink] 从兜底文件加载凭据: alias=%s, account=%s",
                    alias,
                    acc.get("account_id", ""),
                )
                return acc.get("account_id"), acc.get("bot_token"), acc.get(
                    "user_id"
                ), acc.get("base_url", "")
        except Exception as e:
            logger.debug("[weixin_ilink] 兜底文件读取失败: %s", e)
        return None, None, None, None

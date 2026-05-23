"""
通用平台适配器 (含 WebChat)

用于 SDK 暂不可用或需要以 webhook 模式运行的平台。
"""

from __future__ import annotations

import logging
from typing import Any, Dict, Optional

from core.unified_platform.base import BasePlatform

from .message_mixin import MessageMixin

logger = logging.getLogger("Miya.Platform.Generic")


class GenericPlatform(MessageMixin, BasePlatform):
    """
    通用平台适配器

    用于 webhook 型平台（飞书、钉钉、企业微信等）。
    提供基础连接/断开框架，子类覆写 connect/disconnect 即可。
    """

    platform_id = "generic"
    platform_name = "通用平台"
    health_check_interval = 30.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BasePlatform.__init__(self, config)
        self._connected = False

    async def _do_connect(self) -> bool:
        self._connected = True
        logger.info(f"[{self.platform_id}] 已启动 (通用适配器)")
        return True

    async def _do_disconnect(self):
        self._connected = False

    async def _do_health_check(self) -> bool:
        return self._connected


class WebChatPlatform(MessageMixin, BasePlatform):
    """内置网页聊天平台"""

    platform_id = "webchat"
    platform_name = "网页聊天"
    health_check_interval = 30.0

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        BasePlatform.__init__(self, config)
        self._initialized = False

    async def _do_connect(self) -> bool:
        port = self.config.get("port", 5000)
        host = self.config.get("host", "0.0.0.0")
        logger.info(f"[webchat] 网页聊天就绪 ({host}:{port})")
        self._initialized = True
        return True

    async def _do_disconnect(self):
        logger.info("[webchat] 网页聊天已停止")

    async def _do_health_check(self) -> bool:
        return True

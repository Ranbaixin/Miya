"""
平台适配器管理器 - Platform Adapters

18平台统一管理
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger("miya.adapters")


AVAILABLE_ADAPTERS = {
    # ===== 官方平台 =====
    "qq": {
        "name": "QQ",
        "adapter": "QQAdapter",
    },
    "telegram": {
        "name": "Telegram",
        "adapter": "TelegramAdapter",
    },
    "discord": {
        "name": "Discord",
        "adapter": "DiscordAdapter",
    },
    "slack": {
        "name": "Slack",
        "adapter": "SlackAdapter",
    },
    "lark": {
        "name": "飞书/Lark",
        "adapter": "LarkAdapter",
    },
    "dingtalk": {
        "name": "钉钉",
        "adapter": "DingTalkAdapter",
    },
    "wecom": {
        "name": "企业微信",
        "adapter": "WeComAdapter",
    },
    "kook": {
        "name": "KOOK",
        "adapter": "KOOKAdapter",
    },
    "satori": {
        "name": "Satori",
        "adapter": "SatoriAdapter",
    },
    "line": {
        "name": "LINE",
        "adapter": "LINEAdapter",
    },
    "mattermost": {
        "name": "Mattermost",
        "adapter": "MattermostAdapter",
    },
    "misskey": {
        "name": "Misskey",
        "adapter": "MisskeyAdapter",
    },
    "webchat": {
        "name": "WebChat",
        "adapter": "WebChatAdapter",
    },
    "weixin_oa": {
        "name": "微信公众平台",
        "adapter": "WeixinOAAdapter",
    },
    "weixin_oc": {
        "name": "微信开放平台",
        "adapter": "WeixinOCAdapter",
    },
    "terminal": {
        "name": "终端",
        "adapter": "TerminalAdapter",
    },
    "web": {
        "name": "Web",
        "adapter": "WebAdapter",
    },
    "pc": {
        "name": "PC UI",
        "adapter": "PCAdapter",
    },
}


class AdapterManager:
    """平台适配器管理器"""

    def __init__(self) -> None:
        self._adapters: Dict[str, Any] = {}
        self._event_queue: asyncio.Queue = asyncio.Queue()

    async def initialize(self, configs: List[Dict]) -> None:
        """初始化"""
        logger.info("[Adapter] 初始化平台适配器...")

        for config in configs:
            adapter_type = config.get("type")
            if adapter_type in AVAILABLE_ADAPTERS:
                await self._create_adapter(adapter_type, config)

        logger.info(f"[Adapter] 已加载 {len(self._adapters)} 个平台")

    async def _create_adapter(self, adapter_type: str, config: Dict) -> None:
        """创建适配器"""
        adapter_info = AVAILABLE_ADAPTERS[adapter_type]

        try:
            # 尝试导入
            from hub.platform_adapters import get_adapter

            adapter_cls = get_adapter(adapter_type)
            if adapter_cls:
                adapter_id = config.get("id", adapter_type)
                self._adapters[adapter_id] = adapter_cls(adapter_id)
                logger.info(f"[Adapter] 创建: {adapter_type}")
        except Exception as e:
            logger.warning(f"[Adapter] 创建失败 {adapter_type}: {e}")

    def get(self, adapter_id: str) -> Optional[Any]:
        """获取适配器"""
        return self._adapters.get(adapter_id)

    def list_all(self) -> Dict[str, str]:
        """列出所有适配器"""
        return {k: v["name"] for k, v in AVAILABLE_ADAPTERS.items()}


# 全局实例
_adapter_manager: Optional[AdapterManager] = None


def get_adapter_manager() -> AdapterManager:
    global _adapter_manager
    if _adapter_manager is None:
        _adapter_manager = AdapterManager()
    return _adapter_manager


__all__ = ["AdapterManager", "get_adapter_manager", "AVAILABLE_ADAPTERS"]

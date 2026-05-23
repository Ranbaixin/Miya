"""
Platform Bridge - 平台桥接器

将 core/platform (新架构) 与 hub/platform_adapters (旧系统) 连接
"""

import asyncio
import logging
from typing import Any, Dict, Optional

logger = logging.getLogger("miya.platform.bridge")


class PlatformBridge:
    """平台桥接器 - 连接新旧平台系统"""

    def __init__(self, platform_manager=None) -> None:
        self.platform_manager = platform_manager
        self._event_queue: asyncio.Queue | None = None
        self._running = False

    async def initialize(self, event_queue: asyncio.Queue) -> None:
        """初始化桥接器"""
        self._event_queue = event_queue
        logger.info("[PlatformBridge] 平台桥接器已初始化")

    async def start_listening(self) -> None:
        """开始监听事件"""
        if not self._event_queue:
            logger.warning("[PlatformBridge] 事件队列未初始化")
            return

        self._running = True
        logger.info("[PlatformBridge] 开始监听平台事件...")

        while self._running:
            try:
                event = await self._event_queue.get()
                await self._handle_event(event)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[PlatformBridge] 处理事件失败: {e}")

    async def _handle_event(self, event) -> None:
        """处理平台事件"""
        logger.debug(f"[PlatformBridge] 收到事件: {event}")

        # 将事件转换为 M-Link Message
        if hasattr(event, "message_str"):
            # 使用主系统的消息格式
            from hub.platform_adapters import get_adapter

            platform_name = getattr(event, "platform_id", "unknown")
            try:
                adapter = get_adapter(platform_name)
                message = adapter.to_message(
                    event.message_str,
                    {
                        "user_id": event.user_id,
                        "session_id": event.session_id,
                        "group_id": event.group_id,
                        "timestamp": event.timestamp,
                    },
                )
                # 发送到 M-Link
                from mlink import MLinkCore

                mlink = MLinkCore()
                await mlink.send(message)
            except Exception as e:
                logger.error(f"[PlatformBridge] 事件转换失败: {e}")

    async def stop(self) -> None:
        """停止桥接器"""
        self._running = False
        logger.info("[PlatformBridge] 已停止")


# 新平台适配器注册表
_platform_adapters: Dict[str, type] = {}


def register_miya_platform(platform_id: str):
    """注册新平台适配器"""

    def decorator(cls):
        _platform_adapters[platform_id] = cls
        logger.info(f"[PlatformBridge] 注册平台: {platform_id}")
        return cls

    return decorator


def get_miya_platform(platform_id: str) -> Optional[type]:
    """获取平台适配器类"""
    return _platform_adapters.get(platform_id)


def list_miya_platforms() -> list:
    """列出所有平台"""
    return list(_platform_adapters.keys())


async def create_platform_instance(
    platform_id: str,
    config: dict,
    event_queue: asyncio.Queue,
) -> Optional[Any]:
    """创建平台实例"""
    cls = get_miya_platform(platform_id)
    if not cls:
        logger.warning(f"[PlatformBridge] 未知平台: {platform_id}")
        return None

    try:
        instance = cls(config, event_queue)
        logger.info(f"[PlatformBridge] 创建平台实例: {platform_id}")
        return instance
    except Exception as e:
        logger.error(f"[PlatformBridge] 创建平台失败 {platform_id}: {e}")
        return None


__all__ = [
    "PlatformBridge",
    "register_miya_platform",
    "get_miya_platform",
    "list_miya_platforms",
    "create_platform_instance",
]

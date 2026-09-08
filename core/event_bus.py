"""轻量事件总线（2026-09 新增）

用途：核心链路（如平台消息收发）向外部观察者广播事件，
当前消费者：ManagementAPI → WebSocket /api/v1/ws 实时推送（new_message）。

设计约束：
- 零依赖、不 import 任何业务模块，避免循环导入；
- emit_event 必须在事件循环内调用（消息处理链路均为 async 上下文）；
- 监听器异常绝不影响主链路（只记日志）。
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Awaitable, Callable, Dict, List, Union

logger = logging.getLogger(__name__)

Listener = Union[
    Callable[[Dict[str, Any]], None],
    Callable[[Dict[str, Any]], Awaitable[None]],
]

_sync_listeners: List[Callable[[Dict[str, Any]], None]] = []
_async_listeners: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []


def on_event(fn: Listener) -> Listener:
    """注册事件监听器（自动区分同步/异步）"""
    if asyncio.iscoroutinefunction(fn):
        _async_listeners.append(fn)
    else:
        _sync_listeners.append(fn)
    return fn


def emit_event(event: Dict[str, Any]) -> None:
    """广播事件（fire-and-forget；绝不抛出、不阻塞主链路）"""
    for fn in list(_sync_listeners):
        try:
            fn(event)
        except Exception as e:  # noqa: BLE001 — 事件总线吞掉监听器异常并记录
            logger.debug(f"[event_bus] 同步监听器异常: {e}")
    for fn in list(_async_listeners):
        try:
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop is not None:
                loop.create_task(_safe_call(fn, event))
            else:
                logger.debug("[event_bus] 无运行中的事件循环，跳过异步监听器")
        except Exception as e:  # noqa: BLE001 — 调度失败仅记录
            logger.debug(f"[event_bus] 异步监听器调度失败: {e}")


async def _safe_call(fn, event: Dict[str, Any]) -> None:
    try:
        await fn(event)
    except Exception as e:  # noqa: BLE001 — 异步监听器异常记录后吞掉
        logger.debug(f"[event_bus] 异步监听器执行异常: {e}")

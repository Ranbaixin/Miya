"""单例工厂装饰器（P7.3 线程安全修复）。

背景：P5 在独立线程跑 uvicorn，90+ 全局单例无锁保护。本模块提供
同步/异步两种单例装饰器，**不改 get_xxx() 调用签名**，只加锁保证
跨线程/跨事件循环只构造一次。

使用约定：
    @sync_singleton
    def get_xxx() -> Xxx:
        return Xxx()

    @async_singleton
    async def get_xxx() -> Xxx:
        x = Xxx()
        await x.initialize()
        return x

不要做的事：
- 不要用 functools.lru_cache（unhashable 参数会炸，无 reset 语义）
- 不要用 threading.local（每线程一个实例 = 正好是 bug）
"""

from __future__ import annotations

import functools
import threading
from collections.abc import Callable
from typing import Any, TypeVar

T = TypeVar("T")

_SYNC_LOCK = threading.RLock()


def sync_singleton(fn: Callable[..., T]) -> Callable[..., T]:
    """同步单例工厂 —— 不改 get_xxx() 调用签名。

    首次调用在 _SYNC_LOCK 内构造，之后直接返回缓存实例。
    参数只影响首次初始化（与原有 global + if None 语义一致）。
    """

    cell: dict[str, T] = {}

    @functools.wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> T:
        if "v" in cell:
            return cell["v"]
        with _SYNC_LOCK:
            if "v" not in cell:
                cell["v"] = fn(*args, **kwargs)
            return cell["v"]

    wrapper.reset = lambda: cell.clear()  # type: ignore[attr-defined]  # 测试专用
    return wrapper


def async_singleton(fn: Callable[..., Any]) -> Callable[..., Any]:
    """异步单例工厂 —— 按事件循环分桶，防止跨 loop 复用导致错误。

    同一事件循环内只构造一次；不同 loop 各自持有实例。
    """

    cells: dict[Any, Any] = {}
    locks: dict[Any, Any] = {}

    @functools.wraps(fn)
    async def wrapper(*args: Any, **kwargs: Any) -> Any:
        import asyncio

        loop = asyncio.get_running_loop()
        if loop in cells:
            return cells[loop]
        lk = locks.setdefault(loop, asyncio.Lock())
        async with lk:
            if loop not in cells:
                cells[loop] = await fn(*args, **kwargs)
            return cells[loop]

    wrapper.reset = lambda: (cells.clear(), locks.clear())  # type: ignore[attr-defined]  # 测试专用
    return wrapper

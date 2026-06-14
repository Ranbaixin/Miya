"""
M-Link 消息队列模块
提供异步消息排队和持久化能力
"""

import asyncio
import logging
from collections import deque
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MessageQueue:
    """异步消息队列"""

    def __init__(self, max_size: int = 1000):
        self._queue: deque = deque()  # 不用 maxlen（会导致静默丢弃）
        self._max_size = max_size
        self._lock = asyncio.Lock()
        self._stats = {"enqueued": 0, "dequeued": 0, "dropped": 0}

    async def enqueue(self, message: Any) -> bool:
        async with self._lock:
            if len(self._queue) >= self._max_size:
                self._stats["dropped"] += 1
                return False
            self._queue.append(message)
            self._stats["enqueued"] += 1
            return True

    async def dequeue(self) -> Optional[Any]:
        async with self._lock:
            if not self._queue:
                return None
            self._stats["dequeued"] += 1
            return self._queue.popleft()

    async def peek(self, n: int = 1) -> List[Any]:
        async with self._lock:
            items = list(self._queue)[:n]
            return items

    async def size(self) -> int:
        return len(self._queue)

    def get_stats(self) -> Dict:
        return dict(self._stats)

    async def stop_processor(self):
        """停止消息处理器（兼容 mlink_core 调用）"""
        logger.info("[MessageQueue] 处理器已停止")

    async def clear(self):
        async with self._lock:
            self._queue.clear()

"""车站-列车消息队列模型

借鉴 Undefined 的 queue_manager.py 设计：
- per-Model 独立队列组（"站台"）
- 4 级优先级调度 (超管 > 私聊 > @提及 > 普通群聊)
- 可配置节奏的非阻塞调度循环
- 群聊队列自动修剪
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger(__name__)


@dataclass
class QueueRequest:
    """队列请求"""

    request_id: str
    priority: int  # 0=超管, 1=私聊, 2=@提及, 3=普通群聊, 9=后台
    payload: Any
    timestamp: float = field(default_factory=time.time)
    model_name: str = "default"
    max_retries: int = 0
    retry_count: int = 0


class LaneQueue:
    """单优先级通道 (FIFO + 修剪)"""

    def __init__(self, max_size: int = 0):
        self._queue: deque[QueueRequest] = deque()
        self.max_size = max_size

    def put(self, request: QueueRequest) -> None:
        self._queue.append(request)
        self._trim()

    def put_second(self, request: QueueRequest) -> None:
        """插入到第二位 (重试时跳过当前处理中的)"""
        if len(self._queue) <= 1:
            self._queue.append(request)
        else:
            items = list(self._queue)
            self._queue.clear()
            self._queue.append(items[0])
            self._queue.append(request)
            self._queue.extend(items[1:])
        self._trim()

    def get(self) -> QueueRequest | None:
        if self._queue:
            return self._queue.popleft()
        return None

    def _trim(self) -> None:
        """超过 max_size 时保留最新 N 条"""
        if self.max_size > 0 and len(self._queue) > self.max_size:
            keep = self.max_size // 2
            while len(self._queue) > keep:
                self._queue.popleft()

    def __len__(self) -> int:
        return len(self._queue)

    def __bool__(self) -> bool:
        return bool(self._queue)


class ModelQueue:
    """单模型队列组 (多优先级通道)"""

    def __init__(self, model_name: str, interval: float = 1.0):
        self.model_name = model_name
        self.interval = interval  # 发车间隔

        self.admin_queue = LaneQueue()  # P0: 超管
        self.private_queue = LaneQueue()  # P1: 私聊
        self.mention_queue = LaneQueue()  # P2: @提及
        self.group_queue = LaneQueue(
            max_size=10
        )  # P3: 普通群聊 (最多缓存10条, 超了只保留最新2)
        self.background_queue = LaneQueue()  # P9: 后台任务

        self._dispatch_task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    def put(self, request: QueueRequest) -> None:
        """按优先级投递到对应通道"""
        if request.priority == 0:
            self.admin_queue.put(request)
        elif request.priority == 1:
            self.private_queue.put(request)
        elif request.priority == 2:
            self.mention_queue.put(request)
        elif request.priority == 9:
            self.background_queue.put(request)
        else:
            self.group_queue.put(request)

    def total_pending(self) -> int:
        return (
            len(self.admin_queue)
            + len(self.private_queue)
            + len(self.mention_queue)
            + len(self.group_queue)
            + len(self.background_queue)
        )


class QueueManager:
    """车站-列车队列管理器

    每个 AI 模型 = 一个站台 (ModelQueue)
    站台内通道:
        P0: admin (严格优先)
        P1+P2+P3: private → mention → group (轮转调度, 每通道取2个后切换)
        P9: background (最低优先级)

    发车间隔控制请求节奏
    """

    def __init__(
        self,
        models: dict[str, float] | None = None,
        default_interval: float = 1.0,
    ):
        """
        Args:
            models: {model_name: interval_seconds} 模型队列配置
            default_interval: 默认发车间隔
        """
        model_configs = models or {"default": default_interval}
        self._model_queues: dict[str, ModelQueue] = {
            name: ModelQueue(name, interval) for name, interval in model_configs.items()
        }
        self._handler: Callable[[QueueRequest], Any] | None = None
        self._max_retries: int = 2
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._running = False

    @classmethod
    def from_config(cls) -> "QueueManager":
        from config.config_utils import get_queue_config

        cfg = get_queue_config()
        models_config = cfg.get("models", {})

        models: dict[str, float] = {}
        for name, model_cfg in models_config.items():
            if isinstance(model_cfg, dict):
                models[name] = model_cfg.get("interval", 1.0)

        return cls(
            models=models if models else None,
            default_interval=cfg.get("default_interval", 1.0),
        )

    def set_handler(self, handler: Callable[[QueueRequest], Any]) -> None:
        self._handler = handler

    def update_max_retries(self, max_retries: int) -> None:
        self._max_retries = max_retries

    def update_model_intervals(self, intervals: dict[str, float]) -> None:
        """热更新模型发车间隔"""
        for name, interval in intervals.items():
            if name in self._model_queues:
                self._model_queues[name].interval = interval
            else:
                self._model_queues[name] = ModelQueue(name, interval)
        logger.info("[Queue] 模型间隔已更新: %s", intervals)

    async def start(self) -> None:
        """启动所有模型的调度 loop"""
        self._running = True
        for name, mq in self._model_queues.items():
            mq._stop_event.clear()
            mq._dispatch_task = asyncio.create_task(self._dispatch_loop(name, mq))
        logger.info("[Queue] 已启动: %s 个模型队列", len(self._model_queues))

    async def stop(self) -> None:
        """停止所有调度 loop"""
        self._running = False
        for mq in self._model_queues.values():
            mq._stop_event.set()
        tasks = [
            mq._dispatch_task for mq in self._model_queues.values() if mq._dispatch_task
        ]
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        logger.info("[Queue] 已停止")

    def enqueue(self, request: QueueRequest) -> None:
        """投递请求"""
        mq = self._model_queues.get(request.model_name)
        if mq is None:
            mq = self._model_queues["default"]
        mq.put(request)
        logger.debug(
            "[Queue] 入队: id=%s model=%s priority=%s pending=%s",
            request.request_id[:8],
            request.model_name,
            request.priority,
            mq.total_pending(),
        )

    async def _dispatch_loop(self, name: str, mq: ModelQueue) -> None:
        rotate_step = 0  # 轮转计数器
        while self._running and not mq._stop_event.is_set():
            request = self._get_next_request(mq, rotate_step)
            if request is None:
                await asyncio.sleep(mq.interval)
                rotate_step = 0
                continue

            rotate_step += 1
            if self._handler:
                try:
                    await self._handler(request)
                except Exception as e:
                    logger.warning(
                        "[Queue] 处理请求失败: id=%s error=%s",
                        request.request_id[:8],
                        e,
                    )
                    if request.retry_count < self._max_retries:
                        request.retry_count += 1
                        mq.put_second(request)

            await asyncio.sleep(mq.interval)

    def _get_next_request(self, mq: ModelQueue, step: int) -> QueueRequest | None:
        """获取下一个请求 (严格优先 + 轮转调度)"""
        # P0: admin 严格优先
        req = mq.admin_queue.get()
        if req:
            return req

        # P1+P2+P3: 轮转调度, 每通道连续取 2 个后切换
        lanes = [mq.private_queue, mq.mention_queue, mq.group_queue]
        lane_idx = (step // 2) % 3
        for offset in range(3):
            idx = (lane_idx + offset) % 3
            req = lanes[idx].get()
            if req:
                return req

        # P9: background
        return mq.background_queue.get()

    def estimate_wait(self, model_name: str = "default") -> float:
        """估算等待时间"""
        mq = self._model_queues.get(model_name)
        if mq is None:
            mq = self._model_queues["default"]
        return mq.total_pending() * mq.interval

    def pending_count(self, model_name: str = "default") -> int:
        """获取待处理数量"""
        mq = self._model_queues.get(model_name)
        if mq is None:
            mq = self._model_queues["default"]
        return mq.total_pending()

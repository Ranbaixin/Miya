"""后台史官 Worker

借鉴 Undefined 的 historian.py 设计：
- 轮询 + 重试 Worker 模式
- 两阶段管道: 改写 → 侧写合并
- Inflight 任务追踪
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any, Callable

from cognitive.job_queue import JobQueue
from cognitive.vector_store import CognitiveVectorStore
from cognitive.profile_storage import ProfileStorage

logger = logging.getLogger(__name__)


class HistorianWorker:
    """后台史官 Worker

    职责:
        1. 从 JobQueue 取 pending 任务
        2. 调用 LLM 进行绝对化改写
        3. 写入向量存储
        4. 触发侧写合并更新
    """

    def __init__(
        self,
        job_queue: JobQueue,
        vector_store: CognitiveVectorStore,
        profile_storage: ProfileStorage,
        get_embedding: Callable[[str], list[float]],
        call_llm: Callable[..., Any] | None = None,
        poll_interval: float = 1.0,
        max_retries: int = 3,
        max_concurrency: int = 4,
    ) -> None:
        self.job_queue = job_queue
        self.vector_store = vector_store
        self.profile_storage = profile_storage
        self._get_embedding = get_embedding
        self._call_llm = call_llm
        self.poll_interval = poll_interval
        self.max_retries = max_retries
        self.max_concurrency = max_concurrency

        self._stop_event = asyncio.Event()
        self._task: asyncio.Task[None] | None = None
        self._inflight_tasks: set[asyncio.Task[Any]] = set()

    @classmethod
    def from_config(
        cls,
        job_queue: "JobQueue" = None,
        vector_store: "CognitiveVectorStore" = None,
        profile_storage: "ProfileStorage" = None,
        get_embedding=None,
        call_llm=None,
    ) -> "HistorianWorker":
        from config.config_utils import get_cognitive_config

        cfg = get_cognitive_config()
        historian = cfg.get("historian", {})

        return cls(
            job_queue=job_queue,
            vector_store=vector_store,
            profile_storage=profile_storage,
            get_embedding=get_embedding,
            call_llm=call_llm,
            poll_interval=historian.get("poll_interval_seconds", 1.0),
            max_retries=historian.get("max_retries", 3),
            max_concurrency=historian.get("max_concurrency", 4),
        )

    async def start(self) -> None:
        """启动 Worker 轮询 loop"""
        self._stop_event.clear()
        self._task = asyncio.create_task(self._poll_loop())
        logger.info(
            "[Historian] 已启动: interval=%.2fs concurrency=%s",
            self.poll_interval,
            self.max_concurrency,
        )

    async def stop(self, timeout: float | None = 5.0) -> None:
        """停止 Worker"""
        self._stop_event.set()
        if self._inflight_tasks:
            logger.info(
                "[Historian] 等待 %s 个进行中任务完成...",
                len(self._inflight_tasks),
            )
            try:
                await asyncio.wait_for(
                    asyncio.gather(*self._inflight_tasks, return_exceptions=True),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                logger.warning("[Historian] 停止超时，强制取消")
                for t in self._inflight_tasks:
                    t.cancel()
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[Historian] 已停止")

    async def _poll_loop(self) -> None:
        while not self._stop_event.is_set():
            # 恢复过期任务
            await self.job_queue.recover_stale()

            # 控制并发数
            if len(self._inflight_tasks) >= self.max_concurrency:
                await asyncio.sleep(self.poll_interval)
                continue

            job = await self.job_queue.dequeue()
            if job is None:
                await asyncio.sleep(self.poll_interval)
                continue

            task = asyncio.create_task(self._process_job(job))
            self._inflight_tasks.add(task)
            task.add_done_callback(self._inflight_tasks.discard)

    async def _process_job(self, job: dict[str, Any]) -> None:
        job_id = job.get("job_id", "unknown")
        retry_count = job.get("_retry_count", 0)
        logger.debug("[Historian] 处理任务: %s (retry=%s)", job_id, retry_count)

        try:
            text = job.get("text", "")
            if not text:
                await self.job_queue.done(job)
                return

            # 阶段1: 改写为第三人称绝对化事件
            rewritten = await self._rewrite(text, job)

            # 阶段2: 写入向量存储
            if rewritten:
                embedding = self._get_embedding(rewritten)
                event_id = f"cognitive_{job_id}"
                group_id = job.get("group_id")
                user_id = job.get("user_id")
                metadata: dict[str, Any] = {
                    "timestamp": job.get("timestamp", time.time()),
                    "source_type": job.get("source_type", "chat"),
                }
                if group_id:
                    metadata["group_id"] = str(group_id)
                if user_id:
                    metadata["user_id"] = str(user_id)

                await self.vector_store.add_event(
                    event_id=event_id,
                    text=rewritten,
                    embedding=embedding,
                    metadata=metadata,
                )

            await self.job_queue.done(job)

        except Exception as e:
            logger.warning("[Historian] 任务 %s 失败: %s", job_id, e)
            if retry_count < self.max_retries:
                await self.job_queue.requeue(job)
            else:
                await self.job_queue.fail(job)

    async def _rewrite(self, text: str, job: dict[str, Any]) -> str:
        """将原始观察改写为第三人称绝对化事件

        例: "佳好像喜欢咖啡" → "佳喜欢喝咖啡。佳对咖啡有偏好。"
        """
        if self._call_llm is None:
            # 无 LLM 时直接返回原文本
            return text

        try:
            sender_id = job.get("sender_id")
            context = f"用户 {sender_id} " if sender_id else ""
            prompt = (
                f"请将以下观察改写为第三人称、绝对化的事实陈述。\n"
                f"只陈述确定的事实，去除推测性语言（好像/可能/也许）。\n"
                f"保持中文输出，直接给出结果不要解释。\n\n"
                f"观察: {context}{text}"
            )
            result = await self._call_llm(prompt)
            return result.strip() if result else text
        except Exception:
            return text

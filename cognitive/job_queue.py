"""认知记忆 - 文件持久化任务队列

借鉴 Undefined 的 job_queue.py 设计：
- 文件系统状态机：pending → processing → done/failed
- 原子移动保证并发安全 (os.replace)
- 自动 stale job 恢复
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


class JobQueue:
    """文件系统持久化任务队列

    四状态流转:
        pending/     → 待处理
        processing/  → 处理中 (原子移动进入)
        failed/      → 失败 (超出重试)
        done/        → 完成时删除
    """

    def __init__(
        self,
        base_dir: Path | str = "data/cognitive/queues",
        stale_timeout_seconds: float = 300.0,
        max_retries: int = 3,
        failed_max_age_days: int = 30,
        failed_max_files: int = 500,
        failed_cleanup_interval: int = 100,
    ) -> None:
        max_retries = max_retries or cfg.get("historian", {}).get("max_retries", 3)
        failed_max_age_days = failed_max_age_days or jq_cfg.get(
            "failed_max_age_days", 30
        )
        failed_max_files = failed_max_files or jq_cfg.get("failed_max_files", 500)
        failed_cleanup_interval = failed_cleanup_interval or jq_cfg.get(
            "failed_cleanup_interval", 100
        )
        self.base_dir = Path(base_dir)
        self.pending_dir = self.base_dir / "pending"
        self.processing_dir = self.base_dir / "processing"
        self.failed_dir = self.base_dir / "failed"
        self.done_dir = self.base_dir / "done"
        self.stale_timeout = stale_timeout_seconds
        self.max_retries = max_retries
        self.failed_max_age_days = failed_max_age_days
        self.failed_max_files = failed_max_files
        self.failed_cleanup_interval = failed_cleanup_interval
        self._failed_count = 0

        # 启动时清理残留 lock 文件
        self._cleanup_locks()

    @classmethod
    def from_config(cls) -> "JobQueue":
        from config.config_utils import get_cognitive_config

        cfg = get_cognitive_config()
        paths = cfg.get("paths", {})
        jq = cfg.get("job_queue", {})
        return cls(
            base_dir=paths.get("queues", "data/cognitive/queues"),
            stale_timeout_seconds=jq.get("stale_timeout_seconds", 300),
            max_retries=cfg.get("historian", {}).get("max_retries", 3),
            failed_max_age_days=jq.get("failed_max_age_days", 30),
            failed_max_files=jq.get("failed_max_files", 500),
            failed_cleanup_interval=jq.get("failed_cleanup_interval", 100),
        )

    def _cleanup_locks(self) -> None:
        for d in (self.processing_dir, self.pending_dir, self.failed_dir):
            if not d.exists():
                continue
            for lock_file in d.glob("*.lock"):
                try:
                    lock_file.unlink()
                except OSError:
                    pass

    async def enqueue(self, job_data: dict[str, Any]) -> str:
        """投递任务到 pending 队列"""
        self.pending_dir.mkdir(parents=True, exist_ok=True)
        job_id = job_data.get(
            "job_id",
            f"{job_data.get('request_id', 'unknown')}_{int(time.time() * 1000)}",
        )
        filepath = self.pending_dir / f"{job_id}.json"
        await asyncio.to_thread(self._write_job, filepath, job_data)
        logger.debug("[JobQueue] 入队: %s", job_id)
        return job_id

    def _write_job(self, filepath: Path, job_data: dict[str, Any]) -> None:
        tmp_path = filepath.with_suffix(".tmp")
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(job_data, f, ensure_ascii=False)
        os.replace(tmp_path, filepath)

    async def dequeue(self) -> dict[str, Any] | None:
        """从 pending 取出一个任务 (原子移动到 processing)"""
        self.processing_dir.mkdir(parents=True, exist_ok=True)
        return await asyncio.to_thread(self._dequeue_sync)

    def _dequeue_sync(self) -> dict[str, Any] | None:
        if not self.pending_dir.exists():
            return None
        files = sorted(self.pending_dir.glob("*.json"))
        if not files:
            return None
        for filepath in files:
            try:
                target = self.processing_dir / filepath.name
                os.replace(str(filepath), str(target))
                return json.loads(target.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
        return None

    async def requeue(self, job_data: dict[str, Any]) -> None:
        """任务重试：增加重试计数后移回 pending"""
        job_id = job_data.get("job_id", "unknown")
        retry_count = job_data.get("_retry_count", 0) + 1
        job_data["_retry_count"] = retry_count
        await asyncio.to_thread(self._requeue_sync, job_data, job_id)

    def _requeue_sync(self, job_data: dict[str, Any], job_id: str) -> None:
        source = self.processing_dir / f"{job_id}.json"
        if source.exists():
            self._write_job(source, job_data)
            os.replace(str(source), str(self.pending_dir / f"{job_id}.json"))

    async def fail(self, job_data: dict[str, Any]) -> None:
        """标记任务失败 (移动到 failed)"""
        job_id = job_data.get("job_id", "unknown")
        job_data["_failed_at"] = time.time()
        self.failed_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(self._fail_sync, job_data, job_id)
        self._failed_count += 1
        if self._failed_count % self.failed_cleanup_interval == 0:
            await self._cleanup_failed()

    def _fail_sync(self, job_data: dict[str, Any], job_id: str) -> None:
        source = self.processing_dir / f"{job_id}.json"
        if source.exists():
            self._write_job(source, job_data)
            target = self.failed_dir / f"{job_id}.json"
            try:
                os.replace(str(source), str(target))
            except OSError:
                pass

    async def done(self, job_data: dict[str, Any]) -> None:
        """标记任务完成 (删除文件)"""
        job_id = job_data.get("job_id", "unknown")
        await asyncio.to_thread(self._done_sync, job_id)

    def _done_sync(self, job_id: str) -> None:
        source = self.processing_dir / f"{job_id}.json"
        if source.exists():
            source.unlink(missing_ok=True)

    async def _cleanup_failed(self) -> None:
        """清理过期的 failed 任务"""
        cutoff = time.time() - self.failed_max_age_days * 86400
        if not self.failed_dir.exists():
            return
        files = sorted(self.failed_dir.glob("*.json"))
        if len(files) <= self.failed_max_files:
            return

        await asyncio.to_thread(self._cleanup_failed_sync, files, cutoff)

    def _cleanup_failed_sync(self, files: list[Path], cutoff: float) -> None:
        for f in files[: -self.failed_max_files]:
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
                failed_at = data.get("_failed_at", 0)
                if failed_at < cutoff:
                    f.unlink(missing_ok=True)
            except (json.JSONDecodeError, OSError):
                try:
                    f.unlink(missing_ok=True)
                except OSError:
                    pass

    async def recover_stale(self) -> int:
        """恢复卡在 processing 中的过期任务"""
        if not self.processing_dir.exists():
            return 0
        recovered = 0
        cutoff = time.time() - self.stale_timeout
        for f in list(self.processing_dir.glob("*.json")):
            try:
                if f.stat().st_mtime < cutoff:
                    os.replace(str(f), str(self.pending_dir / f.name))
                    recovered += 1
            except OSError:
                pass
        if recovered:
            logger.info("[JobQueue] 恢复 %s 个过期任务", recovered)
        return recovered

    async def pending_count(self) -> int:
        """pending 队列长度"""
        if not self.pending_dir.exists():
            return 0
        return len(list(self.pending_dir.glob("*.json")))

    async def processing_count(self) -> int:
        """processing 队列长度"""
        if not self.processing_dir.exists():
            return 0
        return len(list(self.processing_dir.glob("*.json")))

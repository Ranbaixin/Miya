"""
AP 记忆深度融合 v10.0 — AP MemoryStore ↔ MiyaMemoryCore 双向融合

弥娅 v10.0 重构：AP 的 StatePool 是唯一的"当前意识场"。
MiyaMemoryCore SQLite 作为持久化后端。
每次 Tick 结束时写入，每次启动时加载。

双向桥:
  StatePool (当前意识) ←→ MiyaMemoryCore (持久记忆)
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any

logger = logging.getLogger("miya.memory_fusion")


class APMemoryFusion:
    """
    AP 记忆融合层 —— StatePool 与 MiyaMemoryCore 的双向同步

    原则:
    - StatePool 是"当前意识"，每秒衰减
    - MiyaMemoryCore 是"长期记忆"，持久化存储
    - 每次 Tick 后，高能量 StatePool 项写入 MiyaMemoryCore
    - 每次启动时，MiyaMemoryCore 的热数据注入 StatePool
    """

    def __init__(self, ap_core=None):
        self._ap_core = ap_core
        self._engine = None
        self._core = None
        self._write_queue: list[dict[str, Any]] = []
        self._write_lock = threading.Lock()
        self._last_write_time = 0.0
        self._write_interval = 10.0  # 每 10 秒批量写一次
        self._energy_priority_divisor = 5.0
        self._auto_write_running = False

    async def initialize(self) -> APMemoryFusion:
        """初始化记忆融合"""
        try:
            from memory import get_memory_core

            self._core = await get_memory_core()
            logger.info("[记忆融合] MiyaMemoryCore 已连接")
        except Exception as e:
            logger.warning(f"[记忆融合] MiyaMemoryCore 连接失败: {e}")

        if self._ap_core and hasattr(self._ap_core, "_engine"):
            self._engine = self._ap_core._engine

        return self

    def load_to_state_pool(self, limit: int = 40) -> int:
        """启动时：从 MiyaMemoryCore 加载热记忆到 AP StatePool"""
        if not self._engine or not self._core:
            return 0

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        try:
            recent_memories = loop.run_until_complete(self._core.get_recent(limit=limit))
            items = []
            for mem in recent_memories:
                content = getattr(mem, "content", str(mem))
                if not content or len(content) < 3:
                    continue
                items.append(
                    {
                        "sa_label": f"miya_memory::{getattr(mem, 'memory_id', str(hash(content)))}",
                        "display_text": content[:50],
                        "family": "miya_memory",
                        "source_type": "long_term",
                        "real_energy": 1.2,
                        "anchor_meta": {
                            "full_content": content,
                            "tags": list(getattr(mem, "tags", []) or []),
                            "created_at": str(getattr(mem, "created_at", "")),
                        },
                    }
                )

            if items:
                self._engine._runtime.state_pool.apply_external_items(items, tick_index=0)
                logger.info(f"[记忆融合] {len(items)} 条持久记忆注入 StatePool")

            return len(items)
        except Exception as e:
            logger.warning(f"[记忆融合] 加载失败: {e}")
            return 0

    def sync_after_tick(self, tick_index: int, focus_labels: list[str]) -> int:
        """Tick 后：将高能量 StatePool 项同步到 MiyaMemoryCore"""
        if not self._engine or not self._core:
            return 0

        try:
            pool = self._engine._runtime.state_pool
            candidates = []
            threshold = 1.5

            for label, entry in pool._entries.items():
                if entry.real_energy >= threshold and "miya_memory" not in str(label):
                    if str(label).startswith("miya_") or "context::" in str(label):
                        candidates.append(
                            {
                                "label": str(label),
                                "display_text": entry.display_text,
                                "energy": entry.real_energy,
                                "family": entry.family,
                                "meta": entry.anchor_meta,
                            }
                        )

            # 批量写入
            with self._write_lock:
                for item in candidates[:10]:  # 每 tick 最多 10 条
                    self._write_queue.append(item)

            # 定期批量持久化
            now = time.time()
            if now - self._last_write_time > self._write_interval:
                return self._flush_writes()

            return 0
        except Exception as e:
            logger.debug(f"[记忆融合] 同步失败: {e}")
            return 0

    def _flush_writes(self) -> int:
        """批量写入 MiyaMemoryCore"""
        if not self._write_queue:
            return 0

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()

        count = 0
        with self._write_lock:
            batch = list(self._write_queue)
            self._write_queue = []

        for item in batch:
            try:
                from memory import store_important

                tags = list(item.get("meta", {}).get("tags", []) or [])
                tags.append("ap_sync")
                tags.append(item.get("family", "unknown"))

                loop.run_until_complete(
                    store_important(
                        content=f"{item['display_text']}",
                        user_id="miya_ap",
                        tags=tags,
                        priority=min(item["energy"] / self._energy_priority_divisor, 1.0),
                        metadata={
                            "ap_label": item["label"],
                            "ap_family": item["family"],
                            "ap_energy": item["energy"],
                        },
                    )
                )
                count += 1
            except Exception as e:
                logger.debug(f"[记忆融合] 单条写入失败: {e}")

        self._last_write_time = time.time()
        if count > 0:
            logger.debug(f"[记忆融合] {count} 条记忆持久化")

        return count


# 全局单例
_fusion_instance: APMemoryFusion | None = None


async def get_memory_fusion(ap_core=None) -> APMemoryFusion:
    global _fusion_instance
    if _fusion_instance is None:
        _fusion_instance = APMemoryFusion(ap_core=ap_core)
        await _fusion_instance.initialize()
    return _fusion_instance

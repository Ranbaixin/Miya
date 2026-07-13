"""
弥娅记忆回填器 v10.1

从 SQLite / JSON 备份中批量加载历史记忆到 AP StatePool。
分批注入，避免阻塞启动。

策略:
1. 启动时: 加载最近 100 条对话 + 50 条高质量记忆
2. 心跳时: 每 30 秒增量注入 10 条旧记忆
3. 新对话自动保存到 cognitive_memories.json
"""

from __future__ import annotations

import json
import logging
import sqlite3
import threading
from collections import deque
from pathlib import Path
from typing import Any

logger = logging.getLogger("miya.memory_backfill")


class MemoryBackfill:
    """弥娅记忆回填器"""

    def __init__(self, ap_engine=None):
        from pathlib import Path as _Path

        try:
            from config.memory_config import get_storage_dir

            data_dir = get_storage_dir()
        except Exception:
            data_dir = "data/memory"

        self._engine = ap_engine
        self._db_path = _Path(data_dir) / "miya_memory.db"
        self._cognitive_path = _Path(data_dir) / "cognitive_memories.json"
        self._backup_dir = _Path(data_dir) / "backups"

        self._loaded_ids: set[str] = set()
        self._pending: deque[dict[str, Any]] = deque()
        self._backfill_thread: threading.Thread | None = None
        self._running = False

    def load_recent_conversations(self, limit: int = 100) -> int:
        """从 SQLite 加载最近对话"""
        if not self._engine or not self._db_path.exists():
            return 0

        try:
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            cur.execute(
                "SELECT id, content, level, priority, tags, user_id, created_at "
                "FROM memories WHERE level IN ('dialogue', 'short_term', 'long_term') "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            )
            rows = cur.fetchall()
            conn.close()

            items = []
            for r in rows:
                mid = r["id"]
                if mid in self._loaded_ids:
                    continue
                self._loaded_ids.add(mid)

                content = r["content"] or ""
                preview = content[:60] if content else ""
                tags = json.loads(r["tags"]) if r["tags"] else []
                family = "miya_memory"
                if "emotion_context" in tags or "情绪" in content[:5]:
                    family = "miya_emotion"
                elif "cognition" in tags or "思考" in content[:5]:
                    family = "cognitive_memory"

                items.append(
                    {
                        "sa_label": "miya_memory::" + (mid or str(hash(content))),
                        "display_text": preview,
                        "family": family,
                        "source_type": "sql_backfill",
                        "real_energy": 0.6 + float(r["priority"] or 0.3) * 0.4,
                        "anchor_meta": {
                            "memory_id": mid,
                            "full_content": content,
                            "tags": tags,
                            "user_id": r["user_id"],
                            "created_at": r["created_at"],
                        },
                    }
                )

            if items:
                self._engine._runtime.state_pool.apply_external_items(items, tick_index=0)
                logger.info("[回填] " + str(len(items)) + " 条对话记忆注入 StatePool")

            return len(items)
        except Exception as e:
            logger.warning("[回填] SQLite 加载失败: " + str(e))
            return 0

    def load_cognitive_memories(self, limit: int = 50) -> int:
        """从 cognitive_memories.json 加载认知记忆到 StatePool"""
        if not self._engine or not self._cognitive_path.exists():
            return 0

        try:
            with open(self._cognitive_path, "r", encoding="utf-8") as f:
                memories = json.load(f)[-limit:]

            items = []
            for m in memories:
                inner = m.get("inner_thought", "")
                attribution = m.get("attribution", "")
                reflection = m.get("reflection", "")
                emotions = m.get("emotions", {})

                if inner:
                    items.append(
                        {
                            "sa_label": "cognitive::inner::" + m.get("id", str(hash(inner))),
                            "display_text": inner[:50],
                            "family": "cognitive_memory",
                            "source_type": "inner_thought",
                            "real_energy": 1.0,
                            "anchor_meta": {"emotions": emotions, "reflection": reflection},
                        }
                    )
                if attribution:
                    items.append(
                        {
                            "sa_label": "cognitive::attr::" + m.get("id", str(hash(attribution))),
                            "display_text": attribution[:50],
                            "family": "cognitive_memory",
                            "source_type": "attribution",
                            "real_energy": 0.8,
                        }
                    )
                if reflection:
                    items.append(
                        {
                            "sa_label": "cognitive::refl::" + m.get("id", str(hash(reflection))),
                            "display_text": reflection[:50],
                            "family": "cognitive_memory",
                            "source_type": "reflection",
                            "real_energy": 0.9,
                        }
                    )

            if items:
                self._engine._runtime.state_pool.apply_external_items(items, tick_index=0)
                logger.info("[回填] " + str(len(items)) + " 条认知记忆注入 StatePool")

            return len(items)
        except Exception as e:
            logger.warning("[回填] 认知记忆加载失败: " + str(e))
            return 0

    def start_incremental(self, interval: float = 30.0, batch: int = 10) -> None:
        """启动增量回填线程 — 持续将旧记忆分批注入"""
        if self._running:
            return
        self._running = True

        def _loop():
            while self._running:
                try:
                    if self._engine:
                        count = self._inject_one_batch(batch)
                        if count > 0:
                            logger.debug("[回填] 增量 " + str(count) + " 条")
                except Exception:
                    pass
                threading.Event().wait(interval)

        self._backfill_thread = threading.Thread(target=_loop, daemon=True)
        self._backfill_thread.start()
        logger.info("[回填] 增量注入已启动 (每 " + str(interval) + "s, " + str(batch) + " 条)")

    def stop(self) -> None:
        self._running = False

    def _inject_one_batch(self, batch: int) -> int:
        if not self._db_path.exists():
            return 0
        try:
            conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
            conn.row_factory = sqlite3.Row
            cur = conn.cursor()
            if self._loaded_ids:
                placeholders = ",".join("?" * min(len(self._loaded_ids), 500))
                query = (
                    "SELECT id, content, level, priority, tags, user_id, created_at "
                    f"FROM memories WHERE id NOT IN ({placeholders}) "
                    "ORDER BY priority DESC, created_at DESC LIMIT ?"
                )
                params = list(self._loaded_ids)[:500] + [batch]
            else:
                query = (
                    "SELECT id, content, level, priority, tags, user_id, created_at "
                    "FROM memories ORDER BY priority DESC, created_at DESC LIMIT ?"
                )
                params = [batch]
            cur.execute(query, params)
            rows = cur.fetchall()
            conn.close()

            items = []
            for r in rows[:batch]:
                mid = r["id"]
                self._loaded_ids.add(mid)
                content = r["content"] or ""
                items.append(
                    {
                        "sa_label": "miya_memory::" + mid,
                        "display_text": content[:50],
                        "family": "miya_memory",
                        "source_type": "incremental_backfill",
                        "real_energy": 0.5,
                        "anchor_meta": {"memory_id": mid, "full_content": content},
                    }
                )

            if items:
                self._engine._runtime.state_pool.apply_external_items(
                    items, tick_index=self._engine._current_soul.tick_index if self._engine._current_soul else 0
                )

            return len(items)
        except Exception:
            return 0

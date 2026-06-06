"""
弥娅记忆桥接 — SQLite 直读，同步注入 AP 状态池 + LLM 上下文
"""

from __future__ import annotations

import logging
import sqlite3
from pathlib import Path

logger = logging.getLogger("miya_psyarch.memory")

_DB_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "memory" / "miya_memory.db"


def _connect():
    return sqlite3.connect(str(_DB_PATH))


class MiyaMemoryBridge:
    def __init__(self):
        self._recent: list[dict] = []
        self._initialized = False

    def warmup(self, limit: int = 30) -> None:
        try:
            conn = _connect()
            rows = conn.execute(
                "SELECT role, content, created_at FROM memories "
                "WHERE level='dialogue' AND content IS NOT NULL "
                "ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            conn.close()
            self._recent = [{"role": r[0] or "", "content": r[1], "created_at": r[2]} for r in rows if r[1]]
            self._recent.reverse()
            self._initialized = True
            logger.info(f"memory warmup: {len(self._recent)} items")
        except Exception as e:
            logger.warning(f"memory warmup failed: {e}")

    def search(self, query: str, limit: int = 8) -> list[dict]:
        if not query or len(query) < 2:
            return []
        if not self._initialized:
            self.warmup()
        try:
            conn = _connect()
            rows = conn.execute(
                "SELECT role, content, created_at FROM memories "
                "WHERE content LIKE ? AND level='dialogue' "
                "ORDER BY created_at DESC LIMIT ?",
                (f"%{query}%", limit),
            ).fetchall()
            conn.close()
            return [{"role": r[0] or "", "content": r[1], "created_at": r[2]} for r in rows if r[1]]
        except Exception as e:
            logger.debug(f"memory search failed: {e}")
            return []

    def as_state_items(self, memories: list[dict], base_energy: float = 0.6) -> list[dict]:
        items = []
        for m in memories:
            content = m.get("content", "")
            if not content:
                continue
            role = m.get("role", "")
            items.append(
                {
                    "sa_label": f"memory::{role}::{content[:30]}",
                    "display_text": f"[记忆] {content[:40]}",
                    "source_type": "memory_recall",
                    "family": "miya_memory",
                    "real_energy": base_energy,
                    "anchor_meta": {
                        "channel": "memory",
                        "role": role,
                        "created_at": m.get("created_at", ""),
                        "full_content": content,
                    },
                }
            )
        return items

    def context_text(self, memories: list[dict]) -> str:
        if not memories:
            return ""
        lines = ["相关记忆:"]
        for m in memories[:6]:
            role = "佳" if m.get("role") in ("user", "") else "弥娅"
            ts = str(m.get("created_at", ""))[:16]
            lines.append(f"  [{ts}] {role}: {m.get('content', '')[:80]}")
        return "\n".join(lines)

    def recent_context_text(self) -> str:
        return self.context_text(self._recent)


_bridge: MiyaMemoryBridge | None = None


def get_memory_bridge() -> MiyaMemoryBridge:
    global _bridge
    if _bridge is None:
        _bridge = MiyaMemoryBridge()
    return _bridge

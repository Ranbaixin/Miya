"""
弥娅记忆桥接 — SQLite 直读 + Jieba 分词搜索，同步注入 AP 状态池 + LLM 上下文
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

    def warmup(self, limit: int = 100) -> None:
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
        """FTS5 分词搜索——利用全文索引替代 LIKE 全表扫描"""
        if not query or len(query) < 2:
            return []
        if not self._initialized:
            self.warmup()

        try:
            tokens = self._tokenize(query)
            if not tokens:
                return []

            conn = _connect()
            results: dict[int, dict] = {}

            for token in tokens[:5]:
                if len(token) < 2:
                    continue
                fts_query = self._build_fts_query(token)
                try:
                    rows = conn.execute(
                        "SELECT memories.rowid, role, content, created_at FROM memories "
                        "JOIN memories_fts ON memories.rowid = memories_fts.rowid "
                        "WHERE memories_fts MATCH ? AND level='dialogue' "
                        "ORDER BY created_at DESC LIMIT ?",
                        (fts_query, limit * 2),
                    ).fetchall()
                except Exception:
                    rows = conn.execute(
                        "SELECT rowid, role, content, created_at FROM memories "
                        "WHERE content LIKE ? AND level='dialogue' "
                        "ORDER BY created_at DESC LIMIT ?",
                        (f"%{token}%", limit * 2),
                    ).fetchall()
                for r in rows:
                    rowid = r[0]
                    if rowid not in results:
                        results[rowid] = {"role": r[1] or "", "content": r[2], "created_at": r[3], "score": 0}
                    results[rowid]["score"] += 1

            conn.close()

            ranked = sorted(
                results.values(),
                key=lambda x: (
                    -x["score"],
                    x.get("created_at", ""),
                ),
            )[:limit]
            return [{"role": m["role"], "content": m["content"], "created_at": m.get("created_at", "")} for m in ranked]
        except Exception as e:
            logger.debug(f"memory search failed: {e}")
            return []

    @staticmethod
    def _build_fts_query(token: str) -> str:
        escaped = token.replace('"', '""')
        return f'"{escaped}"'

    def _tokenize(self, text: str) -> list[str]:
        try:
            import jieba

            return [w for w in jieba.lcut(text) if len(w.strip()) >= 1]
        except Exception:
            return text.split()

    def search_and_inject(self, query: str, state_pool, tick_index: int, limit: int = 12) -> int:
        """搜索并立即注入 AP 状态池——让 Bn/Cn 能自然召回深层记忆"""
        memories = self.search(query, limit=limit)
        if not memories:
            return 0

        items = []
        for i, m in enumerate(memories):
            content = m.get("content", "")
            if not content or len(content) < 3:
                continue
            items.append(
                {
                    "sa_label": f"memory_recall::{content[:25]}",
                    "display_text": f"[记忆] {content[:40]}",
                    "family": "memory_recall",
                    "source_type": "deep_search",
                    "real_energy": 0.8 + i * 0.05,
                    "anchor_meta": {
                        "role": m.get("role", ""),
                        "created_at": m.get("created_at", ""),
                        "full_content": content,
                    },
                }
            )

        if items:
            state_pool.apply_external_items(items, tick_index=tick_index)
        return len(items)

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

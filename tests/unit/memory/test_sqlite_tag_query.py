"""SQLite 后端多标签 any_tag 语义测试（2026-08 验收补充）。

覆盖：
- any_tag=True：多标签 OR 语义（此前错误地按 AND 处理，导致稳定画像白名单查不到）
- any_tag=False：保持 AND 语义
"""

import pytest

from memory.core import MemoryItem, MemoryQuery
from memory.sqlite_backend import SQLiteBackend


@pytest.fixture
def backend(tmp_path, monkeypatch):
    cfg = {
        "enabled": True,
        "db_path": str(tmp_path / "test.db"),
        "table": {"name": "memories", "fts_enabled": False},
        "query": {
            "default_order": "priority DESC, created_at DESC",
            "like_pattern_prefix": "%",
            "like_pattern_suffix": "%",
        },
        "indexes": [],
        "defaults": {},
    }
    monkeypatch.setattr("memory.sqlite_backend._load_sqlite_config", lambda: cfg)
    b = SQLiteBackend(str(tmp_path / "test.db"))
    assert b.enabled
    yield b
    b._conn.close()


@pytest.mark.asyncio
async def test_any_tag_or_semantics(backend):
    m1 = MemoryItem(id="a", content="喜欢读书", tags=["喜好"], user_id="u1", created_at="2026-01-01T00:00:00")
    m2 = MemoryItem(id="b", content="我是程序员", tags=["信息"], user_id="u1", created_at="2026-01-01T00:00:00")
    m3 = MemoryItem(id="c", content="无标签", tags=[], user_id="u1", created_at="2026-01-01T00:00:00")
    for m in (m1, m2, m3):
        await backend.save(m)

    q = MemoryQuery(tags=["喜好", "信息"], any_tag=True, limit=10)
    rows = await backend.query(q)
    ids = {r.id for r in rows}
    assert "a" in ids and "b" in ids
    assert "c" not in ids


@pytest.mark.asyncio
async def test_all_tags_and_semantics(backend):
    m1 = MemoryItem(id="a", content="喜欢读书", tags=["喜好", "信息"], user_id="u1", created_at="2026-01-01T00:00:00")
    m2 = MemoryItem(id="b", content="我是程序员", tags=["信息"], user_id="u1", created_at="2026-01-01T00:00:00")
    for m in (m1, m2):
        await backend.save(m)

    q = MemoryQuery(tags=["喜好", "信息"], any_tag=False, limit=10)
    rows = await backend.query(q)
    ids = {r.id for r in rows}
    assert ids == {"a"}  # 只有同时带两个标签的条目

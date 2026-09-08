"""记忆双后端一致性测试（2026-08 验收）。

验证 update/delete/归档路径都同步 SQLite 镜像。
使用内存 FakeSqlite 记录调用，不依赖真实数据库。
"""

import shutil
import tempfile

import pytest

from memory.core import MemoryLevel, MiyaMemoryCore


class FakeSqlite:
    """记录 save/delete 调用的 SQLite 镜像替身。"""

    def __init__(self):
        self.saved_ids = []
        self.deleted_ids = []

    async def save(self, memory):
        self.saved_ids.append(memory.id)

    async def delete(self, memory_id):
        self.deleted_ids.append(memory_id)


@pytest.fixture
async def core():
    tmp = tempfile.mkdtemp()
    c = MiyaMemoryCore(tmp, enable_backup=False)
    await c.initialize(lazy_load=True)
    c.sqlite_backend = FakeSqlite()
    yield c
    try:
        await c.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_store_writes_both(core):
    mid = await core.store("hello", user_id="u1")
    assert mid in core.sqlite_backend.saved_ids


async def test_update_writes_both(core):
    mid = await core.store("hello", user_id="u1")
    core.sqlite_backend.saved_ids.clear()
    ok = await core.update(mid, content="hello 2", tags=["x"])
    assert ok
    assert mid in core.sqlite_backend.saved_ids
    # 读回确认字段更新
    m = await core.get_by_id(mid)
    assert m and m.content == "hello 2" and "x" in m.tags


async def test_delete_writes_both(core):
    mid = await core.store("hello", user_id="u1")
    ok = await core.delete(mid)
    assert ok
    assert mid in core.sqlite_backend.deleted_ids
    assert await core.get_by_id(mid) is None


async def test_delete_batch_writes_both(core):
    ids = [await core.store(f"m{i}", user_id="u1") for i in range(3)]
    assert await core.delete_batch(ids[:2]) == 2
    for i in ids[:2]:
        assert i in core.sqlite_backend.deleted_ids


async def test_archive_old_syncs_sqlite(core):
    """归档路径（archive_old）也同步 SQLite。

    2026-09：archive_old 改为磁盘索引预筛，伪造时间需同时更新
    索引条目与记忆本体（真实数据流中两者一致）。
    """
    mid = await core.store(
        "old dialogue", user_id="u1", level=MemoryLevel.DIALOGUE
    )
    m = await core.get_by_id(mid)
    assert m is not None
    # 伪造 100 天前的创建时间（索引 + 记忆本体）
    from datetime import datetime, timedelta

    old_ts = (datetime.now() - timedelta(days=100)).isoformat()
    m.created_at = old_ts
    core.backend._index[mid]["created_at"] = old_ts
    core.sqlite_backend.saved_ids.clear()
    n = await core.archive_old(days=90)
    assert n >= 1
    assert mid in core.sqlite_backend.saved_ids

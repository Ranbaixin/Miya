"""记忆核心读写测试 —— P9 异常吞噬治理的安全网（P8 Step2）。

覆盖 MiyaMemoryCore 的 store / retrieve / update / delete / 归档 / 衰减 6 个核心操作。
"""

import asyncio

from memory.core import MemoryLevel


async def test_store_and_retrieve(memory_core):
    """写入一条记忆 → 检索 → 内容一致"""
    mid = await memory_core.store("明天早上七点叫我起床", priority=0.5, tags=["提醒"])
    assert mid, "store 应返回 memory_id"

    results = await memory_core.retrieve("叫我起床", limit=5)
    assert len(results) >= 1
    assert results[0].id == mid
    assert results[0].content == "明天早上七点叫我起床"


async def test_update_preserves_id(memory_core):
    """更新记忆 → ID 不变、内容变"""
    mid = await memory_core.store("原始内容")
    m0 = await memory_core.get_by_id(mid)
    assert m0 is not None

    ok = await memory_core.update(mid, content="更新后内容")
    assert ok

    m1 = await memory_core.get_by_id(mid)
    assert m1 is not None
    assert m1.id == mid, "更新后 ID 必须保持不变"
    assert m1.content == "更新后内容"


async def test_delete_removes_from_index(memory_core):
    """删除 → get_by_id 返回空"""
    mid = await memory_core.store("要删除的记忆")
    assert await memory_core.get_by_id(mid) is not None

    ok = await memory_core.delete(mid)
    assert ok
    assert await memory_core.get_by_id(mid) is None


async def test_archive_flags(memory_core):
    """归档 → 普通检索不返回"""
    mid = await memory_core.store("归档测试记忆", priority=0.6)
    ok = await memory_core.update(mid, is_archived=True)
    assert ok

    results = await memory_core.retrieve("归档测试记忆", limit=10)
    assert not any(m.id == mid for m in results), "归档记忆不应出现在普通检索结果中"


async def test_decay_updates_priority(memory_core):
    """衰减 → 低优先级长期记忆优先级降低"""
    mid = await memory_core.store(
        "低优先级长期记忆", priority=0.15, level=MemoryLevel.LONG_TERM
    )
    m0 = await memory_core.get_by_id(mid)
    assert m0 is not None
    original_priority = m0.priority  # 快照（get_by_id 返回缓存引用，decay 会就地修改）
    m0.update_access()  # store 不自动设置 last_accessed，decay 依赖它判断"最后访问时间"

    count = await memory_core.decay_low_priority_memories(days=0, threshold=0.3)
    assert count >= 1, "应有至少一条记忆被衰减"

    m1 = await memory_core.get_by_id(mid)
    assert m1 is not None
    assert m1.priority < original_priority, "衰减后优先级应降低"


async def test_concurrent_writes_no_corruption(memory_core):
    """10 并发写入 → 索引完整 → 所有 id 可读出"""
    ids = await asyncio.gather(
        *(memory_core.store(f"并发写入 {i}", priority=0.5, user_id="u") for i in range(10))
    )
    assert len(ids) == 10
    for mid in ids:
        m = await memory_core.get_by_id(mid)
        assert m is not None, f"并发写入的 {mid} 应可读出"

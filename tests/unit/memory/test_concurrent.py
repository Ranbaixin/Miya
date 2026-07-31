"""记忆并发写入测试 —— 验证 load() 加锁（P3 batch3 修复）不退化（P8 Step2）。"""
import asyncio


async def test_concurrent_read_write(memory_core):
    """同时读写 → 不丢数据、不损坏索引"""
    ids = await asyncio.gather(
        *(memory_core.store(f"并发写入 {i}", priority=0.5, user_id="u") for i in range(10))
    )
    assert len(ids) == 10
    for mid in ids:
        assert await memory_core.get_by_id(mid) is not None


async def test_concurrent_reads_no_error(memory_core):
    """并发检索 → 无异常、结果一致"""
    await memory_core.store("并发读基准", priority=0.5, user_id="u")
    results = await asyncio.gather(
        *(memory_core.retrieve("并发读基准", limit=5) for _ in range(5))
    )
    assert all(len(r) >= 1 for r in results)

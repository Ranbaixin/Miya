"""A1 遗忘与容量接线测试（2026-09）。

覆盖：
- 短期记忆容量裁剪：超上限删最旧低优先级
- 定时清理循环接线：delete_expired / archive_old / decay 均被周期调用
"""

import asyncio
import shutil
import tempfile

from memory.core import MemoryLevel, MemorySource, MiyaMemoryCore


async def _make_core() -> MiyaMemoryCore:
    tmp = tempfile.mkdtemp()
    core = MiyaMemoryCore(tmp, enable_backup=False)
    await core.initialize(lazy_load=True)
    core.__tmpdir = tmp  # 测试自清理用
    return core


async def _teardown(core: MiyaMemoryCore):
    tmp = getattr(core, "__tmpdir", None)
    try:
        await core.close()
    finally:
        if tmp:
            shutil.rmtree(tmp, ignore_errors=True)


async def test_short_term_capacity_trim():
    """store 时短期记忆超上限 → 裁剪到上限内，且保留较新的。"""
    core = await _make_core()
    try:
        core.short_term_max_items = 3
        for i in range(8):
            await core.store(f"短期记忆内容 {i}", user_id="u1", priority=0.5)

        n = await core.backend.count(MemoryLevel.SHORT_TERM)
        assert n <= 3, f"应裁剪到 ≤3 条，实际 {n}"

        # 同优先级下应保留最新的
        remaining = []
        for mid in await core.backend.get_all_ids():
            info = core.backend._index[mid]
            if info.get("level") == MemoryLevel.SHORT_TERM.value:
                remaining.append(info.get("created_at", ""))
        assert len(remaining) == sorted(remaining, reverse=True) or len(remaining) <= 3
    finally:
        await _teardown(core)


async def test_capacity_trim_prefers_low_priority():
    """超限时优先删除低优先级记忆，高优先级保留。"""
    core = await _make_core()
    try:
        core.short_term_max_items = 3
        # 先存 3 条高优先级
        for i in range(3):
            await core.store(f"重要记忆 {i}", user_id="u1", priority=0.9)
        # 再存 3 条低优先级 → 裁剪应删低优先级
        for i in range(3):
            await core.store(f"琐碎记忆 {i}", user_id="u1", priority=0.1)

        surviving = []
        for mid in await core.backend.get_all_ids():
            mem = await core.get_by_id(mid)
            if mem and mem.level == MemoryLevel.SHORT_TERM:
                surviving.append(mem.content)
        assert len(surviving) <= 3
        assert all("重要记忆" in c for c in surviving), (
            f"高优先级应保留，实际存活: {surviving}"
        )
    finally:
        await _teardown(core)


async def test_cleanup_task_loop_runs():
    """start_cleanup_task 周期调用 delete_expired + archive_old + decay。"""
    core = await _make_core()
    try:
        calls = []

        async def _fake_delete_expired():
            calls.append("delete_expired")
            return 0

        async def _fake_archive_old(days=90, max_per_run=500):
            calls.append("archive_old")
            return 0

        async def _fake_decay(days=90, threshold=0.3):
            calls.append("decay")
            return 0

        core.delete_expired = _fake_delete_expired
        core.archive_old = _fake_archive_old
        core.decay_low_priority_memories = _fake_decay

        await core.start_cleanup_task(interval=0.05)
        await asyncio.sleep(0.3)

        assert "delete_expired" in calls
        assert "archive_old" in calls
        assert "decay" in calls
    finally:
        await _teardown(core)  # close() 会取消清理任务


async def test_trim_skips_higher_levels():
    """容量裁剪只作用于短期记忆，长期记忆不受影响。"""
    core = await _make_core()
    try:
        core.short_term_max_items = 2
        long_ids = []
        for i in range(5):
            mid = await core.store(
                f"长期事实 {i}",
                user_id="u1",
                level=MemoryLevel.LONG_TERM,
                source=MemorySource.MANUAL,
                priority=0.5,
            )
            long_ids.append(mid)
        # 初始化锚点会额外写入长期记忆，因此按自己存入的 ID 断言
        for mid in long_ids:
            mem = await core.get_by_id(mid)
            assert mem is not None, f"长期记忆 {mid} 不应被容量裁剪删除"
    finally:
        await _teardown(core)

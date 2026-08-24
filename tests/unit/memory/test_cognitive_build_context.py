"""CognitiveEngine.build_context 预取条目测试（2026-08 验收补充）。

覆盖：
- 传入 memories → 跳过内部 retrieve（避免二次检索）
- 未传 memories → 走内部 retrieve（向后兼容）
"""

import pytest

from memory.cognitive_engine import CognitiveEngine
from memory.core import MemoryItem


def _engine(retrieve_impl):
    eng = CognitiveEngine(memory_core=None)

    async def _noop():
        return None

    eng._ensure_memory_core_initialized = _noop
    eng.retrieve = retrieve_impl
    return eng


async def _raise_retrieve(*args, **kwargs):
    raise AssertionError("memories 已传入时不应再调用 retrieve")


async def _fake_retrieve(*args, **kwargs):
    return [MemoryItem(id="m1", content="来自检索的记忆")]


@pytest.mark.asyncio
async def test_build_context_uses_provided_memories():
    eng = _engine(_raise_retrieve)
    item = MemoryItem(id="m1", content="预取条目", created_at="2026-08-01T10:00:00")
    ctx = await eng.build_context("你好", memories=[item])
    assert "预取条目" in ctx


@pytest.mark.asyncio
async def test_build_context_without_memories_retrieves():
    eng = _engine(_fake_retrieve)
    ctx = await eng.build_context("你好")
    assert "来自检索的记忆" in ctx


@pytest.mark.asyncio
async def test_build_context_empty_memories_returns_empty():
    eng = _engine(_raise_retrieve)
    assert await eng.build_context("你好", memories=[]) == ""

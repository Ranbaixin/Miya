"""A4 联想式召回测试（2026-09）。

覆盖：
- memory_links 一跳关联：top 记忆带出关联记忆并标注 recalled_via
- build_context 渲染"（由「…」想起）"
- 无链接时零影响
"""

import shutil
import tempfile

import pytest

from memory.cognitive_engine import CognitiveEngine
from memory.core import MemoryItem, MemoryLevel, MiyaMemoryCore
from memory.memory_enhancer import MemoryEnhancer, MemoryLink


@pytest.fixture
async def env():
    """临时目录的记忆核心 + 认知引擎 + 已初始化的增强器。"""
    tmp = tempfile.mkdtemp()
    core = MiyaMemoryCore(tmp, enable_backup=False)
    await core.initialize(lazy_load=True)
    engine = CognitiveEngine(memory_core=core)
    engine._enhancer = core._enhancer or MemoryEnhancer(tmp)
    yield core, engine
    try:
        await core.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_fetch_associations_brings_linked_memory(env):
    """有一跳链接时带出关联记忆，且标注来源。"""
    core, engine = env
    a_id = await core.store(
        "我们一起讨论了期末考试复习计划", user_id="u1", level=MemoryLevel.LONG_TERM
    )
    b_id = await core.store(
        "考试安排在下周一早上", user_id="u1", level=MemoryLevel.LONG_TERM
    )
    a_item = await core.get_by_id(a_id)

    engine._enhancer._links[a_id] = [
        MemoryLink(source_id=a_id, target_id=b_id, link_type="entity", strength=0.9)
    ]

    associated = await engine._fetch_associations([a_item], [], [], exclude_ids={a_id})
    assert len(associated) == 1
    mem, score = associated[0]
    assert mem.id == b_id
    assert score > 0
    assert mem.metadata.get("recalled_via") == "我们一起讨论了期末考试复习计划"


async def test_fetch_associations_no_links_zero_impact(env):
    """无链接数据时返回空列表（对检索零影响）。"""
    core, engine = env
    a_id = await core.store("随便的一条记忆", user_id="u1", level=MemoryLevel.LONG_TERM)
    a_item = await core.get_by_id(a_id)
    associated = await engine._fetch_associations([a_item], [], [], exclude_ids={a_id})
    assert associated == []


async def test_fetch_associations_excludes_already_selected(env):
    """关联目标已在结果集中时不重复带出。"""
    core, engine = env
    a_id = await core.store("记忆A", user_id="u1", level=MemoryLevel.LONG_TERM)
    a_item = await core.get_by_id(a_id)
    engine._enhancer._links[a_id] = [
        MemoryLink(source_id=a_id, target_id=a_id, link_type="semantic", strength=0.9)
    ]
    associated = await engine._fetch_associations([a_item], [], [], exclude_ids={a_id})
    assert associated == []


async def test_build_context_renders_association_annotation(env):
    """build_context 渲染联想来源标注。"""
    core, engine = env
    b = MemoryItem(id="b1", content="关联到的记忆内容")
    b.metadata["recalled_via"] = "源头记忆"
    ctx = await engine.build_context("你还好吗", memories=[b])
    assert "（由「源头记忆」想起）" in ctx
    assert "关联到的记忆内容" in ctx

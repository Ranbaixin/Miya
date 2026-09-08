"""A3 情绪显著性加权测试（2026-09）。

覆盖：
- 检索侧：emotional_tone / significance 加分
- store 侧：情绪强度 > 0.7 的记忆 priority+0.2 并写入 emotion 元数据
"""

import shutil
import tempfile
from datetime import datetime, timedelta

import pytest

from memory.cognitive_engine import CognitiveEngine
from memory.core import MemoryItem, MemoryLevel, MiyaMemoryCore


@pytest.fixture
async def core():
    tmp = tempfile.mkdtemp()
    c = MiyaMemoryCore(tmp, enable_backup=False)
    await c.initialize(lazy_load=True)
    yield c
    try:
        await c.close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_emotional_tone_boosts_relevance():
    """同龄同优先级：带情感基调的记忆得分更高。"""
    eng = CognitiveEngine(memory_core=None)
    ts = (datetime.now() - timedelta(days=5)).isoformat()
    plain = MemoryItem(id="a", content="那天的事情", created_at=ts, priority=0.5)
    emotional = MemoryItem(
        id="b", content="那天的事情", created_at=ts, priority=0.5, emotional_tone="愉快"
    )
    r_plain = await eng._calculate_relevance(plain, [], [])
    r_emotional = await eng._calculate_relevance(emotional, [], [])
    assert r_emotional > r_plain


async def test_high_significance_boosts_relevance():
    """significance ≥ 0.7 的记忆得分更高。"""
    eng = CognitiveEngine(memory_core=None)
    ts = (datetime.now() - timedelta(days=5)).isoformat()
    normal = MemoryItem(id="a", content="普通的事情", created_at=ts, priority=0.5, significance=0.4)
    big = MemoryItem(id="b", content="重要的事情", created_at=ts, priority=0.5, significance=0.9)
    r_normal = await eng._calculate_relevance(normal, [], [])
    r_big = await eng._calculate_relevance(big, [], [])
    assert r_big > r_normal


async def test_store_emotion_enhancement(core):
    """store 侧：高情绪强度内容 priority+0.2 并记录 emotion 元数据。"""
    mid = await core.store(
        "今天真的很开心，太高兴了，哈哈笑个不停，太幸福了",
        user_id="u1",
        level=MemoryLevel.LONG_TERM,
        priority=0.5,
    )
    mem = await core.get_by_id(mid)
    assert mem is not None
    assert mem.priority == pytest.approx(0.7, abs=0.01), (
        f"情绪强化应 +0.2，实际 priority={mem.priority}"
    )
    assert "emotion" in mem.metadata, "应写入 emotion 元数据"


async def test_store_neutral_not_enhanced(core):
    """中性内容不受情绪强化影响。"""
    mid = await core.store(
        "明天下午三点开会讨论项目排期",
        user_id="u1",
        level=MemoryLevel.LONG_TERM,
        priority=0.5,
    )
    mem = await core.get_by_id(mid)
    assert mem is not None
    assert mem.priority == pytest.approx(0.5, abs=0.001)
    assert "emotion" not in mem.metadata

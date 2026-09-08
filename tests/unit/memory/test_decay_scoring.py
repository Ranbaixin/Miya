"""A2 艾宾浩斯衰减 + 访问强化测试（2026-09）。

覆盖：
- calculate_decay_weight 指数衰减（exp(-0.05/天)）
- access_count 高的记忆衰减更慢（间隔重复效应）
- _calculate_relevance 排序：常被回忆的旧记忆 > 30 天没回忆的旧记忆
- on_memories_accessed 回忆强化落盘
"""

import json
import math
import shutil
import tempfile
from datetime import datetime, timedelta

from memory.cognitive_engine import CognitiveEngine
from memory.core import MemoryItem
from memory.memory_enhancer import MemoryEnhancer


async def test_decay_weight_exponential():
    """指数衰减：40 天 ≈ exp(-0.05*40) ≈ 0.135（原线性实现此时已触底 0.1）。"""
    tmp = tempfile.mkdtemp()
    try:
        enh = MemoryEnhancer(tmp)
        await enh.initialize()
        created = (datetime.now() - timedelta(days=40)).isoformat()
        w = enh.calculate_decay_weight("m1", created)
        expected = math.exp(-0.05 * 40)
        assert abs(w - expected) < 0.02, f"40天衰减权重应≈{expected:.3f}，实际 {w:.3f}"
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_access_count_slows_decay():
    """同龄记忆，access_count=8 的比 access_count=0 的权重高。"""
    tmp = tempfile.mkdtemp()
    try:
        enh = MemoryEnhancer(tmp)
        await enh.initialize()
        created = (datetime.now() - timedelta(days=40)).isoformat()
        w_quiet = enh.calculate_decay_weight("a", created, access_count=0)
        w_recalled = enh.calculate_decay_weight("b", created, access_count=8)
        assert w_recalled > w_quiet + 0.2, (
            f"常被回忆的记忆应明显更重: {w_recalled:.3f} vs {w_quiet:.3f}"
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


async def test_relevance_prefers_recalled_memory():
    """同优先级同龄旧记忆：常被回忆的检索得分更高。"""
    eng = CognitiveEngine(memory_core=None)
    old = (datetime.now() - timedelta(days=40)).isoformat()
    quiet = MemoryItem(id="a", content="我们聊过考试", created_at=old, priority=0.5)
    recalled = MemoryItem(
        id="b", content="我们聊过考试", created_at=old, priority=0.5, access_count=8
    )
    r_quiet = await eng._calculate_relevance(quiet, [], ["考试"])
    r_recalled = await eng._calculate_relevance(recalled, [], ["考试"])
    assert r_recalled > r_quiet


async def test_recent_beats_old():
    """无访问差异时，新记忆得分高于 40 天前的旧记忆（遗忘曲线生效）。"""
    eng = CognitiveEngine(memory_core=None)
    fresh = MemoryItem(id="a", content="我们聊过考试", priority=0.5)
    old = MemoryItem(
        id="b",
        content="我们聊过考试",
        created_at=(datetime.now() - timedelta(days=40)).isoformat(),
        priority=0.5,
    )
    r_fresh = await eng._calculate_relevance(fresh, [], ["考试"])
    r_old = await eng._calculate_relevance(old, [], ["考试"])
    assert r_fresh > r_old


async def test_on_memories_accessed_persists():
    """回忆强化：批量访问写入权重文件，衰减因子提升。"""
    tmp = tempfile.mkdtemp()
    try:
        enh = MemoryEnhancer(tmp)
        await enh.initialize()
        await enh.on_memories_accessed(["m1", "m2"])
        assert enh._weights["m1"].decay_factor == 1.05
        assert enh._weights["m1"].last_accessed is not None

        with open(f"{tmp}/memory_weights.json", encoding="utf-8") as f:
            data = json.load(f)
        assert "m1" in data and "m2" in data
    finally:
        shutil.rmtree(tmp, ignore_errors=True)

"""A5 回忆模糊化测试（2026-09）。

覆盖：
- build_context 按相关度分档措辞（确定 / 印象里 / 好像）
- 模糊片段（fuzzy_fragment 元数据）特殊措辞
- _humanize_time 人类口吻时间
- _is_fuzzy_candidate 时间窗（30~50 天）
"""

from datetime import datetime, timedelta

from memory.cognitive_engine import CognitiveEngine
from memory.core import MemoryItem


def _engine_with_relevance(value: float) -> CognitiveEngine:
    eng = CognitiveEngine(memory_core=None)

    async def _noop():
        return None

    eng._ensure_memory_core_initialized = _noop

    async def _fixed(*args, **kwargs):
        return value

    eng._calculate_relevance = _fixed
    return eng


async def test_confident_tier():
    eng = _engine_with_relevance(0.9)
    item = MemoryItem(id="m1", content="确定记得的事", created_at=datetime.now().isoformat())
    ctx = await eng.build_context("在吗", memories=[item])
    assert "确定记得的事" in ctx
    line = [ln for ln in ctx.splitlines() if "确定记得的事" in ln][0]
    assert line.startswith("- 今天："), f"高相关应确定陈述: {line}"
    assert "印象里" not in line and "好像" not in line


async def test_impression_tier():
    eng = _engine_with_relevance(0.6)
    item = MemoryItem(id="m1", content="大概的事", created_at=datetime.now().isoformat())
    ctx = await eng.build_context("在吗", memories=[item])
    line = [ln for ln in ctx.splitlines() if "大概的事" in ln][0]
    assert "印象里" in line, f"中等相关应含'印象里': {line}"


async def test_uncertain_tier():
    eng = _engine_with_relevance(0.35)
    item = MemoryItem(id="m1", content="模糊的事", created_at=datetime.now().isoformat())
    ctx = await eng.build_context("在吗", memories=[item])
    line = [ln for ln in ctx.splitlines() if "模糊的事" in ln][0]
    assert "好像" in line and "不太确定" in line, f"低相关应不确定措辞: {line}"


async def test_fuzzy_fragment_wording():
    eng = _engine_with_relevance(0.05)
    item = MemoryItem(id="m1", content="很久前的碎片")
    item.created_at = (datetime.now() - timedelta(days=40)).isoformat()
    item.metadata["fuzzy_fragment"] = True
    ctx = await eng.build_context("在吗", memories=[item])
    line = [ln for ln in ctx.splitlines() if "很久前的碎片" in ln][0]
    assert "很模糊的记忆碎片" in line and "记不太清" in line, f"模糊片段措辞: {line}"


def test_humanize_time():
    h = CognitiveEngine._humanize_time
    now = datetime.now()
    assert h(now.isoformat()) == "今天"
    assert h((now - timedelta(days=1)).isoformat()) == "昨天"
    assert h((now - timedelta(days=7)).isoformat()) == "上周"
    assert h((now - timedelta(days=30)).isoformat()) == "上个月"
    assert "去年" in h((now - timedelta(days=400)).isoformat())
    assert h("坏数据") == "以前"


def test_is_fuzzy_candidate_window():
    eng = CognitiveEngine(memory_core=None)

    def _item(days: float) -> MemoryItem:
        return MemoryItem(
            id=f"m{days}",
            content="x",
            created_at=(datetime.now() - timedelta(days=days)).isoformat(),
        )

    assert eng._is_fuzzy_candidate(_item(40)) is True
    assert eng._is_fuzzy_candidate(_item(35)) is True
    assert eng._is_fuzzy_candidate(_item(10)) is False, "太新，不是模糊片段候选"
    assert eng._is_fuzzy_candidate(_item(60)) is False, "太旧（>50天），不浮现"
    assert eng._is_fuzzy_candidate(MemoryItem(id="bad", content="x", created_at="垃圾")) is False

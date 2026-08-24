"""稳定画像测试（2026-08 修订计划 Step 6）。

覆盖：
- 归一化文本去重键
- ID/文本双重去重，时间戳最新者胜
- 用户隔离（群聊不跨用户泄漏）
- 最多 3 条上限
- 格式化输出与空段
- fetch 失败降级空段、日志无正文
"""

import pytest

from core.stable_persona import (
    MAX_STABLE_ITEMS,
    STABLE_TAGS,
    dedupe_against,
    fetch_stable_persona,
    format_stable_persona,
    merge_and_dedupe,
    normalize_text,
)
from memory.core import MemoryItem


def _item(content, mid="", uid="global", created="2026-01-01T00:00:00"):
    return MemoryItem(id=mid, content=content, user_id=uid, created_at=created)


# ==================== 归一化 ====================

def test_normalize_text_strips_and_lowercases():
    assert normalize_text("  喜欢  读书  ") == "喜欢读书"
    assert normalize_text("Hello  World") == "helloworld"
    assert normalize_text("") == ""


# ==================== 合并去重 ====================

def test_dedupe_by_id_newest_wins():
    old = _item("用户喜欢读书", mid="m1", created="2026-01-01T00:00:00")
    new = _item("用户喜欢读书（更新）", mid="m1", created="2026-06-01T00:00:00")
    merged = merge_and_dedupe([old, new])
    assert len(merged) == 1
    assert merged[0].content == "用户喜欢读书（更新）"


def test_dedupe_by_normalized_text_without_id():
    from types import SimpleNamespace

    # 无 ID 条目（MemoryItem 会自动生成 ID，故用 SimpleNamespace 模拟）
    a = SimpleNamespace(id="", content="喜欢 读书", user_id="global", created_at="2026-01-01T00:00:00", updated_at="")
    b = SimpleNamespace(id="", content="喜欢读书", user_id="global", created_at="2026-05-01T00:00:00", updated_at="")
    merged = merge_and_dedupe([a, b])
    assert len(merged) == 1
    assert merged[0].content == "喜欢读书"  # 最新


def test_merge_keeps_distinct_items():
    items = [_item("喜欢读书", mid="m1"), _item("用户是程序员", mid="m2")]
    assert len(merge_and_dedupe(items)) == 2


def test_max_items_cap():
    items = [_item(f"条目{i}", mid=f"m{i}") for i in range(10)]
    merged = merge_and_dedupe(items)
    assert len(merged) == MAX_STABLE_ITEMS == 3


# ==================== 用户隔离 ====================

def test_user_isolation_filters_others():
    mine = _item("我的喜好", mid="m1", uid="123")
    others = _item("别人私密信息", mid="m2", uid="999")
    merged = merge_and_dedupe([mine, others], target_user_id="123")
    assert len(merged) == 1
    assert merged[0].content == "我的喜好"


def test_global_items_not_filtered():
    items = [_item("全局条目", mid="m1", uid="global")]
    merged = merge_and_dedupe(items, target_user_id="123")
    assert len(merged) == 1


# ==================== 格式化 ====================

def test_format_empty_returns_empty():
    assert format_stable_persona([]) == ""


def test_format_segment():
    items = [_item("用户喜欢读书", mid="m1", created="2026-06-01T10:30:00")]
    seg = format_stable_persona(items)
    assert "【关于TA的稳定印象（长期记忆）】" in seg
    assert "用户喜欢读书" in seg
    assert "06-01 10:30" in seg


# ==================== fetch ====================

class _FakeCore:
    def __init__(self, items=None, raise_err=False):
        self.items = items or []
        self.raise_err = raise_err

    async def retrieve(self, query):
        if self.raise_err:
            raise RuntimeError("boom")
        return self.items


@pytest.mark.asyncio
async def test_fetch_returns_segment():
    core = _FakeCore([_item("用户喜欢读书", mid="m1")])
    seg = await fetch_stable_persona(core, user_id="123", group_id="456")
    assert "用户喜欢读书" in seg


@pytest.mark.asyncio
async def test_fetch_none_core_returns_empty():
    assert await fetch_stable_persona(None, user_id="123") == ""


@pytest.mark.asyncio
async def test_fetch_failure_returns_empty():
    core = _FakeCore(raise_err=True)
    assert await fetch_stable_persona(core, user_id="123") == ""


@pytest.mark.asyncio
async def test_fetch_logs_counts_not_content(caplog):
    import logging

    core = _FakeCore([_item("秘密内容XYZ", mid="m1")])
    with caplog.at_level(logging.INFO):
        await fetch_stable_persona(core, user_id="123")
    assert "秘密内容XYZ" not in caplog.text
    assert "去重后 1 条" in caplog.text


def test_whitelist_tags_defined():
    assert set(STABLE_TAGS) == {"喜好", "信息", "identity", "重要"}


# ==================== 隐私硬约束（验收补充） ====================

@pytest.mark.asyncio
async def test_fetch_without_user_id_returns_empty_no_global_retrieval():
    """缺少 user_id 时返回空段，绝不退化为全局检索（隐私硬约束）"""
    core = _FakeCore([_item("OTHER_USER_PRIVATE", mid="m9", uid="999")])
    seg = await fetch_stable_persona(core, user_id=None, group_id=None)
    assert seg == ""
    assert "OTHER_USER_PRIVATE" not in seg


@pytest.mark.asyncio
async def test_fetch_without_user_id_no_query():
    """缺少 user_id 时不应构造查询（记录查询次数）"""
    class _CountingCore:
        def __init__(self):
            self.queries = 0

        async def retrieve(self, query):
            self.queries += 1
            return [_item("OTHER_USER_PRIVATE", mid="m9", uid="999")]

    core = _CountingCore()
    await fetch_stable_persona(core, user_id=None)
    assert core.queries == 0  # 未发起任何检索


# ==================== 双轨去重（验收补充） ====================

def test_dedupe_against_by_id():
    a = _item("用户喜欢读书", mid="m1")
    b = _item("用户喜欢读书", mid="m1")  # 同一 ID
    result = dedupe_against([a], [b])
    assert result == []


def test_dedupe_against_by_normalized_text():
    from types import SimpleNamespace

    a = SimpleNamespace(id="", content="喜欢 读书", user_id="global", created_at="", updated_at="")
    excl = SimpleNamespace(id="", content="喜欢读书", user_id="global", created_at="", updated_at="")
    result = dedupe_against([a], [excl])
    assert result == []


def test_dedupe_against_keeps_distinct():
    a = _item("用户喜欢读书", mid="m1")
    b = _item("用户是程序员", mid="m2")
    excl = _item("无关条目", mid="m9")
    result = dedupe_against([a, b], [excl])
    assert len(result) == 2


@pytest.mark.asyncio
async def test_fetch_excludes_cognitive_duplicates():
    """同一记忆同时被认知引擎与稳定画像命中 → 稳定画像剔除（双轨不重复）"""
    cognitive_item = _item("用户喜欢读书", mid="m1")
    persona_item = _item("用户喜欢读书", mid="m1")  # 双轨命中同一条
    core = _FakeCore([persona_item])
    seg = await fetch_stable_persona(
        core, user_id="123", exclude_items=[cognitive_item]
    )
    assert seg == ""  # 与认知记忆重复 → 稳定画像为空

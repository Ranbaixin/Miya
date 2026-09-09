"""对话历史截断测试（2026-08 修订计划 Step 7）。

覆盖：
- 最新优先截断：超预算时保留最新消息（原实现保旧丢新）
- 截断后恢复时间正序
- 档位锚定配置：正常=config max_count(30)，回忆/深聊有下限
- 配置驱动 max_count（不硬编码 20/30/50）
"""

from types import SimpleNamespace

import pytest

from hub.conversation_context import ConversationContextManager


class _FakeHistory:
    def __init__(self, messages):
        self.messages = messages
        self.last_limit = None

    async def get_history(self, session_id, limit=None):
        self.last_limit = limit
        return self.messages


class _FakeMemoryNet:
    def __init__(self, messages):
        self.conversation_history = _FakeHistory(messages)


def _msg(i, cjk_len=30):
    """第 i 条消息（时间严格递增，内容中文，保守估算 2*cjk_len+1 tokens）"""
    from datetime import datetime, timedelta

    ts = (datetime(2026, 8, 1) + timedelta(minutes=i)).isoformat()
    return SimpleNamespace(
        role="user" if i % 2 == 0 else "assistant",
        content=f"消息{i}：" + "中" * cjk_len,
        timestamp=ts,
    )


def _make_manager(messages, max_count=30, max_tokens=6000):
    mgr = ConversationContextManager(_FakeMemoryNet(messages))
    mgr.conversation_context_max_count = max_count
    mgr.conversation_context_max_tokens = max_tokens
    return mgr


# ==================== 最新优先截断 ====================

@pytest.mark.asyncio
async def test_newest_first_truncation_keeps_newest():
    # 每条约 37 tokens（2026-09 校准系数 1.1/字）；max_tokens=120 → 只能装下最新 3 条
    messages = [_msg(i) for i in range(10)]
    mgr = _make_manager(messages, max_tokens=120)
    ctx = await mgr.get_conversation_context("s1", current_input="你好")
    contents = [m["content"] for m in ctx]
    assert len(contents) == 3
    assert contents == [m.content for m in messages[-3:]]  # 最新 3 条
    assert messages[0].content not in contents  # 最旧被丢


@pytest.mark.asyncio
async def test_truncated_context_is_ascending():
    messages = [_msg(i) for i in range(10)]
    mgr = _make_manager(messages, max_tokens=120)
    ctx = await mgr.get_conversation_context("s1", current_input="你好")
    times = [m["timestamp"] for m in ctx]
    assert times == sorted(times)  # 恢复时间正序


@pytest.mark.asyncio
async def test_no_truncation_when_under_budget():
    messages = [_msg(i) for i in range(3)]
    mgr = _make_manager(messages, max_tokens=6000)
    ctx = await mgr.get_conversation_context("s1", current_input="你好")
    assert len(ctx) == 3


# ==================== 档位锚定配置 ====================

@pytest.mark.asyncio
async def test_normal_tier_uses_config_max_count():
    messages = [_msg(i) for i in range(40)]
    mgr = _make_manager(messages, max_count=30)
    await mgr.get_conversation_context("s1", current_input="你好")
    assert mgr.memory_net.conversation_history.last_limit == 30


@pytest.mark.asyncio
async def test_normal_tier_loads_last_config_count():
    messages = [_msg(i) for i in range(40)]
    mgr = _make_manager(messages, max_count=30, max_tokens=999999)
    ctx = await mgr.get_conversation_context("s1", current_input="你好")
    assert len(ctx) == 30
    assert ctx[-1]["content"] == messages[-1].content  # 最新保留


@pytest.mark.asyncio
async def test_recall_tier_has_floor():
    messages = [_msg(i) for i in range(100)]
    mgr = _make_manager(messages, max_count=30, max_tokens=999999)
    await mgr.get_conversation_context("s1", current_input="你还记得上次我们聊过什么吗")
    assert mgr.memory_net.conversation_history.last_limit >= 80


@pytest.mark.asyncio
async def test_deep_discussion_tier_has_floor():
    messages = [_msg(i) for i in range(100)]
    mgr = _make_manager(messages, max_count=30, max_tokens=999999)
    long_input = "为什么" * 30  # 超 50 字符触发深度讨论
    await mgr.get_conversation_context("s1", current_input=long_input)
    assert mgr.memory_net.conversation_history.last_limit >= 50

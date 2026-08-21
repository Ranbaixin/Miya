"""OneBot 消息并发分发测试（2026-08 并发改造验收）。

验证：
- 会话 key 划分（群按群、私聊按用户）
- 同会话串行（conv lock）
- 跨会话并发且受 semaphore(4) 限流
"""

import asyncio

import pytest

from core.unified_platform_impl.onebot_platform import OneBotPlatform


@pytest.fixture
def platform():
    return OneBotPlatform(config={"bot_qq": "10001", "ws_reverse_port": 0})


def test_conv_key(platform):
    assert platform._conv_key("group", "123", "456") == "group:123"
    assert platform._conv_key("group", "", "456") == "private:456"
    assert platform._conv_key("private", "999", "456") == "private:456"


def test_conv_lock_singleton(platform):
    a = platform._get_conv_lock("group:1")
    b = platform._get_conv_lock("group:1")
    assert a is b
    c = platform._get_conv_lock("group:2")
    assert c is not a


async def test_same_conversation_serial(platform):
    """同会话两条消息必须串行（并发度 1）。"""
    active = 0
    max_active = 0

    async def fake_handle(data):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.03)
        active -= 1

    platform._handle_onebot_message = fake_handle
    msgs = [
        {"message_type": "private", "sender": {"user_id": "42"}},
        {"message_type": "private", "sender": {"user_id": "42"}},
        {"message_type": "private", "sender": {"user_id": "42"}},
    ]
    await asyncio.gather(*[platform._dispatch_message(m) for m in msgs])
    assert max_active == 1


async def test_cross_conversation_concurrent_but_limited(platform):
    """不同会话可并发，但全局限流 ≤4。"""
    active = 0
    max_active = 0

    async def fake_handle(data):
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1

    platform._handle_onebot_message = fake_handle
    msgs = [
        {"message_type": "private", "sender": {"user_id": str(i)}} for i in range(10)
    ]
    await asyncio.gather(*[platform._dispatch_message(m) for m in msgs])
    assert 1 < max_active <= 4


async def test_dispatch_error_isolated(platform):
    """单条消息异常不影响后续消息。"""
    calls = []

    async def fake_handle(data):
        if data.get("boom"):
            raise RuntimeError("boom")
        calls.append(data["ok"])

    platform._handle_onebot_message = fake_handle
    await platform._dispatch_message({"message_type": "private", "sender": {"user_id": "1"}, "boom": True})
    await platform._dispatch_message({"message_type": "private", "sender": {"user_id": "1"}, "ok": "fine"})
    assert calls == ["fine"]

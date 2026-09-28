"""OneBot 私聊合并接线测试：私聊 intake 不取会话锁、并发不串行；
群聊路径保持原并发门；合并轮次端到端只生成一次、只发送一次。"""
import asyncio
import types

import pytest

from core.unified_platform_impl.dm_merger import IngestOutcome
from core.unified_platform_impl.onebot_platform import OneBotPlatform


def _make_platform(**extra) -> OneBotPlatform:
    cfg = {"bot_qq": "10001", "ws_reverse_port": 0, "dm_merge_enabled": True}
    cfg.update(extra)
    return OneBotPlatform(config=cfg)


def _event(user_id: int, text: str) -> dict:
    return {
        "post_type": "message",
        "message_type": "private",
        "user_id": user_id,
        "sender": {"user_id": user_id, "nickname": f"u{user_id}"},
        "message": text,
        "raw_message": text,
        "time": 0,
        "self_id": 10001,
    }


@pytest.mark.asyncio
async def test_private_intake_not_serialized_by_conv_lock(monkeypatch):
    """私聊分发不走会话锁：两条同用户私聊消息可同时进入处理（旧实现此处=1 串行）。

    替换 _handle_onebot_message（重量级解析层）为可控慢桩，
    只验证 _dispatch_message 的分支与并发语义。"""
    p = _make_platform()
    inside = 0
    max_concurrent = 0
    release = asyncio.Event()

    async def slow_handle(data):
        nonlocal inside, max_concurrent
        inside += 1
        max_concurrent = max(max_concurrent, inside)
        await release.wait()
        inside -= 1

    monkeypatch.setattr(p, "_handle_onebot_message", slow_handle)
    t1 = asyncio.create_task(p._dispatch_message(_event(1, "一")))
    await asyncio.sleep(0.02)
    t2 = asyncio.create_task(p._dispatch_message(_event(1, "二")))
    await asyncio.sleep(0.02)
    assert max_concurrent == 2  # 关键断言：私聊未被会话锁串行化
    release.set()
    await asyncio.gather(t1, t2)


@pytest.mark.asyncio
async def test_group_path_unchanged_through_conv_lock(monkeypatch):
    p = _make_platform()
    order = []

    async def fake_group_handle(data):
        order.append(("handle", data["group_id"]))

    monkeypatch.setattr(p, "_handle_onebot_message", fake_group_handle)
    data = {
        "post_type": "message",
        "message_type": "group",
        "group_id": "g1",
        "sender": {"user_id": 9},
        "message": "x",
        "raw_message": "x",
    }
    await p._dispatch_message(data)
    assert order == [("handle", "g1")]
    assert p._dm_merger._states == {}  # 群聊不进合并器


@pytest.mark.asyncio
async def test_route_branch_merges_and_sends_once():
    p = _make_platform()
    calls = {"generate": 0, "send": 0}

    async def ingest(sub):
        return IngestOutcome(respond_ctx=types.SimpleNamespace(content=sub.content), direct_text=None)

    async def generate(key, batch, handle):
        calls["generate"] += 1
        await handle.try_commit()  # 模拟 decision_hub 提交契约
        return "合并回复"

    async def send(key, batch, text):
        calls["send"] += 1
        assert text == "合并回复"
        return True

    p._dm_merger._ingest_fn = ingest
    p._dm_merger._generate_fn = generate
    p._dm_merger._send_fn = send

    await p._route_chat_response(
        data=_event(1, "一"), content="一", user_id="1", user_name="u1",
        msg_type="private", group_id_str="", group_name="", sender_role="member",
        is_at_bot=True, extra=None, has_media=False,
    )
    await p._route_chat_response(
        data=_event(1, "二"), content="二", user_id="1", user_name="u1",
        msg_type="private", group_id_str="", group_name="", sender_role="member",
        is_at_bot=True, extra=None, has_media=False,
    )
    st = p._dm_merger._states["private:1"]
    deadline = asyncio.get_running_loop().time() + 2.0
    while st.worker is not None and not st.worker.done():
        assert asyncio.get_running_loop().time() < deadline, "worker 未收敛"
        await asyncio.sleep(0.01)
    assert calls == {"generate": 1, "send": 1}  # 两条输入只生成一次、发送一次


@pytest.mark.asyncio
async def test_route_branch_group_uses_legacy_route(monkeypatch):
    p = _make_platform()
    called = {"route": 0}

    async def fake_route(**kwargs):
        called["route"] += 1
        return "群回复"

    async def fake_reply(original, text):
        called["reply"] = text

    monkeypatch.setattr(p, "route_to_decision_hub", fake_route)
    monkeypatch.setattr(p, "_send_onebot_reply", fake_reply)
    await p._route_chat_response(
        data={"message_type": "group", "group_id": "g1", "sender": {"user_id": 9}},
        content="x", user_id="9", user_name="u9", msg_type="group",
        group_id_str="g1", group_name="", sender_role="member",
        is_at_bot=True, extra=None, has_media=False,
    )
    assert called == {"route": 1, "reply": "群回复"}


@pytest.mark.asyncio
async def test_dm_generate_applies_filters_and_uses_respond():
    p = _make_platform()
    seen = {}

    async def respond(ctx, turn_handle=None):
        seen["ctx"] = ctx
        seen["handle"] = turn_handle
        return "[Draft notes in english]\n答案正文"  # 首行=英文风格前缀，_filter_thinking 应剥除

    p._miya_core = types.SimpleNamespace(
        decision_hub=types.SimpleNamespace(respond_cross_platform=respond)
    )
    from core.unified_platform_impl.dm_merger import DmPending

    batch = [
        DmPending(original={}, content="x", respond_ctx=types.SimpleNamespace(content="x"))
    ]
    out = await p._dm_generate("private:1", batch, None)
    assert seen["handle"] is None
    assert out == "答案正文"  # _filter_thinking 已剥除前缀行


@pytest.mark.asyncio
async def test_dm_generate_injects_merge_header_for_batch():
    p = _make_platform()

    async def respond(ctx, turn_handle=None):
        return ctx.content

    p._miya_core = types.SimpleNamespace(
        decision_hub=types.SimpleNamespace(respond_cross_platform=respond)
    )
    from core.unified_platform_impl.dm_merger import DmPending

    batch = [
        DmPending(original={}, content="第一条", respond_ctx=types.SimpleNamespace(content="第一条")),
        DmPending(original={}, content="第二条", respond_ctx=types.SimpleNamespace(content="第二条")),
    ]
    out = await p._dm_generate("private:1", batch, None)
    assert "【合并回复】" in out
    assert "2 条消息" in out
    assert "第一条" in out and "第二条" in out


def test_merge_disabled_falls_back():
    p = _make_platform(dm_merge_enabled=False)
    assert p._dm_merger is None
    assert p._dm_merge_enabled is False

"""OneBot 私聊合并接线测试（2026-09-29 修复版契约）。

覆盖：登记先行（媒体分析不阻塞登记）/ 准备回调 / 生成副本不叠加 / echo 发送确认
（sent/partial/timeout、语音回退文字）/ 群聊路径不变 / commit 与 shutdown 挂接。"""
import asyncio
import types

import pytest

from core.unified_platform_impl.dm_merger import (
    DmInput,
    GenerateOutcome,
    IngestOutcome,
    PreparedInput,
    SendResult,
    SynthOutcome,
)
from core.unified_platform_impl.onebot_platform import OneBotPlatform


def _make_platform(**extra) -> OneBotPlatform:
    cfg = {"bot_qq": "10001", "ws_reverse_port": 0, "dm_merge_enabled": True}
    cfg.update(extra)
    return OneBotPlatform(config=cfg)


def _event(user_id: int, text: str, msg_id: int = 100) -> dict:
    return {
        "post_type": "message",
        "message_type": "private",
        "user_id": user_id,
        "message_id": msg_id,
        "sender": {"user_id": user_id, "nickname": f"u{user_id}"},
        "message": text,
        "raw_message": text,
        "time": 0,
        "self_id": 10001,
    }


# ---------- 登记先行 ----------


@pytest.mark.asyncio
async def test_private_registration_before_media_analysis(monkeypatch):
    """私聊带图消息：登记立即发生，慢分析（_analyze_message_media）不被同步调用。"""
    p = _make_platform()
    registered = []
    analyzed = {"n": 0}

    async def fake_register(sub):
        registered.append(sub)

    async def fake_analyze(**kwargs):
        analyzed["n"] += 1
        return kwargs["content"], kwargs["extra"], kwargs["has_media"], False

    async def fake_handle(data):
        await p._handle_chat_message(data)

    p._dm_merger = types.SimpleNamespace(register=fake_register)
    monkeypatch.setattr(p, "_analyze_message_media", fake_analyze)
    monkeypatch.setattr(p, "_is_user_allowed", lambda uid: True)
    monkeypatch.setattr(p, "_is_group_allowed", lambda gid: True)
    monkeypatch.setattr(p, "_is_at_bot", lambda raw, qq: False)
    monkeypatch.setattr(p, "_extract_at_list", lambda raw: [])
    monkeypatch.setattr(p, "_spawn", lambda coro: None)
    monkeypatch.setattr(p, "_ensure_decision_hub_refs", lambda: None)
    monkeypatch.setattr(p, "_auto_save_images", lambda segs, uid: _noop())
    monkeypatch.setattr(p, "_auto_save_string_images", lambda raw, uid: _noop())

    data = _event(1, "")
    data["raw_message"] = "[CQ:image,file=abc.jpg,url=https://x/y.jpg]"
    await p._handle_chat_message(data)

    assert len(registered) == 1, "私聊消息必须立即登记"
    sk = registered[0].extra["__skeleton__"]
    assert len(sk["image_segments"]) == 1, "骨架携带图片段供准备任务分析"
    assert registered[0].msg_id == "100"
    assert analyzed["n"] == 0, "慢分析不得阻塞登记路径"


async def _noop():
    return None


@pytest.mark.asyncio
async def test_dm_prepare_invokes_media_analysis():
    """准备回调：从骨架还原并调用 _analyze_message_media。"""
    p = _make_platform()
    captured = {}

    async def fake_analyze(**kwargs):
        captured.update(kwargs)
        return "带图内容", {"image_analysis": {"success": True}}, True, False

    p._analyze_message_media = fake_analyze
    from core.unified_platform_impl.dm_merger import DmSubmit

    sub = DmSubmit(
        key="private:1",
        original={},
        msg_id="m1",
        raw_content="",
        user_id="1",
        user_name="u1",
        extra={"__skeleton__": {"content": "", "image_segments": [{"type": "image"}], "file_segments": [],
                                "reply_id": "", "face_texts": [], "has_media": True, "user_id": "1", "bot_qq": "10001"}},
    )
    prepared = await p._dm_prepare(sub)
    assert prepared.content == "带图内容"
    assert prepared.extra["image_analysis"]["success"] is True
    assert captured["user_id"] == "1"


# ---------- 生成副本不叠加 ----------


@pytest.mark.asyncio
async def test_dm_generate_fresh_copy_no_accumulation():
    """同一 batch 重算两次：原始 ctx.content 不被修改（合并提示只进副本）。"""
    p = _make_platform()
    seen_contents = []

    async def respond(ctx):
        seen_contents.append(ctx.content)
        return types.SimpleNamespace(response="回答", artifacts={"n": 1})

    p._miya_core = types.SimpleNamespace(decision_hub=types.SimpleNamespace(respond_cross_platform=respond))
    ctx = types.SimpleNamespace(
        perception={"content": "原始"}, content="原始", platform="aiocqhttp", message=None
    )
    inp = DmInput(seq=1, msg_id="m1", original={}, raw_content="x", user_id="1")
    inp.content = "原始"
    inp.respond_ctx = ctx

    from core.turn_context import DraftContext

    inp2 = DmInput(seq=2, msg_id="m2", original={}, raw_content="y", user_id="1")
    inp2.content = "第二条"
    inp2.respond_ctx = types.SimpleNamespace(
        perception={}, content="第二条", platform="aiocqhttp", message=None
    )
    batch = [inp, inp2]
    for _ in range(2):
        await p._dm_generate("private:1", batch, None, DraftContext())

    assert ctx.content == "原始", "原始上下文不得被合并提示污染"
    assert seen_contents[0] == seen_contents[1], "每次生成独立副本，不叠加"
    assert seen_contents[0].count("【合并回复】") == 1, "重算不叠加合并提示"
    assert "原始" in seen_contents[0] and "第二条" in seen_contents[0]


@pytest.mark.asyncio
async def test_dm_generate_injects_draft_note():
    """草稿上下文的提示说明被注入副本。"""
    p = _make_platform()

    async def respond(ctx):
        return types.SimpleNamespace(response=ctx.content, artifacts=None)

    p._miya_core = types.SimpleNamespace(decision_hub=types.SimpleNamespace(respond_cross_platform=respond))
    from core.turn_context import DraftContext

    draft = DraftContext(draft_reply="上一轮草稿")
    inp = DmInput(seq=1, msg_id="m1", original={}, raw_content="x", user_id="1")
    inp.content = "新输入"
    inp.respond_ctx = types.SimpleNamespace(
        perception={}, content="新输入", platform="aiocqhttp", message=None
    )
    out = await p._dm_generate("private:1", [inp], None, draft)
    assert "未发送草稿" in out.response and "上一轮草稿" in out.response
    assert "新输入" in out.response


# ---------- echo 发送确认 ----------


@pytest.mark.asyncio
async def test_dm_send_echo_all_confirmed():
    p = _make_platform()
    p._ws = types.SimpleNamespace()
    p._connected = True
    calls = []

    async def fake_echo(action, params):
        calls.append(params["message"])
        return True, {"message_id": len(calls)}

    p._send_onebot_with_echo = fake_echo
    inp = DmInput(seq=1, msg_id="m1", original=_event(1, "hi"), raw_content="hi", user_id="1")
    result = await p._dm_send("private:1", [inp], "第一条\n\n第二条", None)
    assert result.status == "sent"
    assert len(result.message_ids) == 2 and len(result.sent_chunks) == 2


@pytest.mark.asyncio
async def test_dm_send_second_chunk_fails_partial():
    p = _make_platform()
    p._ws = types.SimpleNamespace()
    p._connected = True

    async def fake_echo(action, params):
        if params["message"] == "第二段":
            return False, {"status": "failed", "wording": "rejected"}
        return True, {"message_id": 1}

    p._send_onebot_with_echo = fake_echo
    p._split_message = lambda text, max_len: ["第一段", "第二段"]
    inp = DmInput(seq=1, msg_id="m1", original=_event(1, "hi"), raw_content="hi", user_id="1")
    result = await p._dm_send("private:1", [inp], "第一段第二段", None)
    assert result.status == "partial"
    assert result.sent_chunks == ["第一段"], "只保留确认成功的片段"
    assert result.delivered_text == "第一段"


@pytest.mark.asyncio
async def test_dm_send_echo_timeout_no_retry():
    """echo 超时：状态未知、停止剩余分条、不重发。"""
    p = _make_platform()
    p._ws = types.SimpleNamespace()
    p._connected = True
    attempts = []

    async def fake_echo(action, params):
        attempts.append(params["message"])
        return None, None

    p._send_onebot_with_echo = fake_echo
    p._split_message = lambda text, max_len: ["A", "B"]
    inp = DmInput(seq=1, msg_id="m1", original=_event(1, "hi"), raw_content="hi", user_id="1")
    result = await p._dm_send("private:1", [inp], "AB", None)
    assert result.status == "timeout"
    assert attempts == ["A"], "超时后停止剩余分条且不重试"


@pytest.mark.asyncio
async def test_dm_send_voice_timeout_falls_back_to_text():
    """语音发送超时 → 回退文字发送（不重试语音）。"""
    p = _make_platform()
    p._ws = types.SimpleNamespace()
    p._connected = True
    voice_attempts = {"n": 0}
    text_calls = []

    async def fake_voice(msg_type, target_id, text, audio):
        voice_attempts["n"] += 1
        return SendResult(status="timeout", error="语音 echo 超时")

    async def fake_echo(action, params):
        text_calls.append(params["message"])
        return True, {"message_id": 9}

    p._send_voice_with_echo = fake_voice
    p._send_onebot_with_echo = fake_echo
    inp = DmInput(seq=1, msg_id="m1", original=_event(1, "hi"), raw_content="hi", user_id="1")
    result = await p._dm_send("private:1", [inp], "文字内容", "/tmp/a.mp3")
    assert voice_attempts["n"] == 1, "语音只尝试一次"
    assert result.status == "sent" and text_calls == ["文字内容"], "语音未确认时回退文字"


# ---------- 群聊与杂项 ----------


@pytest.mark.asyncio
async def test_dm_ingest_maps_error_text():
    p = _make_platform()
    p.ingest_to_decision_hub = _fake_ingest_err
    inp = DmInput(seq=1, msg_id="m1", original={}, raw_content="x", user_id="1")
    inp.content = "hi"
    out = await p._dm_ingest(inp)
    assert out.error_text == "系统未就绪"


async def _fake_ingest_err(**kwargs):
    return "系统未就绪", None


@pytest.mark.asyncio
async def test_do_stop_shuts_down_merger():
    p = _make_platform()
    stopped = []

    async def fake_shutdown():
        stopped.append(True)

    p._dm_merger = types.SimpleNamespace(shutdown=fake_shutdown)
    await p._do_stop()
    assert stopped == [True]


def test_merge_disabled_falls_back():
    p = _make_platform(dm_merge_enabled=False)
    assert p._dm_merger is None
    assert p._dm_merge_enabled is False


# ---------- dispatch 并发语义（修复版：私聊免会话锁） ----------


@pytest.mark.asyncio
async def test_private_intake_not_serialized_by_conv_lock(monkeypatch):
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
    assert max_concurrent == 2
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
    assert p._dm_merger._states == {}

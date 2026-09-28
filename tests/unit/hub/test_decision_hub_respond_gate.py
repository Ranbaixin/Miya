"""_respond_phase 提交闸门测试：被替代轮次必须跳过 主动聊天/表情包/AI记忆/
工作记忆/Historian 全部输出副作用；已提交轮次全部执行。

手法：SimpleNamespace 桩 + 调用未绑定方法 DecisionHub._respond_phase(hub_stub, ...)，
仅依赖被测函数真实代码路径（不 mock 被测函数本身）。"""
import types

import pytest

from hub.decision_hub import RespondContext


class _FakeHandle:
    def __init__(self, allow_commit: bool):
        self._allow = allow_commit
        self.committed = False

    async def try_commit(self) -> bool:
        self.committed = self._allow
        return self._allow

    def is_superseded(self) -> bool:
        return not self._allow


def _hub_stub(response: str):
    hub = types.SimpleNamespace()
    calls = {"proactive": 0, "emoji": 0, "memory": 0, "historian": 0, "wm": 0}

    async def fake_generate(content, platform, context=None):
        return response

    async def fake_proactive(perception, content, resp):
        calls["proactive"] += 1

        class _R:
            should_respond = False

        return _R()

    async def fake_emoji_fn(resp, perception):
        calls["emoji"] += 1

    async def fake_store(perception, role):
        calls["memory"] += 1

    hub._generate_response_cross_platform = fake_generate
    hub._handle_proactive_chat = fake_proactive
    hub._handle_smart_emoji = fake_emoji_fn
    hub.memory_manager = types.SimpleNamespace(store_unified_memory=fake_store)
    hub.personality = types.SimpleNamespace(
        current_form="normal",
        get_profile=lambda: {"current_form": "normal", "speak_mode": "casual"},
    )
    hub.emotion = types.SimpleNamespace(
        set_form=lambda f: None,
        influence_response=lambda r: r,
        decay_coloring=lambda: None,
    )
    hub._test_calls = calls
    return hub


@pytest.fixture
def patched_globals(monkeypatch):
    """替换 _respond_phase 内部用到的模块级单例获取函数，避免触碰真实存储。"""
    import hub.decision_hub as dh

    calls = {"historian": 0}

    async def process_after_response(user_input, response, uid):
        calls["historian"] += 1

    fake_hist = types.SimpleNamespace(process_after_response=process_after_response)
    monkeypatch.setattr(dh, "get_historian", lambda: fake_hist, raising=True)

    wm_calls = {"wm": 0}

    def add_message(**kwargs):
        wm_calls["wm"] += 1

    fake_wm = types.SimpleNamespace(add_message=add_message)
    monkeypatch.setattr("memory.working_memory.get_working_memory", lambda: fake_wm, raising=True)
    calls["wm_obj"] = wm_calls
    return calls


def _ctx():
    return RespondContext(
        perception={"user_id": "u1", "content": "你好", "message_type": "private"},
        content="你好",
        platform="aiocqhttp",
        message=types.SimpleNamespace(content={}),
    )


def _respond(hub_stub, handle):
    from hub.decision_hub import DecisionHub

    return DecisionHub._respond_phase(hub_stub, _ctx(), turn_handle=handle)


@pytest.mark.asyncio
async def test_superseded_round_skips_all_output_side_effects(patched_globals):
    hub = _hub_stub("草稿回复")
    out = await _respond(hub, _FakeHandle(allow_commit=False))
    assert out == "草稿回复"
    c = hub._test_calls
    assert c == {"proactive": 0, "emoji": 0, "memory": 0, "historian": 0, "wm": 0}
    assert patched_globals["historian"] == 0 and patched_globals["wm_obj"]["wm"] == 0


@pytest.mark.asyncio
async def test_committed_round_runs_all_output_side_effects(patched_globals):
    hub = _hub_stub("正式回复")
    out = await _respond(hub, _FakeHandle(allow_commit=True))
    assert out == "正式回复"
    c = hub._test_calls
    assert c["proactive"] == 1 and c["memory"] == 1
    assert patched_globals["historian"] == 1 and patched_globals["wm_obj"]["wm"] == 1


@pytest.mark.asyncio
async def test_no_handle_keeps_legacy_behavior(patched_globals):
    """turn_handle=None（群聊/终端/Web 原路径）：不做闸门，副作用照常执行。"""
    hub = _hub_stub("普通回复")
    out = await _respond(hub, None)
    assert out == "普通回复"
    c = hub._test_calls
    assert c["proactive"] == 1 and c["memory"] == 1

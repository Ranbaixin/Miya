"""_respond_phase 双模式 + commit_pending 测试（2026-09-29 待提交数据语义）。

- collect_only=True（DM 合并）：情绪染色执行；主动聊天/表情/正式记忆/工作记忆/
  Historian/生成侧产物全部不落库（打包进 PendingCommit）。
- collect_only=False（原路径）：全部副作用立即执行，行为不变。
- commit_pending：按 SendResult 分层提交——完整→全文；部分→确认片段；失败→不写。

手法：SimpleNamespace 桩 + 未绑定调用真实代码路径，不 mock 被测函数本身。"""
import types

import pytest

import hub.decision_hub as dh_mod
from hub.decision_hub import GeneratedArtifacts, PendingCommit, RespondContext


class _Recorder:
    def __init__(self):
        self.calls = {"proactive": 0, "emoji": 0, "memory": 0, "historian": 0, "wm": 0, "artifacts": 0}
        self.memory_args = []
        self.wm_args = []
        self.artifacts_arg = None

    def snapshot(self):
        return dict(self.calls)


def _hub_stub(response: str, rec: _Recorder):
    hub = types.SimpleNamespace()

    async def fake_generate(content, platform, context=None):
        # 返回 (response, artifacts) 新契约
        art = GeneratedArtifacts(
            emotion_memory_content="【情绪记录】测试",
            owner_user_id="u1",
            lifebook_interaction={"user_message": content, "lover_response": response},
        )
        return response, art

    async def fake_proactive(perception, content, resp):
        rec.calls["proactive"] += 1

        class _R:
            should_respond = False

        return _R()

    async def fake_emoji(resp, perception):
        rec.calls["emoji"] += 1

    async def fake_store(perception, role):
        rec.calls["memory"] += 1
        rec.memory_args.append((dict(perception), role))

    def fake_wm_add(**kwargs):
        rec.calls["wm"] += 1
        rec.wm_args.append(kwargs)

    hub._generate_response_cross_platform = fake_generate
    hub._handle_proactive_chat = fake_proactive
    hub._handle_smart_emoji = fake_emoji

    async def fake_commit_artifacts(art):
        rec.calls["artifacts"] += 1
        rec.artifacts_arg = art

    hub._commit_artifacts = fake_commit_artifacts
    hub.memory_manager = types.SimpleNamespace(store_unified_memory=fake_store)
    hub.personality = types.SimpleNamespace(
        current_form="normal",
        get_profile=lambda: {"current_form": "normal", "speak_mode": "casual"},
    )
    hub.emotion = types.SimpleNamespace(
        set_form=lambda f: None,
        influence_response=lambda r: r + "♪",
        decay_coloring=lambda: None,
    )
    hub._rec = rec
    return hub


@pytest.fixture
def patched_globals(monkeypatch):
    rec = _Recorder()

    async def process_after_response(user_input, response, uid):
        rec.calls["historian"] += 1

    fake_hist = types.SimpleNamespace(process_after_response=process_after_response)
    monkeypatch.setattr(dh_mod, "get_historian", lambda: fake_hist, raising=True)

    def add_message(**kwargs):
        rec.calls["wm"] += 1
        rec.wm_args.append(kwargs)

    fake_wm = types.SimpleNamespace(add_message=add_message)
    monkeypatch.setattr("memory.working_memory.get_working_memory", lambda: fake_wm, raising=True)
    return rec


def _ctx():
    return RespondContext(
        perception={"user_id": "u1", "content": "你好", "message_type": "private"},
        content="你好",
        platform="aiocqhttp",
        message=types.SimpleNamespace(content={}),
    )


def _respond(hub_stub, ctx, collect_only):
    from hub.decision_hub import DecisionHub

    return DecisionHub._respond_phase(hub_stub, ctx, collect_only=collect_only)


# ---------- collect_only=True（DM 合并路径） ----------


@pytest.mark.asyncio
async def test_collect_mode_defers_all_output_side_effects(patched_globals):
    hub = _hub_stub("草稿回复", patched_globals)
    outcome = await _respond(hub, _ctx(), collect_only=True)
    assert outcome.response == "草稿回复♪", "情绪染色照常执行（发送前文本效果）"
    assert outcome.pending is not None
    assert outcome.pending.response == "草稿回复♪"
    assert outcome.pending.artifacts.emotion_memory_content is not None
    c = patched_globals.snapshot()
    assert c == {"proactive": 0, "emoji": 0, "memory": 0, "historian": 0, "wm": 0, "artifacts": 0}, (
        "草稿阶段零落库、零发送"
    )


# ---------- collect_only=False（原路径行为不变） ----------


@pytest.mark.asyncio
async def test_legacy_mode_runs_all_side_effects(patched_globals):
    hub = _hub_stub("正式回复", patched_globals)
    outcome = await _respond(hub, _ctx(), collect_only=False)
    assert outcome.response == "正式回复♪"
    assert outcome.pending is None
    c = patched_globals.snapshot()
    assert c["proactive"] == 1 and c["memory"] == 1 and c["historian"] == 1 and c["wm"] == 1
    assert c["artifacts"] == 1, "生成侧产物在原路径立即提交"
    assert patched_globals.artifacts_arg.emotion_memory_content is not None


# ---------- commit_pending 分层提交 ----------


def _pending():
    art = GeneratedArtifacts(
        emotion_memory_content="情绪", owner_user_id="u1",
        lifebook_interaction={"user_message": "你好", "lover_response": "全文回复", "emotion": "平静"},
    )
    return PendingCommit(artifacts=art, perception={"user_id": "u1", "content": "你好", "message_type": "private"}, response="全文回复♪")


def _commit_hub(rec):
    hub = _hub_stub("x", rec)
    return hub


@pytest.mark.asyncio
async def test_commit_pending_full_send_writes_full_text(patched_globals, monkeypatch):
    from core.unified_platform_impl.dm_merger import SendResult
    from hub.decision_hub import DecisionHub

    hub = _commit_hub(patched_globals)

    async def no_artifacts(art):
        patched_globals.calls["artifacts"] += 1

    hub._commit_artifacts = no_artifacts
    await DecisionHub.commit_pending(hub, _pending(), SendResult(status="sent", sent_chunks=["全文回复♪"], message_ids=[1]))
    assert patched_globals.calls["memory"] == 1
    assert patched_globals.memory_args[0][0]["response"] == "全文回复♪"
    assert patched_globals.calls["historian"] == 1 and patched_globals.calls["wm"] == 1


@pytest.mark.asyncio
async def test_commit_pending_partial_writes_only_delivered(patched_globals):
    from core.unified_platform_impl.dm_merger import SendResult
    from hub.decision_hub import DecisionHub

    hub = _commit_hub(patched_globals)

    async def no_artifacts(art):
        pass

    hub._commit_artifacts = no_artifacts
    await DecisionHub.commit_pending(hub, _pending(), SendResult(status="partial", sent_chunks=["全文"], message_ids=[1]))
    assert patched_globals.calls["memory"] == 1
    assert patched_globals.memory_args[0][0]["response"] == "全文", "部分发送只记录确认片段"


@pytest.mark.asyncio
async def test_commit_pending_failed_writes_nothing_but_model_experience(patched_globals):
    from core.unified_platform_impl.dm_merger import SendResult
    from hub.decision_hub import DecisionHub

    hub = _commit_hub(patched_globals)
    committed = []

    async def fake_artifacts(art):
        committed.append(art)

    hub._commit_artifacts = fake_artifacts
    await DecisionHub.commit_pending(hub, _pending(), SendResult(status="failed", error="ws 断开"))
    assert patched_globals.calls["memory"] == 0, "发送失败不写正式回答"
    assert patched_globals.calls["wm"] == 0 and patched_globals.calls["historian"] == 0
    assert len(committed) == 1, "情绪/认知等模型侧体验照常提交"


@pytest.mark.asyncio
async def test_commit_pending_runs_emoji_inline_only_when_delivered(patched_globals):
    from core.unified_platform_impl.dm_merger import SendResult
    from hub.decision_hub import DecisionHub

    hub = _commit_hub(patched_globals)

    async def no_artifacts(art):
        pass

    hub._commit_artifacts = no_artifacts
    # 未送达 → 不执行附加输出
    await DecisionHub.commit_pending(hub, _pending(), SendResult(status="failed", error="x"))
    assert patched_globals.calls["emoji"] == 0 and patched_globals.calls["proactive"] == 0
    # 送达 → 表情在当前任务内执行（无 create_task）
    await DecisionHub.commit_pending(hub, _pending(), SendResult(status="sent", sent_chunks=["全文回复♪"]))
    assert patched_globals.calls["emoji"] == 1 and patched_globals.calls["proactive"] == 1

"""DM 私聊连续输入合并器状态机单元测试（修复版语义）。

覆盖：按序处理/去重/准备超时/失败统一出口/发送阶段划分/草稿与工具记录传递/
SendResult 提交/批次清理/shutdown。手法：真实 PrivateChatMerger + 受控 fake
回调（asyncio.Event 控制时序，不依赖短睡眠），不 mock 被测对象自身。"""
import asyncio

import pytest

from core.turn_context import current_draft_context, current_turn_handle
from core.unified_platform_impl.dm_merger import (
    DmSubmit,
    GenerateOutcome,
    IngestOutcome,
    PreparedInput,
    PrivateChatMerger,
    SendResult,
    SynthOutcome,
)


def _sub(user_id="u1", content="你好", msg_id="m1") -> DmSubmit:
    return DmSubmit(
        key=f"private:{user_id}",
        original={"message_type": "private", "sender": {"user_id": user_id}, "message_id": msg_id},
        msg_id=msg_id,
        raw_content=content,
        user_id=user_id,
        user_name=f"用户{user_id}",
        extra=None,
    )


class _Harness:
    """可控 fake 回调：prepare/ingest/generate/send 均可挂 Event 控制时序。"""

    def __init__(self, prepare_timeout=30.0):
        self.gen_gate = asyncio.Event()  # 生成完成放行
        self.send_gate = asyncio.Event()  # 发送放行
        self.hold_send = False
        self.prep_gates: dict[str, asyncio.Event] = {}  # content -> gate
        self.prep_calls: list[str] = []
        self.ingest_order: list[str] = []
        self.generate_calls: list[list[str]] = []  # 每轮 batch 的内容序列
        self.draft_views: list = []  # 每轮收到的 DraftContext
        self.sent: list[str] = []
        self.commits: list[SendResult] = []
        self.post_sends: list[SendResult] = []
        self.gen_error: Optional[Exception] = None
        self.gen_error_text: Optional[str] = None
        self.send_results: list[SendResult] = []  # 逐次 send 返回值
        self.merger = PrivateChatMerger(
            prepare_fn=self._prepare,
            ingest_fn=self._ingest,
            generate_fn=self._generate,
            synth_fn=self._synth,
            send_fn=self._send,
            commit_fn=self._commit,
            post_send_fn=self._post_send,
            prepare_timeout=prepare_timeout,
        )

    async def _prepare(self, sub: DmSubmit) -> PreparedInput:
        self.prep_calls.append(sub.raw_content)
        gate = self.prep_gates.get(sub.raw_content)
        if gate is not None:
            await gate.wait()
        return PreparedInput(content=sub.raw_content, extra=None)

    async def _ingest(self, inp) -> IngestOutcome:
        self.ingest_order.append(inp.content or f"<{inp.status}>")
        return IngestOutcome(respond_ctx={"content": inp.content}, direct_text=None)

    async def _generate(self, key, batch, handle, draft_ctx):
        assert current_turn_handle() is handle, "生成期间轮次凭证必须在位"
        assert current_draft_context() is draft_ctx, "生成期间草稿上下文必须在位"
        self.generate_calls.append([i.content for i in batch])
        self.draft_views.append(draft_ctx)
        if self.gen_error is not None:
            err, self.gen_error = self.gen_error, None
            raise err
        if self.gen_error_text is not None:
            t, self.gen_error_text = self.gen_error_text, None
            return GenerateOutcome(response=t, artifacts=None, is_error=True)
        await self.gen_gate.wait()
        self.gen_gate.clear()
        return GenerateOutcome(response=f"回复@{len(self.generate_calls)}", artifacts={"n": len(self.generate_calls)})

    async def _synth(self, batch, text) -> SynthOutcome:
        return SynthOutcome(send_text=text, audio_path=None)

    async def _send(self, key, batch, text, audio) -> SendResult:
        if self.hold_send:
            await self.send_gate.wait()
            self.send_gate.clear()
            self.hold_send = False
        if self.send_results:
            return self.send_results.pop(0)
        self.sent.append(text)
        return SendResult(status="sent", message_ids=[1], sent_chunks=[text])

    async def _commit(self, artifacts, send_result):
        self.commits.append(send_result)

    async def _post_send(self, key, batch, send_result, outcome):
        self.post_sends.append(send_result)


async def _wait(cond, timeout=2.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while not cond():
        assert loop.time() < deadline, "等待超时"
        await asyncio.sleep(0.01)


# ---------- 按序与去重 ----------


@pytest.mark.asyncio
async def test_slow_first_input_preserves_order():
    """A 先到但准备慢、B 后到：入账顺序与模型 batch 均为 A→B。"""
    h = _Harness()
    h.prep_gates["A"] = asyncio.Event()
    await h.merger.register(_sub(content="A", msg_id="m1"))
    await h.merger.register(_sub(content="B", msg_id="m2"))
    await _wait(lambda: len(h.merger._states["private:u1"].inputs) == 2)
    h.prep_gates["A"].set()  # A 准备完成（B 早已 ready，但必须等 A）
    await _wait(lambda: len(h.generate_calls) == 1)
    assert h.generate_calls[0] == ["A", "B"], "模型输入必须按 A→B"
    assert h.ingest_order == ["A", "B"], "用户记忆入账必须按 A→B"
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 1)


@pytest.mark.asyncio
async def test_duplicate_event_ignored():
    """同一 msg_id 重复事件：不重复登记、不触发重算。"""
    h = _Harness()
    await h.merger.register(_sub(msg_id="m1"))
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.generate_calls) == 1)
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 1)
    await asyncio.sleep(0.05)
    assert len(h.generate_calls) == 1 and len(h.sent) == 1
    st = h.merger._states["private:u1"]
    assert st.version == 1


# ---------- 准备超时与失败 ----------


@pytest.mark.asyncio
async def test_prepare_timeout_marks_failed_others_continue():
    """A 准备超时→失败退出批次；B 正常参与综合。"""
    h = _Harness(prepare_timeout=0.2)
    h.prep_gates["A"] = asyncio.Event()  # A 永不就绪
    await h.merger.register(_sub(content="A", msg_id="m1"))
    await h.merger.register(_sub(content="B", msg_id="m2"))
    await _wait(lambda: len(h.generate_calls) == 1, timeout=3.0)
    assert h.generate_calls[0] == ["B"], "失败项不参与，B 继续综合"
    assert h.ingest_order == ["B"]
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 1)
    st = h.merger._states["private:u1"]
    await _wait(lambda: not st.inputs)
    assert st.inputs == []  # 失败项被清理


# ---------- 失败统一出口 ----------


@pytest.mark.asyncio
async def test_model_exception_latest_round_hint_once_then_recovers():
    """最新轮模型异常：仅一次失败提示；下一条消息正常处理。"""
    h = _Harness()
    h.gen_error = RuntimeError("模型超时")
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.sent) == 1)
    assert "小差错" in h.sent[0]
    await asyncio.sleep(0.05)
    assert len(h.sent) == 1, "失败提示只发一次"
    st = h.merger._states["private:u1"]
    assert st.status == "idle" and not st.inputs, "worker 结束且批次清理"
    # 下一条消息正常
    await h.merger.register(_sub(msg_id="m2", content="第二条"))
    await _wait(lambda: len(h.generate_calls) == 2)
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 2)
    assert "回复@" in h.sent[1]


@pytest.mark.asyncio
async def test_model_error_text_uses_failure_exit():
    """模型返回错误文本与异常同路：最新轮一次提示；过期轮静默重算。"""
    h = _Harness()
    h.gen_error_text = "AI 服务暂时不可用"
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.sent) == 1)
    assert "小差错" in h.sent[0]  # 错误文本不透传给用户
    assert h.commits == [], "失败轮不提交正式记忆"

    # 过期轮：生成前新输入到达 → 静默重算
    h2 = _Harness()

    async def gen_then_supersede(key, batch, handle, draft_ctx):
        h2.generate_calls.append([i.content for i in batch])
        if len(h2.generate_calls) == 1:
            await h2.merger.register(_sub(msg_id="mx", content="补充"))  # 生成期间新输入
            return GenerateOutcome(response="AI 服务错误", artifacts=None, is_error=True)
        return GenerateOutcome(response="最新综合回答", artifacts={"n": 2})

    h2.merger._generate_fn = gen_then_supersede
    await h2.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h2.generate_calls) == 1)
    await _wait(lambda: len(h2.generate_calls) == 2)  # 静默重算第二轮
    await _wait(lambda: len(h2.sent) == 1)
    assert h2.sent == ["最新综合回答"], "过期轮错误静默，最终发最新综合回答"


# ---------- 发送阶段划分 ----------


@pytest.mark.asyncio
async def test_synthesis_then_commit_new_input_during_synth_supersedes():
    """合成期间新输入：本轮作废为草稿（发送未发起），下一轮综合。"""
    h = _Harness()
    synth_gate = asyncio.Event()

    async def slow_synth(batch, text):
        await synth_gate.wait()
        return SynthOutcome(send_text=text, audio_path=None)

    h.merger._synth_fn = slow_synth
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.generate_calls) == 1)
    h.gen_gate.set()
    await asyncio.sleep(0.05)  # 进入 synth（卡住）
    await h.merger.register(_sub(msg_id="m2", content="补充"))
    synth_gate.set()
    await _wait(lambda: len(h.generate_calls) == 2)
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 1)
    assert h.sent == ["回复@2"], "草稿未发送，只发最新综合"
    assert h.commits and h.commits[0].fully_sent


@pytest.mark.asyncio
async def test_input_during_sending_starts_next_round():
    """发送期间新输入：本轮完整发完，新输入进入下一轮。"""
    h = _Harness()
    h.hold_send = True
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.generate_calls) == 1)
    h.gen_gate.set()
    st = h.merger._states["private:u1"]
    await _wait(lambda: st.status == "sending")
    await h.merger.register(_sub(msg_id="m2", content="第二条"))
    h.send_gate.set()
    await _wait(lambda: len(h.sent) == 1 and len(h.generate_calls) == 2)
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 2)
    assert h.sent == ["回复@1", "回复@2"]


# ---------- 草稿与工具记录 ----------


@pytest.mark.asyncio
async def test_draft_context_carried_to_next_round_and_cleared():
    """重算轮收到：草稿回复 + 累计工具记录；发送成功后批次清理。"""
    h = _Harness()

    async def gen_with_tool(key, batch, handle, draft_ctx):
        h.generate_calls.append([i.content for i in batch])
        h.draft_views.append(draft_ctx)
        from core.turn_context import ToolExecutionRecord

        draft_ctx.tool_records.append(ToolExecutionRecord("reminder_create", "{}", "ok", "已创建"))
        if len(h.generate_calls) == 1:
            await h.merger.register(_sub(msg_id="m2", content="补充"))  # 触发重算
            return GenerateOutcome(response="草稿回答", artifacts=None)
        await h.gen_gate.wait()
        h.gen_gate.clear()
        return GenerateOutcome(response="最终回答", artifacts={"n": 2})

    h.merger._generate_fn = gen_with_tool
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.generate_calls) == 2)
    # 第二轮收到草稿与累计工具记录
    d2 = h.draft_views[1]
    assert d2.draft_reply == "草稿回答"
    assert any(r.tool_name == "reminder_create" for r in d2.tool_records), "重算轮继承上轮工具记录"
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 1)
    st = h.merger._states["private:u1"]
    await _wait(lambda: st.last_draft_reply is None and not st.batch_tool_records)
    assert st.last_draft_reply is None and st.batch_tool_records == [], "批次结束清理"


@pytest.mark.asyncio
async def test_each_generation_gets_fresh_draft_copy():
    """每次生成使用新副本：修改本轮 draft_ctx 不影响上一轮对象。"""
    h = _Harness()
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.generate_calls) == 1)
    h.draft_views[0].draft_reply = "污染"
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 1)
    st = h.merger._states["private:u1"]
    assert st.last_draft_reply is None, "副本修改不回写状态"


# ---------- SendResult 提交 ----------


@pytest.mark.asyncio
async def test_partial_send_commits_only_confirmed_chunks():
    """部分发送：commit_fn 收到 SendResult（只含确认片段），不虚假标记全文。"""
    h = _Harness()
    h.send_results = [
        SendResult(status="partial", message_ids=[1], sent_chunks=["第一段"], error="第二段发送失败")
    ]
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.generate_calls) == 1)
    h.gen_gate.set()
    await _wait(lambda: len(h.commits) == 1)
    assert h.commits[0].status == "partial"
    assert h.commits[0].delivered_text == "第一段"
    st = h.merger._states["private:u1"]
    await _wait(lambda: not st.inputs)
    assert st.last_send_error is not None


@pytest.mark.asyncio
async def test_failed_send_no_retry_consume_batch():
    """发送失败：停止剩余、不重发、批次消费结束。"""
    h = _Harness()
    h.send_results = [SendResult(status="failed", error="ws 断开")]
    await h.merger.register(_sub(msg_id="m1"))
    await _wait(lambda: len(h.generate_calls) == 1)
    h.gen_gate.set()
    await _wait(lambda: len(h.commits) == 1)
    await asyncio.sleep(0.05)
    assert len(h.sent) == 0 and len(h.commits) == 1
    st = h.merger._states["private:u1"]
    await _wait(lambda: not st.inputs and st.status == "idle")


# ---------- 直发与隔离 ----------


@pytest.mark.asyncio
async def test_direct_text_immediate_send():
    """快捷命令：入账即发送，不参与生成轮次。"""
    h = _Harness()
    h.merger._ingest_fn = _make_direct_ingest(h, "状态结果")
    await h.merger.register(_sub(msg_id="m1", content="状态"))
    await _wait(lambda: len(h.sent) == 1)
    assert h.sent == ["状态结果"]
    assert h.generate_calls == []


def _make_direct_ingest(h, text):
    async def ingest(inp):
        h.ingest_order.append(inp.content)
        return IngestOutcome(respond_ctx=None, direct_text=text)

    return ingest


@pytest.mark.asyncio
async def test_different_users_isolated():
    h = _Harness()
    await h.merger.register(_sub("u1", "A", "m1"))
    await h.merger.register(_sub("u2", "B", "m2"))
    await _wait(lambda: len(h.generate_calls) == 2)
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 2)
    contents = {c[0] for c in h.generate_calls}
    assert contents == {"A", "B"}
    h.gen_gate.set()


# ---------- 清理 ----------


@pytest.mark.asyncio
async def test_worker_crash_state_recovers_next_message():
    """worker 兜底退出：状态被 finally 清理，下一条消息自愈。"""
    h = _Harness()
    boom_count = {"n": 0}

    async def boom_once(sub):
        boom_count["n"] += 1
        if boom_count["n"] == 1:
            raise RuntimeError("prep crash")
        return PreparedInput(content=sub.raw_content, extra=None)

    h.merger._prepare_fn = boom_once
    await h.merger.register(_sub(msg_id="m1"))
    st = h.merger._states["private:u1"]
    await _wait(lambda: st.inputs and st.inputs[0].status == "failed")
    # 失败项清理后 worker 退出，状态 idle
    await _wait(lambda: st.status == "idle" and not st.inputs)
    await h.merger.register(_sub(msg_id="m2", content="恢复"))
    await _wait(lambda: len(h.generate_calls) == 1)
    h.gen_gate.set()
    await _wait(lambda: len(h.sent) == 1)


@pytest.mark.asyncio
async def test_shutdown_cancels_all_tasks():
    """shutdown：取消 worker 与准备任务并等待退出。"""
    h = _Harness()
    h.prep_gates["慢"] = asyncio.Event()
    h.gen_gate.set()
    h.merger._ingest_fn = _make_direct_ingest(h, None) if False else h._ingest
    await h.merger.register(_sub(content="慢", msg_id="m1"))
    await asyncio.sleep(0.05)
    st = h.merger._states["private:u1"]
    assert st.worker is not None and not st.worker.done()
    await h.merger.shutdown()
    assert st.worker is None or st.worker.done()
    assert st.inputs == []

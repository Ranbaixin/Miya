"""DM 私聊连续输入合并器状态机单元测试。

手法：真实 PrivateChatMerger + 受控 fake 回调（asyncio.Event 控制节奏），
不 mock 被测对象自身。"""
import asyncio

import pytest

from core.turn_context import current_turn_handle
from core.unified_platform_impl.dm_merger import (
    DmPending,
    DmSubmit,
    IngestOutcome,
    PrivateChatMerger,
    TurnHandle,
)


def _sub(user_id: str = "u1", content: str = "你好") -> DmSubmit:
    return DmSubmit(
        key=f"private:{user_id}",
        original={"message_type": "private", "sender": {"user_id": user_id}},
        content=content,
        user_id=user_id,
        user_name=f"用户{user_id}",
        sender_role="member",
        extra=None,
    )


class _Harness:
    """可控 fake：ingest 立即返回；generate/send 可用 Event 卡住以便编排时序。

    - generate 恒等 generate_gate（模拟模型调用在途）
    - send 仅在 hold_send=True 时等 send_gate（模拟分条发送在途）
    - _generate 尾部调用 handle.try_commit()，模拟 decision_hub 的提交契约"""

    def __init__(self):
        self.generate_gate = asyncio.Event()
        self.send_gate = asyncio.Event()
        self.hold_send = False
        self.generate_calls: list[list[DmPending]] = []
        self.sent: list[str] = []
        self.merger = PrivateChatMerger(
            ingest_fn=self._ingest,
            generate_fn=self._generate,
            send_fn=self._send,
        )

    async def _ingest(self, sub: DmSubmit) -> IngestOutcome:
        return IngestOutcome(respond_ctx={"content": sub.content}, direct_text=None)

    async def _generate(self, key, batch, handle):
        assert current_turn_handle() is handle, "生成期间 contextvar 必须是当前轮次凭证"
        self.generate_calls.append(list(batch))
        await self.generate_gate.wait()
        self.generate_gate.clear()
        await handle.try_commit()  # 模拟 decision_hub._respond_phase 的提交契约
        return f"回复@轮{len(self.generate_calls)}"

    async def _send(self, key, batch, text):
        if self.hold_send:
            self.hold_send = False  # 仅卡第一次发送（模拟首轮分条发送在途）
            await self.send_gate.wait()
            self.send_gate.clear()
        self.sent.append(text)
        return True


async def _wait_condition(cond, timeout=2.0):
    deadline = asyncio.get_running_loop().time() + timeout
    while not cond():
        assert asyncio.get_running_loop().time() < deadline, "等待超时"
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_single_message_generates_and_sends_once():
    h = _Harness()
    await h.merger.submit(_sub())
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    assert len(h.generate_calls[0]) == 1  # 首条立即生成，无等待
    h.generate_gate.set()
    await _wait_condition(lambda: len(h.sent) == 1)
    assert h.sent == ["回复@轮1"]


@pytest.mark.asyncio
async def test_rapid_inputs_merge_into_one_round():
    h = _Harness()
    for text in ("一", "二", "三"):
        await h.merger.submit(_sub(content=text))
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    assert [p.content for p in h.generate_calls[0]] == ["一", "二", "三"]
    h.generate_gate.set()
    await _wait_condition(lambda: len(h.sent) == 1)
    assert len(h.generate_calls) == 1  # 三条输入只生成一次


@pytest.mark.asyncio
async def test_input_during_thinking_superseds_and_regenerates():
    h = _Harness()
    await h.merger.submit(_sub(content="第一条"))
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    await h.merger.submit(_sub(content="第二条"))  # 思考期间新输入 → 版本自增
    h.generate_gate.set()  # 第一轮生成完成 → 应判为草稿并重算
    await _wait_condition(lambda: len(h.generate_calls) == 2)
    assert [p.content for p in h.generate_calls[1]] == ["第一条", "第二条"]
    h.generate_gate.set()
    await _wait_condition(lambda: len(h.sent) == 1)
    assert h.sent == ["回复@轮2"]  # 草稿（轮1）永不发送
    st = h.merger._states["private:u1"]
    assert st.draft == "回复@轮1"


@pytest.mark.asyncio
async def test_input_during_sending_starts_next_round():
    h = _Harness()
    h.hold_send = True  # 发送卡在 gate（模拟多分条发送在途）
    await h.merger.submit(_sub(content="第一条"))
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    h.generate_gate.set()
    st = h.merger._states["private:u1"]
    await _wait_condition(lambda: st.status == "sending")
    await h.merger.submit(_sub(content="第二条"))  # 发送期间新输入 → 下一轮
    h.send_gate.set()
    await _wait_condition(lambda: len(h.sent) == 1 and len(h.generate_calls) == 2)
    h.generate_gate.set()
    await _wait_condition(lambda: len(h.sent) == 2)
    assert h.sent == ["回复@轮1", "回复@轮2"]


@pytest.mark.asyncio
async def test_try_commit_atomic_version_mismatch():
    h = _Harness()
    st = await h.merger._state_for("private:u1")
    handle = TurnHandle(h.merger, "private:u1", snapshot_version=st.version)
    st.version += 1  # 模拟提交前一刻新输入到达
    assert await handle.try_commit() is False
    assert handle.committed is False
    assert st.status != "sending"
    assert handle.is_superseded() is True
    # 版本一致时：原子置位 + 清空 pending
    handle2 = TurnHandle(h.merger, "private:u1", snapshot_version=st.version)
    st.pending.append(DmPending(original={}, content="x", respond_ctx={}))
    assert await handle2.try_commit() is True
    assert st.status == "sending" and st.pending == []


@pytest.mark.asyncio
async def test_different_users_isolated():
    h = _Harness()
    await h.merger.submit(_sub("u1", "A"))
    await h.merger.submit(_sub("u2", "B"))
    await _wait_condition(lambda: len(h.generate_calls) == 2)
    h.generate_gate.set()
    await _wait_condition(lambda: len(h.sent) == 2)
    contents = {sorted(p.content for p in c)[0] for c in h.generate_calls}
    assert contents == {"A", "B"}  # 两用户各自独立一轮
    h.generate_gate.set()


@pytest.mark.asyncio
async def test_generate_failure_current_round_sends_hint_once():
    h = _Harness()

    async def boom(key, batch, handle):
        h.generate_calls.append(list(batch))
        await h.generate_gate.wait()
        h.generate_gate.clear()
        raise RuntimeError("模型超时")

    h.merger._generate_fn = boom
    await h.merger.submit(_sub())
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    h.generate_gate.set()
    await _wait_condition(lambda: len(h.sent) == 1)
    assert h.merger._failure_hint in h.sent[0]
    await asyncio.sleep(0.05)
    assert len(h.sent) == 1  # 只提示一次，不重试


@pytest.mark.asyncio
async def test_generate_failure_superseded_round_silent():
    h = _Harness()

    async def boom_then_ok(key, batch, handle):
        h.generate_calls.append(list(batch))
        await h.generate_gate.wait()
        h.generate_gate.clear()
        if len(h.generate_calls) == 1:
            raise RuntimeError("过期轮次失败")
        await handle.try_commit()  # 成功轮走 decision_hub 的提交契约
        return "第二轮回复"

    h.merger._generate_fn = boom_then_ok
    await h.merger.submit(_sub(content="一"))
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    await h.merger.submit(_sub(content="二"))  # 生成在途时新输入 → 轮次过期
    h.generate_gate.set()  # 第一轮失败（已过期 → 静默）
    await _wait_condition(lambda: len(h.generate_calls) == 2)
    h.generate_gate.set()  # 第二轮成功
    await _wait_condition(lambda: len(h.sent) == 1)
    assert h.sent == ["第二轮回复"]  # 过期轮次错误不输出


@pytest.mark.asyncio
async def test_send_failure_records_and_does_not_retry():
    h = _Harness()

    async def failing_send(key, batch, text):
        raise ConnectionError("ws 断开")

    h.merger._send_fn = failing_send
    await h.merger.submit(_sub())
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    h.generate_gate.set()
    st = h.merger._states["private:u1"]
    await _wait_condition(lambda: st.status == "idle")
    assert st.last_send_error is not None


@pytest.mark.asyncio
async def test_direct_text_short_circuits_merge():
    h = _Harness()
    sent_direct: list[str] = []

    async def ingest(sub):
        return IngestOutcome(respond_ctx=None, direct_text="!命令结果")

    async def direct_send(key, batch, text):
        sent_direct.append(text)
        return True

    h.merger._ingest_fn = ingest
    h.merger._send_fn = direct_send
    await h.merger.submit(_sub(content="!状态"))
    await _wait_condition(lambda: len(sent_direct) == 1)
    assert h.generate_calls == []  # 即时结果不触发生成轮次

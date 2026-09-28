# QQ 私聊连续输入合并（DM Merge）实施计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** QQ 私聊同一用户连续发送的多条消息合并为一轮回复：首条立即生成；生成期间收到新输入则当前回答转为内部草稿并重算，直到生成期间无新增输入才发送；发送期间新输入排入下一轮。

**Architecture:** 新增 `PrivateChatMerger`（每私聊一个状态机：输入队列 + 版本号 + thinking/sending 状态），挂接在 OneBot 平台层；`DecisionHub.process_perception_cross_platform` 机械拆分为 `_ingest_phase`（感知+入账，不生成）与 `_respond_phase`（生成+提交闸门+副作用），原入口行为组合两 phase 保持不变；提交闸门 `TurnHandle.try_commit()` 用「版本比对 + 状态置位」的原子段实现「检查与进入发送之间不得插入」；工具暂停通过 contextvar（沿用 `_tool_context_var` 先例）传入 `ToolRegistry.execute_tool`，非只读工具在已替代轮次中跳过。

**Tech Stack:** Python 3.11 / asyncio（contextvars、Lock、Semaphore、create_task）/ pytest + pytest-asyncio（`asyncio_mode = "auto"`，无需标记）/ ruff（line-length 120）。

## Global Constraints

- 只影响 QQ 私聊（`message_type == "private"`）；群聊、终端、Web、拍一拍路径行为必须逐字节保持不变。
- 首条消息立即触发生成，不引入任何额外等待（intake 不取会话锁、不取全局信号量）。
- 生成期间新输入：当前请求继续完成但不输出（成为草稿）；**不取消**在途生成与已开始的工具调用。
- 提交检查（版本比对 → 状态置 sending → 清空 pending）必须是单个无 await 间隙的原子段。
- 一旦提交进入发送，本轮完整发完；分条发送失败即停止剩余分条，不重发已发送内容（现有 `_send_onebot_reply` 已具备，见 `core/unified_platform_impl/onebot_platform.py:981-983`）。
- 被替代轮次：不发送文字/语音/表情，不发桌面端助手事件，不写 AI 侧对话记忆/工作记忆/Historian（由 decision_hub 提交闸门统一保证）。
- 保留现有跨会话并发限制：生成仍走 `platform._dispatch_semaphore`（4）；ingest 用独立 `Semaphore(6)`；**不新增**请求超时/重试。
- 最新轮次生成失败仅发送一次失败提示；过期轮次错误静默记日志。
- 每条用户输入只记录一次：入账（store_user_message 等）发生在 intake 的 ingest 阶段，合并不重复入账。
- ruff line-length 120；新增 `except Exception` 必须带 `# noqa: BLE001 — <降级理由>`；CI 不变量脚本 `scripts/check_new_swallowed.py` 只放过带理由的新增行。
- 不新增第三方依赖；测试基线 321 passed 只增不减。
- 测试手法遵循项目惯例：真实实例 + 替换实例属性/方法 + fake 依赖注入（参照 `tests/unit/platform/test_message_dispatch.py`），禁止 mock 被测对象自证。

---

### Task 1: 轮次上下文 + 合并状态机核心（`dm_merger.py`）

**Files:**
- Create: `core/turn_context.py`
- Create: `core/unified_platform_impl/dm_merger.py`
- Test: `tests/unit/platform/test_dm_merger.py`

**Interfaces:**
- Consumes: 无（纯 asyncio，回调注入）。
- Produces:
  - `core.turn_context.turn_handle_var: ContextVar`、`current_turn_handle()` —— Task 3 的工具闸门读取。
  - `DmSubmit(key, original, content, user_id, user_name, sender_role, extra)`
  - `IngestOutcome(respond_ctx=None, direct_text=None, error_text=None)`
  - `DmPending(original, content, respond_ctx)`
  - `TurnHandle(merger, key, snapshot_version)`：`is_superseded() -> bool`、`async try_commit() -> bool`、`committed: bool`、`executed_tools: list`
  - `PrivateChatMerger(ingest_fn=, generate_fn=, send_fn=, generation_semaphore=None, ingest_semaphore=None, drain_timeout=15.0)`：`async submit(sub: DmSubmit)`；回调签名 `ingest_fn(sub) -> IngestOutcome`、`generate_fn(key, batch, handle) -> Optional[str]`、`send_fn(key, batch, text) -> bool`。

- [ ] **Step 1: 写失败测试 —— 状态机全行为**

创建 `tests/unit/platform/test_dm_merger.py`：

```python
"""DM 私聊连续输入合并器状态机单元测试。

手法：真实 PrivateChatMerger + 受控 fake 回调（asyncio.Event 控制节奏），
不 mock 被测对象自身。"""
import asyncio

import pytest

from core.turn_context import current_turn_handle, turn_handle_var
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
    """可控 fake：ingest 立即返回；generate/send 用 Event 卡住以便编排时序。"""

    def __init__(self):
        self.generate_gate = asyncio.Event()  # 置位后 generate 才返回
        self.send_gate = asyncio.Event()
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
        return f"回复@轮{len(self.generate_calls)}"

    async def _send(self, key, batch, text):
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
    await h.merger.submit(_sub(content="第一条"))
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    h.generate_gate.set()
    await _wait_condition(lambda: len(h.sent) == 0)  # send 卡在 gate
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
    keys = {sorted(p.content for p in c)[0] for c in h.generate_calls}
    assert keys == {"A", "B"}  # 两用户各自独立一轮
    h.generate_gate.set()


@pytest.mark.asyncio
async def test_generate_failure_current_round_sends_hint_once():
    h = _Harness()

    async def boom(key, batch, handle):
        h.generate_calls.append(list(batch))
        raise RuntimeError("模型超时")

    h.merger._generate_fn = boom
    await h.merger.submit(_sub())
    await _wait_condition(lambda: len(h.sent) == 1)
    assert h.merger._failure_hint in h.sent[0]
    await asyncio.sleep(0.05)
    assert len(h.sent) == 1  # 只提示一次，不重试


@pytest.mark.asyncio
async def test_generate_failure_superseded_round_silent():
    h = _Harness()

    async def boom_then_ok(key, batch, handle):
        h.generate_calls.append(list(batch))
        if len(h.generate_calls) == 1:
            raise RuntimeError("过期轮次失败")
        return "第二轮回复"

    h.merger._generate_fn = boom_then_ok
    await h.merger.submit(_sub(content="一"))
    await _wait_condition(lambda: len(h.generate_calls) == 1)
    await h.merger.submit(_sub(content="二"))
    await _wait_condition(lambda: len(h.generate_calls) == 2)
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
    await _wait_condition(lambda: h.merger._states["private:u1"].status == "idle")
    st = h.merger._states["private:u1"]
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
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/unit/platform/test_dm_merger.py -q -p no:cacheprovider`
Expected: FAIL —— `ModuleNotFoundError: No module named 'core.unified_platform_impl.dm_merger'`

- [ ] **Step 3: 实现 `core/turn_context.py`**

```python
"""请求级轮次上下文（contextvar）。

DM 私聊连续输入合并（core/unified_platform_impl/dm_merger.py）在生成期间
设置当前轮次凭证，工具执行层（webnet/ToolNet/registry.py）读取它判断本轮
是否已被新输入替代。独立轻量模块：避免 ai_client / webnet 反向依赖平台实现层
（先例：core/ai_client.py 的 _tool_context_var）。
"""
from contextvars import ContextVar
from typing import Optional, Protocol


class TurnHandleProtocol(Protocol):
    def is_superseded(self) -> bool:
        ...


turn_handle_var: ContextVar[Optional[TurnHandleProtocol]] = ContextVar(
    "miya_turn_handle", default=None
)


def current_turn_handle() -> Optional[TurnHandleProtocol]:
    """当前协程关联的 DM 合并轮次凭证；非合并路径返回 None。"""
    return turn_handle_var.get()
```

- [ ] **Step 4: 实现 `core/unified_platform_impl/dm_merger.py`**

```python
"""QQ 私聊连续输入合并器（DM Merge，2026-09-28 方案）。

行为契约：
- 每个私聊用户一个处理任务；首条消息立即触发生成，不引入额外等待
  （intake 只做：版本自增 + ingest 入账 + 入队，不取会话锁/生成信号量）。
- 思考（生成）期间收到新输入：当前生成继续完成但不输出，其回答作为内部
  草稿保留；worker 立即结合全部未回复输入重新生成，直到生成期间无新增。
- 提交闸门 TurnHandle.try_commit()：版本比对 + 状态置位在同一个
  「持锁且无内部 await」的原子段完成——检查与进入发送之间不得插入其他任务。
- 一旦提交进入 sending，本轮完整发完；期间新输入只 bump 版本并入队，
  由 send 完成后的下一轮处理。
- 被替代轮次不发送、不发事件、不写记忆（生成副作用由 decision_hub 的
  提交闸门跳过；发送由 worker 只在 committed 后执行）。
- ingest_fn 可能较慢（图片走视觉模型），worker 生成前等待在途 ingest 排空。
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from core.turn_context import turn_handle_var

logger = logging.getLogger(__name__)


@dataclass
class DmSubmit:
    """平台层递交给合并器的原始提交（收到即提交，不等任何长操作）。"""

    key: str  # 会话键，如 "private:12345"
    original: dict  # OneBot 原始事件（发送回复时的目标载体）
    content: str
    user_id: str
    user_name: str = ""
    sender_role: str = "member"
    extra: Optional[dict] = None


@dataclass
class IngestOutcome:
    """ingest_fn 的结果：待回复上下文 / 即时命令结果 / 错误文本（三选一）。"""

    respond_ctx: Any = None  # decision_hub.RespondContext，None=无需回复
    direct_text: Optional[str] = None  # 快捷命令/定时任务即时结果，不参与合并
    error_text: Optional[str] = None  # 系统未就绪等文本，立即原样发送


@dataclass
class DmPending:
    """已完成入账、等待合并回复的一条原始输入（每条只记录一次）。"""

    original: dict
    content: str
    respond_ctx: Any


@dataclass
class DmMergeState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    pending: List[DmPending] = field(default_factory=list)
    version: int = 0  # 收到新输入即自增（intake 快路径）
    status: str = "idle"  # idle | thinking | sending
    worker: Optional[asyncio.Task] = None
    draft: Optional[str] = None  # 最近一轮被替代的未发送回答（仅观测/排查）
    draft_tools: List[str] = []  # 被替代轮次已执行的工具名（仅观测/排查）
    ingesting: int = 0  # 在途 ingest 计数（图片分析可能秒级）
    last_send_error: Optional[str] = None


class TurnHandle:
    """一轮生成的提交凭证：worker 创建（快照版本号），decision_hub 生成后调用
    try_commit() 提交；工具层经 contextvar 读取以判断轮次是否已被替代。"""

    __slots__ = ("_merger", "_key", "snapshot_version", "committed", "executed_tools")

    def __init__(self, merger: "PrivateChatMerger", key: str, snapshot_version: int):
        self._merger = merger
        self._key = key
        self.snapshot_version = snapshot_version
        self.committed = False
        self.executed_tools: List[str] = []

    def is_superseded(self) -> bool:
        st = self._merger._states.get(self._key)
        if st is None:
            return True
        return st.version != self.snapshot_version

    async def try_commit(self) -> bool:
        """原子提交：版本一致 → status=sending + 清空 pending，返回 True；
        版本不一致（已被新输入替代）→ 返回 False。
        检查与置位之间持锁且无内部 await——满足「不得插入」约束。"""
        st = self._merger._states.get(self._key)
        if st is None:
            return False
        async with st.lock:
            if st.version != self.snapshot_version:
                return False
            st.status = "sending"
            st.pending.clear()
            self.committed = True
            return True


class PrivateChatMerger:
    """每私聊一状态机的合并编排核心。平台相关逻辑全部经回调注入，
    本类保持纯 asyncio、可独立单测。"""

    def __init__(
        self,
        *,
        ingest_fn: Callable[[DmSubmit], Awaitable[IngestOutcome]],
        generate_fn: Callable[[str, List[DmPending], TurnHandle], Awaitable[Optional[str]]],
        send_fn: Callable[[str, List[DmPending], str], Awaitable[bool]],
        generation_semaphore: Optional[asyncio.Semaphore] = None,
        ingest_semaphore: Optional[asyncio.Semaphore] = None,
        drain_timeout: float = 15.0,
        failure_hint: str = "（刚才回复时出了点小差错，请再发一次试试~）",
    ):
        self._ingest_fn = ingest_fn
        self._generate_fn = generate_fn
        self._send_fn = send_fn
        self._gen_sem = generation_semaphore or asyncio.Semaphore(4)
        self._ingest_sem = ingest_semaphore or asyncio.Semaphore(6)
        self.drain_timeout = drain_timeout
        self._failure_hint = failure_hint
        self._states: Dict[str, DmMergeState] = {}
        self._states_guard = asyncio.Lock()

    async def _state_for(self, key: str) -> DmMergeState:
        async with self._states_guard:
            st = self._states.get(key)
            if st is None:
                st = DmMergeState()
                self._states[key] = st
            return st

    async def submit(self, sub: DmSubmit) -> None:
        """私聊消息入口：版本自增（收到即记账）→ ingest 入账 → 入队/拉起 worker。"""
        st = await self._state_for(sub.key)
        async with st.lock:
            st.version += 1  # 接收新消息立即更新版本，不等待会话锁/ingest/生成
            st.ingesting += 1
        try:
            async with self._ingest_sem:
                outcome = await self._ingest_fn(sub)
        except Exception as e:  # noqa: BLE001 — 入账失败按失败提示处理，不让消息无声消失
            logger.error(f"[DM合并] ingest 失败 key={sub.key}: {e}", exc_info=True)
            outcome = IngestOutcome(error_text=self._failure_hint)
        finally:
            async with st.lock:
                st.ingesting -= 1

        if outcome.error_text:
            await self._safe_send(sub.key, [DmPending(original=sub.original, content=sub.content, respond_ctx=None)], outcome.error_text)
            return
        if outcome.direct_text:
            # 快捷命令/定时任务：即时回复，不参与合并轮次（不触发生成）
            await self._safe_send(
                sub.key,
                [DmPending(original=sub.original, content=sub.content, respond_ctx=None)],
                outcome.direct_text,
            )
            return

        async with st.lock:
            st.pending.append(
                DmPending(original=sub.original, content=sub.content, respond_ctx=outcome.respond_ctx)
            )
            worker = st.worker
            if worker is None or worker.done():
                st.worker = asyncio.create_task(self._run_chat(sub.key))

    async def _run_chat(self, key: str) -> None:
        """该私聊的唯一处理任务：循环「快照 → 生成 → 提交判定 → 发送」。"""
        st = self._states.get(key)
        assert st is not None
        while True:
            async with st.lock:
                if not st.pending:
                    st.status = "idle"
                    st.worker = None
                    return
                st.status = "thinking"
            await self._drain_ingest(st)  # 等在途 ingest 排空，保证快照完整
            async with st.lock:
                if not st.pending:  # 防御：排空等待期间被清空
                    st.status = "idle"
                    st.worker = None
                    return
                batch = list(st.pending)
                handle = TurnHandle(self, key, st.version)

            response: Optional[str] = None
            gen_error: Optional[BaseException] = None
            token = turn_handle_var.set(handle)
            try:
                async with self._gen_sem:  # 保留现有跨会话并发限制
                    response = await self._generate_fn(key, batch, handle)
            except Exception as e:  # noqa: BLE001 — 生成失败走统一提示路径，不冒泡
                gen_error = e
            finally:
                turn_handle_var.reset(token)

            if not handle.committed:
                # 未提交 = 生成期间收到新输入（或生成失败且轮次已过期）
                async with st.lock:
                    if gen_error is None:
                        st.draft = response
                        st.draft_tools = list(handle.executed_tools)
                    st.status = "idle"  # 立即进入下一轮重算
                if gen_error is not None:
                    logger.info(f"[DM合并] 过期轮次生成失败（静默，不输出）: {gen_error}")
                else:
                    logger.info(
                        f"[DM合并] 轮次#{handle.snapshot_version} 被新输入替代，"
                        f"回答保留为草稿并重算（已执行工具: {handle.executed_tools or '无'}）"
                    )
                continue

            if gen_error is not None:
                # 最新轮次失败：仅发送一次失败提示
                logger.error(f"[DM合并] 最新轮次生成失败: {gen_error}", exc_info=True)
                await self._safe_send(key, batch, self._failure_hint)
                async with st.lock:
                    st.status = "idle"
                continue

            send_ok = await self._safe_send(key, batch, response or "")
            if not send_ok:
                logger.error("[DM合并] 发送中断：停止剩余分条，不重发已发送内容")
            async with st.lock:
                st.status = "idle"
                # 循环回顶：pending 有新输入则下一轮，否则 idle 退出

    async def _drain_ingest(self, st: DmMergeState) -> None:
        deadline = time.monotonic() + self.drain_timeout
        while st.ingesting > 0:
            if time.monotonic() > deadline:
                logger.warning(f"[DM合并] 等待在途输入入账超时（{self.drain_timeout:.0f}s），按已就绪输入继续")
                return
            await asyncio.sleep(0.05)

    async def _safe_send(self, key: str, batch: List[DmPending], text: str) -> bool:
        try:
            ok = bool(await self._send_fn(key, batch, text))
            if not ok:
                st = self._states.get(key)
                if st is not None:
                    async with st.lock:
                        st.last_send_error = "send_fn 返回 False"
            return ok
        except Exception as e:  # noqa: BLE001 — 发送层异常不重发已发送内容，只记录
            logger.error(f"[DM合并] 发送异常（不重发已发送内容）: {e}")
            st = self._states.get(key)
            if st is not None:
                async with st.lock:
                    st.last_send_error = str(e)
            return False
```

- [ ] **Step 5: 运行测试确认通过**

Run: `uv run pytest tests/unit/platform/test_dm_merger.py -q -p no:cacheprovider`
Expected: PASS（11 个测试）

- [ ] **Step 6: 提交**

```bash
git add core/turn_context.py core/unified_platform_impl/dm_merger.py tests/unit/platform/test_dm_merger.py
git commit -m "feat: DM 私聊连续输入合并——轮次上下文与状态机核心（输入队列/版本/提交闸门）"
```

---

### Task 2: DecisionHub 拆分 ingest/respond 两阶段 + 提交闸门

**Files:**
- Modify: `hub/decision_hub.py`（`process_perception_cross_platform` 现位于 L810-1219）
- Test: `tests/unit/hub/test_decision_hub_respond_gate.py`

**Interfaces:**
- Consumes: Task 1 的 `TurnHandle.try_commit()`。
- Produces:
  - `RespondContext`（dataclass：`perception: dict`、`content: str`、`platform: str`、`message: Any`）
  - `DecisionHub._ingest_phase(message) -> tuple[Optional[RespondContext], Optional[str]]`
  - `DecisionHub._respond_phase(ctx: RespondContext, turn_handle=None) -> Optional[str]`
  - `DecisionHub.ingest_cross_platform(message)` —— DM 合并 intake 专用
  - `DecisionHub.respond_cross_platform(ctx, turn_handle=None)` —— DM 合并 worker 专用
  - `process_perception_cross_platform(message)` 对外签名与行为**完全不变**（群聊/终端/Web 继续走它）

- [ ] **Step 1: 写失败测试 —— 提交闸门跳过全部输出副作用**

创建 `tests/unit/hub/test_decision_hub_respond_gate.py`：

```python
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

    async def fake_store(perception, role):
        calls["memory"] += 1

    hub._generate_response_cross_platform = fake_generate
    hub._handle_proactive_chat = fake_proactive

    async def fake_emoji_fn(resp, perception):
        calls["emoji"] += 1

    hub._handle_smart_emoji = fake_emoji_fn
    hub.memory_manager = types.SimpleNamespace(store_unified_memory=fake_store)
    hub.personality = types.SimpleNamespace(
        current_form="normal", get_profile=lambda: {"current_form": "normal", "speak_mode": "casual"}
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

    calls = {"historian": 0, "wm": 0}
    fake_hist = types.SimpleNamespace()

    async def process_after_response(user_input, response, uid):
        calls["historian"] += 1

    fake_hist.process_after_response = process_after_response
    monkeypatch.setattr(dh, "get_historian", lambda: fake_hist, raising=True)

    fake_wm = types.SimpleNamespace()

    def add_message(**kwargs):
        calls["wm"] += 1

    fake_wm.add_message = add_message
    monkeypatch.setattr("memory.working_memory.get_working_memory", lambda: fake_wm, raising=True)
    return calls


def _ctx():
    return RespondContext(
        perception={"user_id": "u1", "content": "你好", "message_type": "private"},
        content="你好",
        platform="aiocqhttp",
        message=types.SimpleNamespace(content={}),
    )


@pytest.mark.asyncio
async def test_superseded_round_skips_all_output_side_effects(patched_globals):
    hub = _hub_stub("草稿回复")
    out = await DecisionHubModule()._respond_phase_call(hub, _FakeHandle(allow_commit=False))
    assert out == "草稿回复"
    c = hub._test_calls
    assert c == {"proactive": 0, "emoji": 0, "memory": 0, "historian": 0, "wm": 0}


@pytest.mark.asyncio
async def test_committed_round_runs_all_output_side_effects(patched_globals):
    hub = _hub_stub("正式回复")
    out = await DecisionHubModule()._respond_phase_call(hub, _FakeHandle(allow_commit=True))
    assert out == "正式回复"
    c = hub._test_calls
    assert c["proactive"] == 1 and c["memory"] == 1 and c["wm"] == 1 and c["historian"] == 1


class DecisionHubModule:
    """未绑定调用辅助：DecisionHub._respond_phase(hub_stub, ctx, handle)。"""

    @staticmethod
    def _respond_phase_call(hub_stub, handle):
        from hub.decision_hub import DecisionHub

        return DecisionHub._respond_phase(hub_stub, _ctx(), turn_handle=handle)
```

注意：`smart emoji` 在真实代码里是 `asyncio.create_task(self._handle_smart_emoji(response, perception))`（`decision_hub.py:1144`）。**测试里把该行所在分支要求为被替代时不执行**；若实现保留 create_task 形式，测试改为断言「被替代时该协程未被创建」——实现时直接用 `if response:` 分支整体跳过即可满足。

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/unit/hub/test_decision_hub_respond_gate.py -q -p no:cacheprovider`
Expected: FAIL —— `ImportError: cannot import name 'RespondContext'`

- [ ] **Step 3: 实现——机械拆分**

对 `hub/decision_hub.py` 做如下修改（先只动结构，不改任何既有语句）：

3a. 模块顶部（import 区之后）新增：

```python
@dataclass
class RespondContext:
    """_ingest_phase 的产物：_respond_phase 所需的最小上下文包。"""

    perception: dict
    content: str
    platform: str
    message: Any  # mlink Message（回写 response 用；可为 None）
```

（`dataclass`/`Any` 若未导入则补充 `from dataclasses import dataclass`、`from typing import Any`。）

3b. 把 `process_perception_cross_platform`（L810 起）**整体改名为** `_ingest_phase`，签名改为
`async def _ingest_phase(self, message: Message) -> tuple:`，然后**只修改其内部的 return**（方法体其余语句逐字保留）：

| 位置 | 原 return | 新 return |
|---|---|---|
| L847-850 内部标志消息过滤 | `return None` | `return None, None` |
| L985-988 快捷命令命中 | `return <resp>` | `return None, <resp>` |
| L1048 群聊无关键词不响应 | `return None` | `return None, None` |
| L1050-1059 终端命令 | `return <resp>` | `return None, <resp>` |
| L1082-1090 游戏模式直调工具 | `return tool_call_result` | `return None, tool_call_result` |
| L1126-1130 定时任务直调 | `return timer_result` | `return None, timer_result` |
| L1130 之后（原 L1132 生成之前） | （无） | `return RespondContext(perception=perception, content=content, platform=platform, message=message), None` |

完成后执行 `grep -n "return" hub/decision_hub.py` 核对：`_ingest_phase` 体内所有 return 均为二元组，无遗漏（这是拆分正确性的硬校验）。

3c. 紧接着新增 `_respond_phase`（**原 L1103-1219 的语句逐字搬入**，仅做以下改动）：

```python
    async def _respond_phase(self, ctx: "RespondContext", turn_handle=None) -> Optional[str]:
        """响应生成 + 提交闸门 + 输出副作用。

        turn_handle 非 None（DM 合并路径）时：生成完成后先 try_commit()，
        未提交（生成期间收到新输入）→ 本回答转为草稿，跳过下方全部输出副作用
        （主动聊天/表情包/情绪染色/AI记忆/工作记忆/Historian），直接返回。"""
        content = ctx.content
        perception = ctx.perception
        platform = ctx.platform
        message = ctx.message

        # 6. 生成响应（原 L1132）
        response = await self._generate_response_cross_platform(content, platform, perception)

        # ★ DM 合并提交闸门（2026-09-28）：版本比对+置位在 try_commit 内部原子完成
        if turn_handle is not None:
            committed = await turn_handle.try_commit()
            if not committed:
                logger.info("[决策层] 本轮生成期间收到新输入，回答转为草稿：跳过发送副作用与记忆写入")
                return response

        # 7. 主动聊天系统 v2.0（原 L1134-1144，逐字保留）
        ...（原 L1134-1219 全部语句不变，其中 L1215-1216 的 message.content[...] 用 ctx.message）...
```

（实现者注意：`原 L1104-1121` 的 content 规范化**留在 `_ingest_phase`**（它产出 ctx.content）；`_respond_phase` 从 ctx 取值，不重复规范化。）

3d. 新增对外入口（放在 `_respond_phase` 之后）：

```python
    async def process_perception_cross_platform(self, message: Message) -> Optional[str]:
        """兼容入口：感知入账 + 生成响应（群聊/终端/Web/拍一拍继续走此处，行为不变）。"""
        ctx, direct = await self._ingest_phase(message)
        if direct is not None:
            return direct
        if ctx is None:
            return None
        return await self._respond_phase(ctx, turn_handle=None)

    async def ingest_cross_platform(self, message: Message):
        """DM 合并 intake：仅感知+入账（含快捷命令/定时任务即时结果），不生成。
        Returns: (RespondContext | None, direct_text | None)"""
        return await self._ingest_phase(message)

    async def respond_cross_platform(self, ctx: "RespondContext", turn_handle=None) -> Optional[str]:
        """DM 合并 worker：对已入账上下文生成回复（turn_handle 提供提交闸门）。"""
        return await self._respond_phase(ctx, turn_handle=turn_handle)
```

- [ ] **Step 4: 运行新测试 + 既有回归**

Run: `uv run pytest tests/unit/hub/ tests/unit/webapi tests/unit/core -q -p no:cacheprovider`
Expected: 新测试 PASS；既有测试无回归（`process_perception_cross_platform` 行为不变）。

- [ ] **Step 5: 全量单元基线**

Run: `uv run pytest tests/unit/ -q -p no:cacheprovider`
Expected: 321+ passed（只增不减）

- [ ] **Step 6: 提交**

```bash
git add hub/decision_hub.py tests/unit/hub/test_decision_hub_respond_gate.py
git commit -m "feat: DecisionHub 拆分 ingest/respond 两阶段——DM 合并提交闸门（被替代轮次零副作用）"
```

---

### Task 3: 工具暂停闸门 + BaseTool 只读标记

**Files:**
- Modify: `webnet/ToolNet/registry.py`（`ToolRegistry.execute_tool` 现位于 L116-179；`BaseTool` 基类 L751-773）
- Modify: `webnet/ToolNet/base.py`（兼容层 `BaseTool` L79-143）
- Modify: `webnet/ToolNet/tools/`（只读工具标记，见 Step 3）
- Test: `tests/unit/webnet/test_tool_turn_gate.py`

**Interfaces:**
- Consumes: Task 1 的 `core.turn_context.current_turn_handle()`。
- Produces:
  - `BaseTool.read_only: bool = False`（两个基类定义一致）
  - `ToolRegistry._turn_gate_blocks(tool, handle) -> bool`（纯静态逻辑，便于测试）
  - `TurnHandle.executed_tools: list[str]` 由 `execute_tool` 成功后追加（供草稿观测）

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/webnet/test_tool_turn_gate.py`：

```python
"""工具暂停闸门测试：已替代轮次中，非只读工具必须被跳过（返回说明文本，
不执行）；只读工具与无轮次上下文的路径不受影响。"""
import types

from core.turn_context import turn_handle_var
from webnet.ToolNet.registry import BaseTool, ToolRegistry


class _Handle:
    def __init__(self, superseded: bool):
        self._superseded = superseded
        self.executed_tools = []

    def is_superseded(self) -> bool:
        return self._superseded


class _Tool:
    def __init__(self, name: str, read_only: bool = False):
        self.name = name
        self.read_only = read_only
        self.executed = 0

    async def execute(self, args, context):  # noqa: ARG002
        self.executed += 1
        return "ok"


def test_basetool_default_not_read_only():
    assert getattr(BaseTool, "read_only", None) is False


def test_gate_blocks_mutating_tool_when_superseded():
    reg = ToolRegistry.__new__(ToolRegistry)  # 只测纯逻辑，不经构造器
    handle = _Handle(superseded=True)
    tool = _Tool("qq_send_message", read_only=False)
    assert ToolRegistry._turn_gate_blocks(reg, tool, handle) is True
    assert tool.executed == 0


def test_gate_allows_readonly_tool_when_superseded():
    reg = ToolRegistry.__new__(ToolRegistry)
    tool = _Tool("memory_search", read_only=True)
    assert ToolRegistry._turn_gate_blocks(reg, tool, _Handle(superseded=True)) is False


def test_gate_inactive_without_supersession():
    reg = ToolRegistry.__new__(ToolRegistry)
    tool = _Tool("reminder_create", read_only=False)
    assert ToolRegistry._turn_gate_blocks(reg, tool, _Handle(superseded=False)) is False
    assert ToolRegistry._turn_gate_blocks(reg, tool, None) is False


def test_executed_tools_recorded_via_handle():
    """执行成功的工具名追加到 handle.executed_tools（草稿观测）。"""
    handle = _Handle(superseded=False)
    reg = ToolRegistry.__new__(ToolRegistry)
    ToolRegistry._record_executed_tool(reg, handle, "pc_context")
    assert handle.executed_tools == ["pc_context"]
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/unit/webnet/test_tool_turn_gate.py -q -p no:cacheprovider`
Expected: FAIL —— `read_only` 属性不存在 / `_turn_gate_blocks` 不存在

- [ ] **Step 3: 实现**

3a. 两个 `BaseTool` 定义（`webnet/ToolNet/registry.py:751` 与 `webnet/ToolNet/base.py:79`）各加类属性：

```python
    read_only: bool = False  # True=纯读取（查询/搜索/状态），替代轮次中仍可执行
```

3b. `ToolRegistry` 内新增两个方法（实例方法，便于测试经 `__new__` 裸实例调用）：

```python
    def _turn_gate_blocks(self, tool, handle) -> bool:
        """DM 合并闸门：轮次已被新输入替代时，未标记 read_only 的工具暂停启动。"""
        if handle is None or not handle.is_superseded():
            return False
        return not getattr(tool, "read_only", False)

    def _record_executed_tool(self, handle, tool_name: str) -> None:
        if handle is not None:
            handle.executed_tools.append(tool_name)
```

（相应地，3c 中闸门调用改为 `self._turn_gate_blocks(tool, _turn)`，记录改为 `self._record_executed_tool(_turn, tool_name)`。）

3c. 在 `ToolRegistry.execute_tool`（L116-179）中，**tool 实例解析之后、validate/调用之前**插入：

```python
        # DM 合并：被替代轮次暂停非只读工具（已开始的操作不中断；结果文本回填模型）
        from core.turn_context import current_turn_handle

        _turn = current_turn_handle()
        if self._turn_gate_blocks(tool, _turn):
            logger.info(f"[ToolNet] 轮次已被新输入替代，暂停非只读工具: {tool_name}")
            return f"（用户补充了新输入，本轮为草稿重算中，修改类操作「{tool_name}」已跳过）"
```

并在工具成功执行、返回结果之前追加：

```python
        self._record_executed_tool(self, _turn, tool_name)
```

（若 execute_tool 有多个返回路径，只在实际执行成功的路径上记录；`_turn` 为 None 时 `_record_executed_tool` 自身即为空操作。）

3d. 只读标记首发清单（规则：只读=查询/搜索/读取/状态类；任何发送/创建/删除/修改/提醒/执行类一律保持 False）。执行发现命令并列出全部工具类：

```bash
grep -rn "^class .*(" webnet/ToolNet/tools --include="*.py" | grep -iv base | head -100
```

按下表标记（`read_only = True` 加在类属性区）：

| 类别 | 判定 |
|---|---|
| `mcpserver/pc_tracker` 桥接的 6 个工具（context/daily/processes/current/insights/status） | True |
| 余额查询（balance_query）、系统状态/统计读取类 | True |
| 记忆搜索/读取类（只 get/search，不含 add/delete） | True |
| B 站/网页搜索类 | True |
| QQ 消息发送、群管理、表情、TTS、提醒/定时任务创建、记忆写入/删除、文件写入、代码执行、MCP 写操作适配 | False（默认，不标注） |

标注完成后运行：

```bash
uv run python -c "
from webnet.ToolNet import registry
"
```
Expected: 无 import 错误。

- [ ] **Step 4: 运行测试 + 相关回归**

Run: `uv run pytest tests/unit/webnet tests/unit/platform tests/unit/core -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add webnet/ToolNet/registry.py webnet/ToolNet/base.py webnet/ToolNet/tools tests/unit/webnet/test_tool_turn_gate.py
git commit -m "feat: ToolNet 轮次闸门——被替代 DM 轮次暂停非只读工具 + BaseTool.read_only 标记"
```

---

### Task 4: MessageMixin 感知构建抽取 + ingest 通道

**Files:**
- Modify: `core/unified_platform_impl/message_mixin.py`（`route_to_decision_hub` L171-295）
- Test: `tests/unit/platform/test_mixin_ingest_channel.py`

**Interfaces:**
- Consumes: Task 2 的 `decision_hub.ingest_cross_platform(message) -> (RespondContext|None, direct|None)`。
- Produces:
  - `PlatformMessageMixin._build_perception_message(*, content, user_id, user_name, message_type, group_id, group_name, sender_role, is_at_bot, extra) -> tuple[Any, dict]`
  - `PlatformMessageMixin.ingest_to_decision_hub(...同参...) -> tuple[Any, Optional[str]]` —— 返回 `(respond_ctx|错误文本, direct_text|None)`；用户消息侧 realtime 事件与 `_after_route` 在此触发。

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/platform/test_mixin_ingest_channel.py`：

```python
"""mixin ingest 通道测试：感知构建与 route 完全一致；ingest 不触发回复侧事件。"""
import types

import pytest

import core.unified_permission as perm_mod
from core.unified_platform_impl.message_mixin import PlatformMessageMixin


class _Host(PlatformMessageMixin):
    platform_id = "aiocqhttp"

    def __init__(self):
        self._miya_core = types.SimpleNamespace()
        self.spawned = []

    def _spawn(self, coro):
        self.spawned.append(coro)
        coro.close()  # 不真正运行，防泄漏

    def _emit_realtime_events(self, content, reply, sender_name):
        self.events.append((content, reply))

    def _after_route(self, content, reply, user_id):
        return _noop_after(content)


async def _noop_after(content):
    return None


@pytest.fixture
def host(monkeypatch):
    h = _Host()
    h.events = []
    engine = types.SimpleNamespace(
        is_superadmin=lambda uid, platform: uid == "888",
        is_staff=lambda uid, platform: False,
        _config={"superadmins": {"q": {"name": "然鑫", "ids": {"qq": ["888"]}}}},
    )
    monkeypatch.setattr(perm_mod, "get_permission_engine", lambda: engine)
    return h


@pytest.mark.asyncio
async def test_build_perception_matches_route_shape(host):
    msg, perception = await host._build_perception_message(
        content="你好", user_id="888", user_name="然鑫", message_type="private",
        group_id="", group_name="", sender_role="member", is_at_bot=True, extra=None,
    )
    assert perception["is_owner"] is True
    assert perception["user_id"] == "888"  # 规范 ID 回填
    assert perception["unified_user_id"] == "aiocqhttp_888"
    assert msg.content is perception


@pytest.mark.asyncio
async def test_ingest_channel_calls_decision_hub_ingest_and_emits_user_event(host):
    captured = {}

    def fake_dh():
        async def ingest(message):
            captured["msg"] = message
            return ("CTX", None)

        return types.SimpleNamespace(ingest_cross_platform=ingest)

    host._miya_core = types.SimpleNamespace(decision_hub=types.SimpleNamespace(
        ingest_cross_platform=fake_dh().__getattribute__("ingest_cross_platform")))
    ctx, direct = await host.ingest_to_decision_hub(
        content="在吗", user_id="u1", user_name="小明", message_type="private",
        group_id="", group_name="", sender_role="member", is_at_bot=True, extra=None,
    )
    assert ctx == "CTX" and direct is None
    assert host.events == [(("在吗", ""),)]  # 只发用户消息侧事件，无助手回复事件
    assert len(host.spawned) == 1  # _after_route 已安排


@pytest.mark.asyncio
async def test_ingest_channel_not_ready_returns_error_text(host):
    host._miya_core = None
    ctx, direct = await host.ingest_to_decision_hub(
        content="hi", user_id="u1", user_name="", message_type="private",
        group_id="", group_name="", sender_role="member", is_at_bot=True, extra=None,
    )
    assert ctx == "弥娅系统未就绪" and direct is None
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/unit/platform/test_mixin_ingest_channel.py -q -p no:cacheprovider`
Expected: FAIL —— `_build_perception_message` / `ingest_to_decision_hub` 不存在

- [ ] **Step 3: 实现 message_mixin.py**

3a. 将 `route_to_decision_hub` 中 **L204-273**（`try:` 之后到构造 `mlink_msg` 为止：perception_data 构建 + 权限注入 + extra 合并 + Message 包装）**原样搬入**新方法：

```python
    async def _build_perception_message(
        self, *, content, user_id, user_name, message_type, group_id,
        group_name, sender_role, is_at_bot, extra,
    ):
        """构建 perception dict + M-Link Message（含超管身份注入）。原 route L204-273。"""
        from mlink.message import Message
        ...（原语句逐字搬入，末尾）...
        return mlink_msg, perception_data
```

`route_to_decision_hub` 原位置改为：

```python
        miya = self._miya_core
        if not miya:
            return "弥娅系统未就绪"
        try:
            mlink_msg, _perception = await self._build_perception_message(
                content=content, user_id=user_id, user_name=user_name,
                message_type=message_type, group_id=group_id, group_name=group_name,
                sender_role=sender_role, is_at_bot=is_at_bot, extra=extra,
            )
            if hasattr(miya, "decision_hub"):
                ...（原 L275-289 不变）...
```

3b. 新增 ingest 通道：

```python
    async def ingest_to_decision_hub(
        self, *, content, user_id, user_name, message_type, group_id,
        group_name, sender_role, is_at_bot, extra,
    ):
        """DM 合并 intake：感知构建 + decision_hub 入账（不生成回复）。

        Returns: (respond_ctx | 错误文本, direct_text | None)
        用户消息侧 realtime 事件照发；助手回复事件由 worker 发送后补发。"""
        miya = self._miya_core
        if not miya:
            return "弥娅系统未就绪", None
        try:
            mlink_msg, _perception = await self._build_perception_message(
                content=content, user_id=user_id, user_name=user_name,
                message_type=message_type, group_id=group_id, group_name=group_name,
                sender_role=sender_role, is_at_bot=is_at_bot, extra=extra,
            )
            self._emit_realtime_events(content, "", user_name or user_id)
            outcome = await miya.decision_hub.ingest_cross_platform(mlink_msg)
            self._spawn(self._after_route(content, "", user_id))
            respond_ctx, direct = outcome
            return respond_ctx, direct
        except Exception as e:  # noqa: BLE001 — intake 异常按错误文本上抛给合并器发送
            logger.error(f"[{self.platform_id}] DM ingest 异常: {e}", exc_info=True)
            return f"处理消息时出错了: {e}", None
```

- [ ] **Step 4: 运行测试 + mixin 相关回归**

Run: `uv run pytest tests/unit/platform -q -p no:cacheprovider`
Expected: PASS

- [ ] **Step 5: 提交**

```bash
git add core/unified_platform_impl/message_mixin.py tests/unit/platform/test_mixin_ingest_channel.py
git commit -m "feat: MessageMixin 抽取感知构建 + DM ingest 通道（用户侧事件/after_route 前置）"
```

---

### Task 5: OneBot 平台接线（分发分支 + 三个回调 + 即时命令）

**Files:**
- Modify: `core/unified_platform_impl/onebot_platform.py`（`__init__` 并发原语区 L43-55；`_dispatch_message` L357-370；`_handle_chat_message` 尾部 L926-943）
- Test: `tests/unit/platform/test_dm_route_branch.py`

**Interfaces:**
- Consumes: Task 1 `PrivateChatMerger` / `DmSubmit` / `IngestOutcome`；Task 4 `ingest_to_decision_hub`；Task 2 `respond_cross_platform`。
- Produces:
  - `OneBotPlatform._dm_merger: Optional[PrivateChatMerger]`（config `dm_merge_enabled`，默认 True）
  - `OneBotPlatform._route_chat_response(...) -> None`（私聊走合并器，群聊走原路径）
  - `OneBotPlatform._dm_ingest / _dm_generate / _dm_send` 三个回调

- [ ] **Step 1: 写失败测试**

创建 `tests/unit/platform/test_dm_route_branch.py`：

```python
"""OneBot 私聊合并接线测试：私聊 intake 不取会话锁、并发不串行；
群聊路径保持原并发门；合并轮次端到端只生成一次、只发送一次。"""
import asyncio
import types

import pytest

from core.unified_platform_impl.dm_merger import IngestOutcome
from core.unified_platform_impl.onebot_platform import OneBotPlatform


def _make_platform() -> OneBotPlatform:
    return OneBotPlatform(config={"bot_qq": "10001", "ws_reverse_port": 0, "dm_merge_enabled": True})


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
    data = {"post_type": "message", "message_type": "group", "group_id": "g1",
            "sender": {"user_id": 9}, "message": "x", "raw_message": "x"}
    await p._dispatch_message(data)
    assert order == [("handle", "g1")]
    assert p._dm_merger._states == {}  # 群聊不进合并器


@pytest.mark.asyncio
async def test_route_branch_merges_and_sends_once():
    p = _make_platform()
    calls = {"generate": 0, "send": 0}

    async def ingest(sub):
        return IngestOutcome(respond_ctx={"content": sub.content})

    async def generate(key, batch, handle):
        calls["generate"] += 1
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
    await asyncio.sleep(0.05)
    st = p._dm_merger._states["private:1"]
    await _wait_worker_idle(st)
    assert calls == {"generate": 1, "send": 1}  # 两条输入只生成一次、发送一次


async def _wait_worker_idle(st, timeout=2.0):
    loop = asyncio.get_running_loop()
    deadline = loop.time() + timeout
    while st.worker is not None and not st.worker.done():
        assert loop.time() < deadline
        await asyncio.sleep(0.01)


@pytest.mark.asyncio
async def test_dm_generate_applies_filters_and_uses_respond():
    p = _make_platform()
    seen = {}

    async def respond(ctx, turn_handle=None):
        seen["ctx"] = ctx
        seen["handle"] = turn_handle
        return "答案<think>内部推理残留</think>正文"

    p._miya_core = types.SimpleNamespace(
        decision_hub=types.SimpleNamespace(respond_cross_platform=respond)
    )
    from core.unified_platform_impl.dm_merger import DmPending

    batch = [DmPending(original={}, content="x",
                       respond_ctx=types.SimpleNamespace(content="x"))]
    out = await p._dm_generate("private:1", batch, None)
    assert seen["handle"] is None
    assert "think>" not in out  # _filter_thinking 已应用
    assert "正文" in out


def test_merge_disabled_falls_back():
    p = OneBotPlatform(config={"bot_qq": "10001", "ws_reverse_port": 0, "dm_merge_enabled": False})
    assert p._dm_merger is None
```

- [ ] **Step 2: 运行确认失败**

Run: `uv run pytest tests/unit/platform/test_dm_route_branch.py -q -p no:cacheprovider`
Expected: FAIL —— `_dm_merger` / `_route_chat_response` / `_dm_generate` 不存在

- [ ] **Step 3: 实现 onebot_platform.py**

3a. 模块 import 区新增：

```python
from core.unified_platform_impl.dm_merger import DmSubmit, IngestOutcome, PrivateChatMerger
```

3b. `__init__` 并发原语区（L43-55 附近，`_last_process_time` 之后）新增：

```python
        # 2026-09 DM 合并：私聊连续输入合并器（dm_merge_enabled=false 回退逐条回复）
        self._dm_merge_enabled = bool(self._config_data.get("dm_merge_enabled", True))
        self._dm_merger = (
            PrivateChatMerger(
                ingest_fn=self._dm_ingest,
                generate_fn=self._dm_generate,
                send_fn=self._dm_send,
                generation_semaphore=self._dispatch_semaphore,  # 保留跨会话并发限制
            )
            if self._dm_merge_enabled
            else None
        )
```

3c. `_dispatch_message`（L357-370）改为：

```python
    async def _dispatch_message(self, data: Dict) -> None:
        """消息分发：收包循环只负责入队，此处限流 + 会话串行后处理。

        2026-09 DM 合并：私聊改走合并器 intake（不取会话锁——收到即 bump 版本，
        生成/发送由每用户唯一 worker 串行）；群聊维持原「信号量+会话锁」并发门。"""
        try:
            msg_type = data.get("message_type", "private")
            sender = data.get("sender", {}) or {}
            user_id = str(sender.get("user_id", ""))
            group_id = str(data.get("group_id", ""))
            key = self._conv_key(msg_type, group_id, user_id)
            if self._dm_merger is not None and msg_type == "private":
                await self._handle_onebot_message(data)  # intake 快路径，_route_chat_response 接管
                return
            lock = self._get_conv_lock(key)
            async with self._dispatch_semaphore:
                async with lock:
                    await self._handle_onebot_message(data)
        except Exception as e:  # noqa: BLE001 — 分发层兜底，单条异常不影响后续消息
            logger.error(f"[{self.platform_id}] 消息分发异常: {e}", exc_info=True)
```

3d. `_handle_chat_message` 尾部（原 L926-943 的 route+send 块）替换为：

```python
        # === 16. 路由到决策中心 ===
        await self._route_chat_response(
            data=data, content=content, user_id=user_id, user_name=user_name,
            msg_type=msg_type, group_id_str=group_id_str, group_name=group_name,
            sender_role=sender_role, is_at_bot=is_at_bot, extra=extra, has_media=has_media,
        )
```

（上方原 L924 的 debug 日志保留。）新增方法（放在 `_send_onebot_reply` 之前）：

```python
    async def _route_chat_response(
        self, *, data, content, user_id, user_name, msg_type,
        group_id_str, group_name, sender_role, is_at_bot, extra, has_media,
    ) -> None:
        """私聊 → DM 合并器；群聊/未启用 → 原 route+send 路径（行为不变）。"""
        if self._dm_merger is not None and msg_type == "private":
            await self._dm_merger.submit(
                DmSubmit(
                    key=f"private:{user_id}",
                    original=data,
                    content=content,
                    user_id=user_id,
                    user_name=user_name,
                    sender_role=sender_role,
                    extra=extra,
                )
            )
            return
        response = await self.route_to_decision_hub(
            content=content, user_id=user_id, user_name=user_name,
            message_type=msg_type, group_id=group_id_str, group_name=group_name,
            sender_role=sender_role, is_at_bot=is_at_bot, extra=extra,
        )
        if response:
            await self._send_onebot_reply(data, response)
        elif has_media and not is_at_bot:
            pass
```

3e. 三个回调（放在 `_route_chat_response` 之后）：

```python
    async def _dm_ingest(self, sub: DmSubmit) -> IngestOutcome:
        """合并器回调：感知构建 + decision_hub 入账（含快捷命令/定时任务即时结果）。"""
        respond_ctx, direct = await self.ingest_to_decision_hub(
            content=sub.content, user_id=sub.user_id, user_name=sub.user_name,
            message_type="private", group_id="", group_name="",
            sender_role=sub.sender_role, is_at_bot=True, extra=sub.extra,
        )
        if isinstance(respond_ctx, str):  # mixin 返回的错误文本
            return IngestOutcome(error_text=respond_ctx)
        return IngestOutcome(respond_ctx=respond_ctx, direct_text=direct)

    async def _dm_generate(self, key, batch, handle):
        """合并器回调：对快照 batch 生成回复（最新一条为触发消息）。

        合并批次说明注入 content 头部（ingest 已入账的记忆不受影响），
        模型据此统一回应全部未回复消息。"""
        last = batch[-1]
        ctx = last.respond_ctx
        if ctx is None:
            raise RuntimeError("无待回复上下文")
        if len(batch) > 1:
            ctx.content = (
                f"【合并回复】用户连续发来了 {len(batch)} 条消息，请统一回应全部内容：\n"
                + "\n".join(f"- {p.content}" for p in batch[:-1])
                + f"\n- {last.content}\n\n"
                + ctx.content
            )
        response = await self._miya_core.decision_hub.respond_cross_platform(ctx, turn_handle=handle)
        if response:
            response = self._filter_thinking(response)
            response = self._filter_output(response)
        return response

    async def _dm_send(self, key, batch, text) -> bool:
        """合并器回调：发送已提交轮次（文字/语音分条 + 助手侧 realtime 事件 + 本地 TTS）。"""
        if not text:
            return False
        last_original = batch[-1].original
        await self._send_onebot_reply(last_original, text)
        self._emit_realtime_events("", text, "弥娅")
        if self._tts_should_local():
            self._spawn(self._tts_play_response(text))
        return True
```

- [ ] **Step 4: 运行测试 + 平台全量回归**

Run: `uv run pytest tests/unit/platform -q -p no:cacheprovider && uv run pytest tests/unit/ -q -p no:cacheprovider`
Expected: PASS；全量 321+新增 全绿。

- [ ] **Step 5: ruff + 吞噬不变量检查**

Run: `uv run ruff check core/unified_platform_impl/ hub/ webnet/ToolNet/ core/turn_context.py && python scripts/check_new_swallowed.py`
Expected: 0 error；新增 except 均带 `# noqa: BLE001 —` 理由。

- [ ] **Step 6: 提交**

```bash
git add core/unified_platform_impl/onebot_platform.py tests/unit/platform/test_dm_route_branch.py
git commit -m "feat: OneBot 私聊接入 DM 合并器——intake 免会话锁 + worker 唯一轮转 + 即时命令旁路"
```

---

### Task 6: 配置开关、文档与全量验收

**Files:**
- Modify: `config/qq_config.example.yaml`（追加开关，带注释）
- Modify: `docs/PROJECT_STATUS_20260926.md`（待办表新增一行）
- Modify: `README.md`（核心特性无需改动；不加营销性描述，仅 docs 记录）

**Interfaces:** 无代码接口；运维开关 `dm_merge_enabled`（默认 true）。

- [ ] **Step 1: 配置示例追加**

在 `config/qq_config.example.yaml` 的顶层配置区追加：

```yaml
# 私聊连续输入合并（2026-09-28）：同一用户连续消息合并为一轮回复；
# 生成期间收到新消息自动重算，发送期间新消息排入下一轮。false 回退逐条回复。
dm_merge_enabled: true
```

- [ ] **Step 2: 文档更新**

`docs/PROJECT_STATUS_20260926.md` 第 6 节表格追加一行：

```markdown
| DM 私聊输入合并 | 📋 已实施待线上验收 | 行为：连续消息合并一轮回复；草稿轮不发送/不写记忆；非只读工具在替代轮次暂停。设计：`docs/superpowers/plans/2026-09-28-qq-private-input-merge.md`；验收点：连续输入/生成中新输入/发送中新输入/多用户隔离/群聊不变 |
```

- [ ] **Step 3: 全量验收**

```bash
uv run pytest tests/unit/ -q -p no:cacheprovider   # Expected: 全绿（321+新增）
uv run ruff check .                                # Expected: 0 error
python scripts/check_new_swallowed.py              # Expected: PASS
python scripts/doctor.py                            # Expected: FAIL=0
uv run python scripts/import_graph.py --check      # Expected: PASS（无新增环）
```

- [ ] **Step 4: 提交**

```bash
git add config/qq_config.example.yaml docs/PROJECT_STATUS_20260926.md
git commit -m "docs: DM 私聊输入合并——配置开关示例与项目状态记录"
```

---

## 方案与规格的逐条对照（自审记录）

| 规格条目 | 落点 |
|---|---|
| 第一条立即触发、不加等待 | Task 1 `submit()` 版本自增+入队即拉起 worker；intake 无锁无量 |
| 思考期间新输入→草稿+重算 | Task 1 worker `committed=False` 分支；Task 2 闸门跳过副作用 |
| 重复直到无新增 | Task 1 `_run_chat` while 循环 |
| 开始发送后本轮发完、新输入下一轮 | Task 1 `try_commit` 原子置位；sending 期间 intake 仅入队 |
| 分条发送允许 | Task 5 `_dm_send` 复用 `_send_onebot_reply`（`_split_message`） |
| 每私聊一任务、版本即时更新不等锁 | Task 5 `_dispatch_message` 私聊分支免会话锁 |
| 原子提交检查 | Task 1 `try_commit` 持锁无内部 await |
| 原始消息按序保留（图片/文件/引用） | Task 4 感知构建复用（图片分析在 ingest，L908-976 原逻辑不动）；Task 5 `_dm_generate` 批次清单注入 |
| 每条输入只记录一次 | ingest 入账一次；worker 不重复调 ingest |
| 草稿不作为正式助手消息 | Task 2 被替代分支零副作用（记忆/工作记忆/Historian 全跳过） |
| 轮次状态传决策中心/客户端/工具路径 | contextvar `turn_handle_var`（Task 1/3），沿用 `_tool_context_var` 先例 |
| 保留跨会话并发限制 | worker 生成复用 `_dispatch_semaphore`（Task 5 3b） |
| 替代轮次不发文字/语音/表情/桌面事件 | 文字：worker 只在 committed 后 send；语音/表情：闸门在响应生成后、`_handle_proactive_chat`/`_handle_smart_emoji`/`_send_voice_reply` 之前返回；桌面：`_emit_realtime_events` 助手侧只在 `_dm_send` 发生 |
| 替代后只读可继续、非只读暂停 | Task 3 闸门（默认暂停，`read_only=True` 例外） |
| 已开始操作不中断、结果供下轮 | 闸门只在启动前拦截；`TurnHandle.executed_tools` 记录 + `st.draft_tools` 留存（日志可查） |
| 已知限制（如实记录） | 草稿回答内容不注入下一轮提示词（避免自我条件化与提示膨胀）；拍一拍 AI 路径维持原样（15s 冷却，与合并器并发窗口极小）——两者在 PROJECT_STATUS 验收行中注明 |
| 连续补充持续推迟回答（默认边界） | 属预期行为，无需代码 |
| 测试矩阵（连续输入/生成中新输入/发送中新输入/多用户/群聊不变/草稿零泄漏/工具不重复执行） | Task 1 七个时序测试 + Task 2 副作用零断言 + Task 3 闸门测试 + Task 5 接线测试 |
| 沿用超时/重试、过期错误不输出、最新失败提示一次 | Task 1 `gen_error` 分支；无新增超时重试 |
| 发送失败停止剩余分条 | 现有 `onebot_platform.py:981-983` break + Task 1 `_safe_send` 记录 `last_send_error` |

## 已知风险与实施注意

1. **`_ingest_phase` 搬移是纯机械操作**：L822-1130 语句逐字移动，只允许按映射表改 return；任何"顺手重构"都会破坏群聊/终端回归。
2. **`decision_hub.py:2067` 的共享 `tool_context` 实例写入是既有并发窗口**（contextvar 已缓解），合并器不加剧也不修复它——不在本计划范围内。
3. **拍一拍路径**（`_route_with_conv_lock`）继续走锁+route：与合并轮次存在理论并发，靠 15s 冷却压制；如线上出现串扰再收编进合并器。
4. **群临时会话**（`message_type != "group"` 但带 group_id）按私聊合并处理，`_conv_key` 既有语义一致（`onebot_platform.py:340-345`）。
5. **worker 崩溃兜底**：`_run_chat` 外层若被取消（如平台关闭），`finally` 未包住的状态残留由下一条消息 `submit` 的 `worker.done()` 检查自愈；平台 `ashutdown` 关闭链无需改动（worker 是平台内部任务，随事件循环终止）。

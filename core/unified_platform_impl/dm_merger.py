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
    draft_tools: List[str] = field(default_factory=list)  # 被替代轮次已执行的工具名
    ingesting: int = 0  # 在途 ingest 计数（图片分析可能秒级）
    last_send_error: Optional[str] = None


class TurnHandle:
    """一轮生成的提交凭证：worker 创建（快照版本号），decision_hub 生成后调用
    try_commit() 提交；工具层经 contextvar 读取以判断轮次是否已被替代。"""

    __slots__ = ("_merger", "_key", "snapshot_version", "committed", "executed_tools")

    def __init__(self, merger: PrivateChatMerger, key: str, snapshot_version: int):
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
            await self._safe_send(
                sub.key,
                [DmPending(original=sub.original, content=sub.content, respond_ctx=None)],
                outcome.error_text,
            )
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

            if gen_error is not None:
                # 生成失败：过期轮次静默；最新轮次仅发送一次失败提示
                if handle.is_superseded():
                    logger.info(f"[DM合并] 过期轮次生成失败（静默，不输出）: {gen_error}")
                else:
                    logger.error(f"[DM合并] 最新轮次生成失败: {gen_error}", exc_info=True)
                    await self._safe_send(key, batch, self._failure_hint)
                async with st.lock:
                    st.status = "idle"  # 循环回顶：有新输入则下一轮，否则退出
                continue

            if not handle.committed:
                # 生成正常完成但提交未通过 = 生成期间收到新输入
                async with st.lock:
                    st.draft = response
                    st.draft_tools = list(handle.executed_tools)
                    st.status = "idle"  # 立即进入下一轮重算
                logger.info(
                    f"[DM合并] 轮次#{handle.snapshot_version} 被新输入替代，"
                    f"回答保留为草稿并重算（已执行工具: {handle.executed_tools or '无'}）"
                )
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
                logger.warning(
                    f"[DM合并] 等待在途输入入账超时（{self.drain_timeout:.0f}s），按已就绪输入继续"
                )
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

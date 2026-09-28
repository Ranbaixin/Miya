"""QQ 私聊连续输入合并器（DM Merge，2026-09-28 方案 / 09-29 修复版）。

行为契约（修复版）：
- 登记先行：平台完成黑白名单过滤后立即登记消息（占位 + 递增序号 + 版本自增），
  图片分析、引用查询等慢操作在准备任务中异步执行；按 OneBot 消息 ID 去重，
  重复事件不触发重算。
- 按序处理：每位用户按接收顺序入账（用户记忆按 A→B 排列），每条只入账一次；
  单条准备超时（默认 30s）标记失败，后续项不越过未完成项改变顺序，
  其他有效输入继续参与综合。
- 失败统一出口：模型异常与模型返回的错误文本同路——原子检查版本，
  过期静默重算，最新仅发送一次提示并结束本轮批次；后来输入留给下一轮。
- 发送阶段划分：模型回答、输出过滤、语音合成均在提交前完成；首次发送请求
  发起前原子检查版本进入 sending；此后新输入进入下一轮。
- 发送确认：send_fn 返回 SendResult（等 NapCat echo）；commit_fn 按
  实际发送结果写正式记忆——完整才写全文，部分只写确认片段，失败/超时
  不把回复标记为已送达。
- 草稿上下文：每轮生成使用新 DraftContext 副本（草稿回复 + 本批工具记录），
  重算期间工具记录累计，批次结束清理；工具层可复用同批次内已执行结果。
- 清理：worker 使用 finally 清理状态；shutdown() 取消全部任务供平台关闭调用。
"""
from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional

from core.turn_context import DraftContext, draft_context_var, turn_handle_var

logger = logging.getLogger(__name__)


# ==================== 数据结构 ====================


@dataclass
class DmSubmit:
    """平台层递交给合并器的登记请求（收到即登记，不做慢操作）。"""

    key: str  # 会话键，如 "private:12345"
    original: dict  # OneBot 原始事件
    msg_id: str  # OneBot 消息 ID（去重键）
    raw_content: Any = ""  # 平台解析的原始 content（str 或 list）
    user_id: str = ""
    user_name: str = ""
    sender_role: str = "member"
    extra: Optional[dict] = None  # 消息骨架 extra（图片 URL / 引用 ID 等，供准备用）


@dataclass
class PreparedInput:
    """prepare_fn 的产物：准备完成后的输入内容。"""

    content: str
    extra: Optional[dict] = None  # 增强后的 extra（含 image_analysis 等）


@dataclass
class IngestOutcome:
    """ingest_fn 的结果：待回复上下文 / 即时命令结果 / 错误文本（三选一）。"""

    respond_ctx: Any = None  # decision_hub.RespondContext，None=无需模型回复
    direct_text: Optional[str] = None  # 快捷命令/定时任务即时结果，不参与合并
    error_text: Optional[str] = None  # 系统未就绪等文本，立即原样发送


@dataclass
class GenerateOutcome:
    """generate_fn 的产物：回答文本 + 发送确认后才提交的待落库数据。"""

    response: str = ""
    artifacts: Any = None  # decision_hub 侧 GeneratedArtifacts / 待提交包
    is_error: bool = False  # True=模型返回的是错误文本（走失败出口）
    audio_path: Optional[str] = None  # synth 后由 worker 回填（post_send 本地播放用）


@dataclass
class SynthOutcome:
    """synth_fn 的产物：提交前完成的发送准备（文本过滤 + 语音合成）。"""

    send_text: str = ""
    audio_path: Optional[str] = None  # None=文字模式


@dataclass
class SendResult:
    """send_fn 的产物：分条发送的确认结果（NapCat echo 确认，非阅读回执）。"""

    status: str = "failed"  # sent | partial | failed | timeout
    message_ids: List[Any] = field(default_factory=list)  # 确认成功的消息 ID
    sent_chunks: List[str] = field(default_factory=list)  # 确认成功的片段
    error: Optional[str] = None

    @property
    def delivered_text(self) -> str:
        """已确认送达的文本（部分发送只含确认片段）。"""
        return "".join(self.sent_chunks)

    @property
    def fully_sent(self) -> bool:
        return self.status == "sent"


@dataclass
class DmInput:
    """一位用户输入队列中的单条消息（占位 → 准备 → 入账）。"""

    seq: int  # 会话内递增序号（接收顺序）
    msg_id: str  # OneBot 消息 ID
    original: dict
    raw_content: Any
    user_id: str
    user_name: str = ""
    sender_role: str = "member"
    extra: Optional[dict] = None
    status: str = "preparing"  # preparing | ready | failed
    content: str = ""  # 准备完成后补齐
    ready_extra: Optional[dict] = None
    ingest_done: bool = False  # 已入账（每条只入账一次）
    respond_ctx: Any = None  # 入账产物
    direct_text: Optional[str] = None  # 快捷命令即时结果（已发送，不参与综合）
    direct_done: bool = False
    prep_error: Optional[str] = None


@dataclass
class DmMergeState:
    lock: asyncio.Lock = field(default_factory=asyncio.Lock)
    inputs: List[DmInput] = field(default_factory=list)
    seen_msg_ids: Dict[str, bool] = field(default_factory=dict)  # 去重表（FIFO 裁剪）
    version: int = 0  # 收到新输入即自增（登记时）
    next_seq: int = 0
    status: str = "idle"  # idle | thinking | sending
    worker: Optional[asyncio.Task] = None
    tasks: List[asyncio.Task] = field(default_factory=list)  # 准备任务等（shutdown 时取消）
    last_draft_reply: Optional[str] = None  # 最近被替代未发送回答（跨轮传递）
    batch_tool_records: List[Any] = field(default_factory=list)  # 本批次工具执行记录（跨轮累计）
    last_send_error: Optional[str] = None

    def remember_msg_id(self, msg_id: str) -> None:
        self.seen_msg_ids[msg_id] = True
        while len(self.seen_msg_ids) > 200:
            self.seen_msg_ids.pop(next(iter(self.seen_msg_ids)), None)


class TurnHandle:
    """一轮回复的提交凭证：worker 创建（快照版本号），发送前 try_commit()；
    工具层经 contextvar 读取以判断轮次是否已被替代。"""

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
        """原子提交：版本一致 → status=sending + 标记快照输入已消费，返回 True；
        版本不一致（生成/合成期间收到新输入）→ 返回 False。
        检查与置位之间持锁且无内部 await——满足「不得插入」约束。"""
        st = self._merger._states.get(self._key)
        if st is None:
            return False
        async with st.lock:
            if st.version != self.snapshot_version:
                return False
            st.status = "sending"
            self.committed = True
            return True


# ==================== 合并器 ====================


class PrivateChatMerger:
    """每私聊一状态机的合并编排核心。平台相关逻辑全部经回调注入，
    本类保持纯 asyncio、可独立单测。"""

    def __init__(
        self,
        *,
        prepare_fn: Callable[[DmSubmit], Awaitable[PreparedInput]],
        ingest_fn: Callable[[DmInput], Awaitable[IngestOutcome]],
        generate_fn: Callable[[str, List[DmInput], TurnHandle, DraftContext], Awaitable[GenerateOutcome]],
        synth_fn: Callable[[List[DmInput], str], Awaitable[SynthOutcome]],
        send_fn: Callable[[str, List[DmInput], str, Optional[str]], Awaitable[SendResult]],
        commit_fn: Optional[Callable[[Any, SendResult], Awaitable[None]]] = None,
        post_send_fn: Optional[Callable[[str, List[DmInput], SendResult, GenerateOutcome], Awaitable[None]]] = None,
        generation_semaphore: Optional[asyncio.Semaphore] = None,
        prepare_timeout: float = 30.0,
        failure_hint: str = "（刚才回复时出了点小差错，请再发一次试试~）",
    ):
        self._prepare_fn = prepare_fn
        self._ingest_fn = ingest_fn
        self._generate_fn = generate_fn
        self._synth_fn = synth_fn
        self._send_fn = send_fn
        self._commit_fn = commit_fn
        self._post_send_fn = post_send_fn
        self._gen_sem = generation_semaphore or asyncio.Semaphore(4)
        self.prepare_timeout = prepare_timeout
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

    # ---------- 登记入口 ----------

    async def register(self, sub: DmSubmit) -> None:
        """私聊消息登记入口：去重 → 占位（序号+版本）→ 拉起准备任务与 worker。
        不做任何慢操作——图片/引用分析由 _prepare_task 异步完成。"""
        st = await self._state_for(sub.key)
        async with st.lock:
            if sub.msg_id and sub.msg_id in st.seen_msg_ids:
                dup = True
            else:
                dup = False
                if sub.msg_id:
                    st.remember_msg_id(sub.msg_id)
                st.version += 1
                st.next_seq += 1
                inp = DmInput(
                    seq=st.next_seq,
                    msg_id=sub.msg_id,
                    original=sub.original,
                    raw_content=sub.raw_content,
                    user_id=sub.user_id,
                    user_name=sub.user_name,
                    sender_role=sub.sender_role,
                    extra=sub.extra,
                )
                st.inputs.append(inp)
        if dup:
            logger.debug(f"[DM合并] 重复事件忽略 msg_id={sub.msg_id} key={sub.key}")
            return
        prep_task = asyncio.create_task(self._prepare_task(sub.key, st, inp))
        async with st.lock:
            st.tasks.append(prep_task)
            if st.worker is None or st.worker.done():
                st.worker = asyncio.create_task(self._run_chat(sub.key))
                st.worker.add_done_callback(lambda t: self._worker_done(sub.key, t))

    def _worker_done(self, key: str, task: asyncio.Task) -> None:
        """worker 真实结束后的同步回调：清引用；若队列仍有积压则补拉新 worker，
        消除「register 判 done=False → worker 随后退出」的丢唤醒窗口。"""
        st = self._states.get(key)
        if st is None:
            return
        if st.worker is task:
            st.worker = None
        if st.inputs and (st.worker is None or st.worker.done()):
            st.worker = asyncio.create_task(self._run_chat(key))
            st.worker.add_done_callback(lambda t: self._worker_done(key, t))

    async def _prepare_task(self, key: str, st: DmMergeState, inp: DmInput) -> None:
        """单条输入准备：内容补齐（图片分析/引用查询在平台回调内），超时标记失败。"""
        sub = DmSubmit(
            key=key,
            original=inp.original,
            msg_id=inp.msg_id,
            raw_content=inp.raw_content,
            user_id=inp.user_id,
            user_name=inp.user_name,
            sender_role=inp.sender_role,
            extra=inp.extra,
        )
        try:
            prepared = await asyncio.wait_for(self._prepare_fn(sub), timeout=self.prepare_timeout)
            async with st.lock:
                inp.status = "ready"
                inp.content = prepared.content
                inp.ready_extra = prepared.extra
        except asyncio.TimeoutError:
            async with st.lock:
                inp.status = "failed"
                inp.prep_error = f"准备超时（>{self.prepare_timeout:.0f}s）"
            logger.warning(f"[DM合并] 输入准备超时标记失败 seq={inp.seq} key={key}")
        except asyncio.CancelledError:
            async with st.lock:
                inp.status = "failed"
                inp.prep_error = "准备任务取消"
            raise
        except Exception as e:  # noqa: BLE001 — 单条准备失败不影响其他输入参与综合
            async with st.lock:
                inp.status = "failed"
                inp.prep_error = str(e)
            logger.warning(f"[DM合并] 输入准备失败 seq={inp.seq} key={key}: {e}")

    # ---------- worker 主循环 ----------

    async def _run_chat(self, key: str) -> None:
        """该私聊的唯一处理任务：稳定等待+按序入账 → 生成 → 失败出口 →
        合成 → 提交闸门 → 发送确认 → 按结果提交记忆 → 批次清理。"""
        st = self._states.get(key)
        assert st is not None
        try:
            while True:
                async with st.lock:
                    if not st.inputs:
                        st.status = "idle"
                        return
                    st.status = "thinking"
                await self._settle_and_ingest(key, st)

                batch = [
                    i
                    for i in st.inputs
                    if i.status != "failed" and i.respond_ctx is not None
                ]
                if not batch:
                    await self._consume(key, [])  # 清理失败/直发项
                    async with st.lock:
                        st.status = "idle"
                    continue

                handle = TurnHandle(self, key, st.version)
                draft_ctx = DraftContext(draft_reply=st.last_draft_reply)
                draft_ctx.tool_records = list(st.batch_tool_records)

                outcome: Optional[GenerateOutcome] = None
                gen_error: Optional[BaseException] = None
                th = turn_handle_var.set(handle)
                dh = draft_context_var.set(draft_ctx)
                try:
                    async with self._gen_sem:  # 保留现有跨会话并发限制
                        outcome = await self._generate_fn(key, batch, handle, draft_ctx)
                except Exception as e:  # noqa: BLE001 — 生成失败走统一出口，不冒泡
                    gen_error = e
                finally:
                    draft_context_var.reset(dh)
                    turn_handle_var.reset(th)

                st.batch_tool_records = list(draft_ctx.tool_records)

                if gen_error is not None or outcome is None or outcome.is_error:
                    await self._failure_exit(key, st, handle, batch, gen_error, outcome)
                    continue

                # 合成在提交前完成（输出过滤在 generate_fn 内已完成）
                synth = await self._synth_safe(batch, outcome.response)
                outcome.audio_path = synth.audio_path

                # 提交闸门：首次发送请求发起前的原子检查
                committed = await handle.try_commit()
                if not committed:
                    async with st.lock:
                        st.last_draft_reply = outcome.response
                        st.status = "idle"  # 立即进入下一轮重算
                    logger.info(
                        f"[DM合并] 轮次#{handle.snapshot_version} 生成/合成期间收到新输入，"
                        f"转为草稿重算（累计工具记录 {len(st.batch_tool_records)} 条）"
                    )
                    continue

                send_result = await self._send_safe(key, batch, synth)
                if self._commit_fn is not None:
                    try:
                        await self._commit_fn(outcome.artifacts, send_result)
                    except Exception as e:  # noqa: BLE001 — 记忆提交失败不影响发送结果，留日志排查
                        logger.error(f"[DM合并] 正式记忆提交失败 key={key}: {e}", exc_info=True)
                if self._post_send_fn is not None:
                    try:
                        await self._post_send_fn(key, batch, send_result, outcome)
                    except Exception as e:  # noqa: BLE001 — 附加输出失败不重发主回复、不另起轮次
                        logger.warning(f"[DM合并] 附加输出失败（不重发主回复）key={key}: {e}")

                await self._consume(key, batch)
                async with st.lock:
                    st.last_draft_reply = None
                    st.batch_tool_records = []  # 批次结束即清理
                    st.status = "idle"
        except asyncio.CancelledError:
            raise
        except Exception as e:  # noqa: BLE001 — worker 兜底：日志留痕后退出，状态下一条消息自愈
            logger.error(f"[DM合并] worker 异常退出 key={key}: {e}", exc_info=True)
        finally:
            async with st.lock:
                st.status = "idle"
                if st.worker is not None and st.worker.done():
                    st.worker = None

    async def _settle_and_ingest(self, key: str, st: DmMergeState) -> None:
        """稳定等待：所有输入 preparing 结束且按 seq 顺序全部入账。
        入账在 worker 内串行执行——用户记忆严格按 A→B 排列，每条只入账一次。
        快捷命令/错误文本的即时结果在此直接发送（不经生成）。"""
        loop = asyncio.get_running_loop()
        deadline = loop.time() + self.prepare_timeout + 30.0
        while True:
            target: Optional[DmInput] = None
            preparing = False
            async with st.lock:
                # 失败项不阻塞队列：直接从待处理集中排除（由 _consume 清理）
                undone = [
                    i
                    for i in st.inputs
                    if not i.ingest_done and not i.direct_done and i.status != "failed"
                ]
                if undone:
                    first = min(undone, key=lambda i: i.seq)
                    if first.status == "ready":
                        target = first
                    else:  # 队首仍在准备——后续项不得越过（按序原则）
                        preparing = True
            if target is not None:
                outcome = await self._ingest_fn(target)
                async with st.lock:
                    target.ingest_done = True
                    if outcome.error_text or outcome.direct_text:
                        target.direct_text = outcome.error_text or outcome.direct_text
                    else:
                        target.respond_ctx = outcome.respond_ctx
                text = outcome.error_text or outcome.direct_text
                if text:
                    await self._send_safe(
                        key, [target], SynthOutcome(send_text=text, audio_path=None)
                    )
                    async with st.lock:
                        target.direct_done = True
                continue
            async with st.lock:
                remaining = [
                    i
                    for i in st.inputs
                    if not i.ingest_done and not i.direct_done and i.status != "failed"
                ]
                if not remaining and not preparing:
                    return
            if loop.time() > deadline:
                logger.warning(f"[DM合并] 稳定等待超时，按已就绪输入继续 key={key}")
                return
            await asyncio.sleep(0.05)

    async def _failure_exit(
        self,
        key: str,
        st: DmMergeState,
        handle: TurnHandle,
        batch: List[DmInput],
        gen_error: Optional[BaseException],
        outcome: Optional[GenerateOutcome],
    ) -> None:
        """统一失败出口：原子检查版本——过期静默重算；最新仅发送一次提示并结束本轮批次。"""
        if handle.is_superseded():
            logger.info(
                f"[DM合并] 过期轮次失败（静默，不输出）: {gen_error or (outcome.response if outcome else '')}"
            )
            return  # batch 留给下一轮重算
        detail = str(gen_error) if gen_error else (outcome.response if outcome else "未知错误")
        logger.error(f"[DM合并] 最新轮次生成失败: {detail}", exc_info=gen_error is not None)
        await self._send_safe(key, [batch[-1]], SynthOutcome(send_text=self._failure_hint, audio_path=None))
        await self._consume(key, batch)  # 结束本轮输入批次；后来输入留给下一轮

    async def _consume(self, key: str, batch: List[DmInput]) -> None:
        """从队列移除已消费项（batch + 失败项 + 直发项）。"""
        st = self._states.get(key)
        if st is None:
            return
        consumed = set(id(i) for i in batch)
        async with st.lock:
            st.inputs = [
                i
                for i in st.inputs
                if id(i) not in consumed and i.status != "failed" and not i.direct_done
            ]

    # ---------- 安全包装 ----------

    async def _synth_safe(self, batch: List[DmInput], response: str) -> SynthOutcome:
        try:
            return await self._synth_fn(batch, response)
        except Exception as e:  # noqa: BLE001 — 合成失败回退纯文本，不阻断发送
            logger.warning(f"[DM合并] 合成失败回退文字: {e}")
            return SynthOutcome(send_text=response, audio_path=None)

    async def _send_safe(self, key: str, batch: List[DmInput], synth: SynthOutcome) -> SendResult:
        try:
            result = await self._send_fn(key, batch, synth.send_text, synth.audio_path)
            if not isinstance(result, SendResult):
                result = SendResult(status="sent" if result else "failed")
            if result.status != "sent":
                st = self._states.get(key)
                if st is not None:
                    async with st.lock:
                        st.last_send_error = result.error or result.status
            return result
        except Exception as e:  # noqa: BLE001 — 发送异常不重发已发送内容，只记录
            logger.error(f"[DM合并] 发送异常（不重发已发送内容）: {e}")
            st = self._states.get(key)
            if st is not None:
                async with st.lock:
                    st.last_send_error = str(e)
            return SendResult(status="failed", error=str(e))

    # ---------- 关闭清理 ----------

    async def shutdown(self) -> None:
        """平台关闭时调用：取消全部 worker 与准备任务并等待退出。"""
        tasks: List[asyncio.Task] = []
        async with self._states_guard:
            for st in self._states.values():
                for t in ([st.worker] if st.worker else []) + list(st.tasks):
                    if t is not None and not t.done():
                        tasks.append(t)
                st.tasks.clear()
        for t in tasks:
            t.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        async with self._states_guard:
            for st in self._states.values():
                st.worker = None
                st.inputs.clear()
                st.status = "idle"

"""
消息汇总窗口期管理器

在群聊消息密集时，收集一段时间内的消息再统一处理，
避免消息过快导致 AI 回复不过来。

策略：
- 第1条消息：立即处理（不等待）
- 第2条消息在 N 秒内到达：开始窗口期，收集后续消息
- 窗口期内收到新消息：重置计时器
- 窗口期结束：批量处理所有收集的消息
"""

import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class QueuedMessage:
    """队列中的消息"""

    timestamp: float
    user_id: str
    sender_name: str
    content: Any
    message_type: str
    group_id: Optional[str] = None
    is_at_bot: bool = False
    raw_event: Optional[dict] = None


@dataclass
class BatchWindow:
    """一个汇总窗口"""

    group_key: str
    messages: List[QueuedMessage] = field(default_factory=list)
    timer_task: Optional[asyncio.Task] = None
    is_active: bool = False
    is_flushing: bool = False  # 防止重复刷新
    window_start: float = 0.0
    last_reset: float = 0.0
    processed_message_ids: set = field(default_factory=set)  # 已处理消息ID去重


class MessageBatcher:
    """
    消息汇总窗口期管理器

    工作原理：
    1. 第1条消息：立即返回处理（不等待）
    2. 第2条消息在 cooldown 秒内到达：进入收集模式，两条消息都加入队列
    3. 收集模式下收到新消息：重置计时器
    4. 窗口期结束：批量处理所有收集的消息
    """

    def __init__(
        self,
        window_seconds: float = 8.0,
        max_window_seconds: float = 15.0,
        max_messages: int = 20,
        only_group: bool = True,
        status_message: str = "",
        send_status_callback: Optional[Any] = None,
        cooldown_seconds: float = 3.0,  # 两条消息间隔小于此时长才触发窗口期
    ):
        self.window_seconds = window_seconds
        self.max_window_seconds = max_window_seconds
        self.max_messages = max_messages
        self.only_group = only_group
        self.status_message = status_message
        self.send_status_callback = send_status_callback
        self.cooldown_seconds = cooldown_seconds

        # 输出队列：(group_key, batch_messages)
        self.output_queue: asyncio.Queue = asyncio.Queue()

        # 窗口队列：group_key -> BatchWindow
        self._windows: Dict[str, BatchWindow] = {}
        self._lock = asyncio.Lock()
        self._status_sent: Dict[str, bool] = {}
        self._last_message_time: Dict[str, float] = {}  # 上次消息时间

    def _get_group_key(
        self, message_type: str, group_id: Optional[str], user_id: str
    ) -> str:
        """生成窗口分组键"""
        if message_type == "group" and group_id:
            return f"group_{group_id}"
        return f"private_{user_id}"

    async def submit_message(
        self,
        message_type: str,
        group_id: Optional[str],
        user_id: str,
        sender_name: str,
        content: Any,
        is_at_bot: bool = False,
        raw_event: Optional[dict] = None,
    ) -> bool:
        """
        提交消息到窗口队列

        Returns:
            True: 消息已加入窗口队列，等待窗口期结束
            False: 消息应立即处理
        """
        group_key = self._get_group_key(message_type, group_id, user_id)

        # 私聊或禁用窗口期时，直接处理
        if self.only_group and message_type != "group":
            return False

        now = time.time()

        async with self._lock:
            # 获取或创建窗口
            if group_key not in self._windows:
                self._windows[group_key] = BatchWindow(
                    group_key=group_key,
                    window_start=now,
                    last_reset=now,
                )
                self._status_sent[group_key] = False

            window = self._windows[group_key]
            last_time = self._last_message_time.get(group_key, 0)
            self._last_message_time[group_key] = now

            msg = QueuedMessage(
                timestamp=now,
                user_id=user_id,
                sender_name=sender_name,
                content=content,
                message_type=message_type,
                group_id=group_id,
                is_at_bot=is_at_bot,
                raw_event=raw_event,
            )

            # 消息ID去重：从raw_event中提取消息ID
            msg_id = None
            if raw_event:
                msg_id = raw_event.get("message_id") or raw_event.get("message_id")
            if msg_id is None:
                msg_id = f"{user_id}_{now}_{content}"

            # 检查消息是否已处理过
            if msg_id in window.processed_message_ids:
                logger.info(f"[消息汇总] 消息已处理过，跳过: msg_id={msg_id}")
                return False

            # 如果窗口正在活跃收集模式中
            if window.is_active:
                window.messages.append(msg)
                window.processed_message_ids.add(msg_id)
                return True

            # 先加入当前消息，再检查是否达到上限
            window.messages.append(msg)
            window.processed_message_ids.add(msg_id)

            if len(window.messages) >= self.max_messages:
                logger.info(
                    f"[消息汇总] 窗口 {group_key} 达到最大消息数 {self.max_messages}，立即处理"
                )
                await self._cancel_timer(window)
                batch = list(window.messages)
                window.messages.clear()
                window.is_active = False
                window.is_flushing = False
                window.processed_message_ids.clear()
                await self.output_queue.put((group_key, batch))
                return True

            # 窗口不在活跃模式
            # 检查距离上次消息是否很短（说明消息密集）
            if last_time > 0 and (now - last_time) < self.cooldown_seconds:
                # 消息密集，进入收集模式
                # 把上次那条也加入队列（上次已经返回 False 被处理了，所以只收集这条及后续）
                window.is_active = True
                window.messages.append(msg)
                window.processed_message_ids.add(msg_id)
                window.window_start = now
                window.last_reset = now

                # 发送状态提示
                if self.status_message and not self._status_sent.get(group_key, False):
                    self._status_sent[group_key] = True
                    if self.send_status_callback:
                        try:
                            await self.send_status_callback(
                                group_id, self.status_message
                            )
                        except Exception as e:
                            logger.warning(f"[消息汇总] 发送状态提示失败: {e}")

                # 启动计时器
                window.timer_task = asyncio.create_task(
                    self._window_timer(group_key, window)
                )
                return True

            # 单条消息，立即处理
            return False

    async def _window_timer(self, group_key: str, window: BatchWindow):
        """窗口期计时器"""
        try:
            await asyncio.sleep(self.window_seconds)

            # 检查窗口是否仍活跃
            async with self._lock:
                if group_key not in self._windows:
                    return
                current_window = self._windows[group_key]
                if current_window is not window or not current_window.is_active:
                    return

            # 刷新窗口
            await self._flush_window(group_key)

        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"[消息汇总] 窗口计时器异常: {e}")

    async def _flush_window(self, group_key: str):
        """刷新窗口，将消息放入输出队列"""
        async with self._lock:
            if group_key not in self._windows:
                return

            window = self._windows[group_key]
            # 先检查标志，再设置（原子操作）
            if not window.messages or not window.is_active or window.is_flushing:
                return

            window.is_flushing = True

            batch = list(window.messages)
            window.messages.clear()
            window.is_active = False
            window.processed_message_ids.clear()  # 清空已处理消息ID
            self._status_sent.pop(group_key, None)

            logger.info(f"[消息汇总] 窗口 {group_key} 超时，处理 {len(batch)} 条消息")

            # 重置刷新标志，允许下次窗口期
            window.is_flushing = False

            await self.output_queue.put((group_key, batch))

    async def _cancel_timer(self, window: BatchWindow):
        """取消窗口的计时器"""
        if window.timer_task and not window.timer_task.done():
            window.timer_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await window.timer_task
            window.timer_task = None

    async def get_next_batch(self) -> Optional[Tuple[str, List[QueuedMessage]]]:
        """获取下一个待处理的批次"""
        try:
            return await asyncio.wait_for(self.output_queue.get(), timeout=1.0)
        except asyncio.TimeoutError:
            return None

    async def force_flush(self, group_key: str) -> Optional[List[QueuedMessage]]:
        """强制刷新指定窗口"""
        async with self._lock:
            if group_key not in self._windows:
                return None

            window = self._windows[group_key]
            if not window.messages:
                return None

            await self._cancel_timer(window)
            batch = list(window.messages)
            window.messages.clear()
            window.is_active = False
            self._status_sent.pop(group_key, None)
            return batch

    async def shutdown(self):
        """关闭所有窗口"""
        async with self._lock:
            for group_key, window in self._windows.items():
                await self._cancel_timer(window)
                if window.messages:
                    logger.info(
                        f"[消息汇总] 关闭时刷新窗口 {group_key}，{len(window.messages)} 条消息"
                    )
                    await self.output_queue.put((group_key, list(window.messages)))
            self._windows.clear()

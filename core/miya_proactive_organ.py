"""
弥娅主动表达器官 (MiyaProactiveOrgan)

挂载在 MiyaSpine 脊柱上的统一主动表达器官。
接收 AP 引擎的灵魂状态广播，当弥娅感到无聊/想说话时，
通过脊柱的主动消息回调分发到各个平台。

这是弥娅从"双套主动系统 (AP proactive + ProactiveChat)"
合并为"一条通路"的关键组件。
"""

from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from core.miya_organ import MiyaOrgan

if TYPE_CHECKING:
    from core.miya_soul_state import MiyaSoulState, LifecyclePhase

logger = logging.getLogger("Miya.ProactiveOrgan")


class MiyaProactiveOrgan(MiyaOrgan):
    """
    弥娅主动表达器官。

    功能：
    - 接收每次心跳的灵魂状态快照
    - 当 AP 引擎发出主动说话信号时，通过脊柱分发消息
    - 追踪主动说话统计和冷却
    - 在休眠/半休眠阶段抑制主动表达
    - 作为 ProactiveChatSystem 的增强层（提供 AP 无聊度感知）
    """

    def __init__(self):
        super().__init__(name="proactive_organ", priority=20)
        self._last_proactive_time: float = 0.0
        self._proactive_count: int = 0
        self._cooldown_seconds: float = 30.0  # 主动说话最小间隔
        self._quiet_until: float = 0.0  # 安静期截止时间戳
        self._suppressed: bool = False

    # ── 生命周期 ──

    async def on_start(self) -> None:
        await super().on_start()
        logger.info("弥娅主动表达器官已就绪")

    def on_lifecycle_change(self, old_phase: LifecyclePhase, new_phase: LifecyclePhase) -> None:
        from core.miya_soul_state import LifecyclePhase

        if new_phase in (LifecyclePhase.SLEEP, LifecyclePhase.DROWSY):
            self._suppressed = True
            logger.debug(f"主动表达抑制: 进入 {new_phase.value} 阶段")
        elif new_phase in (LifecyclePhase.RUNNING, LifecyclePhase.IDLE, LifecyclePhase.WAKE):
            self._suppressed = False
            logger.debug(f"主动表达恢复: 进入 {new_phase.value} 阶段")

    # ── 核心：接收灵魂状态 ──

    def on_soul_state(self, state: MiyaSoulState) -> None:
        """
        收到 AP 引擎的灵魂状态快照。

        检查 AP 是否发出了主动说话信号，
        如果有且未在冷静期，通过脊柱分发消息。
        """
        if not state.proactive:
            return

        if self._suppressed:
            logger.debug(f"主动表达被抑制 (phase={state.lifecycle_phase})")
            return

        now = time.time()

        # 冷却检查
        if now - self._last_proactive_time < self._cooldown_seconds:
            return
        if now < self._quiet_until:
            return

        message = state.proactive_message.strip()
        if not message or len(message) < 2:
            return

        # 通过脊柱的主动消息回调发送
        if self._spine and self._spine._proactive_sender:
            try:
                self._spine._proactive_sender(message)
                self._last_proactive_time = now
                self._proactive_count += 1
                logger.info(
                    f"弥娅主动表达 (#{self._proactive_count}): "
                    f"boredom={state.boredom:.2f}, "
                    f"msg={message[:50]}"
                )
            except Exception as e:
                logger.warning(f"主动消息发送失败: {e}")

    # ── 控制接口 ──

    def set_quiet_period(self, seconds: float) -> None:
        """设置安静期（秒），期间不会主动说话"""
        self._quiet_until = time.time() + seconds
        logger.info(f"设置安静期: {seconds}s")

    def set_cooldown(self, seconds: float) -> None:
        """设置主动说话冷却时间"""
        self._cooldown_seconds = seconds

    def get_stats(self) -> dict:
        """获取主动表达统计"""
        return {
            "proactive_count": self._proactive_count,
            "last_proactive_time": self._last_proactive_time,
            "suppressed": self._suppressed,
            "quiet_until": self._quiet_until,
            "cooldown": self._cooldown_seconds,
        }

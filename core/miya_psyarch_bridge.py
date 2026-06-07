"""
弥娅 APV2.1 认知引擎桥接层 v2

接入主系统：
- process_message(): AP 认知 + LLM 皮层 → 回复
- idle_heartbeat(): 持续 tick → 主动说话检测 → 回调
- emotion_snapshot(): AP 情绪数据 → 旧情绪系统
- mount_observatory(): Web 仪表盘 → 主 dashboard
"""

from __future__ import annotations

import asyncio
import logging
import threading
import time
from typing import Any, Callable

logger = logging.getLogger("miya.psyarch_bridge")


class MiyaPsyArchBridge:
    def __init__(
        self,
        personality_form: str | None = None,
        enable_cortex: bool = True,
        proactive_callback: Callable[[str], None] | None = None,
    ):
        self._engine: Any = None
        self._personality_form = personality_form
        self._enable_cortex = enable_cortex
        self._message_count: int = 0
        self._total_latency_ms: float = 0.0
        self._initialized = False
        self._proactive_callback = proactive_callback
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_running = False

    def _init_engine(self) -> None:
        if self._initialized:
            return
        from miya_psyarch.engine import MiyaEngine

        self._engine = MiyaEngine(
            trace_mode="summary",
            enable_cortex=self._enable_cortex,
            personality_form=self._personality_form,
        )
        self._engine.start()
        self._initialized = True
        logger.info("MiyaPsyArchBridge initialized")

    def process_message(self, text: str) -> tuple[str, dict]:
        self._init_engine()
        t0 = time.perf_counter()
        if self._enable_cortex:
            reply = self._engine.chat(text)
        else:
            self._engine.tick(text=text)
            reply = ""
        elapsed = (time.perf_counter() - t0) * 1000
        self._message_count += 1
        self._total_latency_ms += elapsed
        return reply, self._engine.status_report()

    async def process_message_async(self, text: str) -> tuple[str, dict]:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.process_message, text)

    # ── 主动说话 ──

    def start_heartbeat(self, interval_s: float = 3.0) -> None:
        """启动后台心跳——AP 持续 tick，检测主动说话"""
        if self._heartbeat_running:
            return
        self._init_engine()
        self._heartbeat_running = True
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, args=(interval_s,), daemon=True)
        self._heartbeat_thread.start()
        logger.info("AP heartbeat started")

    def stop_heartbeat(self) -> None:
        self._heartbeat_running = False

    def _heartbeat_loop(self, interval_s: float) -> None:
        ticks_per_interval = max(1, int(interval_s * 10))
        while self._heartbeat_running:
            try:
                for _ in range(ticks_per_interval):
                    trace = self._engine.idle_tick()
                    if isinstance(trace, dict):
                        proactive = trace.get("proactive", {})
                        if proactive.get("proactive"):
                            msg = proactive.get("message", "")
                            if msg and self._proactive_callback:
                                self._proactive_callback(msg)
                time.sleep(interval_s)
            except Exception as e:
                logger.warning(f"AP heartbeat error: {e}")
                time.sleep(5)

    def set_proactive_callback(self, callback: Callable[[str], None]) -> None:
        self._proactive_callback = callback

    # ── 情绪合并 ──

    def emotion_snapshot(self) -> dict:
        """获取 AP 情绪快照，供旧情绪系统使用"""
        self._init_engine()
        s = self._engine.soul_state()
        # 从状态池读取所有情绪相关项
        real_emotions = {}
        if self._engine._runtime:
            from miya_psyarch.emotion_pool import EMOTION_CN_MAP

            pool = self._engine._runtime.state_pool
            for k, v in pool._entries.items():
                # 情绪池项 (emotion_pool) 或 先天规则项 (miya_emotion)
                if str(v.family) == "miya_emotion":
                    name = str(k).replace("miya_emotion::", "").replace("miya::", "")
                    if name and name not in ("contentment", "curious"):  # 先天规则项转换中文
                        pass
                    real_emotions[name] = round(v.real_energy, 4)
        return {
            "nt_channels": s.emotion_nt,
            "miya_feelings": real_emotions if real_emotions else s.miya_feelings,
            "cognitive": s.feelings,
            "has_active_intent": s.has_active_intent,
        }

    # ── 观测台 ──

    def mount_observatory(self, port: int = 8765) -> str:
        """启动 AP 观测台 Web 服务器"""
        self._init_engine()
        return self._engine.start_observatory(port=port)

    # ── NT 回写 (闭环反馈) ──

    def apply_nt_adjustments(self, adjustments: dict) -> None:
        """将 AI 情绪分析结果回写到 AP NT 通道 (闭环反馈)"""
        self._init_engine()
        if not self._engine._runtime:
            return
        runtime = self._engine._runtime
        if not hasattr(runtime, "_emotion_state") or not runtime._emotion_state:
            return
        emo_state = runtime._emotion_state
        for ch, delta in adjustments.items():
            if ch in emo_state.channels:
                emo_state.apply_delta(ch, delta)

    # ── 多模态 ──

    def see_image(self, image_bytes: bytes, description: str = "") -> dict:
        self._init_engine()
        p = self._engine.see_image(image_bytes, description=description)
        return {
            "width": p.width,
            "height": p.height,
            "brightness": round(p.avg_brightness, 3),
            "dominant_colors": p.dominant_colors[:3],
        }

    def hear_audio(self, audio_bytes: bytes, transcript: str = "") -> dict:
        self._init_engine()
        p = self._engine.hear_audio(audio_bytes, transcript=transcript)
        return {
            "duration_ms": round(p.duration_ms, 0),
            "max_amplitude": round(p.max_amplitude, 3),
            "has_voice": p.has_voice,
        }

    # ── 属性 ──

    @property
    def engine(self):
        self._init_engine()
        return self._engine

    @property
    def stats(self) -> dict:
        return {
            "messages": self._message_count,
            "avg_latency_ms": round(self._total_latency_ms / max(self._message_count, 1), 0),
            "engine_ready": self._initialized,
            "heartbeat_running": self._heartbeat_running,
        }


_bridge: MiyaPsyArchBridge | None = None


def get_psyarch_bridge() -> MiyaPsyArchBridge:
    global _bridge
    if _bridge is None:
        _bridge = MiyaPsyArchBridge()
        _bridge._init_engine()  # 立即初始化引擎
    return _bridge

"""
认知服务 v9.0 — AP 引擎统一认知层

弥娅 v9.0 重构：APV2.1 白盒认知引擎作为底层认知驱动
降级策略：AP 不可用时回退到 Emotion + SoulGenerator
"""

from __future__ import annotations

import asyncio
import logging
import threading
from typing import Any

from hub.services.context import ProcessRequest, ProcessState

logger = logging.getLogger("miya.services.cognition")


class CognitionService:
    """认知层服务 — AP 引擎统一驱动"""

    def __init__(
        self,
        emotion: Any = None,
        soul_generator: Any = None,
        personality: Any = None,
        decision_engine: Any = None,
        use_ap: bool = True,
    ):
        self.emotion = emotion
        self.soul_generator = soul_generator
        self.personality = personality
        self.decision_engine = decision_engine

        self.use_ap = use_ap
        self._ap_bridge: Any = None
        self._ap_ready = False
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_running = False
        self._on_proactive: Any = None

        if use_ap:
            self._init_ap()

    def _init_ap(self) -> None:
        try:
            from core.miya_psyarch_bridge import get_psyarch_bridge

            self._ap_bridge = get_psyarch_bridge()
            self._ap_ready = True
            logger.info("[认知] APV2.1 认知引擎已加载")
        except Exception as e:
            logger.warning(f"[认知] AP 引擎加载失败, 降级到传统模式: {e}")
            self._ap_ready = False

    def start_heartbeat(self, interval: float = 5.0, on_proactive: Any = None) -> None:
        """启动 AP 心跳（主动认知循环）"""
        if not self._ap_ready or not self._ap_bridge:
            return

        self._on_proactive = on_proactive
        self._heartbeat_running = True

        def _loop():
            while self._heartbeat_running:
                try:
                    self._ap_bridge.idle_heartbeat()
                except Exception as e:
                    logger.debug(f"[认知] 心跳异常: {e}")
                threading.Event().wait(interval)

        self._heartbeat_thread = threading.Thread(target=_loop, daemon=True)
        self._heartbeat_thread.start()
        logger.info(f"[认知] AP 心跳已启动 (间隔 {interval}s)")

    def stop_heartbeat(self) -> None:
        self._heartbeat_running = False

    async def process(self, request: ProcessRequest, state: ProcessState) -> ProcessState:
        state.phase = state.phase.COGNITION

        if self._ap_ready and self._ap_bridge:
            return await self._process_ap(request, state)
        return await self._process_fallback(request, state)

    async def _process_ap(self, request: ProcessRequest, state: ProcessState) -> ProcessState:
        try:
            if hasattr(self._ap_bridge, "process_message"):
                result = self._ap_bridge.process_message(request.content)
                reply, soul_state = result if isinstance(result, tuple) else (result, {})
            else:
                reply, soul_state = "", {}

            if soul_state:
                state.soul_data = soul_state
                state.emotion_context = self._build_emotion_context_ap(soul_state)
                state.emotion_state = soul_state.get("emotion", {})

            logger.debug(f"[认知] AP 处理完成: {soul_state.get('dominant_emotion', 'neutral')}")

        except Exception as e:
            logger.warning(f"[认知] AP 处理异常, 降级: {e}")
            state = await self._process_fallback(request, state)

        return state

    async def _process_fallback(self, request: ProcessRequest, state: ProcessState) -> ProcessState:
        """传统模式：Emotion + SoulGenerator"""
        if self.emotion:
            try:
                if hasattr(self.emotion, "auto_detect_from_input"):
                    self.emotion.auto_detect_from_input(request.content)
                if hasattr(self.emotion, "get_emotion_state"):
                    state.emotion_state = self.emotion.get_emotion_state()
                if hasattr(self.emotion, "decay_coloring"):
                    self.emotion.decay_coloring(0.02)
            except Exception as e:
                logger.warning(f"[认知] 情绪处理异常: {e}")

        if self.soul_generator:
            try:
                result = await self.soul_generator.process(
                    message=request.content,
                    history=[],
                    ai_client=None,
                    user_info={"user_id": str(request.user_id), "name": request.sender_name},
                    personality_info=self._get_personality_info(),
                    cognitive_memory=None,
                )
                if result:
                    state.soul_data = result
                    state.emotion_context = self._build_emotion_context_fallback(result)
            except Exception as e:
                logger.warning(f"[认知] 灵魂处理异常: {e}")

        return state

    def _get_personality_info(self) -> dict[str, Any]:
        if not self.personality:
            return {"name": "弥娅", "form": "default"}
        try:
            return {
                "name": getattr(self.personality, "name", "弥娅"),
                "form": getattr(self.personality, "current_form", "default"),
            }
        except Exception:
            return {"name": "弥娅", "form": "default"}

    def _build_emotion_context_ap(self, soul_state: dict[str, Any]) -> str:
        dominant = soul_state.get("dominant_emotion", "neutral")
        intensity = soul_state.get("emotion_intensity", 50)
        inner = soul_state.get("inner_thought", "")
        user_emo = soul_state.get("user_emotion", {})

        parts = ["\n\n【AP 认知 · 情感画像】"]
        if user_emo:
            parts.append(f"- 用户情绪: {user_emo.get('dominant', user_emo)}")
        parts.append(f"- 弥娅情绪: {dominant} ({intensity}%)")
        if inner:
            parts.append(f"- 内心微澜: {inner}")
        parts.append("请感知这份情感画像，给出你真实自然的回应。")
        return "\n".join(parts)

    def _build_emotion_context_fallback(self, soul_data: dict[str, Any]) -> str:
        dominant = soul_data.get("dominant_emotion", "neutral")
        intensity = soul_data.get("emotion_intensity", 50)
        inner_thought = soul_data.get("inner_thought", "")
        user_emotion = soul_data.get("user_emotion", {})

        parts = ["\n\n【情感指引】"]
        if user_emotion:
            parts.append(f"- 用户情绪: {user_emotion.get('dominant', 'neutral')}")
        parts.append(f"- 你的情绪: {dominant} ({intensity}%)")
        if inner_thought:
            parts.append(f"- 你的内心独白: {inner_thought}")
        parts.append("请根据上述情感自然回应，展现你真实的情感。")
        return "\n".join(parts)

    def get_ap_status(self) -> dict[str, Any]:
        return {
            "ap_ready": self._ap_ready,
            "heartbeat_running": self._heartbeat_running,
        }

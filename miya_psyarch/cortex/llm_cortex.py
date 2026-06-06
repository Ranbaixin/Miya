"""
弥娅语言皮层 — LLM 调用封装

配置加载自 miya_config.yaml，无硬编码字符串。
"""

from __future__ import annotations

import asyncio
import concurrent.futures
import io
import logging
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger("miya_psyarch.cortex")

_CFG_PATH = Path(__file__).resolve().parent.parent / "config" / "miya_config.yaml"
with open(_CFG_PATH, "r", encoding="utf-8") as _f:
    _CFG = yaml.safe_load(_f) or {}

_FALLBACKS = _CFG.get("fallbacks", {})
_FALLBACK_BOREDOM_THRESHOLD = _CFG.get("fallback_thresholds", {}).get("boredom", 0.7)
_LLM_TIMEOUT = _CFG.get("llm_timeout", 15.0)
_TASK_STATE_KEYS = tuple(
    _CFG.get("task_state_keys", ["boredom", "fulfillment", "task_available", "unfinished_strength"])
)


@dataclass
class CortexResult:
    text: str = ""
    success: bool = False
    error: str = ""
    model_used: str = ""
    latency_ms: float = 0.0
    raw_response: Any = None


class MiyaCortex:
    def __init__(
        self,
        *,
        model_id: str | None = None,
        task_type: str = "simple_chat",
    ) -> None:
        self._model_id = model_id
        self._task_type = task_type
        self._client = None

    def _get_client(self):
        if self._client is not None:
            return self._client
        try:
            from core.model_pool_manager import get_model_pool

            pool = get_model_pool()
            if self._model_id:
                self._client = pool.create_ai_client(model_id=self._model_id)
            else:
                self._client = pool.create_ai_client(task_type=self._task_type)
        except Exception as e:
            logger.warning(f"无法创建 LLM 客户端: {e}")
            self._client = None
        return self._client

    def build_prompt(
        self, state, user_message: str, *, form: str | None = None, memory_context: str = ""
    ) -> tuple[str, str]:
        from datetime import datetime
        from miya_psyarch.cortex.prompt_builder import MiyaInternalState, build_miya_cortex_prompt

        now = datetime.now()
        if now.hour < 6:
            time_desc = "深夜"
        elif now.hour < 9:
            time_desc = "清晨"
        elif now.hour < 12:
            time_desc = "上午"
        elif now.hour < 14:
            time_desc = "中午"
        elif now.hour < 18:
            time_desc = "下午"
        elif now.hour < 21:
            time_desc = "傍晚"
        else:
            time_desc = "晚上"

        internal = MiyaInternalState(
            tick=state.tick_index,
            feelings=state.feelings,
            miya_feelings=state.miya_feelings,
            emotion_nt=state.emotion_nt,
            focus=state.focus_texts,
            task_state={k: v for k, v in state.feelings.items() if k in _TASK_STATE_KEYS},
            current_time=f"{now.strftime('%Y年%m月%d日')} {time_desc} {now.strftime('%H:%M')}",
            recent_context=getattr(state, "recent_context", None),
            memory_context=memory_context,
        )
        return build_miya_cortex_prompt(internal, user_message, personality_form=form)

    def select_fallback(self, state) -> str:
        mf = state.miya_feelings or {}
        feelings = state.feelings or {}
        strongest, strongest_val = None, 0.0
        for k, v in mf.items():
            if v > strongest_val:
                strongest, strongest_val = k, v
        if strongest and strongest in _FALLBACKS:
            return random.choice(_FALLBACKS[strongest])
        if feelings.get("boredom", 0) > _FALLBACK_BOREDOM_THRESHOLD:
            return random.choice(_FALLBACKS.get("boredom", _FALLBACKS.get("default", ["嗯。"])))
        return random.choice(_FALLBACKS.get("default", ["嗯。"]))

    def describe_image(self, image_bytes: bytes) -> str:
        """用视觉 LLM 描述图片"""
        import asyncio

        try:
            from core.multi_vision_analyzer import MultiVisionAnalyzer

            async def _run():
                analyzer = MultiVisionAnalyzer()
                await analyzer.initialize()
                result = await analyzer.analyze_image(image_bytes)
                if result.success and result.description:
                    return result.description
                return ""

            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(lambda: asyncio.new_event_loop().run_until_complete(_run()))
                    return future.result(timeout=12)
            else:
                return loop.run_until_complete(asyncio.wait_for(_run(), timeout=12))

        except (asyncio.TimeoutError, concurrent.futures.TimeoutError):
            logger.debug("Vision LLM timeout (using PIL fallback)")
            return ""
        except Exception as e:
            logger.warning(f"Vision LLM failed: {e}")
            return ""

    def transcribe_audio(self, audio_bytes: bytes) -> str:
        """用 STT 转写音频"""
        try:
            from core.providers_astrbot.provider import ProviderManager

            mgr = ProviderManager()
            stt_provider = mgr.get_provider("speech_to_text")
            if stt_provider:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(
                            lambda: asyncio.new_event_loop().run_until_complete(stt_provider.transcribe(audio_bytes))
                        )
                        return future.result(timeout=20)
                else:
                    return loop.run_until_complete(stt_provider.transcribe(audio_bytes))
        except Exception as e:
            logger.debug(f"STT unavailable: {e}")
        return ""

    async def render(self, system_prompt: str, user_message: str, *, timeout: float | None = None) -> CortexResult:
        if timeout is None:
            timeout = _LLM_TIMEOUT

        t0 = time.perf_counter()
        result = CortexResult()
        client = self._get_client()
        if client is None:
            result.error = "LLM client unavailable"
            return result

        try:
            original_stdout = sys.stdout
            sys.stdout = io.StringIO()
            try:
                response = await asyncio.wait_for(
                    client.chat_with_system_prompt(system_prompt=system_prompt, user_message=user_message, tools=None),
                    timeout=timeout,
                )
            finally:
                sys.stdout = original_stdout

            result.latency_ms = (time.perf_counter() - t0) * 1000

            if response and hasattr(response, "content"):
                result.text = str(response.content).strip()
            elif isinstance(response, str):
                result.text = response.strip()
            elif isinstance(response, dict):
                result.text = str(response.get("content", response.get("text", ""))).strip()
            else:
                result.text = str(response).strip()

            result.success = bool(result.text)
            result.model_used = getattr(client, "model", getattr(client, "model_name", self._model_id or "unknown"))
            result.raw_response = response

        except asyncio.TimeoutError:
            result.error = f"LLM timeout after {timeout}s"
            result.latency_ms = timeout * 1000
            logger.warning(result.error)
        except Exception as e:
            result.error = str(e)
            result.latency_ms = (time.perf_counter() - t0) * 1000
            logger.warning(f"LLM render error: {e}")

        return result

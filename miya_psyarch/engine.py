"""
弥娅心灵引擎 —— APV2.1 认知闭环 + LLM 语言皮层

MiyaEngine 提供两种模式：
1. tick() — 纯 AP 认知，不调用 LLM（弥娅的内心活动）
2. chat() — AP 认知 + LLM 渲染 = 弥娅的完整回复
"""

from __future__ import annotations

import asyncio
import io
import logging
import sys
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

import yaml

from miya_psyarch.config.defaults import RuntimeConfig
from miya_psyarch.core.emotion.emotion_state import NT_CHANNEL_META
from miya_psyarch.core.runtime.engine import APV21Runtime
from miya_psyarch.cortex.llm_cortex import CortexResult, MiyaCortex
from miya_psyarch.miya_educator import package_response_as_education
from miya_psyarch.emotion_pool import analyze_emotions, emotions_to_state_items
from miya_psyarch.memory.miya_memory_bridge import MiyaMemoryBridge, get_memory_bridge
from miya_psyarch.memory.miya_memory_fusion import MiyaMemoryFusion, get_memory_fusion
from miya_psyarch.multimodal import (
    AudioPerception,
    MultiModalContext,
    VisualPerception,
    audio_to_state_items,
    image_to_state_items,
    perceive_audio,
    perceive_image,
)
from miya_psyarch.miya_obs import MiyaObservatory, record_tick
from miya_psyarch.rules.miya_rules import MIYA_EMOTION_BASELINE, miya_rules
from miya_psyarch.sensors.miya_text_sensor import patch_text_sensor

logger = logging.getLogger("miya_psyarch.engine")

# 加载引擎配置
_CFG_PATH = Path(__file__).resolve().parent.parent / "config" / "miya_config.yaml"
with open(_CFG_PATH, "r", encoding="utf-8") as _f:
    _ENGINE_CFG = (yaml.safe_load(_f) or {}).get("engine", {})

_TICK_HISTORY_MAX = _ENGINE_CFG.get("tick_history_max", 1000)
_TICK_HISTORY_KEEP = _ENGINE_CFG.get("tick_history_keep", 500)
_FOCUS_SLICE = _ENGINE_CFG.get("focus_slice", 5)
_STATE_TOP_SLICE = _ENGINE_CFG.get("state_top_slice", 8)
_PROACTIVE = _ENGINE_CFG.get("proactive", {})

_FULL_CFG = yaml.safe_load(_CFG_PATH.read_text(encoding="utf-8")) or {}
# 情绪→NT 映射 fallback（当 YAML 不可用时）
_FALLBACK_EMOTION_NT_MAP: dict[str, dict[str, float]] = {
    "love": {"OXY": 0.14, "DA": 0.10},
    "joy": {"DA": 0.10},
    "sadness": {"SER": -0.08},
    "attachment": {"OXY": 0.14},
    "curiosity": {"NOV": 0.14},
    "warmth": {"OXY": 0.12},
    "fear": {"COR": 0.12},
    "anger": {"COR": 0.12},
    "contentment": {"SER": 0.12},
}

_SP_CFG = (yaml.safe_load(_CFG_PATH.read_text(encoding="utf-8")) or {}).get("state_pool", {})
_MIYA_FAMILY_PREFIX = _SP_CFG.get("miya_family_prefix", "miya_")
_MIYA_LABEL_PREFIX = _SP_CFG.get("miya_label_prefix", "miya::")


@dataclass
class MiyaSoulState:
    """弥娅心灵状态 —— 从 AP tick trace 中提取的高层可读状态"""

    tick_index: int = 0
    focus_labels: list[str] = field(default_factory=list)
    focus_texts: list[str] = field(default_factory=list)
    feelings: dict[str, float] = field(default_factory=dict)
    miya_feelings: dict[str, float] = field(default_factory=dict)
    emotion_nt: dict[str, float] = field(default_factory=dict)
    state_top: list[dict] = field(default_factory=list)
    text_output: str = ""
    has_active_intent: bool = False
    llm_response: str = ""
    llm_model: str = ""
    llm_latency_ms: float = 0.0
    recent_context: list[str] = field(default_factory=list)
    raw_trace: dict | None = None


class MiyaEngine:
    """弥娅的心灵引擎 + 语言皮层。"""

    def __init__(
        self,
        *,
        trace_mode: str = "summary",
        enable_cortex: bool = True,
        cortex_model_id: str | None = None,
        personality_form: str | None = None,
    ) -> None:
        self._trace_mode = trace_mode
        self._config = self._build_config()
        self._runtime: APV21Runtime | None = None
        self._ticks: list[dict] = []
        self._current_soul: MiyaSoulState = MiyaSoulState()
        self._miya_rules_list = miya_rules()
        self._personality_form = personality_form

        self._cortex_enabled = enable_cortex
        self._cortex: MiyaCortex | None = None
        if enable_cortex:
            self._cortex = MiyaCortex(model_id=cortex_model_id)

        self._memory_bridge: MiyaMemoryBridge | None = None
        self._memory_context: str = ""
        self._pending_education: list[dict] = []
        self._idle_streak: int = 0
        self._proactive_threshold: float = 0.65
        self._proactive_min_streak: int = 10
        self._proactive_cooldown: int = 0
        self._observatory: MiyaObservatory | None = None
        self._multimodal: MultiModalContext = MultiModalContext()
        self._perf_stats: dict = {"tick_times_ms": [], "max_samples": 100, "total_ticks": 0}
        self._perf_detail: dict[str, list[float]] = {}

    def _build_config(self) -> RuntimeConfig:
        return RuntimeConfig()

    def _apply_miya_emotion_baseline(self) -> None:
        for channel, (baseline, _decay, _cap) in MIYA_EMOTION_BASELINE.items():
            if channel in NT_CHANNEL_META:
                NT_CHANNEL_META[channel]["baseline"] = baseline
        if self._runtime is not None:
            es = self._runtime.emotion_modulator.state
            for channel, (baseline, _decay, _cap) in MIYA_EMOTION_BASELINE.items():
                if channel in es.channels:
                    es.channels[channel] = baseline

    def _apply_cognitive_feeling_gains(self) -> None:
        """应用弥娅专属的认知感受增益 + 降低 CFS→NT 注入强度"""
        if self._runtime is None:
            return
        cfg = {}
        _p = _CFG_PATH  # 使用统一的配置路径
        if _p.exists():
            import yaml

            cfg = (yaml.safe_load(_p.read_text(encoding="utf-8")) or {}).get("cognitive_feeling_gains", {})
        ch = self._runtime.cognitive_feelings
        for key in ("surprise", "coherence", "dissonance", "correctness", "grasp", "expectation", "pressure"):
            attr = f"{key}_gain"
            if key in cfg and hasattr(ch, attr):
                setattr(ch, attr, cfg[key])

        # 降低 CFS→NT 映射强度，防止情绪饱和
        # OXY 由文本触发 + 教育反馈驱动，而非持续的 CFS 映射
        if hasattr(self._runtime.emotion_modulator, "cfs_gain"):
            self._runtime.emotion_modulator.cfs_gain = 0.08

    def _apply_training_state(self) -> None:
        """加载训练结果: 离线预训练锚点 → 状态池 + 规则蒸馏调制"""
        try:
            from miya_psyarch.miya_trainer import get_trainer

            trainer = get_trainer()
            # 离线预训练锚点注入
            anchors = trainer.get_baseline_anchors()
            if anchors and self._runtime:
                items = [
                    {
                        "sa_label": f"pretrain::{a.get('text', '')[:25]}",
                        "display_text": a.get("text", "")[:40],
                        "family": a.get("family", "pretrain_anchor"),
                        "real_energy": a.get("energy", 0.5),
                        "anchor_meta": {"tags": a.get("tags", []), "source": "pretrain"},
                    }
                    for a in anchors[:40]
                ]
                if items:
                    self._runtime.state_pool.apply_external_items(items, tick_index=0)

            # 规则蒸馏调制 → 存为引擎属性
            modulation = trainer.get_rule_modulation()
            if modulation:
                self._training_modulation = modulation
                logger.info(f"[训练] 已加载 {len(modulation)} 条规则蒸馏调制")
        except Exception as e:
            logger.debug(f"[训练] 状态加载跳过: {e}")

    def _apply_tuner_modulation(self, modulation: dict) -> None:
        """消费 tuner 调制输出，调整 runtime 参数"""
        mem_mod = modulation.get("memory", {})
        gain = mem_mod.get("prediction_gain_multiplier", 1.0)
        if hasattr(self._runtime, "attention_selector"):
            sel = self._runtime.attention_selector
            if hasattr(sel, "recency_boost"):
                sel.recency_boost = max(0.1, min(3.0, getattr(sel, "recency_boost", 1.0) * gain))

        action_mod = modulation.get("action", {})
        threshold = action_mod.get("threshold_adjustment", 0.0)
        if abs(threshold) > 0.001 and hasattr(self._runtime, "action_planner"):
            ap = self._runtime.action_planner
            if hasattr(ap, "base_threshold"):
                ap.base_threshold = max(0.05, min(0.5, getattr(ap, "base_threshold", 0.2) + threshold))

        learn_mod = modulation.get("learning", {})
        rate = learn_mod.get("rate_multiplier", 1.0)
        if abs(rate - 1.0) > 0.05 and hasattr(self._runtime, "learning_router"):
            lr = self._runtime.learning_router
            if hasattr(lr, "event_rate"):
                lr.event_rate = max(0.01, min(1.0, getattr(lr, "event_rate", 0.5) * rate))

    def _inject_memories_into_state_pool(self) -> list[dict]:
        """收集记忆 items（不直接写入，由调用方批量写入）"""
        if self._runtime is None or self._memory_bridge is None:
            return []
        all_recent = list(self._memory_bridge._recent)
        if not all_recent:
            return []
        items = self._memory_bridge.as_state_items(all_recent[-40:], base_energy=1.2)
        logger.debug(f"collected {len(items)} memories for batch injection")
        return items

    def _collect_memory_items(self) -> list[dict]:
        """每 20 tick 收集记忆 items（供 tick() 批量写入）"""
        return self._inject_memories_into_state_pool()

    def _tick_memory_context(self, user_message: str) -> None:
        """从 AP 注意力中提取 Bn 召回的記憶 + 情绪上下文 + SQL 关键词搜索补充"""
        if self._memory_bridge is None:
            return
        trace = self._current_soul.raw_trace or {}

        # 情绪池上下文
        emotion_context = self._emotion_pool_context()

        # 从 AP 注意力中提取被 Bn/Cn 自然召回的記憶
        recalled = []
        att_items = trace.get("attention", {}).get("selected_items", [])
        for item in att_items[:10]:
            if str(item.get("family", "")).startswith("miya_memory"):
                full = item.get("anchor_meta", {}).get("full_content", "") or item.get("display_text", "")
                if full:
                    recalled.append({"role": "memory", "content": full, "created_at": ""})

        if recalled:
            mem_text = self._memory_bridge.context_text(recalled[:4])
        else:
            related = self._memory_bridge.search(user_message, limit=4)
            if related:
                mem_text = self._memory_bridge.context_text(related)
            else:
                mem_text = self._memory_bridge.recent_context_text()

        self._memory_context = emotion_context + "\n" + mem_text if emotion_context else mem_text

    def _emotion_pool_context(self) -> str:
        """从状态池提取当前情绪指纹"""
        if self._runtime is None:
            return ""
        pool = self._runtime.state_pool
        emotions = {}
        for k, v in pool._entries.items():
            if "miya_emotion::" in str(k):
                name = str(k).replace("miya_emotion::", "")
                if name not in ("contentment",):  # 排除先天规则项
                    emotions[name] = v.real_energy
        if not emotions:
            return ""
        top = sorted(emotions.items(), key=lambda x: -x[1])[:8]
        from miya_psyarch.emotion_pool import EMOTION_CN_MAP

        parts = []
        for name, val in top:
            cn = EMOTION_CN_MAP.get(name, name)
            parts.append(f"{cn}:{val:.1f}")
        return f"弥娅对这句话的情绪反应: {', '.join(parts)}"

    def start(self) -> None:
        """初始化并启动心灵引擎（批量写入优化版）"""
        self._runtime = APV21Runtime(
            config=self._config,
            innate_rules=self._miya_rules_list,
        )
        self._apply_miya_emotion_baseline()
        patch_text_sensor(self._runtime)
        self._apply_cognitive_feeling_gains()

        self._memory_bridge = get_memory_bridge()
        self._memory_bridge.warmup(limit=100)
        self._memory_fusion = get_memory_fusion(self)
        self._memory_fusion.load_all()

        # 批量收集初始 items → 一次写入
        batch = []
        batch.extend(self._inject_memories_into_state_pool())
        batch.extend(self._memory_fusion.inject_permanent_anchors())
        batch.extend(self._memory_fusion.inject_cognitive_memories())
        if batch:
            self._runtime.state_pool.apply_external_items(batch, tick_index=0)
            logger.info(f"injected {len(batch)} items into state pool (batched)")

        self._memory_context = self._memory_bridge.recent_context_text()

        trace = self._runtime.process_multimodal_tick(text="", trace_mode=self._trace_mode)
        self._ticks.append(trace)
        self._current_soul = self._extract_soul(trace)

        # 加载训练结果: 离线预训练锚点 + 规则蒸馏调制
        self._apply_training_state()

    def tick(
        self,
        text: str = "",
        *,
        education_interventions: dict | list[dict] | None = None,
    ) -> dict:
        """推进一次认知 tick（纯 AP 引擎，不调用 LLM）。批量写入优化版。"""
        t0 = time.perf_counter()
        trace: dict = {}

        def _step(name: str):
            t = time.perf_counter()
            self._perf_detail.setdefault(name, [])
            return t

        def _done(name: str, t_start: float):
            ms = (time.perf_counter() - t_start) * 1000
            times = self._perf_detail.setdefault(name, [])
            times.append(ms)
            if len(times) > 200:
                self._perf_detail[name] = times[-100:]

        if self._runtime is None:
            self.start()

        batch_items: list[dict] = []

        t_s = _step("emotion_pool")
        emotion_items = self._inject_emotion_pool(text)
        if emotion_items:
            batch_items.extend(emotion_items)
        _done("emotion_pool", t_s)

        combined_edu = list(education_interventions or []) + list(self._pending_education)
        self._pending_education = []

        t_s = _step("multimodal_tick")
        trace = self._runtime.process_multimodal_tick(
            text=text,
            trace_mode=self._trace_mode,
            education_interventions=combined_edu if combined_edu else None,
        )
        _done("multimodal_tick", t_s)

        t_s = _step("context_inject")
        ctx_items = self._inject_context_into_state_pool(text)
        if ctx_items:
            batch_items.extend(ctx_items)
        _done("context_inject", t_s)

        t_s = _step("anchors")
        anchor_items = self._memory_fusion.inject_permanent_anchors()
        if anchor_items:
            batch_items.extend(anchor_items)
        cog_items = self._memory_fusion.inject_cognitive_memories()
        if cog_items:
            batch_items.extend(cog_items)
        _done("anchors", t_s)

        if self._current_soul.tick_index % 20 == 0 and text:
            t_s = _step("memory_reload")
            mem_items = self._collect_memory_items()
            if mem_items:
                batch_items.extend(mem_items)
            _done("memory_reload", t_s)

        t_s = _step("batch_write")
        if batch_items:
            self._runtime.state_pool.apply_external_items(batch_items, tick_index=self._runtime.tick_index)
        _done("batch_write", t_s)

        t_s = _step("tuner_modulation")
        if hasattr(self._runtime, "tuner") and self._runtime.tuner:
            try:
                mod = self._runtime.tuner.active_modulation()
                self._apply_tuner_modulation(mod)
            except Exception:
                pass
        _done("tuner_modulation", t_s)

        t_s = _step("clamp")
        self._clamp_emotion_ceiling()
        _done("clamp", t_s)

        t_s = _step("record")
        self._ticks.append(trace)
        self._current_soul = self._extract_soul(trace)
        record_tick(self)
        if self._observatory is not None:
            self._observatory.set_trace(trace)
        if len(self._ticks) > _TICK_HISTORY_MAX:
            self._ticks = self._ticks[-_TICK_HISTORY_KEEP:]
        _done("record", t_s)

        elapsed_ms = (time.perf_counter() - t0) * 1000
        self._perf_stats["total_ticks"] += 1
        self._perf_stats["tick_times_ms"].append(elapsed_ms)
        if len(self._perf_stats["tick_times_ms"]) > self._perf_stats["max_samples"]:
            self._perf_stats["tick_times_ms"] = self._perf_stats["tick_times_ms"][-self._perf_stats["max_samples"] :]

        return trace

    def perf_stats(self) -> dict:
        """返回 tick 性能统计 — CPU 火焰图 + GPU 监控"""
        times = self._perf_stats.get("tick_times_ms", [])
        result: dict = {"ready": bool(times), "total_ticks": self._perf_stats["total_ticks"]}

        if times:
            s = sorted(times)
            result.update(
                {
                    "cpu_avg_ms": round(sum(times) / len(times), 2),
                    "cpu_p50_ms": round(s[len(s) // 2], 2),
                    "cpu_p95_ms": round(s[int(len(s) * 0.95)], 2) if len(s) > 5 else round(s[-1], 2),
                    "cpu_max_ms": round(max(times), 2),
                    "cpu_samples": len(times),
                }
            )

        # 子步骤火焰图
        detail = {}
        for step, step_times in getattr(self, "_perf_detail", {}).items():
            if step_times:
                detail[step] = {
                    "avg_ms": round(sum(step_times) / len(step_times), 3),
                    "max_ms": round(max(step_times), 3),
                    "count": len(step_times),
                }
        if detail:
            result["cpu_flame_steps"] = dict(sorted(detail.items(), key=lambda x: -x[1]["avg_ms"]))

        # GPU 监控
        gpu = _collect_gpu_stats()
        if gpu:
            result["gpu"] = gpu

        return result

    def _clamp_emotion_ceiling(self) -> None:
        """限制情绪通道天花板，留出波动空间 (从 miya_config.yaml 读取)"""
        if self._runtime is None:
            return
        es = self._runtime.emotion_modulator.state
        default_limits = {
            "OXY": 0.50,
            "SER": 0.45,
            "DA": 0.45,
            "FOC": 0.40,
        }
        cfg_ceiling = _ENGINE_CFG.get("emotion_ceiling", {})
        if not cfg_ceiling.get("enabled", True):
            return
        limits = {k: cfg_ceiling.get(k, v) for k, v in default_limits.items()}
        for ch, ceil in limits.items():
            if ch in es.channels and es.channels[ch] > ceil:
                es.channels[ch] = ceil

    def _inject_context_into_state_pool(self, user_message: str) -> list[dict]:
        """构建对话上下文 items（不直接写入，由 tick() 统一批量写入）"""
        if self._runtime is None:
            return []
        items = []
        for i, line in enumerate(self._current_soul.recent_context[-6:]):
            if len(line) < 5:
                continue
            preview = line[:40]
            items.append(
                {
                    "sa_label": f"context::{line[:25]}",
                    "display_text": preview,
                    "family": "conversation_context",
                    "source_type": "recent_context",
                    "real_energy": 0.4 + i * 0.05,
                    "anchor_meta": {"full_text": line},
                }
            )
        items.append(
            {
                "sa_label": f"context::now::{user_message[:25]}",
                "display_text": f"当前: {user_message[:30]}",
                "family": "conversation_context",
                "source_type": "current_input",
                "real_energy": 0.8,
            }
        )
        return items

    def _inject_emotion_pool(self, text: str) -> list[dict]:
        """分析用户消息情绪，返回 state_items（不直接写入，由 tick() 批量写入）"""
        if not text or self._runtime is None:
            return []
        try:
            emotions = analyze_emotions(text)
            if emotions:
                items = emotions_to_state_items(emotions)
                self._emotion_pool_to_nt(emotions)
                return items
        except Exception as e:
            logger.debug(f"emotion pool injection failed: {e}")
        return []

    def _emotion_pool_to_nt(self, emotions: dict[str, float]) -> None:
        """情绪池 → NT 通道联动：从 miya_config.yaml 读取映射"""
        if self._runtime is None:
            return
        es = self._runtime.emotion_modulator.state
        nt_deltas: dict[str, float] = {}
        emotion_nt_map = _FULL_CFG.get("emotion_nt_map", _FALLBACK_EMOTION_NT_MAP)
        clamp = _FULL_CFG.get("emotion_nt_clamp", {})

        for name, val in emotions.items():
            if val > clamp.get("input_threshold", 0.25) and name in emotion_nt_map:
                for ch, delta in emotion_nt_map[name].items():
                    nt_deltas[ch] = nt_deltas.get(ch, 0) + delta * val

        delta_min = clamp.get("delta_min", -0.15)
        delta_max = clamp.get("delta_max", 0.15)
        ch_min = clamp.get("channel_min", 0.02)
        ch_max = clamp.get("channel_max", 1.0)
        for ch, delta in nt_deltas.items():
            if ch in es.channels:
                clamped = max(delta_min, min(delta_max, delta))
                es.channels[ch] = max(ch_min, min(ch_max, es.channels[ch] + clamped))

    def idle_tick(self) -> dict:
        trace = self.tick(text="")

        if self._cortex_enabled and self._cortex is not None:
            if self._proactive_cooldown > 0:
                self._proactive_cooldown -= 1
            else:
                boredom = self._current_soul.feelings.get("boredom", 0)
                if boredom > self._proactive_threshold:
                    self._idle_streak += 1
                    if self._idle_streak >= self._proactive_min_streak:
                        result = self._generate_proactive_message()
                        self._proactive_cooldown = 30
                        return {**trace, "proactive": result}
                else:
                    self._idle_streak = max(0, self._idle_streak - 1)

        return trace

    def _generate_proactive_message(self) -> dict:
        import io
        import sys as _sys

        self._idle_streak = 0
        prompt = self._build_proactive_prompt()
        if not prompt:
            return {"proactive": False}

        saved = _sys.stdout
        _sys.stdout = io.StringIO()
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor() as pool:
                    future = pool.submit(
                        lambda: asyncio.new_event_loop().run_until_complete(self._cortex.render(prompt, ""))
                    )
                    result = future.result(timeout=15)
            else:
                result = loop.run_until_complete(self._cortex.render(prompt, ""))
        except Exception:
            return {"proactive": False}
        finally:
            _sys.stdout = saved

        return {"proactive": True, "message": result.text.strip() if result.success else ""}

    def _build_proactive_prompt(self) -> str:
        from miya_psyarch.cortex.prompt_builder import get_identity_prompt

        identity = get_identity_prompt(self._personality_form)
        s = self._current_soul
        boredom = s.feelings.get("boredom", 0)
        mood = (
            _PROACTIVE.get("boredom_high_label", "很无聊")
            if boredom > 0.85
            else _PROACTIVE.get("boredom_mid_label", "有点无聊")
        )
        return f"""{identity}

弥娅当前状态: {mood}。
弥娅想主动找佳说话。不要说\"在吗\"\"干嘛呢\"。
像真的想念他一样自然地开口。1-2句。"""

    def chat(self, user_message: str, *, idle_ticks: int = 0, form: str | None = None) -> str:
        for _ in range(idle_ticks):
            self.idle_tick()
        self.tick(text=user_message)
        effective_form = form if form is not None else self._personality_form
        return self._render_response(user_message, effective_form)

    def set_form(self, form: str | None) -> None:
        """切换弥娅的当前形态"""
        self._personality_form = form

    def chat_async(self, user_message: str, *, idle_ticks: int = 0) -> tuple[str, CortexResult]:
        """异步版 chat，返回 (回复文本, CortexResult)。"""
        for _ in range(idle_ticks):
            self.idle_tick()
        self.tick(text=user_message)

        if self._cortex is None or not self._cortex_enabled:
            text = self._cortex.select_fallback(self._current_soul) if self._cortex else ""
            self._current_soul.llm_response = text
            return text, CortexResult(text=text, success=False, error="cortex disabled")

        system_prompt, user_prompt = self._cortex.build_prompt(self._current_soul, user_message)

        result = asyncio.get_event_loop().run_until_complete(self._cortex.render(system_prompt, user_prompt))

        if result.success:
            self._current_soul.llm_response = result.text
            self._current_soul.llm_model = result.model_used
            self._current_soul.llm_latency_ms = result.latency_ms
        else:
            fallback = self._cortex.select_fallback(self._current_soul)
            self._current_soul.llm_response = fallback
            result.text = fallback

        return self._current_soul.llm_response, result

    def _render_response(self, user_message: str, form: str | None = None) -> str:
        """同步渲染弥娅回复（内部使用）。"""
        import sys

        if self._cortex is None or not self._cortex_enabled:
            fallback = self._cortex.select_fallback(self._current_soul) if self._cortex else ""
            self._current_soul.llm_response = fallback
            return fallback

        # 从 AP 注意力提取被 Bn/Cn 召回的記憶
        self._tick_memory_context(user_message)
        if len(self._current_soul.recent_context) > 20:
            self._current_soul.recent_context = self._current_soul.recent_context[-16:]

        system_prompt, user_prompt = self._cortex.build_prompt(
            self._current_soul,
            user_message,
            form=form,
            memory_context=self._memory_context + "\n" + self._memory_fusion.get_memory_context_for_llm(),
        )

        # 多模态上下文
        mm_ctx = self._multimodal.to_llm_context()
        if mm_ctx:
            user_prompt = f"{user_prompt}\n\n{mm_ctx}"
        self._multimodal = MultiModalContext()  # 单次消费

        saved_stdout = sys.stdout
        sys.stdout = io.StringIO()
        try:
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures

                    with concurrent.futures.ThreadPoolExecutor() as pool:
                        future = pool.submit(
                            lambda: asyncio.new_event_loop().run_until_complete(
                                self._cortex.render(system_prompt, user_prompt)
                            )
                        )
                        result = future.result(timeout=20)
                else:
                    result = loop.run_until_complete(self._cortex.render(system_prompt, user_prompt))
            except Exception as e:
                logger.warning(f"LLM render failed: {e}")
                result = CortexResult(error=str(e))
        finally:
            sys.stdout = saved_stdout

        if result.success:
            self._current_soul.llm_response = result.text
            self._current_soul.llm_model = result.model_used
            self._current_soul.llm_latency_ms = result.latency_ms
        else:
            fallback = self._cortex.select_fallback(self._current_soul)
            self._current_soul.llm_response = fallback

        # 生成教育协议：让 AP 从 LLM 回复中学习
        self._generate_education(user_message, self._current_soul.llm_response)

        self._current_soul.recent_context.append(f"弥娅: {self._current_soul.llm_response}")

        return self._current_soul.llm_response

    def _generate_education(self, user_message: str, response: str) -> None:
        """从 LLM 回复生成教育协议信号，教 AP 学习对话模式"""
        if not response or len(response) < 2:
            return
        # 同步分析情绪
        emotions = analyze_emotions(user_message)
        # 打包为教育协议
        edu = package_response_as_education(user_message, response, emotions)
        if isinstance(edu, list):
            self._pending_education.extend(edu)
        elif isinstance(edu, dict):
            self._pending_education.append(edu)

    def soul_state(self) -> MiyaSoulState:
        return self._current_soul

    def _extract_soul(self, trace: dict) -> MiyaSoulState:
        state = MiyaSoulState()
        state.tick_index = trace.get("tick_index", 0)
        state.raw_trace = trace

        attention = trace.get("attention", {})
        state.focus_labels = attention.get("selected_labels", [])[:_FOCUS_SLICE]
        state.focus_texts = [
            item.get("display_text", item.get("sa_label", ""))
            for item in attention.get("selected_items", [])[:_FOCUS_SLICE]
        ]

        feelings = trace.get("cognitive_feelings", {})
        state.feelings = {
            k: round(v, 4) for k, v in feelings.get("channels", {}).items() if isinstance(v, (int, float))
        }

        snapshot_items = trace.get("state_pool", {}).get("snapshot", {}).get("items", [])
        # 先天规则的情绪 (miya_emotion 族)
        innate_emo = [
            item
            for item in snapshot_items
            if str(item.get("family", "")) == "miya_emotion" and str(item.get("sa_label", "")).startswith("miya::")
        ]
        state.miya_feelings = {
            item.get("sa_label", "").replace("miya::", ""): round(item.get("real_energy", 0), 4) for item in innate_emo
        }
        # 记忆召回可视化
        if self._runtime is not None:
            recall_count = 0
            cog_count = 0
            for k, v in self._runtime.state_pool._entries.items():
                if str(v.family) in ("memory_recall", "memory_anchor"):
                    recall_count += 1
                elif str(v.family) == "cognitive_memory":
                    cog_count += 1
            if recall_count > 0:
                state.miya_feelings["回忆:记忆库"] = round(recall_count * 0.2, 2)
            if cog_count > 0:
                state.miya_feelings["认知:思考模式"] = round(cog_count * 0.02, 2)

        # 对话上下文感知
        from miya_psyarch.emotion_pool import EMOTION_CN_MAP

        if self._runtime is not None:
            ctx_count = 0
            for k, v in self._runtime.state_pool._entries.items():
                if str(v.family) == "conversation_context":
                    ctx_count += 1
            if ctx_count > 0:
                state.miya_feelings["对话记忆"] = round(ctx_count * 0.3, 2)

            # 情绪池的情绪
            for k, v in self._runtime.state_pool._entries.items():
                if str(k).startswith("miya_emotion::") and "miya::" not in str(k):
                    name = str(k).replace("miya_emotion::", "")
                    cn = EMOTION_CN_MAP.get(name, name)
                    state.miya_feelings[cn] = round(v.real_energy, 4)

        # 从已钳制的实时情绪状态读取（而非 trace）
        if self._runtime is not None:
            state.emotion_nt = {k: round(v, 4) for k, v in self._runtime.emotion_modulator.state.channels.items()}
        elif trace.get("emotion"):
            em_state = trace["emotion"].get("update", {}).get("emotion_state", {})
            state.emotion_nt = {k: round(v, 4) for k, v in em_state.items() if isinstance(v, (int, float))}

        snapshot = trace.get("state_pool", {}).get("snapshot", {})
        state.state_top = snapshot.get("items", [])[:_STATE_TOP_SLICE]

        text_output = trace.get("text_output", {})
        state.text_output = text_output.get("visible_draft", "") or ""

        action_trace = trace.get("action", {})
        selected = action_trace.get("selected_actions", [])
        output_actions = [a for a in selected if "text_insert" in str(a.get("action_id", ""))]
        state.has_active_intent = len(output_actions) > 0

        return state

    def start_observatory(self, port: int = 8765) -> str:
        if self._observatory is None:
            self._observatory = MiyaObservatory(self, port=port)
        return self._observatory.start()

    def see_image(self, image_bytes: bytes, *, description: str = "") -> VisualPerception:
        perception = perceive_image(image_bytes)
        # 优先用视觉 LLM 描述
        if self._cortex and not description:
            llm_desc = self._cortex.describe_image(image_bytes)
            if llm_desc:
                description = llm_desc
        if description:
            perception.llm_description = description
        self._multimodal.image = perception
        if self._runtime:
            items = image_to_state_items(perception)
            if items:
                self._runtime.state_pool.apply_external_items(items, tick_index=self._runtime.tick_index)
        return perception

    def hear_audio(self, audio_bytes: bytes, *, transcript: str = "") -> AudioPerception:
        perception = perceive_audio(audio_bytes)
        # 优先用 STT 转写
        if self._cortex and not transcript and perception.has_voice:
            stt_text = self._cortex.transcribe_audio(audio_bytes)
            if stt_text:
                transcript = stt_text
        if transcript:
            perception.llm_transcript = transcript
        self._multimodal.audio = perception
        if self._runtime:
            items = audio_to_state_items(perception)
            if items:
                self._runtime.state_pool.apply_external_items(items, tick_index=self._runtime.tick_index)
        return perception

    def clear_multimodal(self) -> None:
        self._multimodal = MultiModalContext()

    def status_report(self) -> dict:
        s = self._current_soul
        return {
            "tick": s.tick_index,
            "focus": s.focus_texts,
            "feelings": s.feelings,
            "miya_feelings": s.miya_feelings,
            "emotion": s.emotion_nt,
            "text_output": s.text_output,
            "llm_response": s.llm_response,
            "llm_model": s.llm_model,
            "llm_latency_ms": s.llm_latency_ms,
            "active_intent": s.has_active_intent,
        }


# ── GPU 监控 ──


def _collect_gpu_stats() -> dict | None:
    """收集 GPU 状态 (NVIDIA NVML + PyTorch CUDA)"""
    gpu = {}

    # 方案A: nvidia-ml-py3 (NVML)
    try:
        import pynvml

        pynvml.nvmlInit()
        device_count = pynvml.nvmlDeviceGetCount()
        gpu["devices"] = device_count
        for i in range(device_count):
            handle = pynvml.nvmlDeviceGetHandleByIndex(i)
            info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            util = pynvml.nvmlDeviceGetUtilizationRates(handle)
            temp = pynvml.nvmlDeviceGetTemperature(handle, pynvml.NVML_TEMPERATURE_GPU)
            gpu[f"gpu{i}"] = {
                "name": pynvml.nvmlDeviceGetName(handle).decode()
                if hasattr(pynvml.nvmlDeviceGetName(handle), "decode")
                else str(pynvml.nvmlDeviceGetName(handle)),
                "mem_total_gb": round(info.total / 1024**3, 1),
                "mem_used_gb": round(info.used / 1024**3, 1),
                "mem_free_gb": round(info.free / 1024**3, 1),
                "gpu_util_pct": util.gpu,
                "mem_util_pct": info.used * 100 // info.total,
                "temp_c": temp,
            }
        pynvml.nvmlShutdown()
        return gpu if gpu.get("devices", 0) > 0 else None
    except ImportError:
        pass
    except Exception:
        pass

    # 方案B: PyTorch CUDA
    try:
        import torch

        if torch.cuda.is_available():
            gpu["devices"] = torch.cuda.device_count()
            for i in range(torch.cuda.device_count()):
                gpu[f"gpu{i}"] = {
                    "name": torch.cuda.get_device_name(i),
                    "mem_allocated_gb": round(torch.cuda.memory_allocated(i) / 1024**3, 2),
                    "mem_reserved_gb": round(torch.cuda.memory_reserved(i) / 1024**3, 2),
                }
            return gpu if gpu.get("devices", 0) > 0 else None
    except ImportError:
        pass
    except Exception:
        pass

    return None

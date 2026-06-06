"""
弥娅心灵引擎 —— APV2.1 认知闭环 + LLM 语言皮层

MiyaEngine 提供两种模式：
1. tick() — 纯 AP 认知，不调用 LLM（弥娅的内心活动）
2. chat() — AP 认知 + LLM 渲染 = 弥娅的完整回复
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from pathlib import Path

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
_CFG_PATH = Path(__file__).resolve().parent / "config" / "miya_config.yaml"
with open(_CFG_PATH, "r", encoding="utf-8") as _f:
    _ENGINE_CFG = (yaml.safe_load(_f) or {}).get("engine", {})

_TICK_HISTORY_MAX = _ENGINE_CFG.get("tick_history_max", 1000)
_TICK_HISTORY_KEEP = _ENGINE_CFG.get("tick_history_keep", 500)
_FOCUS_SLICE = _ENGINE_CFG.get("focus_slice", 5)
_STATE_TOP_SLICE = _ENGINE_CFG.get("state_top_slice", 8)

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
        _p = Path(__file__).resolve().parent / "config" / "miya_config.yaml"
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

    def _inject_memories_into_state_pool(self) -> None:
        """引擎启动时：将弥娅记忆预加载到 AP 状态池，让 Bn/Cn 能自然召回"""
        if self._runtime is None or self._memory_bridge is None:
            return
        all_recent = list(self._memory_bridge._recent)
        if not all_recent:
            return
        items = self._memory_bridge.as_state_items(all_recent[-40:], base_energy=1.2)
        self._runtime.state_pool.apply_external_items(items, tick_index=0)
        logger.info(f"injected {len(items)} memories into state pool")

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
        """初始化并启动心灵引擎"""
        self._runtime = APV21Runtime(
            config=self._config,
            innate_rules=self._miya_rules_list,
        )
        self._apply_miya_emotion_baseline()
        patch_text_sensor(self._runtime)
        self._apply_cognitive_feeling_gains()

        self._memory_bridge = get_memory_bridge()
        self._memory_bridge.warmup(limit=50)
        self._memory_fusion = get_memory_fusion(self)
        self._memory_fusion.load_all()
        self._inject_memories_into_state_pool()
        self._memory_fusion.inject_permanent_anchors()
        self._memory_fusion.inject_cognitive_memories()
        self._memory_context = self._memory_bridge.recent_context_text()

        trace = self._runtime.process_multimodal_tick(text="", trace_mode=self._trace_mode)
        self._ticks.append(trace)
        self._current_soul = self._extract_soul(trace)

    def tick(
        self,
        text: str = "",
        *,
        education_interventions: dict | list[dict] | None = None,
    ) -> dict:
        """推进一次认知 tick（纯 AP 引擎，不调用 LLM）。"""
        if self._runtime is None:
            self.start()

        # 情绪池注入（放在 tick 之前，让 AP 本轮就能感知）
        self._inject_emotion_pool(text)

        # 注入上一轮的教育协议信号
        combined_edu = list(education_interventions or []) + list(self._pending_education)
        self._pending_education = []

        trace = self._runtime.process_multimodal_tick(
            text=text,
            trace_mode=self._trace_mode,
            education_interventions=combined_edu if combined_edu else None,
        )

        # tick 后立即注入当前消息上下文 → Bn/Cn 立即感知
        self._inject_context_into_state_pool(text)

        # 刷新永久锚定（身份/用户事实）→ 确保永不衰减
        self._memory_fusion.inject_permanent_anchors()
        # 刷新认知记忆（弥娅的思考模式）→ Bn/Cn 自然召回
        self._memory_fusion.inject_cognitive_memories()

        # 先钳制 CFS 带来的天花板，再让文本触发生效
        self._clamp_emotion_ceiling()
        self._apply_text_reactions(text)
        self._ticks.append(trace)
        self._current_soul = self._extract_soul(trace)
        record_tick(self)
        if self._observatory is not None:
            self._observatory.set_trace(trace)
        if len(self._ticks) > _TICK_HISTORY_MAX:
            self._ticks = self._ticks[-_TICK_HISTORY_KEEP:]

        if self._current_soul.tick_index % 20 == 0 and text:
            self._inject_memories_into_state_pool()

        return trace

    def _clamp_emotion_ceiling(self) -> None:
        """限制情绪通道天花板，留出波动空间"""
        if self._runtime is None:
            return
        es = self._runtime.emotion_modulator.state
        # 每个通道设置硬限制
        limits = {
            "OXY": 0.50,
            "SER": 0.45,
            "DA": 0.45,
            "FOC": 0.40,
        }
        for ch, ceil in limits.items():
            if ch in es.channels and es.channels[ch] > ceil:
                es.channels[ch] = ceil

    def _inject_context_into_state_pool(self, user_message: str) -> None:
        """将对话上下文注入 AP 状态池——让 Bn/Cn 能\"回忆\"最近对话"""
        if self._runtime is None:
            return
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
                    "real_energy": 0.4 + i * 0.05,  # 越近越高
                    "anchor_meta": {"full_text": line},
                }
            )
        # 当前消息最高能量
        items.append(
            {
                "sa_label": f"context::now::{user_message[:25]}",
                "display_text": f"当前: {user_message[:30]}",
                "family": "conversation_context",
                "source_type": "current_input",
                "real_energy": 0.8,
            }
        )
        if items:
            self._runtime.state_pool.apply_external_items(items, tick_index=self._runtime.tick_index)

    def _inject_emotion_pool(self, text: str) -> None:
        """用 SoulGenerator 分析用户消息，将 70+ 情绪注入 AP 状态池"""
        if not text or self._runtime is None:
            return
        try:
            emotions = analyze_emotions(text)
            if emotions:
                items = emotions_to_state_items(emotions)
                self._runtime.state_pool.apply_external_items(items, tick_index=self._runtime.tick_index)
        except Exception as e:
            logger.debug(f"emotion pool injection failed: {e}")

    def _apply_text_reactions(self, text: str) -> None:
        """根据输入文本中的触发词直接调整 AP 情绪 (保留做补充)"""
        if not text or self._runtime is None:
            return
        es = self._runtime.emotion_modulator.state
        text_lower = text.lower()

        triggers = {
            ("可爱", "喜欢", "爱你", "想你了", "真美"): {"OXY": 0.10, "DA": 0.08, "END": 0.06},
            ("累", "难过", "疼", "哭", "不开心", "伤心"): {"OXY": 0.06, "SER": -0.04},
            ("烦", "滚", "讨厌", "恶心"): {"COR": 0.10, "OXY": -0.08},
            ("好笑", "哈哈", "笑死", "有趣"): {"DA": 0.08, "END": 0.05, "NOV": 0.06},
            ("惊讶", "什么", "真的", "居然"): {"NOV": 0.10, "ADR": 0.05},
        }

        for words, effects in triggers.items():
            if any(w in text_lower for w in words):
                for ch, delta in effects.items():
                    if ch in es.channels:
                        es.channels[ch] = min(1.0, max(0.0, es.channels[ch] + delta))
                break

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
        import io, sys as _sys

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
        nt = s.emotion_nt
        mood = "很无聊" if boredom > 0.85 else "有点无聊"
        oxy = nt.get("OXY", 0)

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
        import io, sys

        if self._cortex is None or not self._cortex_enabled:
            fallback = self._cortex.select_fallback(self._current_soul) if self._cortex else ""
            self._current_soul.llm_response = fallback
            return fallback

        # 注入对话上下文到 AP 状态池 (下一次 tick 可被 Bn/Cn 召回)
        self._inject_context_into_state_pool(user_message)

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
            "state_items_count": len(s.state_top),
        }

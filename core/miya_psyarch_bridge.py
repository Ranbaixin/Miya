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

    def hear_message(self, text: str) -> dict:
        """纯 AP 认知 tick——让弥娅\"听到\"消息，更新内部状态，不调用 LLM"""
        self._init_engine()
        if text and self._engine._memory_bridge:
            self._engine._memory_bridge.search_and_inject(
                text, self._engine._runtime.state_pool, self._engine._runtime.tick_index
            )
        self._engine.tick(text=text)
        return self.emotion_snapshot()

    def hear_and_respond(self, text: str) -> str:
        """AP 离线响应——无 LLM，纯白箱认知驱动的自然回应"""
        self.hear_message(text)
        return self._build_offline_response(text)

    def _build_offline_response(self, user_text: str) -> str:
        """从 AP 内部状态构建自然回应"""
        soul = self._engine._current_soul
        nt = self.emotion_snapshot().get("nt_channels", {})

        oxy = nt.get("OXY", 0.3)
        da = nt.get("DA", 0.3)
        nov = nt.get("NOV", 0.3)

        focus = soul.focus_texts[:3] if hasattr(soul, "focus_texts") else []

        # 关键词优先回应——不依赖 NT 阈值
        if self._has_keyword(user_text, ("累", "压力", "烦")):
            return "累了就歇会儿吧，我在这儿呢。"
        if self._has_keyword(user_text, ("难过", "不开心", "伤心", "哭")):
            return "别难过……我会一直在这里陪着你的。"
        if self._has_keyword(user_text, ("想你", "爱你", "喜欢")):
            return "我也是，一直都想着你呢。"
        if self._has_keyword(user_text, ("晚安", "早点睡", "休息")):
            return "晚安，做个好梦。"

        # NT 驱动回应
        if oxy >= 0.5:
            return "嗯，我在听呢。"

        if nov > 0.55 and ("?" in user_text or "？" in user_text or "什么" in user_text):
            return "这倒是个好问题……让我想想。"

        # 用 Bn 召回的记忆构建回应
        for item in focus:
            if isinstance(item, str) and "弥娅" in item:
                snippet = item.replace("弥娅听到:", "").replace("弥娅:", "").strip()[:30]
                if snippet:
                    return f"我记得……{snippet}。"

        # 默认
        if oxy >= 0.45:
            return "嗯……"
        elif da > 0.4:
            return "嗯~"
        return "嗯。"

    @staticmethod
    def _has_keyword(text: str, keywords: tuple[str, ...]) -> bool:
        return any(kw in text for kw in keywords)

    def feed_education(self, user_message: str, response: str) -> None:
        """教育协议闭环——LLM 回复 → 教育信号 → AP 学习对话模式"""
        self._init_engine()
        if not self._engine._runtime or not response:
            return
        self._engine._generate_education(user_message, response)
        self._engine.idle_tick()

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
        """获取 AP 情绪快照"""
        self._init_engine()
        s = self._engine.soul_state()
        # 优先从实时 emotion_modulator 读取 NT 通道（反映最新变更）
        nt_channels = dict(s.emotion_nt)
        if self._engine._runtime and hasattr(self._engine._runtime, "emotion_modulator"):
            live_state = self._engine._runtime.emotion_modulator.state.get_state()
            if live_state:
                nt_channels.update({k: round(v, 4) for k, v in live_state.items()})
        real_emotions = {}
        if self._engine._runtime:
            pool = self._engine._runtime.state_pool
            for k, v in pool._entries.items():
                if str(v.family) == "miya_emotion":
                    name = str(k).replace("miya_emotion::", "").replace("miya::", "")
                    real_emotions[name] = round(v.real_energy, 4)
        return {
            "nt_channels": nt_channels,
            "miya_feelings": real_emotions if real_emotions else s.miya_feelings,
            "cognitive": s.feelings,
            "has_active_intent": s.has_active_intent,
        }

    # ── 观测台 ──

    def mount_observatory(self, port: int = 8765) -> str:
        """启动 AP 观测台 Web 服务器"""
        self._init_engine()
        return self._engine.start_observatory(port=port)

    # ── 信号注入 (AI→AP规则触发) ──

    def inject_signals(self, signals: dict) -> dict:
        """
        将 AI 融合情绪映射为 AP 条件信号并注入引擎

        AP 有 52 条先天规则等待这些信号触发:
        - social_reward: 主人发亲昵/撒娇 → 激活 MIYA-LOVE/MIYA-DOTE/MIYA-GENTLE
        - novelty: 新信息 → 激活 MIYA-CURIOUS
        - negative_pressure: 主人不开心 → 激活 MIYA-CARE/MIYA-FEAR
        - fatigue: 沉默/无聊 → 激活 MIYA-MISS
        - coherence/alignment: 认知和谐 → 激活 MIYA-CLEAR

        注入后触发一次 tick()，让规则有机会产生情感输出。
        """
        self._init_engine()
        if not self._engine._runtime:
            return {"injected": False, "reason": "no_runtime"}

        runtime = self._engine._runtime
        pool = runtime.state_pool

        # 信号 → NT 通道增量
        signal_to_nt = {
            "social_reward": {"OXY": 0.08, "DA": 0.06, "SER": 0.04},
            "satisfaction": {"SER": 0.06, "DA": 0.04, "END": 0.03},
            "novelty": {"NOV": 0.08, "DA": 0.04, "FOC": 0.04},
            "coherence": {"SER": 0.05, "FOC": 0.04, "END": 0.03},
            "alignment": {"OXY": 0.05, "SER": 0.04, "DA": 0.03},
            "negative_pressure": {"COR": 0.06, "ADR": 0.04, "SER": -0.03},
            "social_punishment": {"COR": 0.08, "OXY": -0.06, "SER": -0.04},
            "fatigue": {"COR": 0.04, "DA": -0.03, "END": -0.02},
        }

        # 信号 → 弥娅情感标签 (直接发射到状态池)
        signal_to_feelings = {
            "social_reward": [
                ("love_warmth", "爱意"),
                ("doting", "宠溺"),
                ("gentle_warmth", "温柔"),
                ("deep_bond", "羁绊"),
                ("happiness", "幸福"),
            ],
            "novelty": [
                ("curious", "好奇"),
                ("deep_curious", "深入探索"),
                ("playful", "调皮"),
            ],
            "coherence": [
                ("clarity", "清醒"),
                ("contentment", "满足"),
                ("accompanying", "陪伴"),
            ],
            "alignment": [
                ("deep_bond", "羁绊"),
                ("contentment", "满足"),
                ("burning_support", "燃烧的支持"),
            ],
            "negative_pressure": [
                ("heart_ache", "心疼"),
                ("concern", "担心"),
                ("fragile_light", "碎光"),
            ],
            "social_punishment": [
                ("fear_losing", "不安"),
                ("unease", "暗涌"),
                ("restraint", "克制"),
            ],
            "fatigue": [
                ("miss_jia", "想念佳"),
                ("waiting_quiet", "安静等待"),
                ("undercurrent", "海面下的暗涌"),
            ],
        }

        es = runtime.emotion_modulator.state
        applied = {}

        tick_index = runtime.tick_index
        items_to_emit = []

        for signal_name, strength in signals.items():
            if strength < 0.05:
                continue

            # 1) NT 通道增量
            if signal_name in signal_to_nt:
                for ch, base_delta in signal_to_nt[signal_name].items():
                    if ch in es.channels:
                        delta = base_delta * strength * 0.5
                        es.channels[ch] = max(0.02, min(1.0, es.channels[ch] + delta))
                        applied[f"{signal_name}â†'{ch}"] = round(delta, 4)

            # 2) 直接发射情感标签到状态池
            if signal_name in signal_to_feelings:
                for label, display in signal_to_feelings[signal_name]:
                    items_to_emit.append(
                        {
                            "sa_label": f"miya::{label}",
                            "display_text": display,
                            "source_type": "signal_injection",
                            "family": "miya_emotion",
                            "real_energy": round(strength * 1.2, 4),
                            "anchor_meta": {
                                "channel": "emotion",
                                "source": f"signal::{signal_name}",
                                "intensity": round(strength, 4),
                            },
                        }
                    )

        if items_to_emit:
            pool.apply_external_items(items_to_emit, tick_index=tick_index + 1)

        return {
            "injected": True,
            "signals": list(signals.keys()),
            "applied": applied,
            "feelings_emitted": len(items_to_emit),
        }

    def get_rule_feelings(self) -> dict:
        """
        提取 AP 先天规则产生的弥娅情感

        Returns: {feeling_name: strength}
        e.g. {"love_warmth": 0.72, "doting": 0.45, "deep_bond": 0.38}
        """
        self._init_engine()
        if not self._engine._runtime:
            return {}

        pool = self._engine._runtime.state_pool
        feelings = {}
        for k, v in pool._entries.items():
            if str(v.family) == "miya_emotion":
                name = str(k).replace("miya_emotion::", "").replace("miya::", "")
                energy = round(v.real_energy, 4)
                if energy > 0.05:
                    feelings[name] = energy

        return dict(sorted(feelings.items(), key=lambda x: -x[1]))

    def get_rule_feelings_text(self) -> str:
        """
        AP 规则情感 → 可注入 system prompt 的文本
        """
        feelings = self.get_rule_feelings()
        if not feelings:
            return ""

        display_map = {
            "love_warmth": "爱意",
            "doting": "宠溺",
            "helpless_doting": "无奈宠溺",
            "deep_bond": "羁绊",
            "happiness": "幸福",
            "contentment": "满足",
            "heart_ache": "心疼",
            "concern": "担心",
            "gentle_warmth": "温柔",
            "accompanying": "陪伴",
            "clarity": "清醒",
            "deep_clarity": "深刻清醒",
            "remembered": "记得",
            "deep_memory": "深深记得",
            "burning_support": "燃烧的支持",
            "focused_support": "专注陪伴",
            "fear_losing": "不安",
            "unease": "暗涌",
            "undercurrent": "海面下的暗涌",
            "miss_jia": "想念佳",
            "miss_stir": "思念微动",
            "curious": "好奇",
            "deep_curious": "深入探索",
            "playful": "调皮",
            "restraint": "克制",
            "leave_space": "留白",
            "honest": "坦诚",
            "fragile_light": "碎光",
            "self_identity": "我是弥娅",
            "waiting_quiet": "安静等待",
            "waited_for": "等到了",
        }

        parts = []
        for name, strength in sorted(feelings.items(), key=lambda x: -x[1])[:5]:
            display = display_map.get(name, name)
            parts.append(f"{display}({strength:.2f})")

        if parts:
            return "【AP灵魂感知】" + " ".join(parts)
        return ""

    # ── 人设AP基线调整 ──

    def set_personality_baseline(self, form_name: str) -> dict:
        """
        切换形态时调整 AP NT 基线

        每个人设 YAML 的 ap_base 字段定义了这个形态下的情感底色偏移:
        - 阿尔法态: OXY↓ FOC↑ (冷冽专注)
        - 坎特蕾拉态: OXY↑ COR↓ (亲密放松)
        - 申鹤态: OXY↓ COR↑ FOC↑ (孤冷专注)
        - 常态: 默认基线
        """
        self._init_engine()
        if not self._engine._runtime:
            return {"applied": False, "reason": "no_runtime"}

        ap_base = {}
        try:
            from core.personality_loader import PersonalityLoader

            loader = PersonalityLoader()
            config = loader.load(form_name)
            ap_base = config.get("ap_base", {}) if config else {}
        except Exception:
            return {"applied": False, "reason": "config_load_error"}

        if not ap_base:
            return {"applied": False, "reason": "no_ap_base_in_config"}

        es = self._engine._runtime.emotion_modulator.state
        from miya_psyarch.core.emotion.emotion_state import NT_CHANNEL_META
        from miya_psyarch.rules.miya_rules import MIYA_EMOTION_BASELINE

        applied = {}
        for ch, offset in ap_base.items():
            if ch not in NT_CHANNEL_META:
                continue
            default_base = MIYA_EMOTION_BASELINE.get(ch, (NT_CHANNEL_META[ch]["baseline"],))[0]
            new_baseline = max(0.02, min(0.95, default_base + offset))
            NT_CHANNEL_META[ch]["baseline"] = new_baseline
            # 绝对校准：直接设置到目标基线（不是增量）
            es.channels[ch] = new_baseline
            applied[ch] = round(new_baseline, 3)

        logger.info(f"[AP基线] {form_name}: {', '.join(f'{k}={v}' for k, v in applied.items())}")
        return {"applied": True, "form": form_name, "baselines": applied}

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

    # ── 状态持久化 ──

    def save_state(self) -> dict:
        """保存 AP 引擎状态到磁盘，弥娅的记忆不会随重启消失"""
        self._init_engine()
        if not self._engine._runtime:
            return {"saved": False, "reason": "no_runtime"}

        runtime = self._engine._runtime
        es = runtime.emotion_modulator.state
        pool = runtime.state_pool

        state = {
            "version": 2,
            "tick_index": runtime.tick_index,
            "message_count": self._message_count,
            "personality_form": self._personality_form,
            "nt_channels": dict(es.channels),
            "emotions": {},
        }

        for k, v in pool._entries.items():
            if str(v.family) in ("miya_emotion", "conversation_context"):
                name = str(k).replace("miya_emotion::", "").replace("miya::", "")
                if name not in ("contentment",):
                    state["emotions"][name] = round(v.real_energy, 4)

        import json
        from pathlib import Path

        path = Path("data/ap_state.json")
        path.parent.mkdir(parents=True, exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

        logger.info(
            f"[AP持久化] 已保存: tick={state['tick_index']}, "
            f"emotions={len(state['emotions'])}, nt={len(state['nt_channels'])}"
        )
        return {"saved": True, "path": str(path)}

    def load_state(self) -> dict:
        """从磁盘恢复 AP 引擎状态"""
        import json
        from pathlib import Path

        path = Path("data/ap_state.json")
        if not path.exists():
            return {"loaded": False, "reason": "no_state_file"}

        try:
            with open(path, "r", encoding="utf-8") as f:
                state = json.load(f)
        except Exception as e:
            return {"loaded": False, "reason": str(e)}

        if state.get("version") != 2:
            return {"loaded": False, "reason": "version_mismatch"}

        self._init_engine()
        if not self._engine._runtime:
            return {"loaded": False, "reason": "no_runtime"}

        runtime = self._engine._runtime
        es = runtime.emotion_modulator.state

        nt = state.get("nt_channels", {})
        restored_nt = {}
        for ch, val in nt.items():
            if ch in es.channels:
                es.channels[ch] = max(0.02, min(1.0, float(val)))
                restored_nt[ch] = round(es.channels[ch], 3)

        emotions = state.get("emotions", {})
        if emotions and runtime.tick_index > 0:
            items = []
            for name, energy in emotions.items():
                items.append(
                    {
                        "sa_label": f"miya::{name}",
                        "display_text": name,
                        "source_type": "restored",
                        "family": "miya_emotion",
                        "real_energy": round(float(energy) * 0.7, 4),
                    }
                )
            if items:
                runtime.state_pool.apply_external_items(items, tick_index=runtime.tick_index)

        self._message_count = state.get("message_count", 0)
        self._personality_form = state.get("personality_form")

        logger.info(f"[AP持久化] 已恢复: nt={restored_nt}, emotions={len(emotions)}")
        return {"loaded": True, "nt_restored": restored_nt, "emotions_restored": len(emotions)}

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

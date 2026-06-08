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

# 加载 miya_config.yaml
try:
    import yaml
    from pathlib import Path

    _BRIDGE_CFG = {}
    _CFG_P = Path(__file__).resolve().parent.parent / "config" / "miya_config.yaml"
    if _CFG_P.exists():
        _BRIDGE_CFG = yaml.safe_load(_CFG_P.read_text(encoding="utf-8")) or {}
except Exception:
    _BRIDGE_CFG = {}

_FALLBACK_FEELING_LABELS = {
    "love_warmth": "爱意",
    "doting": "宠溺",
    "deep_bond": "羁绊",
    "happiness": "幸福",
    "contentment": "满足",
    "heart_ache": "心疼",
    "concern": "担心",
    "gentle_warmth": "温柔",
    "accompanying": "陪伴",
    "fear_losing": "不安",
    "remembered": "记得",
    "deep_memory": "深深记得",
}

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
        self._platform_sender: callable | None = None
        self._current_trace: dict | None = None
        self._heartbeat_thread: threading.Thread | None = None
        self._heartbeat_running = False
        self.memory_protection: bool = True  # True=永不清理任何记忆

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
        self._register_toolnet_actions()
        self._initialized = True
        logger.info("MiyaPsyArchBridge initialized")

    def _register_toolnet_actions(self) -> None:
        try:
            from miya_psyarch.action_bridge import register_miya_actions_to_ap

            count = register_miya_actions_to_ap(self._engine)
            if count > 0:
                logger.info(f"[AP] ActionPlanner 已接入 ToolNet: {count} 个工具注册为行动节点")
        except Exception as e:
            logger.debug(f"[AP] ActionPlanner 接入 ToolNet 跳过: {e}")

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
        """教育协议闭环——LLM 回复 → 教育信号 → AP 真正学习 + 记忆同步"""
        self._init_engine()
        if not self._engine._runtime or not response:
            return
        self._engine._generate_education(user_message, response)
        self._engine.idle_tick()
        self._accumulate_education_history(response)
        self._sync_significant_memory(user_message, response)

    def _sync_significant_memory(self, user_message: str, response: str) -> None:
        """将重要对话记忆从 AP 同步写入 Miya 统一记忆系统"""
        if not hasattr(self, "_sync_counter"):
            self._sync_counter = 0
        self._sync_counter += 1
        if self._sync_counter % 10 != 0:  # 每 10 条同步一次
            return
        try:
            from memory import get_memory_core
            import asyncio

            async def _store():
                core = await get_memory_core()
                snap = self.emotion_snapshot()
                nt = snap.get("nt_channels", {})
                oxy = nt.get("OXY", 0)
                cor = nt.get("COR", 0)
                tags = ["ap_sync"]
                if oxy > 0.35:
                    tags.append("positive")
                if cor > 0.35:
                    tags.append("tense")
                await core.store_memory(
                    content=f"[弥娅记忆] {user_message[:60]} → {response[:60]}",
                    importance=0.5 + oxy * 0.3,
                    tags=tags,
                    source="ap_memory_sync",
                )

            try:
                loop = asyncio.get_running_loop()
                loop.call_soon_threadsafe(lambda: asyncio.ensure_future(_store()))
            except RuntimeError:
                pass
        except Exception:
            pass

    def _accumulate_education_history(self, response: str) -> None:
        """累积教育记录，用于调整先天规则敏感度和 NT 基线"""
        if not hasattr(self, "_edu_history"):
            self._edu_history: list[dict] = []
            self._edu_total_reward = 0.0
            self._edu_message_count = 0
        self._edu_message_count += 1
        response_len = len(response)
        quality = min(1.0, response_len / 80.0) if response_len > 8 else 0.3
        self._edu_total_reward += quality
        self._edu_history.append({"len": response_len, "quality": quality, "count": self._edu_message_count})
        if len(self._edu_history) > 100:
            self._edu_history = self._edu_history[-50:]
        # 每 20 轮优质对话，微调 NT 基线
        if self._edu_message_count % 20 == 0 and self._edu_total_reward > 15.0:
            self._apply_education_nt_shift()

    def _apply_education_nt_shift(self) -> None:
        """教育积累足够后，微调 NT 通道基线"""
        runtime = self._engine._runtime
        if not runtime:
            return
        es = runtime.emotion_modulator.state
        avg_quality = self._edu_total_reward / max(1, self._edu_message_count)
        shift = min(0.03, avg_quality * 0.02)
        channels_to_boost = ["OXY", "SER", "END"]
        for ch in channels_to_boost:
            if ch in es.baselines:
                es.baselines[ch] = min(0.50, es.baselines[ch] + shift)
        logger.info(
            f"[AP教育] 累计{self._edu_message_count}轮对话, "
            f"质量={avg_quality:.2f}, NT基线微调 +{shift:.3f} → OXY/SER/END"
        )
        self._edu_total_reward = 0.0
        self._edu_message_count = 0

    def education_stats(self) -> dict:
        """获取教育统计"""
        return {
            "message_count": getattr(self, "_edu_message_count", 0),
            "total_reward": round(getattr(self, "_edu_total_reward", 0.0), 3),
            "history_len": len(getattr(self, "_edu_history", [])),
            "last_nt_baselines": {
                ch: round(v, 3) for ch, v in self._engine._runtime.emotion_modulator.state.baselines.items()
            }
            if self._engine._runtime
            else {},
        }

    def perf_stats(self) -> dict:
        """AP tick 性能统计 (火焰图数据)"""
        self._init_engine()
        if not self._engine._runtime:
            return {"ready": False}
        return self._engine.perf_stats()

    def trigger_memory_compression(self) -> dict:
        """触发记忆潮汐压缩——睡眠/闲置阶段的认知清理。仅删除极低能量的临时条目。"""
        self._init_engine()
        if not self._engine._runtime:
            return {"compressed": False, "reason": "no_runtime"}
        try:
            pool = self._engine._runtime.state_pool
            before = len(pool._entries)
            stale_cutoff = self._engine._runtime.tick_index - 50
            purged = 0
            for k, v in list(pool._entries.items()):
                if v.real_energy < 0.15 and v.family not in ("memory_anchor", "cognitive_memory"):
                    purged += 1
                    del pool._entries[k]
            self._engine.idle_tick()
            after = len(pool._entries)
            return {
                "compressed": True,
                "before": before,
                "after": after,
                "purged": purged,
                "stale_cutoff": stale_cutoff,
            }
        except Exception as e:
            return {"compressed": False, "error": str(e)}

    def _soft_decay_weak_entries(self) -> None:
        """轻量降权：仅降低临时对话上下文的能量，不删除任何记忆"""
        if not self._engine._runtime:
            return
        pool = self._engine._runtime.state_pool
        decayed = 0
        for k, v in list(pool._entries.items()):
            if v.family not in ("memory_anchor", "cognitive_memory") and v.real_energy < 0.15:
                v.real_energy = max(0.01, v.real_energy * 0.5)
                decayed += 1
        if decayed > 0:
            logger.debug(f"[AP记忆] 轻量降权: {decayed} 条低能量临时条目降权")

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
        compression_counter = 0
        while self._heartbeat_running:
            try:
                for _ in range(ticks_per_interval):
                    trace = self._engine.idle_tick()
                    self._current_trace = trace
                    if isinstance(trace, dict):
                        proactive = trace.get("proactive", {})
                        if proactive.get("proactive"):
                            msg = proactive.get("message", "")
                            if msg:
                                if self._proactive_callback:
                                    self._proactive_callback(msg)
                                if hasattr(self, "_platform_sender") and self._platform_sender:
                                    try:
                                        self._platform_sender(msg)
                                    except Exception:
                                        pass
                # 每 60 次心跳 (约5分钟) 轻量降权 (受 memory_protection 保护)
                compression_counter += 1
                if compression_counter % 60 == 0 and not self.memory_protection:
                    try:
                        self._soft_decay_weak_entries()
                    except Exception:
                        pass
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

    def cognitive_state(self) -> dict:
        """获取 AP 完整认知状态（注意力/认知感受/聚焦/记忆召回）"""
        self._init_engine()
        if not self._engine._runtime:
            return {"ready": False}

        runtime = self._engine._runtime
        trace = self._current_trace if hasattr(self, "_current_trace") else {}

        focus_labels = []
        focus_texts = []
        if hasattr(self._engine, "_current_soul"):
            soul = self._engine._current_soul
            focus_labels = soul.focus_labels[:10] if hasattr(soul, "focus_labels") else []
            focus_texts = soul.focus_texts[:10] if hasattr(soul, "focus_texts") else []

        cfs = {}
        if hasattr(runtime, "cognitive_feelings"):
            cf = runtime.cognitive_feelings
            for attr in ("surprise", "coherence", "dissonance", "correctness", "grasp", "expectation", "pressure"):
                val = round(getattr(cf, attr, 0), 4)
                if abs(val) > 0.01:
                    cfs[attr] = val

        recalled = trace.get("attention", {}).get("selected_items", [])
        recalled_texts = []
        for item in recalled[:5]:
            content = item.get("display_text", "") or item.get("anchor_meta", {}).get("full_content", "")
            if content:
                recalled_texts.append(str(content)[:80])

        rhythm_state = {}
        if hasattr(runtime, "rhythm"):
            r = runtime.rhythm
            for attr in ("burst_count", "interval_avg", "phase"):
                if hasattr(r, attr):
                    rhythm_state[attr] = getattr(r, attr)

        return {
            "ready": True,
            "focus_labels": focus_labels,
            "focus_texts": focus_texts,
            "cognitive_feelings": cfs,
            "recalled_memories": recalled_texts,
            "rhythm": rhythm_state,
        }

    def channels_state(self) -> dict:
        """获取 AP 5条感知通道的完整状态"""
        self._init_engine()
        if not self._engine._runtime:
            return {"ready": False}

        runtime = self._engine._runtime
        state = {"ready": True}

        if hasattr(runtime, "runtime_load") and runtime.runtime_load:
            load = runtime.runtime_load
            state["runtime_load"] = {
                "complexity": round(getattr(load, "complexity", 0), 3),
                "simplicity": round(getattr(load, "simplicity", 0), 3),
            }
        if hasattr(runtime, "rhythm") and runtime.rhythm:
            r = runtime.rhythm
            state["rhythm"] = {
                "burst_count": getattr(r, "burst_count", 0),
                "interval_avg": round(getattr(r, "interval_avg", 0.0), 2),
                "phase": getattr(r, "phase", "idle"),
            }
        if hasattr(runtime, "time_feeling") and runtime.time_feeling:
            t = runtime.time_feeling
            state["time"] = {
                "elapsed_text": getattr(t, "elapsed_text", ""),
                "time_pressure": round(getattr(t, "time_pressure", 0.0), 3),
            }
        if hasattr(runtime, "expectation_pressure"):
            ep = runtime.expectation_pressure
            state["expectation_pressure"] = {
                "expectation": round(getattr(ep, "expectation", 0), 3),
                "pressure": round(getattr(ep, "pressure", 0), 3),
                "fulfillment": round(getattr(ep, "fulfillment", 0), 3),
            }
        if hasattr(runtime, "task_feeling") and runtime.task_feeling:
            tf = runtime.task_feeling
            state["task"] = {
                "boredom": round(getattr(tf, "boredom", 0), 3),
                "fulfillment": round(getattr(tf, "fulfillment", 0), 3),
                "task_available": round(getattr(tf, "task_available", 0), 3),
            }

        return state

    def set_platform_sender(self, sender: callable) -> None:
        """设置跨平台主动消息发送路由"""
        self._platform_sender = sender

    def feed_visual(self, image_bytes: bytes, description: str = "") -> dict:
        """注入视觉感知到 AP 状态池"""
        self._init_engine()
        if not self._engine._runtime:
            return {"injected": False}
        try:
            from miya_psyarch.multimodal import perceive_image

            vis = perceive_image(image_bytes) if image_bytes else None
            items = []
            if vis:
                items.append(
                    {
                        "sa_label": "visual::scene",
                        "display_text": f"画面: {vis.llm_description or description or '场景'}"[:40],
                        "family": "multimodal_visual",
                        "real_energy": 0.6,
                        "anchor_meta": {
                            "brightness": vis.avg_brightness,
                            "complexity": vis.complexity,
                            "description": vis.llm_description or description,
                        },
                    }
                )
            if items:
                self._engine._runtime.state_pool.apply_external_items(
                    items, tick_index=self._engine._runtime.tick_index
                )
            return {
                "injected": bool(items),
                "brightness": vis.avg_brightness if vis else 0,
                "complexity": vis.complexity if vis else 0,
            }
        except Exception as e:
            return {"injected": False, "error": str(e)}

    def feed_audio(self, audio_bytes: bytes, transcription: str = "") -> dict:
        """注入音频感知到 AP 状态池"""
        self._init_engine()
        if not self._engine._runtime:
            return {"injected": False}
        try:
            from miya_psyarch.multimodal import perceive_audio

            aud = perceive_audio(audio_bytes) if audio_bytes else None
            items = []
            if aud:
                items.append(
                    {
                        "sa_label": "audio::capture",
                        "display_text": f"音频: {aud.transcription or transcription or '声音'}"[:40],
                        "family": "multimodal_audio",
                        "real_energy": 0.5,
                        "anchor_meta": {
                            "duration_s": aud.duration_s,
                            "amplitude": aud.rms_amplitude,
                            "transcription": aud.transcription or transcription,
                        },
                    }
                )
            if items:
                self._engine._runtime.state_pool.apply_external_items(
                    items, tick_index=self._engine._runtime.tick_index
                )
            return {"injected": bool(items), "duration_s": aud.duration_s if aud else 0}
        except Exception as e:
            return {"injected": False, "error": str(e)}

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
        """AP 规则情感 → 可注入 system prompt 的文本 (从配置读取展式名)"""
        feelings = self.get_rule_feelings()
        if not feelings:
            return ""
        display_map = _BRIDGE_CFG.get("feeling_display_names", _FALLBACK_FEELING_LABELS)

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
            "cognitive_feelings": {
                k: round(v, 4) for k, v in self.cognitive_state().get("cognitive_feelings", {}).items()
            },
            "education": {
                "msg_count": getattr(self, "_edu_message_count", 0),
                "total_reward": round(getattr(self, "_edu_total_reward", 0.0), 3),
            },
        }

        # 心跳状态
        try:
            idle_streak = getattr(self._engine, "_proactive_cooldown", 0)
            state["idle_streak"] = idle_streak
            ch = self.channels_state()
            if ch.get("rhythm"):
                state["rhythm"] = ch["rhythm"]
            if ch.get("task"):
                state["task"] = ch["task"]
        except Exception:
            pass

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

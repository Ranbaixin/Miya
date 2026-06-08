"""AP 上下文注入器 — 将 APV2.1 认知引擎状态注入 LLM 提示词"""

from __future__ import annotations

import logging

logger = logging.getLogger("Miya.APContext")


def inject_ap_context(personality_info: dict) -> None:
    """将 AP 全部状态注入 personality_info（原地修改）

    personality_info 中新增:
    - ap_state:      NT通道 + 感受 + 认知 + 记忆 + 通道状态
    - multimodal_context: 视觉/音频融合上下文
    """
    try:
        from core.miya_psyarch_bridge import get_psyarch_bridge

        bridge = get_psyarch_bridge()
        if not bridge or not bridge._initialized:
            return

        ap_hint = ""
        emo = bridge.emotion_snapshot()
        if emo:
            nt = emo.get("nt_channels", {})
            mf = emo.get("miya_feelings", {})
            parts = [f"AP:OXY={nt.get('OXY', 0):.0%} COR={nt.get('COR', 0):.0%}"]
            top = sorted(mf.items(), key=lambda x: -x[1])[:4]
            if top:
                parts.append(", ".join(f"{k}:{v:.1f}" for k, v in top))
            ap_hint = " | ".join(parts)

        cog = bridge.cognitive_state()
        if cog.get("ready"):
            cfs = cog.get("cognitive_feelings", {})
            if cfs:
                cfs_zh = {
                    "surprise": "惊讶",
                    "coherence": "连贯感",
                    "dissonance": "违和感",
                    "correctness": "正确感",
                    "grasp": "把握感",
                    "expectation": "期待",
                    "pressure": "压力",
                }
                cfs_parts = [
                    f"{cfs_zh.get(k, k)}:{v:.1f}" for k, v in sorted(cfs.items(), key=lambda x: -abs(x[1]))[:4]
                ]
                ap_hint += f"\n认知感受: {', '.join(cfs_parts)}"
            focus = cog.get("focus_texts", [])[:3]
            if focus:
                ap_hint += f"\n当前注意: {'; '.join(focus[:3])}"

        mem_ctx = bridge.engine._memory_fusion.get_memory_context_for_llm()
        if mem_ctx:
            ap_hint += f"\n{mem_ctx}"

        recent = bridge.engine._current_soul.recent_context[-4:]
        if recent:
            ap_hint += "\n最近对话:\n" + "\n".join(recent[-4:])

        channels = bridge.channels_state()
        if channels.get("ready"):
            task = channels.get("task", {})
            rhythm = channels.get("rhythm", {})
            chan_parts = []
            if task.get("boredom", 0) > 0.5:
                chan_parts.append(f"有些无聊({task['boredom']:.1f})")
            if task.get("fulfillment", 0) > 0.5:
                chan_parts.append(f"感到充实({task['fulfillment']:.1f})")
            if rhythm.get("phase") and rhythm["phase"] != "idle":
                chan_parts.append(f"对话节奏:{rhythm['phase']}")
            if chan_parts:
                ap_hint += "\n弥娅内在状态: " + ", ".join(chan_parts)

        if ap_hint:
            personality_info["ap_state"] = ap_hint

    except Exception:
        pass

    # 多模态融合上下文
    try:
        from core.miya_multimodal_fusion import get_multimodal_fusion

        fusion = get_multimodal_fusion()
        vis = fusion.get_vision_context()
        aud = fusion.get_audio_context()
        mm_ctx = " ".join(filter(None, [vis, aud]))
        if mm_ctx:
            personality_info["multimodal_context"] = mm_ctx
    except Exception:
        pass

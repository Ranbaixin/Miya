"""
AP + AI 混合情绪融合引擎 (Hybrid Emotion Fusion Engine)

核心设计:
- AP (8通道神经递质): 提供情绪惯性/底色 — 连续、不依赖 LLM、有记忆
- AI (70+情绪标签): 提供情绪增量/细节 — 语境感知、细腻、动态
- 融合引擎: 两套系统取长补短，生成最终情绪状态

融合策略:
1. AP NT 通道 → 情绪基底映射 (OXY→温柔底子, COR→戒备底子, NOV→好奇底子...)
2. AI 情绪分析 → 情绪增量 (丰富标签 + 强度)
3. 加权合并: base_emotion * AP惯性系数 + ai_emotion * 语境系数
4. 闭环回写: AI 分析结果更新 AP 状态池 (形成反馈回路)

使用:
    from core.ap_emotion_fusion import get_fusion_engine

    engine = get_fusion_engine()
    result = await engine.fuse(
        message="用户消息",
        ai_emotions=[{"name": "爱", "intensity": 80}, {"name": "心动", "intensity": 60}],
        ap_nt_snapshot=bridge.emotion_snapshot(),
    )
    # result = {"emotions": {...}, "dominant": "爱", "nt_adjustments": {...}}
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("Miya.EmotionFusion")

# ─── AP NT 通道 → 情绪中文映射 ───
NT_TO_EMOTION_MAP = {
    "OXY": {"name": "温柔", "base_weight": 0.8, "description": "催产素→联结/亲密度"},
    "DA": {"name": "积极", "base_weight": 0.7, "description": "多巴胺→奖励/愉悦度"},
    "SER": {"name": "稳定", "base_weight": 0.6, "description": "血清素→满足/安定感"},
    "COR": {"name": "戒备", "base_weight": 0.7, "description": "皮质醇→警戒/防御度"},
    "NOV": {"name": "好奇", "base_weight": 0.75, "description": "新奇探索→好奇心"},
    "ADR": {"name": "兴奋", "base_weight": 0.5, "description": "肾上腺素→警觉/兴奋"},
    "END": {"name": "舒适", "base_weight": 0.6, "description": "内啡肽→舒适/放松"},
    "FOC": {"name": "专注", "base_weight": 0.5, "description": "焦点锁定→注意力"},
}

# ─── AI 情绪标签 → AP NT 通道反向映射 (用于回写) ───
AI_EMOTION_TO_NT = {
    # ── 联结/爱意 (OXY↑) ──
    "爱": [("OXY", 0.15), ("DA", 0.08)],
    "依恋": [("OXY", 0.18), ("SER", 0.05)],
    "心动": [("DA", 0.10), ("OXY", 0.12)],
    "甜蜜": [("OXY", 0.15), ("DA", 0.10)],
    "温暖": [("OXY", 0.12), ("END", 0.10)],
    "感动": [("OXY", 0.10), ("SER", 0.08)],
    "关怀": [("OXY", 0.14), ("SER", 0.06)],
    "保护欲": [("OXY", 0.12), ("ADR", 0.05)],
    "思念": [("OXY", 0.14), ("NOV", 0.04)],
    "挂念": [("OXY", 0.12), ("COR", 0.04)],
    "怀旧": [("SER", 0.10), ("OXY", 0.06)],
    "信任": [("OXY", 0.14), ("SER", 0.08)],
    "感恩": [("OXY", 0.10), ("SER", 0.06)],
    "共情": [("OXY", 0.10), ("SER", 0.04)],
    "亲近": [("OXY", 0.16), ("END", 0.06)],
    "宠溺": [("OXY", 0.14), ("DA", 0.08), ("END", 0.04)],
    "纵容": [("OXY", 0.10), ("SER", 0.04)],
    "珍视": [("OXY", 0.12), ("SER", 0.06)],
    "守护": [("OXY", 0.10), ("ADR", 0.04), ("FOC", 0.04)],
    "牵挂": [("OXY", 0.10), ("COR", 0.04)],
    "倾慕": [("OXY", 0.12), ("DA", 0.10)],
    "喜欢": [("OXY", 0.12), ("DA", 0.08)],
    # ── 喜悦/积极 (DA↑) ──
    "幸福": [("DA", 0.12), ("SER", 0.10), ("OXY", 0.08)],
    "喜悦": [("DA", 0.14), ("SER", 0.06)],
    "开心": [("DA", 0.14), ("SER", 0.06)],
    "高兴": [("DA", 0.12), ("SER", 0.04)],
    "兴奋": [("ADR", 0.12), ("DA", 0.10)],
    "惊喜": [("NOV", 0.12), ("DA", 0.08), ("ADR", 0.06)],
    "满足": [("SER", 0.15), ("END", 0.08)],
    "充实": [("SER", 0.10), ("DA", 0.06), ("FOC", 0.04)],
    "欣慰": [("SER", 0.08), ("OXY", 0.08)],
    "放心": [("SER", 0.10), ("END", 0.08)],
    # ── 好奇/探索 (NOV↑) ──
    "期待": [("NOV", 0.12), ("DA", 0.08)],
    "好奇": [("NOV", 0.15), ("FOC", 0.06)],
    "调皮": [("DA", 0.10), ("NOV", 0.08)],
    "惊讶": [("NOV", 0.10), ("ADR", 0.08)],
    # ── 安定/放松 (SER↑ END↑) ──
    "平静": [("SER", 0.10), ("END", 0.06)],
    "安然": [("SER", 0.12), ("END", 0.08)],
    "放松": [("SER", 0.08), ("END", 0.12)],
    "自在": [("SER", 0.10), ("END", 0.08)],
    "惬意": [("SER", 0.10), ("END", 0.10)],
    "慵懒": [("SER", 0.06), ("END", 0.08), ("DA", -0.02)],
    "踏實": [("SER", 0.12), ("END", 0.06)],
    # ── 骄傲/自信 (DA↑ FOC↑) ──
    "骄傲": [("DA", 0.10), ("SER", 0.06), ("FOC", 0.04)],
    "自豪": [("DA", 0.12), ("SER", 0.08)],
    "自信": [("DA", 0.08), ("SER", 0.08), ("FOC", 0.06)],
    "坚定": [("FOC", 0.10), ("SER", 0.06)],
    # ── 傲娇/矛盾 (OXY↑ COR↑ 并存) ──
    "傲娇": [("COR", 0.08), ("OXY", 0.06)],
    "吃醋": [("COR", 0.10), ("OXY", 0.08), ("SER", -0.02)],
    "赌气": [("COR", 0.08), ("OXY", 0.06), ("SER", -0.02)],
    "撒娇": [("OXY", 0.12), ("DA", 0.06)],
    # ── 负面/压力 (COR↑) ──
    "无奈": [("COR", 0.06), ("SER", -0.02)],
    "失落": [("COR", 0.08), ("DA", -0.04), ("SER", -0.04)],
    "委屈": [("COR", 0.10), ("OXY", 0.04)],
    "难过": [("COR", 0.12), ("SER", -0.05)],
    "悲伤": [("COR", 0.10), ("SER", -0.06), ("DA", -0.04)],
    "焦虑": [("COR", 0.15), ("ADR", 0.06), ("SER", -0.04)],
    "不安": [("COR", 0.12), ("SER", -0.06)],
    "恐惧": [("COR", 0.14), ("ADR", 0.10), ("SER", -0.08)],
    "害怕": [("COR", 0.12), ("ADR", 0.08), ("SER", -0.04)],
    "紧张": [("ADR", 0.10), ("COR", 0.08), ("SER", -0.04)],
    "烦躁": [("COR", 0.12), ("ADR", 0.04)],
    "愤怒": [("COR", 0.12), ("ADR", 0.10), ("OXY", -0.06)],
    "生气": [("COR", 0.10), ("ADR", 0.06), ("SER", -0.04)],
    "恼火": [("COR", 0.12), ("ADR", 0.06)],
    "疲惫": [("COR", 0.08), ("END", -0.04), ("DA", -0.04)],
    "无聊": [("NOV", -0.06), ("FOC", -0.04)],
    "疏离": [("COR", 0.06), ("OXY", -0.04), ("SER", -0.04)],
    "反感": [("COR", 0.08), ("OXY", -0.06), ("SER", -0.04)],
    "厌恶": [("COR", 0.08), ("OXY", -0.06), ("SER", -0.06)],
    # ── 脆弱/内省 (SER↓) ──
    "心疼": [("OXY", 0.10), ("COR", 0.06), ("END", 0.04)],
    "寂寞": [("SER", -0.08), ("OXY", -0.04), ("NOV", 0.04)],
    "孤独": [("SER", -0.10), ("OXY", -0.06), ("END", -0.04)],
    "迷茫": [("NOV", 0.06), ("FOC", -0.04), ("SER", -0.04)],
    "困惑": [("NOV", 0.06), ("FOC", 0.04), ("SER", -0.02)],
    "羞耻": [("COR", 0.06), ("END", -0.02)],
    "愧疚": [("COR", 0.08), ("SER", -0.04)],
    "后悔": [("COR", 0.08), ("DA", -0.04), ("SER", -0.04)],
    "遗憾": [("COR", 0.06), ("SER", -0.04)],
    "害羞": [("COR", 0.04), ("OXY", 0.06), ("NOV", 0.04)],
    # ── 同情 (OXY↑ COR↑ 复合) ──
    "同情": [("OXY", 0.08), ("COR", 0.04)],
    "怜惜": [("OXY", 0.10), ("COR", 0.04), ("END", 0.04)],
    # ── 反思/认知 (FOC↑) ──
    "感慨": [("FOC", 0.06), ("SER", 0.04)],
    "豁然": [("SER", 0.06), ("FOC", 0.04), ("NOV", 0.04)],
    "释怀": [("SER", 0.08), ("END", 0.06)],
    # ── 浪漫/憧憬 (DA↑ NOV↑) ──
    "浪漫": [("DA", 0.08), ("OXY", 0.08), ("NOV", 0.06)],
    "憧憬": [("NOV", 0.10), ("DA", 0.08), ("OXY", 0.04)],
    "梦幻": [("NOV", 0.08), ("DA", 0.06), ("END", 0.04)],
}


@dataclass
class FusionResult:
    """融合结果"""

    emotions: Dict[str, float]  # 最终情绪词汇 → 强度
    dominant: str  # 主导情绪
    dominant_intensity: float  # 主导情绪强度
    ap_baseline: Dict[str, float]  # AP 贡献的情绪基底
    ai_delta: Dict[str, float]  # AI 贡献的情绪增量
    nt_snapshot: Dict[str, float]  # NT 通道快照
    nt_adjustments: Dict[str, float]  # 需要回写到 AP 的 NT 调整量
    fusion_weight_ap: float  # AP 惯性权重 (0-1)
    fusion_weight_ai: float  # AI 语境权重 (0-1)
    inner_thought: str = ""
    attribution: str = ""
    reflection: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class EmotionHistory:
    """情绪历史记录（用于惯性计算）"""

    last_fusion: Optional[FusionResult] = None
    last_ai_emotions: List[Dict] = field(default_factory=list)
    emotion_trajectory: List[Dict] = field(default_factory=list)  # 最近N次情绪快照
    max_history: int = 10


class APEmotionFusion:
    """
    AP + AI 混合情绪融合引擎

    ┌──────────────┐     ┌──────────────┐
    │  AP 8通道NT  │     │  AI 70+情绪  │
    │  (连续模拟)  │     │  (语境感知)  │
    └──────┬───────┘     └──────┬───────┘
           │                     │
           └────────┬───────────┘
                    ▼
           ┌───────────────┐
           │  融合引擎      │
           │  AP惯性×AI增量 │
           └───────┬───────┘
                   │
         ┌─────────┼─────────┐
         ▼                    ▼
    ┌──────────┐      ┌──────────────┐
    │ 最终情绪  │      │  NT回写 (闭环)│
    │ (响应输入)│      │  AP状态池更新 │
    └──────────┘      └──────────────┘
    """

    def __init__(self):
        self._history: EmotionHistory = EmotionHistory()
        self._last_fusion: Optional[FusionResult] = None

        # 权重配置
        self.ap_inertia_base = 0.55  # AP 惯性基础权重
        self.ai_context_base = 0.45  # AI 语境基础权重
        self.ap_inertia_max = 0.75  # 长对话中 AP 惯性最大权重
        self.ap_inertia_min = 0.35  # 短对话/新话题中 AP 惯性最小权重
        self.conversation_turns_for_max_inertia = 10  # 达到最大惯性所需轮次

    def fuse(
        self,
        message: str,
        ai_emotions: List[Dict],
        ap_nt_snapshot: Dict,
        conversation_turns: int = 1,
        personality_form: str = "default",
    ) -> FusionResult:
        """
        融合 AP 和 AI 的情绪输出

        Args:
            message: 当前用户消息
            ai_emotions: AI 分析的情绪 [{"name": "爱", "intensity": 80}, ...]
            ap_nt_snapshot: AP emotion_snapshot() 返回的数据
                {"nt_channels": {...}, "miya_feelings": {...}, "cognitive": {...}}
            conversation_turns: 当前对话轮次
            personality_form: 当前形态名

        Returns:
            FusionResult: 融合后的情绪结果
        """
        # 1. 解析 AP NT 通道 → 情绪基底
        nt_channels = ap_nt_snapshot.get("nt_channels", {})
        ap_baseline = {}
        nt_values = {}

        for ch_id, meta in NT_TO_EMOTION_MAP.items():
            raw_val = nt_channels.get(ch_id, 0.0)
            nt_values[ch_id] = raw_val
            # NT 值映射到 0-100 强度 (NT 通道值通常在 0-1 之间)
            intensity = min(100, max(0, raw_val * 100 * meta["base_weight"]))
            ap_baseline[meta["name"]] = round(intensity, 1)

        # 2. 解析 AI 情绪 → 情绪增量字典
        ai_delta: Dict[str, float] = {}
        for emo in ai_emotions:
            name = emo.get("name", "")
            intensity = emo.get("intensity", 50)
            if name and intensity > 0:
                ai_delta[name] = float(intensity)

        # 3. 计算融合权重 (基于对话轮次动态调整)
        ap_weight = self._calc_ap_weight(conversation_turns)
        ai_weight = 1.0 - ap_weight

        # 4. 融合: AP 基底 + AI 增量，加权合并
        fused: Dict[str, float] = {}
        all_emotion_names = set(list(ap_baseline.keys()) + list(ai_delta.keys()))

        for name in all_emotion_names:
            ap_val = ap_baseline.get(name, 0)
            ai_val = ai_delta.get(name, 0)

            # AI 情绪中出现的标签以 AI 为主，AP 提供惯性
            if name in ai_delta:
                # AI 识别到的情绪: 以 AI 强度为主，AP 基底提供平滑
                fused[name] = ap_val * ap_weight * 0.4 + ai_val * (ai_weight + 0.2)
            elif name in ap_baseline:
                # AP 独有情绪: 保留 AP 基底但衰减
                fused[name] = ap_val * ap_weight * 0.8
            else:
                fused[name] = 0

            fused[name] = min(100, max(0, round(fused[name], 1)))

        # 移除强度太低的情绪
        fused = {k: v for k, v in fused.items() if v > 10}

        # 5. 计算 AP NT 调整量 (闭环回写)
        nt_adjustments = self._calc_nt_adjustments(ai_emotions, nt_values)

        # 6. 确定主导情绪
        if fused:
            dominant = max(fused, key=fused.get)
            dominant_intensity = fused[dominant]
        else:
            dominant = "平静"
            dominant_intensity = 50

        result = FusionResult(
            emotions=fused,
            dominant=dominant,
            dominant_intensity=dominant_intensity,
            ap_baseline=ap_baseline,
            ai_delta=ai_delta,
            nt_snapshot=nt_values,
            nt_adjustments=nt_adjustments,
            fusion_weight_ap=round(ap_weight, 3),
            fusion_weight_ai=round(ai_weight, 3),
        )

        # 记录历史
        self._last_fusion = result
        self._history.last_fusion = result
        self._history.last_ai_emotions = list(ai_emotions)
        self._history.emotion_trajectory.append(
            {
                "dominant": dominant,
                "intensity": dominant_intensity,
                "top3": dict(sorted(fused.items(), key=lambda x: -x[1])[:3]),
                "timestamp": time.time(),
            }
        )
        if len(self._history.emotion_trajectory) > self._history.max_history:
            self._history.emotion_trajectory = self._history.emotion_trajectory[-self._history.max_history :]

        logger.info(
            f"[融合] 主导={dominant}({dominant_intensity:.0f}%) "
            f"| AP权重={ap_weight:.2f} AI权重={ai_weight:.2f} "
            f"| NT调整={len(nt_adjustments)}通道"
        )

        return result

    def _calc_ap_weight(self, conversation_turns: int) -> float:
        """计算 AP 惯性权重"""
        if conversation_turns <= 1:
            return self.ap_inertia_min
        ratio = min(1.0, conversation_turns / self.conversation_turns_for_max_inertia)
        return self.ap_inertia_min + (self.ap_inertia_max - self.ap_inertia_min) * ratio

    def _calc_nt_adjustments(self, ai_emotions: List[Dict], current_nt: Dict[str, float]) -> Dict[str, float]:
        """
        从 AI 情绪计算 NT 通道调整量 (闭环回写)
        AI 识别到的情绪 → 调整对应的 NT 通道
        """
        adjustments: Dict[str, float] = {ch: 0.0 for ch in NT_TO_EMOTION_MAP}

        for emo in ai_emotions:
            name = emo.get("name", "")
            intensity = emo.get("intensity", 50)
            if name not in AI_EMOTION_TO_NT:
                continue

            normalized = (intensity - 50) / 50.0  # 归一化到 -1 ~ +1

            for ch, base_delta in AI_EMOTION_TO_NT[name]:
                delta = base_delta * normalized * 0.3  # 回写系数 0.3，避免过冲
                adjustments[ch] = round(adjustments.get(ch, 0) + delta, 4)

        # 裁剪
        for ch in adjustments:
            adjustments[ch] = max(-0.1, min(0.1, adjustments[ch]))

        return adjustments

    def get_inertia_factor(self) -> float:
        """获取当前情绪惯性因子"""
        if self._last_fusion:
            return self._last_fusion.fusion_weight_ap
        return self.ap_inertia_base

    @property
    def last_result(self) -> Optional[FusionResult]:
        return self._last_fusion

    @property
    def trajectory(self) -> List[Dict]:
        return list(self._history.emotion_trajectory)


# ─── 全局单例 ───

_fusion_engine: Optional[APEmotionFusion] = None


def get_fusion_engine() -> APEmotionFusion:
    global _fusion_engine
    if _fusion_engine is None:
        _fusion_engine = APEmotionFusion()
    return _fusion_engine


def reset_fusion_engine():
    global _fusion_engine
    _fusion_engine = APEmotionFusion()

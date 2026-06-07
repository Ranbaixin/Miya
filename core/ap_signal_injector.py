"""
AP 信号注入器 — 将 AI 融合情绪转化为 AP 规则引擎的触发信号

AP 有 52 条先天规则，等待这些信号触发:
  - social_reward: 主人发了亲昵/撒娇/夸奖的内容
  - satisfaction: 对话顺利进行、情绪积极
  - novelty: 新信息、新话题
  - alignment: 弥娅的回应与主人期待一致
  - coherence: 认知和谐（理解到位）
  - negative_pressure: 主人不开心/批评/冷落
  - social_punishment: 主人明显生气/拒绝
  - fatigue: 长时间沉默/无聊

之前这些信号几乎从未被注入，导致 AP 规则悬空。
现在 AI 融合引擎产出的情绪直接映射为 AP 能理解的信号。
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Dict, List, Optional

if TYPE_CHECKING:
    from core.ap_emotion_fusion import FusionResult

logger = logging.getLogger("Miya.APSignalInjector")

# ─── AI 情绪 → AP 条件信号映射 ───
# 每条规则: {触发情绪关键词: (AP条件名, 信号强度映射函数)}
EMOTION_TO_AP_SIGNAL: Dict[str, List[tuple]] = {
    # === social_reward 触发 (激活: MIYA-LOVE, MIYA-DOTE, MIYA-GENTLE, MIYA-BOND) ===
    "爱": [("social_reward", lambda v: v * 1.2), ("coherence", lambda v: v * 0.6)],
    "依恋": [("social_reward", lambda v: v * 1.0), ("alignment", lambda v: v * 0.7)],
    "心动": [("social_reward", lambda v: v * 1.1), ("novelty", lambda v: v * 0.4)],
    "甜蜜": [("social_reward", lambda v: v * 1.3), ("satisfaction", lambda v: v * 0.8)],
    "幸福": [("satisfaction", lambda v: v * 1.2), ("social_reward", lambda v: v * 0.9)],
    "满足": [("satisfaction", lambda v: v * 1.0), ("coherence", lambda v: v * 0.5)],
    "温暖": [("social_reward", lambda v: v * 0.8), ("coherence", lambda v: v * 0.6)],
    "感动": [("social_reward", lambda v: v * 1.1), ("coherence", lambda v: v * 0.7)],
    "关怀": [("coherence", lambda v: v * 0.8), ("alignment", lambda v: v * 0.5)],
    "保护欲": [("alignment", lambda v: v * 0.9), ("social_reward", lambda v: v * 0.5)],
    "宠溺": [("social_reward", lambda v: v * 1.4)],  # 高触发 MIYA-DOTE
    "玩味": [("social_reward", lambda v: v * 0.9), ("novelty", lambda v: v * 0.5)],
    # === novelty 触发 (激活: MIYA-CURIOUS) ===
    "好奇": [("novelty", lambda v: v * 1.5), ("satisfaction", lambda v: v * 0.3)],
    "期待": [("novelty", lambda v: v * 1.0), ("coherence", lambda v: v * 0.4)],
    "惊喜": [("novelty", lambda v: v * 1.3), ("social_reward", lambda v: v * 0.5)],
    "兴奋": [("novelty", lambda v: v * 1.0), ("social_reward", lambda v: v * 0.4)],
    # === negative_pressure 触发 (激活: MIYA-CARE, MIYA-FEAR, MIYA-FRAGILE) ===
    "心疼": [("negative_pressure", lambda v: v * 0.9), ("coherence", lambda v: v * 0.3)],
    "担忧": [("negative_pressure", lambda v: v * 1.0), ("social_reward", lambda v: v * -0.3)],
    "不安": [("negative_pressure", lambda v: v * 1.2), ("social_punishment", lambda v: v * 0.3)],
    "失落": [("negative_pressure", lambda v: v * 0.8), ("fatigue", lambda v: v * 0.5)],
    "难过": [("negative_pressure", lambda v: v * 1.1), ("social_punishment", lambda v: v * 0.5)],
    "委屈": [("negative_pressure", lambda v: v * 0.9), ("social_punishment", lambda v: v * 0.4)],
    "愧疚": [("negative_pressure", lambda v: v * 0.7), ("alignment", lambda v: v * -0.3)],
    "疲惫": [("fatigue", lambda v: v * 1.2), ("negative_pressure", lambda v: v * 0.4)],
    "烦躁": [("negative_pressure", lambda v: v * 1.1), ("social_punishment", lambda v: v * 0.7)],
    "无聊": [("fatigue", lambda v: v * 1.5)],
    "孤单": [("negative_pressure", lambda v: v * 0.8), ("fatigue", lambda v: v * 0.5)],
    "焦虑": [("negative_pressure", lambda v: v * 1.0), ("social_punishment", lambda v: v * 0.3)],
    "疏离": [("negative_pressure", lambda v: v * 0.8), ("social_punishment", lambda v: v * 0.7)],
    # === coherence / alignment 触发 ===
    "温柔": [("coherence", lambda v: v * 0.9), ("alignment", lambda v: v * 0.6)],
    "积极": [("alignment", lambda v: v * 0.8), ("satisfaction", lambda v: v * 0.6)],
    "稳定": [("coherence", lambda v: v * 1.0), ("satisfaction", lambda v: v * 0.4)],
    "专注": [("coherence", lambda v: v * 1.1)],
    "平静": [("coherence", lambda v: v * 0.7)],
    "信任": [("alignment", lambda v: v * 1.2), ("coherence", lambda v: v * 0.6)],
    "共情": [("alignment", lambda v: v * 1.0), ("coherence", lambda v: v * 0.5)],
}

# 信号归一化范围 (0-1)
SIGNAL_CLAMP = (0.0, 1.0)

# 多情绪对同一信号叠加时的上限（防止单个信号被多个情绪推到 1.0 以上）
SIGNAL_MAX_ACCUMULATED = 1.0


class APSignalInjector:
    """
    AP 信号注入器

    将 AI 融合引擎产生的中文情绪标签转化为 AP 先天规则引擎能理解的信号。

    用法:
        injector = APSignalInjector()
        signals = injector.translate_fusion_to_signals(fusion_result)
        bridge.inject_signals(signals)
    """

    def __init__(self):
        self._last_signals: Dict[str, float] = {}
        self._signal_history: List[Dict[str, float]] = []
        self._max_history = 20

    def translate_fusion_to_signals(self, fusion_result: "FusionResult") -> Dict[str, float]:
        """
        将融合结果转化为 AP 条件信号

        Args:
            fusion_result: 融合引擎的输出

        Returns:
            {signal_name: strength (0.0-1.0)}
            e.g. {"social_reward": 0.72, "satisfaction": 0.45, "novelty": 0.30}
        """
        raw_signals: Dict[str, float] = {}

        for name, intensity in fusion_result.emotions.items():
            normalized = intensity / 100.0  # 0-100 → 0.0-1.0
            if normalized < 0.1:
                continue

            if name in EMOTION_TO_AP_SIGNAL:
                for signal_name, strength_fn in EMOTION_TO_AP_SIGNAL[name]:
                    signal_val = strength_fn(normalized)
                    signal_val = max(SIGNAL_CLAMP[0], min(SIGNAL_CLAMP[1], signal_val))
                    raw_signals[signal_name] = min(
                        SIGNAL_MAX_ACCUMULATED,
                        raw_signals.get(signal_name, 0) + signal_val,
                    )

        # 别名映射：确保所有 AP 规则能识别的信号都存在
        self._ensure_aliases(raw_signals)

        # 历史平滑：与上一轮的信号做 EMA，防止突变
        smoothed = self._smooth_signals(raw_signals)

        # 记录
        self._last_signals = dict(smoothed)
        self._signal_history.append(dict(smoothed))
        if len(self._signal_history) > self._max_history:
            self._signal_history = self._signal_history[-self._max_history :]

        return smoothed

    def _ensure_aliases(self, signals: Dict[str, float]) -> None:
        """补充别名，确保所有信号覆盖"""
        # social_reward 和 satisfaction 互哺
        if "social_reward" in signals and "satisfaction" not in signals:
            signals["satisfaction"] = signals["social_reward"] * 0.7
        if "satisfaction" in signals and "social_reward" not in signals:
            signals["social_reward"] = signals["satisfaction"] * 0.6

        # novelty 和 curiosity 关系
        if "novelty" in signals and signals["novelty"] > 0.3:
            if "curiosity" not in signals:
                signals["curiosity"] = signals["novelty"] * 0.8

    def _smooth_signals(self, raw: Dict[str, float]) -> Dict[str, float]:
        """EMA 平滑，避免信号突变"""
        if not self._last_signals:
            return raw

        alpha = 0.35  # 平滑系数（越高越跟随新信号）
        smoothed = {}
        all_keys = set(list(raw.keys()) + list(self._last_signals.keys()))

        for key in all_keys:
            prev = self._last_signals.get(key, 0)
            curr = raw.get(key, 0)
            smoothed[key] = round(prev * (1 - alpha) + curr * alpha, 4)

        return smoothed

    @property
    def last_signals(self) -> Dict[str, float]:
        return dict(self._last_signals)

    @property
    def signal_history(self) -> List[Dict[str, float]]:
        return list(self._signal_history)


# ─── 全局单例 ───

_signal_injector: Optional[APSignalInjector] = None


def get_signal_injector() -> APSignalInjector:
    global _signal_injector
    if _signal_injector is None:
        _signal_injector = APSignalInjector()
    return _signal_injector

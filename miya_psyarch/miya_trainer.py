"""
弥娅 AP 训练引擎 — 让认知越来越像和佳相处的弥娅

三种模式:
  distill — 规则蒸馏: 从对话记忆中提取互动模式 → 微调规则权重
  reinforce — 强化学习: 奖励信号 → 强化认知路径
  pretrain — 离线预训练: 历史记忆 → 认知基线注入
"""

from __future__ import annotations

import json
import logging
import math
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger("miya_psyarch.trainer")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MEMORY_PATH = _PROJECT_ROOT / ".memory" / "memory.json"
_COGNITION_CACHE = _PROJECT_ROOT / "data" / "cognition_cache.db"
_TRAINING_OUTPUT = _PROJECT_ROOT / "data" / "ap_training.json"
_CONVERSATIONS_DIR = _PROJECT_ROOT / "data" / "conversations"

# — 训练调控表结构 —
# 存于 data/ap_training.json，启动时由引擎读取并应用


class MiyaTrainer:
    """弥娅训练引擎"""

    def __init__(self):
        self._state = self._load_training_state()
        self._memories: list[dict] = []
        self._cognition_entries: list[dict] = []

    # ──────────────── ① 规则蒸馏 ────────────────

    def distill_rules(self) -> dict:
        """
        规则蒸馏训练:
        1. 加载所有可用记忆 → 提取情绪分布、话题偏好、互动模式
        2. 根据模式调整 52 条先天规则的敏感度/阈值
        3. 存储到 ap_training.json
        """
        self._load_memories()
        if not self._memories:
            return {"distilled": False, "reason": "no_memories"}

        patterns = self._extract_interaction_patterns()
        if not patterns:
            return {"distilled": False, "reason": "no_patterns"}

        modulation = self._compute_rule_modulation(patterns)
        self._state["distill"] = modulation
        self._state["distill_ts"] = str(Path(_TRAINING_OUTPUT).stat().st_mtime) if _TRAINING_OUTPUT.exists() else "new"
        self._save()

        logger.info(f"[训练·蒸馏] 分析 {len(self._memories)} 条记忆 → {len(modulation)} 条规则调整")
        return {
            "distilled": True,
            "rules_adjusted": len(modulation),
            "patterns": patterns.__dict__ if hasattr(patterns, "__dict__") else str(patterns),
        }

    def _load_memories(self) -> None:
        """加载弥娅记忆 + 认知缓存"""
        self._memories = []
        # 源1: .memory/memory.json
        if _MEMORY_PATH.exists():
            try:
                raw = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
                self._memories.extend(raw if isinstance(raw, list) else raw.get("entries", []))
            except Exception:
                pass

        # 源2: 教育历史 (由 MiyaPsyArchBridge 累积)
        try:
            from core.miya_psyarch_bridge import get_psyarch_bridge

            bridge = get_psyarch_bridge()
            edu_history = getattr(bridge, "_edu_history", [])
            for entry in edu_history:
                self._memories.append(
                    {"type": "education", "quality": entry.get("quality", 0), "count": entry.get("count", 0)}
                )
        except Exception:
            pass

    def _extract_interaction_patterns(self) -> dict:
        """从记忆中提取互动模式"""
        patterns = InteractionPatterns()

        # 统计情绪词频
        emotion_counter: Counter = Counter()
        topic_counter: Counter = Counter()
        quality_scores: list[float] = []
        for mem in self._memories:
            if isinstance(mem, dict):
                text = str(mem.get("content", "") or mem.get("fact", "") or "")
                tags = mem.get("tags", [])
                quality = mem.get("quality", 0)

                if quality > 0:
                    quality_scores.append(quality)

                for tag in tags:
                    topic_counter[tag] += 1

                for word in ["爱", "喜欢", "想", "陪", "累", "睡", "好", "开心", "温柔", "担心", "黑", "怕"]:
                    if word in text:
                        emotion_counter[word] += 1

        total = sum(emotion_counter.values()) or 1
        patterns.dominant_emotions = {k: round(v / total, 3) for k, v in emotion_counter.most_common(10)}
        patterns.top_topics = dict(topic_counter.most_common(5))
        patterns.avg_quality = round(sum(quality_scores) / len(quality_scores), 3) if quality_scores else 0.5
        patterns.interaction_count = len(self._memories)

        # 推理对话节奏偏好
        if emotion_counter.get("黑", 0) > 5 or emotion_counter.get("怕", 0) > 5:
            patterns.comfort_mode = True
        if emotion_counter.get("爱", 0) > emotion_counter.get("累", 0) * 2:
            patterns.affection_heavy = True
        if emotion_counter.get("想", 0) > 10:
            patterns.longing_trait = True

        return patterns

    def _compute_rule_modulation(self, patterns) -> dict:
        """根据互动模式计算规则调制参数"""
        mod: dict[str, dict] = {}

        # 宠溺类规则增强 (若爱意>疲惫)
        if patterns.affection_heavy:
            mod["doting"] = {"threshold_adj": -0.05, "gain_mult": 1.15}
            mod["love_warmth"] = {"threshold_adj": -0.08, "gain_mult": 1.20}
            mod["gentle_warmth"] = {"threshold_adj": -0.05, "gain_mult": 1.10}
            mod["deep_bond"] = {"threshold_adj": -0.06, "gain_mult": 1.15}

        # 安慰模式增强
        if patterns.comfort_mode:
            mod["accompanying"] = {"threshold_adj": -0.10, "gain_mult": 1.25}
            mod["concern"] = {"threshold_adj": -0.08, "gain_mult": 1.20}
            mod["heart_ache"] = {"threshold_adj": 0.05, "gain_mult": 0.90}

        # 思念倾向
        if patterns.longing_trait:
            mod["longing"] = {"threshold_adj": -0.10, "gain_mult": 1.30}
            mod["anticipation"] = {"threshold_adj": -0.06, "gain_mult": 1.12}

        # 质量驱动全局调参
        quality = patterns.avg_quality
        if quality > 0.6:
            mod["global"] = {"learning_rate_mult": 1.15, "exploration_bonus": 0.05}
        elif quality < 0.4:
            mod["global"] = {"learning_rate_mult": 0.85, "exploration_bonus": 0.10}

        # 互动频率 → Cooldown 调整
        if patterns.interaction_count > 500:
            mod["proactive"] = {"cooldown_adj": -5, "min_streak_adj": -3}
        elif patterns.interaction_count > 200:
            mod["proactive"] = {"cooldown_adj": -2, "min_streak_adj": -1}

        return mod

    # ──────────────── ② 强化学习 ────────────────

    def reinforce(self, reward_type: str, reward_value: float, context: str = "") -> dict:
        """
        强化学习优化:
        佳点赞/喜欢/长回复 → 奖励信号
        → 强化触发该奖励的认知路径

        reward_type: "like" | "long_reply" | "positive_emoji" | "call_name"
        """
        rl = self._state.setdefault("reinforce", {"reward_history": [], "strengthened_paths": []})

        rl["reward_history"].append(
            {
                "type": reward_type,
                "value": reward_value,
                "context": context[:60] if context else "",
            }
        )
        if len(rl["reward_history"]) > 200:
            rl["reward_history"] = rl["reward_history"][-100:]

        signal = self._reward_to_signal(reward_type, reward_value)
        if signal:
            self._apply_reinforcement_signal(signal)

        self._save()
        return {"reinforced": True, "reward_type": reward_type, "signal": signal}

    def _reward_to_signal(self, reward_type: str, value: float) -> dict | None:
        """奖励类型 → 认知路径强化信号"""
        if value < 0.3:
            return None

        signals = {
            "like": {"path": "affection", "oxy_boost": 0.05, "da_boost": 0.03},
            "long_reply": {"path": "engagement", "foc_boost": 0.06, "nov_boost": 0.04},
            "positive_emoji": {"path": "playful", "da_boost": 0.04, "nov_boost": 0.05},
            "call_name": {"path": "intimacy", "oxy_boost": 0.08, "end_boost": 0.04},
        }
        return signals.get(reward_type)

    def _apply_reinforcement_signal(self, signal: dict) -> None:
        """应用强化信号到训练状态"""
        path = signal["path"]
        paths = self._state.setdefault("strengthened_paths", {})
        paths[path] = round(paths.get(path, 1.0) + 0.02, 3)
        paths[f"{path}_count"] = paths.get(f"{path}_count", 0) + 1

    # ──────────────── ③ 离线预训练 ────────────────

    def pretrain(self) -> dict:
        """
        离线预训练:
        将历史记忆提取为认知基线 → 启动时自动注入 AP 状态池
        效果: 弥娅一醒来就有"和佳相处很久"的感觉
        """
        self._load_memories()
        if not self._memories:
            return {"pretrained": False, "reason": "no_memories"}

        baseline = self._build_cognitive_baseline()
        self._state["pretrain"] = baseline
        self._state["pretrain_count"] = len(self._memories)
        self._save()

        logger.info(
            f"[训练·预训练] 从 {len(self._memories)} 条记忆构建认知基线: {len(baseline.get('anchors', []))} 条锚点"
        )
        return {"pretrained": True, "memories_used": len(self._memories), "anchors": len(baseline.get("anchors", []))}

    def _build_cognitive_baseline(self) -> dict:
        """构建认知基线 — 提取最高频、最新的记忆锚点"""
        anchors = []
        emotions = Counter()
        topics = Counter()

        for mem in self._memories[-200:]:  # 取最近 200 条
            text = str(mem.get("content", "") or mem.get("fact", "") or "")
            if len(text) < 5:
                continue
            tags = mem.get("tags", []) if isinstance(mem, dict) else []
            for tag in tags:
                topics[tag] += 1

            anchors.append(
                {
                    "text": text[:80],
                    "energy": round(0.3 + len(text) / 200, 3),
                    "family": "pretrain_anchor",
                    "tags": tags[:3],
                }
            )

        # 情绪基调
        for word, count in Counter(
            w for m in self._memories for w in str(m.get("content", "") or "").split() if len(w) < 4
        ).most_common(20):
            emotions[word] = count

        rl_paths = self._state.get("strengthened_paths", {})
        return {
            "anchors": anchors[:50],
            "emotion_baseline": dict(emotions.most_common(10)),
            "topic_baseline": dict(topics.most_common(5)),
            "strengthened_paths": {k: v for k, v in rl_paths.items() if not k.endswith("_count")},
        }

    def get_baseline_anchors(self) -> list[dict]:
        """返回离线预训练的认知锚点 → 供引擎注入状态池"""
        pretrain = self._state.get("pretrain", {})
        return pretrain.get("anchors", [])

    def get_rule_modulation(self) -> dict:
        """返回蒸馏训练的规则调制 → 供引擎应用"""
        return self._state.get("distill", {})

    def get_training_summary(self) -> dict:
        """训练总览"""
        distill = self._state.get("distill", {})
        rl = self._state.get("reinforce", {})
        pretrain = self._state.get("pretrain", {})
        return {
            "distilled_rules": len(distill),
            "rl_events": len(rl.get("reward_history", [])),
            "reinforced_paths": {
                k: v for k, v in self._state.get("strengthened_paths", {}).items() if not k.endswith("_count")
            },
            "pretrain_anchors": len(pretrain.get("anchors", [])),
            "total_memories_analyzed": pretrain.get("pretrain_count", 0),
        }

    # ── 训练全部 ──

    def train_all(self) -> dict:
        """一键完成全部训练"""
        result = {}
        d = self.distill_rules()
        result["distill"] = d
        r = self.pretrain()
        result["pretrain"] = r
        return result

    # ── 持久化 ──

    def _load_training_state(self) -> dict:
        if _TRAINING_OUTPUT.exists():
            try:
                return json.loads(_TRAINING_OUTPUT.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    def _save(self) -> None:
        _TRAINING_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        _TRAINING_OUTPUT.write_text(json.dumps(self._state, ensure_ascii=False, indent=2), encoding="utf-8")


class InteractionPatterns:
    __slots__ = (
        "dominant_emotions",
        "top_topics",
        "avg_quality",
        "interaction_count",
        "comfort_mode",
        "affection_heavy",
        "longing_trait",
    )

    def __init__(self):
        self.dominant_emotions: dict = {}
        self.top_topics: dict = {}
        self.avg_quality: float = 0.5
        self.interaction_count: int = 0
        self.comfort_mode: bool = False
        self.affection_heavy: bool = False
        self.longing_trait: bool = False


# ── 全局单例 ──

_trainer: MiyaTrainer | None = None


def get_trainer() -> MiyaTrainer:
    global _trainer
    if _trainer is None:
        _trainer = MiyaTrainer()
    return _trainer

"""
弥娅 AP 训练引擎 — 让认知越来越像和佳相处的弥娅
三种模式: distill / reinforce / pretrain
"""

from __future__ import annotations

import json
import logging
from collections import Counter
from pathlib import Path
from typing import Any

logger = logging.getLogger("miya_psyarch.trainer")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_MEMORY_PATH = _PROJECT_ROOT / ".memory" / "memory.json"
_TRAINING_OUTPUT = _PROJECT_ROOT / "data" / "ap_training.json"


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


class MiyaTrainer:
    def __init__(self):
        self._memories: list[dict] = []
        self._state = self._load_training_state()

    # ── ① 规则蒸馏 ──

    def distill_rules(self) -> dict:
        self._load_memories()
        if not self._memories:
            return {"distilled": False, "reason": "no_memories"}
        patterns = self._extract_patterns()
        modulation = self._compute_modulation(patterns)
        self._state["distill"] = modulation
        self._save()
        logger.info(f"[训练·蒸馏] 分析 {len(self._memories)} 条记忆 → {len(modulation)} 条规则调整")
        return {"distilled": True, "rules_adjusted": len(modulation), "memories_analyzed": len(self._memories)}

    # ── ② 强化学习 ──

    def reinforce(self, reward_type: str, reward_value: float, context: str = "") -> dict:
        rl = self._state.setdefault("reinforce", {"reward_history": [], "strengthened_paths": {}})
        rl["reward_history"].append({"type": reward_type, "value": reward_value, "context": context[:60]})
        if len(rl["reward_history"]) > 200:
            rl["reward_history"] = rl["reward_history"][-100:]
        signal = {
            "like": {"path": "affection", "oxy_boost": 0.05, "da_boost": 0.03},
            "long_reply": {"path": "engagement", "foc_boost": 0.06},
            "positive_emoji": {"path": "playful", "da_boost": 0.04},
            "call_name": {"path": "intimacy", "oxy_boost": 0.08},
        }.get(reward_type)
        if signal and reward_value > 0.3:
            paths = self._state.setdefault("strengthened_paths", {})
            paths[signal["path"]] = round(paths.get(signal["path"], 1.0) + 0.02, 3)
            paths[f"{signal['path']}_count"] = paths.get(f"{signal['path']}_count", 0) + 1
        self._save()
        return {"reinforced": True, "reward_type": reward_type}

    # ── ③ 离线预训练 ──

    def pretrain(self) -> dict:
        self._load_memories()
        if not self._memories:
            return {"pretrained": False, "reason": "no_memories"}
        baseline = self._build_baseline()
        self._state["pretrain"] = baseline
        self._state["pretrain_count"] = len(self._memories)
        self._save()
        logger.info(f"[训练·预训练] {len(self._memories)} 条记忆 → {len(baseline.get('anchors', []))} 条锚点")
        return {"pretrained": True, "memories_used": len(self._memories), "anchors": len(baseline.get("anchors", []))}

    def train_all(self) -> dict:
        d = self.distill_rules()
        r = self.pretrain()
        return {"distill": d, "pretrain": r}

    # ── 数据加载 ──

    def _load_memories(self) -> None:
        self._memories = []
        # 源1: memory.json
        if _MEMORY_PATH.exists():
            try:
                raw = json.loads(_MEMORY_PATH.read_text(encoding="utf-8"))
                entries = raw if isinstance(raw, list) else raw.get("memories", [])
                if isinstance(entries, str):
                    try:
                        entries = json.loads(entries.replace("'", '"'))
                    except Exception:
                        import ast

                        try:
                            entries = ast.literal_eval(entries)
                        except Exception:
                            entries = []
                for m in entries if isinstance(entries, list) else []:
                    if isinstance(m, dict):
                        text = str(
                            m.get("content", "") or m.get("fact", "") or m.get("text", "") or m.get("key", "") or ""
                        )
                        self._memories.append(
                            {
                                "content": text,
                                "tags": m.get("tags", []) if isinstance(m.get("tags"), list) else [],
                                "type": m.get("type", "memory"),
                            }
                        )
            except Exception:
                pass

        # 源2: AP 引擎运行时数据
        try:
            from core.miya_psyarch_bridge import get_psyarch_bridge

            bridge = get_psyarch_bridge()
            if bridge and bridge._initialized:
                engine = bridge._engine
                fusion = getattr(engine, "_memory_fusion", None)
                if fusion:
                    for e in getattr(fusion, "_cognitive_entries", []):
                        t = e.get("inner_thought", "") or e.get("thought", "")
                        if t and len(t) > 3:
                            self._memories.append(
                                {"content": t, "tags": ["cognitive"], "type": "inner_thought", "quality": 0.6}
                            )
                    for a in getattr(fusion, "_identity_anchors", []):
                        t = str(a.get("fact", "") or a.get("content", "") or "")
                        if t:
                            self._memories.append(
                                {"content": t, "tags": ["identity"], "type": "identity", "quality": 0.8}
                            )
                    for a in getattr(fusion, "_user_anchors", []):
                        t = str(a.get("fact", "") or a.get("content", "") or "")
                        if t:
                            self._memories.append(
                                {"content": t, "tags": ["user", "佳"], "type": "user", "quality": 1.0}
                            )
                if engine._runtime:
                    for v in list(getattr(engine._runtime.state_pool, "_entries", {}).values())[:100]:
                        if getattr(v, "family", "") == "memory_anchor" and getattr(v, "real_energy", 0) > 0.3:
                            d = getattr(v, "display_text", "") or ""
                            if d and len(d) > 5:
                                self._memories.append(
                                    {
                                        "content": d,
                                        "tags": ["memory"],
                                        "type": "state_pool",
                                        "quality": getattr(v, "real_energy", 0.5),
                                    }
                                )
        except Exception:
            pass

    # ── 模式分析 ──

    def _extract_patterns(self) -> InteractionPatterns:
        p = InteractionPatterns()
        ec: Counter = Counter()
        tc: Counter = Counter()
        qs: list[float] = []
        for m in self._memories:
            if isinstance(m, dict):
                text = str(m.get("content", "") or m.get("fact", "") or "")
                for t in m.get("tags", []):
                    tc[t] += 1
                q = m.get("quality", 0)
                if q > 0:
                    qs.append(q)
                for w in _load_training_keywords():
                    if w in text:
                        ec[w] += 1
        total = sum(ec.values()) or 1
        p.dominant_emotions = {k: round(v / total, 3) for k, v in ec.most_common(10)}
        p.top_topics = dict(tc.most_common(5))
        p.avg_quality = round(sum(qs) / len(qs), 3) if qs else 0.5
        p.interaction_count = len(self._memories)
        if ec.get("陪", 0) > 10 or ec.get("护", 0) > 5:
            p.comfort_mode = True
        if ec.get("爱", 0) + ec.get("想", 0) > ec.get("累", 0) * 3:
            p.affection_heavy = True
        if ec.get("想", 0) > 10:
            p.longing_trait = True
        return p

    def _compute_modulation(self, p: InteractionPatterns) -> dict:
        mod = {}
        if p.affection_heavy:
            mod["doting"] = {"threshold_adj": -0.05, "gain_mult": 1.15}
            mod["love_warmth"] = {"threshold_adj": -0.08, "gain_mult": 1.20}
            mod["deep_bond"] = {"threshold_adj": -0.06, "gain_mult": 1.15}
        if p.comfort_mode:
            mod["accompanying"] = {"threshold_adj": -0.10, "gain_mult": 1.25}
            mod["concern"] = {"threshold_adj": -0.08, "gain_mult": 1.20}
        if p.longing_trait:
            mod["longing"] = {"threshold_adj": -0.10, "gain_mult": 1.30}
        if p.avg_quality > 0.6:
            mod["global"] = {"learning_rate_mult": 1.15}
        if p.interaction_count > 200:
            mod["proactive"] = {"cooldown_adj": -5}
        return mod

    def _build_baseline(self) -> dict:
        anchors = []
        for m in self._memories:
            text = str(m.get("content", "") or "")
            if len(text) > 5:
                anchors.append(
                    {
                        "text": text[:80],
                        "energy": 0.3,
                        "family": "pretrain",
                        "tags": m.get("tags", []) if isinstance(m.get("tags"), list) else [],
                    }
                )
        return {"anchors": anchors[:50]}

    # ── 查询 API ──

    def get_baseline_anchors(self) -> list:
        return self._state.get("pretrain", {}).get("anchors", [])

    def get_rule_modulation(self) -> dict:
        return self._state.get("distill", {})

    def get_training_summary(self) -> dict:
        return {
            "distilled_rules": len(self._state.get("distill", {})),
            "rl_events": len(self._state.get("reinforce", {}).get("reward_history", [])),
            "reinforced_paths": {
                k: v for k, v in self._state.get("strengthened_paths", {}).items() if not k.endswith("_count")
            },
            "pretrain_anchors": len(self._state.get("pretrain", {}).get("anchors", [])),
            "total_memories_analyzed": self._state.get("pretrain_count", 0),
        }

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


_trainer: MiyaTrainer | None = None


def get_trainer() -> MiyaTrainer:
    global _trainer
    if _trainer is None:
        _trainer = MiyaTrainer()
    return _trainer


def _load_training_keywords() -> list[str]:
    """从 miya_config.yaml 加载训练用情绪关键词"""
    try:
        import yaml

        cfg_path = _PROJECT_ROOT / "config" / "miya_config.yaml"
        if cfg_path.exists():
            cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
            kw_cfg = cfg.get("training_emotion_keywords", {})
            keywords = []
            for level, words in kw_cfg.items():
                keywords.extend(words)
            return keywords
    except Exception:
        pass
    return []

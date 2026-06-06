from __future__ import annotations

from heapq import nsmallest

"""
PHASE1_MINIMAL_UPGRADED:
Attention now includes a simple but explicit continuation bias so the slow
system does not depend only on the newest exogenous labels. It is still not the
final APV2.1 arbitration model, but it is stronger than the original one-shot
linear selector.
"""


class AttentionSelector:
    def __init__(
        self,
        *,
        focus_limit: int,
        pressure_gain: float,
        attention_gain_weight: float,
        fatigue_weight: float,
        continuation_bias: float = 0.35,
    ) -> None:
        self.focus_limit = max(1, int(focus_limit))
        self.pressure_gain = float(pressure_gain)
        self.attention_gain_weight = float(attention_gain_weight)
        self.fatigue_weight = float(fatigue_weight)
        self.continuation_bias = float(continuation_bias)

    def select(
        self,
        attention_rows: list[dict],
        *,
        previous_focus_labels: list[str] | None = None,
        emotion_modulation: dict | None = None,
        successor_bias: dict | None = None,
        innate_attention_biases: list[dict] | None = None,
        action_attention_controls: list[dict] | None = None,
    ) -> dict:
        previous_set = {str(label or "") for label in (previous_focus_labels or []) if str(label or "")}
        successor_bias_by_label = dict((successor_bias or {}).get("bias_by_label", {}) or {})
        innate_bias_by_label = self._build_innate_bias_by_label(innate_attention_biases or [])
        action_bias_by_label = self._build_action_bias_by_label(action_attention_controls or [])
        # Extract emotion modulation from 8-channel NT system
        # emotion_modulation format: {"attention": {...}, "hdb": {...}, "action": {...}}
        attention_mod = (emotion_modulation or {}).get("attention", {})
        resource_multiplier = float(attention_mod.get("resource_multiplier", 1.0))
        threshold_adjustment = float(attention_mod.get("threshold_adjustment", 0.0))

        ranked = []
        for row in attention_rows:
            label = str(row.get("sa_label", "") or "")
            continuation_bonus = self.continuation_bias if label in previous_set else 0.0
            successor_bonus = max(0.0, float(successor_bias_by_label.get(label, 0.0) or 0.0))
            innate_bonus = float(innate_bias_by_label.get(label, 0.0) or 0.0)
            action_bias = dict(action_bias_by_label.get(label, {}) or {})
            action_boost = float(action_bias.get("boost", 0.0) or 0.0)
            action_suppression = float(action_bias.get("suppression", 0.0) or 0.0)
            action_net_bias = action_boost - action_suppression
            base_score = (
                float(row.get("cognitive_pressure", 0.0) or 0.0) * self.pressure_gain
                + float(row.get("attention_gain", 0.0) or 0.0) * self.attention_gain_weight
                + float(row.get("virtual_energy", 0.0) or 0.0) * 0.25
                - float(row.get("fatigue", 0.0) or 0.0) * self.fatigue_weight
                + continuation_bonus
                + successor_bonus
                + innate_bonus
                + action_net_bias
            )
            # Apply emotion modulation to attention resource
            score = base_score * resource_multiplier
            enriched = dict(row)
            enriched["continuation_bonus"] = round(continuation_bonus, 4)
            enriched["successor_bias"] = round(successor_bonus, 4)
            enriched["innate_attention_bias"] = round(innate_bonus, 4)
            enriched["action_attention_boost"] = round(action_boost, 4)
            enriched["action_attention_suppression"] = round(action_suppression, 4)
            enriched["action_attention_net_bias"] = round(action_net_bias, 4)
            if action_bias.get("sources"):
                enriched["action_attention_sources"] = list(action_bias.get("sources", []) or [])[:4]
            enriched["base_focus_score"] = round(base_score, 4)
            enriched["emotion_multiplier"] = round(resource_multiplier, 4)
            enriched["focus_score"] = round(score, 4)
            ranked.append(enriched)
        rank_key = lambda item: (-float(item["focus_score"]), str(item["sa_label"]))
        ranked_limit = max(self.focus_limit * 8, self.focus_limit + 8)
        if len(ranked) > ranked_limit:
            ranked_items = nsmallest(ranked_limit, ranked, key=rank_key)
        else:
            ranked.sort(key=rank_key)
            ranked_items = ranked
        selected = ranked_items[: self.focus_limit]
        return {
            "selected_labels": [item["sa_label"] for item in selected],
            "selected_items": selected,
            "ranked_items": ranked_items,
            "innate_attention_biases": list(innate_attention_biases or [])[:8],
            "action_attention_controls": list(action_attention_controls or [])[:8],
        }

    def _build_innate_bias_by_label(self, biases: list[dict]) -> dict[str, float]:
        by_label: dict[str, float] = {}
        for bias in biases or []:
            if not isinstance(bias, dict):
                continue
            strength = max(0.0, float(bias.get("strength", 0.0) or 0.0))
            if strength <= 0.0:
                continue
            target_labels = [str(label or "") for label in list(bias.get("target_labels", []) or []) if str(label or "")]
            if not target_labels:
                anchor_key = str(bias.get("anchor_key", "") or "")
                if anchor_key and anchor_key != "global":
                    target_labels = [anchor_key]
            for label in target_labels:
                by_label[label] = by_label.get(label, 0.0) + min(0.42, strength * 0.35)
        return {label: round(min(0.6, value), 4) for label, value in by_label.items()}

    def _build_action_bias_by_label(self, controls: list[dict]) -> dict[str, dict]:
        by_label: dict[str, dict] = {}
        for control in controls or []:
            if not isinstance(control, dict):
                continue
            strength = max(0.0, float(control.get("strength", 0.0) or 0.0))
            if strength <= 0.0:
                continue
            source = str(control.get("source_action_id", "") or control.get("control_kind", "") or "action_control")
            control_kind = str(control.get("control_kind", "") or "")
            # Inspect/focus actions should be visible but bounded. They bias the
            # next readout of the cognitive field; they do not create truth.
            boost_gain = 0.55 if control_kind in {"focus_anchor", "inspect_residual"} else 0.38
            suppression_gain = 0.65 if control_kind == "release_focus" else 0.45
            for label in [str(item or "") for item in list(control.get("boost_labels", []) or []) if str(item or "")]:
                bucket = by_label.setdefault(label, {"boost": 0.0, "suppression": 0.0, "sources": []})
                bucket["boost"] = float(bucket.get("boost", 0.0) or 0.0) + min(0.55, strength * boost_gain)
                sources = list(bucket.get("sources", []) or [])
                if source not in sources:
                    sources.append(source)
                bucket["sources"] = sources
            for label in [str(item or "") for item in list(control.get("suppress_labels", []) or []) if str(item or "")]:
                bucket = by_label.setdefault(label, {"boost": 0.0, "suppression": 0.0, "sources": []})
                bucket["suppression"] = float(bucket.get("suppression", 0.0) or 0.0) + min(0.62, strength * suppression_gain)
                sources = list(bucket.get("sources", []) or [])
                if source not in sources:
                    sources.append(source)
                bucket["sources"] = sources
        return {
            label: {
                "boost": round(min(0.75, float(value.get("boost", 0.0) or 0.0)), 4),
                "suppression": round(min(0.75, float(value.get("suppression", 0.0) or 0.0)), 4),
                "sources": list(value.get("sources", []) or [])[:4],
            }
            for label, value in by_label.items()
        }

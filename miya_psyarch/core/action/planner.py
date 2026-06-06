from __future__ import annotations

import hashlib
import json
from collections import defaultdict

from miya_psyarch.core.action.outcome_memory import ActionOutcomeMemory
from miya_psyarch.core.action.parameter_memory import ActionParameterMemory
from miya_psyarch.core.action.registry import action_actuator_id, action_meta, actuator_meta, is_external_action


PASSIVE_MAINTENANCE_ACTIONS = {
    "action::hold_gaze",
    "action::lock_audio_band",
    "action::wait",
}


def _round4(value: float) -> float:
    return round(float(value), 4)


def _clamp(value: float, low: float, high: float) -> float:
    return max(float(low), min(float(high), float(value)))


class ActionConsequencePlanner:
    def __init__(
        self,
        *,
        enabled: bool,
        selection_threshold: float,
        max_selected_actions: int,
        fatigue_decay: float,
        fatigue_step: float,
        bias_learning_rate: float,
        bias_gain: float,
        confidence_gain: float,
        wait_base_drive: float,
        outcome_memory_enabled: bool = True,
        outcome_memory_learning_rate: float = 0.18,
        outcome_memory_decay_per_tick: float = 0.992,
        outcome_memory_support_scale: float = 6.0,
        outcome_memory_max_drive_bias: float = 0.75,
    ) -> None:
        self.enabled = bool(enabled)
        self.selection_threshold = max(0.0, float(selection_threshold))
        self.max_selected_actions = max(1, int(max_selected_actions))
        self.fatigue_decay = _clamp(fatigue_decay, 0.0, 1.0)
        self.fatigue_step = max(0.0, float(fatigue_step))
        self.bias_learning_rate = max(0.0, float(bias_learning_rate))
        self.bias_gain = max(0.0, float(bias_gain))
        self.confidence_gain = max(0.0, float(confidence_gain))
        self.wait_base_drive = max(0.0, float(wait_base_drive))
        self._actuator_fatigue: dict[str, float] = defaultdict(float)
        self._drive_bias: dict[str, float] = defaultdict(float)
        self._feedback_modulation: dict[str, dict[str, float | int]] = {}
        self._visual_target_fatigue: dict[str, float] = defaultdict(float)
        self._parameter_action_fatigue: dict[str, dict] = {}
        self._last_tick = -1
        self._outcome_memory = ActionOutcomeMemory(
            enabled=outcome_memory_enabled,
            learning_rate=outcome_memory_learning_rate,
            decay_per_tick=outcome_memory_decay_per_tick,
            support_scale=outcome_memory_support_scale,
            max_drive_bias=outcome_memory_max_drive_bias,
        )
        self._parameter_memory = ActionParameterMemory(
            enabled=outcome_memory_enabled,
            learning_rate=outcome_memory_learning_rate,
            decay_per_tick=outcome_memory_decay_per_tick,
        )

    def plan(
        self,
        *,
        tick_index: int,
        state_snapshot_items: list[dict],
        attention_trace: dict | None = None,
        fast_bn: list[dict],
        fast_cn: list[dict],
        slow_bn: list[dict],
        slow_cn: list[dict],
        cognitive_feelings: dict,
        rhythm_trace: dict,
        time_trace: dict,
        expectation_pressure_trace: dict | None = None,
        residual_summary: dict | None = None,
        prediction_trace: dict | None = None,
        action_consequence_trace: dict | None = None,
        emotion_modulation: dict | None = None,
        innate_action_nodes: list[dict] | None = None,
        innate_action_biases: list[dict] | None = None,
        recent_thought_readback: dict | None = None,
        short_term_memory_readback: dict | None = None,
        memory_action_drive_gain: float = 0.28,
    ) -> dict:
        self._advance_tick(int(tick_index))
        if not self.enabled:
            return {"candidates": [], "selected_actions": [], "feedback_items": [], "drive_state": self._drive_snapshot()}
        candidates = self._build_candidates(
            tick_index=int(tick_index),
            state_snapshot_items=state_snapshot_items,
            attention_trace=attention_trace,
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            cognitive_feelings=cognitive_feelings,
            expectation_pressure_trace=expectation_pressure_trace,
            rhythm_trace=rhythm_trace,
            time_trace=time_trace,
            residual_summary=residual_summary,
            prediction_trace=prediction_trace,
            action_consequence_trace=action_consequence_trace,
            emotion_modulation=emotion_modulation,
            innate_action_nodes=innate_action_nodes,
            innate_action_biases=innate_action_biases,
            recent_thought_readback=recent_thought_readback,
            short_term_memory_readback=short_term_memory_readback,
            memory_action_drive_gain=memory_action_drive_gain,
        )
        # Apply emotion modulation to selection threshold (8-channel NT system)
        # emotion_modulation format: {"attention": {...}, "hdb": {...}, "action": {...}}
        action_mod = (emotion_modulation or {}).get("action", {})
        threshold_adjustment = float(action_mod.get("threshold_adjustment", 0.0))
        effective_threshold = max(0.1, self.selection_threshold + threshold_adjustment)
        candidates.sort(key=lambda item: (-float(item["drive"]), item["action_id"]))
        selected, competition_trace = self._select_with_competition(
            candidates=candidates,
            effective_threshold=effective_threshold,
            max_selected_actions=self.max_selected_actions,
        )
        action_items = self._build_action_items(selected, tick_index=int(tick_index))
        return {
            "candidates": candidates,
            "selected_actions": selected,
            "action_items": action_items,
            "feedback_items": [],
            "drive_state": self._drive_snapshot(),
            "effective_threshold": _round4(effective_threshold),
            "consequence_trace": dict(action_consequence_trace or {}),
            "competition_trace": competition_trace,
        }

    def record_feedback(self, *, selected_actions: list[dict], observed_feedback: dict, parameter_events: list[dict] | None = None) -> dict:
        reward = float(observed_feedback.get("reward", 0.0) or 0.0)
        punishment = float(observed_feedback.get("punishment", 0.0) or 0.0)
        correctness = float(observed_feedback.get("correctness", 0.0) or 0.0)
        confidence = float(observed_feedback.get("confidence", 0.0) or 0.0)
        utility = reward + correctness * 0.4 - punishment
        events_by_action = self._parameter_events_by_action(parameter_events or [])
        parameter_estimates = []
        for row in selected_actions:
            action_id = str(row.get("action_id", "") or "")
            if not action_id:
                continue
            outcome_estimate = self._outcome_memory.record(
                action_id=action_id,
                observed_feedback=observed_feedback,
                predicted_outcome=dict(row.get("predicted_outcome", {}) or {}),
            )
            actuator_id = str(row.get("actuator_id", "") or "")
            self._drive_bias[action_id] = _clamp(
                float(self._drive_bias[action_id]) + utility * self.bias_learning_rate,
                -1.0,
                1.0,
            )
            self._actuator_fatigue[actuator_id] = _clamp(
                float(self._actuator_fatigue[actuator_id]) + self.fatigue_step * max(0.5, confidence),
                0.0,
                1.0,
            )
            self._record_parameter_action_fatigue(
                action_id=action_id,
                actuator_id=actuator_id,
                params=dict(row.get("params", {}) or {}),
                confidence=confidence,
                utility=utility,
            )
            modulation = 1.0
            ttl = 0
            if utility < -0.04:
                modulation = 0.48
                ttl = 2
            elif utility < 0.04:
                modulation = 0.72
                ttl = 1
            elif utility > 0.32:
                modulation = 1.08
                ttl = 1
            self._feedback_modulation[action_id] = {
                "modulation": _round4(modulation),
                "ttl": int(ttl),
                "last_utility": _round4(utility),
                "outcome_support": _round4(float(outcome_estimate.get("support", 0.0) or 0.0)),
                "outcome_drive_bias": _round4(float(outcome_estimate.get("drive_bias", 0.0) or 0.0)),
                }
            for event in events_by_action.get(action_id, []):
                parameter_estimates.append(
                    self._parameter_memory.record(
                        action_id=action_id,
                        selected_action=row,
                        control_event=event,
                        observed_feedback=observed_feedback,
                        tick_index=event.get("tick_index"),
                    )
                )
        self._update_visual_target_fatigue(
            selected_actions=selected_actions,
            parameter_events=parameter_events or [],
            observed_feedback=observed_feedback,
        )
        return {
            "updated_bias": {key: _round4(value) for key, value in self._drive_bias.items()},
            "updated_fatigue": {key: _round4(value) for key, value in self._actuator_fatigue.items()},
            "feedback_modulation": {key: dict(value) for key, value in self._feedback_modulation.items()},
            "outcome_memory": self._outcome_memory.snapshot(),
            "parameter_memory": self._parameter_memory.snapshot(),
            "parameter_estimates": parameter_estimates,
        }

    def _select_with_competition(
        self,
        *,
        candidates: list[dict],
        effective_threshold: float,
        max_selected_actions: int,
    ) -> tuple[list[dict], dict]:
        """
        Select actions through AP actuator conflict domains.

        A humanlike action field can contain two strong impulses at once. We do
        not erase the losing impulse; we record the competition cost so the
        later feedback/learning chain can know "this wanted to happen too".
        """

        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in candidates or []:
            domain = self._conflict_domain(row)
            grouped[domain].append(row)

        selected: list[dict] = []
        domain_rows: list[dict] = []
        epsilon = 0.0001
        for domain, rows in sorted(grouped.items(), key=lambda item: item[0]):
            ordered = sorted(rows, key=lambda item: (-float(item.get("drive", 0.0) or 0.0), str(item.get("action_id", "") or "")))
            if not ordered:
                continue
            winner = dict(ordered[0])
            second = dict(ordered[1]) if len(ordered) > 1 else {}
            winner_drive = float(winner.get("drive", 0.0) or 0.0)
            second_drive = float(second.get("drive", 0.0) or 0.0)
            competition_cost = max(0.0, second_drive - float(effective_threshold) + epsilon) if second_drive >= float(effective_threshold) else 0.0
            winner_after = max(0.0, winner_drive - competition_cost)
            suppressed = [
                str(row.get("action_id", "") or "")
                for row in ordered[1:]
                if float(row.get("drive", 0.0) or 0.0) >= float(effective_threshold)
            ]
            domain_trace = {
                "conflict_domain": domain,
                "winner_action_id": str(winner.get("action_id", "") or ""),
                "winner_drive_before": _round4(winner_drive),
                "winner_drive_after_competition": _round4(winner_after),
                "second_action_id": str(second.get("action_id", "") or ""),
                "second_drive": _round4(second_drive),
                "competition_cost": _round4(competition_cost),
                "suppressed_action_ids": suppressed,
                "candidate_count": len(ordered),
            }
            domain_rows.append(domain_trace)
            if winner_after < float(effective_threshold):
                continue
            winner["drive_before_competition"] = _round4(winner_drive)
            winner["drive"] = _round4(winner_after)
            winner["competition_cost"] = _round4(competition_cost)
            winner["suppressed_action_ids"] = suppressed
            winner["conflict_domain"] = domain
            winner["planner_selected"] = True
            winner["effective_threshold"] = _round4(effective_threshold)
            winner["effective_decisiveness"] = _round4(max(0.0, winner_after - float(effective_threshold)))
            winner.setdefault("notes", [])
            if competition_cost > 0.0:
                winner["notes"] = list(winner.get("notes", []) or []) + ["action_competition_cost_applied"]
            selected.append(winner)

        selected.sort(key=lambda item: (-float(item.get("drive", 0.0) or 0.0), str(item.get("action_id", "") or "")))
        selected_ids = {str(row.get("action_id", "") or "") for row in selected}
        return selected, {
            "schema_id": "action_competition_trace/v1",
            "effective_threshold": _round4(effective_threshold),
            "policy": "one_winner_per_conflict_domain_independent_threshold_no_global_topn_clip",
            "max_selected_actions_observability_only": int(max_selected_actions),
            "selected_action_ids": sorted(selected_ids),
            "parallel_channel_floor": self._parallel_channel_floor_trace(selected),
            "domains": domain_rows,
            "suppressed_action_ids": sorted(
                {
                    action_id
                    for domain in domain_rows
                    for action_id in list(domain.get("suppressed_action_ids", []) or [])
                    if action_id and action_id not in selected_ids
                }
            ),
        }

    def _apply_parallel_channel_floor(self, selected: list[dict], *, max_selected_actions: int) -> list[dict]:
        """
        Compatibility shim for the older global-clip era.

        APV2.1 now treats conflict domains as independent execution lanes:
        after each lane chooses its winner, there is no cross-lane TopN clip.
        This method remains only so older traces/tests can see that the previous
        sensorimotor-floor workaround is deliberately inactive.
        """

        return [dict(row) for row in selected]

    def _parallel_floor_replace_index(self, rows: list[dict]) -> int | None:
        protected_domains = {
            "single_visual_center",
            "visual_sampling_scale",
            "single_auditory_band_center",
            "auditory_sampling_width",
        }
        replaceable = [
            (idx, float(row.get("drive", 0.0) or 0.0), str(row.get("action_id", "") or ""))
            for idx, row in enumerate(rows)
            if str(row.get("conflict_domain", "") or self._conflict_domain(row)) not in protected_domains
            and str(row.get("conflict_domain", "") or self._conflict_domain(row))
            in {"attention_focus_width_and_anchor", "legacy_internal_prediction"}
            and str(row.get("action_id", "") or "") != "action::wait"
        ]
        if not replaceable:
            replaceable = [
                (idx, float(row.get("drive", 0.0) or 0.0), str(row.get("action_id", "") or ""))
                for idx, row in enumerate(rows)
                if str(row.get("conflict_domain", "") or self._conflict_domain(row)) not in protected_domains
                and str(row.get("conflict_domain", "") or self._conflict_domain(row))
                in {"attention_focus_width_and_anchor", "legacy_internal_prediction"}
            ]
        if not replaceable:
            return None
        replaceable.sort(key=lambda item: (item[1], item[2]))
        return int(replaceable[0][0])

    def _parallel_channel_floor_trace(self, selected: list[dict]) -> dict:
        return {
            "schema_id": "sensorimotor_parallel_channel_floor/v1",
            "enabled": False,
            "disabled_reason": "no_global_topn_clip_conflict_domains_are_independent_execution_lanes",
            "protected_domains": [
                "single_visual_center",
                "visual_sampling_scale",
                "single_auditory_band_center",
                "auditory_sampling_width",
            ],
            "selected_by_floor": [
                str(row.get("action_id", "") or "")
                for row in selected
                if bool(row.get("parallel_channel_floor", False))
            ],
        }

    def _conflict_domain(self, candidate: dict) -> str:
        actuator_id = str((candidate or {}).get("actuator_id", "") or "")
        meta = actuator_meta(actuator_id)
        domain = str(meta.get("conflict_domain", "") or "")
        return domain or actuator_id or "unknown_action_domain"

    def _build_candidates(
        self,
        *,
        tick_index: int,
        state_snapshot_items: list[dict],
        attention_trace: dict | None = None,
        fast_bn: list[dict],
        fast_cn: list[dict],
        slow_bn: list[dict],
        slow_cn: list[dict],
        cognitive_feelings: dict,
        rhythm_trace: dict,
        time_trace: dict,
        expectation_pressure_trace: dict | None = None,
        residual_summary: dict | None = None,
        prediction_trace: dict | None = None,
        action_consequence_trace: dict | None = None,
        emotion_modulation: dict | None = None,
        innate_action_nodes: list[dict] | None = None,
        innate_action_biases: list[dict] | None = None,
        recent_thought_readback: dict | None = None,
        short_term_memory_readback: dict | None = None,
        memory_action_drive_gain: float = 0.28,
    ) -> list[dict]:
        pressure = float((cognitive_feelings.get("channels", {}) or {}).get("pressure", 0.0) or 0.0)
        dissonance = float((cognitive_feelings.get("channels", {}) or {}).get("dissonance", 0.0) or 0.0)
        expectation = float((cognitive_feelings.get("channels", {}) or {}).get("expectation", 0.0) or 0.0)
        correctness = float((cognitive_feelings.get("channels", {}) or {}).get("correctness", 0.0) or 0.0)
        grasp = float((cognitive_feelings.get("channels", {}) or {}).get("grasp", 0.0) or 0.0)
        uncertainty = float((cognitive_feelings.get("channels", {}) or {}).get("uncertainty", 0.0) or 0.0)
        boredom = _clamp(float((cognitive_feelings.get("channels", {}) or {}).get("boredom", 0.0) or 0.0), 0.0, 1.0)
        fulfillment = _clamp(float((cognitive_feelings.get("channels", {}) or {}).get("fulfillment", 0.0) or 0.0), 0.0, 1.0)
        task_available = _clamp(float((cognitive_feelings.get("channels", {}) or {}).get("task_available", 0.0) or 0.0), 0.0, 1.0)
        unfinished_strength = _clamp(float((cognitive_feelings.get("channels", {}) or {}).get("unfinished_strength", 0.0) or 0.0), 0.0, 1.0)
        ep_channels = dict((expectation_pressure_trace or {}).get("channels", {}) or {})
        expectation_level = float(ep_channels.get("expectation_level", 0.0) or 0.0)
        pressure_level = float(ep_channels.get("pressure_level", 0.0) or 0.0)
        satisfaction_level = float(ep_channels.get("satisfaction_level", 0.0) or 0.0)
        expectation_gap = float(ep_channels.get("expectation_gap", 0.0) or 0.0)
        expectation_anchor_trace = dict((expectation_pressure_trace or {}).get("anchor_verification", {}) or {})
        expectation_anchors = self._active_expectation_anchors(expectation_anchor_trace)
        top_anchor_level = max([float(anchor.get("level", 0.0) or 0.0) for anchor in expectation_anchors] or [0.0])
        pressure_anchor_level = max(
            [
                float(anchor.get("level", 0.0) or 0.0)
                for anchor in expectation_anchors
                if str(anchor.get("anchor_type", "") or "") == "pressure"
            ]
            or [0.0]
        )
        expectation_anchor_level = max(
            [
                float(anchor.get("level", 0.0) or 0.0)
                for anchor in expectation_anchors
                if str(anchor.get("anchor_type", "") or "") == "expectation"
            ]
            or [0.0]
        )
        expectation = max(expectation, expectation_level)
        pressure = max(pressure, pressure_level)
        rhythm_expect = float((rhythm_trace.get("channels", {}) or {}).get("phase_expectation", 0.0) or 0.0)
        time_conf = float((time_trace.get("channels", {}) or {}).get("confidence", 0.0) or 0.0)
        dominant_time_peak = dict((time_trace or {}).get("dominant_peak", {}) or {})
        target_delta_t = dominant_time_peak.get("center_delta_t")
        time_sigma = dominant_time_peak.get("sigma", 1.0)
        predicted_mass = sum(len(branch.get("predicted_items", []) or []) for branch in fast_cn) + sum(
            len(branch.get("predicted_items", []) or []) for branch in slow_cn
        )
        focusable_count = sum(1 for item in state_snapshot_items if float(item.get("cognitive_pressure", 0.0) or 0.0) > 0.0)
        residual = dict(residual_summary or {})
        trace = dict(prediction_trace or {})
        residual_mass = float(residual.get("total_unresolved_mass", 0.0) or 0.0)
        residual_count = int(residual.get("count", 0) or 0)
        residual_drive = _clamp(residual_mass / max(1.0, residual_mass + len(state_snapshot_items)), 0.0, 1.0)
        mismatch_ratio = float(trace.get("mismatch_ratio", 0.0) or 0.0)
        alignment_score = float(trace.get("alignment_score", 0.0) or 0.0)
        output_mismatch = self._output_mismatch_context(state_snapshot_items)
        correction_pressure = float(output_mismatch.get("correction_pressure", 0.0) or 0.0)
        latest_expected_token = str(output_mismatch.get("latest_expected_token", "") or "")
        reread_after_mismatch = bool(output_mismatch.get("reread_after_mismatch", False))
        expected_text = self._expected_text_context(fast_cn=fast_cn, slow_cn=slow_cn)
        expected_token = str(expected_text.get("token", "") or "")
        expected_strength = float(expected_text.get("strength", 0.0) or 0.0)
        draft_context = self._draft_writing_context(state_snapshot_items, current_tick=int(tick_index))
        visible_length = int(draft_context.get("visible_length", 0) or 0)
        revision_opportunities = self._text_revision_opportunities(state_snapshot_items)
        draft_eval = self._draft_self_evaluation(
            draft_context,
            expected_text,
            correctness=correctness,
            grasp=grasp,
            pressure=pressure,
            dissonance=dissonance,
            uncertainty=uncertainty,
        )
        continuation_readiness = float(draft_eval.get("continuation_readiness", 0.0) or 0.0)
        ambiguity_pause = float(draft_eval.get("ambiguity_pause", 0.0) or 0.0)
        cleanup_pressure = float(draft_eval.get("cleanup_pressure", 0.0) or 0.0)
        draft_satisfaction = float(draft_eval.get("satisfaction", 0.0) or 0.0)
        successor_decisive = bool(expected_text.get("decisive", False))
        recent_thought = dict(recent_thought_readback or {})
        readback_available = bool(recent_thought.get("available", False))
        readback_strength = _clamp(float(recent_thought.get("strength", 0.0) or 0.0), 0.0, 1.0)
        readback_drift = _clamp(float(recent_thought.get("drift_score", 0.0) or 0.0), 0.0, 1.0)
        readback_branch_end = _clamp(float(recent_thought.get("branch_end_score", 0.0) or 0.0), 0.0, 1.0)
        short_term_readback = dict(short_term_memory_readback or {})
        short_term_available = bool(short_term_readback.get("available", False))
        short_term_strength = _clamp(
            max([float(event.get("score", 0.0) or 0.0) for event in list(short_term_readback.get("selected_events", []) or []) if isinstance(event, dict)] or [0.0]) / 3.0,
            0.0,
            1.0,
        )
        short_term_candidate_pressure = _clamp(float(short_term_readback.get("candidate_count", 0) or 0) / 6.0, 0.0, 1.0)

        # Extract emotion modulation (reward gain affects utility calculation)
        action_mod = (emotion_modulation or {}).get("action", {})
        reward_gain_multiplier = float(action_mod.get("reward_gain_multiplier", 1.0))
        exploration_bias = float(action_mod.get("exploration_bias", 0.0) or 0.0)
        consequence_estimates = dict((action_consequence_trace or {}).get("action_estimates", {}) or {})
        commit_outcome_estimate = self._outcome_memory.estimate("action::text_commit")
        draft_goal_alignment = self._draft_goal_alignment(
            state_snapshot_items=state_snapshot_items,
            draft_context=draft_context,
            fast_cn=fast_cn,
            slow_cn=slow_cn,
            consequence_estimates=consequence_estimates,
            outcome_estimate=commit_outcome_estimate,
        )
        draft_satisfaction_field = self._draft_satisfaction_field(
            draft_eval=draft_eval,
            draft_goal_alignment=draft_goal_alignment,
            correctness=correctness,
            grasp=grasp,
            pressure=pressure,
            dissonance=dissonance,
            uncertainty=uncertainty,
            pressure_anchor_level=pressure_anchor_level,
            expectation_gap=expectation_gap,
        )
        visual_target = self._visual_gaze_target_context(
            state_snapshot_items=state_snapshot_items,
            attention_trace=attention_trace or {},
        )

        candidates = []
        replay_base_drive = (
            0.18
            + time_conf * 0.26
            + expectation * 0.14
            + expectation_gap * 0.12
            + correction_pressure * 0.42
            + max(0.0, 1.0 - correctness) * 0.18
            + dissonance * 0.12
        )
        if correction_pressure > 0.0:
            # Output-side mismatch is not generic prediction stabilization. It is
            # specifically a reread/revise situation, so replay gets an explicit
            # local priority instead of being crowded out by high predicted_mass.
            replay_base_drive += 0.34 + correction_pressure * 0.22
        candidates.append(
            self._candidate(
                action_id="action::continue_focus",
                actuator_id=action_actuator_id("action::continue_focus", "actuator::attention_allocation"),
                base_drive=0.18
                + expectation * 0.32
                + grasp * 0.24
                + rhythm_expect * 0.18
                + satisfaction_level * 0.08
                + fulfillment * 0.10
                + max(0.0, task_available - 0.42) * 0.08
                - boredom * 0.06,
                predicted={
                    "reward": (0.22 + grasp * 0.28) * reward_gain_multiplier,
                    "punishment": max(0.0, 0.12 - grasp * 0.08),
                    "expectation": expectation * 0.85,
                    "pressure": max(0.0, pressure * 0.65 - grasp * 0.18),
                    "correctness": correctness * 0.72 + grasp * 0.18,
                    "confidence": 0.35 + grasp * self.confidence_gain + rhythm_expect * 0.12,
                },
                notes=[
                    "slow_continuation",
                    "focus_development",
                    f"expectation_level={_round4(expectation_level)}",
                    f"satisfaction_level={_round4(satisfaction_level)}",
                    f"fulfillment={_round4(fulfillment)}",
                    f"task_available={_round4(task_available)}",
                ],
                consequence_estimates=consequence_estimates,
            )
        )
        candidates.append(
            self._candidate(
                action_id="action::inspect_residual",
                actuator_id=action_actuator_id("action::inspect_residual", "actuator::attention_allocation"),
                base_drive=0.14
                + dissonance * 0.38
                + pressure * 0.22
                + residual_drive * 0.34
                + mismatch_ratio * 0.22
                + pressure_level * 0.16
                + min(0.18, residual_count * 0.03)
                + max(0.0, predicted_mass - 1) * 0.02,
                predicted={
                    "reward": (0.14 + dissonance * 0.16 + residual_drive * 0.14 + mismatch_ratio * 0.08) * reward_gain_multiplier,
                    "punishment": max(0.0, 0.08 - dissonance * 0.03 + max(0.0, alignment_score - 0.3) * 0.02),
                    "expectation": expectation * 0.42,
                    "pressure": pressure * 0.88 + expectation_gap * 0.08,
                    "correctness": correctness * 0.52 + dissonance * 0.08,
                    "confidence": 0.28 + dissonance * self.confidence_gain,
                },
                notes=[
                    "residual_probe",
                    "mismatch_resolution",
                    f"residual_mass={_round4(residual_mass)}",
                    f"mismatch_ratio={_round4(mismatch_ratio)}",
                    f"pressure_level={_round4(pressure_level)}",
                ],
                consequence_estimates=consequence_estimates,
            )
        )
        if readback_available or short_term_available:
            no_clear_successor = bool(int(expected_text.get("candidate_count", 0) or 0) <= 0 or not successor_decisive)
            readback_drive = (
                0.12
                + readback_strength * 0.30
                + readback_drift * 0.28
                + readback_branch_end * 0.24
                + short_term_strength * 0.22
                + short_term_candidate_pressure * 0.10
                + boredom * 0.14
                + unfinished_strength * 0.20
                + uncertainty * 0.14
                + ambiguity_pause * 0.18
                + (0.12 if no_clear_successor else 0.0)
                + max(0.0, 0.42 - continuation_readiness) * 0.12
                - pressure * 0.06
            )
            candidates.append(
                self._candidate(
                    action_id="action::recall_recent_context",
                    actuator_id=action_actuator_id("action::recall_recent_context", "actuator::memory_recall"),
                    base_drive=max(0.0, readback_drive),
                    predicted={
                        "reward": (0.08 + readback_strength * 0.10 + short_term_strength * 0.06 + readback_drift * 0.04 + readback_branch_end * 0.05) * reward_gain_multiplier,
                        "punishment": max(0.018, 0.05 - readback_strength * 0.015),
                        "expectation": max(expectation * 0.20, readback_strength * 0.20, short_term_strength * 0.18),
                        "pressure": max(0.0, pressure * 0.24 + ambiguity_pause * 0.04),
                        "correctness": correctness * 0.18 + readback_strength * 0.18 + short_term_strength * 0.10,
                        "confidence": 0.22 + readback_strength * 0.20 + short_term_strength * 0.12 + max(readback_drift, readback_branch_end) * 0.12,
                    },
                    notes=[
                        "recent_thought_readback",
                        "short_term_memory_self_observation",
                        "multimodal_short_term_memory" if short_term_available else "focus_only_short_term_memory",
                        "branch_end_or_drift" if (readback_drift >= 0.18 or readback_branch_end >= 0.34 or no_clear_successor) else "ordinary_recent_context_readback",
                        "unfinished_thought_recovery_bias" if unfinished_strength >= 0.12 else "ordinary_no_param_recall_bias",
                        "boredom_drives_self_probe" if boredom >= 0.12 else "task_feeling_low",
                        f"readback_strength={_round4(readback_strength)}",
                        f"short_term_strength={_round4(short_term_strength)}",
                        f"unfinished_strength={_round4(unfinished_strength)}",
                        f"boredom={_round4(boredom)}",
                        f"drift_score={_round4(readback_drift)}",
                        f"branch_end_score={_round4(readback_branch_end)}",
                        f"successor_decisive={successor_decisive}",
                    ],
                    consequence_estimates=consequence_estimates,
                    params={
                        "horizon": int(recent_thought.get("horizon", 6) or 6),
                        "reason": "recent_thought_readback",
                        "recall_mode": "unfinished_soft_recovery" if unfinished_strength >= 0.12 else ("no_param_recent_context" if no_clear_successor else "cued_recent_context"),
                        "labels": list(recent_thought.get("labels", []) or [])[:8],
                        "active_episode_id": int(recent_thought.get("active_episode_id", -1) or -1),
                        "short_term_event_ids": [
                            str(event.get("event_id", "") or "")
                            for event in list(short_term_readback.get("selected_events", []) or [])[:4]
                            if isinstance(event, dict)
                        ],
                    },
                )
            )
        if expected_token and correction_pressure <= 0.0:
            last_visible_token = str(draft_context.get("last_visible_token", "") or "")
            last_insert_tick = int(draft_context.get("last_insert_tick", -1) or -1)
            last_reread_tick = int(draft_context.get("last_reread_tick", -1) or -1)
            last_commit_tick = int(draft_context.get("last_commit_tick", -1) or -1)
            visible_length = int(draft_context.get("visible_length", 0) or 0)
            insert_count = int(draft_context.get("insert_count", 0) or 0)
            has_internal_draft = bool(draft_context.get("has_internal_draft", False))
            same_token_waiting_for_reread = bool(
                last_visible_token
                and expected_token == last_visible_token
                and last_insert_tick >= 0
                and last_insert_tick > max(last_reread_tick, last_commit_tick)
            )
            if not same_token_waiting_for_reread:
                continuation_bonus = 0.14 if has_internal_draft else 0.0
                early_draft_bonus = 0.08 if 0 < visible_length < 5 else 0.0
                new_draft_bonus = 0.06 if insert_count <= 0 else 0.0
                ambiguous_successor_cost = 0.0
                if not successor_decisive:
                    ambiguous_successor_cost = 0.20 + uncertainty * 0.18 + ambiguity_pause * 0.22 + max(0.0, 0.46 - grasp) * 0.12
                expected_drive = (
                    0.36
                    + expected_strength * 0.62
                    + continuation_readiness * 0.28
                    + expectation * 0.16
                    + grasp * 0.10
                    + correctness * 0.08
                    + continuation_bonus
                    + early_draft_bonus
                    + new_draft_bonus
                    - pressure * 0.28
                    - uncertainty * 0.10
                    - ambiguity_pause * 0.30
                    - cleanup_pressure * 0.36
                    - ambiguous_successor_cost
                )
                if expected_drive > 0.02:
                    # Text insert is a one-token draft action. The candidate is
                    # intentionally local and parameterized by live Cn/Cn'
                    # evidence. If the successor is so ambiguous that its
                    # base write impulse collapses, no write candidate is
                    # emitted; wait/recall/resampling can still win instead.
                    candidates.append(
                        self._candidate(
                            action_id="action::text_insert",
                            actuator_id=action_actuator_id("action::text_insert", "actuator::text_editor"),
                            base_drive=max(0.0, expected_drive),
                            predicted={
                                "reward": (0.15 + expected_strength * 0.14 + continuation_readiness * 0.08 + continuation_bonus * 0.30) * reward_gain_multiplier,
                                "punishment": max(0.025, 0.08 + pressure * 0.04 + ambiguity_pause * 0.03 - expected_strength * 0.03),
                                "expectation": max(expectation * 0.56, expected_strength * 0.62 + continuation_readiness * 0.18),
                                "pressure": max(0.0, pressure * 0.42 + uncertainty * 0.04 + ambiguity_pause * 0.08 + cleanup_pressure * 0.08),
                                "correctness": correctness * 0.30 + expected_strength * 0.25 + continuation_readiness * 0.12 + grasp * 0.08,
                                "confidence": 0.34 + expected_strength * 0.28 + continuation_readiness * 0.18 + grasp * 0.08 - ambiguity_pause * 0.08,
                            },
                            notes=[
                                "draft_expected_token_write",
                                "one_token_internal_draft_action",
                                "successor_decisive" if successor_decisive else "successor_ambiguous",
                                f"expected_token={expected_token}",
                                f"expected_strength={_round4(expected_strength)}",
                                f"top_share={_round4(float(expected_text.get('top_share', 0.0) or 0.0))}",
                                f"dominance_gap={_round4(float(expected_text.get('dominance_gap', 0.0) or 0.0))}",
                                f"ambiguity_pause={_round4(ambiguity_pause)}",
                                f"ambiguous_successor_cost={_round4(ambiguous_successor_cost)}",
                                f"visible_length={visible_length}",
                            ],
                            consequence_estimates=consequence_estimates,
                            params={"token": expected_token, "reason": "expected_token_draft_write"},
                        )
                    )
        if bool(draft_context.get("has_internal_draft", False)) and correction_pressure <= 0.0:
            visible_length = int(draft_context.get("visible_length", 0) or 0)
            last_event_type = str(draft_context.get("last_event_type", "") or "")
            last_insert_age = int(draft_context.get("last_insert_age", 9999) or 9999)
            last_reread_age = int(draft_context.get("last_reread_age", 9999) or 9999)
            last_delete_age = int(draft_context.get("last_delete_age", 9999) or 9999)
            last_replace_age = int(draft_context.get("last_replace_age", 9999) or 9999)
            last_mutation_tick = int(draft_context.get("last_mutation_tick", -1) or -1)
            last_commit_tick = int(draft_context.get("last_commit_tick", -1) or -1)
            last_commit_age = int(draft_context.get("last_commit_age", 9999) or 9999)
            reread_count = int(draft_context.get("reread_count", 0) or 0)
            just_inserted = last_insert_age <= 2 and last_event_type in {"insert", "replace"}
            review_due = just_inserted or (visible_length >= 2 and last_reread_age > 2)
            if review_due or ambiguity_pause >= 0.32 or cleanup_pressure >= 0.28:
                repeat_reread_penalty = 0.22 if (last_event_type == "reread" and last_reread_age <= 1) else 0.0
                review_drive = (
                    0.44
                    + (0.46 if just_inserted else 0.12)
                    + min(0.18, visible_length * 0.04)
                    + uncertainty * 0.10
                    + ambiguity_pause * 0.28
                    + cleanup_pressure * 0.20
                    + max(0.0, 0.5 - correctness) * 0.08
                    - pressure * 0.10
                    - repeat_reread_penalty
                )
                candidates.append(
                    self._candidate(
                        action_id="action::text_reread",
                        actuator_id=action_actuator_id("action::text_reread", "actuator::text_editor"),
                        base_drive=max(0.0, review_drive),
                        predicted={
                            "reward": (0.12 + min(0.18, visible_length * 0.03) + (0.06 if just_inserted else 0.0)) * reward_gain_multiplier,
                            "punishment": max(0.015, 0.05 - min(0.02, reread_count * 0.004)),
                            "expectation": expectation * 0.34 + expected_strength * 0.18,
                            "pressure": max(0.0, pressure * 0.28 - 0.04),
                            "correctness": correctness * 0.34 + grasp * 0.10 + 0.10,
                            "confidence": 0.38 + grasp * 0.12 + min(0.20, visible_length * 0.04),
                        },
                        notes=[
                            "draft_reread_for_review",
                            "humanlike_pause_after_writing",
                            "successor_distribution_review" if ambiguity_pause >= 0.32 else "draft_surface_review",
                            f"last_event_type={last_event_type}",
                            f"last_insert_age={last_insert_age}",
                            f"ambiguity_pause={_round4(ambiguity_pause)}",
                            f"cleanup_pressure={_round4(cleanup_pressure)}",
                            f"visible_length={visible_length}",
                            f"repeat_reread_penalty={_round4(repeat_reread_penalty)}",
                        ],
                        consequence_estimates=consequence_estimates,
                        params={"reason": "draft_review"},
                    )
                )
            trailing_repeat_count = int(draft_context.get("trailing_repeat_count", 0) or 0)
            trailing_repeat_token = str(draft_context.get("trailing_repeat_token", "") or "")
            if trailing_repeat_count >= 2 and cleanup_pressure >= 0.24 and last_delete_age > 1:
                delete_start = max(0, visible_length - 1)
                delete_drive = (
                    0.34
                    + cleanup_pressure * 0.62
                    + (0.10 if last_reread_age <= 3 else 0.0)
                    + dissonance * 0.08
                    - pressure * 0.10
                    - (0.18 if last_delete_age <= 3 else 0.0)
                )
                candidates.append(
                    self._candidate(
                        action_id="action::text_delete",
                        actuator_id=action_actuator_id("action::text_delete", "actuator::text_editor"),
                        base_drive=max(0.0, delete_drive),
                        predicted={
                            "reward": (0.11 + cleanup_pressure * 0.20 + (0.04 if last_reread_age <= 3 else 0.0)) * reward_gain_multiplier,
                            "punishment": max(0.03, pressure * 0.05),
                            "expectation": expectation * 0.20,
                            "pressure": max(0.0, pressure * 0.36 - cleanup_pressure * 0.06),
                            "correctness": correctness * 0.24 + cleanup_pressure * 0.24,
                            "confidence": 0.34 + cleanup_pressure * 0.28,
                        },
                        notes=[
                            "draft_tail_repetition_cleanup",
                            "local_delete_not_sentence_reset",
                            f"trailing_repeat_token={trailing_repeat_token}",
                            f"trailing_repeat_count={trailing_repeat_count}",
                            f"cleanup_pressure={_round4(cleanup_pressure)}",
                        ],
                        consequence_estimates=consequence_estimates,
                        params={"span": [delete_start, visible_length], "reason": "tail_repetition_cleanup"},
                    )
                )
            last_visible_token = str(draft_context.get("last_visible_token", "") or "")
            if (
                expected_token
                and last_visible_token
                and expected_token != last_visible_token
                and last_reread_age <= 3
                and last_replace_age > 2
                and cleanup_pressure < 0.55
                and ambiguity_pause <= 0.42
                and successor_decisive
            ):
                replace_drive = (
                    0.30
                    + continuation_readiness * 0.24
                    + expected_strength * 0.20
                    + correctness * 0.08
                    - pressure * 0.12
                )
                replace_params = {"span": [max(0, visible_length - 1), visible_length], "new_text": expected_token, "expected_token": expected_token, "from_token": last_visible_token, "reason": "local_successor_revision"}
                replace_parameter_estimate = self._parameter_memory.estimate(action_id="action::text_replace", proposed_params=replace_params)
                replace_drive += float(replace_parameter_estimate.get("drive_bias", 0.0) or 0.0)
                candidates.append(
                    self._candidate(
                        action_id="action::text_replace",
                        actuator_id=action_actuator_id("action::text_replace", "actuator::text_editor"),
                        base_drive=max(0.0, replace_drive),
                        predicted={
                            "reward": (0.10 + continuation_readiness * 0.10 + expected_strength * 0.06) * reward_gain_multiplier,
                            "punishment": max(0.035, pressure * 0.05 + ambiguity_pause * 0.03),
                            "expectation": expectation * 0.22 + expected_strength * 0.16,
                            "pressure": max(0.0, pressure * 0.38 + ambiguity_pause * 0.04),
                            "correctness": correctness * 0.26 + continuation_readiness * 0.18,
                            "confidence": 0.34 + continuation_readiness * 0.18 + expected_strength * 0.10,
                        },
                        notes=[
                            "draft_local_replace_after_reread",
                            "successor_decisive_local_revision",
                            f"from_token={last_visible_token}",
                            f"to_token={expected_token}",
                            f"last_reread_age={last_reread_age}",
                        ]
                        + (
                            [
                                "parameter_memory_bias",
                                f"parameter_drive_bias={_round4(float(replace_parameter_estimate.get('drive_bias', 0.0) or 0.0))}",
                                f"parameter_similarity={_round4(float(replace_parameter_estimate.get('similarity', 0.0) or 0.0))}",
                            ]
                            if float(replace_parameter_estimate.get("support", 0.0) or 0.0) > 0.0
                            else []
                        ),
                        consequence_estimates=consequence_estimates,
                        params=replace_params,
                    )
                )
            stable_after_reread = last_reread_age <= 3 or (last_insert_age >= 3 and reread_count > 0)
            if visible_length > 0 and stable_after_reread:
                pending_revision_pressure = 0.0
                if revision_opportunities:
                    pending_revision_pressure = _clamp(
                        max(float(row.get("support", 0.0) or 0.0) for row in revision_opportunities)
                        * (0.72 if last_reread_age <= 4 else 0.42),
                        0.0,
                        1.0,
                    )
                field_satisfaction = _clamp(float(draft_satisfaction_field.get("satisfaction", 0.0) or 0.0), 0.0, 1.0)
                closure_pressure = _clamp(float(draft_satisfaction_field.get("closure_pressure", 0.0) or 0.0), 0.0, 1.0)
                goal_alignment = _clamp(float(draft_satisfaction_field.get("goal_alignment", 0.0) or 0.0), 0.0, 1.0)
                continuation_pressure = _clamp(float(draft_satisfaction_field.get("continuation_pressure", 0.0) or 0.0), 0.0, 1.0)
                revision_pressure = _clamp(max(float(draft_satisfaction_field.get("revision_pressure", 0.0) or 0.0), pending_revision_pressure), 0.0, 1.0)
                habitual_commit_pressure = _clamp(float(draft_satisfaction_field.get("habitual_commit_pressure", 0.0) or 0.0), 0.0, 1.0)
                outcome_commit_pressure = _clamp(float(draft_satisfaction_field.get("outcome_commit_pressure", 0.0) or 0.0), 0.0, 1.0)
                risk_commit_pressure = _clamp(max(float(draft_satisfaction_field.get("risk_commit_pressure", 0.0) or 0.0), pending_revision_pressure * 0.82), 0.0, 1.0)
                same_draft_already_committed = bool(last_commit_tick >= 0 and last_commit_tick >= last_mutation_tick)
                recent_commit_fatigue = 0.0
                same_draft_commit_fatigue = 0.0
                commit_params = {
                    "target_channel": "draft",
                    "reason": "draft_satisfaction_field_commit_ready",
                    "satisfaction_field": dict(draft_satisfaction_field),
                    "goal_alignment": dict(draft_goal_alignment),
                    "pending_revision_pressure": _round4(pending_revision_pressure),
                    "draft_signature": str(draft_context.get("visible_text", "") or ""),
                    "task_context_signature": self._draft_task_context_signature(draft_goal_alignment),
                }
                commit_drive = (
                    0.28
                    + min(0.22, visible_length * 0.05)
                    + draft_satisfaction * 0.24
                    + field_satisfaction * 0.22
                    + closure_pressure * 0.18
                    + goal_alignment * 0.12
                    + habitual_commit_pressure * 0.24
                    + outcome_commit_pressure * 0.16
                    + correctness * 0.18
                    + grasp * 0.18
                    + (0.16 if last_reread_age <= 2 else 0.0)
                    - max(0.0, expected_strength - 0.35) * 0.06
                    - continuation_pressure * 0.20
                    - revision_pressure * 0.24
                    - risk_commit_pressure * 0.58
                    - ambiguity_pause * 0.22
                    - cleanup_pressure * 0.34
                    - pressure * 0.12
                    - dissonance * 0.10
                    - uncertainty * 0.08
                    - unfinished_strength * 0.30
                    - recent_commit_fatigue
                    - same_draft_commit_fatigue
                    - pending_revision_pressure * 0.68
                )
                candidates.append(
                    self._candidate(
                        action_id="action::text_commit",
                        actuator_id=action_actuator_id("action::text_commit", "actuator::text_editor"),
                        base_drive=max(0.0, commit_drive),
                        predicted={
                            "reward": (
                                0.12
                                + draft_satisfaction * 0.08
                                + field_satisfaction * 0.08
                                + closure_pressure * 0.06
                                + goal_alignment * 0.05
                                + outcome_commit_pressure * 0.06
                                + correctness * 0.18
                                + grasp * 0.12
                            )
                            * reward_gain_multiplier,
                            "punishment": max(
                                0.06,
                                pressure * 0.12
                                + uncertainty * 0.04
                                + cleanup_pressure * 0.04
                                + revision_pressure * 0.05
                                + risk_commit_pressure * 0.16,
                            ),
                            "expectation": expectation * 0.24,
                            "pressure": max(
                                0.0,
                                pressure * 0.48
                                + ambiguity_pause * 0.06
                                + cleanup_pressure * 0.08
                                + continuation_pressure * 0.05
                                + risk_commit_pressure * 0.22
                                + pending_revision_pressure * 0.18
                                + unfinished_strength * 0.10
                                + 0.04,
                            ),
                            "correctness": correctness * 0.50 + grasp * 0.18 + field_satisfaction * 0.12 + goal_alignment * 0.08 + min(0.14, visible_length * 0.02) - pending_revision_pressure * 0.12,
                            "confidence": 0.42 + grasp * 0.16 + correctness * 0.14 + closure_pressure * 0.08 + goal_alignment * 0.06 - pending_revision_pressure * 0.08,
                        },
                        notes=[
                            "draft_commit_ready",
                            "draft_satisfaction_field_commit_ready",
                            "commit_still_external_safety_gate_boundary",
                            "commit_is_internal_draft_closure_not_external_send",
                            f"field_satisfaction={_round4(field_satisfaction)}",
                            f"goal_alignment={_round4(goal_alignment)}",
                            f"closure_pressure={_round4(closure_pressure)}",
                            f"habitual_commit_pressure={_round4(habitual_commit_pressure)}",
                            f"outcome_commit_pressure={_round4(outcome_commit_pressure)}",
                            f"risk_commit_pressure={_round4(risk_commit_pressure)}",
                            f"continuation_pressure={_round4(continuation_pressure)}",
                            f"revision_pressure={_round4(revision_pressure)}",
                            f"pending_revision_pressure={_round4(pending_revision_pressure)}",
                            "commit_risk_from_text_revision_opportunity" if pending_revision_pressure > 0.0 else "no_pending_revision_opportunity",
                            f"habit_scope={str(draft_goal_alignment.get('habit_scope', 'none') or 'none')}",
                            f"draft_satisfaction={_round4(draft_satisfaction)}",
                            f"ambiguity_pause={_round4(ambiguity_pause)}",
                            f"cleanup_pressure={_round4(cleanup_pressure)}",
                            f"last_reread_age={last_reread_age}",
                            f"last_commit_tick={last_commit_tick}",
                            f"last_mutation_tick={last_mutation_tick}",
                            f"last_commit_age={last_commit_age}",
                            f"visible_length={visible_length}",
                            f"recent_commit_fatigue={_round4(recent_commit_fatigue)}",
                            f"same_draft_commit_fatigue={_round4(same_draft_commit_fatigue)}",
                            f"unfinished_strength={_round4(unfinished_strength)}",
                            "unfinished_soft_bias_suppresses_premature_commit"
                            if unfinished_strength > 0.0
                            else "no_unfinished_commit_suppression",
                            "same_draft_already_committed_suppression"
                            if same_draft_already_committed
                            else "draft_changed_since_last_commit",
                        ],
                        consequence_estimates=consequence_estimates,
                        params=commit_params,
                    )
                )
        if correction_pressure > 0.0 and latest_expected_token:
            # Output mismatch is a local draft-editing problem. We create text
            # editor candidates from generic mismatch evidence instead of
            # hard-coding any sequence answer; normal action competition still
            # decides whether AP rereads, waits, recalls, or actually revises.
            reread_drive = (
                0.38
                + correction_pressure * 0.54
                + min(0.22, dissonance * 0.16 + mismatch_ratio * 0.12)
                + uncertainty * 0.08
            )
            replace_drive = (
                0.28
                + correction_pressure * 0.44
                + (0.44 if reread_after_mismatch else 0.0)
                + min(0.26, dissonance * 0.12 + mismatch_ratio * 0.10 + max(0.0, 1.0 - correctness) * 0.06)
            )
            mismatch_span_start = max(0, int(draft_context.get("latest_mismatch_index", -1) or -1))
            if mismatch_span_start < 0:
                mismatch_span_start = max(0, visible_length - 1)
            mismatch_token = str(draft_context.get("latest_mismatch_token", "") or latest_mismatch_token)
            output_replace_params = {
                "span": [mismatch_span_start, mismatch_span_start + 1],
                "new_text": latest_expected_token,
                "expected_token": latest_expected_token,
                "candidate_token": latest_expected_token,
                "from_token": mismatch_token,
                "conflict_index": mismatch_span_start,
                "reason": "real_virtual_conflict_revision",
            }
            output_parameter_estimate = self._parameter_memory.estimate(action_id="action::text_replace", proposed_params=output_replace_params)
            replace_drive += float(output_parameter_estimate.get("drive_bias", 0.0) or 0.0)
            if reread_after_mismatch:
                # Once AP has looked back at the doubtful draft, continuing to
                # reread should fatigue relative to revision. This preserves
                # humanlike hesitation while avoiding an endless "just looking"
                # loop when the expected replacement is clear.
                reread_drive -= 0.18
            candidates.append(
                self._candidate(
                    action_id="action::text_reread",
                    actuator_id=action_actuator_id("action::text_reread", "actuator::text_editor"),
                    base_drive=reread_drive,
                    predicted={
                        "reward": (0.14 + correction_pressure * 0.18 + dissonance * 0.04) * reward_gain_multiplier,
                        "punishment": max(0.02, 0.07 - correction_pressure * 0.02),
                        "expectation": expectation * 0.34 + correction_pressure * 0.22,
                        "pressure": max(0.0, pressure * 0.42 - correction_pressure * 0.08),
                        "correctness": correctness * 0.34 + correction_pressure * 0.24,
                        "confidence": 0.42 + correction_pressure * 0.26 + min(0.12, dissonance * 0.06),
                    },
                    notes=[
                        "output_side_revision_pressure",
                        "humanlike_reread_before_revise",
                        f"correction_pressure={_round4(correction_pressure)}",
                        f"latest_expected_token={latest_expected_token}",
                    ],
                    consequence_estimates=consequence_estimates,
                    params={
                        "reason": "write_mismatch",
                        "expected_token": latest_expected_token,
                    },
                )
            )
            candidates.append(
                self._candidate(
                    action_id="action::text_replace",
                    actuator_id=action_actuator_id("action::text_replace", "actuator::text_editor"),
                    base_drive=replace_drive,
                    predicted={
                        "reward": (0.16 + correction_pressure * 0.24 + (0.06 if reread_after_mismatch else 0.0)) * reward_gain_multiplier,
                        "punishment": max(0.035, 0.10 - correction_pressure * 0.025),
                        "expectation": expectation * 0.30 + correction_pressure * 0.26,
                        "pressure": max(0.0, pressure * 0.48 - correction_pressure * 0.05),
                        "correctness": correctness * 0.28 + correction_pressure * 0.36 + (0.08 if reread_after_mismatch else 0.0),
                        "confidence": 0.40 + correction_pressure * 0.24 + (0.14 if reread_after_mismatch else 0.0),
                    },
                    notes=[
                        "output_side_revision_pressure",
                        "revise_unresolved_write_mismatch",
                        f"correction_pressure={_round4(correction_pressure)}",
                        f"reread_after_mismatch={reread_after_mismatch}",
                        f"latest_expected_token={latest_expected_token}",
                    ]
                    + (
                        [
                            "parameter_memory_bias",
                            f"parameter_drive_bias={_round4(float(output_parameter_estimate.get('drive_bias', 0.0) or 0.0))}",
                            f"parameter_similarity={_round4(float(output_parameter_estimate.get('similarity', 0.0) or 0.0))}",
                        ]
                        if float(output_parameter_estimate.get("support", 0.0) or 0.0) > 0.0
                        else []
                    ),
                    consequence_estimates=consequence_estimates,
                    params=output_replace_params,
                )
            )
        if revision_opportunities:
            visible_length = int(draft_context.get("visible_length", 0) or 0)
            last_reread_age = int(draft_context.get("last_reread_age", 9999) or 9999)
            last_reread_tick = int(draft_context.get("last_reread_tick", -1) or -1)
            has_recent_reread = last_reread_age <= 4 and last_reread_tick >= 0
            top_opportunity = revision_opportunities[0]
            top_support = _clamp(float(top_opportunity.get("support", 0.0) or 0.0), 0.0, 1.2)
            top_kind = str(top_opportunity.get("conflict_kind", "") or top_opportunity.get("operation", "") or "")
            reread_drive = (
                0.30
                + top_support * 0.26
                + min(0.20, len(revision_opportunities) * 0.05)
                + dissonance * 0.10
                + uncertainty * 0.08
                - (0.18 if has_recent_reread else 0.0)
            )
            if visible_length > 0 and not has_recent_reread:
                candidates.append(
                    self._candidate(
                        action_id="action::text_reread",
                        actuator_id=action_actuator_id("action::text_reread", "actuator::text_editor"),
                        base_drive=max(0.0, reread_drive),
                        predicted={
                            "reward": (0.10 + top_support * 0.08 + min(0.08, len(revision_opportunities) * 0.02)) * reward_gain_multiplier,
                            "punishment": max(0.018, 0.055 - top_support * 0.012),
                            "expectation": expectation * 0.28 + top_support * 0.16,
                            "pressure": max(0.0, pressure * 0.34 - top_support * 0.03),
                            "correctness": correctness * 0.28 + top_support * 0.16,
                            "confidence": 0.34 + top_support * 0.18,
                        },
                        notes=[
                            "text_revision_opportunity_review",
                            "humanlike_reread_before_multi_edit",
                            f"opportunity_kind={top_kind}",
                            f"opportunity_count={len(revision_opportunities)}",
                            f"top_support={_round4(top_support)}",
                        ],
                        consequence_estimates=consequence_estimates,
                        params={"span": [0, visible_length], "reason": "text_revision_opportunity_review"},
                    )
                )
            if has_recent_reread:
                for opportunity in revision_opportunities[:4]:
                    operation = str(opportunity.get("operation", "") or "")
                    candidate_text = str(opportunity.get("candidate_text", "") or "")
                    from_text = str(opportunity.get("from_text", "") or "")
                    support = _clamp(float(opportunity.get("support", 0.0) or 0.0), 0.0, 1.2)
                    span = self._text_span(opportunity.get("span"))
                    cursor = int(opportunity.get("cursor", span[0]) or 0)
                    conflict_kind = str(opportunity.get("conflict_kind", operation) or operation)
                    if operation == "insert" and candidate_text:
                        params = {
                            "cursor": max(0, min(visible_length, cursor)),
                            "token": candidate_text,
                            "expected_token": candidate_text,
                            "candidate_token": candidate_text,
                            "parameter_kind": "text_insert",
                            "reason": f"text_revision_opportunity::{conflict_kind}",
                        }
                        parameter_estimate = self._parameter_memory.estimate(action_id="action::text_insert", proposed_params=params)
                        drive = 0.36 + support * 0.46 + dissonance * 0.10 + float(parameter_estimate.get("drive_bias", 0.0) or 0.0)
                        candidates.append(
                            self._candidate(
                                action_id="action::text_insert",
                                actuator_id=action_actuator_id("action::text_insert", "actuator::text_editor"),
                                base_drive=max(0.0, drive),
                                predicted={
                                    "reward": (0.12 + support * 0.14) * reward_gain_multiplier,
                                    "punishment": max(0.035, pressure * 0.04 + ambiguity_pause * 0.02),
                                    "expectation": expectation * 0.22 + support * 0.20,
                                    "pressure": max(0.0, pressure * 0.36 - support * 0.04),
                                    "correctness": correctness * 0.24 + support * 0.26,
                                    "confidence": 0.38 + support * 0.24,
                                },
                                notes=self._revision_opportunity_notes(opportunity, parameter_estimate, "insert"),
                                consequence_estimates=consequence_estimates,
                                params=params,
                            )
                        )
                    elif operation == "delete":
                        params = {
                            "span": list(span),
                            "from_token": from_text,
                            "parameter_kind": "text_delete",
                            "reason": f"text_revision_opportunity::{conflict_kind}",
                        }
                        parameter_estimate = self._parameter_memory.estimate(action_id="action::text_delete", proposed_params=params)
                        drive = 0.36 + support * 0.48 + cleanup_pressure * 0.10 + dissonance * 0.08 + float(parameter_estimate.get("drive_bias", 0.0) or 0.0)
                        candidates.append(
                            self._candidate(
                                action_id="action::text_delete",
                                actuator_id=action_actuator_id("action::text_delete", "actuator::text_editor"),
                                base_drive=max(0.0, drive),
                                predicted={
                                    "reward": (0.12 + support * 0.15 + cleanup_pressure * 0.05) * reward_gain_multiplier,
                                    "punishment": max(0.035, pressure * 0.04),
                                    "expectation": expectation * 0.18 + support * 0.18,
                                    "pressure": max(0.0, pressure * 0.34 - support * 0.04),
                                    "correctness": correctness * 0.24 + support * 0.28,
                                    "confidence": 0.38 + support * 0.24,
                                },
                                notes=self._revision_opportunity_notes(opportunity, parameter_estimate, "delete"),
                                consequence_estimates=consequence_estimates,
                                params=params,
                            )
                        )
                    elif operation == "replace" and candidate_text:
                        params = {
                            "span": list(span),
                            "new_text": candidate_text,
                            "expected_token": candidate_text,
                            "candidate_token": candidate_text,
                            "from_token": from_text,
                            "conflict_index": int(span[0]),
                            "parameter_kind": "text_replace",
                            "reason": f"text_revision_opportunity::{conflict_kind}",
                        }
                        parameter_estimate = self._parameter_memory.estimate(action_id="action::text_replace", proposed_params=params)
                        drive = 0.34 + support * 0.48 + dissonance * 0.10 + float(parameter_estimate.get("drive_bias", 0.0) or 0.0)
                        candidates.append(
                            self._candidate(
                                action_id="action::text_replace",
                                actuator_id=action_actuator_id("action::text_replace", "actuator::text_editor"),
                                base_drive=max(0.0, drive),
                                predicted={
                                    "reward": (0.12 + support * 0.16) * reward_gain_multiplier,
                                    "punishment": max(0.04, pressure * 0.045 + ambiguity_pause * 0.02),
                                    "expectation": expectation * 0.20 + support * 0.20,
                                    "pressure": max(0.0, pressure * 0.36 - support * 0.035),
                                    "correctness": correctness * 0.24 + support * 0.28,
                                    "confidence": 0.38 + support * 0.24,
                                },
                                notes=self._revision_opportunity_notes(opportunity, parameter_estimate, "replace"),
                                consequence_estimates=consequence_estimates,
                                params=params,
                            )
                        )
        candidates.append(
            self._candidate(
                action_id="action::replay_recent_context",
                actuator_id=action_actuator_id("action::replay_recent_context", "actuator::memory_recall"),
                base_drive=replay_base_drive + boredom * 0.08 + unfinished_strength * 0.10,
                predicted={
                    "reward": (0.16 + time_conf * 0.24 + correction_pressure * 0.22) * reward_gain_multiplier,
                    "punishment": max(0.0, 0.09 - time_conf * 0.04 - correction_pressure * 0.03),
                    "expectation": expectation * 0.58,
                    "pressure": max(0.0, pressure * 0.72 - time_conf * 0.12),
                    "correctness": correctness * 0.44 + time_conf * 0.24,
                    "confidence": 0.26 + time_conf * self.confidence_gain,
                },
                notes=[
                    "temporal_replay",
                    "memory_only_continuation",
                    f"expectation_gap={_round4(expectation_gap)}",
                    f"output_mismatch_pressure={_round4(correction_pressure)}",
                    f"boredom={_round4(boredom)}",
                    f"unfinished_strength={_round4(unfinished_strength)}",
                ],
                consequence_estimates=consequence_estimates,
            )
        )
        if time_conf > 0.0 or dominant_time_peak:
            candidates.append(
                self._candidate(
                    action_id="action::recall_by_timefelt",
                    actuator_id=action_actuator_id("action::recall_by_timefelt", "actuator::memory_recall"),
                    base_drive=0.12 + time_conf * 0.54 + rhythm_expect * 0.12 + max(0.0, 1.0 - grasp) * 0.08,
                    predicted={
                        "reward": (0.11 + time_conf * 0.26 + rhythm_expect * 0.06) * reward_gain_multiplier,
                        "punishment": max(0.015, 0.08 - time_conf * 0.04),
                        "expectation": max(expectation * 0.35, rhythm_expect * 0.52),
                        "pressure": max(0.0, pressure * 0.36 - time_conf * 0.08),
                        "correctness": correctness * 0.28 + time_conf * 0.26,
                        "confidence": 0.22 + time_conf * self.confidence_gain + rhythm_expect * 0.10,
                    },
                    notes=[
                        "timefelt_recall",
                        "temporal_interval_memory_query",
                        f"time_confidence={_round4(time_conf)}",
                        f"target_delta_t={_round4(float(target_delta_t or 0.0))}",
                    ],
                    consequence_estimates=consequence_estimates,
                    params={
                        "delta_t": target_delta_t,
                        "sigma": time_sigma,
                        "confidence": _round4(time_conf),
                    },
                )
            )
        if expectation_anchors:
            anchor_drive = 0.18 + top_anchor_level * 0.44 + expectation_anchor_level * 0.14 + pressure_anchor_level * 0.18 + expectation_gap * 0.12
            candidates.append(
                self._candidate(
                    action_id="action::recall_by_expectation",
                    actuator_id=action_actuator_id("action::recall_by_expectation", "actuator::memory_recall"),
                    base_drive=anchor_drive,
                    predicted={
                        "reward": (0.13 + expectation_anchor_level * 0.20 + pressure_anchor_level * 0.08) * reward_gain_multiplier,
                        "punishment": max(0.02, pressure_anchor_level * 0.08),
                        "expectation": max(expectation, top_anchor_level * 0.82),
                        "pressure": max(0.0, pressure * 0.62 + pressure_anchor_level * 0.28),
                        "correctness": correctness * 0.34 + top_anchor_level * 0.22,
                        "confidence": 0.28 + top_anchor_level * self.confidence_gain + min(0.18, len(expectation_anchors) * 0.03),
                    },
                    notes=[
                        "b_anchor_recall",
                        "expectation_pressure_self_query",
                        f"top_anchor_level={_round4(top_anchor_level)}",
                        f"pressure_anchor_level={_round4(pressure_anchor_level)}",
                    ],
                    consequence_estimates=consequence_estimates,
                    params={
                        "b_anchor": str(expectation_anchors[0].get("anchor_id", "") or ""),
                        "source_memory_id": str(expectation_anchors[0].get("source_memory_id", "") or ""),
                    },
                    supporting_anchors=expectation_anchors[:4],
                )
            )
        evidence_gap = self._evidence_gap_context(
            state_snapshot_items=state_snapshot_items,
            expected_text=expected_text,
            draft_context=draft_context,
            uncertainty=uncertainty,
            dissonance=dissonance,
            pressure=pressure,
            ambiguity_pause=ambiguity_pause,
            revision_opportunities=revision_opportunities,
        )
        if evidence_gap.get("available"):
            gap_strength = float(evidence_gap.get("strength", 0.0) or 0.0)
            missing_visual = float(evidence_gap.get("missing_visual", 0.0) or 0.0)
            missing_audio = float(evidence_gap.get("missing_audio", 0.0) or 0.0)
            conflict_strength = float(evidence_gap.get("conflict_strength", 0.0) or 0.0)
            low_grasp = float(evidence_gap.get("low_grasp", 0.0) or 0.0)
            candidates.append(
                self._candidate(
                    action_id="action::llm_think",
                    actuator_id=action_actuator_id("action::llm_think", "actuator::llm_call"),
                    base_drive=max(
                        0.0,
                        0.20
                        + gap_strength * 0.62
                        + conflict_strength * 0.22
                        + low_grasp * 0.16
                        + pressure * 0.06
                        - grasp * 0.08,
                    ),
                    predicted={
                        "reward": (0.08 + gap_strength * 0.16 + conflict_strength * 0.05) * reward_gain_multiplier,
                        "punishment": max(0.035, 0.08 + pressure * 0.025),
                        "expectation": max(expectation * 0.22, gap_strength * 0.20),
                        "pressure": max(0.0, pressure * 0.52 + gap_strength * 0.08),
                        "correctness": correctness * 0.22 + low_grasp * 0.20,
                        "confidence": 0.26 + gap_strength * 0.18 + conflict_strength * 0.08,
                    },
                    notes=[
                        "uncertainty_evidence_gap_probe",
                        "request_more_evidence_as_generic_llm_think",
                        "soft_competing_action_not_forced_rule",
                        f"gap_strength={_round4(gap_strength)}",
                        f"missing_visual={_round4(missing_visual)}",
                        f"missing_audio={_round4(missing_audio)}",
                        f"conflict_strength={_round4(conflict_strength)}",
                        f"low_grasp={_round4(low_grasp)}",
                    ],
                    consequence_estimates=consequence_estimates,
                    params={
                        "prompt_context": "need_more_evidence",
                        "reason": "uncertainty_evidence_gap",
                        "missing_modalities": list(evidence_gap.get("missing_modalities", []) or [])[:4],
                        "candidate_conflicts": list(evidence_gap.get("conflict_labels", []) or [])[:6],
                        "visible_text": str(draft_context.get("visible_text", "") or "")[:80],
                    },
                )
            )
            if missing_visual > 0.0:
                candidates.append(
                    self._candidate(
                        action_id="action::scan_visual_field",
                        actuator_id=action_actuator_id("action::scan_visual_field", "actuator::visual_gaze_center"),
                        base_drive=max(0.0, 0.18 + gap_strength * 0.28 + missing_visual * 0.36 + uncertainty * 0.08),
                        predicted={
                            "reward": (0.08 + missing_visual * 0.12 + gap_strength * 0.04) * reward_gain_multiplier,
                            "punishment": 0.035 + pressure * 0.012,
                            "expectation": max(expectation * 0.16, missing_visual * 0.20),
                            "pressure": max(0.0, pressure * 0.32 + gap_strength * 0.04),
                            "correctness": correctness * 0.14 + missing_visual * 0.18,
                            "confidence": 0.24 + missing_visual * 0.18,
                        },
                        notes=[
                            "uncertainty_visual_resample",
                            "missing_visual_evidence",
                            "scan_is_soft_sampling_action",
                            f"gap_strength={_round4(gap_strength)}",
                        ],
                        consequence_estimates=consequence_estimates,
                        params={"pattern": "uncertain_scene_resample", "reason": "missing_or_ambiguous_visual_evidence"},
                    )
                )
                candidates.append(
                    self._candidate(
                        action_id="action::widen_visual_focus",
                        actuator_id=action_actuator_id("action::widen_visual_focus", "actuator::visual_focus_scale"),
                        base_drive=max(0.0, 0.16 + missing_visual * 0.32 + ambiguity_pause * 0.12),
                        predicted={
                            "reward": (0.07 + missing_visual * 0.10) * reward_gain_multiplier,
                            "punishment": 0.03 + pressure * 0.01,
                            "expectation": max(expectation * 0.15, missing_visual * 0.18),
                            "pressure": max(0.0, pressure * 0.30 + ambiguity_pause * 0.03),
                            "correctness": correctness * 0.12 + missing_visual * 0.16,
                            "confidence": 0.22 + missing_visual * 0.14,
                        },
                        notes=[
                            "uncertainty_visual_widen",
                            "peripheral_or_missing_visual_evidence",
                        ],
                        consequence_estimates=consequence_estimates,
                        params={"scale": 1.18, "reason": "widen_for_uncertain_visual_evidence"},
                    )
                )
            if missing_audio > 0.0:
                candidates.append(
                    self._candidate(
                        action_id="action::widen_audio_band",
                        actuator_id=action_actuator_id("action::widen_audio_band", "actuator::auditory_band_width"),
                        base_drive=max(0.0, 0.17 + gap_strength * 0.26 + missing_audio * 0.38 + uncertainty * 0.07),
                        predicted={
                            "reward": (0.08 + missing_audio * 0.12 + gap_strength * 0.04) * reward_gain_multiplier,
                            "punishment": 0.035 + pressure * 0.012,
                            "expectation": max(expectation * 0.16, missing_audio * 0.20),
                            "pressure": max(0.0, pressure * 0.32 + gap_strength * 0.04),
                            "correctness": correctness * 0.14 + missing_audio * 0.18,
                            "confidence": 0.24 + missing_audio * 0.18,
                        },
                        notes=[
                            "uncertainty_audio_resample",
                            "missing_audio_evidence",
                            "audio_sampling_action_not_answer_hint",
                            f"gap_strength={_round4(gap_strength)}",
                        ],
                        consequence_estimates=consequence_estimates,
                        params={"width_hz": 3200, "reason": "missing_or_ambiguous_audio_evidence"},
                    )
                )
        if visual_target.get("available"):
            target_score = float(visual_target.get("score", 0.0) or 0.0)
            target_gain = float(visual_target.get("focus_gain", 0.0) or 0.0)
            target_precision = float(visual_target.get("focus_precision", 0.0) or 0.0)
            target_distance = float(visual_target.get("distance", 0.0) or 0.0)
            peripheral_need = float(visual_target.get("peripheral_need", 0.0) or 0.0)
            target_label = str(visual_target.get("sa_label", "") or "")
            target_fatigue = float(visual_target.get("target_fatigue", 0.0) or 0.0)
            gaze_params = {
                "x": _round4(float(visual_target.get("x", 0.5) or 0.5)),
                "y": _round4(float(visual_target.get("y", 0.5) or 0.5)),
                "target": target_label,
                "gaze_target_key": str(visual_target.get("gaze_target_key", "") or target_label),
                "bbox_norm": list(visual_target.get("bbox_norm", []) or []),
                "reason": str(visual_target.get("reason", "") or "visual_attention_target"),
                "score_components": dict(visual_target.get("score_components", {}) or {}),
            }
            parameter_estimate = self._parameter_memory.estimate(
                action_id="action::move_gaze_to",
                proposed_params=gaze_params,
                current_gaze={
                    "center_x": _clamp(float(visual_target.get("current_gaze_x", 0.5) or 0.5), 0.0, 1.0),
                    "center_y": _clamp(float(visual_target.get("current_gaze_y", 0.5) or 0.5), 0.0, 1.0),
                },
            )
            parameter_drive_bias = float(parameter_estimate.get("drive_bias", 0.0) or 0.0)
            parameter_pressure_bias = float(parameter_estimate.get("pressure_bias", 0.0) or 0.0)
            if float(parameter_estimate.get("support", 0.0) or 0.0) > 0.0:
                gaze_params["learned_parameter_hint"] = dict(parameter_estimate)
            if target_distance > 0.045 or peripheral_need > 0.18:
                # This is the visual analogue of turning the eyes toward what the
                # cognitive field says matters. The target is derived from live SA
                # energy/attention, not from a fixed scan script.
                candidates.append(
                    self._candidate(
                        action_id="action::move_gaze_to",
                        actuator_id=action_actuator_id("action::move_gaze_to", "actuator::visual_gaze_center"),
                        base_drive=0.20 + target_score * 0.50 + peripheral_need * 0.22 + target_distance * 0.08 + parameter_drive_bias,
                        predicted={
                            "reward": (0.10 + target_score * 0.12 + peripheral_need * 0.06) * reward_gain_multiplier,
                            "punishment": max(0.018, 0.055 - target_score * 0.018),
                            "expectation": max(expectation * 0.22, target_score * 0.36),
                            "pressure": max(0.0, pressure * 0.32 + peripheral_need * 0.05 - target_score * 0.03 + parameter_pressure_bias),
                            "correctness": correctness * 0.18 + target_score * 0.22,
                            "confidence": 0.30 + target_score * 0.26 + peripheral_need * 0.10,
                        },
                        notes=[
                            "cognition_driven_visual_gaze",
                            "target_from_state_field_and_attention",
                            f"target={target_label}",
                            f"target_score={_round4(target_score)}",
                            f"target_fatigue={_round4(target_fatigue)}",
                            f"peripheral_need={_round4(peripheral_need)}",
                            f"distance={_round4(target_distance)}",
                        ]
                        + (
                            [
                                "parameter_memory_bias",
                                f"parameter_drive_bias={_round4(parameter_drive_bias)}",
                                f"parameter_similarity={_round4(float(parameter_estimate.get('similarity', 0.0) or 0.0))}",
                            ]
                            if float(parameter_estimate.get("support", 0.0) or 0.0) > 0.0
                            else []
                        ),
                        consequence_estimates=consequence_estimates,
                        params=gaze_params,
                    )
                )
            if target_gain >= 0.42 and target_score >= 0.18:
                candidates.append(
                    self._candidate(
                        action_id="action::hold_gaze",
                        actuator_id=action_actuator_id("action::hold_gaze", "actuator::visual_gaze_center"),
                        base_drive=max(0.0, 0.12 + target_score * 0.26 + target_gain * 0.14 + target_precision * 0.08 - target_fatigue * 0.22),
                        predicted={
                            "reward": (0.08 + target_score * 0.08 + target_precision * 0.05) * reward_gain_multiplier,
                            "punishment": 0.026,
                            "expectation": max(expectation * 0.18, target_score * 0.24),
                            "pressure": max(0.0, pressure * 0.22 - target_precision * 0.04),
                            "correctness": correctness * 0.16 + target_precision * 0.16,
                            "confidence": 0.28 + target_gain * 0.16 + target_score * 0.16,
                        },
                        notes=[
                            "visual_target_already_near_fovea",
                            "hold_to_continue_sampling",
                            f"target={target_label}",
                            f"focus_gain={_round4(target_gain)}",
                            f"target_fatigue={_round4(target_fatigue)}",
                        ],
                        consequence_estimates=consequence_estimates,
                        params={"target": target_label, "reason": "continue_visual_sampling", "bbox_norm": list(visual_target.get("bbox_norm", []) or [])},
                    )
                )
            if target_score >= 0.20 and target_precision < 0.86:
                candidates.append(
                    self._candidate(
                        action_id="action::zoom_visual_focus",
                        actuator_id=action_actuator_id("action::zoom_visual_focus", "actuator::visual_focus_scale"),
                        base_drive=max(0.0, 0.14 + target_score * 0.34 + max(0.0, 1.0 - target_precision) * 0.18 + uncertainty * 0.06 - target_fatigue * 0.10),
                        predicted={
                            "reward": (0.08 + target_score * 0.08 + max(0.0, 1.0 - target_precision) * 0.04) * reward_gain_multiplier,
                            "punishment": 0.032 + max(0.0, pressure - target_score) * 0.018,
                            "expectation": max(expectation * 0.16, target_score * 0.22),
                            "pressure": max(0.0, pressure * 0.26 + uncertainty * 0.03),
                            "correctness": correctness * 0.15 + target_score * 0.12,
                            "confidence": 0.26 + target_score * 0.16 + max(0.0, 1.0 - target_precision) * 0.08,
                        },
                        notes=[
                            "visual_detail_sampling_pressure",
                            "foveated_resolution_action",
                            f"target={target_label}",
                            f"focus_precision={_round4(target_precision)}",
                            f"target_fatigue={_round4(target_fatigue)}",
                        ],
                        consequence_estimates=consequence_estimates,
                        params={"scale": 0.68, "target": target_label, "reason": "increase_visual_detail", "bbox_norm": list(visual_target.get("bbox_norm", []) or [])},
                    )
                )
            for alternative in list(visual_target.get("alternatives", []) or [])[:3]:
                if not isinstance(alternative, dict):
                    continue
                alt_score = float(alternative.get("score", 0.0) or 0.0)
                alt_need = float(alternative.get("peripheral_need", 0.0) or 0.0)
                alt_distance = float(alternative.get("distance", 0.0) or 0.0)
                alt_fatigue = float(alternative.get("target_fatigue", 0.0) or 0.0)
                # Alternatives are allowed into competition only when there is
                # real exploratory pressure: the current best is fatigued, or
                # the alternative is close enough in score and still unclear.
                if not (target_fatigue >= 0.12 or (alt_score >= max(0.14, target_score - 0.18) and alt_need > 0.16)):
                    continue
                alt_label = str(alternative.get("sa_label", "") or "")
                if not alt_label or alt_label == target_label:
                    continue
                alt_params = {
                    "x": _round4(float(alternative.get("x", 0.5) or 0.5)),
                    "y": _round4(float(alternative.get("y", 0.5) or 0.5)),
                    "target": alt_label,
                    "gaze_target_key": str(alternative.get("gaze_target_key", "") or alt_label),
                    "bbox_norm": list(alternative.get("bbox_norm", []) or []),
                    "reason": "visual_exploration_after_target_fatigue",
                    "score_components": dict(alternative.get("score_components", {}) or {}),
                }
                alt_parameter_estimate = self._parameter_memory.estimate(
                    action_id="action::move_gaze_to",
                    proposed_params=alt_params,
                    current_gaze={
                        "center_x": _clamp(float(alternative.get("current_gaze_x", 0.5) or 0.5), 0.0, 1.0),
                        "center_y": _clamp(float(alternative.get("current_gaze_y", 0.5) or 0.5), 0.0, 1.0),
                    },
                )
                alt_parameter_drive_bias = float(alt_parameter_estimate.get("drive_bias", 0.0) or 0.0)
                if float(alt_parameter_estimate.get("support", 0.0) or 0.0) > 0.0:
                    alt_params["learned_parameter_hint"] = dict(alt_parameter_estimate)
                candidates.append(
                    self._candidate(
                        action_id="action::move_gaze_to",
                        actuator_id=action_actuator_id("action::move_gaze_to", "actuator::visual_gaze_center"),
                        base_drive=max(
                            0.0,
                            0.12
                            + alt_score * 0.34
                            + alt_need * 0.24
                            + alt_distance * 0.06
                            + target_fatigue * 0.18
                            - alt_fatigue * 0.20
                            + alt_parameter_drive_bias,
                        ),
                        predicted={
                            "reward": (0.08 + alt_score * 0.10 + alt_need * 0.05) * reward_gain_multiplier,
                            "punishment": max(0.022, 0.06 - alt_score * 0.012),
                            "expectation": max(expectation * 0.16, alt_score * 0.24),
                            "pressure": max(0.0, pressure * 0.24 + alt_need * 0.04),
                            "correctness": correctness * 0.12 + alt_score * 0.16,
                            "confidence": 0.22 + alt_score * 0.18 + alt_need * 0.08,
                        },
                        notes=[
                            "visual_exploration_alternative",
                            "alternative_target_from_fatigue_or_unclear_periphery",
                            f"target={alt_label}",
                            f"alt_score={_round4(alt_score)}",
                            f"best_target_fatigue={_round4(target_fatigue)}",
                            f"alt_target_fatigue={_round4(alt_fatigue)}",
                            f"peripheral_need={_round4(alt_need)}",
                        ]
                        + (
                            [
                                "parameter_memory_bias",
                                f"parameter_drive_bias={_round4(alt_parameter_drive_bias)}",
                                f"parameter_similarity={_round4(float(alt_parameter_estimate.get('similarity', 0.0) or 0.0))}",
                            ]
                            if float(alt_parameter_estimate.get("support", 0.0) or 0.0) > 0.0
                            else []
                        ),
                        consequence_estimates=consequence_estimates,
                        params=alt_params,
                    )
                )
        episode_risk = self._episode_replay_risk(
            action_consequence_trace=action_consequence_trace or {},
            pressure_anchor_level=pressure_anchor_level,
            pressure=pressure,
            expectation_gap=expectation_gap,
        )
        if pressure > 0.0 or pressure_anchor_level > 0.0 or episode_risk["risk"] > 0.0 or expectation_gap > 0.0:
            candidates.append(
                self._candidate(
                    action_id="action::replay_episode",
                    actuator_id=action_actuator_id("action::replay_episode", "actuator::memory_recall"),
                    base_drive=0.16
                    + pressure * 0.24
                    + pressure_anchor_level * 0.42
                    + expectation_gap * 0.16
                    + float(episode_risk.get("risk", 0.0) or 0.0) * 0.24,
                    predicted={
                        "reward": (0.10 + pressure_anchor_level * 0.08 + float(episode_risk.get("support", 0.0) or 0.0) * 0.06) * reward_gain_multiplier,
                        "punishment": max(0.04, pressure_anchor_level * 0.10 + float(episode_risk.get("punishment", 0.0) or 0.0) * 0.16),
                        "expectation": expectation * 0.28,
                        "pressure": max(pressure * 0.72, pressure_anchor_level * 0.62, float(episode_risk.get("risk", 0.0) or 0.0) * 0.58),
                        "correctness": correctness * 0.22 + pressure_anchor_level * 0.10,
                        "confidence": 0.24 + pressure_anchor_level * self.confidence_gain + float(episode_risk.get("support", 0.0) or 0.0) * 0.12,
                    },
                    notes=[
                        "episode_replay_before_risky_action",
                        "pressure_consequence_memory_query",
                        f"pressure_anchor_level={_round4(pressure_anchor_level)}",
                        f"episode_risk={_round4(float(episode_risk.get('risk', 0.0) or 0.0))}",
                    ],
                    consequence_estimates=consequence_estimates,
                    params={
                        "source_memory_id": str(episode_risk.get("source_memory_id", "") or ""),
                        "risk": _round4(float(episode_risk.get("risk", 0.0) or 0.0)),
                    },
                    supporting_anchors=[
                        anchor
                        for anchor in expectation_anchors[:4]
                        if str(anchor.get("anchor_type", "") or "") == "pressure"
                    ],
                )
            )
        candidates.append(
            self._candidate(
                action_id="action::stabilize_prediction",
                actuator_id=action_actuator_id("action::stabilize_prediction", "actuator::legacy_internal"),
                base_drive=0.10 + max(0.0, predicted_mass - 2) * 0.04 + expectation * 0.18 + pressure * 0.16 + expectation_gap * 0.1,
                predicted={
                    "reward": (0.12 + expectation * 0.18 + alignment_score * 0.08) * reward_gain_multiplier,
                    "punishment": max(0.0, 0.11 - correctness * 0.05),
                    "expectation": expectation * 0.74,
                    "pressure": pressure * 0.84,
                    "correctness": correctness * 0.64,
                    "confidence": 0.24 + correctness * self.confidence_gain,
                },
                notes=[
                    "prediction_binding",
                    "future_consequence_estimate",
                    f"expectation_gap={_round4(expectation_gap)}",
                ],
                consequence_estimates=consequence_estimates,
            )
        )
        candidates.append(
            self._candidate(
                action_id="action::wait",
                actuator_id=action_actuator_id("action::wait", "actuator::timing"),
                base_drive=self.wait_base_drive
                + max(0.0, 0.14 - focusable_count * 0.02)
                + uncertainty * 0.22
                + rhythm_expect * 0.18
                + ambiguity_pause * 0.22
                + cleanup_pressure * 0.10
                + max(0.0, pressure - correctness * 0.45) * 0.12
                + pressure_anchor_level * 0.16
                + max(0.0, fulfillment - 0.45) * 0.06
                - boredom * 0.04,
                predicted={
                    "reward": (0.06 + uncertainty * 0.06 + rhythm_expect * 0.05 + ambiguity_pause * 0.06 + pressure_anchor_level * 0.04) * reward_gain_multiplier,
                    "punishment": 0.025 + max(0.0, pressure - pressure_anchor_level) * 0.015,
                    "expectation": expectation * 0.18,
                    "pressure": max(0.0, pressure * 0.38 - 0.06 + cleanup_pressure * 0.03),
                    "correctness": correctness * 0.18,
                    "confidence": 0.18 + uncertainty * 0.08 + rhythm_expect * 0.08 + ambiguity_pause * 0.08,
                },
                notes=[
                    "timing_wait",
                    "legal_non_action",
                    "successor_ambiguity_pause" if ambiguity_pause >= 0.32 else "ordinary_timing_pause",
                    f"uncertainty={_round4(uncertainty)}",
                    f"rhythm_expectation={_round4(rhythm_expect)}",
                    f"ambiguity_pause={_round4(ambiguity_pause)}",
                    f"cleanup_pressure={_round4(cleanup_pressure)}",
                    f"boredom={_round4(boredom)}",
                    f"fulfillment={_round4(fulfillment)}",
                ],
                consequence_estimates=consequence_estimates,
                params={"duration_ticks": 1, "rhythm_expectation": _round4(rhythm_expect), "uncertainty": _round4(uncertainty)},
            )
        )
        candidates = self._merge_memory_predicted_action_energy(
            candidates,
            state_snapshot_items,
            drive_gain=memory_action_drive_gain,
            consequence_estimates=consequence_estimates,
        )
        candidates = self._apply_visual_orientation_arbitration(candidates)
        candidates = self._suppress_unavailable_draft_actions(candidates, draft_context)
        candidates = self._apply_draft_repetition_guard(candidates, draft_context)
        candidates = self._merge_innate_action_nodes(candidates, innate_action_nodes or [], consequence_estimates=consequence_estimates)
        candidates = self._apply_innate_action_biases(candidates, innate_action_biases or [])
        candidates = self._apply_visual_orientation_arbitration(candidates)
        candidates = self._suppress_unavailable_draft_actions(candidates, draft_context)
        candidates = self._apply_draft_repetition_guard(candidates, draft_context)
        return candidates

    def _visual_gaze_target_context(self, *, state_snapshot_items: list[dict], attention_trace: dict) -> dict:
        """
        Pick a visual object worth looking at from the current cognitive field.

        This is intentionally a generic SA-energy readout, not a detector for a
        specific class or color. AP's gaze should be pulled by surprise, focus
        competition, motion, and low current clarity, the same signals a humanlike
        continuous system already uses elsewhere.
        """

        state_by_label: dict[str, dict] = {}
        for item in state_snapshot_items or []:
            if not isinstance(item, dict):
                continue
            label = str(item.get("sa_label", "") or "")
            if not label or not self._is_visual_object_row(item):
                continue
            bbox = self._bbox_norm(item)
            if len(bbox) < 4:
                continue
            state_by_label[label] = item
        if not state_by_label:
            return {"available": False, "reason": "no_visual_object_bbox"}

        attention_rows: dict[str, dict] = {}
        max_focus_score = 0.0
        selected = {str(label or "") for label in list((attention_trace or {}).get("selected_labels", []) or []) if str(label or "")}
        for idx, row in enumerate(list((attention_trace or {}).get("selected_items", []) or []) + list((attention_trace or {}).get("ranked_items", []) or [])):
            if not isinstance(row, dict):
                continue
            label = str(row.get("sa_label", "") or "")
            if not label:
                continue
            current = attention_rows.get(label, {})
            focus_score = max(float(current.get("focus_score", 0.0) or 0.0), float(row.get("focus_score", 0.0) or 0.0))
            max_focus_score = max(max_focus_score, focus_score)
            attention_rows[label] = {
                **current,
                **row,
                "focus_score": focus_score,
                "attention_rank": min(int(current.get("attention_rank", idx) or idx), idx),
                "selected_by_attention": label in selected or bool(current.get("selected_by_attention", False)),
            }

        candidates: list[dict] = []
        for label, state_row in state_by_label.items():
            meta = dict(state_row.get("anchor_meta", {}) or {})
            sampling_focus = dict(meta.get("sampling_focus", {}) or {})
            if not sampling_focus:
                sampling_focus = self._sampling_focus_from_numeric(state_row)
            bbox = self._bbox_norm(state_row)
            attention_row = dict(attention_rows.get(label, {}) or {})
            focus_score = float(attention_row.get("focus_score", 0.0) or 0.0)
            attention_norm = _clamp(focus_score / max(0.18, max_focus_score), 0.0, 1.0) if max_focus_score > 0.0 else 0.0
            selected_bonus = 0.16 if bool(attention_row.get("selected_by_attention", False)) else 0.0
            cp = float(state_row.get("cognitive_pressure", 0.0) or 0.0)
            real = float(state_row.get("real_energy", 0.0) or 0.0)
            virtual = float(state_row.get("virtual_energy", 0.0) or 0.0)
            precision = _clamp(float(sampling_focus.get("precision", 0.24) or 0.24), 0.0, 1.0)
            gain = _clamp(float(sampling_focus.get("gain", 0.0) or 0.0), 0.0, 1.0)
            distance = _clamp(float(sampling_focus.get("distance", 0.0) or 0.0), 0.0, 1.5)
            peripheral_need = _clamp((1.0 - precision) * (0.58 + min(0.42, distance)), 0.0, 1.0)
            motion = self._visual_motion_strength(state_row)
            salience = _clamp(max(real, float(meta.get("salience", 0.0) or 0.0)), 0.0, 1.4) / 1.4
            familiar_expected = bool(meta.get("familiar", False) and meta.get("expected", False))
            if familiar_expected and abs(cp) < 0.05 and motion < 0.05:
                salience *= 0.34
                peripheral_need *= 0.36
                selected_bonus *= 0.20
                attention_norm *= 0.38
            target_key = self._visual_gaze_target_key(state_row)
            fatigue = _clamp(float(self._visual_target_fatigue.get(target_key, self._visual_target_fatigue.get(label, 0.0)) or 0.0), 0.0, 1.0)
            components = {
                "attention": _round4(attention_norm),
                "selected_bonus": _round4(selected_bonus),
                "positive_pressure": _round4(_clamp(max(0.0, cp), 0.0, 1.2) / 1.2),
                "abs_pressure": _round4(_clamp(abs(cp), 0.0, 1.4) / 1.4),
                "salience": _round4(salience),
                "peripheral_need": _round4(peripheral_need),
                "motion": _round4(motion),
                "virtual_hint": _round4(_clamp(virtual, 0.0, 1.2) / 1.2),
                "target_fatigue": _round4(fatigue),
                "familiar_expected_suppression": 1.0 if familiar_expected and abs(cp) < 0.05 and motion < 0.05 else 0.0,
            }
            raw_score = (
                components["attention"] * 0.30
                + selected_bonus
                + components["positive_pressure"] * 0.25
                + components["abs_pressure"] * 0.08
                + salience * 0.15
                + peripheral_need * 0.22
                + motion * 0.10
                + components["virtual_hint"] * 0.05
            )
            # Fatigue is a soft exploration pressure. It lowers the score of a
            # target that has already been sampled clearly, but strong fresh
            # pressure or motion can still make it win again.
            score = raw_score - fatigue * (0.20 + max(0.0, precision - 0.62) * 0.20)
            if familiar_expected and abs(cp) < 0.05 and motion < 0.05:
                score *= 0.46
            candidates.append(
                {
                    "available": True,
                    "sa_label": label,
                    "x": _clamp(float(bbox[0]), 0.0, 1.0),
                    "y": _clamp(float(bbox[1]), 0.0, 1.0),
                    "bbox_norm": bbox,
                    "score": _round4(_clamp(score, 0.0, 1.0)),
                    "focus_score": _round4(focus_score),
                    "focus_gain": _round4(gain),
                    "focus_precision": _round4(precision),
                    "distance": _round4(distance),
                    "peripheral_need": _round4(peripheral_need),
                    "target_fatigue": _round4(fatigue),
                    "raw_score_before_fatigue": _round4(_clamp(raw_score, 0.0, 1.0)),
                    "current_gaze_x": _round4(float(meta.get("gaze_center_x", 0.5) or 0.5)),
                    "current_gaze_y": _round4(float(meta.get("gaze_center_y", 0.5) or 0.5)),
                    "gaze_target_key": target_key,
                    "score_components": components,
                    "reason": "visual_attention_pressure_target",
                }
            )
        if not candidates:
            return {"available": False, "reason": "no_scored_visual_target"}
        candidates = self._aggregate_visual_gaze_targets(candidates)
        candidates.sort(key=lambda row: (-float(row.get("score", 0.0) or 0.0), -float(row.get("focus_score", 0.0) or 0.0), str(row.get("gaze_target_key", "") or str(row.get("sa_label", "") or ""))))
        best = dict(candidates[0])
        best["alternatives"] = candidates[1:4]
        return best

    def _aggregate_visual_gaze_targets(self, candidates: list[dict]) -> list[dict]:
        """
        Collapse visual SA channels into executable gaze targets.

        The state pool keeps object, color, shape, spatial and motion rows as
        first-class SA because AP should recognize the whole field. The eye,
        however, can only move toward a place. This aggregation happens only at
        the actuator-parameter layer: feature rows still contribute pressure,
        motion and salience evidence, but they no longer multiply one object
        into several competing "places to look at".
        """

        grouped: dict[str, list[dict]] = defaultdict(list)
        for row in candidates or []:
            if not isinstance(row, dict):
                continue
            key = str(row.get("gaze_target_key", "") or row.get("sa_label", "") or "")
            if not key:
                continue
            grouped[key].append(row)

        merged: list[dict] = []
        for key, rows in grouped.items():
            ordered = sorted(
                rows,
                key=lambda item: (
                    0 if str(item.get("sa_label", "") or "").startswith("vision_obj::") else 1,
                    -float(item.get("score", 0.0) or 0.0),
                    str(item.get("sa_label", "") or ""),
                ),
            )
            display_row = dict(ordered[0])
            strongest = max(rows, key=lambda item: float(item.get("score", 0.0) or 0.0))
            component_keys = {
                comp_key
                for row in rows
                for comp_key in dict(row.get("score_components", {}) or {}).keys()
            }
            components = {
                comp_key: _round4(
                    max(
                        float(dict(row.get("score_components", {}) or {}).get(comp_key, 0.0) or 0.0)
                        for row in rows
                    )
                )
                for comp_key in component_keys
            }
            merged_score = max(float(row.get("score", 0.0) or 0.0) for row in rows)
            merged_raw = max(float(row.get("raw_score_before_fatigue", 0.0) or 0.0) for row in rows)
            display_row.update(
                {
                    "available": True,
                    "sa_label": str(display_row.get("sa_label", "") or key),
                    "gaze_target_key": key,
                    "score": _round4(_clamp(merged_score, 0.0, 1.0)),
                    "raw_score_before_fatigue": _round4(_clamp(merged_raw, 0.0, 1.0)),
                    "focus_score": _round4(max(float(row.get("focus_score", 0.0) or 0.0) for row in rows)),
                    "focus_gain": _round4(max(float(row.get("focus_gain", 0.0) or 0.0) for row in rows)),
                    "focus_precision": _round4(max(float(row.get("focus_precision", 0.0) or 0.0) for row in rows)),
                    "peripheral_need": _round4(max(float(row.get("peripheral_need", 0.0) or 0.0) for row in rows)),
                    "target_fatigue": _round4(max(float(row.get("target_fatigue", 0.0) or 0.0) for row in rows)),
                    "score_components": components,
                    "source_labels": sorted({str(row.get("sa_label", "") or "") for row in rows if str(row.get("sa_label", "") or "")}),
                    "merged_source_count": len(rows),
                    "strongest_source_label": str(strongest.get("sa_label", "") or ""),
                    "reason": "visual_attention_pressure_target_group",
                }
            )
            merged.append(display_row)
        return merged

    def _visual_gaze_target_key(self, item: dict) -> str:
        """
        Resolve the spatial object that a gaze action would actually look at.

        The state field keeps visual objects and their shape/color/motion
        channels as first-class SA. For eye movement, however, those channels
        refer to the same place in the world. Fatigue and parameter learning
        therefore use this object/space key so one already-sampled object cannot
        bypass exploration pressure by reappearing as a different feature
        channel label.
        """

        label = str((item or {}).get("sa_label", "") or "")
        meta = dict((item or {}).get("anchor_meta", {}) or {})
        for key in ("object_anchor_id", "parent_object_label"):
            value = str(meta.get(key, "") or "")
            if value:
                return value
        if str((item or {}).get("family", "") or "") == "vision_object":
            return label
        bbox = self._bbox_norm(item)
        if len(bbox) >= 2:
            return self._visual_spatial_target_key(bbox)
        return label

    def _visual_spatial_target_key(self, bbox_norm: list[float]) -> str:
        x = float((bbox_norm or [0.5])[0] if bbox_norm else 0.5)
        y = float((bbox_norm or [0.5, 0.5])[1] if len(bbox_norm or []) > 1 else 0.5)
        if x < 0.34:
            x_bucket = "left"
        elif x > 0.66:
            x_bucket = "right"
        else:
            x_bucket = "center"
        if y < 0.34:
            y_bucket = "upper"
        elif y > 0.66:
            y_bucket = "lower"
        else:
            y_bucket = "mid"
        return f"vision_obj::{x_bucket}_{y_bucket}"

    def _is_visual_object_row(self, item: dict) -> bool:
        label = str((item or {}).get("sa_label", "") or "")
        family = str((item or {}).get("family", "") or "")
        source_type = str((item or {}).get("source_type", "") or "")
        return family == "vision_object" or label.startswith("vision_obj::") or (family.startswith("vision") and source_type == "vision_numeric")

    def _bbox_norm(self, item: dict) -> list[float]:
        meta = dict((item or {}).get("anchor_meta", {}) or {})
        bbox = list(meta.get("bbox_norm", []) or [])
        if len(bbox) >= 4:
            return [_round4(_clamp(float(value or 0.0), 0.0, 1.0)) for value in bbox[:4]]
        numeric = dict((item or {}).get("numeric_features", {}) or {})
        spatial = list(numeric.get("vision.spatial", []) or [])
        if len(spatial) >= 4:
            return [_round4(_clamp(float(value or 0.0), 0.0, 1.0)) for value in spatial[:4]]
        return []

    def _sampling_focus_from_numeric(self, item: dict) -> dict:
        numeric = dict((item or {}).get("numeric_features", {}) or {})
        values = list(numeric.get("vision.focus", []) or [])
        if len(values) < 2:
            return {}
        return {
            "precision": _clamp(float(values[0] or 0.0), 0.0, 1.0),
            "distance": _clamp(float(values[1] or 0.0), 0.0, 1.5),
            "gain": _clamp(max(0.0, float(values[0] or 0.0) - 0.24) / 0.76, 0.0, 1.0),
        }

    def _visual_motion_strength(self, item: dict) -> float:
        numeric = dict((item or {}).get("numeric_features", {}) or {})
        for key in ("vision.motion_vector", "vision.motion"):
            values = numeric.get(key, [])
            if isinstance(values, (list, tuple)) and values:
                try:
                    return _clamp(sum(abs(float(value or 0.0)) for value in values[:3]), 0.0, 1.0)
                except (TypeError, ValueError):
                    return 0.0
        return 0.0

    def _output_mismatch_context(self, state_snapshot_items: list[dict]) -> dict:
        mismatch_rows = []
        revision_rows = []
        reread_rows = []
        for item in state_snapshot_items:
            if not isinstance(item, dict):
                continue
            label = str(item.get("sa_label", "") or "")
            source_type = str(item.get("source_type", "") or "")
            family = str(item.get("family", "") or "")
            anchor_meta = dict(item.get("anchor_meta", {}) or {})
            event_type = str(anchor_meta.get("event_type", "") or "")
            if source_type != "text_action" and family != "text_action" and not label.startswith("text_action::"):
                continue
            if label.startswith("text_action::revise::") or event_type in {"revise", "write_revision"}:
                revision_rows.append(item)
                continue
            if label.startswith("text_action::reread::") or event_type == "reread":
                reread_rows.append(item)
                continue
            token = str(anchor_meta.get("token", "") or "")
            expected = str(anchor_meta.get("expected_token", "") or "")
            token_mismatch = bool(token and expected and token != expected)
            if label.startswith("text_action::write::") and (event_type == "write_mismatch" or token_mismatch):
                mismatch_rows.append(item)
        unresolved_count = max(0, len(mismatch_rows) - len(revision_rows))
        latest_mismatch = self._latest_text_action_row(mismatch_rows)
        latest_reread = self._latest_text_action_row(reread_rows)
        mismatch_meta = dict((latest_mismatch or {}).get("anchor_meta", {}) or {})
        reread_meta = dict((latest_reread or {}).get("anchor_meta", {}) or {})
        latest_mismatch_tick = int(mismatch_meta.get("tick_index", -1) or -1) if latest_mismatch else -1
        latest_reread_tick = int(reread_meta.get("tick_index", -1) or -1) if latest_reread else -1
        return {
            "mismatch_count": len(mismatch_rows),
            "revision_count": len(revision_rows),
            "reread_count": len(reread_rows),
            "unresolved_count": unresolved_count,
            "correction_pressure": _clamp(unresolved_count / 2.0, 0.0, 1.0),
            "latest_mismatch_token": str(mismatch_meta.get("token", "") or ""),
            "latest_expected_token": str(mismatch_meta.get("expected_token", "") or ""),
            "latest_mismatch_tick": latest_mismatch_tick,
            "latest_reread_tick": latest_reread_tick,
            "reread_after_mismatch": latest_mismatch_tick >= 0 and latest_reread_tick >= latest_mismatch_tick,
        }

    def _latest_text_action_row(self, rows: list[dict]) -> dict:
        if not rows:
            return {}
        def _tick(row: dict) -> int:
            meta = dict((row or {}).get("anchor_meta", {}) or {})
            try:
                return int(meta.get("tick_index", -1) or -1)
            except (TypeError, ValueError):
                return -1

        return dict(max([row for row in rows if isinstance(row, dict)], key=_tick, default={}))

    def _expected_text_context(self, *, fast_cn: list[dict], slow_cn: list[dict]) -> dict:
        scores: dict[str, float] = defaultdict(float)
        sources: dict[str, set[str]] = defaultdict(set)
        # Slow focus predictions are the inner draft thread, so they get a tiny
        # preference, but not enough to override a clearly stronger fast-field
        # prediction. The result is a distribution summary, not a hard decision.
        for source, branches, source_weight in (("slow_cn", slow_cn, 1.08), ("fast_cn", fast_cn, 1.0)):
            for branch in branches or []:
                for item in list((branch or {}).get("predicted_items", []) or []):
                    label = str((item or {}).get("sa_label", "") or "")
                    if not label.startswith("text::"):
                        continue
                    token = label.split("::", 1)[-1]
                    if not token:
                        continue
                    strength = _clamp(float((item or {}).get("virtual_energy", 0.2) or 0.2) * source_weight, 0.0, 1.2)
                    if strength <= 0.0:
                        continue
                    scores[token] += strength
                    sources[token].add(source)
        ranked = sorted(scores.items(), key=lambda item: (-float(item[1]), item[0]))
        if not ranked:
            return {
                "token": "",
                "strength": 0.0,
                "source": "",
                "alternatives": [],
                "candidate_count": 0,
                "top_share": 0.0,
                "dominance_gap": 0.0,
                "dominance_ratio": 0.0,
                "ambiguity": 0.0,
                "decisive": False,
            }
        total = max(1e-9, sum(score for _, score in ranked))
        top_token, top_score = ranked[0]
        second_score = ranked[1][1] if len(ranked) > 1 else 0.0
        top_share = _clamp(top_score / total, 0.0, 1.0)
        dominance_gap = _clamp(top_score - second_score, 0.0, 1.0)
        dominance_ratio = top_score / max(0.001, second_score)
        candidate_count = len(ranked)
        ambiguity = _clamp(
            (1.0 - top_share) * 0.55
            + max(0.0, 0.22 - dominance_gap) * 1.35
            + min(0.18, max(0, candidate_count - 2) * 0.035),
            0.0,
            1.0,
        )
        decisive = bool(candidate_count == 1 or top_share >= 0.55 or dominance_gap >= 0.22 or dominance_ratio >= 1.75)
        return {
            "token": top_token,
            "strength": _round4(_clamp(top_score, 0.0, 1.2)),
            "source": "+".join(sorted(sources[top_token])),
            "alternatives": [
                {
                    "token": token,
                    "score": _round4(score),
                    "share": _round4(score / total),
                    "sources": sorted(sources[token]),
                }
                for token, score in ranked[:8]
            ],
            "candidate_count": int(candidate_count),
            "top_share": _round4(top_share),
            "dominance_gap": _round4(dominance_gap),
            "dominance_ratio": _round4(min(99.0, dominance_ratio)),
            "ambiguity": _round4(ambiguity),
            "decisive": decisive,
        }

    def expected_text_context(self, *, fast_cn: list[dict], slow_cn: list[dict]) -> dict:
        """
        Read-only public bridge for runtime feeling channels.

        TaskFeeling reuses the same successor clarity that action planning uses,
        avoiding a second, conflicting definition of "can continue writing".
        """

        return self._expected_text_context(fast_cn=fast_cn, slow_cn=slow_cn)

    def draft_writing_context(self, state_snapshot_items: list[dict], *, current_tick: int) -> dict:
        """
        Read-only bridge for teaching scaffolds and reports.

        Skill scaffolds must see the same draft surface that the planner sees.
        Exposing this compact context prevents a second, subtly different
        "draft state" parser from growing outside the action system.
        """

        return self._draft_writing_context(state_snapshot_items, current_tick=int(current_tick))

    def _draft_writing_context(self, state_snapshot_items: list[dict], *, current_tick: int) -> dict:
        draft_state = {}
        inactive_draft_state = {}
        event_rows = []
        for item in state_snapshot_items or []:
            if not isinstance(item, dict):
                continue
            label = str(item.get("sa_label", "") or "")
            source_type = str(item.get("source_type", "") or "")
            family = str(item.get("family", "") or "")
            if source_type != "text_action" and family != "text_action" and not label.startswith("text_action::"):
                continue
            meta = dict(item.get("anchor_meta", {}) or {})
            if label == "text_action::draft_state" or str(meta.get("schema_id", "") or "") == "text_draft_state/v1":
                is_active = bool(meta.get("active_draft_surface", label == "text_action::draft_state"))
                if is_active:
                    draft_state = meta
                elif not inactive_draft_state:
                    inactive_draft_state = meta
                continue
            event_rows.append(meta)
        if not draft_state and inactive_draft_state:
            draft_state = inactive_draft_state
        if draft_state:
            ctx = dict(draft_state)
        else:
            # Fallback keeps planner robust when tests or older traces provide
            # text_action events without the compact draft_state item.
            visible_tokens = [
                str(row.get("token", "") or "")
                for row in event_rows
                if str(row.get("event_type", "") or "") in {"insert", "write_revision", "write", "write_mismatch"}
                and str(row.get("token", "") or "")
            ]
            ctx = {
                "visible_text": "".join(visible_tokens),
                "visible_tokens": visible_tokens,
                "visible_length": len(visible_tokens),
                "last_visible_token": visible_tokens[-1] if visible_tokens else "",
                "trailing_repeat_token": visible_tokens[-1] if visible_tokens else "",
                "trailing_repeat_count": self._trailing_repeat_count(visible_tokens),
                "duplicate_ratio": self._duplicate_ratio(visible_tokens),
                "insert_count": sum(1 for row in event_rows if str(row.get("event_type", "") or "") == "insert"),
                "external_write_count": sum(1 for row in event_rows if str(row.get("source", "") or "") == "external_text"),
                "mismatch_count": sum(1 for row in event_rows if self._is_text_mismatch_meta(row)),
                "revision_count": sum(1 for row in event_rows if str(row.get("event_type", "") or "") in {"revise", "replace", "write_revision"}),
                "reread_count": sum(1 for row in event_rows if str(row.get("event_type", "") or "") == "reread"),
                "delete_count": sum(1 for row in event_rows if str(row.get("event_type", "") or "") == "delete"),
                "replace_count": sum(1 for row in event_rows if str(row.get("event_type", "") or "") == "replace"),
                "commit_count": sum(1 for row in event_rows if str(row.get("event_type", "") or "") == "commit"),
                "last_event_type": str((event_rows[-1] if event_rows else {}).get("event_type", "") or ""),
                "last_event_tick": self._latest_meta_tick(event_rows),
                "last_insert_tick": self._latest_meta_tick([row for row in event_rows if str(row.get("event_type", "") or "") == "insert"]),
                "last_reread_tick": self._latest_meta_tick([row for row in event_rows if str(row.get("event_type", "") or "") == "reread"]),
                "last_delete_tick": self._latest_meta_tick([row for row in event_rows if str(row.get("event_type", "") or "") == "delete"]),
                "last_replace_tick": self._latest_meta_tick([row for row in event_rows if str(row.get("event_type", "") or "") == "replace"]),
                "last_revision_tick": self._latest_meta_tick([row for row in event_rows if str(row.get("event_type", "") or "") in {"revise", "replace", "write_revision"}]),
                "last_mutation_tick": self._latest_meta_tick([row for row in event_rows if str(row.get("event_type", "") or "") in {"insert", "delete", "replace", "revise", "write_revision"}]),
                "last_commit_tick": self._latest_meta_tick([row for row in event_rows if str(row.get("event_type", "") or "") == "commit"]),
            }
        if "visible_tokens" not in ctx:
            ctx["visible_tokens"] = [token for token in list(ctx.get("visible_tokens", []) or []) if str(token or "")]
        if "trailing_repeat_count" not in ctx:
            ctx["trailing_repeat_count"] = self._trailing_repeat_count([str(token or "") for token in list(ctx.get("visible_tokens", []) or [])])
        if "duplicate_ratio" not in ctx:
            ctx["duplicate_ratio"] = self._duplicate_ratio([str(token or "") for token in list(ctx.get("visible_tokens", []) or [])])
        if "trailing_repeat_token" not in ctx:
            tokens = [str(token or "") for token in list(ctx.get("visible_tokens", []) or []) if str(token or "")]
            ctx["trailing_repeat_token"] = tokens[-1] if tokens else str(ctx.get("last_visible_token", "") or "")
        for key in (
            "last_event_tick",
            "last_insert_tick",
            "last_reread_tick",
            "last_delete_tick",
            "last_replace_tick",
            "last_revision_tick",
            "last_mutation_tick",
            "last_commit_tick",
        ):
            try:
                tick = int(ctx.get(key, -1) or -1)
            except (TypeError, ValueError):
                tick = -1
            ctx[key] = tick
            age_key = key.replace("_tick", "_age")
            ctx[age_key] = 9999 if tick < 0 else max(0, int(current_tick) - tick)
        if "latest_mismatch_index" not in ctx or int(ctx.get("latest_mismatch_index", -1) or -1) < 0:
            latest_index, latest_row = self._latest_text_mismatch_meta(event_rows)
            ctx["latest_mismatch_index"] = latest_index
            ctx["latest_mismatch_tick"] = self._latest_meta_tick([latest_row]) if latest_row else -1
            ctx["latest_mismatch_token"] = str((latest_row or {}).get("token", "") or "")
            ctx["latest_mismatch_expected_token"] = str((latest_row or {}).get("expected_token", "") or "")
        insert_count = int(ctx.get("insert_count", 0) or 0)
        revision_count = int(ctx.get("revision_count", 0) or 0)
        ctx["has_internal_draft"] = bool(insert_count > 0 or revision_count > 0)
        ctx["has_any_visible_text"] = bool(int(ctx.get("visible_length", 0) or 0) > 0)
        ctx["can_reread"] = bool(str(ctx.get("visible_text", "") or "") and int(ctx.get("visible_length", 0) or 0) > 0)
        return ctx

    def _is_text_mismatch_meta(self, row: dict) -> bool:
        event_type = str((row or {}).get("event_type", "") or "")
        token = str((row or {}).get("token", "") or "")
        expected = str((row or {}).get("expected_token", "") or "")
        return bool(event_type == "write_mismatch" or (token and expected and token != expected))

    def _latest_text_mismatch_meta(self, rows: list[dict]) -> tuple[int, dict]:
        for index in range(len(rows) - 1, -1, -1):
            row = dict(rows[index] or {})
            if self._is_text_mismatch_meta(row):
                return index, row
        return -1, {}

    def _text_span(self, span) -> tuple[int, int]:
        if isinstance(span, dict):
            start = span.get("start", span.get("from", span.get("begin", 0)))
            end = span.get("end", span.get("to", span.get("stop", None)))
            try:
                left = int(start or 0)
                right = int(end if end is not None else left + 1)
            except (TypeError, ValueError):
                return (0, 1)
            return (max(0, left), max(max(0, left), right))
        if isinstance(span, (list, tuple)) and len(span) >= 2:
            try:
                left = int(span[0])
                right = int(span[1])
            except (TypeError, ValueError):
                return (0, 1)
            return (max(0, left), max(max(0, left), right))
        return (0, 1)

    def _text_revision_opportunities(self, state_snapshot_items: list[dict]) -> list[dict]:
        rows = []
        for item in state_snapshot_items or []:
            if not isinstance(item, dict):
                continue
            label = str(item.get("sa_label", "") or "")
            family = str(item.get("family", "") or "")
            source_type = str(item.get("source_type", "") or "")
            meta = dict(item.get("anchor_meta", {}) or {})
            if not (
                label.startswith("text_revision_opportunity::")
                or family == "text_revision_opportunity"
                or str(meta.get("schema_id", "") or "") == "text_revision_opportunity/v1"
            ):
                continue
            operation = str(meta.get("operation", "") or "")
            if operation not in {"insert", "delete", "replace"}:
                continue
            support = _clamp(
                max(
                    float(meta.get("support", 0.0) or 0.0),
                    float(item.get("virtual_energy", 0.0) or 0.0),
                    float(item.get("real_energy", 0.0) or 0.0),
                    float(item.get("cognitive_pressure", 0.0) or 0.0),
                ),
                0.0,
                1.2,
            )
            span = self._text_span(meta.get("span"))
            cursor = int(meta.get("cursor", span[0]) or 0)
            rows.append(
                {
                    "schema_id": "text_revision_opportunity/v1",
                    "operation": operation,
                    "conflict_kind": str(meta.get("conflict_kind", operation) or operation),
                    "span": list(span),
                    "cursor": max(0, cursor),
                    "candidate_text": str(meta.get("candidate_text", meta.get("to_text", meta.get("expected_text", ""))) or ""),
                    "from_text": str(meta.get("from_text", "") or ""),
                    "visible_text": str(meta.get("visible_text", "") or ""),
                    "support": _round4(support),
                    "source_type": source_type,
                    "sa_label": label,
                    "notes": list(meta.get("notes", []) or [])[:8],
                }
            )
        rows.sort(
            key=lambda row: (
                -float(row.get("support", 0.0) or 0.0),
                int(list(row.get("span", [0, 0]) or [0, 0])[0]),
                str(row.get("operation", "") or ""),
            )
        )
        return rows

    def _revision_opportunity_notes(self, opportunity: dict, parameter_estimate: dict, operation: str) -> list[str]:
        support = float((opportunity or {}).get("support", 0.0) or 0.0)
        notes = [
            "text_revision_opportunity_action",
            "not_spellchecker_state_field_opportunity",
            "requires_recent_reread",
            f"operation={operation}",
            f"conflict_kind={str((opportunity or {}).get('conflict_kind', '') or '')}",
            f"support={_round4(support)}",
        ]
        if float((parameter_estimate or {}).get("support", 0.0) or 0.0) > 0.0:
            notes.extend(
                [
                    "parameter_memory_bias",
                    f"parameter_drive_bias={_round4(float((parameter_estimate or {}).get('drive_bias', 0.0) or 0.0))}",
                    f"parameter_similarity={_round4(float((parameter_estimate or {}).get('similarity', 0.0) or 0.0))}",
                ]
            )
        return notes

    def _draft_self_evaluation(
        self,
        draft_context: dict,
        expected_text: dict,
        *,
        correctness: float,
        grasp: float,
        pressure: float,
        dissonance: float,
        uncertainty: float,
    ) -> dict:
        """
        Low-level draft appraisal for action competition.

        This is deliberately not a semantic quality judge. It only converts
        white-box state facts (successor distribution, recent reread/edit ages,
        repetition, pressure) into soft drive terms that write/wait/reread/edit
        actions can compete over.
        """

        visible_length = int((draft_context or {}).get("visible_length", 0) or 0)
        has_internal_draft = bool((draft_context or {}).get("has_internal_draft", False))
        last_insert_age = int((draft_context or {}).get("last_insert_age", 9999) or 9999)
        last_reread_age = int((draft_context or {}).get("last_reread_age", 9999) or 9999)
        last_delete_age = int((draft_context or {}).get("last_delete_age", 9999) or 9999)
        trailing_repeat_count = int((draft_context or {}).get("trailing_repeat_count", 0) or 0)
        duplicate_ratio = _clamp(float((draft_context or {}).get("duplicate_ratio", 0.0) or 0.0), 0.0, 1.0)
        top_share = _clamp(float((expected_text or {}).get("top_share", 0.0) or 0.0), 0.0, 1.0)
        dominance_gap = _clamp(float((expected_text or {}).get("dominance_gap", 0.0) or 0.0), 0.0, 1.0)
        expected_strength = _clamp(float((expected_text or {}).get("strength", 0.0) or 0.0), 0.0, 1.2)
        decisive = bool((expected_text or {}).get("decisive", False))
        candidate_count = int((expected_text or {}).get("candidate_count", 0) or 0)
        raw_ambiguity = _clamp(float((expected_text or {}).get("ambiguity", 0.0) or 0.0), 0.0, 1.0)
        no_clear_successor = bool(candidate_count <= 0 or not decisive)
        ambiguity_pause = _clamp(
            raw_ambiguity
            + (0.12 if no_clear_successor and has_internal_draft else 0.0)
            + (0.08 if last_insert_age <= 1 and not decisive else 0.0)
            + uncertainty * 0.16
            + pressure * 0.08,
            0.0,
            1.0,
        )
        cleanup_pressure = _clamp(
            max(0, trailing_repeat_count - 1) * 0.34
            + duplicate_ratio * 0.28
            + dissonance * 0.10
            - (0.14 if last_delete_age <= 2 else 0.0),
            0.0,
            1.0,
        )
        continuation_readiness = _clamp(
            expected_strength * 0.34
            + top_share * 0.34
            + dominance_gap * 0.44
            + (0.16 if decisive else 0.0)
            + (0.10 if has_internal_draft else 0.0)
            - ambiguity_pause * 0.35
            - cleanup_pressure * 0.28
            - pressure * 0.12,
            0.0,
            1.0,
        )
        recently_reviewed = last_reread_age <= 3
        satisfaction = _clamp(
            (0.16 if has_internal_draft and visible_length > 0 else 0.0)
            + (0.18 if recently_reviewed else 0.0)
            + correctness * 0.24
            + grasp * 0.20
            + max(0.0, 0.42 - ambiguity_pause) * 0.18
            - cleanup_pressure * 0.32
            - pressure * 0.16
            - dissonance * 0.12,
            0.0,
            1.0,
        )
        return {
            "schema_id": "draft_self_evaluation/v1",
            "continuation_readiness": _round4(continuation_readiness),
            "ambiguity_pause": _round4(ambiguity_pause),
            "cleanup_pressure": _round4(cleanup_pressure),
            "satisfaction": _round4(satisfaction),
            "successor_decisive": decisive,
            "candidate_count": int(candidate_count),
            "top_share": _round4(top_share),
            "dominance_gap": _round4(dominance_gap),
            "trailing_repeat_count": int(trailing_repeat_count),
            "duplicate_ratio": _round4(duplicate_ratio),
        }

    def _draft_goal_alignment(
        self,
        *,
        state_snapshot_items: list[dict],
        draft_context: dict,
        fast_cn: list[dict],
        slow_cn: list[dict],
        consequence_estimates: dict,
        outcome_estimate: dict,
    ) -> dict:
        """
        Build a soft goal / consequence view for draft closure.

        This is not a task-completion judge. It converts ordinary state-pool
        anchors, successor evidence, and action-outcome memory into short-lived
        pressure terms that text_insert / reread / revise / commit can compete
        over. The action-level habit path is deliberately capped because it is
        not yet a context-indexed habit memory.
        """

        draft = dict(draft_context or {})
        expected_text = self._expected_text_context(fast_cn=fast_cn, slow_cn=slow_cn)
        visible_tokens = [str(token or "") for token in list(draft.get("visible_tokens", []) or []) if str(token or "")]
        visible_text = str(draft.get("visible_text", "") or "")
        visible_length = int(draft.get("visible_length", len(visible_tokens)) or 0)
        last_reread_age = int(draft.get("last_reread_age", 9999) or 9999)
        trailing_repeat_count = int(draft.get("trailing_repeat_count", 0) or 0)
        duplicate_ratio = _clamp(float(draft.get("duplicate_ratio", 0.0) or 0.0), 0.0, 1.0)
        visible_lookup = set(visible_tokens)
        visible_lookup.update(f"text::{token}" for token in visible_tokens)
        if visible_text:
            visible_lookup.add(visible_text)
            visible_lookup.add(f"text::{visible_text}")

        task_anchors = []
        target_hits = []
        alignment_scores = []
        for item in state_snapshot_items or []:
            if not isinstance(item, dict):
                continue
            label = str(item.get("sa_label", "") or "")
            family = str(item.get("family", "") or "")
            source_type = str(item.get("source_type", "") or "")
            if not (
                label.startswith("task::")
                or label.startswith("intention::")
                or family in {"task", "intention"}
                or source_type in {"task_anchor", "intention_anchor"}
            ):
                continue
            meta = dict(item.get("anchor_meta", {}) or {})
            target_labels = self._draft_anchor_target_labels(item, meta)
            strictness = _clamp(float(meta.get("strictness", item.get("strictness", 0.35)) or 0.35), 0.0, 1.0)
            anchor_energy = _clamp(
                max(
                    float(item.get("real_energy", 0.0) or 0.0),
                    float(item.get("virtual_energy", 0.0) or 0.0),
                    abs(float(item.get("cognitive_pressure", 0.0) or 0.0)),
                    0.20,
                ),
                0.0,
                1.0,
            )
            hits = []
            for target in target_labels:
                raw = target.split("::", 1)[-1] if "::" in target else target
                matched = bool(
                    target in visible_lookup
                    or raw in visible_lookup
                    or (raw and visible_text and raw in visible_text)
                )
                if matched:
                    hits.append(target)
                    target_hits.append(target)
            hit_share = len(hits) / max(1, len(target_labels)) if target_labels else 0.0
            anchor_alignment = _clamp(hit_share * (0.25 + anchor_energy * 0.45 + strictness * 0.30), 0.0, 1.0)
            if target_labels:
                alignment_scores.append(anchor_alignment)
            task_anchors.append(
                {
                    "anchor_label": label,
                    "target_labels": target_labels[:8],
                    "hit_labels": hits[:8],
                    "strictness": _round4(strictness),
                    "anchor_energy": _round4(anchor_energy),
                    "alignment": _round4(anchor_alignment),
                }
            )

        max_alignment = max(alignment_scores or [0.0])
        avg_alignment = sum(alignment_scores) / max(1, len(alignment_scores)) if alignment_scores else 0.0
        goal_alignment = _clamp(max_alignment * 0.72 + avg_alignment * 0.28, 0.0, 1.0)

        expected_strength = _clamp(float(expected_text.get("strength", 0.0) or 0.0), 0.0, 1.2)
        top_share = _clamp(float(expected_text.get("top_share", 0.0) or 0.0), 0.0, 1.0)
        dominance_gap = _clamp(float(expected_text.get("dominance_gap", 0.0) or 0.0), 0.0, 1.0)
        ambiguity = _clamp(float(expected_text.get("ambiguity", 0.0) or 0.0), 0.0, 1.0)
        decisive = bool(expected_text.get("decisive", False))
        candidate_count = int(expected_text.get("candidate_count", 0) or 0)
        continuation_pressure = _clamp(
            expected_strength * 0.34
            + top_share * 0.22
            + dominance_gap * 0.34
            + (0.12 if decisive else 0.0)
            - ambiguity * 0.18,
            0.0,
            1.0,
        )
        revision_pressure = _clamp(
            max(0, trailing_repeat_count - 1) * 0.32
            + duplicate_ratio * 0.22
            + float(draft.get("mismatch_count", 0) or 0) * 0.10,
            0.0,
            1.0,
        )

        commit_estimate = dict((consequence_estimates or {}).get("action::text_commit", {}) or {})
        consequence_support = _clamp(float(commit_estimate.get("support", 0.0) or 0.0), 0.0, 1.0)
        consequence_reward = max(0.0, float(commit_estimate.get("reward", 0.0) or 0.0))
        consequence_correctness = max(0.0, float(commit_estimate.get("correctness", 0.0) or 0.0))
        consequence_punishment = max(0.0, float(commit_estimate.get("punishment", 0.0) or 0.0))
        consequence_pressure = max(0.0, float(commit_estimate.get("pressure", 0.0) or 0.0))

        outcome = dict(outcome_estimate or {})
        outcome_support = _clamp(float(outcome.get("support", 0.0) or 0.0), 0.0, 1.0)
        outcome_reward = max(0.0, float(outcome.get("reward", 0.0) or 0.0))
        outcome_correctness = max(0.0, float(outcome.get("correctness", 0.0) or 0.0))
        outcome_punishment = max(0.0, float(outcome.get("punishment", 0.0) or 0.0))
        outcome_pressure = max(0.0, float(outcome.get("pressure", 0.0) or 0.0))
        approach_bias = max(0.0, float(outcome.get("approach_bias", 0.0) or 0.0))
        avoidance_bias = max(0.0, float(outcome.get("avoidance_bias", 0.0) or 0.0))
        drive_bias = float(outcome.get("drive_bias", 0.0) or 0.0)
        event_count = int(outcome.get("event_count", 0) or 0)
        success_count = int(outcome.get("success_count", 0) or 0)
        failure_count = int(outcome.get("failure_count", 0) or 0)
        failure_streak = int(outcome.get("failure_streak", 0) or 0)

        outcome_commit_pressure = _clamp(
            consequence_support * (consequence_reward * 0.38 + consequence_correctness * 0.32)
            + outcome_support * (outcome_reward * 0.30 + outcome_correctness * 0.26 + approach_bias * 0.20 + max(0.0, drive_bias) * 0.22),
            0.0,
            1.0,
        )
        habit_gate = min(1.0, event_count / 8.0)
        habitual_commit_pressure = _clamp(
            outcome_support
            * habit_gate
            * (0.16 + max(0.0, drive_bias) * 0.34 + min(0.18, success_count * 0.018))
            - outcome_support * min(0.12, failure_count * 0.018),
            0.0,
            0.28,
        )
        risk_commit_pressure = _clamp(
            consequence_support * (consequence_punishment * 0.52 + consequence_pressure * 0.42)
            + outcome_support * (outcome_punishment * 0.42 + outcome_pressure * 0.38 + avoidance_bias * 0.28 + max(0.0, -drive_bias) * 0.36)
            + min(0.18, failure_streak * 0.05),
            0.0,
            1.0,
        )
        closure_pressure = _clamp(
            (0.15 if visible_length > 0 else 0.0)
            + (0.16 if last_reread_age <= 3 else 0.0)
            + (0.10 if visible_length > 0 and candidate_count <= 0 else 0.0)
            + goal_alignment * 0.24
            + outcome_commit_pressure * 0.16
            + habitual_commit_pressure * 0.14
            - continuation_pressure * 0.16
            - revision_pressure * 0.28
            - risk_commit_pressure * 0.18,
            0.0,
            1.0,
        )
        return {
            "schema_id": "draft_goal_alignment/v1",
            "goal_alignment": _round4(goal_alignment),
            "closure_pressure": _round4(closure_pressure),
            "continuation_pressure": _round4(continuation_pressure),
            "revision_pressure": _round4(revision_pressure),
            "habitual_commit_pressure": _round4(habitual_commit_pressure),
            "outcome_commit_pressure": _round4(outcome_commit_pressure),
            "risk_commit_pressure": _round4(risk_commit_pressure),
            "task_anchor_count": len(task_anchors),
            "task_anchors": task_anchors[:8],
            "target_label_hits": sorted(set(target_hits))[:12],
            "expected_text": dict(expected_text),
            "habit_scope": "action_level_only" if outcome_support > 0.0 else "none",
            "outcome_support": _round4(outcome_support),
            "consequence_support": _round4(consequence_support),
        }

    def _evidence_gap_context(
        self,
        *,
        state_snapshot_items: list[dict],
        expected_text: dict,
        draft_context: dict,
        uncertainty: float,
        dissonance: float,
        pressure: float,
        ambiguity_pause: float,
        revision_opportunities: list[dict],
    ) -> dict:
        """
        Detect a generic need for more evidence from the state field.

        This does not decide a task answer. It only exposes the humanlike
        feeling of "I do not have enough evidence yet" as soft action material
        so wait, reread, gaze/audio resampling, recall, commit, and LLM/tool
        requests can compete in the ordinary action field.
        """

        counts: dict[str, int] = defaultdict(int)
        missing_modalities: set[str] = set()
        conflict_labels: list[str] = []
        explicit_gap = 0.0
        conflict_strength = 0.0
        low_grasp = 0.0
        for item in state_snapshot_items or []:
            if not isinstance(item, dict):
                continue
            family = str(item.get("family", "") or "")
            source_type = str(item.get("source_type", "") or "")
            label = str(item.get("sa_label", "") or "")
            meta = dict(item.get("anchor_meta", {}) or {})
            if family:
                counts[family] += 1
            if source_type:
                counts[source_type] += 1
            schema = str(meta.get("schema_id", "") or "")
            if (
                family in {"evidence_gap", "uncertainty_evidence_gap"}
                or label.startswith("evidence_gap::")
                or schema in {"evidence_gap/v1", "uncertainty_evidence_gap/v1"}
            ):
                explicit_gap = max(
                    explicit_gap,
                    float(item.get("real_energy", 0.0) or 0.0),
                    float(item.get("virtual_energy", 0.0) or 0.0),
                    abs(float(item.get("cognitive_pressure", 0.0) or 0.0)),
                    float(meta.get("strength", 0.0) or 0.0),
                )
                for value in list(meta.get("missing_modalities", []) or []):
                    if str(value or ""):
                        missing_modalities.add(str(value or ""))
                for value in list(meta.get("conflict_labels", []) or []):
                    if str(value or ""):
                        conflict_labels.append(str(value or ""))
            if (
                family in {"evidence_conflict", "modality_conflict"}
                or label.startswith("evidence_conflict::")
                or schema in {"evidence_conflict/v1", "modality_conflict/v1"}
            ):
                conflict_strength = max(
                    conflict_strength,
                    float(item.get("real_energy", 0.0) or 0.0),
                    float(item.get("virtual_energy", 0.0) or 0.0),
                    abs(float(item.get("cognitive_pressure", 0.0) or 0.0)),
                    float(meta.get("strength", 0.0) or 0.0),
                )
                if label:
                    conflict_labels.append(label)
            if family in {"low_grasp", "cognitive_feeling"} or label.startswith("feeling::uncertainty"):
                low_grasp = max(
                    low_grasp,
                    float(item.get("real_energy", 0.0) or 0.0),
                    float(item.get("virtual_energy", 0.0) or 0.0),
                    abs(float(item.get("cognitive_pressure", 0.0) or 0.0)),
                )

        has_visual = bool(
            counts.get("vision_scene", 0) > 0
            or counts.get("vision_object", 0) > 0
            or counts.get("vision", 0) > 0
        )
        has_audio = bool(counts.get("audio_event", 0) > 0 or counts.get("audio_semantic", 0) > 0)
        if not has_visual:
            missing_modalities.add("vision")
        if not has_audio:
            missing_modalities.add("audio")

        expected_strength = _clamp(float((expected_text or {}).get("strength", 0.0) or 0.0), 0.0, 1.2)
        top_share = _clamp(float((expected_text or {}).get("top_share", 0.0) or 0.0), 0.0, 1.0)
        dominance_gap = _clamp(float((expected_text or {}).get("dominance_gap", 0.0) or 0.0), 0.0, 1.0)
        candidate_count = int((expected_text or {}).get("candidate_count", 0) or 0)
        successor_unclear = _clamp(
            float(ambiguity_pause) * 0.46
            + max(0.0, 0.54 - top_share) * 0.30
            + max(0.0, 0.20 - dominance_gap) * 0.42
            + (0.10 if candidate_count > 2 else 0.0)
            + max(0.0, 0.50 - expected_strength) * 0.12,
            0.0,
            1.0,
        )
        has_draft = bool((draft_context or {}).get("has_any_visible_text", False))
        revision_pressure = max([float(row.get("support", 0.0) or 0.0) for row in revision_opportunities or []] or [0.0])
        missing_visual = 0.0
        missing_audio = 0.0
        if "vision" in missing_modalities:
            missing_visual = max(0.0, 0.52 + float(uncertainty) * 0.24 + explicit_gap * 0.18)
        if "audio" in missing_modalities:
            missing_audio = max(0.0, 0.50 + float(uncertainty) * 0.22 + explicit_gap * 0.18)
        modality_gap = _clamp(max(missing_visual, missing_audio) * 0.42, 0.0, 1.0)
        strength = _clamp(
            explicit_gap * 0.38
            + conflict_strength * 0.32
            + successor_unclear * 0.30
            + modality_gap
            + float(uncertainty) * 0.24
            + float(dissonance) * 0.16
            + max(0.0, float(pressure) - 0.36) * 0.10
            + min(0.16, revision_pressure * 0.10)
            - (0.10 if has_draft and revision_pressure <= 0.0 and explicit_gap <= 0.0 and conflict_strength <= 0.0 else 0.0),
            0.0,
            1.0,
        )
        available = bool(strength >= 0.22 or explicit_gap >= 0.24 or conflict_strength >= 0.24)
        return {
            "schema_id": "evidence_gap_context/v1",
            "available": available,
            "strength": _round4(strength),
            "explicit_gap": _round4(explicit_gap),
            "successor_unclear": _round4(successor_unclear),
            "conflict_strength": _round4(conflict_strength),
            "low_grasp": _round4(max(low_grasp, float(uncertainty), max(0.0, 1.0 - expected_strength) * 0.34)),
            "missing_visual": _round4(missing_visual),
            "missing_audio": _round4(missing_audio),
            "missing_modalities": sorted(missing_modalities),
            "conflict_labels": sorted(set(conflict_labels))[:12],
            "policy": "soft_evidence_gap_action_material_not_answer_judge",
        }

    def _draft_satisfaction_field(
        self,
        *,
        draft_eval: dict,
        draft_goal_alignment: dict,
        correctness: float,
        grasp: float,
        pressure: float,
        dissonance: float,
        uncertainty: float,
        pressure_anchor_level: float,
        expectation_gap: float,
    ) -> dict:
        """
        Convert draft appraisal into a one-tick action field.

        The field is explanatory and short-lived. It should make commit drive
        easier to audit, but it must not lock the draft or force submission.
        """

        low_satisfaction = _clamp(float((draft_eval or {}).get("satisfaction", 0.0) or 0.0), 0.0, 1.0)
        ambiguity_pause = _clamp(float((draft_eval or {}).get("ambiguity_pause", 0.0) or 0.0), 0.0, 1.0)
        cleanup_pressure = _clamp(float((draft_eval or {}).get("cleanup_pressure", 0.0) or 0.0), 0.0, 1.0)
        continuation_pressure = _clamp(
            max(
                float((draft_eval or {}).get("continuation_readiness", 0.0) or 0.0),
                float((draft_goal_alignment or {}).get("continuation_pressure", 0.0) or 0.0),
            ),
            0.0,
            1.0,
        )
        revision_pressure = _clamp(
            max(
                cleanup_pressure,
                float((draft_goal_alignment or {}).get("revision_pressure", 0.0) or 0.0),
            ),
            0.0,
            1.0,
        )
        closure_pressure = _clamp(float((draft_goal_alignment or {}).get("closure_pressure", 0.0) or 0.0), 0.0, 1.0)
        goal_alignment = _clamp(float((draft_goal_alignment or {}).get("goal_alignment", 0.0) or 0.0), 0.0, 1.0)
        habitual_commit_pressure = _clamp(float((draft_goal_alignment or {}).get("habitual_commit_pressure", 0.0) or 0.0), 0.0, 1.0)
        outcome_commit_pressure = _clamp(float((draft_goal_alignment or {}).get("outcome_commit_pressure", 0.0) or 0.0), 0.0, 1.0)
        risk_commit_pressure = _clamp(float((draft_goal_alignment or {}).get("risk_commit_pressure", 0.0) or 0.0), 0.0, 1.0)
        pressure_cost = _clamp(float(pressure) * 0.16 + float(pressure_anchor_level) * 0.10 + float(expectation_gap) * 0.08, 0.0, 1.0)
        satisfaction = _clamp(
            low_satisfaction * 0.34
            + closure_pressure * 0.30
            + goal_alignment * 0.18
            + habitual_commit_pressure * 0.10
            + outcome_commit_pressure * 0.16
            + float(correctness) * 0.12
            + float(grasp) * 0.10
            - continuation_pressure * 0.22
            - revision_pressure * 0.30
            - risk_commit_pressure * 0.36
            - pressure_cost
            - float(dissonance) * 0.10
            - float(uncertainty) * 0.08
            - ambiguity_pause * 0.10,
            0.0,
            1.0,
        )
        return {
            "schema_id": "draft_satisfaction_field/v1",
            "satisfaction": _round4(satisfaction),
            "closure_pressure": _round4(closure_pressure),
            "continuation_pressure": _round4(continuation_pressure),
            "revision_pressure": _round4(revision_pressure),
            "habitual_commit_pressure": _round4(habitual_commit_pressure),
            "outcome_commit_pressure": _round4(outcome_commit_pressure),
            "risk_commit_pressure": _round4(risk_commit_pressure),
            "goal_alignment": _round4(goal_alignment),
            "ambiguity_pause": _round4(ambiguity_pause),
            "cleanup_pressure": _round4(cleanup_pressure),
            "pressure_cost": _round4(pressure_cost),
            "ttl_ticks": 1,
            "meaning": "short_term_action_field_not_locked_state",
        }

    def _draft_anchor_target_labels(self, item: dict, meta: dict) -> list[str]:
        labels = []
        for source in (
            (meta or {}).get("target_labels", []),
            (item or {}).get("target_labels", []),
            (meta or {}).get("targets", []),
            (item or {}).get("targets", []),
        ):
            if isinstance(source, str):
                labels.append(source)
            elif isinstance(source, (list, tuple, set)):
                labels.extend(str(value or "") for value in source)
        target_text = str((meta or {}).get("target_text", "") or (item or {}).get("target_text", "") or "")
        if target_text:
            labels.append(target_text if target_text.startswith("text::") else f"text::{target_text}")
        normalized = []
        seen = set()
        for label in labels:
            text = str(label or "").strip()
            if not text:
                continue
            if "::" not in text:
                text = f"text::{text}"
            if text in seen:
                continue
            seen.add(text)
            normalized.append(text)
        return normalized[:16]

    def _draft_task_context_signature(self, draft_goal_alignment: dict) -> str:
        anchors = []
        for row in list((draft_goal_alignment or {}).get("task_anchors", []) or []):
            if not isinstance(row, dict):
                continue
            label = str(row.get("anchor_label", "") or "")
            if label:
                anchors.append(label)
            for target in list(row.get("target_labels", []) or [])[:4]:
                clean = str(target or "")
                if clean:
                    anchors.append(clean)
        if not anchors:
            return ""
        raw = json.dumps(sorted(set(anchors))[:12], ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]

    def _trailing_repeat_count(self, tokens: list[str]) -> int:
        clean = [str(token or "") for token in tokens if str(token or "")]
        if not clean:
            return 0
        last = clean[-1]
        count = 0
        for token in reversed(clean):
            if token != last:
                break
            count += 1
        return count

    def _duplicate_ratio(self, tokens: list[str]) -> float:
        clean = [str(token or "") for token in tokens if str(token or "")]
        if not clean:
            return 0.0
        return _round4(1.0 - (len(set(clean)) / max(1, len(clean))))

    def _latest_meta_tick(self, rows: list[dict]) -> int:
        ticks = []
        for row in rows or []:
            try:
                ticks.append(int((row or {}).get("tick_index", -1) or -1))
            except (TypeError, ValueError):
                continue
        return max(ticks or [-1])

    def _suppress_unavailable_draft_actions(self, candidates: list[dict], draft_context: dict) -> list[dict]:
        if bool((draft_context or {}).get("can_reread", False)):
            return candidates
        for row in candidates or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("action_id", "") or "") != "action::text_reread":
                continue
            row["base_drive"] = _round4(min(float(row.get("base_drive", 0.0) or 0.0), 0.04))
            row["drive"] = _round4(min(float(row.get("drive", 0.0) or 0.0), 0.06))
            row.setdefault("notes", [])
            row["notes"] = list(row.get("notes", []) or []) + ["draft_reread_suppressed_no_visible_draft"]
            predicted = dict(row.get("predicted_outcome", {}) or {})
            predicted["confidence"] = _round4(min(float(predicted.get("confidence", 0.0) or 0.0), 0.12))
            row["predicted_outcome"] = predicted
        return candidates

    def _apply_draft_repetition_guard(self, candidates: list[dict], draft_context: dict) -> list[dict]:
        last_token = str((draft_context or {}).get("last_visible_token", "") or "")
        if not last_token:
            return candidates
        visible_length = int((draft_context or {}).get("visible_length", 0) or 0)
        last_reread_age = int((draft_context or {}).get("last_reread_age", 9999) or 9999)
        last_insert_age = int((draft_context or {}).get("last_insert_age", 9999) or 9999)
        should_guard = visible_length >= 3 or last_reread_age <= 2 or last_insert_age <= 1
        if not should_guard:
            return candidates
        for row in candidates or []:
            if not isinstance(row, dict):
                continue
            if str(row.get("action_id", "") or "") != "action::text_insert":
                continue
            params = dict(row.get("params", {}) or {})
            token = str(params.get("token", params.get("text", "")) or "")
            if not token or token != last_token:
                continue
            # This is a soft anti-loop pressure, not a ban on repeated text.
            # If a later memory/action pathway supplies stronger evidence, it
            # can still re-enter competition on a following tick.
            row["base_drive"] = _round4(float(row.get("base_drive", 0.0) or 0.0) * 0.42)
            row["drive"] = _round4(float(row.get("drive", 0.0) or 0.0) * 0.42)
            row.setdefault("notes", [])
            row["notes"] = list(row.get("notes", []) or []) + [
                "draft_repetition_guard",
                f"last_visible_token={last_token}",
                f"visible_length={visible_length}",
            ]
            predicted = dict(row.get("predicted_outcome", {}) or {})
            predicted["pressure"] = _round4(float(predicted.get("pressure", 0.0) or 0.0) + 0.08)
            predicted["confidence"] = _round4(max(0.0, float(predicted.get("confidence", 0.0) or 0.0) - 0.08))
            row["predicted_outcome"] = predicted
        return candidates

    def _episode_replay_risk(
        self,
        *,
        action_consequence_trace: dict,
        pressure_anchor_level: float,
        pressure: float,
        expectation_gap: float,
    ) -> dict:
        estimates = dict((action_consequence_trace or {}).get("action_estimates", {}) or {})
        best: dict = {}
        best_risk = 0.0
        for action_id, estimate in estimates.items():
            if not isinstance(estimate, dict):
                continue
            support = _clamp(float(estimate.get("support", 0.0) or 0.0), 0.0, 1.0)
            punishment = max(0.0, float(estimate.get("punishment", 0.0) or 0.0))
            est_pressure = max(0.0, float(estimate.get("pressure", 0.0) or 0.0))
            risk = support * (punishment * 0.62 + est_pressure * 0.38)
            if risk > best_risk:
                best_risk = risk
                best = dict(estimate)
                best["source_action_id"] = str(action_id or "")
        source_ids = list(best.get("source_memory_ids", []) or [])
        baseline = max(0.0, float(pressure_anchor_level) * 0.42 + float(pressure) * 0.22 + float(expectation_gap) * 0.18)
        return {
            "risk": _round4(max(best_risk, baseline)),
            "support": _round4(float(best.get("support", 0.0) or 0.0)),
            "punishment": _round4(float(best.get("punishment", 0.0) or 0.0)),
            "pressure": _round4(float(best.get("pressure", 0.0) or 0.0)),
            "source_action_id": str(best.get("source_action_id", "") or ""),
            "source_memory_id": str(source_ids[0] if source_ids else ""),
        }

    def _candidate(
        self,
        *,
        action_id: str,
        actuator_id: str,
        base_drive: float,
        predicted: dict,
        notes: list[str],
        consequence_estimates: dict | None = None,
        source: str = "analytic_planner",
        innate_nodes: list[dict] | None = None,
        params: dict | None = None,
        supporting_anchors: list[dict] | None = None,
    ) -> dict:
        estimate = dict((consequence_estimates or {}).get(str(action_id or ""), {}) or {})
        outcome_estimate = self._outcome_memory.estimate(action_id)
        predicted = self._merge_predicted_with_consequence(predicted, estimate)
        predicted = self._merge_predicted_with_outcome_memory(predicted, outcome_estimate)
        bias = float(self._drive_bias[action_id] or 0.0)
        fatigue = float(self._actuator_fatigue[actuator_id] or 0.0)
        parameter_fatigue = self._parameter_action_fatigue_estimate(action_id=action_id, actuator_id=actuator_id, params=dict(params or {}))
        feedback_modulation = self._current_feedback_modulation(action_id)
        outcome_drive_bias = float(outcome_estimate.get("drive_bias", 0.0) or 0.0) * float(outcome_estimate.get("support", 0.0) or 0.0)
        if action_id in PASSIVE_MAINTENANCE_ACTIONS and outcome_drive_bias > 0.0:
            # Outcome memory is a low-level consequence/familiarity modulator.
            # It must not become AP's main habit system; state-field Bn/C*
            # recall remains the source of content-sensitive habit. Passive
            # "keep doing this" actions therefore get weaker positive outcome
            # boost so current surprise, motion, and pressure can interrupt.
            outcome_drive_bias *= 0.38
            bias = min(bias, 0.42)
        utility = (
            float(predicted.get("reward", 0.0) or 0.0)
            + 0.45 * float(predicted.get("expectation", 0.0) or 0.0)
            + 0.35 * float(predicted.get("correctness", 0.0) or 0.0)
            - 0.95 * float(predicted.get("punishment", 0.0) or 0.0)
            - 0.55 * float(predicted.get("pressure", 0.0) or 0.0)
        )
        parameter_fatigue_scale = self._parameter_action_fatigue_drive_scale(action_id)
        drive = (base_drive + utility * 0.36 + bias * self.bias_gain + outcome_drive_bias - fatigue * 0.24 - float(parameter_fatigue.get("fatigue", 0.0) or 0.0) * parameter_fatigue_scale) * feedback_modulation
        return {
            "action_id": action_id,
            "actuator_id": actuator_id,
            "base_drive": _round4(base_drive),
            "predicted_outcome": {key: _round4(value) for key, value in predicted.items()},
            "utility": _round4(utility),
            "bias": _round4(bias),
            "outcome_drive_bias": _round4(outcome_drive_bias),
            "fatigue": _round4(fatigue),
            "parameter_action_fatigue": dict(parameter_fatigue),
            "feedback_modulation": _round4(feedback_modulation),
            "drive": _round4(_clamp(drive, 0.0, 1.8)),
            "notes": list(notes)
            + (
                [
                    "same_parameter_action_short_fatigue",
                    f"parameter_action_fatigue={_round4(float(parameter_fatigue.get('fatigue', 0.0) or 0.0))}",
                    f"parameter_action_fatigue_scale={_round4(parameter_fatigue_scale)}",
                    f"parameter_signature={str(parameter_fatigue.get('signature', '') or '')}",
                ]
                if float(parameter_fatigue.get("fatigue", 0.0) or 0.0) > 0.0
                else ["no_same_parameter_action_fatigue"]
            )
            + self._consequence_notes(estimate)
            + self._outcome_memory_notes(outcome_estimate),
            "consequence_estimate": estimate,
            "outcome_memory_estimate": outcome_estimate,
            "planner_selected": False,
            "source": source,
            "innate_nodes": list(innate_nodes or []),
            "params": dict(params or {}),
            "supporting_anchors": [dict(anchor) for anchor in list(supporting_anchors or [])],
        }

    def _merge_innate_action_nodes(self, candidates: list[dict], innate_nodes: list[dict], *, consequence_estimates: dict | None = None) -> list[dict]:
        if not innate_nodes:
            return candidates
        by_action = {str(row.get("action_id", "") or ""): row for row in candidates}
        for node in innate_nodes:
            if not isinstance(node, dict):
                continue
            action_id = str(node.get("action_id", "") or "")
            if not action_id:
                continue
            drive_bonus = float(node.get("drive", 0.0) or 0.0)
            if abs(drive_bonus) <= 0.0:
                continue
            existing = by_action.get(action_id)
            if existing is not None:
                existing["base_drive"] = _round4(float(existing.get("base_drive", 0.0) or 0.0) + drive_bonus)
                existing["drive"] = _round4(_clamp(float(existing.get("drive", 0.0) or 0.0) + drive_bonus, 0.0, 1.8))
                existing.setdefault("notes", [])
                existing["notes"] = list(existing.get("notes", []) or []) + list(node.get("notes", []) or []) + ["innate_drive_merged"]
                existing.setdefault("innate_nodes", [])
                existing["innate_nodes"] = list(existing.get("innate_nodes", []) or []) + [dict(node)]
                existing["source"] = "analytic_planner+innate_rule"
                continue
            if action_id == "action::move_gaze_to" and not self._has_absolute_gaze_params(dict(node.get("params", {}) or {})):
                # A visual surprise rule may add urgency, but a gaze movement
                # must still be parameterized by an actual visual target. If no
                # state-field target was found, creating a naked move action
                # would turn the current text/thought label into a fake eye
                # coordinate and poison parameter learning.
                continue
            meta = action_meta(action_id)
            actuator_id = str(node.get("actuator_id", "") or meta.get("actuator_id", "") or "actuator::legacy_internal")
            predicted = self._innate_predicted_outcome(node)
            candidate = self._candidate(
                action_id=action_id,
                actuator_id=actuator_id,
                base_drive=max(0.0, drive_bonus),
                predicted=predicted,
                notes=list(node.get("notes", []) or []) + ["innate_rule_candidate"],
                consequence_estimates=consequence_estimates,
                source="innate_rule",
                innate_nodes=[dict(node)],
                params=dict(node.get("params", {}) or {}),
            )
            candidates.append(candidate)
            by_action[action_id] = candidate
        return candidates

    def _apply_innate_action_biases(self, candidates: list[dict], innate_biases: list[dict]) -> list[dict]:
        if not innate_biases:
            return candidates
        by_action = {str(row.get("action_id", "") or ""): row for row in candidates}
        for bias in innate_biases:
            if not isinstance(bias, dict):
                continue
            action_id = str(bias.get("action_id", "") or "")
            if not action_id:
                continue
            drive_delta = float(bias.get("drive_delta", bias.get("drive", 0.0)) or 0.0)
            if abs(drive_delta) <= 0.00001:
                continue
            existing = by_action.get(action_id)
            if existing is not None:
                before_drive = float(existing.get("drive", 0.0) or 0.0)
                existing["base_drive"] = _round4(max(0.0, float(existing.get("base_drive", 0.0) or 0.0) + drive_delta))
                existing["drive"] = _round4(_clamp(float(existing.get("drive", 0.0) or 0.0) + drive_delta, 0.0, 1.8))
                existing.setdefault("notes", [])
                existing["notes"] = list(existing.get("notes", []) or []) + list(bias.get("notes", []) or []) + [f"innate_action_bias={_round4(drive_delta)}"]
                existing.setdefault("innate_biases", [])
                existing["innate_biases"] = list(existing.get("innate_biases", []) or []) + [dict(bias)]
                existing["source"] = str(existing.get("source", "") or "analytic_planner") + "+innate_bias"
                if before_drive >= self.selection_threshold and float(existing.get("drive", 0.0) or 0.0) < self.selection_threshold:
                    existing["notes"] = list(existing.get("notes", []) or []) + ["soft_negative_bias_below_threshold"]
                continue
            if drive_delta <= 0.0:
                # Negative innate bias only suppresses actions that are already
                # present. It does not create a ghost candidate just to suppress it.
                continue
            if action_id == "action::move_gaze_to" and not self._has_absolute_gaze_params(dict(bias.get("params", {}) or {})):
                # Positive gaze bias without a spatial target is only an
                # urgency hint. It should merge into an existing visual target,
                # not invent an unparameterized movement.
                continue
            meta = action_meta(action_id)
            candidate = self._candidate(
                action_id=action_id,
                actuator_id=str(bias.get("actuator_id", "") or meta.get("actuator_id", "") or "actuator::legacy_internal"),
                base_drive=drive_delta,
                predicted=self._innate_predicted_outcome(bias),
                notes=list(bias.get("notes", []) or []) + ["innate_bias_positive_candidate"],
                consequence_estimates={},
                source="innate_action_bias",
                innate_nodes=[],
                params=dict(bias.get("params", {}) or {}),
            )
            candidate["innate_biases"] = [dict(bias)]
            candidates.append(candidate)
            by_action[action_id] = candidate
        return candidates

    def _has_absolute_gaze_params(self, params: dict) -> bool:
        if "x" in params or "y" in params:
            return True
        return len(list((params or {}).get("bbox_norm", []) or [])) >= 2

    def _apply_visual_orientation_arbitration(self, candidates: list[dict]) -> list[dict]:
        """
        Let strong peripheral orientation pressure compete with gaze holding.

        This is a same-actuator arbitration step, not a global action cap. The
        AP field may still run memory, wait, text, and internal actions in the
        same tick. Only the single visual center lane is adjusted, because one
        pair of eyes cannot simultaneously keep staring at the old target and
        move to a new peripheral target.
        """

        rows = [dict(row) for row in list(candidates or []) if isinstance(row, dict)]
        move_rows = [
            row
            for row in rows
            if str(row.get("action_id", "") or "") == "action::move_gaze_to"
            and self._has_absolute_gaze_params(dict(row.get("params", {}) or {}))
        ]
        hold_rows = [row for row in rows if str(row.get("action_id", "") or "") == "action::hold_gaze"]
        if not move_rows or not hold_rows:
            return rows

        max_orientation_pressure = 0.0
        for row in move_rows:
            params = dict(row.get("params", {}) or {})
            components = dict(params.get("score_components", {}) or {})
            pressure = _clamp(
                float(components.get("peripheral_need", 0.0) or 0.0) * 0.38
                + float(components.get("motion", 0.0) or 0.0) * 0.24
                + float(components.get("abs_pressure", 0.0) or 0.0) * 0.20
                + float(components.get("salience", 0.0) or 0.0) * 0.18,
                0.0,
                1.0,
            )
            row["visual_orientation_pressure"] = _round4(pressure)
            if pressure >= 0.62:
                # A small generic nudge is enough to let strong anomaly beat
                # gaze-holding habit, while weak peripheral flicker remains free
                # to lose. This uses only the live candidate's score components.
                gain = min(0.16, (pressure - 0.62) * 0.42)
                row["base_drive"] = _round4(float(row.get("base_drive", 0.0) or 0.0) + gain)
                row["drive"] = _round4(_clamp(float(row.get("drive", 0.0) or 0.0) + gain, 0.0, 1.8))
                row.setdefault("notes", [])
                row["notes"] = list(row.get("notes", []) or []) + [
                    "visual_orientation_pressure_gain",
                    f"orientation_pressure={_round4(pressure)}",
                ]
            max_orientation_pressure = max(max_orientation_pressure, pressure)

        if max_orientation_pressure <= 0.0:
            return rows

        hold_discount = min(0.42, max(0.0, max_orientation_pressure - 0.48) * 0.74)
        if hold_discount <= 0.0:
            return rows

        for row in hold_rows:
            old_drive = float(row.get("drive", 0.0) or 0.0)
            old_base = float(row.get("base_drive", 0.0) or 0.0)
            row["drive"] = _round4(_clamp(old_drive - hold_discount, 0.0, 1.8))
            row["base_drive"] = _round4(max(0.0, old_base - hold_discount * 0.45))
            row["visual_orientation_hold_discount"] = _round4(hold_discount)
            row.setdefault("notes", [])
            row["notes"] = list(row.get("notes", []) or []) + [
                "visual_orientation_pressure_softens_hold_gaze",
                f"orientation_pressure={_round4(max_orientation_pressure)}",
            ]
        return rows

    def _merge_memory_predicted_action_energy(
        self,
        candidates: list[dict],
        state_snapshot_items: list[dict],
        *,
        drive_gain: float,
        consequence_estimates: dict | None = None,
    ) -> list[dict]:
        gain = max(0.0, float(drive_gain))
        if gain <= 0.0:
            return candidates
        by_action = {str(row.get("action_id", "") or ""): row for row in candidates}
        for item in state_snapshot_items or []:
            if not isinstance(item, dict):
                continue
            action_id = str(item.get("sa_label", "") or "")
            if not action_id.startswith("action::"):
                continue
            virtual_energy = max(0.0, float(item.get("virtual_energy", 0.0) or 0.0))
            if virtual_energy <= 0.0:
                continue
            drive_bonus = _clamp(virtual_energy * gain, 0.0, 0.42)
            if drive_bonus <= 0.0:
                continue
            existing = by_action.get(action_id)
            note = f"memory_predicted_action_virtual={_round4(virtual_energy)}"
            if existing is not None:
                existing["base_drive"] = _round4(float(existing.get("base_drive", 0.0) or 0.0) + drive_bonus)
                existing["drive"] = _round4(_clamp(float(existing.get("drive", 0.0) or 0.0) + drive_bonus, 0.0, 1.8))
                existing.setdefault("notes", [])
                existing["notes"] = list(existing.get("notes", []) or []) + [note, "drive_source::memory_predicted_action"]
                existing["source"] = str(existing.get("source", "") or "analytic_planner") + "+memory_predicted_action"
                continue
            meta = action_meta(action_id)
            candidate = self._candidate(
                action_id=action_id,
                actuator_id=str(meta.get("actuator_id", "") or "actuator::legacy_internal"),
                base_drive=drive_bonus,
                predicted={
                    "reward": 0.08 + drive_bonus * 0.20,
                    "punishment": 0.08,
                    "expectation": 0.18 + drive_bonus * 0.35,
                    "pressure": 0.10,
                    "correctness": 0.08,
                    "confidence": 0.22 + min(0.28, drive_bonus),
                    "memory_action_virtual_energy": virtual_energy,
                },
                notes=[note, "drive_source::memory_predicted_action"],
                consequence_estimates=consequence_estimates,
                source="memory_predicted_action",
            )
            candidates.append(candidate)
            by_action[action_id] = candidate
        return candidates

    def _innate_predicted_outcome(self, node: dict) -> dict:
        action_id = str((node or {}).get("action_id", "") or "")
        strength = _clamp(float((node or {}).get("strength", 0.0) or 0.0), 0.0, 1.0)
        meta = action_meta(action_id)
        external = is_external_action(action_id, str(meta.get("actuator_id", "") or ""))
        confidence = 0.24 + strength * 0.26
        punishment = 0.08 + (0.10 if external else 0.0)
        pressure = 0.08 + (0.16 if external else 0.0)
        reward = 0.08 + strength * 0.14
        correctness = 0.06 + strength * 0.12
        return {
            "reward": _round4(reward),
            "punishment": _round4(punishment),
            "expectation": _round4(strength * 0.32),
            "pressure": _round4(pressure),
            "correctness": _round4(correctness),
            "confidence": _round4(confidence),
            "innate_strength": _round4(strength),
        }

    def _merge_predicted_with_consequence(self, predicted: dict, estimate: dict) -> dict:
        merged = dict(predicted or {})
        support = _clamp(float((estimate or {}).get("support", 0.0) or 0.0), 0.0, 1.0)
        if support <= 0.0:
            return merged
        # Keep the current analytic prediction, but let experience move it.
        # Support-gating prevents sparse old evidence from overruling live context.
        mix = min(0.42, 0.18 + support * 0.24)
        for key in ("reward", "punishment", "correctness", "pressure", "confidence"):
            if key not in estimate:
                continue
            live = float(merged.get(key, 0.0) or 0.0)
            empirical = float(estimate.get(key, 0.0) or 0.0)
            merged[key] = _round4(live * (1.0 - mix) + empirical * mix)
        merged["experience_support"] = _round4(support)
        merged["experience_mix"] = _round4(mix)
        return merged

    def _merge_predicted_with_outcome_memory(self, predicted: dict, estimate: dict) -> dict:
        merged = dict(predicted or {})
        support = _clamp(float((estimate or {}).get("support", 0.0) or 0.0), 0.0, 1.0)
        if support <= 0.0:
            return merged
        # Long-term reward / punishment memory is an action-shaping signal.
        # It remains more conservative than immediate successor evidence.
        mix = min(0.34, 0.10 + support * 0.24)
        for key in ("reward", "punishment", "correctness", "pressure", "confidence"):
            live = float(merged.get(key, 0.0) or 0.0)
            empirical = float((estimate or {}).get(key, 0.0) or 0.0)
            merged[key] = _round4(live * (1.0 - mix) + empirical * mix)
        merged["outcome_memory_support"] = _round4(support)
        merged["outcome_memory_mix"] = _round4(mix)
        merged["outcome_memory_drive_bias"] = _round4(float((estimate or {}).get("drive_bias", 0.0) or 0.0))
        return merged

    def _consequence_notes(self, estimate: dict) -> list[str]:
        support = float((estimate or {}).get("support", 0.0) or 0.0)
        if support <= 0.0:
            return ["experience_support=0.0"]
        return [
            f"experience_support={_round4(support)}",
            f"experience_reward={_round4(float(estimate.get('reward', 0.0) or 0.0))}",
            f"experience_punishment={_round4(float(estimate.get('punishment', 0.0) or 0.0))}",
        ]

    def _outcome_memory_notes(self, estimate: dict) -> list[str]:
        support = float((estimate or {}).get("support", 0.0) or 0.0)
        if support <= 0.0:
            return ["outcome_memory_support=0.0"]
        return [
            f"outcome_memory_support={_round4(support)}",
            f"outcome_drive_bias={_round4(float(estimate.get('drive_bias', 0.0) or 0.0))}",
            f"outcome_failures={int(estimate.get('failure_count', 0) or 0)}",
        ]

    def _build_action_items(self, selected_actions: list[dict], tick_index: int) -> list[dict]:
        items = []
        for row in selected_actions:
            action_name = str(row.get("action_id", "") or "").split("::")[-1]
            items.append(
                {
                    "sa_label": f"action::{action_name}",
                    "display_text": f"行动:{action_name}",
                    "source_type": "action_selection",
                    "family": "action",
                    "real_energy": _round4(float(row.get("drive", 0.0) or 0.0)),
                    "anchor_meta": {
                        "tick_index": int(tick_index),
                        "action_id": row.get("action_id", ""),
                        "actuator_id": row.get("actuator_id", ""),
                        "base_drive": row.get("base_drive", 0.0),
                        "drive": row.get("drive", 0.0),
                        "effective_decisiveness": row.get("effective_decisiveness", 0.0),
                        "predicted_outcome": dict(row.get("predicted_outcome", {}) or {}),
                        "utility": row.get("utility", 0.0),
                        "consequence_estimate": dict(row.get("consequence_estimate", {}) or {}),
                        "outcome_memory_estimate": dict(row.get("outcome_memory_estimate", {}) or {}),
                        "source": str(row.get("source", "") or ""),
                        "innate_nodes": list(row.get("innate_nodes", []) or []),
                        "params": dict(row.get("params", {}) or {}),
                        "supporting_anchors": list(row.get("supporting_anchors", []) or []),
                    },
                }
            )
        return items

    def _active_expectation_anchors(self, expectation_anchor_trace: dict) -> list[dict]:
        anchors = [dict(anchor) for anchor in list((expectation_anchor_trace or {}).get("anchors", []) or []) if isinstance(anchor, dict)]
        anchors = [
            anchor
            for anchor in anchors
            if str(anchor.get("source_memory_id", "") or "")
            and float(anchor.get("level", 0.0) or 0.0) > 0.0
        ]
        anchors.sort(
            key=lambda anchor: (
                -float(anchor.get("level", 0.0) or 0.0),
                0 if str(anchor.get("anchor_type", "") or "") == "pressure" else 1,
                str(anchor.get("anchor_id", "") or ""),
            )
        )
        return anchors

    def build_action_items(self, selected_actions: list[dict], *, tick_index: int) -> list[dict]:
        return self._build_action_items(selected_actions, tick_index=int(tick_index))

    def _advance_tick(self, tick_index: int) -> None:
        if self._last_tick < 0:
            self._last_tick = tick_index
            self._outcome_memory.advance_tick(tick_index)
            self._parameter_memory.advance_tick(tick_index)
            return
        delta = max(1, tick_index - self._last_tick)
        self._outcome_memory.advance_tick(tick_index)
        self._parameter_memory.advance_tick(tick_index)
        for key in list(self._actuator_fatigue.keys()):
            self._actuator_fatigue[key] = _clamp(float(self._actuator_fatigue[key]) * (self.fatigue_decay**delta), 0.0, 1.0)
            if self._actuator_fatigue[key] < 0.0001:
                self._actuator_fatigue.pop(key, None)
        for key in list(self._visual_target_fatigue.keys()):
            self._visual_target_fatigue[key] = _clamp(float(self._visual_target_fatigue[key]) * (self.fatigue_decay**delta), 0.0, 1.0)
            if self._visual_target_fatigue[key] < 0.0001:
                self._visual_target_fatigue.pop(key, None)
        for key in list(self._parameter_action_fatigue.keys()):
            entry = dict(self._parameter_action_fatigue.get(key, {}) or {})
            value = _clamp(float(entry.get("fatigue", 0.0) or 0.0) * (self.fatigue_decay**delta), 0.0, 1.0)
            if value < 0.0001:
                self._parameter_action_fatigue.pop(key, None)
                continue
            entry["fatigue"] = value
            self._parameter_action_fatigue[key] = entry
        for key in list(self._feedback_modulation.keys()):
            entry = dict(self._feedback_modulation.get(key, {}) or {})
            ttl = int(entry.get("ttl", 0) or 0)
            ttl = max(0, ttl - delta)
            if ttl <= 0:
                self._feedback_modulation.pop(key, None)
                continue
            entry["ttl"] = ttl
            self._feedback_modulation[key] = entry
        self._last_tick = tick_index

    def _record_parameter_action_fatigue(
        self,
        *,
        action_id: str,
        actuator_id: str,
        params: dict,
        confidence: float,
        utility: float,
    ) -> None:
        signature = self._parameter_action_signature(action_id=action_id, actuator_id=actuator_id, params=params)
        if not signature:
            return
        existing = dict(self._parameter_action_fatigue.get(signature, {}) or {})
        # Positive, successful repetitions get the strongest short fatigue: the
        # action probably already did its job. Bad outcomes still add a smaller
        # pause so AP does not thrash the exact same failed parameter.
        if str(action_id or "") == "action::text_commit":
            utility_gain = 26.0 if float(utility) >= 0.0 else 4.8
        else:
            utility_gain = 1.25 if float(utility) >= 0.0 else 0.58
        step = _clamp(self.fatigue_step * max(0.5, float(confidence)) * utility_gain, 0.0, 1.0)
        if step <= 0.0:
            return
        self._parameter_action_fatigue[signature] = {
            "schema_id": "parameter_action_short_fatigue/v1",
            "signature": signature,
            "action_id": str(action_id or ""),
            "actuator_id": str(actuator_id or ""),
            "fatigue": _clamp(float(existing.get("fatigue", 0.0) or 0.0) + step, 0.0, 1.0),
            "params_preview": self._parameter_signature_payload(action_id=action_id, params=params),
            "policy": "same_action_same_key_params_short_fatigue_only",
        }

    def _parameter_action_fatigue_estimate(self, *, action_id: str, actuator_id: str, params: dict) -> dict:
        signature = self._parameter_action_signature(action_id=action_id, actuator_id=actuator_id, params=params)
        if not signature:
            return {"available": False, "fatigue": 0.0}
        entry = dict(self._parameter_action_fatigue.get(signature, {}) or {})
        if not entry:
            return {"available": False, "signature": signature, "fatigue": 0.0}
        return {
            "available": True,
            "signature": signature,
            "fatigue": _round4(float(entry.get("fatigue", 0.0) or 0.0)),
            "action_id": str(entry.get("action_id", "") or action_id),
            "params_preview": dict(entry.get("params_preview", {}) or {}),
        }

    def _parameter_action_signature(self, *, action_id: str, actuator_id: str, params: dict) -> str:
        action = str(action_id or "")
        actuator = str(actuator_id or "")
        if not action:
            return ""
        payload = self._parameter_signature_payload(action_id=action, params=params or {})
        if not payload:
            return ""
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
        return f"{actuator}|{action}|{digest}"

    def _parameter_signature_payload(self, *, action_id: str, params: dict) -> dict:
        action = str(action_id or "")
        data = dict(params or {})
        if action == "action::text_commit":
            text = str(data.get("draft_signature", data.get("visible_text", data.get("text", ""))) or "")
            target_channel = str(data.get("target_channel", "draft") or "draft")
            task_context = str(data.get("task_context_signature", data.get("task_id", data.get("episode_id", ""))) or "")
            # Existing experiments do not always pass a draft signature yet.
            # The channel-only fallback is intentionally weak and temporary; it
            # still keeps parameter fatigue distinct from actuator fatigue.
            return {"target_channel": target_channel, "draft_signature": text, "task_context": task_context}
        if action in {"action::text_insert", "action::text_replace", "action::text_delete", "action::text_reread"}:
            return {
                key: data.get(key)
                for key in ("token", "text", "span", "new_text", "target_channel", "cursor", "reason")
                if key in data
            }
        if action in {"action::move_gaze_to", "action::nudge_gaze", "action::scan_visual_field", "action::hold_gaze", "action::zoom_visual_focus"}:
            return {
                key: data.get(key)
                for key in ("target", "gaze_target_key", "x", "y", "dx", "dy", "bbox_norm", "scale", "pattern")
                if key in data
            }
        if action.startswith("action::recall"):
            return {
                key: data.get(key)
                for key in ("recall_mode", "horizon", "active_episode_id", "delta_t", "b_anchor")
                if key in data
            }
        return {key: data.get(key) for key in sorted(data) if key not in {"reason", "notes"}}

    def _parameter_action_fatigue_drive_scale(self, action_id: str) -> float:
        action = str(action_id or "")
        if action == "action::text_commit":
            return 5.4
        if action.startswith("action::text_"):
            return 1.15
        if action in {"action::move_gaze_to", "action::nudge_gaze", "action::hold_gaze", "action::zoom_visual_focus"}:
            return 0.62
        return 0.82

    def _parameter_events_by_action(self, parameter_events: list[dict]) -> dict[str, list[dict]]:
        rows: dict[str, list[dict]] = defaultdict(list)
        for event in parameter_events or []:
            if not isinstance(event, dict):
                continue
            action_id = str(event.get("action_id", "") or "")
            if not action_id:
                continue
            rows[action_id].append(dict(event))
        return rows

    def _update_visual_target_fatigue(self, *, selected_actions: list[dict], parameter_events: list[dict], observed_feedback: dict) -> None:
        """
        Build short-term exploration fatigue for already-clear gaze targets.

        This is not a scan script. It only reduces the chance that a recently
        clear target monopolizes the next few ticks; strong pressure, movement,
        or fresh surprise can still overcome it.
        """

        feedback_utility = (
            float((observed_feedback or {}).get("reward", 0.0) or 0.0)
            + float((observed_feedback or {}).get("correctness", 0.0) or 0.0) * 0.35
            - float((observed_feedback or {}).get("punishment", 0.0) or 0.0) * 0.65
        )
        events_by_action = self._parameter_events_by_action(parameter_events)
        for row in selected_actions or []:
            action_id = str((row or {}).get("action_id", "") or "")
            if action_id not in {"action::hold_gaze", "action::zoom_visual_focus", "action::move_gaze_to"}:
                continue
            params = dict((row or {}).get("params", {}) or {})
            target = str(params.get("gaze_target_key", "") or params.get("target", "") or "")
            if not target:
                for event in events_by_action.get(action_id, []):
                    target = str(event.get("gaze_target_key", "") or event.get("target", "") or "")
                    if target:
                        break
            if not target:
                continue
            focus_signal = 0.0
            for event in events_by_action.get(action_id, []):
                event_target = str(event.get("gaze_target_key", "") or event.get("target", "") or "")
                if event_target == target:
                    focus_signal = max(focus_signal, 1.0 - min(1.0, float(event.get("movement_distance", 0.0) or 0.0) * 2.0))
            if action_id == "hold_gaze":
                focus_signal = max(focus_signal, 0.78)
            elif action_id == "zoom_visual_focus":
                focus_signal = max(focus_signal, 0.62)
            else:
                focus_signal = max(focus_signal, 0.35)
            if feedback_utility < -0.05:
                focus_signal *= 0.45
            step = _clamp(0.08 + focus_signal * 0.18 + max(0.0, feedback_utility) * 0.04, 0.0, 0.32)
            self._visual_target_fatigue[target] = _clamp(float(self._visual_target_fatigue[target]) + step, 0.0, 1.0)

    def _current_feedback_modulation(self, action_id: str) -> float:
        entry = dict(self._feedback_modulation.get(str(action_id or ""), {}) or {})
        return _clamp(float(entry.get("modulation", 1.0) or 1.0), 0.35, 1.2)

    def _drive_snapshot(self) -> dict:
        return {
            "bias": {key: _round4(value) for key, value in self._drive_bias.items()},
            "fatigue": {key: _round4(value) for key, value in self._actuator_fatigue.items()},
            "visual_target_fatigue": {key: _round4(value) for key, value in self._visual_target_fatigue.items()},
            "parameter_action_fatigue": {
                key: {
                    **{k: v for k, v in dict(value).items() if k != "fatigue"},
                    "fatigue": _round4(float(dict(value).get("fatigue", 0.0) or 0.0)),
                }
                for key, value in self._parameter_action_fatigue.items()
            },
            "feedback_modulation": {key: dict(value) for key, value in self._feedback_modulation.items()},
            "outcome_memory": self._outcome_memory.snapshot(),
            "parameter_memory": self._parameter_memory.snapshot(),
        }

from __future__ import annotations

import gc
from heapq import nsmallest
from pathlib import Path
from time import perf_counter

from miya_psyarch.channels.cognitive_feelings.channel import CognitiveFeelingChannel
from miya_psyarch.channels.expectation_pressure import BAnchorExpectationVerifier, ExpectationPressureChannel
from miya_psyarch.channels.rhythm.channel import RhythmChannel
from miya_psyarch.channels.runtime_load import RuntimeLoadFeelingChannel
from miya_psyarch.channels.task_feeling import TaskFeelingChannel
from miya_psyarch.channels.time.channel import TimeFeelingChannel
from miya_psyarch.config.defaults import RuntimeConfig
from miya_psyarch.core.action import (
    ActionConsequenceEvaluator,
    ActionConsequencePlanner,
    ActionControlEffectRouter,
    AuditoryBandActuator,
    SafetyGate,
    TextActionActuator,
    VisualGazeActuator,
)
from miya_psyarch.core.attention.selector import AttentionSelector
from miya_psyarch.core.cognition.sa_registry import SARegistry
from miya_psyarch.core.emotion import EmotionModulator
from miya_psyarch.core.innate import InnateCodingEngine
from miya_psyarch.core.learning import InnateLearningEventRouter
from miya_psyarch.learning_events import LearningEventBuilder
from miya_psyarch.core.runtime.budget_controller import RuntimeBudgetController
from miya_psyarch.core.state_pool.state_pool import DualEnergyStatePool
from miya_psyarch.core.tuner import AdaptiveTuner
from miya_psyarch.education.intervention import EducationInterventionBuffer
from miya_psyarch.memory.short_term.echo_buffer import ShortTermEchoBuffer
from miya_psyarch.memory.short_term.focus_buffer import FocusBuffer
from miya_psyarch.memory.short_term.focus_successor_bias import FocusSuccessorBias
from miya_psyarch.memory.short_term.memory_window import ShortTermMemoryWindow
from miya_psyarch.memory.assets import MultimodalAssetStore
from miya_psyarch.memory.store.memory_store import MemoryStore
from miya_psyarch.sensors.audio import LegacyAudioBridge, NativeAudioNumericSensor
from miya_psyarch.sensors.text.sensor import TextSensor
from miya_psyarch.sensors.vision import LegacyVisionBridge, NativeVisionNumericSensor

"""
PHASE1_MINIMAL_UPGRADED:
The runtime is still compact, but it is now split into explicit stage methods
and the slow-system query is built from a focus continuation buffer instead of
only the newest selected labels.
"""


class APV21Runtime:
    def __init__(self, *, config: RuntimeConfig | None = None, innate_rules: list | None = None) -> None:
        self.config = config or RuntimeConfig()
        self.text_sensor = TextSensor(budget_limit=self.config.text_sensor.budget_limit)
        self.vision_sensor = NativeVisionNumericSensor(
            max_objects=self.config.vision_sensor.max_objects,
            max_side=self.config.vision_sensor.max_side,
            preview_side=self.config.vision_sensor.preview_side,
        )
        self.audio_sensor = NativeAudioNumericSensor(
            max_samples=self.config.audio_sensor.max_samples,
            band_count=self.config.audio_sensor.band_count,
        )
        self.asset_store = MultimodalAssetStore(
            max_assets=self.config.multimodal_assets.max_assets,
            root_dir=str(Path(self.config.multimodal_assets.asset_root_dir)),
            persist_payloads=self.config.multimodal_assets.persist_payloads,
            keep_hot_payloads=self.config.multimodal_assets.keep_hot_payloads,
        )
        self.vision_bridge = LegacyVisionBridge()
        self.audio_bridge = LegacyAudioBridge()
        self.sa_registry = SARegistry(
            dynamic_phrase_min_observations=self.config.text_sensor.dynamic_phrase_min_observations,
            dynamic_phrase_max_len=self.config.text_sensor.dynamic_phrase_max_len,
            dynamic_phrase_scan_budget=self.config.text_sensor.dynamic_phrase_scan_budget,
            dynamic_phrase_emit_budget=self.config.text_sensor.dynamic_phrase_emit_budget,
        )
        self.state_pool = DualEnergyStatePool(
            real_decay=self.config.state_pool.real_decay,
            virtual_decay=self.config.state_pool.virtual_decay,
            attention_gain_decay=self.config.state_pool.attention_gain_decay,
            fatigue_decay=self.config.state_pool.fatigue_decay,
            prune_threshold=self.config.state_pool.prune_threshold,
            query_limit=self.config.state_pool.query_limit,
            snapshot_limit=self.config.state_pool.snapshot_limit,
            memory_snapshot_limit=self.config.state_pool.memory_snapshot_limit,
            r_state_head_limit=self.config.state_pool.r_state_head_limit,
            r_state_items_per_head=self.config.state_pool.r_state_items_per_head,
            maintenance_budget=self.config.state_pool.maintenance_budget,
            recent_external_limit=self.config.state_pool.recent_external_limit,
            hot_anchor_limit=self.config.state_pool.hot_anchor_limit,
            prediction_validation_actual_limit=self.config.state_pool.prediction_validation_actual_limit,
            prediction_validation_update_limit=self.config.state_pool.prediction_validation_update_limit,
            focus_boost=self.config.state_pool.focus_boost,
            focus_fatigue_step=self.config.state_pool.focus_fatigue_step,
            prediction_fatigue_enabled=self.config.state_pool.prediction_fatigue_enabled,
            prediction_fatigue_min_mass=self.config.state_pool.prediction_fatigue_min_mass,
            prediction_fatigue_ratio=self.config.state_pool.prediction_fatigue_ratio,
            prediction_fatigue_gain=self.config.state_pool.prediction_fatigue_gain,
            prediction_fatigue_max_step=self.config.state_pool.prediction_fatigue_max_step,
            cstar_trace_top_labels=self.config.state_pool.cstar_trace_top_labels,
            bootstrap_virtual_energy=self.config.state_pool.bootstrap_virtual_energy,
        )
        self.attention = AttentionSelector(
            focus_limit=self.config.attention.focus_limit,
            pressure_gain=self.config.attention.pressure_gain,
            attention_gain_weight=self.config.attention.attention_gain_weight,
            fatigue_weight=self.config.attention.fatigue_weight,
            continuation_bias=self.config.attention.continuation_bias,
        )
        self.memory = MemoryStore(
            recall_top_k=self.config.memory.recall_top_k,
            predict_top_k=self.config.memory.predict_top_k,
            prediction_energy_scale=self.config.memory.prediction_energy_scale,
            max_snapshots_per_kind=self.config.memory.max_snapshots_per_kind,
            candidate_limit=self.config.memory.candidate_limit,
            core_item_limit=self.config.memory.core_item_limit,
            query_feature_limit=self.config.memory.query_feature_limit,
            posting_label_token_limit=self.config.memory.posting_label_token_limit,
            posting_display_token_limit=self.config.memory.posting_display_token_limit,
            posting_bigram_token_limit=self.config.memory.posting_bigram_token_limit,
            posting_sequence_token_limit=self.config.memory.posting_sequence_token_limit,
            vector_token_limit=self.config.memory.vector_token_limit,
            scoring_candidate_limit=self.config.memory.scoring_candidate_limit,
            learned_rerank_limit=self.config.memory.learned_rerank_limit,
            state_query_signature_token_limit=self.config.memory.state_query_signature_token_limit,
            numeric_enabled=self.config.memory.numeric_enabled,
            numeric_dim=self.config.memory.numeric_dim,
            numeric_candidate_limit=self.config.memory.numeric_candidate_limit,
            numeric_top_k_per_channel=self.config.memory.numeric_top_k_per_channel,
            numeric_weight=self.config.memory.numeric_weight,
            relation_enabled=self.config.memory.relation_enabled,
            relation_token_limit=self.config.memory.relation_token_limit,
            relation_event_limit=self.config.memory.relation_event_limit,
            relation_context_limit=self.config.memory.relation_context_limit,
            relation_score_weight=self.config.memory.relation_score_weight,
            relation_focus_score_weight=self.config.memory.relation_focus_score_weight,
            temporal_applicability_enabled=self.config.memory.temporal_applicability_enabled,
            temporal_tick_seconds=self.config.memory.temporal_tick_seconds,
            temporal_fatigue_window_ticks=self.config.memory.temporal_fatigue_window_ticks,
            temporal_fatigue_strength=self.config.memory.temporal_fatigue_strength,
            temporal_recent_gain_window_ticks=self.config.memory.temporal_recent_gain_window_ticks,
            temporal_recent_gain=self.config.memory.temporal_recent_gain,
            temporal_long_half_life_ticks=self.config.memory.temporal_long_half_life_ticks,
            temporal_floor=self.config.memory.temporal_floor,
            index_jobs_per_tick=self.config.memory.index_jobs_per_tick,
            ann_enabled=True,
            online_enabled=self.config.online_embedding.enabled,
            online_dim=self.config.online_embedding.dim,
            online_token_limit=self.config.online_embedding.token_limit,
            online_min_support_to_promote=self.config.online_embedding.min_support_to_promote,
            online_per_tick_update_limit=self.config.online_embedding.per_tick_update_limit,
            online_scoring_token_limit=self.config.online_embedding.scoring_token_limit,
            learned_weight=self.config.online_embedding.learned_weight,
            transition_learned_weight=self.config.online_embedding.transition_learned_weight,
        )
        self.cognitive_feelings = CognitiveFeelingChannel(
            min_activation=self.config.cognitive_feelings.min_activation,
            surprise_gain=self.config.cognitive_feelings.surprise_gain,
            coherence_gain=self.config.cognitive_feelings.coherence_gain,
            dissonance_gain=self.config.cognitive_feelings.dissonance_gain,
            correctness_gain=self.config.cognitive_feelings.correctness_gain,
            grasp_gain=self.config.cognitive_feelings.grasp_gain,
            expectation_gain=self.config.cognitive_feelings.expectation_gain,
            pressure_gain=self.config.cognitive_feelings.pressure_gain,
        )
        self.task_feeling = TaskFeelingChannel(
            min_activation=self.config.task_feeling.min_activation,
            boredom_gain=self.config.task_feeling.boredom_gain,
            fulfillment_gain=self.config.task_feeling.fulfillment_gain,
        )
        self.runtime_load_feeling = RuntimeLoadFeelingChannel(
            enabled=self.config.runtime_load_feeling.enabled,
            min_activation=self.config.runtime_load_feeling.min_activation,
            complexity_gain=self.config.runtime_load_feeling.complexity_gain,
            simplicity_gain=self.config.runtime_load_feeling.simplicity_gain,
            target_load_ratio=self.config.runtime_load_feeling.target_load_ratio,
            ideal_load_ratio=self.config.runtime_load_feeling.ideal_load_ratio,
            state_item_soft_limit=self.config.runtime_load_feeling.state_item_soft_limit,
            r_state_item_soft_limit=self.config.runtime_load_feeling.r_state_item_soft_limit,
            attention_candidate_soft_limit=self.config.runtime_load_feeling.attention_candidate_soft_limit,
            pending_index_soft_limit=self.config.runtime_load_feeling.pending_index_soft_limit,
            family_overflow_soft_limit=self.config.runtime_load_feeling.family_overflow_soft_limit,
            residual_mass_soft_limit=self.config.runtime_load_feeling.residual_mass_soft_limit,
            mismatch_weight=self.config.runtime_load_feeling.mismatch_weight,
            fatigue_decay=self.config.runtime_load_feeling.fatigue_decay,
            fatigue_step=self.config.runtime_load_feeling.fatigue_step,
            fatigue_gain=self.config.runtime_load_feeling.fatigue_gain,
            max_energy=self.config.runtime_load_feeling.max_energy,
        )
        self.runtime_budget_controller = RuntimeBudgetController(
            enabled=self.config.runtime_budget_controller.enabled,
            smoothing_alpha=self.config.runtime_budget_controller.smoothing_alpha,
            readout_min_multiplier=self.config.runtime_budget_controller.readout_min_multiplier,
            readout_max_multiplier=self.config.runtime_budget_controller.readout_max_multiplier,
            attention_candidate_min_multiplier=self.config.runtime_budget_controller.attention_candidate_min_multiplier,
            attention_candidate_max_multiplier=self.config.runtime_budget_controller.attention_candidate_max_multiplier,
            index_jobs_min_multiplier=self.config.runtime_budget_controller.index_jobs_min_multiplier,
            index_jobs_max_multiplier=self.config.runtime_budget_controller.index_jobs_max_multiplier,
            index_time_min_multiplier=self.config.runtime_budget_controller.index_time_min_multiplier,
            index_time_max_multiplier=self.config.runtime_budget_controller.index_time_max_multiplier,
            trace_detail_min_multiplier=self.config.runtime_budget_controller.trace_detail_min_multiplier,
            trace_detail_max_multiplier=self.config.runtime_budget_controller.trace_detail_max_multiplier,
            min_r_state_items_per_head=self.config.runtime_budget_controller.min_r_state_items_per_head,
            preserve_1024_query_floor=self.config.runtime_budget_controller.preserve_1024_query_floor,
            max_extra_index_jobs=self.config.runtime_budget_controller.max_extra_index_jobs,
        )
        self.time_feeling = TimeFeelingChannel(
            enabled=self.config.time_feeling.enabled,
            threshold=self.config.time_feeling.threshold,
            gain=self.config.time_feeling.gain,
            min_confidence=self.config.time_feeling.min_confidence,
            default_radius_ticks=self.config.time_feeling.default_radius_ticks,
            recall_gain=self.config.time_feeling.recall_gain,
            fatigue_decay=self.config.time_feeling.fatigue_decay,
            fatigue_step=self.config.time_feeling.fatigue_step,
            fatigue_gain=self.config.time_feeling.fatigue_gain,
            fatigue_max=self.config.time_feeling.fatigue_max,
            max_sources=self.config.time_feeling.max_sources,
        )
        self.rhythm = RhythmChannel(
            enabled=self.config.rhythm.enabled,
            window=self.config.rhythm.window,
            min_hits=self.config.rhythm.min_hits,
            min_period=self.config.rhythm.min_period,
            max_period=self.config.rhythm.max_period,
            period_sigma_scale=self.config.rhythm.period_sigma_scale,
            phase_sigma_scale=self.config.rhythm.phase_sigma_scale,
            pulse_threshold=self.config.rhythm.pulse_threshold,
            phase_threshold=self.config.rhythm.phase_threshold,
            fatigue_decay=self.config.rhythm.fatigue_decay,
            fatigue_step=self.config.rhythm.fatigue_step,
            fatigue_gain=self.config.rhythm.fatigue_gain,
            fatigue_max=self.config.rhythm.fatigue_max,
            salience_threshold=self.config.rhythm.salience_threshold,
        )
        self.expectation_pressure = ExpectationPressureChannel(
            enabled=self.config.expectation_pressure.enabled,
            min_activation=self.config.expectation_pressure.min_activation,
            expectation_decay=self.config.expectation_pressure.expectation_decay,
            pressure_decay=self.config.expectation_pressure.pressure_decay,
            satisfaction_decay=self.config.expectation_pressure.satisfaction_decay,
            expectation_gain=self.config.expectation_pressure.expectation_gain,
            pressure_gain=self.config.expectation_pressure.pressure_gain,
            satisfaction_gain=self.config.expectation_pressure.satisfaction_gain,
            residual_gain=self.config.expectation_pressure.residual_gain,
            feedback_gain=self.config.expectation_pressure.feedback_gain,
        )
        self.expectation_anchor_verifier = BAnchorExpectationVerifier(
            enabled=self.config.expectation_pressure.anchor_verifier_enabled,
            max_anchors=self.config.expectation_pressure.anchor_max_anchors,
            decay=self.config.expectation_pressure.anchor_decay,
            min_anchor_level=self.config.expectation_pressure.anchor_min_level,
            min_outcome_virtual=self.config.expectation_pressure.anchor_min_outcome_virtual,
            validation_gain=self.config.expectation_pressure.anchor_validation_gain,
            miss_gain=self.config.expectation_pressure.anchor_miss_gain,
        )
        self.emotion_modulator = EmotionModulator(
            cfs_gain=self.config.emotion.cfs_gain,
            rwd_pun_gain=self.config.emotion.rwd_pun_gain,
        )
        self.innate_engine = InnateCodingEngine(
            enabled=self.config.innate_rules.enabled,
            min_fire_strength=self.config.innate_rules.min_fire_strength,
            max_items_per_phase=self.config.innate_rules.max_items_per_phase,
            max_action_nodes_per_phase=self.config.innate_rules.max_action_nodes_per_phase,
            max_learning_events_per_phase=self.config.innate_rules.max_learning_events_per_phase,
            apply_emit_sa=self.config.innate_rules.apply_emit_sa,
            apply_action_nodes=self.config.innate_rules.apply_action_nodes,
            apply_emotion_deltas=self.config.innate_rules.apply_emotion_deltas,
            rules=innate_rules,
        )
        self.innate_learning_router = InnateLearningEventRouter()
        self.learning_event_builder = LearningEventBuilder()
        self.safety_gate = SafetyGate(
            enabled=self.config.innate_rules.safety_gate_enabled,
            veto_pressure_threshold=self.config.innate_rules.safety_veto_pressure_threshold,
            veto_cor_threshold=self.config.innate_rules.safety_veto_cor_threshold,
            review_pressure_threshold=self.config.innate_rules.safety_review_pressure_threshold,
            review_cor_threshold=self.config.innate_rules.safety_review_cor_threshold,
            min_external_confidence=self.config.innate_rules.safety_min_external_confidence,
        )
        self.adaptive_tuner = AdaptiveTuner(
            enabled=self.config.tuner.enabled,
            ema_alpha=self.config.tuner.ema_alpha,
            min_support_ticks=self.config.tuner.min_support_ticks,
            target_prediction_alignment=self.config.tuner.target_prediction_alignment,
            max_normal_pressure=self.config.tuner.max_normal_pressure,
            target_action_success=self.config.tuner.target_action_success,
            adjustment_rate=self.config.tuner.adjustment_rate,
            rollback_threshold=self.config.tuner.rollback_threshold,
        )
        self.action_planner = ActionConsequencePlanner(
            enabled=self.config.action.enabled,
            selection_threshold=self.config.action.selection_threshold,
            max_selected_actions=self.config.action.max_selected_actions,
            fatigue_decay=self.config.action.fatigue_decay,
            fatigue_step=self.config.action.fatigue_step,
            bias_learning_rate=self.config.action.bias_learning_rate,
            bias_gain=self.config.action.bias_gain,
            confidence_gain=self.config.action.confidence_gain,
            wait_base_drive=self.config.action.wait_base_drive,
            outcome_memory_enabled=self.config.action.outcome_memory_enabled,
            outcome_memory_learning_rate=self.config.action.outcome_memory_learning_rate,
            outcome_memory_decay_per_tick=self.config.action.outcome_memory_decay_per_tick,
            outcome_memory_support_scale=self.config.action.outcome_memory_support_scale,
            outcome_memory_max_drive_bias=self.config.action.outcome_memory_max_drive_bias,
        )
        self.action_consequence_evaluator = ActionConsequenceEvaluator(
            max_successor_rows=self.config.action.consequence_max_successor_rows,
            max_evidence_per_action=self.config.action.consequence_max_evidence_per_action,
            max_horizon=self.config.action.consequence_max_horizon,
            branching=self.config.action.consequence_branching,
            path_decay=self.config.action.consequence_path_decay,
        )
        self.action_control_effect_router = ActionControlEffectRouter()
        self.education_interventions = EducationInterventionBuffer()
        self.focus_buffer = FocusBuffer(
            focus_history_limit=self.config.short_term.focus_history_limit,
            recency_decay=self.config.short_term.recency_decay,
            synthetic_query_weight=self.config.short_term.synthetic_query_weight,
            replay_decay=self.config.short_term.replay_decay,
            replay_query_weight=self.config.short_term.replay_query_weight,
            max_replay_items=self.config.short_term.max_replay_items,
            episode_break_overlap=self.config.short_term.episode_break_overlap,
        )
        self.short_term_echo = ShortTermEchoBuffer(
            history_limit=self.config.short_term.echo_history_limit,
            max_age_ticks=self.config.short_term.echo_max_age_ticks,
            decay=self.config.short_term.echo_decay,
            sensory_gain=self.config.short_term.echo_sensory_gain,
            thought_gain=self.config.short_term.echo_thought_gain,
            max_echo_energy=self.config.short_term.echo_max_energy,
            max_items_per_tick=self.config.short_term.echo_max_items_per_tick,
            modality_policies={
                "vision": {
                    "max_age_ticks": self.config.short_term.echo_vision_max_age_ticks,
                    "decay": self.config.short_term.echo_vision_decay,
                    "sensory_gain": self.config.short_term.echo_vision_gain,
                    "max_energy": self.config.short_term.echo_vision_max_energy,
                },
                "audio": {
                    "max_age_ticks": self.config.short_term.echo_audio_max_age_ticks,
                    "decay": self.config.short_term.echo_audio_decay,
                    "sensory_gain": self.config.short_term.echo_audio_gain,
                    "max_energy": self.config.short_term.echo_audio_max_energy,
                },
                "text": {
                    "max_age_ticks": self.config.short_term.echo_text_max_age_ticks,
                    "decay": self.config.short_term.echo_text_decay,
                    "sensory_gain": self.config.short_term.echo_text_gain,
                    "max_energy": self.config.short_term.echo_text_max_energy,
                },
                "thought": {
                    "max_age_ticks": self.config.short_term.echo_thought_max_age_ticks,
                    "decay": self.config.short_term.echo_thought_decay,
                    "sensory_gain": self.config.short_term.echo_thought_modality_gain,
                    "thought_gain": self.config.short_term.echo_thought_modality_gain,
                    "max_energy": self.config.short_term.echo_thought_max_energy,
                },
            },
        )
        self.short_term_memory = ShortTermMemoryWindow(
            history_limit=self.config.short_term.memory_window_history_limit,
            max_age_ticks=self.config.short_term.memory_window_max_age_ticks,
            recency_decay=self.config.short_term.memory_window_recency_decay,
            fatigue_decay=self.config.short_term.memory_window_fatigue_decay,
            fatigue_step=self.config.short_term.memory_window_fatigue_step,
            max_items_per_event=self.config.short_term.memory_window_max_items_per_event,
            default_recall_limit=self.config.short_term.memory_window_recall_limit,
        )
        self.focus_successor_bias = FocusSuccessorBias(
            enabled=self.config.attention.successor_bias_enabled,
            context_limit=self.config.attention.successor_bias_context_limit,
            max_successors_per_context=self.config.attention.successor_bias_max_successors_per_context,
            max_context_labels=self.config.attention.successor_bias_max_context_labels,
            max_order=self.config.attention.successor_bias_max_order,
            top_k=self.config.attention.successor_bias_top_k,
            per_tick_update_limit=self.config.attention.successor_bias_per_tick_update_limit,
            real_threshold=self.config.attention.successor_bias_real_threshold,
            decay=self.config.attention.successor_bias_decay,
            rescale_threshold=self.config.attention.successor_bias_rescale_threshold,
            rescale_factor=self.config.attention.successor_bias_rescale_factor,
            min_support=self.config.attention.successor_bias_min_support,
            gain=self.config.attention.successor_bias_gain,
            max_bias=self.config.attention.successor_bias_max,
            entropy_floor=self.config.attention.successor_bias_entropy_floor,
        )
        self.text_actuator = TextActionActuator()
        self.visual_gaze_actuator = VisualGazeActuator()
        self.auditory_band_actuator = AuditoryBandActuator()
        self._pending_action_feedback: dict | None = None
        self._queued_external_feedback: dict | None = None
        self._pending_innate_attention_biases: list[dict] = []
        self._pending_action_attention_controls: list[dict] = []
        self._pending_slow_query_hints: list[dict] = []
        self._pending_focus_family_modulation: dict = {}
        self._focus_hold_count = 0
        self._text_ingest_cache: dict = {}
        self.tick_index = -1

    def queue_education_intervention(self, intervention: dict) -> dict:
        """Queue one external teaching intervention for the next tick.

        AP core does not own a concrete teaching skill. It only accepts a
        neutral packet of state hints, soft drive biases, and feedback so human,
        detachable-rule, and LLM teachers all use the same non-invasive doorway.
        """

        return self.education_interventions.queue(intervention, tick_index=self.tick_index + 1)

    def process_text_tick(
        self,
        text: str = "",
        *,
        memory_bootstrap: bool = False,
        trace_mode: str | None = None,
        education_interventions: dict | list[dict] | None = None,
    ) -> dict:
        return self.process_multimodal_tick(
            text=text,
            memory_bootstrap=memory_bootstrap,
            trace_mode=trace_mode,
            education_interventions=education_interventions,
        )

    def process_multimodal_tick(
        self,
        text: str = "",
        *,
        image_bytes: bytes | None = None,
        audio_bytes: bytes | None = None,
        memory_bootstrap: bool = False,
        trace_mode: str | None = None,
        education_interventions: dict | list[dict] | None = None,
    ) -> dict:
        trace_mode = self._normalize_trace_mode(trace_mode)
        stage_started_at = perf_counter()
        performance_stages: list[dict] = []

        def mark_stage(stage_name: str) -> None:
            nonlocal stage_started_at
            now = perf_counter()
            performance_stages.append({"stage": stage_name, "ms": round((now - stage_started_at) * 1000.0, 4)})
            stage_started_at = now

        self.tick_index += 1
        gc_was_enabled = gc.isenabled()
        if bool(self.config.observability.disable_gc_during_tick) and gc_was_enabled:
            gc.disable()
        try:
            return self._process_multimodal_tick_inner(
                text=text,
                image_bytes=image_bytes,
                audio_bytes=audio_bytes,
                memory_bootstrap=memory_bootstrap,
                trace_mode=trace_mode,
                education_interventions=education_interventions,
                performance_stages=performance_stages,
                mark_stage=mark_stage,
                stage_started_at_ref=lambda: stage_started_at,
            )
        finally:
            if bool(self.config.observability.disable_gc_during_tick) and gc_was_enabled:
                gc.enable()

    def queue_external_feedback(
        self,
        *,
        reward: float = 0.0,
        punishment: float = 0.0,
        correctness: float = 0.0,
        confidence: float = 1.0,
        source: str = "external_feedback",
        notes: list[str] | None = None,
    ) -> dict:
        feedback = {
            "schema_id": "external_action_feedback/v1",
            "reward": round(max(0.0, float(reward or 0.0)), 4),
            "punishment": round(max(0.0, float(punishment or 0.0)), 4),
            "correctness": round(max(0.0, float(correctness or 0.0)), 4),
            "confidence": round(max(0.0, min(1.0, float(confidence or 0.0))), 4),
            "source": str(source or "external_feedback"),
            "notes": [str(note or "") for note in list(notes or []) if str(note or "")],
        }
        self._queued_external_feedback = feedback
        return {"schema_id": "external_feedback_queue_trace/v1", "queued": True, "feedback": dict(feedback)}

    def _queue_inline_education_interventions(self, interventions: dict | list[dict] | None) -> None:
        """Normalize caller-supplied teacher packets into the one-tick queue.

        This keeps education optional and detachable: if no packet is supplied,
        AP runs exactly as itself. If a packet is supplied, it is still consumed
        as state hints / soft biases / feedback rather than as a privileged
        skill routine inside the runtime.
        """

        if not interventions:
            return
        rows = interventions if isinstance(interventions, list) else [interventions]
        for row in rows:
            if isinstance(row, dict):
                self.queue_education_intervention(row)

    def _process_multimodal_tick_inner(
        self,
        *,
        text: str,
        image_bytes: bytes | None,
        audio_bytes: bytes | None,
        memory_bootstrap: bool,
        trace_mode: str,
        education_interventions: dict | list[dict] | None,
        performance_stages: list[dict],
        mark_stage,
        stage_started_at_ref,
    ) -> dict:
        runtime_budget_trace = self.runtime_budget_controller.begin_tick(self.tick_index)
        self.state_pool.begin_tick(self.tick_index)
        self._queue_inline_education_interventions(education_interventions)
        input_packet, competition, external_items, multimodal_trace = self._ingest_multimodal(
            text=text, image_bytes=image_bytes, audio_bytes=audio_bytes
        )
        mark_stage("ingest")
        self._apply_external_or_bootstrap(external_items, memory_bootstrap=memory_bootstrap)
        short_term_echo_trace = self._apply_short_term_echo(external_items)
        short_term_memory_observations: list[dict] = [
            self._observe_short_term_memory(external_items, source_kind="sensory", role="current_external_input")
        ]
        education_intervention_trace = self.education_interventions.consume(tick_index=self.tick_index)
        education_state_items = list(education_intervention_trace.get("state_items", []) or [])
        if education_state_items:
            self.state_pool.apply_external_items(education_state_items, tick_index=self.tick_index)
            short_term_memory_observations.append(
                self._observe_short_term_memory(
                    education_state_items,
                    source_kind="education_intervention",
                    modality="teacher",
                    role="external_teacher_hint",
                )
            )
        education_feedback = dict(education_intervention_trace.get("feedback", {}) or {})
        if education_feedback:
            self._merge_queued_external_feedback(education_feedback)
        action_feedback_trace = self._consume_pending_action_feedback()
        if action_feedback_trace["feedback_items"]:
            self.state_pool.apply_external_items(action_feedback_trace["feedback_items"], tick_index=self.tick_index)
            short_term_memory_observations.append(
                self._observe_short_term_memory(
                    list(action_feedback_trace.get("feedback_items", []) or []),
                    source_kind="action_feedback",
                    modality="action",
                    role="delayed_action_feedback",
                )
            )
        mark_stage("apply_external")
        innate_traces: dict[str, dict] = {}
        post_external_innate_trace = self._evaluate_innate_phase(
            "post_external",
            state_items=external_items + list(action_feedback_trace.get("feedback_items", []) or []),
            action_feedback_trace=action_feedback_trace,
        )
        innate_traces["post_external"] = post_external_innate_trace
        mark_stage("innate_post_external")

        # Emotion is a slow modulation layer. The attention gate uses the
        # modulation state accumulated before this tick; current feelings and
        # feedback update the layer later and affect action + subsequent ticks.
        prior_emotion_modulation = self.emotion_modulator.get_modulation()

        readout_budget = self.runtime_budget_controller.readout_budget(
            base_items_per_head=self.config.state_pool.r_state_items_per_head,
            base_head_limit=self.config.state_pool.r_state_head_limit,
        )
        runtime_budget_trace["readout_budget"] = readout_budget
        r_state_fast = self.state_pool.read_r_state(
            items_per_head=readout_budget["items_per_head"],
            head_limit=readout_budget["head_limit"],
        )
        r_state_fast["runtime_budget"] = {
            "schema_id": "r_state_runtime_budget/v1",
            "items_per_head_changed": bool(readout_budget.get("changed", False)),
            "source_tick_index": int(runtime_budget_trace.get("source_tick_index", -1) or -1),
        }
        fast_query = self._r_state_to_query_items(r_state_fast)
        fast_bn, fast_cn = self._run_recall_branch(fast_query, memory_kind="state", prediction_source="fast_cn")
        mark_stage("fast_recall_initial")
        innate_traces["post_fast_recall"] = self._evaluate_innate_phase(
            "post_fast_recall",
            state_items=self._r_state_to_query_items(r_state_fast),
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            prediction_trace=self.state_pool.prediction_trace(),
            action_feedback_trace=action_feedback_trace,
        )
        mark_stage("innate_post_fast_recall")
        time_trace = self.time_feeling.derive(tick_index=self.tick_index, bn_rows=fast_bn)
        time_context = self._build_time_context(time_trace)
        if time_trace["items"]:
            self.state_pool.apply_external_items(time_trace["items"], tick_index=self.tick_index)
            time_rows = self.state_pool.rows_for_labels(
                [
                    str(item.get("sa_label", "") or "")
                    for item in time_trace["items"]
                    if str(item.get("sa_label", "") or "")
                ]
            )
            if time_rows:
                r_state_fast = self._append_r_state_head(r_state_fast, "head_time_feeling", time_rows)
            if self._should_rerun_timefelt_recall(time_trace):
                fast_query = self._r_state_to_query_items(r_state_fast)
                fast_bn, fast_cn = self._run_recall_branch(
                    fast_query,
                    memory_kind="state",
                    prediction_source="fast_cn_timefelt",
                    time_context=time_context,
                )
        mark_stage("time_and_fast_recall")

        previous_focus_labels = self.focus_buffer.tail()
        innate_attention_biases_for_selection = self._consume_pending_innate_attention_biases()
        action_attention_controls_for_selection = self._consume_pending_action_attention_controls()
        action_focus_family_modulation = self._consume_pending_focus_family_modulation()
        attention_candidates = self._r_state_to_attention_candidates(r_state_fast)
        successor_bias_trace = self.focus_successor_bias.build_bias(
            previous_focus_labels=previous_focus_labels,
            candidate_items=attention_candidates,
            tick_index=self.tick_index,
        )
        attention_trace = self.attention.select(
            attention_candidates,
            previous_focus_labels=previous_focus_labels,
            emotion_modulation=prior_emotion_modulation,
            successor_bias=successor_bias_trace,
            innate_attention_biases=innate_attention_biases_for_selection,
            action_attention_controls=action_attention_controls_for_selection,
        )
        raw_attention_items = list(attention_trace.get("selected_items", []) or [])
        balanced_focus_items, focus_family_budget_trace = self._shape_focus_family_budget(
            ranked_items=list(attention_trace.get("ranked_items", []) or []),
            raw_selected_items=raw_attention_items,
            action_modulation=action_focus_family_modulation,
        )
        ordered_focus_items, focus_order_trace = self._stabilize_focus_order(balanced_focus_items)
        ordered_focus_labels = [
            str(item.get("sa_label", "") or "") for item in ordered_focus_items if str(item.get("sa_label", "") or "")
        ]
        attention_trace = dict(attention_trace)
        attention_trace["raw_selected_labels"] = [
            str(item.get("sa_label", "") or "") for item in raw_attention_items if str(item.get("sa_label", "") or "")
        ]
        attention_trace["family_budget"] = focus_family_budget_trace
        attention_trace["action_attention_controls_consumed"] = action_attention_controls_for_selection
        attention_trace["action_family_budget_modulation_consumed"] = action_focus_family_modulation
        attention_trace["selected_items"] = ordered_focus_items
        attention_trace["selected_labels"] = ordered_focus_labels
        attention_trace["focus_order"] = focus_order_trace
        self.state_pool.select_focus(ordered_focus_labels)
        self.focus_buffer.push(ordered_focus_items, tick_index=self.tick_index)
        self._observe_short_term_thought_echo(ordered_focus_items)
        short_term_memory_observations.append(
            self._observe_short_term_memory(
                ordered_focus_items, source_kind="thought", modality="thought", role="selected_attention_focus"
            )
        )
        successor_bias_update_trace = self.focus_successor_bias.observe_transition(
            previous_focus_labels=previous_focus_labels,
            current_focus_items=ordered_focus_items,
            tick_index=self.tick_index,
        )
        focus_continuation_trace = self.focus_buffer.trace(tick_index=self.tick_index)
        short_term_preview_recall = (
            self.short_term_memory.recall(
                tick_index=self.tick_index,
                cues=ordered_focus_items,
                limit=self.config.short_term.memory_window_recall_limit,
                reason="planning_preview",
                similarity_fn=self._short_term_memory_similarity,
                update_fatigue=False,
            )
            if bool(getattr(self.config.short_term, "memory_window_enabled", True))
            else {"available": False}
        )
        focus_continuation_trace["short_term_memory_readback"] = short_term_preview_recall
        self.rhythm.observe(tick_index=self.tick_index, focus_items=ordered_focus_items)
        rhythm_trace = self.rhythm.derive(tick_index=self.tick_index)
        if rhythm_trace["items"]:
            self.state_pool.apply_external_items(rhythm_trace["items"], tick_index=self.tick_index)
        mark_stage("attention_and_rhythm")
        innate_traces["post_attention"] = self._evaluate_innate_phase(
            "post_attention",
            state_items=ordered_focus_items,
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            attention=attention_trace,
            time_trace=time_trace,
            rhythm_trace=rhythm_trace,
            action_feedback_trace=action_feedback_trace,
        )
        mark_stage("innate_post_attention")

        slow_query_hints_for_selection = self._consume_pending_slow_query_hints()
        focus_continuation_trace["action_slow_query_hints_consumed"] = slow_query_hints_for_selection
        slow_query = self._build_slow_query(ordered_focus_items, action_slow_query_hints=slow_query_hints_for_selection)
        slow_bn, slow_cn = self._run_recall_branch(
            slow_query,
            memory_kind="focus",
            prediction_source="slow_cn",
            time_context=time_context,
        )
        mark_stage("slow_recall")
        innate_traces["post_slow_recall"] = self._evaluate_innate_phase(
            "post_slow_recall",
            state_items=ordered_focus_items,
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            attention=attention_trace,
            time_trace=time_trace,
            rhythm_trace=rhythm_trace,
            action_feedback_trace=action_feedback_trace,
        )
        mark_stage("innate_post_slow_recall")

        state_snapshot_before_feelings = self.state_pool.snapshot()
        prediction_trace_for_feelings = self.state_pool.prediction_trace()
        residual_summary_for_feelings = self.state_pool.residual_summary(limit=8)
        feeling_trace = self.cognitive_feelings.derive(
            state_snapshot_items=state_snapshot_before_feelings["items"],
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            prediction_trace=prediction_trace_for_feelings,
            residual_summary=residual_summary_for_feelings,
        )
        post_validation_innate_trace = self._evaluate_innate_phase(
            "post_prediction_validation",
            state_items=state_snapshot_before_feelings["items"],
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            attention=attention_trace,
            feelings=feeling_trace,
            prediction_trace=prediction_trace_for_feelings,
            residual_summary=residual_summary_for_feelings,
            time_trace=time_trace,
            rhythm_trace=rhythm_trace,
            action_feedback_trace=action_feedback_trace,
        )
        innate_traces["post_prediction_validation"] = post_validation_innate_trace
        if feeling_trace["items"]:
            self.state_pool.apply_external_items(feeling_trace["items"], tick_index=self.tick_index)
        if post_validation_innate_trace["items"]:
            self.state_pool.apply_external_items(post_validation_innate_trace["items"], tick_index=self.tick_index)
        mark_stage("cognitive_feelings")

        # P1-J-17 task feelings must be part of the same cognitive tick, not a
        # post-hoc log row. We derive them from the current successor/readback
        # situation before expectation pressure and emotion update, so boredom
        # and fulfillment can modulate NT state and action planning immediately.
        short_term_memory_trace = self._short_term_memory_trace(last_recall=short_term_preview_recall)
        short_term_memory_trace["observations"] = [
            dict(row) for row in short_term_memory_observations if isinstance(row, dict)
        ]
        task_feeling_trace = self._derive_task_feeling(
            input_packet=input_packet,
            fast_cn=fast_cn,
            slow_cn=slow_cn,
            focus_continuation_trace=focus_continuation_trace,
            short_term_memory_trace=short_term_memory_trace,
            cognitive_feelings=feeling_trace,
            residual_summary=self.state_pool.residual_summary(limit=8),
            action_trace={},
        )
        if task_feeling_trace.get("items"):
            self.state_pool.apply_external_items(
                list(task_feeling_trace.get("items", []) or []), tick_index=self.tick_index
            )
            feeling_trace = self._merge_feelings_with_task_feeling(feeling_trace, task_feeling_trace)
        mark_stage("task_feeling")

        expectation_pressure_trace = self.expectation_pressure.derive(
            tick_index=self.tick_index,
            cognitive_feelings=feeling_trace,
            prediction_trace=self.state_pool.prediction_trace(),
            residual_summary=self.state_pool.residual_summary(limit=8),
            action_feedback_trace=action_feedback_trace,
            rhythm_trace=rhythm_trace,
            time_trace=time_trace,
        )
        if expectation_pressure_trace["items"]:
            self.state_pool.apply_external_items(expectation_pressure_trace["items"], tick_index=self.tick_index)
        expectation_anchor_trace = self.expectation_anchor_verifier.update(
            tick_index=self.tick_index,
            fast_bn=fast_bn,
            slow_bn=slow_bn,
            fast_cn=fast_cn,
            slow_cn=slow_cn,
            action_feedback_trace=action_feedback_trace,
            cognitive_feelings=feeling_trace,
        )
        expectation_pressure_trace = dict(expectation_pressure_trace)
        expectation_pressure_trace["anchor_verification"] = expectation_anchor_trace
        expectation_pressure_trace["items"] = list(expectation_pressure_trace.get("items", []) or []) + list(
            expectation_anchor_trace.get("items", []) or []
        )
        channels = dict(expectation_pressure_trace.get("channels", {}) or {})
        channels["anchor_active_count"] = int(expectation_anchor_trace.get("active_count", 0) or 0)
        channels["anchor_created_count"] = len(expectation_anchor_trace.get("created", []) or [])
        channels["anchor_verified_count"] = len(expectation_anchor_trace.get("verified", []) or [])
        channels["anchor_missed_count"] = len(expectation_anchor_trace.get("missed", []) or [])
        expectation_pressure_trace["channels"] = channels
        if expectation_anchor_trace.get("items"):
            self.state_pool.apply_external_items(
                list(expectation_anchor_trace.get("items", []) or []), tick_index=self.tick_index
            )
        mark_stage("expectation_pressure")

        observed_feedback_for_emotion = dict(action_feedback_trace.get("observed_feedback", {}) or {})
        emotion_post_innate_trace = self._evaluate_innate_phase(
            "emotion_post",
            state_items=self.state_pool.snapshot()["items"],
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            attention=attention_trace,
            feelings=feeling_trace,
            prediction_trace=self.state_pool.prediction_trace(),
            residual_summary=self.state_pool.residual_summary(limit=8),
            time_trace=time_trace,
            rhythm_trace=rhythm_trace,
            expectation_pressure=expectation_pressure_trace,
            emotion_state=self.emotion_modulator.state.get_state(),
            action_feedback_trace=action_feedback_trace,
        )
        innate_traces["emotion_post"] = emotion_post_innate_trace
        # Update emotion state based on cognitive feelings and delayed action feedback
        # (8-channel NT system). This post-attention update is available to action
        # planning immediately and to attention on the next tick.
        emotion_feelings = self._merge_feelings_with_expectation_pressure(
            feeling_trace,
            expectation_pressure_trace,
        )
        emotion_update_trace = self.emotion_modulator.update(
            cognitive_feelings=emotion_feelings,
            reward=float(observed_feedback_for_emotion.get("reward", 0.0) or 0.0),
            punishment=float(observed_feedback_for_emotion.get("punishment", 0.0) or 0.0),
            innate_deltas=emotion_post_innate_trace.get("emotion_deltas", {}),
        )
        emotion_modulation = self.emotion_modulator.get_modulation()

        state_snapshot_before_action = self.state_pool.snapshot()
        text_context_items = self.text_actuator.short_term_context_items()
        if text_context_items:
            # Draft text actions are low-energy, local actuator facts. They can
            # fall out of the global state snapshot when prediction/residual
            # items are loud, but the drive manager still needs them to decide
            # whether a recent output mismatch should be reread or revised.
            # We feed them as planning context only; normal output items are
            # still written to the state pool after the actuator acts.
            seen_snapshot_labels = {
                str(item.get("sa_label", "") or "") for item in state_snapshot_before_action.get("items", [])
            }
            merged_items = list(state_snapshot_before_action.get("items", []) or [])
            merged_items.extend(
                item
                for item in text_context_items
                if str(item.get("sa_label", "") or "") not in seen_snapshot_labels
                or str((item.get("anchor_meta", {}) or {}).get("event_type", "") or "")
                in {"write_mismatch", "reread", "revise", "replace"}
            )
            state_snapshot_before_action = dict(state_snapshot_before_action)
            state_snapshot_before_action["items"] = merged_items
        if education_state_items:
            # External teacher hints are first-class state-field citizens. They
            # make the current teaching context recallable, but teacher control
            # still remains a soft drive bias consumed by the planner below.
            seen_snapshot_labels = {
                str(item.get("sa_label", "") or "") for item in state_snapshot_before_action.get("items", [])
            }
            extra_education_items = [
                item
                for item in education_state_items
                if str(item.get("sa_label", "") or "")
                and str(item.get("sa_label", "") or "") not in seen_snapshot_labels
            ]
            if extra_education_items:
                state_snapshot_before_action = dict(state_snapshot_before_action)
                state_snapshot_before_action["items"] = (
                    list(state_snapshot_before_action.get("items", []) or []) + extra_education_items
                )
        action_consequence_trace = self.action_consequence_evaluator.evaluate(
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            snapshot_lookup=self.memory.snapshot_by_id,
            successor_lookup=self.memory.successor_links,
            current_tick=self.tick_index,
        )
        mark_stage("emotion_and_consequence")
        action_preselect_innate_trace = self._evaluate_innate_phase(
            "action_preselect",
            state_items=state_snapshot_before_action["items"],
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            attention=attention_trace,
            feelings=feeling_trace,
            prediction_trace=self.state_pool.prediction_trace(),
            residual_summary=self.state_pool.residual_summary(limit=8),
            time_trace=time_trace,
            rhythm_trace=rhythm_trace,
            expectation_pressure=expectation_pressure_trace,
            emotion_state=emotion_update_trace.get("emotion_state", {}),
            action_feedback_trace=action_feedback_trace,
            action_consequence_trace=action_consequence_trace,
        )
        innate_traces["action_preselect"] = action_preselect_innate_trace
        action_biases_for_planner = list(action_preselect_innate_trace.get("action_biases", []) or []) + list(
            education_intervention_trace.get("action_biases", []) or []
        )
        action_trace = self.action_planner.plan(
            tick_index=self.tick_index,
            state_snapshot_items=state_snapshot_before_action["items"],
            attention_trace=attention_trace,
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            cognitive_feelings=feeling_trace,
            expectation_pressure_trace=expectation_pressure_trace,
            rhythm_trace=rhythm_trace,
            time_trace=time_trace,
            residual_summary=self.state_pool.residual_summary(limit=8),
            prediction_trace=self.state_pool.prediction_trace(),
            action_consequence_trace=action_consequence_trace,
            emotion_modulation=emotion_modulation,
            innate_action_nodes=action_preselect_innate_trace.get("action_nodes", []),
            innate_action_biases=action_biases_for_planner,
            recent_thought_readback=dict(focus_continuation_trace.get("recent_thought_readback", {}) or {}),
            short_term_memory_readback=dict(focus_continuation_trace.get("short_term_memory_readback", {}) or {}),
            memory_action_drive_gain=self.config.innate_rules.memory_action_virtual_drive_gain,
        )
        action_trace["education_intervention"] = education_intervention_trace
        pre_safety_short_term_recall = self._short_term_memory_recall_for_actions(
            selected_actions=list(action_trace.get("selected_actions", []) or []),
            attention_trace=attention_trace,
            state_snapshot_items=state_snapshot_before_action.get("items", []),
            focus_continuation_trace=focus_continuation_trace,
            reason="pre_safety_action_control",
            update_fatigue=False,
        )
        pre_safety_control_items = self._build_action_control_items(
            selected_actions=action_trace.get("selected_actions", []),
            attention_trace=attention_trace,
            fast_bn=fast_bn,
            slow_bn=slow_bn,
            fast_cn=fast_cn,
            slow_cn=slow_cn,
            state_snapshot_items=state_snapshot_before_action.get("items", []),
            time_context=time_context,
            action_consequence_trace=action_consequence_trace,
            expectation_pressure_trace=expectation_pressure_trace,
            focus_continuation_trace=focus_continuation_trace,
            short_term_memory_recall=pre_safety_short_term_recall,
        )
        safety_gate_trace = self.safety_gate.review(
            tick_index=self.tick_index,
            candidates=list(action_trace.get("candidates", []) or []),
            selected_actions=list(action_trace.get("selected_actions", []) or []),
            cognitive_feelings=feeling_trace,
            emotion_state=emotion_update_trace.get("emotion_state", {}),
            safety_trace={"hits": list(action_preselect_innate_trace.get("safety_gate", []) or [])},
            expectation_pressure_trace=expectation_pressure_trace,
            action_control_items=pre_safety_control_items,
        )
        if safety_gate_trace.get("enabled", False):
            action_trace["selected_actions_before_safety"] = list(action_trace.get("selected_actions", []) or [])
            action_trace["selected_actions"] = list(safety_gate_trace.get("selected_actions", []) or [])
            action_trace["action_items"] = self.action_planner.build_action_items(
                list(action_trace.get("selected_actions", []) or []),
                tick_index=self.tick_index,
            )
        action_trace["safety_gate"] = safety_gate_trace
        action_trace["feedback_items"] = list(action_feedback_trace.get("feedback_items", []) or [])
        selected_short_term_recall = self._short_term_memory_recall_for_actions(
            selected_actions=list(action_trace.get("selected_actions", []) or []),
            attention_trace=attention_trace,
            state_snapshot_items=state_snapshot_before_action.get("items", []),
            focus_continuation_trace=focus_continuation_trace,
            reason="selected_action_control",
            update_fatigue=True,
        )
        control_items = self._build_action_control_items(
            selected_actions=action_trace.get("selected_actions", []),
            attention_trace=attention_trace,
            fast_bn=fast_bn,
            slow_bn=slow_bn,
            fast_cn=fast_cn,
            slow_cn=slow_cn,
            state_snapshot_items=state_snapshot_before_action.get("items", []),
            time_context=time_context,
            action_consequence_trace=action_consequence_trace,
            expectation_pressure_trace=expectation_pressure_trace,
            focus_continuation_trace=focus_continuation_trace,
            short_term_memory_recall=selected_short_term_recall,
        )
        action_control_effect_trace = self.action_control_effect_router.build(
            tick_index=self.tick_index,
            selected_actions=list(action_trace.get("selected_actions", []) or []),
            attention_trace=attention_trace,
            state_snapshot_items=state_snapshot_before_action.get("items", []),
            prediction_trace=self.state_pool.prediction_trace(),
            residual_summary=self.state_pool.residual_summary(limit=8),
            previous_focus_labels=previous_focus_labels,
        )
        effect_control_items = list(action_control_effect_trace.get("control_items", []) or [])
        if effect_control_items:
            control_items = list(control_items) + effect_control_items
        self._remember_action_control_effects(action_control_effect_trace)
        visual_control_trace = self.visual_gaze_actuator.step(
            tick_index=self.tick_index,
            selected_actions=list(action_trace.get("selected_actions", []) or []),
            attention_trace=attention_trace,
        )
        auditory_control_trace = self.auditory_band_actuator.step(
            tick_index=self.tick_index,
            selected_actions=list(action_trace.get("selected_actions", []) or []),
            attention_trace=attention_trace,
        )
        control_items = (
            list(control_items)
            + list(visual_control_trace.get("items", []) or [])
            + list(auditory_control_trace.get("items", []) or [])
        )
        if control_items:
            self.state_pool.apply_external_items(control_items, tick_index=self.tick_index)
            short_term_memory_observations.append(
                self._observe_short_term_memory(
                    control_items, source_kind="action_control", modality="action", role="selected_action_controls"
                )
            )
        if action_trace["action_items"]:
            self.state_pool.apply_external_items(action_trace["action_items"], tick_index=self.tick_index)
            short_term_memory_observations.append(
                self._observe_short_term_memory(
                    list(action_trace.get("action_items", []) or []),
                    source_kind="action",
                    modality="action",
                    role="selected_action_nodes",
                )
            )
        if safety_gate_trace.get("inhibition_items"):
            self.state_pool.apply_external_items(
                list(safety_gate_trace.get("inhibition_items", []) or []), tick_index=self.tick_index
            )
        action_trace["control_items"] = control_items
        action_trace["action_control_effects"] = action_control_effect_trace
        action_trace["visual_gaze"] = visual_control_trace
        action_trace["auditory_band"] = auditory_control_trace
        action_trace["inhibition_items"] = list(safety_gate_trace.get("inhibition_items", []) or [])
        action_trace["short_term_memory_recall"] = selected_short_term_recall
        unfinished_mark_trace = self._mark_unfinished_thought_if_needed(
            focus_continuation_trace=focus_continuation_trace,
            expected_text=self.action_planner.expected_text_context(fast_cn=fast_cn, slow_cn=slow_cn),
            action_trace=action_trace,
            short_term_memory_recall=selected_short_term_recall,
        )
        action_trace["unfinished_thought_mark"] = unfinished_mark_trace
        feedback_focus_rows = attention_trace.get("selected_items", [])[: self.config.attention.focus_limit]
        top_after_control = self._labels_after_action_control(
            feedback_focus_rows=feedback_focus_rows,
            control_items=control_items,
            action_items=list(action_trace.get("action_items", []) or []),
        )
        action_trace["feedback_context"] = {
            "focus_labels_after_control": [str(item.get("sa_label", "") or "") for item in feedback_focus_rows],
            "top_labels_after_control": top_after_control,
            "visual_gaze_events": [dict(event) for event in list(visual_control_trace.get("events", []) or [])],
            "auditory_band_events": [dict(event) for event in list(auditory_control_trace.get("events", []) or [])],
            "action_control_effects": [
                dict((item.get("anchor_meta", {}) or {}))
                for item in list(control_items or [])[:16]
                if str((item.get("anchor_meta", {}) or {}).get("schema_id", "") or "").endswith("_control/v1")
            ],
        }

        # Text output-side closure: explicit write/reread/revise evidence chain.
        # This is not "the model output"; it is a white-box actuator trace that
        # can be audited and learned from later.
        focus_labels_now = list(attention_trace.get("selected_labels", []) or [])
        text_output_trace = self.text_actuator.step(
            tick_index=self.tick_index,
            input_text=input_packet.get("normalized_text", "") or "",
            selected_actions=list(action_trace.get("selected_actions", []) or []),
            fast_cn=fast_cn,
            slow_cn=slow_cn,
            focus_labels=focus_labels_now,
            cognitive_feelings=feeling_trace,
        )
        if text_output_trace.get("output_items"):
            self.state_pool.apply_external_items(
                list(text_output_trace.get("output_items", []) or []), tick_index=self.tick_index
            )
            short_term_memory_observations.append(
                self._observe_short_term_memory(
                    list(text_output_trace.get("output_items", []) or []),
                    source_kind="output",
                    modality="text",
                    role="text_action_output",
                )
            )
        short_term_memory_trace = self._short_term_memory_trace(last_recall=selected_short_term_recall)
        short_term_memory_trace["observations"] = [
            dict(row) for row in short_term_memory_observations if isinstance(row, dict)
        ]
        task_feeling_trace = dict(task_feeling_trace)
        task_feeling_trace["post_action_short_term_memory"] = {
            "schema_id": "task_feeling_post_action_memory_note/v1",
            "last_recall_available": bool(selected_short_term_recall.get("available", False)),
            "selected_action_count": len(list(action_trace.get("selected_actions", []) or [])),
            "meaning": "task_feeling_was_derived_before_emotion;this_note_keeps_late_memory_recall_observable",
        }
        mark_stage("action_and_output")

        state_snapshot = self.state_pool.snapshot()
        state_snapshot_for_memory = self.state_pool.snapshot_for_memory_write()
        state_snapshot["energy_flow"] = self.state_pool.energy_flow_trace(
            items=state_snapshot.get("items", []),
            r_state=r_state_fast,
            memory_write_items=state_snapshot_for_memory.get("items", []),
        )
        target_tick_ms = float(getattr(self.config.observability, "target_tick_ms", 100) or 100)
        pending_index_before_write = self.memory.pending_index_job_summary()
        elapsed_before_load_feeling_ms = (perf_counter() - stage_started_at_ref()) * 1000.0 + sum(
            float(stage.get("ms", 0.0) or 0.0) for stage in performance_stages
        )
        runtime_load_trace = self.runtime_load_feeling.derive(
            tick_index=self.tick_index,
            target_tick_ms=target_tick_ms,
            elapsed_ms=elapsed_before_load_feeling_ms,
            r_state=r_state_fast,
            attention_candidates=attention_candidates,
            state_snapshot=state_snapshot,
            attention_trace=attention_trace,
            prediction_trace=self.state_pool.prediction_trace(),
            residual_summary=self.state_pool.residual_summary(limit=8),
            pending_index_summary=pending_index_before_write,
        )
        if runtime_load_trace["items"]:
            self.state_pool.apply_external_items(runtime_load_trace["items"], tick_index=self.tick_index)
            state_snapshot = self.state_pool.snapshot()
            feeling_trace = self._merge_feelings_with_runtime_load(feeling_trace, runtime_load_trace)
        next_budget_trace = self.runtime_budget_controller.observe_runtime_load(runtime_load_trace)
        runtime_budget_trace["next_budget"] = next_budget_trace
        runtime_load_trace["budget_controller"] = {
            "schema_id": "runtime_load_budget_controller_link/v1",
            "applies_to": "next_tick",
            "next_budget": next_budget_trace,
        }
        mark_stage("runtime_load_feeling")
        tick_end_innate_trace = self._evaluate_innate_phase(
            "tick_end",
            state_items=state_snapshot["items"],
            fast_bn=fast_bn,
            fast_cn=fast_cn,
            slow_bn=slow_bn,
            slow_cn=slow_cn,
            attention=attention_trace,
            feelings=feeling_trace,
            prediction_trace=self.state_pool.prediction_trace(),
            residual_summary=self.state_pool.residual_summary(limit=8),
            time_trace=time_trace,
            rhythm_trace=rhythm_trace,
            expectation_pressure=expectation_pressure_trace,
            emotion_state=emotion_update_trace.get("emotion_state", {}),
            action_trace=action_trace,
            action_feedback_trace=action_feedback_trace,
            action_consequence_trace=action_consequence_trace,
            runtime_load_trace=runtime_load_trace,
        )
        innate_traces["tick_end"] = tick_end_innate_trace
        if tick_end_innate_trace["items"]:
            self.state_pool.apply_external_items(tick_end_innate_trace["items"], tick_index=self.tick_index)
            state_snapshot = self.state_pool.snapshot()
        self._remember_innate_attention_biases(innate_traces)
        mark_stage("innate_tick_end")
        innate_learning_router_trace = self.innate_learning_router.route(
            tick_index=self.tick_index,
            innate_traces=innate_traces,
            expectation_anchor_trace=expectation_anchor_trace,
            action_feedback_trace=action_feedback_trace,
        )
        mark_stage("innate_learning_router")

        action_causal_window = self._build_action_causal_window(
            selected_actions=list(action_trace.get("selected_actions", []) or []),
            state_snapshot_before_action=state_snapshot_before_action,
            feedback_context=dict(action_trace.get("feedback_context", {}) or {}),
            control_items=control_items,
            action_items=list(action_trace.get("action_items", []) or []),
            text_output_trace=text_output_trace,
            state_snapshot_after_output=state_snapshot,
        )
        action_trace["causal_window"] = action_causal_window
        self._pending_action_feedback = {
            "selected_actions": list(action_trace.get("selected_actions", []) or []),
            "feedback_context": dict(action_trace.get("feedback_context", {}) or {}),
            "causal_window": dict(action_causal_window),
        }
        self._write_memory_snapshots(
            state_snapshot,
            input_packet["normalized_text"],
            attention_trace["selected_labels"],
            asset_refs=multimodal_trace.get("asset_refs", []),
            state_snapshot_for_memory=state_snapshot_for_memory,
        )
        elapsed_before_index_ms = (perf_counter() - stage_started_at_ref()) * 1000.0 + sum(
            float(stage.get("ms", 0.0) or 0.0) for stage in performance_stages
        )
        remaining_before_target_ms = target_tick_ms - elapsed_before_index_ms
        index_budget = self.runtime_budget_controller.index_budget(
            base_jobs=self.config.memory.index_jobs_per_tick,
            base_min_remaining_ms=self.config.memory.index_maintenance_min_remaining_ms,
            base_max_ms=self.config.memory.index_maintenance_max_ms,
        )
        runtime_budget_trace["index_budget"] = index_budget
        if int(index_budget.get("jobs_per_tick", 0) or 0) > 0 and remaining_before_target_ms >= float(
            index_budget["min_remaining_ms"]
        ):
            index_maintenance_trace = self.memory.process_pending_index_jobs(
                int(index_budget["jobs_per_tick"]),
                max_ms=float(index_budget["max_ms"]),
            )
            index_maintenance_trace["policy"] = "time_budgeted_runtime_indexing"
        else:
            index_maintenance_trace = self.memory.process_pending_index_jobs(0)
            index_maintenance_trace["policy"] = (
                "runtime_budget_deferred_indexing"
                if int(index_budget.get("jobs_per_tick", 0) or 0) <= 0
                else "deferred_runtime_indexing"
            )
        index_maintenance_trace["remaining_before_target_ms"] = round(remaining_before_target_ms, 4)
        index_maintenance_trace["runtime_budget"] = index_budget
        runtime_budget_trace["trace_budget"] = self.runtime_budget_controller.trace_budget(
            base_item_preview_limit=self.config.observability.trace_item_preview_limit,
            base_r_state_preview_limit=self.config.observability.trace_r_state_item_preview_limit,
            base_matched_token_limit=self.config.observability.trace_matched_token_preview_limit,
        )
        mark_stage("snapshot_and_memory_write")
        if trace_mode == "debug":
            trace_fast_bn = self.memory.strip_runtime_snapshots(fast_bn)
            trace_slow_bn = self.memory.strip_runtime_snapshots(slow_bn)
            explainability = self._build_explainability(
                state_snapshot=state_snapshot,
                fast_bn=trace_fast_bn,
                fast_cn=fast_cn,
                slow_bn=trace_slow_bn,
                slow_cn=slow_cn,
                attention_trace=attention_trace,
                feeling_trace=feeling_trace,
                runtime_load_trace=runtime_load_trace,
                expectation_pressure_trace=expectation_pressure_trace,
                time_trace=time_trace,
                rhythm_trace=rhythm_trace,
                action_trace=action_trace,
                action_feedback_trace=action_feedback_trace,
                action_consequence_trace=action_consequence_trace,
                text_output_trace=text_output_trace,
                emotion_update_trace=emotion_update_trace,
                emotion_modulation=emotion_modulation,
                prior_emotion_modulation=prior_emotion_modulation,
                focus_continuation_trace=focus_continuation_trace,
                innate_traces=innate_traces,
            )
            thought_view = self._build_thought_view(
                fast_bn=trace_fast_bn,
                fast_cn=fast_cn,
                slow_bn=trace_slow_bn,
                slow_cn=slow_cn,
                attention_trace=attention_trace,
                feeling_trace=feeling_trace,
                runtime_load_trace=runtime_load_trace,
                focus_continuation_trace=focus_continuation_trace,
                expectation_pressure_trace=expectation_pressure_trace,
                text_output_trace=text_output_trace,
            )
            trace = {
                "tick_index": self.tick_index,
                "input": input_packet,
                "competition": competition,
                "multimodal": multimodal_trace,
                "education_intervention": education_intervention_trace,
                "short_term_echo": short_term_echo_trace,
                "short_term_memory": short_term_memory_trace,
                "state_pool": {
                    "r_state": r_state_fast,
                    "query_view": fast_query,
                    "attention_view": attention_candidates,
                    "snapshot": state_snapshot,
                    "energy_flow": dict(state_snapshot.get("energy_flow", {}) or {}),
                },
                "fast_system": {
                    "bn": trace_fast_bn,
                    "cn": fast_cn,
                },
                "attention": attention_trace,
                "slow_system": {
                    "query": slow_query,
                    "bn_prime": trace_slow_bn,
                    "cn_prime": slow_cn,
                    "focus_continuation": focus_continuation_trace,
                    "successor_bias": successor_bias_trace,
                    "successor_bias_update": successor_bias_update_trace,
                },
                "cognitive_feelings": feeling_trace,
                "task_feeling": task_feeling_trace,
                "runtime_load_feeling": runtime_load_trace,
                "runtime_budget_controller": runtime_budget_trace,
                "time_feeling": time_trace,
                "rhythm": rhythm_trace,
                "expectation_pressure": expectation_pressure_trace,
                "emotion": {
                    "update": emotion_update_trace,
                    "modulation": emotion_modulation,
                },
                "innate_rules": self._compact_innate_traces(innate_traces),
                "action": action_trace,
                "action_feedback": action_feedback_trace,
                "text_output": text_output_trace,
                "thought_view": thought_view,
                "explainability": explainability,
                "learning": {
                    "online_embedding": self.memory.online_embedding_summary(),
                    "innate_event_router": innate_learning_router_trace,
                    "index_maintenance": index_maintenance_trace,
                    "runtime_budget_controller": runtime_budget_trace,
                },
                "performance": {
                    "target_tick_ms": target_tick_ms,
                    "stages_ms": performance_stages,
                    "total_ms": round(sum(float(stage.get("ms", 0.0) or 0.0) for stage in performance_stages), 4),
                },
            }
            shaped = self._shape_trace(trace, trace_mode=trace_mode)
        else:
            trace_fast_bn = self.memory.strip_runtime_snapshots(fast_bn)
            trace_slow_bn = self.memory.strip_runtime_snapshots(slow_bn)
            explainability = self._build_runtime_explainability_refs(
                state_snapshot=state_snapshot,
                fast_bn=trace_fast_bn,
                slow_bn=trace_slow_bn,
                attention_trace=attention_trace,
                feeling_trace=feeling_trace,
                runtime_load_trace=runtime_load_trace,
                expectation_pressure_trace=expectation_pressure_trace,
                action_trace=action_trace,
                action_consequence_trace=action_consequence_trace,
                emotion_update_trace=emotion_update_trace,
                emotion_modulation=emotion_modulation,
                prior_emotion_modulation=prior_emotion_modulation,
                text_output_trace=text_output_trace,
                focus_continuation_trace=focus_continuation_trace,
                innate_traces=innate_traces,
            )
            thought_view = self._build_runtime_thought_refs(
                fast_bn=trace_fast_bn,
                fast_cn=fast_cn,
                slow_bn=trace_slow_bn,
                slow_cn=slow_cn,
                attention_trace=attention_trace,
                feeling_trace=feeling_trace,
                runtime_load_trace=runtime_load_trace,
                focus_continuation_trace=focus_continuation_trace,
                expectation_pressure_trace=expectation_pressure_trace,
                text_output_trace=text_output_trace,
            )
            shaped = self._build_summary_trace(
                input_packet=input_packet,
                competition=competition,
                multimodal_trace=multimodal_trace,
                education_intervention_trace=education_intervention_trace,
                short_term_echo_trace=short_term_echo_trace,
                short_term_memory_trace=short_term_memory_trace,
                r_state_fast=r_state_fast,
                fast_query=fast_query,
                attention_candidates=attention_candidates,
                state_snapshot=state_snapshot,
                fast_bn=trace_fast_bn,
                fast_cn=fast_cn,
                attention_trace=attention_trace,
                slow_query=slow_query,
                slow_bn=trace_slow_bn,
                slow_cn=slow_cn,
                focus_continuation_trace=focus_continuation_trace,
                successor_bias_trace=successor_bias_trace,
                successor_bias_update_trace=successor_bias_update_trace,
                feeling_trace=feeling_trace,
                task_feeling_trace=task_feeling_trace,
                runtime_load_trace=runtime_load_trace,
                runtime_budget_trace=runtime_budget_trace,
                time_trace=time_trace,
                rhythm_trace=rhythm_trace,
                expectation_pressure_trace=expectation_pressure_trace,
                emotion_update_trace=emotion_update_trace,
                emotion_modulation=emotion_modulation,
                action_trace=action_trace,
                action_feedback_trace=action_feedback_trace,
                text_output_trace=text_output_trace,
                innate_traces=innate_traces,
                thought_view=thought_view,
                explainability=explainability,
                index_maintenance_trace=index_maintenance_trace,
                innate_learning_router_trace=innate_learning_router_trace,
                performance_stages=performance_stages,
            )
        final_start = perf_counter()
        shaping_ms = round((final_start - stage_started_at_ref()) * 1000.0, 4)
        shaped.setdefault("performance", {})
        shaped["performance"]["trace_shape_ms"] = shaping_ms
        shaped["performance"]["total_ms"] = round(
            float(shaped["performance"].get("total_ms", 0.0) or 0.0) + shaping_ms, 4
        )
        tuner_trace = self.adaptive_tuner.observe_tick(shaped)
        shaped["tuner"] = tuner_trace
        return shaped

    def _normalize_trace_mode(self, trace_mode: str | None) -> str:
        mode = str(trace_mode or self.config.observability.default_trace_mode or "summary").strip().lower()
        if mode in {"debug", "full", "raw"}:
            return "debug"
        return "summary"

    def _apply_short_term_echo(self, external_items: list[dict]) -> dict:
        """
        Bring recent sensory/thought residues into this tick without faking input.

        Echo items are intentionally applied after true external input and before
        fast recall. They can influence Bn/Cn like a human afterimage or recent
        thought, but their `source_type` and metadata say they are not a new
        external event. The echo buffer only observes the current external items
        after it has built this tick's echoes, so a fresh input does not echo
        itself until a later tick.
        """

        if not bool(getattr(self.config.short_term, "echo_enabled", True)):
            return {
                "schema_id": "short_term_echo_trace/v1",
                "tick_index": int(self.tick_index),
                "applied": False,
                "echo_count": 0,
                "source_counts": {},
                "items": [],
                "items_preview": [],
                "policy": "disabled",
            }
        trace = self.short_term_echo.build_echo_items(tick_index=self.tick_index)
        echo_items = list(trace.get("items", []) or [])
        if echo_items:
            self.state_pool.apply_external_items(echo_items, tick_index=self.tick_index)
        self.short_term_echo.observe_sensory_items(external_items, tick_index=self.tick_index)
        return trace

    def _observe_short_term_thought_echo(self, ordered_focus_items: list[dict]) -> None:
        if not bool(getattr(self.config.short_term, "echo_enabled", True)):
            return
        self.short_term_echo.observe_thought_items(ordered_focus_items, tick_index=self.tick_index)

    def _observe_short_term_memory(
        self,
        items: list[dict],
        *,
        source_kind: str,
        modality: str | None = None,
        role: str | None = None,
    ) -> dict:
        """
        Store a compact recent-experience event without replaying it.

        This is the P1-J-16 working-memory window. It records many recent
        multimodal facts, while active recall remains action-triggered and
        partial, preserving AP's freedom to ignore, resume, or reinterpret.
        """

        if not bool(getattr(self.config.short_term, "memory_window_enabled", True)):
            return {"schema_id": "short_term_memory_observe_trace/v1", "stored": False, "reason": "disabled"}
        return self.short_term_memory.observe(
            items,
            tick_index=self.tick_index,
            source_kind=source_kind,
            modality=modality,
            role=role,
        )

    def _short_term_memory_similarity(self, query_tokens: list[str], candidate_tokens: list[str]) -> dict:
        return self.memory.learned_similarity(
            query_tokens,
            candidate_tokens,
            limit=self.config.online_embedding.scoring_token_limit,
        )

    def _short_term_memory_trace(self, *, last_recall: dict | None = None) -> dict:
        if not bool(getattr(self.config.short_term, "memory_window_enabled", True)):
            return {
                "schema_id": "short_term_memory_window_trace/v1",
                "tick_index": int(self.tick_index),
                "window_size": 0,
                "active_event_count": 0,
                "last_recall": dict(last_recall or {"available": False}),
                "policy": "disabled",
            }
        return self.short_term_memory.trace(tick_index=self.tick_index, last_recall=last_recall)

    def _short_term_memory_recall_for_actions(
        self,
        *,
        selected_actions: list[dict],
        attention_trace: dict,
        state_snapshot_items: list[dict],
        focus_continuation_trace: dict,
        reason: str,
        update_fatigue: bool,
    ) -> dict:
        if not bool(getattr(self.config.short_term, "memory_window_enabled", True)):
            return {"available": False, "policy": "disabled"}
        action_ids = {
            str((row or {}).get("action_id", "") or "") for row in list(selected_actions or []) if isinstance(row, dict)
        }
        if not ({"action::recall_recent_context", "action::replay_recent_context"} & action_ids):
            return {"available": False, "policy": "no_recent_context_action_selected"}
        no_param_recall = False
        for row in list(selected_actions or []):
            if not isinstance(row, dict):
                continue
            if str(row.get("action_id", "") or "") not in {
                "action::recall_recent_context",
                "action::replay_recent_context",
            }:
                continue
            params = dict(row.get("params", {}) or {})
            if str(params.get("recall_mode", "") or "") in {"no_param_recent_context", "unfinished_soft_recovery"}:
                no_param_recall = True
                break
        cues: list[dict] = []
        readback = dict((focus_continuation_trace or {}).get("recent_thought_readback", {}) or {})
        if not no_param_recall:
            for item in list((attention_trace or {}).get("selected_items", []) or [])[
                : self.config.attention.focus_limit
            ]:
                if isinstance(item, dict):
                    cues.append(dict(item))
            for label in list(readback.get("labels", []) or [])[:8]:
                clean = str(label or "")
                if clean:
                    cues.append({"sa_label": clean, "family": "recent_thought"})
        state_by_label = {
            str(item.get("sa_label", "") or ""): dict(item)
            for item in list(state_snapshot_items or [])
            if isinstance(item, dict) and str(item.get("sa_label", "") or "")
        }
        enriched = []
        seen = set()
        for cue in cues:
            label = str((cue or {}).get("sa_label", "") or "")
            if not label or label in seen:
                continue
            seen.add(label)
            enriched.append(state_by_label.get(label, dict(cue)))
        return self.short_term_memory.recall(
            tick_index=self.tick_index,
            cues=enriched,
            limit=self.config.short_term.memory_window_recall_limit,
            horizon_ticks=self.config.short_term.memory_window_max_age_ticks,
            reason=f"{reason}:no_param" if no_param_recall else reason,
            similarity_fn=self._short_term_memory_similarity,
            update_fatigue=update_fatigue,
        )

    def _mark_unfinished_thought_if_needed(
        self,
        *,
        focus_continuation_trace: dict,
        expected_text: dict,
        action_trace: dict,
        short_term_memory_recall: dict,
    ) -> dict:
        if not bool(getattr(self.config.short_term, "memory_window_enabled", True)):
            return {
                "schema_id": "short_term_unfinished_mark_trace/v1",
                "stored": False,
                "reason": "short_term_memory_disabled",
            }
        selected_ids = {
            str((row or {}).get("action_id", "") or "")
            for row in list((action_trace or {}).get("selected_actions", []) or [])
            if isinstance(row, dict)
        }
        if {"action::text_insert", "action::continue_focus", "action::recall_recent_context"} & selected_ids:
            return {
                "schema_id": "short_term_unfinished_mark_trace/v1",
                "stored": False,
                "reason": "continuation_or_recall_already_selected",
            }
        current_labels = [
            str(label or "")
            for label in list((focus_continuation_trace or {}).get("current_labels", []) or [])
            if str(label or "")
        ]
        readback = dict((focus_continuation_trace or {}).get("recent_thought_readback", {}) or {})
        branch_end = max(0.0, float(readback.get("branch_end_score", 0.0) or 0.0))
        drift = max(0.0, float(readback.get("drift_score", 0.0) or 0.0))
        clarity = max(
            0.0,
            float((expected_text or {}).get("strength", 0.0) or 0.0) * 0.34
            + float((expected_text or {}).get("top_share", 0.0) or 0.0) * 0.30
            + float((expected_text or {}).get("dominance_gap", 0.0) or 0.0) * 0.42
            + (0.16 if bool((expected_text or {}).get("decisive", False)) else 0.0),
        )
        recall_available = bool((short_term_memory_recall or {}).get("available", False))
        mark_strength = min(1.0, clarity * 0.72 + max(branch_end, drift) * 0.18 + (0.08 if recall_available else 0.0))
        if mark_strength < float(getattr(self.config.task_feeling, "unfinished_mark_min_strength", 0.18) or 0.18):
            return {
                "schema_id": "short_term_unfinished_mark_trace/v1",
                "stored": False,
                "reason": "not_clear_or_not_interrupted",
                "clarity": round(clarity, 4),
                "branch_end": round(branch_end, 4),
                "drift": round(drift, 4),
            }
        successor_labels = []
        token = str((expected_text or {}).get("token", "") or "")
        if token:
            successor_labels.append(f"text::{token}")
        for alt in list((expected_text or {}).get("alternatives", []) or [])[:4]:
            alt_token = str((alt or {}).get("token", "") or "")
            if alt_token:
                successor_labels.append(f"text::{alt_token}")
        return self.short_term_memory.mark_unfinished(
            tick_index=self.tick_index,
            labels=current_labels or list(readback.get("labels", []) or []),
            successor_labels=successor_labels,
            strength=mark_strength,
            reason="clear_successor_lost_action_competition_or_interruption",
        )

    def _derive_task_feeling(
        self,
        *,
        input_packet: dict,
        fast_cn: list[dict],
        slow_cn: list[dict],
        focus_continuation_trace: dict,
        short_term_memory_trace: dict,
        cognitive_feelings: dict,
        residual_summary: dict,
        action_trace: dict,
    ) -> dict:
        if not bool(getattr(self.config.task_feeling, "enabled", True)):
            return {
                "schema_id": "task_feeling_trace/v1",
                "tick_index": int(self.tick_index),
                "channels": {},
                "items": [],
                "policy": "disabled",
            }
        expected_text = self.action_planner.expected_text_context(fast_cn=fast_cn, slow_cn=slow_cn)
        return self.task_feeling.derive(
            tick_index=self.tick_index,
            input_packet=input_packet,
            expected_text=expected_text,
            focus_continuation_trace=focus_continuation_trace,
            short_term_memory_trace=short_term_memory_trace,
            cognitive_feelings=cognitive_feelings,
            residual_summary=residual_summary,
            action_trace=action_trace,
        )

    def _trace_item_preview_limit(self) -> int:
        return self.runtime_budget_controller.trace_limit(
            base_limit=self.config.observability.trace_item_preview_limit,
            minimum=4,
        )

    def _trace_r_state_item_preview_limit(self) -> int:
        return self.runtime_budget_controller.trace_limit(
            base_limit=self.config.observability.trace_r_state_item_preview_limit,
            minimum=1,
        )

    def _trace_matched_token_preview_limit(self) -> int:
        return self.runtime_budget_controller.trace_limit(
            base_limit=self.config.observability.trace_matched_token_preview_limit,
            minimum=1,
        )

    def _r_state_to_query_items(self, r_state: dict) -> list[dict]:
        """
        Convert fixed-budget R_state heads into query_items for MemoryStore.recall().

        Policy:
        - Merge heads (dedup by sa_label).
        - Keep the highest query_weight seen across heads.
        - Preserve dual-energy fields for state_match.
        """

        merged: dict[str, dict] = {}
        for head in r_state.get("heads", []) or []:
            for row in head.get("items", []) or []:
                label = str((row or {}).get("sa_label", "") or "")
                if not label:
                    continue
                existing = merged.get(label)
                if existing is None:
                    merged[label] = dict(row)
                    continue
                existing["query_weight"] = max(
                    float(existing.get("query_weight", 0.0) or 0.0), float(row.get("query_weight", 0.0) or 0.0)
                )
                existing["real_energy"] = max(
                    float(existing.get("real_energy", 0.0) or 0.0), float(row.get("real_energy", 0.0) or 0.0)
                )
                existing["virtual_energy"] = max(
                    float(existing.get("virtual_energy", 0.0) or 0.0), float(row.get("virtual_energy", 0.0) or 0.0)
                )
        rows = list(merged.values())
        rows.sort(
            key=lambda item: (
                int(item.get("last_seen_tick", item.get("tick_index", 0)) or 0),
                int(item.get("position", 0) or 0),
                str(item.get("sa_label", "") or ""),
            )
        )
        return rows

    def _evaluate_innate_phase(
        self,
        phase: str,
        *,
        state_items: list[dict] | None = None,
        fast_bn: list[dict] | None = None,
        fast_cn: list[dict] | None = None,
        slow_bn: list[dict] | None = None,
        slow_cn: list[dict] | None = None,
        attention: dict | None = None,
        feelings: dict | None = None,
        prediction_trace: dict | None = None,
        residual_summary: dict | None = None,
        time_trace: dict | None = None,
        rhythm_trace: dict | None = None,
        expectation_pressure: dict | None = None,
        emotion_state: dict | None = None,
        action_trace: dict | None = None,
        action_feedback_trace: dict | None = None,
        action_consequence_trace: dict | None = None,
        runtime_load_trace: dict | None = None,
    ) -> dict:
        context = {
            "tick_index": self.tick_index,
            "state_items": list(state_items or []),
            "fast_bn": list(fast_bn or []),
            "fast_cn": list(fast_cn or []),
            "slow_bn": list(slow_bn or []),
            "slow_cn": list(slow_cn or []),
            "attention": dict(attention or {}),
            "feelings": dict(feelings or {}),
            "prediction_trace": dict(prediction_trace or self.state_pool.prediction_trace()),
            "residual_summary": dict(residual_summary or self.state_pool.residual_summary(limit=8)),
            "time_trace": dict(time_trace or {}),
            "rhythm_trace": dict(rhythm_trace or {}),
            "expectation_pressure": dict(expectation_pressure or {}),
            "emotion_state": dict(emotion_state or {}),
            "action_trace": dict(action_trace or {}),
            "action_feedback_trace": dict(action_feedback_trace or {}),
            "action_consequence_trace": dict(action_consequence_trace or {}),
            "runtime_load_trace": dict(runtime_load_trace or {}),
            "ui_trace": dict((action_trace or {}).get("ui_trace", {}) or {}),
            "pointer_trace": dict((action_trace or {}).get("pointer_trace", {}) or {}),
        }
        return self.innate_engine.evaluate(phase=phase, context=context, tick_index=self.tick_index)

    def _consume_pending_innate_attention_biases(self) -> list[dict]:
        biases = [dict(row) for row in list(self._pending_innate_attention_biases or []) if isinstance(row, dict)]
        self._pending_innate_attention_biases = []
        return biases[:12]

    def _remember_innate_attention_biases(self, innate_traces: dict | None) -> None:
        rows: list[dict] = []
        for phase, trace in dict(innate_traces or {}).items():
            for bias in list((trace or {}).get("attention_biases", []) or []):
                if not isinstance(bias, dict):
                    continue
                row = dict(bias)
                row.setdefault("source_phase", str(phase))
                row["created_tick_index"] = int(self.tick_index)
                rows.append(row)
        self._pending_innate_attention_biases = rows[-12:]

    def _consume_pending_action_attention_controls(self) -> list[dict]:
        controls, remaining = self._consume_ttl_rows(self._pending_action_attention_controls)
        self._pending_action_attention_controls = remaining
        return controls[:12]

    def _consume_pending_slow_query_hints(self) -> list[dict]:
        hints, remaining = self._consume_ttl_rows(self._pending_slow_query_hints)
        self._pending_slow_query_hints = remaining
        return hints[:12]

    def _consume_pending_focus_family_modulation(self) -> dict:
        row = dict(self._pending_focus_family_modulation or {})
        if not row:
            return {}
        ttl = max(0, int(row.get("ttl", 0) or 0))
        if ttl <= 0:
            self._pending_focus_family_modulation = {}
            return {}
        consumed = dict(row)
        next_row = dict(row)
        next_row["ttl"] = ttl - 1
        self._pending_focus_family_modulation = next_row if next_row["ttl"] > 0 else {}
        return consumed

    def _remember_action_control_effects(self, effect_trace: dict) -> None:
        controls = [
            dict(row) for row in list((effect_trace or {}).get("attention_controls", []) or []) if isinstance(row, dict)
        ]
        hints = [
            dict(row) for row in list((effect_trace or {}).get("slow_query_hints", []) or []) if isinstance(row, dict)
        ]
        if controls:
            self._pending_action_attention_controls = (self._pending_action_attention_controls + controls)[-18:]
        if hints:
            self._pending_slow_query_hints = (self._pending_slow_query_hints + hints)[-18:]
        modulation = dict((effect_trace or {}).get("family_budget_modulation", {}) or {})
        if modulation:
            self._pending_focus_family_modulation = modulation

    def _consume_ttl_rows(self, rows: list[dict]) -> tuple[list[dict], list[dict]]:
        consumed: list[dict] = []
        remaining: list[dict] = []
        for row in list(rows or []):
            if not isinstance(row, dict):
                continue
            ttl = max(0, int(row.get("ttl", 0) or 0))
            if ttl <= 0:
                continue
            consumed.append(dict(row))
            next_row = dict(row)
            next_row["ttl"] = ttl - 1
            if next_row["ttl"] > 0:
                remaining.append(next_row)
        return consumed, remaining

    def _shape_trace(self, trace: dict, *, trace_mode: str) -> dict:
        if trace_mode == "debug":
            trace["trace_mode"] = "debug"
            return trace
        shaped = dict(trace)
        shaped["trace_mode"] = "summary"
        shaped["competition"] = self._summarize_competition(trace.get("competition", {}))
        shaped["input"] = self._summarize_input(trace.get("input", {}))
        state_pool = dict(trace.get("state_pool", {}) or {})
        state_pool["r_state"] = self._summarize_r_state(state_pool.get("r_state", {}))
        query_view = list(state_pool.get("query_view", []) or [])
        attention_view = list(state_pool.get("attention_view", []) or [])
        state_pool["query_view_total_count"] = len(query_view)
        state_pool["attention_view_total_count"] = len(attention_view)
        state_pool["query_view"] = self._compact_rows(query_view, limit=self._trace_item_preview_limit())
        state_pool["attention_view"] = self._compact_rows(attention_view, limit=self._trace_item_preview_limit())
        shaped["state_pool"] = state_pool
        attention_trace = dict(trace.get("attention", {}) or {})
        attention_trace["selected_items"] = self._compact_rows(
            attention_trace.get("selected_items", []), limit=self.config.attention.focus_limit
        )
        attention_trace["ranked_items"] = self._compact_rows(
            attention_trace.get("ranked_items", []), limit=self._trace_item_preview_limit()
        )
        shaped["attention"] = attention_trace
        fast_system = dict(trace.get("fast_system", {}) or {})
        fast_system["bn"] = self._compact_bn_rows(fast_system.get("bn", []))
        shaped["fast_system"] = fast_system
        slow_system = dict(trace.get("slow_system", {}) or {})
        slow_system["query"] = self._compact_rows(slow_system.get("query", []), limit=self._trace_item_preview_limit())
        slow_system["bn_prime"] = self._compact_bn_rows(slow_system.get("bn_prime", []))
        if "focus_continuation" in slow_system:
            slow_system["focus_continuation"] = self._compact_focus_continuation_trace(
                slow_system.get("focus_continuation", {})
            )
        shaped["slow_system"] = slow_system
        shaped["thought_view"] = self._compact_thought_view(trace.get("thought_view", {}))
        shaped["education_intervention"] = self._compact_education_intervention_trace(
            trace.get("education_intervention", {})
        )
        shaped["short_term_echo"] = self._compact_short_term_echo_trace(trace.get("short_term_echo", {}))
        shaped["short_term_memory"] = self._compact_short_term_memory_trace(trace.get("short_term_memory", {}))
        shaped["task_feeling"] = trace.get("task_feeling", {})
        shaped["explainability"] = self._compact_explainability(trace.get("explainability", {}))
        shaped["action"] = self._compact_action_trace(trace.get("action", {}))
        shaped["innate_rules"] = self._compact_innate_traces(trace.get("innate_rules", {}))
        return shaped

    def _build_summary_trace(
        self,
        *,
        input_packet: dict,
        competition: dict,
        multimodal_trace: dict,
        education_intervention_trace: dict,
        short_term_echo_trace: dict,
        short_term_memory_trace: dict,
        r_state_fast: dict,
        fast_query: list[dict],
        attention_candidates: list[dict],
        state_snapshot: dict,
        fast_bn: list[dict],
        fast_cn: list[dict],
        attention_trace: dict,
        slow_query: list[dict],
        slow_bn: list[dict],
        slow_cn: list[dict],
        focus_continuation_trace: dict,
        successor_bias_trace: dict,
        successor_bias_update_trace: dict,
        feeling_trace: dict,
        task_feeling_trace: dict,
        runtime_load_trace: dict,
        runtime_budget_trace: dict,
        time_trace: dict,
        rhythm_trace: dict,
        expectation_pressure_trace: dict,
        emotion_update_trace: dict,
        emotion_modulation: dict,
        action_trace: dict,
        action_feedback_trace: dict,
        text_output_trace: dict,
        innate_traces: dict | None = None,
        thought_view: dict,
        explainability: dict,
        index_maintenance_trace: dict,
        innate_learning_router_trace: dict | None = None,
        performance_stages: list[dict],
    ) -> dict:
        return {
            "trace_mode": "summary",
            "tick_index": self.tick_index,
            "input": self._summarize_input(input_packet),
            "competition": self._summarize_competition(competition),
            "multimodal": multimodal_trace,
            "education_intervention": self._compact_education_intervention_trace(education_intervention_trace),
            "short_term_echo": self._compact_short_term_echo_trace(short_term_echo_trace),
            "short_term_memory": self._compact_short_term_memory_trace(short_term_memory_trace),
            "state_pool": {
                "r_state": self._summarize_r_state(r_state_fast),
                "query_view_total_count": len(fast_query or []),
                "attention_view_total_count": len(attention_candidates or []),
                "query_view": self._compact_rows(fast_query, limit=self._trace_item_preview_limit()),
                "attention_view": self._compact_rows(attention_candidates, limit=self._trace_item_preview_limit()),
                "snapshot": state_snapshot,
                "energy_flow": dict(state_snapshot.get("energy_flow", {}) or {}),
            },
            "fast_system": {
                "bn": self._compact_bn_rows(fast_bn),
                "cn": fast_cn,
            },
            "attention": {
                **{
                    key: value
                    for key, value in (attention_trace or {}).items()
                    if key not in {"selected_items", "ranked_items"}
                },
                "selected_items": self._compact_rows(
                    (attention_trace or {}).get("selected_items", []), limit=self.config.attention.focus_limit
                ),
                "ranked_items": self._compact_rows(
                    (attention_trace or {}).get("ranked_items", []), limit=self._trace_item_preview_limit()
                ),
            },
            "slow_system": {
                "query": self._compact_rows(slow_query, limit=self._trace_item_preview_limit()),
                "bn_prime": self._compact_bn_rows(slow_bn),
                "cn_prime": slow_cn,
                "focus_continuation": focus_continuation_trace,
                "successor_bias": successor_bias_trace,
                "successor_bias_update": successor_bias_update_trace,
            },
            "cognitive_feelings": feeling_trace,
            "task_feeling": task_feeling_trace,
            "runtime_load_feeling": runtime_load_trace,
            "runtime_budget_controller": runtime_budget_trace,
            "time_feeling": time_trace,
            "rhythm": rhythm_trace,
            "expectation_pressure": expectation_pressure_trace,
            "emotion": {
                "update": emotion_update_trace,
                "modulation": emotion_modulation,
            },
            "innate_rules": self._compact_innate_traces(innate_traces or {}),
            "action": self._compact_action_trace(action_trace),
            "action_feedback": action_feedback_trace,
            "text_output": text_output_trace,
            "thought_view": self._compact_thought_view(thought_view),
            "explainability": self._compact_explainability(explainability),
            "learning": {
                "online_embedding": self.memory.online_embedding_summary(),
                "innate_event_router": dict(innate_learning_router_trace or {}),
                "index_maintenance": index_maintenance_trace,
                "runtime_budget_controller": runtime_budget_trace,
            },
            "performance": {
                "target_tick_ms": float(getattr(self.config.observability, "target_tick_ms", 100) or 100),
                "stages_ms": performance_stages,
                "total_ms": round(sum(float(stage.get("ms", 0.0) or 0.0) for stage in performance_stages), 4),
            },
        }

    def _compact_short_term_echo_trace(self, trace: dict) -> dict:
        row = dict(trace or {})
        row["items"] = self._compact_short_term_echo_items(list(row.get("items", []) or []), limit=8)
        row["items_preview"] = list(row.get("items_preview", []) or [])[:8]
        return row

    def _compact_education_intervention_trace(self, trace: dict) -> dict:
        row = dict(trace or {})
        row["state_items"] = self._compact_rows(list(row.get("state_items", []) or []), limit=6)
        row["action_biases"] = [
            {
                "action_id": str(bias.get("action_id", "") or ""),
                "drive_delta": bias.get("drive_delta", 0.0),
                "params": dict(bias.get("params", {}) or {}),
                "notes": list(bias.get("notes", []) or [])[:8],
                "teacher_kind": str(bias.get("teacher_kind", "") or ""),
            }
            for bias in list(row.get("action_biases", []) or [])[:8]
            if isinstance(bias, dict)
        ]
        row["interventions"] = [
            {
                "source": str(item.get("source", "") or ""),
                "teacher_kind": str(item.get("teacher_kind", "") or ""),
                "goal": str(item.get("goal", "") or ""),
                "state_item_count": len(list(item.get("state_items", []) or [])),
                "action_bias_count": len(list(item.get("action_biases", []) or [])),
                "has_feedback": bool(item.get("feedback", {})),
            }
            for item in list(row.get("interventions", []) or [])[:6]
            if isinstance(item, dict)
        ]
        return row

    def _compact_short_term_memory_trace(self, trace: dict) -> dict:
        row = dict(trace or {})
        row["recent_events"] = list(row.get("recent_events", []) or [])[:8]
        row["observations"] = list(row.get("observations", []) or [])[:8]
        recall = dict(row.get("last_recall", {}) or {})
        if recall:
            recall["selected_events"] = list(recall.get("selected_events", []) or [])[:4]
            recall["selected_items"] = list(recall.get("selected_items", []) or [])[:8]
            recall["candidate_preview"] = list(recall.get("candidate_preview", []) or [])[:6]
        row["last_recall"] = recall if recall else {"available": False}
        return row

    def _compact_short_term_echo_items(self, rows: list[dict], *, limit: int) -> list[dict]:
        """
        Keep echo rows small while preserving what the observatory needs.

        Summary traces normally drop heavy payloads, but short-term echo is a
        readout of recent afterimage/aftersound residue. The observatory cannot
        draw or synthesize that residue unless the bounded echo trace keeps the
        already-state-pool-derived numeric payload and echo provenance. This is
        still trace-only data; it never feeds back into cognition.
        """

        compact = []
        for source in list(rows or [])[: max(1, int(limit))]:
            if not isinstance(source, dict):
                continue
            item = {
                "sa_label": str(source.get("sa_label", "") or ""),
                "display_text": str(source.get("display_text", "") or ""),
                "family": str(source.get("family", "") or ""),
                "source_type": str(source.get("source_type", "") or ""),
                "real_energy": float(source.get("real_energy", 0.0) or 0.0),
                "virtual_energy": float(source.get("virtual_energy", 0.0) or 0.0),
                "cognitive_pressure": float(source.get("cognitive_pressure", 0.0) or 0.0),
            }
            if isinstance(source.get("anchor_meta"), dict):
                item["anchor_meta"] = dict(source.get("anchor_meta", {}) or {})
            if isinstance(source.get("numeric_features"), dict):
                item["numeric_features"] = {
                    str(channel): list(values if isinstance(values, (list, tuple)) else [values])
                    for channel, values in dict(source.get("numeric_features", {}) or {}).items()
                    if str(channel or "")
                }
            if isinstance(source.get("reconstruction_payload"), dict):
                item["reconstruction_payload"] = dict(source.get("reconstruction_payload", {}) or {})
            compact.append(item)
        return compact

    def process_idle_maintenance(
        self, *, include_heavy: bool = True, budget: int | None = None, max_ms: float | None = None
    ) -> dict:
        """
        Run non-realtime maintenance under an explicit budget.

        Use this from empty/idle windows, experiments, or future observatory
        buttons. It is deliberately not hidden inside the cognitive tick.
        """

        explicit_budget = budget is not None or max_ms is not None
        if include_heavy and explicit_budget:
            trace = self.memory.process_idle_index_maintenance(
                budget=self.config.memory.idle_heavy_index_jobs if budget is None else budget,
                max_ms=self.config.memory.idle_index_maintenance_max_ms if max_ms is None else max_ms,
            )
            trace["runtime_budget"] = {
                "schema_id": "runtime_index_budget/v1",
                "policy": "explicit_idle_budget_not_modulated",
                "jobs_per_tick": int(self.config.memory.idle_heavy_index_jobs if budget is None else budget),
                "max_ms": float(self.config.memory.idle_index_maintenance_max_ms if max_ms is None else max_ms),
            }
        elif include_heavy:
            budget_trace = self.runtime_budget_controller.index_budget(
                base_jobs=self.config.memory.idle_heavy_index_jobs if budget is None else budget,
                base_min_remaining_ms=0.0,
                base_max_ms=self.config.memory.idle_index_maintenance_max_ms if max_ms is None else max_ms,
            )
            trace = self.memory.process_idle_index_maintenance(
                budget=int(budget_trace["jobs_per_tick"]),
                max_ms=float(budget_trace["max_ms"]),
            )
            trace["runtime_budget"] = budget_trace
        elif explicit_budget:
            trace = self.memory.process_pending_index_jobs(
                self.config.memory.index_jobs_per_tick if budget is None else budget,
                max_ms=self.config.memory.index_maintenance_max_ms if max_ms is None else max_ms,
                include_heavy=False,
            )
            trace["policy"] = "idle_light_index_maintenance"
            trace["runtime_budget"] = {
                "schema_id": "runtime_index_budget/v1",
                "policy": "explicit_idle_budget_not_modulated",
                "jobs_per_tick": int(self.config.memory.index_jobs_per_tick if budget is None else budget),
                "max_ms": float(self.config.memory.index_maintenance_max_ms if max_ms is None else max_ms),
            }
        else:
            budget_trace = self.runtime_budget_controller.index_budget(
                base_jobs=self.config.memory.index_jobs_per_tick if budget is None else budget,
                base_min_remaining_ms=0.0,
                base_max_ms=self.config.memory.index_maintenance_max_ms if max_ms is None else max_ms,
            )
            trace = self.memory.process_pending_index_jobs(
                int(budget_trace["jobs_per_tick"]),
                max_ms=float(budget_trace["max_ms"]),
                include_heavy=False,
            )
            trace["policy"] = "idle_light_index_maintenance"
            trace["runtime_budget"] = budget_trace
        if bool(self.config.observability.disable_gc_during_tick):
            generation = max(0, int(self.config.observability.idle_gc_collect_generation))
            gc_started = perf_counter()
            trace["gc_collected"] = int(gc.collect(generation))
            trace["gc_ms"] = round((perf_counter() - gc_started) * 1000.0, 4)
        return trace

    def _summarize_input(self, input_packet: dict) -> dict:
        packet = dict(input_packet or {})
        units = list(packet.get("units", []) or [])
        packet["units"] = self._compact_rows(units, limit=self._trace_item_preview_limit())
        sa_items = list(packet.get("sa_items", []) or [])
        packet["sa_item_count"] = int(packet.get("sa_item_count", len(sa_items)) or 0)
        if sa_items:
            packet["sa_items"] = self._compact_rows(sa_items, limit=self._trace_item_preview_limit())
        text = str(packet.get("normalized_text", "") or "")
        max_chars = max(32, int(self.config.observability.trace_text_preview_chars))
        if len(text) > max_chars:
            packet["normalized_text_preview"] = text[:max_chars]
            packet["normalized_text_length"] = len(text)
            packet["normalized_text"] = text[:max_chars]
        packet["unit_count"] = len(units)
        return packet

    def _summarize_competition(self, competition: dict) -> dict:
        row = dict(competition or {})
        selected = list(row.get("selected_items", []) or [])
        row["selected_items"] = self._compact_rows(selected, limit=self._trace_item_preview_limit())
        row["selected_count"] = len(selected)
        return row

    def _summarize_r_state(self, r_state: dict) -> dict:
        source = dict(r_state or {})
        item_limit = max(1, int(self._trace_r_state_item_preview_limit()))
        heads = []
        total_items = 0
        for head in source.get("heads", []) or []:
            items = list((head or {}).get("items", []) or [])
            total_items += len(items)
            heads.append(
                {
                    "head_id": str((head or {}).get("head_id", "") or ""),
                    "item_count": len(items),
                    "items": self._compact_rows(items, limit=item_limit),
                }
            )
        source["heads"] = heads
        source["total_head_item_count"] = total_items
        return source

    def _compact_rows(self, rows: list[dict], *, limit: int) -> list[dict]:
        compact = []
        for row in list(rows or [])[: max(1, int(limit))]:
            if not isinstance(row, dict):
                continue
            item = {
                "sa_label": str(row.get("sa_label", "") or ""),
                "display_text": str(row.get("display_text", "") or ""),
                "family": str(row.get("family", "") or ""),
                "source_type": str(row.get("source_type", "") or ""),
                "real_energy": float(row.get("real_energy", 0.0) or 0.0),
                "virtual_energy": float(row.get("virtual_energy", 0.0) or 0.0),
                "cognitive_pressure": float(row.get("cognitive_pressure", 0.0) or 0.0),
            }
            for key in (
                "query_weight",
                "attention_score",
                "focus_score",
                "continuation_bonus",
                "successor_bias",
                "emotion_multiplier",
                "focus_order_index",
                "focus_family_bucket",
                "focus_family_budget_relaxed",
                "action_attention_boost",
                "action_attention_suppression",
                "action_attention_net_bias",
            ):
                if key in row:
                    item[key] = row.get(key)
            if "action_attention_sources" in row:
                item["action_attention_sources"] = list(row.get("action_attention_sources", []) or [])[:4]
            if "query_sources" in row:
                item["query_sources"] = list(row.get("query_sources", []) or [])[:4]
            compact.append(item)
        return compact

    def _compact_focus_continuation_trace(self, trace: dict) -> dict:
        row = dict(trace or {})
        row["current_labels"] = list(row.get("current_labels", []) or [])[: self.config.attention.focus_limit]
        row["recent_entries"] = list(row.get("recent_entries", []) or [])[-4:]
        row["replay_candidates"] = list(row.get("replay_candidates", []) or [])[:4]
        return row

    def _compact_bn_rows(self, rows: list[dict]) -> list[dict]:
        return [self._compact_bn_row(row) for row in list(rows or [])]

    def _compact_bn_row(self, row: dict) -> dict:
        matched = dict((row or {}).get("matched_tokens", {}) or {})
        token_limit = max(1, int(self._trace_matched_token_preview_limit()))
        return {
            "memory_id": str((row or {}).get("memory_id", "") or ""),
            "tick_index": int((row or {}).get("tick_index", -1) or -1),
            "memory_kind": str((row or {}).get("memory_kind", "") or ""),
            "score": float((row or {}).get("score", 0.0) or 0.0),
            "normalized_weight": float((row or {}).get("normalized_weight", 0.0) or 0.0),
            "match_efficiency": float((row or {}).get("match_efficiency", 0.0) or 0.0),
            "grasp_confidence": float((row or {}).get("grasp_confidence", 0.0) or 0.0),
            "b_real_energy": float((row or {}).get("b_real_energy", 0.0) or 0.0),
            "b_virtual_energy": float((row or {}).get("b_virtual_energy", 0.0) or 0.0),
            "b_effective_real_energy": float((row or {}).get("b_effective_real_energy", 0.0) or 0.0),
            "b_effective_virtual_energy": float((row or {}).get("b_effective_virtual_energy", 0.0) or 0.0),
            "energy_transfer": dict((row or {}).get("energy_transfer", {}) or {}),
            "source_text": str((row or {}).get("source_text", "") or ""),
            "snapshot_ref": dict((row or {}).get("snapshot_ref", {}) or {}),
            "snapshot_preview": dict((row or {}).get("snapshot_preview", {}) or {}),
            "candidate_sources": list((row or {}).get("candidate_sources", []) or []),
            "matched_tokens": {key: list(value or [])[:token_limit] for key, value in matched.items()},
            "score_breakdown": dict((row or {}).get("score_breakdown", {}) or {}),
            "relative_relation_score": float((row or {}).get("relative_relation_score", 0.0) or 0.0),
            "relative_relation_raw_score": float((row or {}).get("relative_relation_raw_score", 0.0) or 0.0),
            "relation_channels": dict((row or {}).get("relation_channels", {}) or {}),
            "relation_matches": list((row or {}).get("relation_matches", []) or [])[:6],
            "learned_score": float((row or {}).get("learned_score", 0.0) or 0.0),
            "learned_contributions": list((row or {}).get("learned_contributions", []) or [])[:6],
        }

    def _compact_thought_view(self, thought_view: dict) -> dict:
        row = dict(thought_view or {})
        if "fast" in row:
            fast = dict(row.get("fast", {}) or {})
            fast["bn"] = self._compact_bn_rows(fast.get("bn", []))
            row["fast"] = fast
        if "slow" in row:
            slow = dict(row.get("slow", {}) or {})
            slow["bn_prime"] = self._compact_bn_rows(slow.get("bn_prime", []))
            row["slow"] = slow
        focus = dict(row.get("focus_reason", {}) or {})
        if focus:
            focus["ranked_items"] = self._compact_rows(focus.get("ranked_items", []), limit=5)
            row["focus_reason"] = focus
        return row

    def _compact_explainability(self, explainability: dict) -> dict:
        row = dict(explainability or {})
        row["fast_bn"] = [self._compact_bn_reason(item) for item in list(row.get("fast_bn", []) or [])]
        row["slow_bn"] = [self._compact_bn_reason(item) for item in list(row.get("slow_bn", []) or [])]
        focus = dict(row.get("focus", {}) or {})
        if focus:
            focus["ranked_items"] = self._compact_rows(focus.get("ranked_items", []), limit=6)
            row["focus"] = focus
        return row

    def _compact_bn_reason(self, row: dict) -> dict:
        matched = dict((row or {}).get("matched_tokens", {}) or {})
        token_limit = max(1, int(self._trace_matched_token_preview_limit()))
        compact = dict(row or {})
        compact["matched_tokens"] = {key: list(value or [])[:token_limit] for key, value in matched.items()}
        return compact

    def _compact_action_trace(self, action_trace: dict) -> dict:
        row = dict(action_trace or {})
        row["candidates"] = list(row.get("candidates", []) or [])[:8]
        return row

    def _compact_innate_traces(self, traces: dict | None) -> dict:
        result = {
            "schema_id": "innate_runtime_trace/v1",
            "enabled": bool(self.config.innate_rules.enabled),
            "validation": self.innate_engine.validate(),
            "actuator_registry": self.innate_engine.actuator_registry(),
            "action_registry": self.innate_engine.action_registry(),
            "phases": {},
            "phase_order": [],
            "total_hit_count": 0,
            "learning_events": [],
        }
        for phase, trace in dict(traces or {}).items():
            row = dict(trace or {})
            compact = {
                "schema_id": row.get("schema_id", "innate_phase_trace/v1"),
                "enabled": bool(row.get("enabled", True)),
                "phase": str(row.get("phase", phase) or phase),
                "rule_count": int(row.get("rule_count", 0) or 0),
                "hit_count": int(row.get("hit_count", 0) or 0),
                "hits": list(row.get("hits", []) or [])[:8],
                "suppressed": list(row.get("suppressed", []) or [])[:6],
                "items": list(row.get("items", []) or [])[:8],
                "action_nodes": list(row.get("action_nodes", []) or [])[:8],
                "action_biases": list(row.get("action_biases", []) or [])[:8],
                "emotion_deltas": dict(row.get("emotion_deltas", {}) or {}),
                "learning_events": list(row.get("learning_events", []) or [])[:8],
                "attention_biases": list(row.get("attention_biases", []) or [])[:6],
                "safety_gate": list(row.get("safety_gate", []) or [])[:6],
                "metrics": dict(row.get("metrics", {}) or {}),
                "fatigue": dict(row.get("fatigue", {}) or {}),
            }
            result["phases"][phase] = compact
            result["phase_order"].append(phase)
            result["total_hit_count"] += int(compact["hit_count"])
            result["learning_events"].extend(list(compact.get("learning_events", []) or []))
        result["learning_events"] = result["learning_events"][:16]
        return result

    def _r_state_to_attention_candidates(self, r_state: dict) -> list[dict]:
        """
        Fixed-budget attention candidate set.

        We intentionally do not scan the full pool here; we reuse the `R_state` heads
        as the bounded candidate set for attention selection.
        """

        merged: dict[str, dict] = {}
        for head in r_state.get("heads", []) or []:
            for row in head.get("items", []) or []:
                label = str((row or {}).get("sa_label", "") or "")
                if not label:
                    continue
                existing = merged.get(label)
                if existing is None:
                    merged[label] = dict(row)
                    continue
                existing["attention_score"] = max(
                    float(existing.get("attention_score", 0.0) or 0.0), float(row.get("attention_score", 0.0) or 0.0)
                )
                existing["query_weight"] = max(
                    float(existing.get("query_weight", 0.0) or 0.0), float(row.get("query_weight", 0.0) or 0.0)
                )
                existing["real_energy"] = max(
                    float(existing.get("real_energy", 0.0) or 0.0), float(row.get("real_energy", 0.0) or 0.0)
                )
                existing["virtual_energy"] = max(
                    float(existing.get("virtual_energy", 0.0) or 0.0), float(row.get("virtual_energy", 0.0) or 0.0)
                )
        rows = list(merged.values())
        base_limit = max(
            self.config.attention.focus_limit * 8, self.config.observability.trace_item_preview_limit * 2, 64
        )
        attention_budget = self.runtime_budget_controller.attention_candidate_limit(base_limit=base_limit)
        limit = max(self.config.attention.focus_limit, int(attention_budget["limit"]))
        r_state.setdefault("runtime_budget", {})
        r_state["runtime_budget"]["attention_candidate_budget"] = attention_budget
        if len(rows) <= limit:
            rows.sort(
                key=lambda item: (
                    -float(item.get("attention_score", 0.0) or 0.0),
                    -float(item.get("query_weight", 0.0) or 0.0),
                    str(item.get("sa_label", "") or ""),
                )
            )
            return rows
        return nsmallest(
            limit,
            rows,
            key=lambda item: (
                -float(item.get("attention_score", 0.0) or 0.0),
                -float(item.get("query_weight", 0.0) or 0.0),
                str(item.get("sa_label", "") or ""),
            ),
        )

    def _shape_focus_family_budget(
        self, *, ranked_items: list[dict], raw_selected_items: list[dict], action_modulation: dict | None = None
    ) -> tuple[list[dict], dict]:
        """
        Shape the finite focus-memory window without mutating state-pool energy.

        Raw attention still decides the score order. This helper only prevents a
        single SA family from occupying the whole slow-system focus window when
        there are other credible ranked candidates available.
        """

        focus_limit = max(1, int(self.config.attention.focus_limit))
        raw_selected = [dict(item) for item in list(raw_selected_items or []) if isinstance(item, dict)]
        if not bool(getattr(self.config.attention, "focus_family_budget_enabled", True)):
            labels = [
                str(item.get("sa_label", "") or "") for item in raw_selected if str(item.get("sa_label", "") or "")
            ]
            return raw_selected[:focus_limit], {
                "schema_id": "focus_family_budget_trace/v1",
                "enabled": False,
                "policy": "disabled_raw_attention_window",
                "focus_limit": int(focus_limit),
                "raw_selected_labels": labels[:focus_limit],
                "balanced_selected_labels": labels[:focus_limit],
                "family_counts": {},
                "family_caps": {},
                "overflow_count": 0,
                "overflow_preview": [],
                "relaxed_fill_count": 0,
            }

        ranked = [dict(item) for item in list(ranked_items or []) if isinstance(item, dict)]
        if not ranked:
            ranked = raw_selected
        family_caps = self._modulated_focus_family_caps(self._focus_family_caps(), action_modulation or {})
        selected: list[dict] = []
        selected_labels: set[str] = set()
        family_counts: dict[str, int] = {}
        overflow: list[dict] = []
        overflow_count = 0

        for item in ranked:
            if len(selected) >= focus_limit:
                break
            label = str(item.get("sa_label", "") or "")
            if not label or label in selected_labels:
                continue
            bucket = self._focus_family_bucket(item)
            cap = max(0, int(family_caps.get(bucket, family_caps.get("other", focus_limit)) or 0))
            count = int(family_counts.get(bucket, 0) or 0)
            if count >= cap:
                overflow_count += 1
                if len(overflow) < max(8, focus_limit * 2):
                    overflow.append(self._focus_family_overflow_row(item, bucket, reason="family_cap"))
                continue
            enriched = dict(item)
            enriched["focus_family_bucket"] = bucket
            selected.append(enriched)
            selected_labels.add(label)
            family_counts[bucket] = count + 1

        relaxed_fill_count = 0
        if len(selected) < focus_limit:
            for item in ranked:
                if len(selected) >= focus_limit:
                    break
                label = str(item.get("sa_label", "") or "")
                if not label or label in selected_labels:
                    continue
                bucket = self._focus_family_bucket(item)
                enriched = dict(item)
                enriched["focus_family_bucket"] = bucket
                enriched["focus_family_budget_relaxed"] = True
                selected.append(enriched)
                selected_labels.add(label)
                family_counts[bucket] = int(family_counts.get(bucket, 0) or 0) + 1
                relaxed_fill_count += 1

        raw_labels = [
            str(item.get("sa_label", "") or "") for item in raw_selected if str(item.get("sa_label", "") or "")
        ]
        balanced_labels = [
            str(item.get("sa_label", "") or "") for item in selected if str(item.get("sa_label", "") or "")
        ]
        return selected, {
            "schema_id": "focus_family_budget_trace/v1",
            "enabled": True,
            "policy": "ranked_attention_then_family_caps_no_energy_mutation",
            "focus_limit": int(focus_limit),
            "raw_selected_labels": raw_labels[:focus_limit],
            "balanced_selected_labels": balanced_labels,
            "family_counts": {key: int(value) for key, value in sorted(family_counts.items())},
            "family_caps": {key: int(value) for key, value in sorted(family_caps.items())},
            "action_modulation": dict(action_modulation or {}),
            "overflow_count": int(overflow_count),
            "overflow_preview": overflow[: max(1, min(8, focus_limit))],
            "relaxed_fill_count": int(relaxed_fill_count),
            "changed": raw_labels[:focus_limit] != balanced_labels,
        }

    def _focus_family_caps(self) -> dict[str, int]:
        cfg = self.config.attention
        focus_limit = max(1, int(getattr(cfg, "focus_limit", 8) or 8))

        def cap(name: str, fallback: int) -> int:
            return max(0, min(focus_limit, int(getattr(cfg, name, fallback) or 0)))

        return {
            "text": cap("focus_family_text_max", 4),
            "vision": cap("focus_family_vision_max", 3),
            "audio": cap("focus_family_audio_max", 3),
            "cognitive_feeling": cap("focus_family_cognitive_feeling_max", 2),
            "emotion": cap("focus_family_emotion_max", 2),
            "action": cap("focus_family_action_max", 2),
            "time": cap("focus_family_time_max", 1),
            "rhythm": cap("focus_family_rhythm_max", 1),
            "expectation_pressure": cap("focus_family_expectation_pressure_max", 2),
            "other": cap("focus_family_other_max", 2),
        }

    def _modulated_focus_family_caps(self, family_caps: dict[str, int], action_modulation: dict) -> dict[str, int]:
        caps = {str(key): int(value) for key, value in dict(family_caps or {}).items()}
        if not action_modulation:
            return caps
        focus_limit = max(1, int(getattr(self.config.attention, "focus_limit", 8) or 8))
        diversity_gain = max(0.0, float(action_modulation.get("diversity_gain", 0.0) or 0.0))
        release_labels = {
            str(label or "") for label in list(action_modulation.get("release_labels", []) or []) if str(label or "")
        }
        if diversity_gain > 0.0:
            for key in ("text", "vision", "audio", "other", "cognitive_feeling", "expectation_pressure"):
                caps[key] = min(focus_limit, max(int(caps.get(key, 0) or 0), int(caps.get(key, 0) or 0) + 1))
        if release_labels:
            # A release action is a short-lived anti-lock control. It should not
            # delete the old family, only prevent it from filling the whole
            # finite focus window while the system tries another angle.
            release_buckets = {self._focus_family_bucket({"sa_label": label}) for label in release_labels}
            for bucket in release_buckets:
                if bucket in caps:
                    caps[bucket] = max(1, min(int(caps[bucket]), max(1, focus_limit - 1)))
        return caps

    def _focus_family_overflow_row(self, item: dict, bucket: str, *, reason: str) -> dict:
        return {
            "sa_label": str((item or {}).get("sa_label", "") or ""),
            "display_text": str((item or {}).get("display_text", "") or ""),
            "focus_family_bucket": str(bucket or "other"),
            "focus_score": float((item or {}).get("focus_score", 0.0) or 0.0),
            "real_energy": float((item or {}).get("real_energy", 0.0) or 0.0),
            "virtual_energy": float((item or {}).get("virtual_energy", 0.0) or 0.0),
            "reason": str(reason or "family_cap"),
        }

    def _focus_family_bucket(self, item: dict) -> str:
        label = str((item or {}).get("sa_label", "") or "").lower()
        family = str((item or {}).get("family", "") or "").lower()
        source_type = str((item or {}).get("source_type", "") or "").lower()
        prefixes = (label, family, source_type)
        if label.startswith("expectation_pressure::") or "expectation_pressure" in prefixes:
            return "expectation_pressure"
        if label.startswith("action::") or label.startswith("action_feedback::") or label.startswith("text_action::"):
            return "action"
        if family in {"action", "action_feedback", "text_action"} or source_type in {
            "action",
            "action_feedback",
            "text_action",
        }:
            return "action"
        if label.startswith("emotion::") or family == "emotion" or source_type == "emotion":
            return "emotion"
        if label.startswith("feeling::") or family == "cognitive_feeling" or source_type == "cognitive_feeling":
            return "cognitive_feeling"
        if (
            label.startswith("timefelt::")
            or family in {"time", "time_feeling"}
            or source_type in {"time", "time_feeling"}
        ):
            return "time"
        if label.startswith("rhythmfelt::") or family == "rhythm" or source_type == "rhythm":
            return "rhythm"
        if (
            label.startswith(("audio::", "sound::", "hearing::"))
            or family.startswith(("audio", "hearing"))
            or source_type.startswith(("audio", "hearing"))
        ):
            return "audio"
        if (
            label.startswith(("vision::", "visual::", "image::"))
            or family.startswith(("vision", "visual", "image"))
            or source_type.startswith(("vision", "visual", "image"))
        ):
            return "vision"
        if (
            label.startswith(("text::", "phrase::"))
            or family in {"text", "learned_text_phrase", "text_phrase"}
            or source_type == "external_text"
        ):
            return "text"
        return "other"

    def _stabilize_focus_order(self, selected_items: list[dict]) -> tuple[list[dict], dict]:
        """
        Keep attention winners, but order the focus window for slow-system memory.

        Attention decides *which* objects enter focus. This helper only decides
        how ordered external evidence is written into focus memory, so text
        sequence statistics do not depend on score tie-breaks.
        """

        rows = []
        for rank, item in enumerate(selected_items or []):
            if not isinstance(item, dict):
                continue
            label = str(item.get("sa_label", "") or "")
            if not label:
                continue
            row = dict(item)
            rows.append(
                {
                    "rank": int(rank),
                    "item": row,
                    "label": label,
                    "is_orderable_text": self._is_orderable_text_focus_item(row),
                    "source_key": self._focus_source_order_key(row, default_rank=rank),
                }
            )
        if not rows:
            return [], {
                "schema_id": "focus_order_trace/v1",
                "policy": "empty",
                "raw_attention_labels": [],
                "ordered_focus_labels": [],
                "text_ordered_count": 0,
                "non_text_count": 0,
                "changed": False,
            }

        orderable_count = sum(1 for row in rows if bool(row.get("is_orderable_text", False)))
        should_reorder_text = orderable_count >= 2
        if should_reorder_text:
            ordered_text_rows = sorted(
                [row for row in rows if bool(row.get("is_orderable_text", False))],
                key=lambda row: (
                    row.get("source_key", (0, int(row.get("rank", 0) or 0))),
                    int(row.get("rank", 0) or 0),
                ),
            )
            text_iter = iter(ordered_text_rows)
            ordered_rows = [next(text_iter) if bool(row.get("is_orderable_text", False)) else row for row in rows]
            policy = "orderable_external_text_relative_order_only"
        else:
            ordered_rows = list(rows)
            policy = "attention_rank_preserved_no_comparable_text_order"

        ordered_items = [dict(row["item"]) for row in ordered_rows]
        raw_labels = [str(row.get("label", "") or "") for row in rows]
        ordered_labels = [str(row.get("label", "") or "") for row in ordered_rows]
        for order_index, item in enumerate(ordered_items):
            anchor_meta = (
                dict(item.get("anchor_meta", {}) or {}) if isinstance(item.get("anchor_meta", {}), dict) else {}
            )
            anchor_meta["focus_order_index"] = int(order_index)
            item["anchor_meta"] = anchor_meta
            item["focus_order_index"] = int(order_index)
        return ordered_items, {
            "schema_id": "focus_order_trace/v1",
            "policy": policy,
            "raw_attention_labels": raw_labels,
            "ordered_focus_labels": ordered_labels,
            "text_ordered_count": int(orderable_count),
            "non_text_count": int(len(rows) - orderable_count),
            "changed": raw_labels != ordered_labels,
        }

    def _is_orderable_text_focus_item(self, item: dict) -> bool:
        label = str((item or {}).get("sa_label", "") or "")
        if not label.startswith(("text::", "phrase::")):
            return False
        source_type = str((item or {}).get("source_type", "") or "")
        family = str((item or {}).get("family", "") or "")
        return source_type == "external_text" or family in {"text", "learned_text_phrase", "text_phrase"}

    def _focus_source_order_key(self, item: dict, *, default_rank: int) -> tuple[int, int, int]:
        anchor_meta = (
            dict((item or {}).get("anchor_meta", {}) or {})
            if isinstance((item or {}).get("anchor_meta", {}), dict)
            else {}
        )
        tick_value = (item or {}).get(
            "last_seen_tick", (item or {}).get("tick_index", anchor_meta.get("tick_index", self.tick_index))
        )
        position_value = (item or {}).get("position", anchor_meta.get("position", default_rank))
        try:
            tick_key = int(tick_value)
        except (TypeError, ValueError):
            tick_key = int(self.tick_index)
        try:
            position_key = int(position_value)
        except (TypeError, ValueError):
            position_key = int(default_rank)
        return (tick_key, position_key, int(default_rank))

    def _append_r_state_head(self, r_state: dict, head_id: str, rows: list[dict]) -> dict:
        updated = dict(r_state or {})
        heads = list(updated.get("heads", []) or [])
        if rows:
            heads.append({"head_id": str(head_id or "head_incremental"), "items": list(rows)})
        updated["heads"] = heads
        updated["head_count"] = len(heads)
        available = list(updated.get("available_head_ids", []) or [])
        if head_id not in available:
            available.append(str(head_id or "head_incremental"))
        updated["available_head_ids"] = available
        preview = list(updated.get("merged_preview", []) or [])
        seen = {str(label or "") for label in preview if str(label or "")}
        for row in rows:
            label = str((row or {}).get("sa_label", "") or "")
            if label and label not in seen:
                seen.add(label)
                preview.append(label)
        updated["merged_preview"] = preview
        return updated

    def _should_rerun_timefelt_recall(self, time_trace: dict) -> bool:
        dominant = dict((time_trace or {}).get("dominant_peak", {}) or {})
        confidence = float(dominant.get("confidence", 0.0) or 0.0)
        max_energy = max(
            [float(item.get("real_energy", 0.0) or 0.0) for item in (time_trace or {}).get("items", []) or []] or [0.0]
        )
        return confidence >= float(self.config.time_feeling.rerun_recall_confidence_threshold) and max_energy >= float(
            self.config.time_feeling.rerun_recall_energy_threshold
        )

    def _ingest_text(self, text: str) -> tuple[dict, dict, list[dict]]:
        input_packet = self.text_sensor.ingest(text, tick_index=self.tick_index)
        self.sa_registry.observe_sequence(input_packet["units"])
        cache_key = (
            str(input_packet.get("normalized_text", "") or ""),
            str(input_packet.get("source_type", "") or ""),
            int(self.config.text_sensor.competition_limit),
            int(self.config.text_sensor.budget_limit),
        )
        cached = self._text_ingest_cache.get(cache_key)
        if cached is not None:
            selected_template = list(cached.get("selected_items", []) or [])
            competition = {
                "selected_items": [dict(item) for item in selected_template],
                "cache": {"hit": True, "kind": "text_competition_template"},
            }
        else:
            competition = self.sa_registry.compete(
                input_packet["units"],
                source_type=input_packet["source_type"],
                max_items=self.config.text_sensor.competition_limit,
            )
            selected_template = [dict(item) for item in list(competition.get("selected_items", []) or [])]
            self._text_ingest_cache[cache_key] = {"selected_items": selected_template}
            if len(self._text_ingest_cache) > 8:
                first_key = next(iter(self._text_ingest_cache))
                self._text_ingest_cache.pop(first_key, None)
            competition = dict(competition)
            competition["cache"] = {"hit": False, "kind": "text_competition_template"}
        external_items = list(competition.get("selected_items", []) or [])
        return input_packet, competition, external_items

    def _ingest_multimodal(
        self, *, text: str, image_bytes: bytes | None, audio_bytes: bytes | None
    ) -> tuple[dict, dict, list[dict], dict]:
        input_packet, competition, external_items = self._ingest_text(text)
        multimodal_trace = {
            "inner_vision": {},
            "inner_audio": {},
            "asset_refs": [],
            "ingested_modalities": [],
        }
        if image_bytes:
            vision_trace = self._ingest_vision_bytes(image_bytes)
            vision_trace = self._register_vision_assets(vision_trace, raw_image_bytes=image_bytes)
            vision_trace = self._strip_raw_multimodal_preview_payloads(vision_trace, modality="vision")
            external_items.extend(vision_trace["state_items"])
            multimodal_trace["inner_vision"] = vision_trace["inner_vision"]
            multimodal_trace["asset_refs"].extend(list(vision_trace.get("asset_refs", []) or []))
            multimodal_trace["ingested_modalities"].append("vision")
        if audio_bytes:
            audio_trace = self._ingest_audio_bytes(audio_bytes)
            audio_trace = self._register_audio_assets(audio_trace, raw_audio_bytes=audio_bytes)
            audio_trace = self._strip_raw_multimodal_preview_payloads(audio_trace, modality="audio")
            external_items.extend(audio_trace["state_items"])
            multimodal_trace["inner_audio"] = audio_trace["inner_audio"]
            multimodal_trace["asset_refs"].extend(list(audio_trace.get("asset_refs", []) or []))
            multimodal_trace["ingested_modalities"].append("audio")
        if text:
            multimodal_trace["ingested_modalities"].append("text")
        multimodal_trace["asset_refs"] = self._dedupe_asset_refs(multimodal_trace.get("asset_refs", []))
        if multimodal_trace["asset_refs"]:
            multimodal_trace["asset_store"] = self.asset_store.summary()
        return input_packet, competition, external_items, multimodal_trace

    def _strip_raw_multimodal_preview_payloads(self, trace: dict, *, modality: str) -> dict:
        result = dict(trace or {})
        if modality == "vision":
            inner = dict(result.get("inner_vision", {}) or {})
            current_frame = dict(inner.get("current_frame", {}) or {})
            current_frame.pop("preview_png_b64", None)
            current_frame.setdefault("reconstruction_basis", "state_pool_numeric_channels")
            current_frame["raw_preview_payload"] = False
            inner["current_frame"] = current_frame
            if not bool(self.config.multimodal_assets.enabled):
                inner.pop("asset_refs", None)
                for key in ("asset_ref", "raw_asset_ref"):
                    current_frame.pop(key, None)
                inner["current_frame"] = current_frame
                objects = []
                for obj in list(inner.get("object_reconstruction", []) or []):
                    if not isinstance(obj, dict):
                        continue
                    row = dict(obj)
                    row.pop("asset_ref", None)
                    row.pop("focus_tile_asset_ref", None)
                    objects.append(row)
                inner["object_reconstruction"] = objects
                result["asset_refs"] = []
            result["inner_vision"] = inner
            return result
        if modality == "audio":
            inner = dict(result.get("inner_audio", {}) or {})
            preview = dict(inner.get("preview_asset_ref", {}) or {})
            preview.pop("preview_wav_b64", None)
            preview.pop("proxy_preview_wav_b64", None)
            preview.setdefault("reconstruction_basis", "state_pool_numeric_channels")
            preview["raw_preview_payload"] = False
            if not bool(self.config.multimodal_assets.enabled):
                for key in ("asset_ref", "feature_asset_ref", "focus_window_asset_ref"):
                    preview.pop(key, None)
                inner.pop("asset_refs", None)
                result["asset_refs"] = []
            inner["preview_asset_ref"] = preview
            result["inner_audio"] = inner
            return result
        return result

    def _ingest_vision_bytes(self, image_bytes: bytes) -> dict:
        mode = str(self.config.vision_sensor.mode or "native_numeric").strip().lower()
        if mode in {"native", "native_numeric", "numeric"}:
            try:
                trace = self.vision_sensor.ingest_image_bytes(
                    image_bytes,
                    tick_index=self.tick_index,
                    focus_state=self.visual_gaze_actuator.state(),
                )
                trace.setdefault("packet", {})["sensor_mode"] = "native_numeric"
                return trace
            except Exception as exc:
                if not self.config.vision_sensor.fallback_to_legacy:
                    raise
                legacy = self.vision_bridge.ingest_image_bytes(image_bytes, tick_index=self.tick_index)
                legacy.setdefault("packet", {})["sensor_mode"] = "legacy_fallback"
                legacy.setdefault("inner_vision", {})["fallback_reason"] = f"{type(exc).__name__}: {exc}"
                return legacy
        legacy = self.vision_bridge.ingest_image_bytes(image_bytes, tick_index=self.tick_index)
        legacy.setdefault("packet", {})["sensor_mode"] = "legacy_bridge"
        return legacy

    def _ingest_audio_bytes(self, audio_bytes: bytes) -> dict:
        mode = str(self.config.audio_sensor.mode or "native_numeric").strip().lower()
        if mode in {"native", "native_numeric", "numeric"}:
            try:
                trace = self.audio_sensor.ingest_wav_bytes(
                    audio_bytes,
                    tick_index=self.tick_index,
                    focus_state=self.auditory_band_actuator.state(),
                )
                trace.setdefault("packet", {})["sensor_mode"] = "native_numeric"
                return trace
            except Exception as exc:
                if not self.config.audio_sensor.fallback_to_legacy:
                    raise
                legacy = self.audio_bridge.ingest_wav_bytes(audio_bytes, tick_index=self.tick_index)
                legacy.setdefault("packet", {})["sensor_mode"] = "legacy_fallback"
                legacy.setdefault("inner_audio", {})["fallback_reason"] = f"{type(exc).__name__}: {exc}"
                return legacy
        legacy = self.audio_bridge.ingest_wav_bytes(audio_bytes, tick_index=self.tick_index)
        legacy.setdefault("packet", {})["sensor_mode"] = "legacy_bridge"
        return legacy

    def _register_vision_assets(self, trace: dict, *, raw_image_bytes: bytes | None = None) -> dict:
        # APV2.1 inner replay must be reconstructed from state-pool numeric SA
        # channels. Raw/near-raw visual assets are intentionally hard-disabled so
        # future observatory work cannot fall back to replaying input media.
        return trace

    def _register_audio_assets(self, trace: dict, *, raw_audio_bytes: bytes | None = None) -> dict:
        # APV2.1 inner replay must be reconstructed from state-pool numeric SA
        # channels. Raw/near-raw audio assets are intentionally hard-disabled so
        # future observatory work cannot fall back to replaying input media.
        return trace

    def _dedupe_asset_refs(self, refs: list[dict]) -> list[dict]:
        rows = []
        seen = set()
        for ref in refs or []:
            if not isinstance(ref, dict):
                continue
            asset_id = str(ref.get("asset_id", "") or "")
            if not asset_id or asset_id in seen:
                continue
            seen.add(asset_id)
            rows.append(dict(ref))
        return rows

    def _apply_external_or_bootstrap(self, external_items: list[dict], *, memory_bootstrap: bool) -> None:
        if external_items:
            self.state_pool.apply_external_items(external_items, tick_index=self.tick_index)
            return
        if memory_bootstrap and self.config.allow_memory_bootstrap:
            latest = self.memory.latest_snapshot("state")
            if latest is not None:
                self.state_pool.apply_memory_bootstrap(latest, tick_index=self.tick_index)

    def _consume_pending_action_feedback(self) -> dict:
        pending = dict(self._pending_action_feedback or {})
        self._pending_action_feedback = None
        if not pending:
            queued_feedback = self._consume_queued_external_feedback()
            if queued_feedback:
                feedback_items = self._build_explicit_feedback_items(queued_feedback)
                structured_events = self._structured_action_outcome_events(
                    selected_actions=[],
                    observed_feedback=queued_feedback,
                    planner_feedback={},
                    parameter_events=[],
                )
                return {
                    "applied": True,
                    "selected_actions": [],
                    "observed_feedback": queued_feedback,
                    "planner_feedback": {},
                    "causal_window": {},
                    "feedback_items": feedback_items,
                    "structured_learning_events": structured_events,
                    "source": "external_feedback_queue",
                }
            return {
                "applied": False,
                "selected_actions": [],
                "observed_feedback": {},
                "feedback_items": [],
                "structured_learning_events": [],
            }
        selected_actions = list(pending.get("selected_actions", []) or [])
        feedback_context = dict(pending.get("feedback_context", {}) or {})
        causal_window = dict(pending.get("causal_window", {}) or {})
        observed_feedback = self._observe_action_feedback(
            selected_actions=selected_actions, feedback_context=feedback_context
        )
        queued_feedback = self._consume_queued_external_feedback()
        if queued_feedback:
            observed_feedback = self._merge_observed_feedback(observed_feedback, queued_feedback)
        parameter_events = (
            list(causal_window.get("visual_gaze_events", []) or [])
            + list(causal_window.get("auditory_band_events", []) or [])
            + list(causal_window.get("text_parameter_events", []) or [])
        )
        planner_feedback = self.action_planner.record_feedback(
            selected_actions=selected_actions,
            observed_feedback=observed_feedback,
            parameter_events=parameter_events,
        )
        feedback_items = self._build_action_feedback_items(
            selected_actions=selected_actions,
            observed_feedback=observed_feedback,
            planner_feedback=planner_feedback,
            causal_window=causal_window,
        )
        structured_events = self._structured_action_outcome_events(
            selected_actions=selected_actions,
            observed_feedback=observed_feedback,
            planner_feedback=planner_feedback,
            parameter_events=parameter_events,
        )
        if queued_feedback:
            feedback_items.extend(self._build_explicit_feedback_items(queued_feedback))
        return {
            "applied": True,
            "selected_actions": selected_actions,
            "observed_feedback": observed_feedback,
            "planner_feedback": planner_feedback,
            "causal_window": causal_window,
            "feedback_items": feedback_items,
            "structured_learning_events": structured_events,
            "external_feedback": dict(queued_feedback or {}),
        }

    def _consume_queued_external_feedback(self) -> dict:
        feedback = dict(self._queued_external_feedback or {})
        self._queued_external_feedback = None
        return feedback

    def _merge_queued_external_feedback(self, feedback: dict) -> None:
        if not feedback:
            return
        existing = dict(self._queued_external_feedback or {})
        if not existing:
            self._queued_external_feedback = dict(feedback)
            return
        self._queued_external_feedback = self._merge_observed_feedback(existing, feedback)

    def _merge_observed_feedback(self, observed_feedback: dict, external_feedback: dict) -> dict:
        observed = dict(observed_feedback or {})
        external = dict(external_feedback or {})
        reward = max(0.0, float(observed.get("reward", 0.0) or 0.0)) + max(
            0.0, float(external.get("reward", 0.0) or 0.0)
        )
        punishment = max(0.0, float(observed.get("punishment", 0.0) or 0.0)) + max(
            0.0, float(external.get("punishment", 0.0) or 0.0)
        )
        correctness = max(0.0, float(observed.get("correctness", 0.0) or 0.0)) + max(
            0.0, float(external.get("correctness", 0.0) or 0.0)
        )
        confidence = max(float(observed.get("confidence", 0.0) or 0.0), float(external.get("confidence", 0.0) or 0.0))
        notes = list(observed.get("notes", []) or []) + [
            f"external_feedback::{external.get('source', 'external_feedback')}"
        ]
        notes.extend([str(note or "") for note in list(external.get("notes", []) or []) if str(note or "")])
        return {
            "reward": round(reward, 4),
            "punishment": round(punishment, 4),
            "correctness": round(correctness, 4),
            "confidence": round(max(0.0, min(1.0, confidence)), 4),
            "notes": notes,
            "external_feedback": external,
        }

    def _build_explicit_feedback_items(self, feedback: dict) -> list[dict]:
        reward = max(0.0, float((feedback or {}).get("reward", 0.0) or 0.0))
        punishment = max(0.0, float((feedback or {}).get("punishment", 0.0) or 0.0))
        correctness = max(0.0, float((feedback or {}).get("correctness", 0.0) or 0.0))
        confidence = max(0.0, min(1.0, float((feedback or {}).get("confidence", 0.0) or 0.0)))
        source = str((feedback or {}).get("source", "") or "external_feedback")
        items: list[dict] = []
        if reward > 0.0:
            items.append(
                {
                    "sa_label": "signal::reward",
                    "display_text": "外部奖励",
                    "source_type": "external_feedback",
                    "family": "signal",
                    "real_energy": round(reward, 4),
                    "anchor_meta": {
                        "schema_id": "explicit_feedback_signal/v1",
                        "feedback_kind": "reward",
                        "source": source,
                        "confidence": round(confidence, 4),
                        "observed_feedback": dict(feedback or {}),
                    },
                }
            )
        if correctness > 0.0:
            items.append(
                {
                    "sa_label": "signal::correctness",
                    "display_text": "外部正确性",
                    "source_type": "external_feedback",
                    "family": "signal",
                    "real_energy": round(correctness, 4),
                    "anchor_meta": {
                        "schema_id": "explicit_feedback_signal/v1",
                        "feedback_kind": "correctness",
                        "source": source,
                        "confidence": round(confidence, 4),
                        "observed_feedback": dict(feedback or {}),
                    },
                }
            )
        if punishment > 0.0:
            items.append(
                {
                    "sa_label": "signal::punishment",
                    "display_text": "外部惩罚",
                    "source_type": "external_feedback",
                    "family": "signal",
                    "real_energy": round(punishment, 4),
                    "virtual_energy": round(punishment, 4),
                    "anchor_meta": {
                        "schema_id": "explicit_feedback_signal/v1",
                        "feedback_kind": "punishment",
                        "source": source,
                        "confidence": round(confidence, 4),
                        "observed_feedback": dict(feedback or {}),
                        "feedback_energy_semantics": {
                            "real_energy": round(punishment, 4),
                            "virtual_energy": round(punishment, 4),
                            "punishment_pressure": round(punishment, 4),
                            "meaning": "punishment_event_as_real;future_avoidance_pressure_as_virtual",
                        },
                    },
                }
            )
        return items

    def _run_recall_branch(
        self,
        query_items: list[dict],
        *,
        memory_kind: str,
        prediction_source: str,
        time_context: dict | None = None,
    ) -> tuple[list[dict], list[dict]]:
        bn_rows = self.memory.recall(query_items, memory_kind=memory_kind, time_context=time_context)
        cn_rows = []
        for row in bn_rows:
            cn_rows.extend(
                self.memory.successors(
                    row["memory_id"],
                    memory_kind=memory_kind,
                    source_b_row=row,
                    current_tick=self.tick_index,
                )
            )
        predicted_items = [item for branch in cn_rows for item in branch.get("predicted_items", [])]
        if predicted_items:
            self.state_pool.apply_predictions(predicted_items, tick_index=self.tick_index, source=prediction_source)
        return bn_rows, cn_rows

    def _build_slow_query(
        self, selected_focus_items: list[dict], *, action_slow_query_hints: list[dict] | None = None
    ) -> list[dict]:
        focus_labels = []
        seen_focus = set()
        for item in selected_focus_items or []:
            label = str((item or {}).get("sa_label", "") or "")
            if label and label not in seen_focus:
                seen_focus.add(label)
                focus_labels.append(label)
        for label in self.focus_buffer.recent_labels():
            if label and label not in seen_focus:
                seen_focus.add(label)
                focus_labels.append(label)
        action_hint_labels = [
            str(hint.get("sa_label", "") or "")
            for hint in list(action_slow_query_hints or [])
            if isinstance(hint, dict) and str(hint.get("sa_label", "") or "")
        ]
        for label in action_hint_labels:
            if label and label not in seen_focus:
                seen_focus.add(label)
                focus_labels.append(label)
        state_rows = self.state_pool.rows_for_labels(focus_labels)
        state_by_label = {
            str(item.get("sa_label", "") or ""): item for item in state_rows if str(item.get("sa_label", "") or "")
        }
        query_rows = []
        current_order: dict[str, int] = {}
        selected_labels = []
        seen_selected = set()
        for item in selected_focus_items or []:
            label = str((item or {}).get("sa_label", "") or "")
            if not label or label in seen_selected:
                continue
            seen_selected.add(label)
            current_order[label] = len(selected_labels)
            selected_labels.append(label)
        for label in selected_labels:
            state_row = state_by_label.get(label)
            if state_row is not None:
                current_row = dict(state_row)
                current_row["source_type"] = str(current_row.get("source_type", "") or "current_focus")
                current_row["query_source"] = "current_focus"
                current_row["focus_order_index"] = int(current_order.get(label, len(current_order)))
                if "query_weight" not in current_row:
                    current_row["query_weight"] = float(current_row.get("real_energy", 0.0) or 0.0)
                query_rows.append(current_row)
        continuation_rows = self.focus_buffer.build_query_items(state_rows, tick_index=self.tick_index)
        replay_rows = self.focus_buffer.build_replay_query_items(state_rows, tick_index=self.tick_index)
        merged: dict[str, dict] = {}
        action_hint_rows = []
        hint_by_label = {
            str(hint.get("sa_label", "") or ""): dict(hint)
            for hint in list(action_slow_query_hints or [])
            if isinstance(hint, dict) and str(hint.get("sa_label", "") or "")
        }
        for label, hint in hint_by_label.items():
            state_row = state_by_label.get(label)
            if state_row is None:
                continue
            row = dict(state_row)
            row["source_type"] = "action_control_hint"
            row["query_source"] = "action_control_hint"
            row["query_weight"] = max(
                float(row.get("query_weight", 0.0) or 0.0), float(hint.get("query_weight", 0.0) or 0.0)
            )
            row["virtual_energy"] = max(
                float(row.get("virtual_energy", 0.0) or 0.0), float(hint.get("virtual_energy", 0.0) or 0.0)
            )
            row["anchor_meta"] = {"action_slow_query_hint": hint}
            action_hint_rows.append(row)
        for row in query_rows + continuation_rows + replay_rows + action_hint_rows:
            label = str(row.get("sa_label", "") or "")
            if not label:
                continue
            bucket = merged.get(label)
            if bucket is None:
                item = dict(row)
                item["query_sources"] = [str(item.get("query_source", item.get("source_type", "")) or "unknown")]
                if label in current_order:
                    item["focus_order_index"] = int(current_order[label])
                merged[label] = item
                continue
            source_name = str(row.get("query_source", row.get("source_type", "")) or "unknown")
            sources = list(bucket.get("query_sources", []) or [])
            if source_name not in sources:
                sources.append(source_name)
            bucket["query_sources"] = sources
            if source_name == "focus_replay" and "current_focus" not in sources:
                bucket["source_type"] = "focus_replay"
            bucket["query_weight"] = max(
                float(bucket.get("query_weight", 0.0) or 0.0), float(row.get("query_weight", 0.0) or 0.0)
            )
            bucket["real_energy"] = max(
                float(bucket.get("real_energy", 0.0) or 0.0), float(row.get("real_energy", 0.0) or 0.0)
            )
            bucket["virtual_energy"] = max(
                float(bucket.get("virtual_energy", 0.0) or 0.0), float(row.get("virtual_energy", 0.0) or 0.0)
            )
            bucket["cognitive_pressure"] = float(bucket.get("real_energy", 0.0) or 0.0) - float(
                bucket.get("virtual_energy", 0.0) or 0.0
            )
        rows = list(merged.values())
        rows.sort(
            key=lambda item: (
                0 if str(item.get("sa_label", "") or "") in current_order else 1,
                int(current_order.get(str(item.get("sa_label", "") or ""), 10**9)),
                -float(item.get("query_weight", item.get("real_energy", 0.0)) or 0.0),
                str(item.get("sa_label", "") or ""),
            )
        )
        return rows

    def _build_action_control_items(
        self,
        *,
        selected_actions: list[dict],
        attention_trace: dict,
        fast_bn: list[dict],
        slow_bn: list[dict],
        fast_cn: list[dict],
        slow_cn: list[dict],
        state_snapshot_items: list[dict] | None = None,
        time_context: dict | None = None,
        action_consequence_trace: dict | None = None,
        expectation_pressure_trace: dict | None = None,
        focus_continuation_trace: dict | None = None,
        short_term_memory_recall: dict | None = None,
    ) -> list[dict]:
        items = []
        if not selected_actions:
            return items
        focus_labels = [
            label
            for label in (attention_trace.get("selected_labels", []) or [])
            if self._is_core_trace_label(str(label or ""))
        ]
        replay_labels = self._extract_replay_labels(fast_bn=fast_bn, slow_bn=slow_bn, focus_labels=focus_labels)
        stabilize_labels = self._extract_predicted_labels(fast_cn=fast_cn, slow_cn=slow_cn)
        for row in selected_actions:
            action_id = str(row.get("action_id", "") or "")
            if action_id == "action::continue_focus":
                for label in focus_labels[:3]:
                    items.append(
                        {
                            "sa_label": label,
                            "display_text": label,
                            "family": "action_control",
                            "source_type": "action_control",
                            "virtual_energy": 0.42,
                            "anchor_meta": {"action_id": action_id, "control_kind": "continue_focus"},
                        }
                    )
            elif action_id in {"action::replay_recent_context", "action::recall_recent_context"}:
                if action_id == "action::recall_recent_context":
                    items.extend(
                        self._short_term_memory_control_rows(
                            selected_action=row,
                            recall_trace=short_term_memory_recall or {},
                            limit=8,
                        )
                    )
                    items.extend(
                        self._recent_thought_readback_control_rows(
                            selected_action=row,
                            focus_continuation_trace=focus_continuation_trace or {},
                            fallback_labels=replay_labels,
                            limit=8,
                        )
                    )
                    continue
                for label in replay_labels[:4]:
                    items.append(
                        {
                            "sa_label": label,
                            "display_text": label,
                            "family": "action_control",
                            "source_type": "action_control",
                            "virtual_energy": 0.58,
                            "anchor_meta": {"action_id": action_id, "control_kind": "replay_recent_context"},
                        }
                    )
                # The legacy replay action often wins the memory-recall lane in
                # real traces. When a short-term readback view is available, we
                # keep the replay rows above and also expose the self-observation
                # part: AP is effectively checking what it was just thinking.
                items.extend(
                    self._short_term_memory_control_rows(
                        selected_action=row,
                        recall_trace=short_term_memory_recall or {},
                        limit=8,
                    )
                )
                items.extend(
                    self._recent_thought_readback_control_rows(
                        selected_action=row,
                        focus_continuation_trace=focus_continuation_trace or {},
                        fallback_labels=replay_labels,
                        limit=8,
                    )
                )
            elif action_id == "action::recall_by_expectation":
                for control in self._expectation_recall_control_rows(
                    selected_action=row,
                    expectation_pressure_trace=expectation_pressure_trace or {},
                    limit=6,
                ):
                    items.append(control)
            elif action_id == "action::recall_by_timefelt":
                items.extend(
                    self._timefelt_recall_control_rows(
                        selected_action=row,
                        state_snapshot_items=state_snapshot_items or [],
                        time_context=time_context,
                        limit=8,
                    )
                )
            elif action_id == "action::replay_episode":
                items.extend(
                    self._episode_replay_control_rows(
                        selected_action=row,
                        expectation_pressure_trace=expectation_pressure_trace or {},
                        action_consequence_trace=action_consequence_trace or {},
                        limit=10,
                    )
                )
            elif action_id == "action::wait":
                items.append(self._wait_control_row(selected_action=row))
            elif action_id == "action::stabilize_prediction":
                for label in stabilize_labels[:4]:
                    items.append(
                        {
                            "sa_label": label,
                            "display_text": label,
                            "family": "action_control",
                            "source_type": "action_control",
                            "virtual_energy": 0.46,
                            "anchor_meta": {"action_id": action_id, "control_kind": "stabilize_prediction"},
                        }
                    )
        return items

    def _recent_thought_readback_control_rows(
        self,
        *,
        selected_action: dict,
        focus_continuation_trace: dict,
        fallback_labels: list[str],
        limit: int,
    ) -> list[dict]:
        readback = dict((focus_continuation_trace or {}).get("recent_thought_readback", {}) or {})
        params = dict((selected_action or {}).get("params", {}) or {})
        labels = [
            str(label or "")
            for label in list(readback.get("labels", []) or params.get("labels", []) or fallback_labels or [])
            if str(label or "")
        ]
        seen = set()
        unique_labels = []
        for label in labels:
            if label in seen:
                continue
            seen.add(label)
            unique_labels.append(label)
            if len(unique_labels) >= max(1, int(limit)):
                break
        if not unique_labels:
            return []
        strength = self._selected_action_strength(selected_action)
        meta = {
            "schema_id": "recent_thought_readback_control/v1",
            "action_id": "action::recall_recent_context",
            "control_kind": "recent_thought_readback",
            "source_action_id": str((selected_action or {}).get("action_id", "") or "action::recall_recent_context"),
            "recalled_labels": unique_labels,
            "entries": list(readback.get("entries", []) or [])[:6],
            "active_episode_id": int(readback.get("active_episode_id", params.get("active_episode_id", -1)) or -1),
            "drift_score": round(float(readback.get("drift_score", 0.0) or 0.0), 4),
            "branch_end_score": round(float(readback.get("branch_end_score", 0.0) or 0.0), 4),
            "strength": round(strength, 4),
            "learning_boundary": "short_term_readback_modulates_attention_and_slow_query_not_forced_answer",
            "meaning": "AP_reading_its_recent_focus_episode_like_checking_what_it_was_thinking",
        }
        rows: list[dict] = [
            {
                "sa_label": "control::recent_thought_readback",
                "display_text": "recent thought readback",
                "family": "action_control",
                "source_type": "action_control",
                "real_energy": 0.0,
                "virtual_energy": round(min(0.68, 0.18 + strength * 0.42), 4),
                "anchor_meta": meta,
            }
        ]
        for label in unique_labels:
            rows.append(
                {
                    "sa_label": label,
                    "display_text": label,
                    "family": "action_control",
                    "source_type": "action_control",
                    "real_energy": 0.0,
                    "virtual_energy": 0.0,
                    "attention_gain": round(min(0.52, 0.10 + strength * 0.30), 4),
                    "anchor_meta": {**meta, "target_label": label, "target_modulation": "recent_thought_readback"},
                }
            )
        return rows

    def _short_term_memory_control_rows(self, *, selected_action: dict, recall_trace: dict, limit: int) -> list[dict]:
        recall = dict(recall_trace or {})
        selected_items = [dict(item) for item in list(recall.get("selected_items", []) or []) if isinstance(item, dict)]
        if not selected_items:
            return []
        strength = self._selected_action_strength(selected_action)
        labels = []
        seen = set()
        for item in selected_items:
            label = str(item.get("sa_label", "") or "")
            if not label or label in seen:
                continue
            seen.add(label)
            labels.append(label)
            if len(labels) >= max(1, int(limit)):
                break
        if not labels:
            return []
        meta = {
            "schema_id": "short_term_memory_recall_control/v1",
            "action_id": "action::recall_recent_context",
            "source_action_id": str((selected_action or {}).get("action_id", "") or "action::recall_recent_context"),
            "control_kind": "short_term_memory_recall",
            "recalled_labels": labels,
            "selected_events": [
                {
                    "event_id": str(event.get("event_id", "") or ""),
                    "tick_index": int(event.get("tick_index", -1) or -1),
                    "source_kind": str(event.get("source_kind", "") or ""),
                    "modality": str(event.get("modality", "") or ""),
                    "score": round(float(event.get("score", 0.0) or 0.0), 4),
                }
                for event in list(recall.get("selected_events", []) or [])[:4]
                if isinstance(event, dict)
            ],
            "cue_tokens": list(recall.get("cue_tokens", []) or [])[:12],
            "strength": round(strength, 4),
            "not_new_external_input": True,
            "learning_boundary": "short_term_memory_readback_modulates_attention_and_slow_query_not_forced_answer",
            "meaning": "AP_actively_recalls_a_recent_multimodal_working_memory_segment",
        }
        rows: list[dict] = [
            {
                "sa_label": "control::short_term_memory_recall",
                "display_text": "short-term memory recall",
                "family": "action_control",
                "source_type": "action_control",
                "real_energy": 0.0,
                "virtual_energy": round(min(0.72, 0.20 + strength * 0.42), 4),
                "anchor_meta": meta,
            }
        ]
        for item in selected_items[: max(1, int(limit))]:
            label = str(item.get("sa_label", "") or "")
            if not label:
                continue
            item_strength = max(0.05, min(1.0, float(item.get("recall_strength", strength) or strength)))
            rows.append(
                {
                    "sa_label": label,
                    "display_text": str(item.get("display_text", label) or label),
                    "family": "action_control",
                    "source_type": "action_control",
                    "real_energy": 0.0,
                    "virtual_energy": 0.0,
                    "attention_gain": round(min(0.56, 0.08 + item_strength * 0.34), 4),
                    "anchor_meta": {
                        **meta,
                        "target_label": label,
                        "target_modulation": "short_term_memory_recall",
                        "origin_tick_index": int(item.get("origin_tick_index", -1) or -1),
                        "source_kind": str(item.get("source_kind", "") or ""),
                        "modality": str(item.get("modality", "") or ""),
                        "event_id": str(item.get("event_id", "") or ""),
                    },
                }
            )
        return rows

    def _expectation_recall_control_rows(
        self, *, selected_action: dict, expectation_pressure_trace: dict, limit: int
    ) -> list[dict]:
        anchors = [
            dict(anchor)
            for anchor in list((selected_action or {}).get("supporting_anchors", []) or [])
            if isinstance(anchor, dict)
        ]
        if not anchors:
            trace = dict((expectation_pressure_trace or {}).get("anchor_verification", {}) or {})
            wanted = str(((selected_action or {}).get("params", {}) or {}).get("b_anchor", "") or "")
            anchors = [
                dict(anchor)
                for anchor in list(trace.get("anchors", []) or [])
                if isinstance(anchor, dict) and (not wanted or str(anchor.get("anchor_id", "") or "") == wanted)
            ]
        anchors.sort(
            key=lambda anchor: (
                -float(anchor.get("level", 0.0) or 0.0),
                0 if str(anchor.get("anchor_type", "") or "") == "pressure" else 1,
                str(anchor.get("anchor_id", "") or ""),
            )
        )
        rows: list[dict] = []
        seen: set[str] = set()
        for anchor in anchors:
            if len(rows) >= max(1, int(limit)):
                break
            source_memory_id = str(anchor.get("source_memory_id", "") or "")
            if not source_memory_id:
                continue
            snapshot = self.memory.snapshot_by_id(source_memory_id) or {}
            labels = self._labels_from_memory_snapshot(snapshot)
            for label in labels:
                if len(rows) >= max(1, int(limit)):
                    break
                if label in seen:
                    continue
                seen.add(label)
                level = max(0.08, min(1.0, float(anchor.get("level", 0.0) or 0.0)))
                rows.append(
                    {
                        "sa_label": label,
                        "display_text": label,
                        "family": "action_control",
                        "source_type": "action_control",
                        "virtual_energy": round(min(0.72, 0.24 + level * 0.46), 4),
                        "anchor_meta": {
                            "schema_id": "expectation_recall_control/v1",
                            "action_id": "action::recall_by_expectation",
                            "control_kind": "recall_by_expectation",
                            "anchor_id": str(anchor.get("anchor_id", "") or ""),
                            "anchor_type": str(anchor.get("anchor_type", "") or ""),
                            "source_memory_id": source_memory_id,
                            "source_memory_kind": str(anchor.get("source_memory_kind", "") or ""),
                            "source_tick_index": int(anchor.get("source_tick_index", -1) or -1),
                            "anchor_level": round(level, 4),
                            "expected_reward": round(float(anchor.get("expected_reward", 0.0) or 0.0), 4),
                            "expected_punishment": round(float(anchor.get("expected_punishment", 0.0) or 0.0), 4),
                            "recalled_from_snapshot": bool(snapshot),
                        },
                    }
                )
        return rows

    def _timefelt_recall_control_rows(
        self,
        *,
        selected_action: dict,
        state_snapshot_items: list[dict],
        time_context: dict | None,
        limit: int,
    ) -> list[dict]:
        if not time_context:
            return []
        query_items = [
            dict(item)
            for item in list(state_snapshot_items or [])[: max(1, self.config.memory.query_feature_limit)]
            if isinstance(item, dict) and self._is_core_trace_label(str(item.get("sa_label", "") or ""))
        ]
        if not query_items:
            params = dict((selected_action or {}).get("params", {}) or {})
            query_items = [
                {
                    "sa_label": label,
                    "display_text": label,
                    "family": "text",
                    "source_type": "timefelt_query",
                    "real_energy": 0.1,
                }
                for label in list(params.get("query_labels", []) or [])[:4]
            ]
        state_rows = (
            self.memory.recall(query_items, memory_kind="state", top_k=4, time_context=time_context)
            if query_items
            else []
        )
        focus_rows = (
            self.memory.recall(query_items, memory_kind="focus", top_k=3, time_context=time_context)
            if query_items
            else []
        )
        recall_rows = sorted(
            [dict(row) for row in list(state_rows or []) + list(focus_rows or [])],
            key=lambda item: (
                -float(item.get("time_match", 0.0) or 0.0),
                -float(item.get("score", 0.0) or 0.0),
                str(item.get("memory_id", "") or ""),
            ),
        )
        if not recall_rows:
            return []
        strength = self._selected_action_strength(selected_action)
        target_delta_t = float(time_context.get("target_delta_t", 0.0) or 0.0)
        sigma = float(time_context.get("time_sigma", 1.0) or 1.0)
        source_memory_ids = []
        labels: list[str] = []
        seen_labels: set[str] = set()
        for row in recall_rows[:4]:
            memory_id = str(row.get("memory_id", "") or "")
            if memory_id and memory_id not in source_memory_ids:
                source_memory_ids.append(memory_id)
            snapshot = dict(row.get("snapshot", {}) or self.memory.snapshot_by_id(memory_id) or {})
            for label in self._labels_from_memory_snapshot(snapshot, limit=max(2, int(limit))):
                if label in seen_labels:
                    continue
                seen_labels.add(label)
                labels.append(label)
                if len(labels) >= max(1, int(limit)):
                    break
            if len(labels) >= max(1, int(limit)):
                break
        meta = {
            "schema_id": "timefelt_recall_control/v1",
            "action_id": "action::recall_by_timefelt",
            "control_kind": "recall_by_timefelt",
            "source_action_id": "action::recall_by_timefelt",
            "target_delta_t": round(target_delta_t, 4),
            "time_sigma": round(max(1.0, sigma), 4),
            "source_memory_ids": source_memory_ids,
            "replayed_labels": labels,
            "strength": round(strength, 4),
            "learning_boundary": "timefelt_recall_modulates_attention_and_slow_query_not_concept_embedding",
            "humanlike_testing": {
                "engineering_latency_ticks": "1-2",
                "behavior_window_ticks": "5-10",
            },
        }
        rows: list[dict] = [
            {
                "sa_label": "control::timefelt_recall",
                "display_text": "时间感回忆",
                "family": "action_control",
                "source_type": "action_control",
                "real_energy": 0.0,
                "virtual_energy": round(min(0.72, 0.18 + strength * 0.46), 4),
                "anchor_meta": meta,
            }
        ]
        for label in labels:
            rows.append(
                {
                    "sa_label": label,
                    "display_text": label,
                    "family": "action_control",
                    "source_type": "action_control",
                    "real_energy": 0.0,
                    "virtual_energy": 0.0,
                    "attention_gain": round(min(0.58, 0.12 + strength * 0.36), 4),
                    "anchor_meta": {**meta, "target_label": label, "target_modulation": "timefelt_recall"},
                }
            )
        return rows

    def _episode_replay_control_rows(
        self,
        *,
        selected_action: dict,
        expectation_pressure_trace: dict,
        action_consequence_trace: dict,
        limit: int,
    ) -> list[dict]:
        source = self._select_episode_replay_source(
            selected_action=selected_action,
            expectation_pressure_trace=expectation_pressure_trace,
            action_consequence_trace=action_consequence_trace,
        )
        source_memory_id = str(source.get("source_memory_id", "") or "")
        snapshot = self.memory.snapshot_by_id(source_memory_id) if source_memory_id else None
        if not snapshot:
            return []
        params = dict((selected_action or {}).get("params", {}) or {})
        episode_id = params.get("episode_id", params.get("source_episode_id", None))
        if episode_id is not None:
            try:
                self.focus_buffer.mark_replay_selected(int(episode_id))
            except (TypeError, ValueError):
                pass
        strength = self._selected_action_strength(selected_action)
        labels = self._labels_from_memory_snapshot(snapshot, limit=max(2, int(limit)))
        feedback_items = [
            dict(item)
            for item in list(snapshot.get("action_feedback_items", []) or snapshot.get("items", []) or [])
            if isinstance(item, dict)
            and (
                str(item.get("sa_label", "") or "").startswith("action_feedback::")
                or str(item.get("family", "") or "") == "action_feedback"
                or str(item.get("source_type", "") or "") == "action_feedback"
            )
        ][:4]
        feedback_summary = self._summarize_replay_feedback(snapshot=snapshot, feedback_items=feedback_items)
        safety_review_hint = {
            "schema_id": "episode_replay_safety_review_hint/v1",
            "source_memory_id": source_memory_id,
            "risk": round(
                max(float(source.get("risk", 0.0) or 0.0), float(feedback_summary.get("risk", 0.0) or 0.0)), 4
            ),
            "punishment": round(float(feedback_summary.get("punishment", 0.0) or 0.0), 4),
            "pressure": round(float(feedback_summary.get("pressure", 0.0) or 0.0), 4),
            "requires_external_review": bool(
                float(feedback_summary.get("risk", 0.0) or 0.0) >= 0.18 or float(source.get("risk", 0.0) or 0.0) >= 0.24
            ),
        }
        meta = {
            "schema_id": "episode_replay_control/v1",
            "action_id": "action::replay_episode",
            "control_kind": "replay_episode",
            "source_action_id": "action::replay_episode",
            "source_memory_id": source_memory_id,
            "source_memory_kind": str(snapshot.get("memory_kind", "") or ""),
            "source_tick_index": int(snapshot.get("tick_index", -1) or -1),
            "source_reason": str(source.get("reason", "") or ""),
            "replayed_labels": labels,
            "feedback_summary": feedback_summary,
            "safety_review_hint": safety_review_hint,
            "strength": round(strength, 4),
            "learning_boundary": "episode_replay_can_shape_action_consequence_but_not_concept_embedding",
        }
        rows: list[dict] = [
            {
                "sa_label": "control::episode_replay",
                "display_text": "经验回放",
                "family": "action_control",
                "source_type": "action_control",
                "real_energy": 0.0,
                "virtual_energy": round(
                    min(0.76, 0.20 + strength * 0.48 + float(feedback_summary.get("risk", 0.0) or 0.0) * 0.16), 4
                ),
                "anchor_meta": meta,
            }
        ]
        for label in labels[: max(1, int(limit))]:
            rows.append(
                {
                    "sa_label": label,
                    "display_text": label,
                    "family": "action_control",
                    "source_type": "action_control",
                    "real_energy": 0.0,
                    "virtual_energy": 0.0,
                    "attention_gain": round(
                        min(0.62, 0.12 + strength * 0.34 + float(feedback_summary.get("risk", 0.0) or 0.0) * 0.08), 4
                    ),
                    "anchor_meta": {**meta, "target_label": label, "target_modulation": "episode_replay"},
                }
            )
        for item in feedback_items:
            label = str(item.get("sa_label", "") or "")
            if not label:
                continue
            rows.append(
                {
                    "sa_label": label,
                    "display_text": str(item.get("display_text", label) or label),
                    "family": "action_control",
                    "source_type": "action_control",
                    "real_energy": 0.0,
                    "virtual_energy": 0.0,
                    "attention_gain": round(min(0.52, 0.10 + strength * 0.28), 4),
                    "anchor_meta": {**meta, "target_label": label, "target_modulation": "episode_feedback_replay"},
                }
            )
        return rows

    def _wait_control_row(self, *, selected_action: dict) -> dict:
        strength = self._selected_action_strength(selected_action)
        params = dict((selected_action or {}).get("params", {}) or {})
        duration = max(1, int(params.get("duration_ticks", 1) or 1))
        meta = {
            "schema_id": "timing_wait_control/v1",
            "action_id": "action::wait",
            "control_kind": "wait",
            "source_action_id": "action::wait",
            "wait_hold_ticks": duration,
            "wait_intensity": round(strength, 4),
            "rhythm_expectation": round(float(params.get("rhythm_expectation", 0.0) or 0.0), 4),
            "uncertainty": round(float(params.get("uncertainty", 0.0) or 0.0), 4),
            "external_action_review_hint": round(min(0.65, 0.10 + strength * 0.42), 4),
            "meaning": "legal_non_action_that_can_be_rewarded_or_punished",
        }
        return {
            "sa_label": "control::timing_wait",
            "display_text": "等待",
            "family": "action_control",
            "source_type": "action_control",
            "real_energy": 0.0,
            "virtual_energy": round(min(0.58, 0.12 + strength * 0.35), 4),
            "anchor_meta": meta,
        }

    def _select_episode_replay_source(
        self, *, selected_action: dict, expectation_pressure_trace: dict, action_consequence_trace: dict
    ) -> dict:
        params = dict((selected_action or {}).get("params", {}) or {})
        explicit = str(params.get("source_memory_id", "") or "")
        if explicit:
            return {
                "source_memory_id": explicit,
                "reason": "selected_action_param",
                "risk": float(params.get("risk", 0.0) or 0.0),
            }
        anchors = [
            dict(anchor)
            for anchor in list(
                ((expectation_pressure_trace or {}).get("anchor_verification", {}) or {}).get("anchors", []) or []
            )
            if isinstance(anchor, dict) and str(anchor.get("source_memory_id", "") or "")
        ]
        anchors.sort(
            key=lambda anchor: (
                0 if str(anchor.get("anchor_type", "") or "") == "pressure" else 1,
                -float(anchor.get("level", 0.0) or 0.0),
                -float(anchor.get("expected_punishment", 0.0) or 0.0),
            )
        )
        if anchors:
            anchor = anchors[0]
            risk = (
                float(anchor.get("level", 0.0) or 0.0) * 0.58
                + float(anchor.get("expected_punishment", 0.0) or 0.0) * 0.32
            )
            return {
                "source_memory_id": str(anchor.get("source_memory_id", "") or ""),
                "reason": "pressure_b_anchor",
                "risk": risk,
            }
        estimates = list(dict((action_consequence_trace or {}).get("action_estimates", {}) or {}).values())
        estimates = [
            dict(row) for row in estimates if isinstance(row, dict) and list(row.get("source_memory_ids", []) or [])
        ]
        estimates.sort(
            key=lambda row: (
                -(
                    float(row.get("support", 0.0) or 0.0)
                    * (float(row.get("punishment", 0.0) or 0.0) + float(row.get("pressure", 0.0) or 0.0))
                ),
                str(row.get("action_id", "") or ""),
            )
        )
        if estimates:
            row = estimates[0]
            source_ids = list(row.get("source_memory_ids", []) or [])
            return {
                "source_memory_id": str(source_ids[0] if source_ids else ""),
                "reason": "action_consequence_evidence",
                "risk": float(row.get("support", 0.0) or 0.0)
                * (float(row.get("punishment", 0.0) or 0.0) + float(row.get("pressure", 0.0) or 0.0)),
            }
        latest = self.memory.latest_snapshot("state")
        return {
            "source_memory_id": str((latest or {}).get("memory_id", "") or ""),
            "reason": "latest_state_fallback",
            "risk": 0.0,
        }

    def _summarize_replay_feedback(self, *, snapshot: dict, feedback_items: list[dict]) -> dict:
        reward = 0.0
        punishment = 0.0
        correctness = 0.0
        pressure = 0.0
        inhibition_count = 0
        labels = []
        for item in list(feedback_items or []) + list((snapshot or {}).get("items", []) or []):
            if not isinstance(item, dict):
                continue
            label = str(item.get("sa_label", "") or "")
            if not label:
                continue
            if label.startswith("action_inhibition::"):
                inhibition_count += 1
                pressure += float(item.get("real_energy", 0.0) or 0.0) * 0.42
            if label.startswith("signal::punishment"):
                punishment += (
                    float(item.get("real_energy", 0.0) or 0.0) + float(item.get("virtual_energy", 0.0) or 0.0) * 0.35
                )
            if label.startswith("signal::reward"):
                reward += float(item.get("real_energy", 0.0) or 0.0)
            if label.startswith("signal::correctness"):
                correctness += float(item.get("real_energy", 0.0) or 0.0)
            if label.startswith("action_feedback::"):
                labels.append(label)
                meta = dict(item.get("anchor_meta", {}) or {})
                observed = dict(meta.get("observed_feedback", {}) or {})
                reward += float(observed.get("reward", 0.0) or 0.0)
                punishment += float(observed.get("punishment", 0.0) or 0.0)
                correctness += float(observed.get("correctness", 0.0) or 0.0)
                semantics = dict(meta.get("feedback_energy_semantics", {}) or {})
                pressure += float(semantics.get("punishment_pressure", 0.0) or 0.0)
        risk = max(0.0, punishment * 0.62 + pressure * 0.38 - reward * 0.16 - correctness * 0.08)
        return {
            "schema_id": "episode_replay_feedback_summary/v1",
            "reward": round(reward, 4),
            "punishment": round(punishment, 4),
            "correctness": round(correctness, 4),
            "pressure": round(pressure, 4),
            "risk": round(risk, 4),
            "inhibition_count": int(inhibition_count),
            "feedback_labels": labels[:8],
        }

    def _selected_action_strength(self, selected_action: dict) -> float:
        decisiveness = float((selected_action or {}).get("effective_decisiveness", 0.0) or 0.0)
        drive = float((selected_action or {}).get("drive", 0.0) or 0.0)
        threshold = float((selected_action or {}).get("effective_threshold", 0.0) or 0.0)
        if decisiveness <= 0.0 and drive > threshold:
            decisiveness = drive - threshold
        innate_strength = max(
            [
                float(node.get("strength", 0.0) or 0.0)
                for node in list((selected_action or {}).get("innate_nodes", []) or [])
                if isinstance(node, dict)
            ]
            or [0.0]
        )
        return max(0.08, min(0.92, 0.18 + decisiveness * 0.55 + innate_strength * 0.12))

    def _labels_from_memory_snapshot(self, snapshot: dict, *, limit: int = 12) -> list[str]:
        labels: list[str] = []
        seen: set[str] = set()
        for item in list(
            (snapshot or {}).get("state_field_items", [])
            or (snapshot or {}).get("core_items", [])
            or (snapshot or {}).get("items", [])
            or []
        ):
            if len(labels) >= max(1, int(limit)):
                break
            if not isinstance(item, dict):
                continue
            label = str(item.get("sa_label", "") or "")
            if not label or label in seen or not self._is_core_trace_label(label):
                continue
            seen.add(label)
            labels.append(label)
        if labels:
            return labels
        for label in list((snapshot or {}).get("focus_labels", []) or []):
            clean = str(label or "")
            if clean and clean not in seen and self._is_core_trace_label(clean):
                seen.add(clean)
                labels.append(clean)
                if len(labels) >= max(1, int(limit)):
                    break
        return labels

    def _labels_after_action_control(
        self, *, feedback_focus_rows: list[dict], control_items: list[dict], action_items: list[dict]
    ) -> list[str]:
        labels = []
        seen = set()
        for row in list(control_items or []) + list(action_items or []) + list(feedback_focus_rows or []):
            label = str((row or {}).get("sa_label", "") or "")
            if not label or label in seen:
                continue
            seen.add(label)
            labels.append(label)
            if len(labels) >= 8:
                break
        return labels

    def _build_action_causal_window(
        self,
        *,
        selected_actions: list[dict],
        state_snapshot_before_action: dict,
        feedback_context: dict,
        control_items: list[dict],
        action_items: list[dict],
        text_output_trace: dict,
        state_snapshot_after_output: dict,
    ) -> dict:
        action_ids = [
            str(row.get("action_id", "") or "")
            for row in (selected_actions or [])
            if str(row.get("action_id", "") or "")
        ]

        def _labels(snapshot: dict, limit: int = 10) -> list[str]:
            return [
                str(item.get("sa_label", "") or "")
                for item in (snapshot.get("items", []) or [])[:limit]
                if str(item.get("sa_label", "") or "")
            ]

        before_labels = _labels(state_snapshot_before_action)
        after_labels = _labels(state_snapshot_after_output)
        output_events = list((text_output_trace or {}).get("recent_events", []) or [])
        revision_events = list((text_output_trace or {}).get("revision_events", []) or [])
        text_parameter_events = self.text_actuator.parameter_events(output_events)
        output_item_labels = [
            str(item.get("sa_label", "") or "")
            for item in (text_output_trace or {}).get("output_items", []) or []
            if str(item.get("sa_label", "") or "")
        ]
        return {
            "schema_id": "action_causal_window/v1",
            "tick_index": int(self.tick_index),
            "action_ids": action_ids,
            "before_top_labels": before_labels,
            "after_top_labels": after_labels,
            "entered_labels": [label for label in after_labels if label not in set(before_labels)][:8],
            "control_labels": [str(item.get("sa_label", "") or "") for item in (control_items or [])[:8]],
            "action_control_effects": [
                dict((item.get("anchor_meta", {}) or {}))
                for item in (control_items or [])[:12]
                if str((item.get("anchor_meta", {}) or {}).get("schema_id", "") or "").endswith("_control/v1")
            ],
            "visual_gaze_events": [
                dict(event)
                for event in (feedback_context or {}).get("visual_gaze_events", []) or []
                if isinstance(event, dict)
            ][:8],
            "auditory_band_events": [
                dict(event)
                for event in (feedback_context or {}).get("auditory_band_events", []) or []
                if isinstance(event, dict)
            ][:8],
            "text_parameter_events": [dict(event) for event in text_parameter_events if isinstance(event, dict)][:8],
            "visual_gaze_state": self.visual_gaze_actuator.state(),
            "auditory_band_state": self.auditory_band_actuator.state(),
            "action_item_labels": [str(item.get("sa_label", "") or "") for item in (action_items or [])[:8]],
            "focus_labels_after_control": list((feedback_context or {}).get("focus_labels_after_control", []) or [])[
                :8
            ],
            "top_labels_after_control": list((feedback_context or {}).get("top_labels_after_control", []) or [])[:8],
            "text_output": {
                "visible_text": str((text_output_trace or {}).get("visible_text", "") or ""),
                "expected_token": str((text_output_trace or {}).get("expected_token", "") or ""),
                "revision_detected": bool((text_output_trace or {}).get("revision_detected", False)),
                "output_item_labels": output_item_labels[:8],
                "recent_events": output_events[:6],
                "revision_events": revision_events[:6],
            },
        }

    def _observe_action_feedback(self, *, selected_actions: list[dict], feedback_context: dict) -> dict:
        top_labels = [
            str(label or "")
            for label in (feedback_context.get("top_labels_after_control", []) or [])
            if str(label or "")
        ]
        focus_labels = [
            str(label or "")
            for label in (feedback_context.get("focus_labels_after_control", []) or [])
            if str(label or "")
        ]
        reward = 0.0
        punishment = 0.0
        correctness = 0.0
        confidence = 0.24
        notes = []
        for row in selected_actions:
            action_id = str(row.get("action_id", "") or "")
            predicted = dict(row.get("predicted_outcome", {}) or {})
            confidence = max(confidence, float(predicted.get("confidence", 0.0) or 0.0))
            if action_id == "action::continue_focus":
                matched = len([label for label in focus_labels if label in top_labels[:5]])
                reward += 0.18 + matched * 0.05
                correctness += 0.16 + matched * 0.06
                punishment += 0.04 if matched == 0 else 0.0
                notes.append("continue_focus_alignment")
            elif action_id == "action::inspect_residual":
                mismatch_labels = [
                    label
                    for label in top_labels
                    if label.startswith("feeling::dissonance") or label.startswith("feeling::surprise")
                ]
                reward += 0.08 + min(0.12, len(mismatch_labels) * 0.04)
                correctness += 0.06
                punishment += 0.12 + min(0.18, max(0, len(top_labels) - 3) * 0.03)
                notes.append("residual_probe_cost")
            elif action_id == "action::replay_recent_context":
                text_hits = len(
                    [label for label in top_labels[:6] if label.startswith("text::") or label.startswith("phrase::")]
                )
                reward += 0.22 + text_hits * 0.04
                correctness += 0.18 + text_hits * 0.03
                punishment += 0.03
                notes.append("replay_context_recovery")
            elif action_id == "action::recall_by_expectation":
                anchor_labels = [
                    label
                    for label in top_labels[:8]
                    if not label.startswith(("action::", "action_feedback::", "expectation_pressure::", "feeling::"))
                ]
                pressure_anchor = any(
                    str(anchor.get("anchor_type", "") or "") == "pressure"
                    for anchor in list(row.get("supporting_anchors", []) or [])
                )
                reward += 0.12 + min(0.18, len(anchor_labels) * 0.035)
                correctness += 0.10 + min(0.18, len(anchor_labels) * 0.03)
                punishment += 0.08 if pressure_anchor else 0.035
                notes.append("expectation_anchor_recall")
            elif action_id in {
                "action::move_gaze_to",
                "action::nudge_gaze",
                "action::scan_visual_field",
                "action::hold_gaze",
            }:
                reward += 0.10 + min(
                    0.12, len([label for label in top_labels[:8] if label.startswith("vision::")]) * 0.04
                )
                correctness += 0.08
                punishment += 0.03
                notes.append("visual_gaze_control")
            elif action_id in {"action::zoom_visual_focus", "action::widen_visual_focus"}:
                reward += 0.09
                correctness += 0.07
                punishment += 0.035
                notes.append("visual_focus_scale_control")
            elif action_id in {
                "action::slide_audio_band",
                "action::lock_audio_band",
                "action::narrow_audio_band",
                "action::widen_audio_band",
            }:
                reward += 0.10 + min(
                    0.12, len([label for label in top_labels[:8] if label.startswith("audio::")]) * 0.04
                )
                correctness += 0.08
                punishment += 0.035
                notes.append("auditory_band_control")
            elif action_id == "action::stabilize_prediction":
                predicted_mass = len(
                    [label for label in top_labels[:6] if label.startswith("text::") or label.startswith("phrase::")]
                )
                reward += 0.16 + predicted_mass * 0.03
                correctness += 0.14 + predicted_mass * 0.025
                punishment += 0.05
                notes.append("prediction_stabilization")
            elif action_id == "action::wait":
                wait_controls = [
                    dict(effect)
                    for effect in list((feedback_context.get("action_control_effects", []) or []))
                    if dict(effect).get("control_kind") == "wait"
                    or dict(effect).get("schema_id") == "timing_wait_control/v1"
                ]
                wait_meta = wait_controls[0] if wait_controls else {}
                wait_intensity = float(wait_meta.get("wait_intensity", row.get("effective_decisiveness", 0.0)) or 0.0)
                rhythm_expectation = float(wait_meta.get("rhythm_expectation", 0.0) or 0.0)
                uncertainty = float(wait_meta.get("uncertainty", 0.0) or 0.0)
                reward += 0.05 + min(0.12, rhythm_expectation * 0.08 + uncertainty * 0.07 + wait_intensity * 0.06)
                punishment += max(0.015, 0.04 - rhythm_expectation * 0.012)
                correctness += 0.025 + min(0.10, rhythm_expectation * 0.06 + uncertainty * 0.04)
                notes.append("timing_wait_semantics")
                if rhythm_expectation > 0.0:
                    notes.append("wait_rhythm_phase_guard")
                if uncertainty > 0.0:
                    notes.append("wait_uncertainty_buffer")
        return {
            "reward": round(reward, 4),
            "punishment": round(punishment, 4),
            "correctness": round(correctness, 4),
            "confidence": round(min(1.0, confidence), 4),
            "notes": notes,
        }

    def _build_action_feedback_items(
        self,
        *,
        selected_actions: list[dict],
        observed_feedback: dict,
        planner_feedback: dict,
        causal_window: dict | None = None,
    ) -> list[dict]:
        items = []
        reward_energy = float(observed_feedback.get("reward", 0.0) or 0.0)
        punishment_energy = float(observed_feedback.get("punishment", 0.0) or 0.0)
        correctness_energy = float(observed_feedback.get("correctness", 0.0) or 0.0)
        confidence = float(observed_feedback.get("confidence", 0.0) or 0.0)
        pressure_energy = max(0.0, punishment_energy * 0.82 - reward_energy * 0.18 - correctness_energy * 0.08)
        for row in selected_actions:
            action_name = str(row.get("action_id", "") or "").split("::")[-1]
            action_id = str(row.get("action_id", "") or "")
            outcome_estimates = list(
                ((planner_feedback or {}).get("outcome_memory", {}) or {}).get("estimates", []) or []
            )
            outcome_estimate = next(
                (dict(item) for item in outcome_estimates if str(item.get("action_id", "") or "") == action_id), {}
            )
            items.append(
                {
                    "sa_label": f"action_feedback::{action_name}",
                    "display_text": f"行动反馈:{action_name}",
                    "source_type": "action_feedback",
                    "family": "action_feedback",
                    "real_energy": round(reward_energy + correctness_energy * 0.35, 4),
                    "virtual_energy": round(punishment_energy + pressure_energy * 0.55, 4),
                    "anchor_meta": {
                        "action_id": action_id,
                        "observed_feedback": dict(observed_feedback),
                        "planner_feedback": dict(planner_feedback or {}),
                        "predicted_outcome": dict(row.get("predicted_outcome", {}) or {}),
                        "consequence_estimate": dict(row.get("consequence_estimate", {}) or {}),
                        "outcome_memory_estimate": outcome_estimate,
                        "feedback_energy_semantics": {
                            "schema_id": "action_feedback_energy/v1",
                            "real_energy": round(reward_energy + correctness_energy * 0.35, 4),
                            "virtual_energy": round(punishment_energy + pressure_energy * 0.55, 4),
                            "punishment_pressure": round(pressure_energy, 4),
                            "confidence": round(confidence, 4),
                            "meaning": "reward_correctness_as_real;punishment_pressure_as_virtual_drive_shaping",
                        },
                        "causal_window": dict(causal_window or {}),
                    },
                }
            )
        return items

    def _structured_action_outcome_events(
        self,
        *,
        selected_actions: list[dict],
        observed_feedback: dict,
        planner_feedback: dict,
        parameter_events: list[dict] | None = None,
    ) -> list[dict]:
        events = []
        selected = [dict(row) for row in list(selected_actions or []) if isinstance(row, dict)]
        if not selected and not observed_feedback:
            return []
        reward = float((observed_feedback or {}).get("reward", 0.0) or 0.0)
        punishment = float((observed_feedback or {}).get("punishment", 0.0) or 0.0)
        correctness = float((observed_feedback or {}).get("correctness", 0.0) or 0.0)
        confidence = float((observed_feedback or {}).get("confidence", 0.0) or 0.0)
        if not selected:
            selected = [{"action_id": "action::external_feedback_context", "predicted_outcome": {}}]
        outcome_estimates = list(((planner_feedback or {}).get("outcome_memory", {}) or {}).get("estimates", []) or [])
        for row in selected:
            action_id = str(row.get("action_id", "") or "")
            if not action_id:
                continue
            outcome_estimate = next(
                (dict(item) for item in outcome_estimates if str(item.get("action_id", "") or "") == action_id), {}
            )
            parameter_event_rows = [
                dict(event)
                for event in list(parameter_events or [])
                if isinstance(event, dict) and str(event.get("action_id", "") or "") == action_id
            ]
            parameter_estimates = list((planner_feedback or {}).get("parameter_estimates", []) or [])
            parameter_estimate = next(
                (
                    dict(item)
                    for item in parameter_estimates
                    if isinstance(item, dict) and str(item.get("action_id", "") or "") == action_id
                ),
                {},
            )
            predicted = dict(row.get("predicted_outcome", {}) or {})
            predicted_utility = (
                float(predicted.get("reward", 0.0) or 0.0)
                + float(predicted.get("correctness", 0.0) or 0.0) * 0.42
                - float(predicted.get("punishment", 0.0) or 0.0) * 1.08
                - float(predicted.get("pressure", 0.0) or 0.0) * 0.28
            )
            observed_utility = reward + correctness * 0.42 - punishment * 1.08
            prediction_error = abs(observed_utility - predicted_utility) if predicted else 0.0
            events.append(
                self.learning_event_builder.build(
                    event_type="action_outcome",
                    learning_layer="action_outcome_memory",
                    writer="ActionOutcomeMemory.record",
                    source=action_id,
                    target="observed_feedback",
                    relation="action_outcome",
                    weight=round(min(1.0, reward + punishment + correctness * 0.7 + prediction_error * 0.3), 4),
                    tick_index=self.tick_index,
                    bc_rule_id="BC-004",
                    write_mode="direct_action_outcome_update"
                    if action_id != "action::external_feedback_context"
                    else "feedback_signal_only",
                    evidence={
                        "observed_feedback": dict(observed_feedback or {}),
                        "predicted_outcome": predicted,
                        "observed_utility": round(observed_utility, 4),
                        "predicted_utility": round(predicted_utility, 4),
                        "prediction_error": round(prediction_error, 4),
                        "outcome_memory_estimate": outcome_estimate,
                        "action_params": dict(row.get("params", {}) or {}),
                        "parameter_events": parameter_event_rows[:4],
                        "parameter_memory_estimate": parameter_estimate,
                    },
                    guards=self.learning_event_builder.concept_guards(),
                    meaning="reward and punishment shape action drive; parameterized actuator evidence can shape future action parameters without writing concept similarity",
                )
            )
        return events

    def _extract_replay_labels(self, *, fast_bn: list[dict], slow_bn: list[dict], focus_labels: list[str]) -> list[str]:
        labels = []
        seen = set()
        for label in focus_labels:
            if label and label not in seen and self._is_core_trace_label(label):
                seen.add(label)
                labels.append(label)
        for branch in list(slow_bn) + list(fast_bn):
            snapshot = dict(branch.get("snapshot", {}) or {})
            if snapshot:
                candidate_labels = [
                    str((item or {}).get("sa_label", "") or "")
                    for item in (
                        snapshot.get("state_field_items", [])
                        or snapshot.get("core_items", [])
                        or snapshot.get("items", [])
                        or []
                    )
                ]
            else:
                preview = dict(branch.get("snapshot_preview", {}) or {})
                candidate_labels = [str(label or "") for label in (preview.get("labels", []) or [])]
            for label in candidate_labels:
                if label and label not in seen and self._is_core_trace_label(label):
                    seen.add(label)
                    labels.append(label)
        return labels

    def _extract_predicted_labels(self, *, fast_cn: list[dict], slow_cn: list[dict]) -> list[str]:
        labels = []
        seen = set()
        for branch in list(slow_cn) + list(fast_cn):
            for item in branch.get("predicted_items", []) or []:
                label = str((item or {}).get("sa_label", "") or "")
                if label and label not in seen and self._is_core_trace_label(label):
                    seen.add(label)
                    labels.append(label)
        return labels

    def _is_core_trace_label(self, label: str) -> bool:
        clean = str(label or "")
        if not clean:
            return False
        return True

    def _write_memory_snapshots(
        self,
        state_snapshot: dict,
        source_text: str,
        focus_labels: list[str],
        *,
        asset_refs: list[dict] | None = None,
        state_snapshot_for_memory: dict | None = None,
    ) -> None:
        # IMPORTANT: Memory write must not drop current-tick external evidence.
        # Use a dedicated snapshot view policy for memory write.
        state_snapshot_for_memory = dict(state_snapshot_for_memory or self.state_pool.snapshot_for_memory_write())
        state_asset_refs = self._dedupe_asset_refs(
            list(asset_refs or []) + self._asset_refs_from_items(state_snapshot_for_memory.get("items", []))
        )
        self.memory.write_snapshot(
            tick_index=self.tick_index,
            memory_kind="state",
            items=state_snapshot_for_memory["items"],
            focus_labels=focus_labels,
            source_text=source_text,
            asset_refs=state_asset_refs,
        )
        focus_items = self.state_pool.rows_for_labels(focus_labels)
        focus_asset_refs = self._dedupe_asset_refs(list(asset_refs or []) + self._asset_refs_from_items(focus_items))
        self.memory.write_snapshot(
            tick_index=self.tick_index,
            memory_kind="focus",
            items=focus_items,
            focus_labels=focus_labels,
            source_text=source_text,
            asset_refs=focus_asset_refs,
        )

    def _asset_refs_from_items(self, items: list[dict]) -> list[dict]:
        refs: list[dict] = []
        for item in items or []:
            if not isinstance(item, dict):
                continue
            meta = dict(item.get("anchor_meta", {}) or {})
            refs.extend([dict(ref) for ref in list(meta.get("asset_refs", []) or []) if isinstance(ref, dict)])
        return self._dedupe_asset_refs(refs)

    def _build_time_context(self, time_trace: dict) -> dict | None:
        dominant = dict(time_trace.get("dominant_peak", {}) or {})
        items = list(time_trace.get("items", []) or [])
        if not dominant:
            return None
        felt_energy = float(items[0].get("real_energy", 0.0) or 0.0) if items else 0.0
        return {
            "current_tick": self.tick_index,
            "target_delta_t": dominant.get("center_delta_t"),
            "time_sigma": max(1.0, float(dominant.get("sigma", 1.0) or 1.0)),
            "confidence": float(dominant.get("confidence", 0.0) or 0.0),
            "gain": self.config.time_feeling.recall_gain,
            "felt_energy": felt_energy,
        }

    def _merge_feelings_with_expectation_pressure(self, feeling_trace: dict, expectation_pressure_trace: dict) -> dict:
        merged = dict(feeling_trace or {})
        channels = dict(merged.get("channels", {}) or {})
        ep_channels = dict((expectation_pressure_trace or {}).get("channels", {}) or {})
        if ep_channels:
            channels["expectation"] = max(
                float(channels.get("expectation", 0.0) or 0.0),
                float(ep_channels.get("expectation_level", 0.0) or 0.0),
            )
            channels["pressure"] = max(
                float(channels.get("pressure", 0.0) or 0.0),
                float(ep_channels.get("pressure_level", 0.0) or 0.0),
            )
            channels["correctness"] = max(
                float(channels.get("correctness", 0.0) or 0.0),
                float(ep_channels.get("satisfaction_level", 0.0) or 0.0) * 0.62,
            )
        merged["channels"] = channels
        merged["expectation_pressure_coupling"] = {
            "expectation_level": float(ep_channels.get("expectation_level", 0.0) or 0.0),
            "pressure_level": float(ep_channels.get("pressure_level", 0.0) or 0.0),
            "satisfaction_level": float(ep_channels.get("satisfaction_level", 0.0) or 0.0),
            "expectation_gap": float(ep_channels.get("expectation_gap", 0.0) or 0.0),
        }
        return merged

    def _merge_feelings_with_runtime_load(self, feeling_trace: dict, runtime_load_trace: dict) -> dict:
        merged = dict(feeling_trace or {})
        channels = dict(merged.get("channels", {}) or {})
        load_channels = dict((runtime_load_trace or {}).get("channels", {}) or {})
        if load_channels:
            channels["complexity"] = max(
                float(channels.get("complexity", 0.0) or 0.0),
                float(load_channels.get("complexity", 0.0) or 0.0),
            )
            channels["simplicity"] = max(
                float(channels.get("simplicity", 0.0) or 0.0),
                float(load_channels.get("simplicity", 0.0) or 0.0),
            )
        merged["channels"] = channels
        existing_items = list(merged.get("items", []) or [])
        load_items = list((runtime_load_trace or {}).get("items", []) or [])
        if load_items:
            seen = {str((item or {}).get("sa_label", "") or "") for item in existing_items if isinstance(item, dict)}
            for item in load_items:
                label = str((item or {}).get("sa_label", "") or "")
                if label and label not in seen:
                    existing_items.append(dict(item))
                    seen.add(label)
        merged["items"] = existing_items
        merged["runtime_load_coupling"] = {
            "schema_id": "runtime_load_feeling_coupling/v1",
            "complexity": float(load_channels.get("complexity", 0.0) or 0.0),
            "simplicity": float(load_channels.get("simplicity", 0.0) or 0.0),
            "load_ratio": float(load_channels.get("load_ratio", 0.0) or 0.0),
            "suggested_modulation": dict((runtime_load_trace or {}).get("suggested_modulation", {}) or {}),
        }
        return merged

    def _merge_feelings_with_task_feeling(self, feeling_trace: dict, task_feeling_trace: dict) -> dict:
        merged = dict(feeling_trace or {})
        channels = dict(merged.get("channels", {}) or {})
        task_channels = dict((task_feeling_trace or {}).get("channels", {}) or {})
        for key in ("boredom", "fulfillment", "task_available", "unfinished_strength"):
            if key in task_channels:
                channels[key] = max(float(channels.get(key, 0.0) or 0.0), float(task_channels.get(key, 0.0) or 0.0))
        merged["channels"] = channels
        existing_items = list(merged.get("items", []) or [])
        task_items = list((task_feeling_trace or {}).get("items", []) or [])
        if task_items:
            seen = {str((item or {}).get("sa_label", "") or "") for item in existing_items if isinstance(item, dict)}
            for item in task_items:
                label = str((item or {}).get("sa_label", "") or "")
                if label and label not in seen:
                    existing_items.append(dict(item))
                    seen.add(label)
        merged["items"] = existing_items
        merged["task_feeling_coupling"] = {
            "schema_id": "task_feeling_coupling/v1",
            "channels": task_channels,
            "policy": str((task_feeling_trace or {}).get("policy", "") or ""),
        }
        return merged

    def _build_thought_view(
        self,
        *,
        fast_bn: list[dict],
        fast_cn: list[dict],
        slow_bn: list[dict],
        slow_cn: list[dict],
        attention_trace: dict,
        feeling_trace: dict,
        runtime_load_trace: dict | None = None,
        focus_continuation_trace: dict | None = None,
        expectation_pressure_trace: dict | None = None,
        text_output_trace: dict | None = None,
    ) -> dict:
        return {
            "fast": {
                "bn": fast_bn,
                "cn": fast_cn,
            },
            "slow": {
                "bn_prime": slow_bn,
                "cn_prime": slow_cn,
            },
            "focus_reason": {
                "selected_labels": list(attention_trace.get("selected_labels", []) or []),
                "ranked_items": list(attention_trace.get("ranked_items", []) or [])[:5],
                "continuation": self._compact_focus_continuation_trace(focus_continuation_trace or {}),
                "focus_order": dict(attention_trace.get("focus_order", {}) or {}),
            },
            "feelings": {
                "channels": dict(feeling_trace.get("channels", {}) or {}),
                "items": list(feeling_trace.get("items", []) or []),
                "prediction_coupling": dict(feeling_trace.get("prediction_coupling", {}) or {}),
            },
            "runtime_load": {
                "channels": dict((runtime_load_trace or {}).get("channels", {}) or {}),
                "components": dict((runtime_load_trace or {}).get("components", {}) or {}),
                "suggested_modulation": dict((runtime_load_trace or {}).get("suggested_modulation", {}) or {}),
            },
            "expectation_pressure": {
                "channels": dict((expectation_pressure_trace or {}).get("channels", {}) or {}),
                "field_state": dict((expectation_pressure_trace or {}).get("field_state", {}) or {}),
                "items": list((expectation_pressure_trace or {}).get("items", []) or []),
                "anchor_verification": dict((expectation_pressure_trace or {}).get("anchor_verification", {}) or {}),
            },
            "text_output": {
                "visible_text": str((text_output_trace or {}).get("visible_text", "") or ""),
                "recent_events": list((text_output_trace or {}).get("recent_events", []) or [])[:6],
                "revision_events": list((text_output_trace or {}).get("revision_events", []) or [])[:6],
            },
        }

    def _build_runtime_thought_refs(
        self,
        *,
        fast_bn: list[dict],
        fast_cn: list[dict],
        slow_bn: list[dict],
        slow_cn: list[dict],
        attention_trace: dict,
        feeling_trace: dict,
        runtime_load_trace: dict | None = None,
        focus_continuation_trace: dict | None = None,
        expectation_pressure_trace: dict | None = None,
        text_output_trace: dict | None = None,
    ) -> dict:
        return {
            "mode": "runtime_refs",
            "rebuild_policy": "observatory_reconstructs_details_by_snapshot_ref",
            "fast": {
                "bn_refs": [dict(row.get("snapshot_ref", {}) or {}) for row in list(fast_bn or [])[:4]],
                "cn_refs": [self._cn_ref(row) for row in list(fast_cn or [])[:4]],
            },
            "slow": {
                "bn_prime_refs": [dict(row.get("snapshot_ref", {}) or {}) for row in list(slow_bn or [])[:4]],
                "cn_prime_refs": [self._cn_ref(row) for row in list(slow_cn or [])[:4]],
            },
            "focus_reason": {
                "selected_labels": list(attention_trace.get("selected_labels", []) or []),
                "focus_order": dict(attention_trace.get("focus_order", {}) or {}),
                "active_episode_id": int((focus_continuation_trace or {}).get("active_episode_id", -1) or -1),
                "replay_candidates": list((focus_continuation_trace or {}).get("replay_candidates", []) or [])[:4],
            },
            "feelings": {
                "channels": dict(feeling_trace.get("channels", {}) or {}),
            },
            "runtime_load": {
                "channels": dict((runtime_load_trace or {}).get("channels", {}) or {}),
                "suggested_modulation": dict((runtime_load_trace or {}).get("suggested_modulation", {}) or {}),
            },
            "expectation_pressure": {
                "channels": dict((expectation_pressure_trace or {}).get("channels", {}) or {}),
                "field_state": dict((expectation_pressure_trace or {}).get("field_state", {}) or {}),
                "anchor_verification": dict((expectation_pressure_trace or {}).get("anchor_verification", {}) or {}),
            },
            "text_output": {
                "visible_text": str((text_output_trace or {}).get("visible_text", "") or ""),
                "revision_detected": bool((text_output_trace or {}).get("revision_detected", False)),
            },
        }

    def _build_runtime_explainability_refs(
        self,
        *,
        state_snapshot: dict,
        fast_bn: list[dict],
        slow_bn: list[dict],
        attention_trace: dict,
        feeling_trace: dict,
        runtime_load_trace: dict | None,
        expectation_pressure_trace: dict | None,
        action_trace: dict,
        action_consequence_trace: dict | None,
        emotion_update_trace: dict | None,
        emotion_modulation: dict | None,
        prior_emotion_modulation: dict | None,
        text_output_trace: dict | None,
        focus_continuation_trace: dict | None = None,
        innate_traces: dict | None = None,
    ) -> dict:
        state_items = list(state_snapshot.get("items", []) or [])[:6]
        return {
            "mode": "runtime_refs",
            "rebuild_policy": "full_whitebox_is_rebuilt_after_tick_from_snapshot_ref_and_memory_store",
            "state_pool": {
                "top_energy_rows": [
                    {
                        "sa_label": str(item.get("sa_label", "") or ""),
                        "real_energy": float(item.get("real_energy", 0.0) or 0.0),
                        "virtual_energy": float(item.get("virtual_energy", 0.0) or 0.0),
                        "cognitive_pressure": float(item.get("cognitive_pressure", 0.0) or 0.0),
                    }
                    for item in state_items
                ],
                "prediction_trace": dict(
                    state_snapshot.get("prediction_trace", {}) or self.state_pool.prediction_trace()
                ),
                "residual_summary": dict(
                    state_snapshot.get("residual_summary", {}) or self.state_pool.residual_summary(limit=8)
                ),
                "energy_flow": dict(state_snapshot.get("energy_flow", {}) or {}),
            },
            "focus": {
                "selected_labels": list(attention_trace.get("selected_labels", []) or []),
                "focus_order": dict(attention_trace.get("focus_order", {}) or {}),
                "continuation": self._compact_focus_continuation_trace(focus_continuation_trace or {}),
            },
            "fast_bn": [self._bn_ref(row) for row in list(fast_bn or [])[:4]],
            "slow_bn": [self._bn_ref(row) for row in list(slow_bn or [])[:4]],
            "feelings": {
                "channels": dict(feeling_trace.get("channels", {}) or {}),
                "prediction_coupling": dict(feeling_trace.get("prediction_coupling", {}) or {}),
            },
            "runtime_load": {
                "channels": dict((runtime_load_trace or {}).get("channels", {}) or {}),
                "components": dict((runtime_load_trace or {}).get("components", {}) or {}),
                "suggested_modulation": dict((runtime_load_trace or {}).get("suggested_modulation", {}) or {}),
            },
            "expectation_pressure": {
                "channels": dict((expectation_pressure_trace or {}).get("channels", {}) or {}),
                "field_state": dict((expectation_pressure_trace or {}).get("field_state", {}) or {}),
                "anchor_verification": dict((expectation_pressure_trace or {}).get("anchor_verification", {}) or {}),
            },
            "emotion": {
                "state": dict((emotion_update_trace or {}).get("emotion_state", {}) or {}),
                "cfs_deltas": dict((emotion_update_trace or {}).get("cfs_deltas", {}) or {}),
                "rwd_pun_deltas": dict((emotion_update_trace or {}).get("rwd_pun_deltas", {}) or {}),
                "innate_deltas": dict((emotion_update_trace or {}).get("innate_deltas", {}) or {}),
                "modulation": dict(emotion_modulation or {}),
                "prior_attention_modulation": dict((prior_emotion_modulation or {}).get("attention", {}) or {}),
            },
            "innate_rules": self._compact_innate_traces(innate_traces or {}),
            "action": {
                "consequence_trace": dict(action_consequence_trace or {}),
                "competition_trace": dict(action_trace.get("competition_trace", {}) or {}),
                "safety_gate": dict(action_trace.get("safety_gate", {}) or {}),
                "visual_gaze": dict(action_trace.get("visual_gaze", {}) or {}),
                "auditory_band": dict(action_trace.get("auditory_band", {}) or {}),
                "selected_actions": [
                    {
                        "action_id": str(item.get("action_id", "") or ""),
                        "drive": float(item.get("drive", 0.0) or 0.0),
                        "utility": float(item.get("utility", 0.0) or 0.0),
                        "predicted_outcome": dict(item.get("predicted_outcome", {}) or {}),
                        "consequence_estimate": dict(item.get("consequence_estimate", {}) or {}),
                    }
                    for item in list(action_trace.get("selected_actions", []) or [])[:4]
                ],
            },
            "text_output": {
                "visible_text": str((text_output_trace or {}).get("visible_text", "") or ""),
                "revision_detected": bool((text_output_trace or {}).get("revision_detected", False)),
            },
        }

    def _bn_ref(self, row: dict) -> dict:
        score_breakdown = dict((row or {}).get("score_breakdown", {}) or {})
        numeric_components = []
        for name, value in score_breakdown.items():
            try:
                numeric_components.append((str(name), float(value or 0.0)))
            except (TypeError, ValueError):
                continue
        components = sorted(numeric_components, key=lambda item: (-float(item[1] or 0.0), item[0]))
        return {
            "memory_id": str((row or {}).get("memory_id", "") or ""),
            "tick_index": int((row or {}).get("tick_index", -1) or -1),
            "memory_kind": str((row or {}).get("memory_kind", "") or ""),
            "score": float((row or {}).get("score", 0.0) or 0.0),
            "normalized_weight": float((row or {}).get("normalized_weight", 0.0) or 0.0),
            "match_efficiency": float((row or {}).get("match_efficiency", 0.0) or 0.0),
            "grasp_confidence": float((row or {}).get("grasp_confidence", 0.0) or 0.0),
            "b_real_energy": float((row or {}).get("b_real_energy", 0.0) or 0.0),
            "b_virtual_energy": float((row or {}).get("b_virtual_energy", 0.0) or 0.0),
            "b_effective_real_energy": float((row or {}).get("b_effective_real_energy", 0.0) or 0.0),
            "b_effective_virtual_energy": float((row or {}).get("b_effective_virtual_energy", 0.0) or 0.0),
            "snapshot_ref": dict((row or {}).get("snapshot_ref", {}) or {}),
            "snapshot_preview": dict((row or {}).get("snapshot_preview", {}) or {}),
            "candidate_sources": list((row or {}).get("candidate_sources", []) or []),
            "top_score_components": [{"name": name, "value": value} for name, value in components[:5]],
            "relative_relation_score": float((row or {}).get("relative_relation_score", 0.0) or 0.0),
            "relation_channels": dict((row or {}).get("relation_channels", {}) or {}),
            "learned_score": float((row or {}).get("learned_score", 0.0) or 0.0),
        }

    def _cn_ref(self, row: dict) -> dict:
        return {
            "source_memory_id": str((row or {}).get("source_memory_id", "") or ""),
            "successor_memory_id": str((row or {}).get("successor_memory_id", "") or ""),
            "score": float((row or {}).get("score", 0.0) or 0.0),
            "source_b_weight": float((row or {}).get("source_b_weight", 0.0) or 0.0),
            "source_b_match_efficiency": float((row or {}).get("source_b_match_efficiency", 0.0) or 0.0),
            "successor_normalized_weight": float((row or {}).get("successor_normalized_weight", 0.0) or 0.0),
            "energy_transfer_multiplier": float((row or {}).get("energy_transfer_multiplier", 0.0) or 0.0),
            "energy_transfer": dict((row or {}).get("energy_transfer", {}) or {}),
            "predicted_label_count": len((row or {}).get("predicted_items", []) or []),
        }

    def _build_explainability(
        self,
        *,
        state_snapshot: dict,
        fast_bn: list[dict],
        fast_cn: list[dict],
        slow_bn: list[dict],
        slow_cn: list[dict],
        attention_trace: dict,
        feeling_trace: dict,
        runtime_load_trace: dict | None,
        time_trace: dict,
        rhythm_trace: dict,
        action_trace: dict,
        action_feedback_trace: dict,
        action_consequence_trace: dict | None = None,
        expectation_pressure_trace: dict | None = None,
        text_output_trace: dict | None = None,
        emotion_update_trace: dict | None = None,
        emotion_modulation: dict | None = None,
        prior_emotion_modulation: dict | None = None,
        focus_continuation_trace: dict | None = None,
        innate_traces: dict | None = None,
    ) -> dict:
        return {
            "state_pool": {
                "top_energy_rows": [
                    {
                        "sa_label": str(item.get("sa_label", "") or ""),
                        "real_energy": float(item.get("real_energy", 0.0) or 0.0),
                        "virtual_energy": float(item.get("virtual_energy", 0.0) or 0.0),
                        "cognitive_pressure": float(item.get("cognitive_pressure", 0.0) or 0.0),
                        "is_focus": bool((item.get("anchor_meta", {}) or {}).get("is_focus", False)),
                    }
                    for item in (state_snapshot.get("items", []) or [])[:6]
                ],
                "prediction_trace": dict(
                    state_snapshot.get("prediction_trace", {}) or self.state_pool.prediction_trace()
                ),
                "residual_summary": dict(
                    state_snapshot.get("residual_summary", {}) or self.state_pool.residual_summary(limit=8)
                ),
            },
            "focus": {
                "selected_labels": list(attention_trace.get("selected_labels", []) or []),
                "focus_order": dict(attention_trace.get("focus_order", {}) or {}),
                "continuation": self._compact_focus_continuation_trace(focus_continuation_trace or {}),
                "ranked_items": [
                    {
                        "sa_label": str(item.get("sa_label", "") or ""),
                        "focus_score": float(item.get("focus_score", 0.0) or 0.0),
                        "continuation_bonus": float(item.get("continuation_bonus", 0.0) or 0.0),
                        "cognitive_pressure": float(item.get("cognitive_pressure", 0.0) or 0.0),
                    }
                    for item in (attention_trace.get("ranked_items", []) or [])[:6]
                ],
            },
            "fast_bn": [self._bn_reason(row) for row in fast_bn[:4]],
            "slow_bn": [self._bn_reason(row) for row in slow_bn[:4]],
            "fast_cn": [self._cn_reason(row) for row in fast_cn[:4]],
            "slow_cn": [self._cn_reason(row) for row in slow_cn[:4]],
            "feelings": {
                "channels": dict(feeling_trace.get("channels", {}) or {}),
                "prediction_coupling": dict(feeling_trace.get("prediction_coupling", {}) or {}),
                "items": [
                    {
                        "sa_label": str(item.get("sa_label", "") or ""),
                        "real_energy": float(item.get("real_energy", 0.0) or 0.0),
                        "anchor_meta": dict(item.get("anchor_meta", {}) or {}),
                    }
                    for item in (feeling_trace.get("items", []) or [])[:8]
                ],
            },
            "runtime_load": {
                "channels": dict((runtime_load_trace or {}).get("channels", {}) or {}),
                "components": dict((runtime_load_trace or {}).get("components", {}) or {}),
                "items": [
                    {
                        "sa_label": str(item.get("sa_label", "") or ""),
                        "real_energy": float(item.get("real_energy", 0.0) or 0.0),
                        "anchor_meta": dict(item.get("anchor_meta", {}) or {}),
                    }
                    for item in ((runtime_load_trace or {}).get("items", []) or [])[:4]
                ],
                "suggested_modulation": dict((runtime_load_trace or {}).get("suggested_modulation", {}) or {}),
            },
            "expectation_pressure": {
                "channels": dict((expectation_pressure_trace or {}).get("channels", {}) or {}),
                "field_state": dict((expectation_pressure_trace or {}).get("field_state", {}) or {}),
                "anchor_verification": dict((expectation_pressure_trace or {}).get("anchor_verification", {}) or {}),
                "items": [
                    {
                        "sa_label": str(item.get("sa_label", "") or ""),
                        "real_energy": float(item.get("real_energy", 0.0) or 0.0),
                        "anchor_meta": dict(item.get("anchor_meta", {}) or {}),
                    }
                    for item in ((expectation_pressure_trace or {}).get("items", []) or [])[:8]
                ],
            },
            "time": {
                "channels": dict(time_trace.get("channels", {}) or {}),
                "dominant_peak": dict(time_trace.get("dominant_peak", {}) or {}),
            },
            "rhythm": {
                "channels": dict(rhythm_trace.get("channels", {}) or {}),
                "family": dict(rhythm_trace.get("family", {}) or {}),
            },
            "emotion": {
                "state": dict((emotion_update_trace or {}).get("emotion_state", {}) or {}),
                "cfs_deltas": dict((emotion_update_trace or {}).get("cfs_deltas", {}) or {}),
                "rwd_pun_deltas": dict((emotion_update_trace or {}).get("rwd_pun_deltas", {}) or {}),
                "innate_deltas": dict((emotion_update_trace or {}).get("innate_deltas", {}) or {}),
                "modulation": dict(emotion_modulation or {}),
                "prior_attention_modulation": dict((prior_emotion_modulation or {}).get("attention", {}) or {}),
            },
            "innate_rules": self._compact_innate_traces(innate_traces or {}),
            "action": {
                "consequence_trace": dict(action_consequence_trace or action_trace.get("consequence_trace", {}) or {}),
                "competition_trace": dict(action_trace.get("competition_trace", {}) or {}),
                "causal_window": dict(action_trace.get("causal_window", {}) or {}),
                "safety_gate": dict(action_trace.get("safety_gate", {}) or {}),
                "selected_actions": [
                    {
                        "action_id": str(item.get("action_id", "") or ""),
                        "drive": float(item.get("drive", 0.0) or 0.0),
                        "utility": float(item.get("utility", 0.0) or 0.0),
                        "predicted_outcome": dict(item.get("predicted_outcome", {}) or {}),
                        "consequence_estimate": dict(item.get("consequence_estimate", {}) or {}),
                        "notes": list(item.get("notes", []) or []),
                    }
                    for item in (action_trace.get("selected_actions", []) or [])[:4]
                ],
                "top_candidates": [
                    {
                        "action_id": str(item.get("action_id", "") or ""),
                        "drive": float(item.get("drive", 0.0) or 0.0),
                        "utility": float(item.get("utility", 0.0) or 0.0),
                        "bias": float(item.get("bias", 0.0) or 0.0),
                        "fatigue": float(item.get("fatigue", 0.0) or 0.0),
                        "feedback_modulation": float(item.get("feedback_modulation", 1.0) or 1.0),
                        "consequence_estimate": dict(item.get("consequence_estimate", {}) or {}),
                        "notes": list(item.get("notes", []) or [])[:6],
                    }
                    for item in (action_trace.get("candidates", []) or [])[:6]
                ],
                "control_items": [
                    {
                        "sa_label": str(item.get("sa_label", "") or ""),
                        "virtual_energy": float(item.get("virtual_energy", 0.0) or 0.0),
                        "control_kind": str((item.get("anchor_meta", {}) or {}).get("control_kind", "") or ""),
                    }
                    for item in (action_trace.get("control_items", []) or [])[:6]
                ],
                "action_control_effects": dict(action_trace.get("action_control_effects", {}) or {}),
                "visual_gaze": dict(action_trace.get("visual_gaze", {}) or {}),
                "auditory_band": dict(action_trace.get("auditory_band", {}) or {}),
            },
            "action_feedback": {
                "applied": bool(action_feedback_trace.get("applied", False)),
                "observed_feedback": dict(action_feedback_trace.get("observed_feedback", {}) or {}),
                "selected_actions": [
                    str(item.get("action_id", "") or "")
                    for item in (action_feedback_trace.get("selected_actions", []) or [])[:4]
                ],
            },
            "text_output": {
                "visible_text": str((text_output_trace or {}).get("visible_text", "") or ""),
                "expected_token": str((text_output_trace or {}).get("expected_token", "") or ""),
                "revision_detected": bool((text_output_trace or {}).get("revision_detected", False)),
                "revision_events": list((text_output_trace or {}).get("revision_events", []) or [])[:8],
            },
        }

    def _bn_reason(self, row: dict) -> dict:
        snapshot = dict(row.get("snapshot", {}) or {})
        snapshot_ref = dict(row.get("snapshot_ref", {}) or {})
        score_breakdown = dict(row.get("score_breakdown", {}) or {})
        numeric_components = []
        for name, value in score_breakdown.items():
            try:
                numeric_components.append((str(name), float(value or 0.0)))
            except (TypeError, ValueError):
                continue
        components = sorted(numeric_components, key=lambda item: (-float(item[1] or 0.0), item[0]))
        return {
            "memory_id": str(row.get("memory_id", "") or ""),
            "tick_index": int(
                row.get("tick_index", snapshot_ref.get("tick_index", snapshot.get("tick_index", -1))) or -1
            ),
            "source_text": str(
                row.get("source_text", snapshot_ref.get("source_text", snapshot.get("source_text", ""))) or ""
            ),
            "score": float(row.get("score", 0.0) or 0.0),
            "normalized_weight": float(row.get("normalized_weight", 0.0) or 0.0),
            "match_efficiency": float(row.get("match_efficiency", 0.0) or 0.0),
            "grasp_confidence": float(row.get("grasp_confidence", 0.0) or 0.0),
            "b_real_energy": float(row.get("b_real_energy", 0.0) or 0.0),
            "b_virtual_energy": float(row.get("b_virtual_energy", 0.0) or 0.0),
            "b_effective_real_energy": float(row.get("b_effective_real_energy", 0.0) or 0.0),
            "b_effective_virtual_energy": float(row.get("b_effective_virtual_energy", 0.0) or 0.0),
            "energy_transfer": dict(row.get("energy_transfer", {}) or {}),
            "candidate_sources": list(row.get("candidate_sources", []) or []),
            "matched_tokens": dict(row.get("matched_tokens", {}) or {}),
            "snapshot_ref": snapshot_ref,
            "snapshot_preview": dict(row.get("snapshot_preview", {}) or {}),
            "top_score_components": [{"name": name, "value": value} for name, value in components[:5]],
            "relation_channels": dict(row.get("relation_channels", score_breakdown.get("relation_channels", {})) or {}),
            "relation_matches": list(row.get("relation_matches", []) or [])[:6],
            "learned_contributions": list(row.get("learned_contributions", []) or [])[:6],
        }

    def _cn_reason(self, row: dict) -> dict:
        predicted_items = list(row.get("predicted_items", []) or [])
        return {
            "source_memory_id": str(row.get("source_memory_id", "") or ""),
            "successor_memory_id": str(row.get("successor_memory_id", "") or ""),
            "score": float(row.get("score", 0.0) or 0.0),
            "learned_transition_score": float(row.get("learned_transition_score", 0.0) or 0.0),
            "source_b_weight": float(row.get("source_b_weight", 0.0) or 0.0),
            "source_b_match_efficiency": float(row.get("source_b_match_efficiency", 0.0) or 0.0),
            "successor_normalized_weight": float(row.get("successor_normalized_weight", 0.0) or 0.0),
            "energy_transfer_multiplier": float(row.get("energy_transfer_multiplier", 0.0) or 0.0),
            "energy_transfer": dict(row.get("energy_transfer", {}) or {}),
            "predicted_labels": [str(item.get("sa_label", "") or "") for item in predicted_items[:8]],
            "predicted_energies": [
                {
                    "sa_label": str(item.get("sa_label", "") or ""),
                    "virtual_energy": float(item.get("virtual_energy", 0.0) or 0.0),
                }
                for item in predicted_items[:8]
            ],
            "learned_transition_contributions": list(row.get("learned_transition_contributions", []) or [])[:6],
        }

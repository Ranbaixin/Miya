from __future__ import annotations

from dataclasses import replace

from miya_psyarch.config.defaults import RuntimeConfig


def runtime_config_for_profile(profile: str = "balanced", *, target_tick_ms: int = 100) -> RuntimeConfig:
    """
    Build a runtime config for a coarse local compute budget.

    This is intentionally deterministic and local. It does not benchmark the
    machine at runtime; it gives APV2.1 a single place to tune accuracy/cost
    without scattering constants through the codebase.
    """

    name = str(profile or "balanced").strip().lower()
    target = max(30, int(target_tick_ms))
    base = RuntimeConfig()

    if name in {"low", "conservative", "small"} or target < 75:
        return replace(
            base,
            observability=replace(base.observability, target_tick_ms=float(target)),
            text_sensor=replace(base.text_sensor, budget_limit=128, competition_limit=128, dynamic_phrase_scan_budget=96, dynamic_phrase_emit_budget=16),
            vision_sensor=replace(base.vision_sensor, max_objects=3, max_side=112, preview_side=72),
            audio_sensor=replace(base.audio_sensor, max_samples=16000, band_count=8),
            state_pool=replace(
                base.state_pool,
                r_state_head_limit=5,
                r_state_items_per_head=96,
                maintenance_budget=32,
                recent_external_limit=512,
                hot_anchor_limit=768,
                memory_snapshot_limit=512,
                prediction_validation_actual_limit=128,
                prediction_validation_update_limit=64,
            ),
            memory=replace(
                base.memory,
                recall_top_k=3,
                predict_top_k=3,
                candidate_limit=96,
                core_item_limit=512,
                query_feature_limit=512,
                posting_label_token_limit=160,
                posting_display_token_limit=96,
                posting_bigram_token_limit=128,
                posting_sequence_token_limit=128,
                vector_token_limit=256,
                scoring_candidate_limit=64,
                learned_rerank_limit=8,
                state_query_signature_token_limit=128,
                numeric_candidate_limit=32,
                numeric_top_k_per_channel=12,
                numeric_weight=0.95,
                relation_token_limit=128,
                relation_event_limit=64,
                relation_context_limit=2048,
                relation_score_weight=0.48,
                relation_focus_score_weight=0.68,
                index_jobs_per_tick=1,
                index_maintenance_min_remaining_ms=28.0,
                index_maintenance_max_ms=12.0,
                idle_heavy_index_jobs=1,
                idle_index_maintenance_max_ms=6.0,
            ),
            attention=replace(
                base.attention,
                focus_limit=8,
                successor_bias_context_limit=1024,
                successor_bias_max_successors_per_context=32,
                successor_bias_top_k=8,
                successor_bias_gain=0.34,
                successor_bias_max=0.36,
                successor_bias_per_tick_update_limit=8,
            ),
            short_term=replace(
                base.short_term,
                focus_history_limit=8,
                max_replay_items=6,
                replay_query_weight=0.68,
            ),
            time_feeling=replace(
                base.time_feeling,
                rerun_recall_confidence_threshold=1.01,
                rerun_recall_energy_threshold=1.01,
            ),
        )

    if name in {"high", "high_accuracy", "large"} and target >= 100:
        return replace(
            base,
            observability=replace(base.observability, target_tick_ms=float(target)),
            text_sensor=replace(base.text_sensor, budget_limit=1024, competition_limit=1024, dynamic_phrase_scan_budget=512, dynamic_phrase_emit_budget=64),
            vision_sensor=replace(base.vision_sensor, max_objects=6, max_side=224, preview_side=128),
            audio_sensor=replace(base.audio_sensor, max_samples=65536, band_count=16),
            state_pool=replace(
                base.state_pool,
                r_state_head_limit=8,
                r_state_items_per_head=384,
                maintenance_budget=96,
                recent_external_limit=4096,
                hot_anchor_limit=4096,
                memory_snapshot_limit=2048,
                prediction_validation_actual_limit=512,
                prediction_validation_update_limit=256,
            ),
            memory=replace(
                base.memory,
                recall_top_k=8,
                predict_top_k=6,
                candidate_limit=512,
                core_item_limit=2048,
                query_feature_limit=2048,
                posting_label_token_limit=512,
                posting_display_token_limit=256,
                posting_bigram_token_limit=384,
                posting_sequence_token_limit=384,
                vector_token_limit=768,
                scoring_candidate_limit=160,
                learned_rerank_limit=24,
                state_query_signature_token_limit=512,
                numeric_candidate_limit=128,
                numeric_top_k_per_channel=48,
                numeric_weight=1.25,
                relation_token_limit=384,
                relation_event_limit=192,
                relation_context_limit=16384,
                relation_score_weight=0.82,
                relation_focus_score_weight=1.08,
                index_jobs_per_tick=2,
                index_maintenance_min_remaining_ms=48.0,
                index_maintenance_max_ms=38.0,
                idle_heavy_index_jobs=2,
                idle_index_maintenance_max_ms=24.0,
            ),
            attention=replace(
                base.attention,
                focus_limit=16,
                successor_bias_context_limit=4096,
                successor_bias_max_successors_per_context=96,
                successor_bias_top_k=16,
                successor_bias_gain=0.48,
                successor_bias_max=0.56,
                successor_bias_per_tick_update_limit=24,
            ),
            short_term=replace(
                base.short_term,
                focus_history_limit=16,
                max_replay_items=12,
                replay_query_weight=0.9,
            ),
            time_feeling=replace(
                base.time_feeling,
                rerun_recall_confidence_threshold=0.62,
                rerun_recall_energy_threshold=0.35,
            ),
        )

    return replace(
        base,
        observability=replace(base.observability, target_tick_ms=float(target)),
        text_sensor=replace(base.text_sensor, budget_limit=1024, competition_limit=1024, dynamic_phrase_scan_budget=128, dynamic_phrase_emit_budget=0),
        vision_sensor=replace(base.vision_sensor, max_objects=4, max_side=160, preview_side=96),
        audio_sensor=replace(base.audio_sensor, max_samples=32768, band_count=12),
        state_pool=replace(
            base.state_pool,
            r_state_head_limit=7,
            r_state_items_per_head=256,
            maintenance_budget=64,
            recent_external_limit=2048,
            hot_anchor_limit=2048,
            memory_snapshot_limit=1024,
            prediction_validation_actual_limit=256,
            prediction_validation_update_limit=128,
        ),
            memory=replace(
                base.memory,
                recall_top_k=5,
                predict_top_k=5,
                candidate_limit=128,
            core_item_limit=1024,
            query_feature_limit=1024,
            posting_label_token_limit=256,
            posting_display_token_limit=128,
                posting_bigram_token_limit=192,
                posting_sequence_token_limit=192,
                vector_token_limit=384,
                scoring_candidate_limit=12,
                learned_rerank_limit=2,
                state_query_signature_token_limit=256,
                numeric_candidate_limit=48,
                numeric_top_k_per_channel=16,
                numeric_weight=1.05,
                relation_token_limit=192,
                relation_event_limit=96,
                relation_context_limit=4096,
                relation_score_weight=0.62,
                relation_focus_score_weight=0.86,
                index_jobs_per_tick=1,
                index_maintenance_min_remaining_ms=60.0,
                index_maintenance_max_ms=2.0,
                idle_heavy_index_jobs=1,
                idle_index_maintenance_max_ms=10.0,
        ),
            attention=replace(
                base.attention,
                focus_limit=8,
                successor_bias_context_limit=2048,
                successor_bias_max_successors_per_context=64,
                successor_bias_top_k=12,
                successor_bias_gain=0.4,
                successor_bias_max=0.44,
                successor_bias_per_tick_update_limit=16,
            ),
            short_term=replace(
                base.short_term,
                focus_history_limit=12,
                max_replay_items=8,
                replay_query_weight=0.78,
            ),
            online_embedding=replace(
                base.online_embedding,
                scoring_token_limit=48,
                learned_weight=0.22,
                transition_learned_weight=0.12,
            ),
            time_feeling=replace(
                base.time_feeling,
                rerun_recall_confidence_threshold=1.01,
                rerun_recall_energy_threshold=1.01,
            ),
    )

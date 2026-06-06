from __future__ import annotations

from miya_psyarch.core.state_pool import DualEnergyStatePool


def _pool() -> DualEnergyStatePool:
    return DualEnergyStatePool(
        real_decay=0.9,
        virtual_decay=0.86,
        attention_gain_decay=0.9,
        fatigue_decay=0.82,
        prune_threshold=0.01,
        query_limit=8,
        snapshot_limit=16,
        memory_snapshot_limit=32,
        focus_boost=0.3,
        focus_fatigue_step=0.18,
        prediction_fatigue_enabled=True,
        prediction_fatigue_min_mass=0.18,
        prediction_fatigue_ratio=0.18,
        prediction_fatigue_gain=0.08,
        prediction_fatigue_max_step=0.2,
        bootstrap_virtual_energy=0.6,
    )


def _pred(label: str, virtual: float, *, source_id: str = "b", successor_id: str = "c", semantics: str = "virtual_energy_is_prediction_strength_not_occurrence_count") -> dict:
    return {
        "sa_label": str(label),
        "display_text": str(label).split("::")[-1],
        "source_type": "predicted",
        "family": "text",
        "virtual_energy": float(virtual),
        "anchor_meta": {
            "prediction_energy_transfer": {
                "source_memory_id": str(source_id),
                "successor_memory_id": str(successor_id),
                "source_b_weight": 0.5,
                "successor_weight": 0.5,
                "payload_share": 1.0,
                "transfer_multiplier": float(virtual),
                "calibrated_transfer_multiplier": float(virtual),
                "energy_budget_semantics": semantics,
            }
        },
    }


def test_cstar_trace_merges_same_label_as_prediction_strength_not_occurrence_count() -> None:
    pool = _pool()
    pool.begin_tick(0)
    pool.apply_predictions(
        [
            _pred("text::pain", 0.7, source_id="b1", successor_id="c1"),
            _pred("text::pain", 0.5, source_id="b2", successor_id="c2"),
            _pred("text::avoid", 0.2, source_id="b3", successor_id="c3"),
        ],
        tick_index=0,
        source="fast_cn",
    )

    trace = pool.cstar_budget_trace()
    top = {row["sa_label"]: row for row in trace["top_labels"]}

    assert trace["schema_id"] == "cstar_budget_trace/v1"
    assert trace["energy_semantics"] == "same_label_sum_means_prediction_strength_not_occurrence_count"
    assert trace["total_virtual_mass"] == 1.4
    assert top["text::pain"]["virtual_mass"] == 1.2
    assert top["text::pain"]["item_count"] == 2
    assert len(top["text::pain"]["source_branches"]) == 2
    assert trace["budget_warnings"] == []


def test_prediction_fatigue_preserves_virtual_energy_but_reduces_attention_score() -> None:
    pool = _pool()
    pool.begin_tick(0)
    pool.apply_predictions(
        [
            _pred("text::pain", 0.9, source_id="b1", successor_id="c1"),
            _pred("text::pain", 0.7, source_id="b2", successor_id="c2"),
            _pred("text::stab", 0.1, source_id="b3", successor_id="c3"),
        ],
        tick_index=0,
        source="fast_cn",
    )

    rows = {row["sa_label"]: row for row in pool.attention_view()}
    pain = rows["text::pain"]
    stab = rows["text::stab"]
    trace = pool.cstar_budget_trace()
    fatigue = {row["sa_label"]: row for row in trace["fatigue_updates"]}

    assert pain["virtual_energy"] == 1.6
    assert pain["fatigue"] > 0.0
    assert "text::pain" in fatigue
    assert "text::stab" not in fatigue
    assert pain["attention_score"] < pain["virtual_energy"] * 0.25
    assert stab["fatigue"] == 0.0


def test_cstar_budget_trace_warns_without_clipping_energy() -> None:
    pool = _pool()
    pool.begin_tick(0)
    pool.apply_predictions(
        [
            _pred(
                "text::pain",
                0.6,
                semantics="legacy_post_normalization_gain",
            )
        ],
        tick_index=0,
        source="fast_cn",
    )

    trace = pool.cstar_budget_trace()
    rows = {row["sa_label"]: row for row in pool.query_view()}

    assert trace["budget_warnings"][0]["warning"] == "unexpected_prediction_energy_semantics"
    assert rows["text::pain"]["virtual_energy"] == 0.6
    assert trace["policy"] == "audit_only_no_energy_clipping"


def test_cstar_trace_accumulates_multiple_prediction_branches_in_one_tick() -> None:
    pool = _pool()
    pool.begin_tick(0)
    pool.apply_predictions([_pred("text::pain", 0.6, source_id="b1", successor_id="c1")], tick_index=0, source="fast_cn")
    pool.apply_predictions([_pred("text::avoid", 0.4, source_id="b2", successor_id="c2")], tick_index=0, source="slow_cn")

    trace = pool.cstar_budget_trace()
    top = {row["sa_label"]: row for row in trace["top_labels"]}

    assert trace["trace_scope"] == "tick_cstar"
    assert trace["total_virtual_mass"] == 1.0
    assert top["text::pain"]["virtual_mass"] == 0.6
    assert top["text::avoid"]["virtual_mass"] == 0.4
    assert [branch["source"] for branch in trace["branches"]] == ["fast_cn", "slow_cn"]

from __future__ import annotations

from miya_psyarch.core.runtime import APV21Runtime
from miya_psyarch.core.tuner import AdaptiveTuner


def _trace(*, pressure: float, alignment: float, mismatch: float, action_success: float = 0.0, action_punishment: float = 0.0) -> dict:
    return {
        "state_pool": {
            "snapshot": {
                "items": [
                    {
                        "sa_label": "sa::probe",
                        "real_energy": pressure,
                        "virtual_energy": 0.0,
                        "cognitive_pressure": pressure,
                    }
                ]
            },
            "prediction_trace": {
                "alignment_score": alignment,
                "mismatch_ratio": mismatch,
            },
        },
        "action": {
            "selected_actions": [
                {
                    "action_id": "action::probe",
                    "predicted_outcome": {
                        "reward": action_success,
                        "correctness": action_success * 0.4,
                        "punishment": action_punishment,
                        "pressure": action_punishment * 0.5,
                    },
                }
            ]
        },
        "action_feedback": {"observed_feedback": {}},
    }


def _trace_with_pressure_anchor() -> dict:
    row = _trace(pressure=1.0, alignment=0.4, mismatch=0.2, action_success=0.0, action_punishment=0.1)
    row["expectation_pressure"] = {
        "anchor_verification": {
            "anchors": [
                {
                    "anchor_id": "pressure:state:mem-risk",
                    "anchor_type": "pressure",
                    "source_memory_id": "mem-risk",
                    "level": 0.8,
                    "expected_punishment": 0.7,
                }
            ],
            "verified": [],
            "missed": [{"anchor_id": "pressure:state:mem-risk"}],
        }
    }
    row["action"]["safety_gate"] = {
        "anchor_risk": {"pressure": 0.72, "top_source_memory_id": "mem-risk"}
    }
    return row


def test_adaptive_tuner_waits_for_support_before_applying_modulation() -> None:
    tuner = AdaptiveTuner(min_support_ticks=4, ema_alpha=0.5)
    first = tuner.observe_tick(_trace(pressure=8.0, alignment=0.1, mismatch=0.8, action_punishment=0.8))
    assert not first["support_ready"]
    assert first["modulation"]["values"]["action"]["threshold_adjustment"] == 0.0

    for _ in range(4):
        latest = tuner.observe_tick(_trace(pressure=8.0, alignment=0.1, mismatch=0.8, action_punishment=0.8))
    assert latest["support_ready"]
    assert latest["modulation"]["values"]["action"]["threshold_adjustment"] > 0.0
    assert latest["modulation"]["values"]["memory"]["prediction_gain_multiplier"] >= 1.0


def test_adaptive_tuner_modulation_is_bounded() -> None:
    tuner = AdaptiveTuner(min_support_ticks=1, ema_alpha=0.6, adjustment_rate=0.2)
    for _ in range(80):
        latest = tuner.observe_tick(_trace(pressure=99.0, alignment=0.0, mismatch=1.0, action_punishment=1.0))
    values = latest["modulation"]["values"]
    assert -0.08 <= values["attention"]["threshold_adjustment"] <= 0.08
    assert 0.85 <= values["memory"]["prediction_gain_multiplier"] <= 1.18
    assert -0.06 <= values["action"]["threshold_adjustment"] <= 0.10
    assert 0.85 <= values["learning"]["rate_multiplier"] <= 1.15


def test_runtime_trace_exposes_tuner_without_breaking_tick() -> None:
    runtime = APV21Runtime()
    for _ in range(3):
        trace = runtime.process_text_tick("alpha beta gamma")
    assert trace["tuner"]["schema_id"] == "adaptive_tuner_trace/v1"
    assert "metrics" in trace["tuner"]
    assert "modulation" in trace["tuner"]


def test_adaptive_tuner_tracks_expectation_pressure_anchor_metrics() -> None:
    tuner = AdaptiveTuner(min_support_ticks=1, ema_alpha=1.0, adjustment_rate=0.2)
    trace = tuner.observe_tick(_trace_with_pressure_anchor())
    metrics = trace["metrics"]
    assert metrics["pressure_anchor_level"] == 0.8
    assert metrics["safety_anchor_pressure"] == 0.72
    assert metrics["anchor_miss_rate"] == 1.0
    assert trace["recommendation"]["pressure_anchor_level"] == 0.8


def test_adaptive_tuner_experiment_rolls_back_when_metrics_degrade() -> None:
    tuner = AdaptiveTuner(min_support_ticks=2, ema_alpha=1.0, adjustment_rate=0.8)
    for _ in range(2):
        trace = tuner.observe_tick(_trace(pressure=1.0, alignment=0.65, mismatch=0.1, action_success=0.5, action_punishment=0.0))
    assert trace["experiment"]["state"] == "probing"

    for _ in range(3):
        trace = tuner.observe_tick(_trace(pressure=9.0, alignment=0.2, mismatch=0.9, action_success=0.0, action_punishment=0.8))
    assert trace["experiment"]["state"] == "rolled_back"
    assert trace["experiment"]["decision"] == "rollback"
    assert trace["experiment"]["rollback_reason"]


def test_adaptive_tuner_experiment_confirms_when_metrics_improve() -> None:
    tuner = AdaptiveTuner(min_support_ticks=2, ema_alpha=1.0, adjustment_rate=0.4)
    for _ in range(2):
        trace = tuner.observe_tick(_trace(pressure=5.0, alignment=0.25, mismatch=0.6, action_success=0.0, action_punishment=0.4))
    assert trace["experiment"]["state"] == "probing"

    for _ in range(3):
        trace = tuner.observe_tick(_trace(pressure=3.0, alignment=0.5, mismatch=0.3, action_success=0.4, action_punishment=0.1))
    assert trace["experiment"]["state"] == "confirmed"
    assert trace["experiment"]["decision"] == "confirmed"

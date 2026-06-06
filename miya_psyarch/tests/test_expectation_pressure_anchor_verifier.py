from __future__ import annotations

from miya_psyarch.channels.expectation_pressure import BAnchorExpectationVerifier
from miya_psyarch.config.defaults import RuntimeConfig
from miya_psyarch.core.action import ActionConsequencePlanner
from miya_psyarch.core.learning import InnateLearningEventRouter
from miya_psyarch.core.runtime.engine import APV21Runtime
# SKIP: observatory.reconstruct not available in miya_psyarch
# from miya_psyarch.observatory.reconstruct import reconstruct_tick_observatory


def _bn(memory_id: str, *, real: float = 0.4, match: float = 0.8, kind: str = "state") -> dict:
    return {
        "memory_id": memory_id,
        "memory_kind": kind,
        "tick_index": 1,
        "normalized_weight": 0.75,
        "match_efficiency": match,
        "grasp_confidence": match,
        "b_real_energy": real,
        "b_effective_real_energy": real,
        "b_virtual_energy": 0.0,
        "b_effective_virtual_energy": 0.0,
    }


def _cn(source_id: str, *, reward: float = 0.0, punishment: float = 0.0) -> dict:
    items = []
    if reward > 0.0:
        items.append(
            {
                "sa_label": "signal::reward",
                "family": "signal",
                "source_type": "predicted",
                "virtual_energy": reward,
            }
        )
    if punishment > 0.0:
        items.append(
            {
                "sa_label": "signal::punishment",
                "family": "signal",
                "source_type": "predicted",
                "virtual_energy": punishment,
            }
        )
    return {
        "source_memory_id": source_id,
        "successor_memory_id": f"{source_id}-next",
        "score": 1.0,
        "predicted_items": items,
    }


def test_b_anchor_verifier_creates_expectation_from_reward_successor_and_verifies_later_b() -> None:
    verifier = BAnchorExpectationVerifier(min_outcome_virtual=0.01, min_anchor_level=0.01)
    first = verifier.update(
        tick_index=1,
        fast_bn=[_bn("mem-cat", real=0.35)],
        slow_bn=[],
        fast_cn=[_cn("mem-cat", reward=0.8)],
        slow_cn=[],
        action_feedback_trace={},
        cognitive_feelings={"channels": {}},
    )
    assert first["created"]
    assert first["anchors"][0]["anchor_type"] == "expectation"
    assert not first["verified"]

    second = verifier.update(
        tick_index=2,
        fast_bn=[_bn("mem-cat", real=0.72)],
        slow_bn=[],
        fast_cn=[],
        slow_cn=[],
        action_feedback_trace={"observed_feedback": {"reward": 0.5, "correctness": 0.3}},
        cognitive_feelings={"channels": {"correctness": 0.4}},
    )
    assert second["verified"]
    assert any(item["sa_label"] == "feeling::satisfaction" for item in second["items"])


def test_b_anchor_verifier_marks_expectation_gap_when_b_disappears() -> None:
    verifier = BAnchorExpectationVerifier(min_outcome_virtual=0.01, min_anchor_level=0.01)
    verifier.update(
        tick_index=1,
        fast_bn=[_bn("mem-reply", real=0.42)],
        slow_bn=[],
        fast_cn=[_cn("mem-reply", reward=0.6)],
        slow_cn=[],
        action_feedback_trace={},
        cognitive_feelings={"channels": {}},
    )
    second = verifier.update(
        tick_index=2,
        fast_bn=[],
        slow_bn=[],
        fast_cn=[],
        slow_cn=[],
        action_feedback_trace={},
        cognitive_feelings={"channels": {}},
    )
    assert second["missed"]
    assert any(item["sa_label"] == "feeling::expectation_gap" for item in second["items"])


def test_b_anchor_verifier_creates_pressure_from_punishment_successor() -> None:
    verifier = BAnchorExpectationVerifier(min_outcome_virtual=0.01, min_anchor_level=0.01)
    first = verifier.update(
        tick_index=1,
        fast_bn=[_bn("mem-risk", real=0.5)],
        slow_bn=[],
        fast_cn=[_cn("mem-risk", punishment=0.7)],
        slow_cn=[],
        action_feedback_trace={},
        cognitive_feelings={"channels": {}},
    )
    assert first["created"][0]["anchor_type"] == "pressure"
    second = verifier.update(
        tick_index=2,
        fast_bn=[_bn("mem-risk", real=0.72)],
        slow_bn=[],
        fast_cn=[],
        slow_cn=[],
        action_feedback_trace={"observed_feedback": {"punishment": 0.4}},
        cognitive_feelings={"channels": {"pressure": 0.5}},
    )
    assert second["verified"]
    assert any(item["sa_label"] == "feeling::pressure_validation" for item in second["items"])


def test_innate_learning_event_router_keeps_action_feedback_out_of_concept_learning() -> None:
    router = InnateLearningEventRouter()
    trace = router.route(
        tick_index=3,
        innate_traces={
            "tick_end": {
                "learning_events": [
                    {"event": "positive_pair", "phase": "tick_end", "rule_id": "BC-001", "strength": 0.5},
                    {"event": "action_outcome", "phase": "tick_end", "rule_id": "BC-004", "strength": 0.8},
                    {"event": "verify_b_anchor", "phase": "emotion_post", "rule_id": "BC-006", "strength": 0.7},
                ]
            }
        },
        expectation_anchor_trace={"active_count": 1, "created": [{}], "verified": [], "missed": []},
        action_feedback_trace={"applied": True, "feedback_items": [{"sa_label": "action_feedback::probe"}]},
    )
    routes = {row["event"]: row["route"] for row in trace["routes"]}
    assert routes["positive_pair"] == "content_online_embedding_trace"
    assert routes["action_outcome"] == "action_outcome_learning_trace"
    assert routes["verify_b_anchor"] == "expectation_pressure_b_anchor_verifier"
    structured = trace["structured_events"]
    assert {row["schema_id"] for row in structured} == {"apv21_learning_event/v1"}
    layers = {row["event_type"]: row["learning_layer"] for row in structured}
    assert layers["prediction_error_positive"] == "content_recognition_embedding"
    assert layers["action_outcome"] == "action_outcome_memory"
    assert layers["b_anchor_verification"] == "expectation_pressure_anchor"
    action_event = next(row for row in structured if row["event_type"] == "action_outcome")
    assert action_event["guards"]["exclude_action_feedback"] is True
    assert "do_not_write_concept_similarity" in trace["safety"]["concept_learning_guard"]


def test_runtime_exposes_anchor_verification_and_innate_event_router_trace() -> None:
    runtime = APV21Runtime()
    runtime.process_text_tick("alpha reward probe", trace_mode="debug")
    trace = runtime.process_text_tick("", trace_mode="debug")
    assert "anchor_verification" in trace["expectation_pressure"]
    assert trace["expectation_pressure"]["anchor_verification"]["schema_id"] == "expectation_pressure_b_anchor_verifier/v1"
    assert "innate_event_router" in trace["learning"]
    assert trace["learning"]["innate_event_router"]["schema_id"] == "innate_learning_event_router/v1"


def test_planner_turns_active_b_anchor_into_recall_by_expectation_candidate() -> None:
    planner = ActionConsequencePlanner(
        enabled=True,
        selection_threshold=0.1,
        max_selected_actions=1,
        fatigue_decay=0.9,
        fatigue_step=0.0,
        bias_learning_rate=0.0,
        bias_gain=0.0,
        confidence_gain=0.18,
        wait_base_drive=0.18,
    )
    trace = planner.plan(
        tick_index=2,
        state_snapshot_items=[],
        fast_bn=[],
        fast_cn=[],
        slow_bn=[],
        slow_cn=[],
        cognitive_feelings={"channels": {"expectation": 0.2}},
        expectation_pressure_trace={
            "channels": {"expectation_level": 0.42, "pressure_level": 0.0, "expectation_gap": 0.16},
            "anchor_verification": {
                "anchors": [
                    {
                        "anchor_id": "expectation:state:mem-cat",
                        "anchor_type": "expectation",
                        "source_memory_id": "mem-cat",
                        "source_memory_kind": "state",
                        "level": 0.74,
                        "expected_reward": 0.8,
                    }
                ]
            },
        },
        rhythm_trace={"channels": {}},
        time_trace={"channels": {}},
    )
    candidate = next(row for row in trace["candidates"] if row["action_id"] == "action::recall_by_expectation")
    assert candidate["params"]["source_memory_id"] == "mem-cat"
    assert candidate["supporting_anchors"][0]["anchor_id"] == "expectation:state:mem-cat"
    assert candidate["drive"] >= trace["effective_threshold"]


def test_recall_by_expectation_control_items_restore_b_anchor_snapshot_labels() -> None:
    config = RuntimeConfig()
    runtime = APV21Runtime(config=config)
    written = runtime.memory.write_snapshot(
        tick_index=1,
        memory_kind="state",
        items=[
            {"sa_label": "text::cat", "family": "text", "source_type": "external_text", "real_energy": 0.8},
            {"sa_label": "feeling::satisfaction", "family": "cognitive_feeling", "source_type": "test", "real_energy": 0.4},
            {"sa_label": "text::purr", "family": "text", "source_type": "external_text", "real_energy": 0.5},
        ],
        focus_labels=["text::cat"],
        source_text="cat purr",
    )
    memory_id = written["memory_id"]
    control = runtime._build_action_control_items(
        selected_actions=[
            {
                "action_id": "action::recall_by_expectation",
                "supporting_anchors": [
                    {
                        "anchor_id": f"expectation:state:{memory_id}",
                        "anchor_type": "expectation",
                        "source_memory_id": memory_id,
                        "source_memory_kind": "state",
                        "source_tick_index": 1,
                        "level": 0.76,
                        "expected_reward": 0.7,
                    }
                ],
            }
        ],
        attention_trace={"selected_labels": []},
        fast_bn=[],
        slow_bn=[],
        fast_cn=[],
        slow_cn=[],
        expectation_pressure_trace={},
    )
    labels = [row["sa_label"] for row in control]
    assert "text::cat" in labels
    assert "text::purr" in labels
    assert "feeling::satisfaction" in labels
    assert control[0]["anchor_meta"]["control_kind"] == "recall_by_expectation"
    assert control[0]["anchor_meta"]["source_memory_id"] == memory_id


def test_runtime_external_feedback_queue_emits_explicit_reward_punishment_signals() -> None:
    runtime = APV21Runtime()
    queued = runtime.queue_external_feedback(
        reward=0.4,
        punishment=0.7,
        correctness=0.2,
        confidence=0.9,
        source="unit_test",
        notes=["teacher_signal"],
    )
    assert queued["queued"]
    trace = runtime.process_text_tick("feedback probe", trace_mode="debug")
    feedback = trace["action_feedback"]
    assert feedback["applied"] is True
    assert feedback["source"] == "external_feedback_queue"
    labels = [item["sa_label"] for item in feedback["feedback_items"]]
    assert "signal::reward" in labels
    assert "signal::punishment" in labels
    punishment = next(item for item in feedback["feedback_items"] if item["sa_label"] == "signal::punishment")
    assert punishment["real_energy"] == 0.7
    assert punishment["virtual_energy"] == 0.7
    assert punishment["anchor_meta"]["feedback_energy_semantics"]["meaning"] == "punishment_event_as_real;future_avoidance_pressure_as_virtual"


def _skip_test_observatory_reconstruction_exposes_expectation_pressure_anchor_view() -> None:
    runtime = APV21Runtime()
    trace = runtime.process_text_tick("alpha reward probe", trace_mode="debug")
    reconstruction = reconstruct_tick_observatory(
        trace,
        snapshot_lookup=runtime.memory.snapshot_by_id,
        successor_lookup=runtime.memory.successor_links,
    )
    anchor_view = reconstruction["feelings"]["expectation_pressure_anchors"]
    assert anchor_view["schema_id"] == "expectation_pressure_anchor_observatory/v1"
    assert "active" in anchor_view
    assert "recall_control_items" in anchor_view

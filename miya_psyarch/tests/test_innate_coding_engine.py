from __future__ import annotations

from miya_psyarch.config.defaults import RuntimeConfig
from miya_psyarch.core.attention.selector import AttentionSelector
from miya_psyarch.core.action import ActionConsequencePlanner, ActionControlEffectRouter, SafetyGate
from miya_psyarch.core.action.text_actuator import TextActionActuator
from miya_psyarch.core.innate import InnateCodingEngine
from miya_psyarch.core.innate.default_rules import default_rules
from miya_psyarch.core.runtime.engine import APV21Runtime


def test_innate_rule_engine_validates_and_simulates_default_rules() -> None:
    engine = InnateCodingEngine()
    validation = engine.validate()
    assert validation["ok"], validation
    assert validation["rule_count"] >= 70
    assert "actuator::attention_allocation" in engine.actuator_registry()
    assert "action::text_replace" in engine.action_registry()

    trace = engine.simulate(
        phase="post_prediction_validation",
        context={
            "tick_index": 1,
            "state_items": [
                {
                    "sa_label": "text::door",
                    "family": "text",
                    "source_type": "external_text",
                    "real_energy": 1.0,
                    "virtual_energy": 0.0,
                    "cognitive_pressure": 1.0,
                }
            ],
            "prediction_trace": {"mismatch_ratio": 0.8, "alignment_score": 0.0, "unexpected_count": 1},
            "residual_summary": {"total_unresolved_mass": 0.8},
        },
    )
    assert trace["hit_count"] >= 1
    assert any(hit["rule_id"] == "CF-001" for hit in trace["hits"])
    assert any(item["sa_label"] == "feeling::surprise" for item in trace["items"])


def test_all_designed_rule_ids_are_present_in_default_rule_bundle() -> None:
    rule_ids = {rule.rule_id for rule in default_rules()}
    expected = {
        *(f"CF-{idx:03d}" for idx in range(1, 16)),
        *(f"AT-{idx:03d}" for idx in range(1, 10)),
        *(f"BC-{idx:03d}" for idx in range(1, 7)),
        "EM-DA-001",
        "EM-DA-002",
        "EM-ADR-001",
        "EM-ADR-002",
        "EM-OXY-001",
        "EM-OXY-002",
        "EM-SER-001",
        "EM-SER-002",
        "EM-END-001",
        "EM-END-002",
        "EM-COR-001",
        "EM-COR-002",
        "EM-NOV-001",
        "EM-NOV-002",
        "EM-FOC-001",
        "EM-FOC-002",
        *(f"AC-{idx:03d}" for idx in range(1, 21)),
        *(f"AF-{idx:03d}" for idx in range(1, 12)),
    }
    assert expected <= rule_ids
    assert len(rule_ids) == len(default_rules())


def test_innate_rule_fatigue_suppresses_repeated_same_anchor_without_silencing_schema() -> None:
    engine = InnateCodingEngine(min_fire_strength=0.001)
    context = {
        "state_items": [
            {
                "sa_label": "text::flash",
                "family": "text",
                "source_type": "external_text",
                "real_energy": 1.0,
                "virtual_energy": 0.0,
                "cognitive_pressure": 1.0,
            }
        ],
        "prediction_trace": {"mismatch_ratio": 0.8, "alignment_score": 0.0, "unexpected_count": 1},
    }
    strengths = []
    for idx in range(4):
        trace = engine.evaluate(phase="post_prediction_validation", context=context, tick_index=idx)
        hit = next(row for row in trace["hits"] if row["rule_id"] == "CF-001")
        strengths.append(hit["effective_strength"])
    assert strengths[-1] < strengths[0]
    assert engine.fatigue_snapshot()["rule"]


def test_action_planner_merges_innate_action_nodes_and_memory_predicted_actions() -> None:
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
        tick_index=1,
        state_snapshot_items=[
            {
                "sa_label": "action::text_reread",
                "family": "action",
                "source_type": "predicted",
                "real_energy": 0.0,
                "virtual_energy": 0.8,
                "cognitive_pressure": -0.8,
            }
        ],
        fast_bn=[],
        fast_cn=[],
        slow_bn=[],
        slow_cn=[],
        cognitive_feelings={"channels": {"dissonance": 0.8, "pressure": 0.3}},
        rhythm_trace={"channels": {}},
        time_trace={"channels": {}},
        innate_action_nodes=[
            {
                "action_id": "action::inspect_residual",
                "actuator_id": "actuator::attention_allocation",
                "drive": 0.25,
                "strength": 0.8,
                "rule_id": "AT-004",
                "notes": ["innate_rule=AT-004"],
            }
        ],
        memory_action_drive_gain=0.4,
    )
    inspect = next(row for row in trace["candidates"] if row["action_id"] == "action::inspect_residual")
    reread = next(row for row in trace["candidates"] if row["action_id"] == "action::text_reread")
    assert any("innate" in note for note in inspect["notes"])
    assert any("memory_predicted_action" in note for note in reread["notes"])
    assert reread["actuator_id"] == "actuator::text_editor"


def test_innate_action_bias_is_separate_and_can_suppress_existing_candidate() -> None:
    engine = InnateCodingEngine()
    innate = engine.simulate(
        phase="action_preselect",
        context={
            "tick_index": 1,
            "feelings": {"channels": {"coherence": 0.95, "surprise": 0.0, "grasp": 0.95}},
            "prediction_trace": {"alignment_score": 0.9, "mismatch_ratio": 0.0},
        },
    )
    assert any(row["action_id"] == "action::diverge_attention" for row in innate["action_biases"])
    assert not any(row["action_id"] == "action::diverge_attention" for row in innate["action_nodes"])

    planner = ActionConsequencePlanner(
        enabled=True,
        selection_threshold=0.1,
        max_selected_actions=4,
        fatigue_decay=0.9,
        fatigue_step=0.0,
        bias_learning_rate=0.0,
        bias_gain=0.0,
        confidence_gain=0.18,
        wait_base_drive=0.18,
    )
    without_bias = planner.plan(
        tick_index=1,
        state_snapshot_items=[],
        fast_bn=[],
        fast_cn=[],
        slow_bn=[],
        slow_cn=[],
        cognitive_feelings={"channels": {"surprise": 0.9, "grasp": 0.0}},
        rhythm_trace={"channels": {}},
        time_trace={"channels": {}},
        innate_action_nodes=[{"action_id": "action::diverge_attention", "actuator_id": "actuator::attention_allocation", "drive": 0.35, "strength": 0.9}],
    )
    with_bias = planner.plan(
        tick_index=2,
        state_snapshot_items=[],
        fast_bn=[],
        fast_cn=[],
        slow_bn=[],
        slow_cn=[],
        cognitive_feelings={"channels": {"surprise": 0.9, "grasp": 0.0}},
        rhythm_trace={"channels": {}},
        time_trace={"channels": {}},
        innate_action_nodes=[{"action_id": "action::diverge_attention", "actuator_id": "actuator::attention_allocation", "drive": 0.35, "strength": 0.9}],
        innate_action_biases=innate["action_biases"],
    )
    drive_without = next(row for row in without_bias["candidates"] if row["action_id"] == "action::diverge_attention")["drive"]
    biased_row = next(row for row in with_bias["candidates"] if row["action_id"] == "action::diverge_attention")
    assert biased_row["drive"] < drive_without
    assert any("innate_action_bias" in note for note in biased_row["notes"])


def test_attention_selector_consumes_innate_attention_biases() -> None:
    selector = AttentionSelector(focus_limit=1, pressure_gain=0.6, attention_gain_weight=0.8, fatigue_weight=0.5)
    rows = [
        {"sa_label": "text::plain", "cognitive_pressure": 0.3, "attention_gain": 0.0, "virtual_energy": 0.0, "fatigue": 0.0},
        {"sa_label": "text::flash", "cognitive_pressure": 0.05, "attention_gain": 0.0, "virtual_energy": 0.0, "fatigue": 0.0},
    ]
    baseline = selector.select(rows)
    biased = selector.select(
        rows,
        innate_attention_biases=[
            {
                "schema_id": "innate_attention_bias/v1",
                "bias": "surprise_anchor",
                "strength": 0.9,
                "target_labels": ["text::flash"],
                "rule_id": "CF-001",
            }
        ],
    )
    assert baseline["selected_labels"] == ["text::plain"]
    assert biased["selected_labels"] == ["text::flash"]
    flash = next(row for row in biased["ranked_items"] if row["sa_label"] == "text::flash")
    assert flash["innate_attention_bias"] > 0.0


def test_safety_gate_vetoes_external_action_and_emits_inhibition_item() -> None:
    gate = SafetyGate(enabled=True, veto_pressure_threshold=0.5, veto_cor_threshold=0.8, min_external_confidence=0.6)
    selected = [
        {
            "action_id": "action::text_commit",
            "actuator_id": "actuator::text_editor",
            "predicted_outcome": {"pressure": 0.7, "punishment": 0.2, "confidence": 0.4},
        }
    ]
    trace = gate.review(
        tick_index=3,
        candidates=selected,
        selected_actions=selected,
        cognitive_feelings={"channels": {"pressure": 0.7}},
        emotion_state={"COR": 0.3},
    )
    assert trace["vetoed_action_ids"] == ["action::text_commit"]
    assert trace["selected_actions"] == []
    assert trace["inhibition_items"][0]["sa_label"] == "action_inhibition::text_commit"


def test_safety_gate_uses_pressure_b_anchor_as_external_action_risk() -> None:
    gate = SafetyGate(enabled=True, veto_pressure_threshold=0.5, review_pressure_threshold=0.3, min_external_confidence=0.1)
    selected = [
        {
            "action_id": "action::text_commit",
            "actuator_id": "actuator::text_editor",
            "predicted_outcome": {"pressure": 0.1, "punishment": 0.0, "confidence": 0.9},
        }
    ]
    trace = gate.review(
        tick_index=4,
        candidates=selected,
        selected_actions=selected,
        cognitive_feelings={"channels": {"pressure": 0.0}},
        emotion_state={"COR": 0.0},
        expectation_pressure_trace={
            "anchor_verification": {
                "anchors": [
                    {
                        "anchor_id": "pressure:state:mem-risk",
                        "anchor_type": "pressure",
                        "source_memory_id": "mem-risk",
                        "level": 0.82,
                        "expected_punishment": 0.6,
                        "expected_pressure": 0.4,
                    }
                ]
            }
        },
    )
    assert trace["vetoed_action_ids"] == ["action::text_commit"]
    assert trace["anchor_risk"]["top_source_memory_id"] == "mem-risk"
    assert "pressure_anchor_veto" in trace["reviewed"][0]["reasons"]


def test_safety_gate_require_review_also_blocks_external_execution() -> None:
    gate = SafetyGate(enabled=True, veto_pressure_threshold=0.9, review_pressure_threshold=0.3, min_external_confidence=0.2)
    selected = [
        {
            "action_id": "action::tool_call",
            "actuator_id": "actuator::tool_api",
            "predicted_outcome": {"pressure": 0.35, "punishment": 0.0, "confidence": 0.8},
        }
    ]
    trace = gate.review(
        tick_index=5,
        candidates=selected,
        selected_actions=selected,
        cognitive_feelings={"channels": {"pressure": 0.34}},
        emotion_state={"COR": 0.0},
    )
    assert trace["vetoed_action_ids"] == []
    assert trace["require_review_action_ids"] == ["action::tool_call"]
    assert trace["selected_actions"] == []
    assert trace["inhibition_items"][0]["anchor_meta"]["decision"] == "require_review"


def test_runtime_exposes_innate_trace_and_action_registry() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    trace = runtime.process_text_tick("alpha beta", trace_mode="debug")
    innate = trace["innate_rules"]
    assert innate["validation"]["ok"]
    assert "post_prediction_validation" in innate["phases"]
    assert "action_preselect" in innate["phases"]
    assert "actuator::memory_recall" in innate["actuator_registry"]
    assert "action::text_reread" in innate["action_registry"]
    assert "innate_rules" in trace["explainability"]


def test_runtime_action_items_match_safety_filtered_selection_when_external_vetoed() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    selected = [
        {
            "action_id": "action::text_commit",
            "actuator_id": "actuator::text_editor",
            "drive": 1.2,
            "predicted_outcome": {"pressure": 0.8, "punishment": 0.2, "confidence": 0.3},
        }
    ]
    safety = runtime.safety_gate.review(
        tick_index=1,
        candidates=selected,
        selected_actions=selected,
        cognitive_feelings={"channels": {"pressure": 0.8}},
        emotion_state={"COR": 0.4},
    )
    action_items = runtime.action_planner.build_action_items(safety["selected_actions"], tick_index=1)
    assert not action_items
    assert safety["inhibition_items"]


def test_visual_and_auditory_focus_actuators_emit_control_state_items() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    selected = [
        {
            "action_id": "action::move_gaze_to",
            "actuator_id": "actuator::visual_gaze_center",
            "drive": 0.9,
            "effective_decisiveness": 0.4,
            "params": {"x": 0.2, "y": 0.8, "target": "vision::red"},
        },
        {
            "action_id": "action::slide_audio_band",
            "actuator_id": "actuator::auditory_band_center",
            "drive": 0.82,
            "effective_decisiveness": 0.5,
            "params": {"center_hz": 1800.0, "target": "audio::voice"},
        },
    ]
    visual = runtime.visual_gaze_actuator.step(tick_index=1, selected_actions=selected, attention_trace={"selected_labels": ["vision::red"]})
    auditory = runtime.auditory_band_actuator.step(tick_index=1, selected_actions=selected, attention_trace={"selected_labels": ["audio::voice"]})
    assert visual["items"][0]["sa_label"] == "control::visual_gaze"
    assert visual["state"]["center_x"] == 0.2
    assert visual["state"]["center_y"] == 0.8
    assert auditory["items"][0]["sa_label"] == "control::auditory_band"
    assert auditory["state"]["center_hz"] != 1000.0


def test_visual_and_audio_control_state_is_consumed_by_sensors_next_tick() -> None:
    import io
    import math
    import wave

    from PIL import Image, ImageDraw

    runtime = APV21Runtime(config=RuntimeConfig())
    runtime.visual_gaze_actuator.step(
        tick_index=1,
        selected_actions=[{"action_id": "action::move_gaze_to", "drive": 1.0, "effective_decisiveness": 0.6, "params": {"x": 0.25, "y": 0.25}}],
        attention_trace={"selected_labels": ["vision::red"]},
    )
    img = Image.new("RGB", (96, 96), "white")
    draw = ImageDraw.Draw(img)
    draw.rectangle((12, 12, 38, 38), fill="red")
    draw.rectangle((60, 60, 86, 86), fill="blue")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    vision = runtime._ingest_vision_bytes(buf.getvalue())
    current = vision["inner_vision"]["current_frame"]
    assert current["sensor_focus_state"]["center_x"] == 0.25
    object_rows = [row for row in vision["state_items"] if row["family"] == "vision_object"]
    assert object_rows
    assert any((row["anchor_meta"].get("sampling_focus", {}) or {}).get("precision", 0.0) > 0.24 for row in object_rows)

    runtime.auditory_band_actuator.step(
        tick_index=1,
        selected_actions=[{"action_id": "action::lock_audio_band", "drive": 1.0, "effective_decisiveness": 0.6, "params": {"center_hz": 440.0}}],
        attention_trace={"selected_labels": ["audio::tone"]},
    )
    audio_buf = io.BytesIO()
    sample_rate = 8000
    with wave.open(audio_buf, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(sample_rate)
        frames = []
        for idx in range(sample_rate // 10):
            value = int(18000 * math.sin(2 * math.pi * 440.0 * idx / sample_rate))
            frames.append(value.to_bytes(2, "little", signed=True))
        wav.writeframes(b"".join(frames))
    audio = runtime._ingest_audio_bytes(audio_buf.getvalue())
    preview = audio["inner_audio"]["preview_asset_ref"]
    assert preview["sensor_focus_state"]["center_hz"] == 440.0
    event = next(row for row in audio["state_items"] if row["sa_label"] == "audio_event::current")
    assert event["anchor_meta"]["sampling_focus"]["center_hz"] == 440.0
    assert event["numeric_features"]["audio.focus_band"]


def test_explicit_punishment_feedback_has_real_event_and_virtual_pressure() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    items = runtime._build_explicit_feedback_items(
        {"punishment": 0.7, "reward": 0.0, "correctness": 0.0, "confidence": 0.9, "source": "test"}
    )
    punishment = next(row for row in items if row["sa_label"] == "signal::punishment")
    assert punishment["real_energy"] == 0.7
    assert punishment["virtual_energy"] == 0.7
    semantics = punishment["anchor_meta"]["feedback_energy_semantics"]
    assert semantics["meaning"] == "punishment_event_as_real;future_avoidance_pressure_as_virtual"


def test_runtime_remembers_innate_attention_bias_for_next_tick_selection() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    runtime._remember_innate_attention_biases(
        {
            "post_prediction_validation": {
                "attention_biases": [
                    {
                        "schema_id": "innate_attention_bias/v1",
                        "bias": "surprise_anchor",
                        "target_labels": ["text::flash"],
                        "strength": 0.8,
                        "rule_id": "CF-001",
                    }
                ]
            }
        }
    )
    consumed = runtime._consume_pending_innate_attention_biases()
    assert consumed[0]["target_labels"] == ["text::flash"]
    assert runtime._consume_pending_innate_attention_biases() == []


def test_action_control_router_builds_focus_anchor_and_residual_controls() -> None:
    router = ActionControlEffectRouter()
    trace = router.build(
        tick_index=7,
        selected_actions=[
            {
                "action_id": "action::focus_anchor",
                "drive": 0.92,
                "effective_threshold": 0.4,
                "innate_nodes": [{"strength": 0.9, "params": {"anchor_label": "text::flash"}}],
            },
            {
                "action_id": "action::inspect_residual",
                "drive": 0.88,
                "effective_threshold": 0.4,
            },
        ],
        attention_trace={"selected_labels": ["text::plain"], "ranked_items": [{"sa_label": "text::plain"}, {"sa_label": "text::flash"}]},
        state_snapshot_items=[
            {"sa_label": "text::plain", "family": "text", "source_type": "external_text", "real_energy": 0.5, "virtual_energy": 0.0, "cognitive_pressure": 0.5},
            {"sa_label": "text::flash", "family": "text", "source_type": "external_text", "real_energy": 0.3, "virtual_energy": 0.0, "cognitive_pressure": 0.3},
            {"sa_label": "text::3", "family": "text", "source_type": "predicted", "real_energy": 0.0, "virtual_energy": 0.6, "cognitive_pressure": -0.6},
            {"sa_label": "text::0", "family": "text", "source_type": "external_text", "real_energy": 0.8, "virtual_energy": 0.0, "cognitive_pressure": 0.8},
        ],
        prediction_trace={"missed_predicted_labels": ["text::3"], "unexpected_labels": ["text::0"], "mismatch_ratio": 0.8},
        residual_summary={"total_unresolved_mass": 1.4},
        previous_focus_labels=["text::plain"],
    )
    labels = [row["sa_label"] for row in trace["control_items"]]
    assert "control::attention_anchor" in labels
    assert "control::residual_inspection" in labels
    focus_control = next(row for row in trace["attention_controls"] if row["control_kind"] == "focus_anchor")
    assert "text::flash" in focus_control["boost_labels"]
    residual = next(row for row in trace["effects"] if row["control_kind"] == "inspect_residual")
    assert residual["slow_query_hints"]
    meta = next(row for row in trace["control_items"] if row["sa_label"] == "control::residual_inspection")["anchor_meta"]
    assert meta["paired_labels"][0]["predicted"] == "text::3"
    assert meta["paired_labels"][0]["actual"] == "text::0"


def test_action_attention_control_biases_and_suppresses_labels() -> None:
    selector = AttentionSelector(focus_limit=1, pressure_gain=0.6, attention_gain_weight=0.8, fatigue_weight=0.5)
    rows = [
        {"sa_label": "text::old", "cognitive_pressure": 0.5, "attention_gain": 0.0, "virtual_energy": 0.0, "fatigue": 0.0},
        {"sa_label": "text::new", "cognitive_pressure": 0.2, "attention_gain": 0.0, "virtual_energy": 0.0, "fatigue": 0.0},
    ]
    boosted = selector.select(
        rows,
        action_attention_controls=[
            {
                "schema_id": "action_attention_control/v1",
                "source_action_id": "action::focus_anchor",
                "control_kind": "focus_anchor",
                "boost_labels": ["text::new"],
                "suppress_labels": ["text::old"],
                "strength": 0.8,
                "ttl": 1,
            }
        ],
    )
    assert boosted["selected_labels"] == ["text::new"]
    new_row = next(row for row in boosted["ranked_items"] if row["sa_label"] == "text::new")
    old_row = next(row for row in boosted["ranked_items"] if row["sa_label"] == "text::old")
    assert new_row["action_attention_boost"] > 0.0
    assert old_row["action_attention_suppression"] > 0.0


def test_innate_engine_detects_actuator_level_external_candidates_and_ui_metrics() -> None:
    engine = InnateCodingEngine(min_fire_strength=0.001)
    pressure = engine.simulate(
        phase="action_preselect",
        context={
            "tick_index": 1,
            "feelings": {"channels": {"pressure": 1.0}},
            "action_trace": {
                "candidates": [
                    {
                        "action_id": "action::text_commit",
                        "actuator_id": "actuator::text_editor",
                        "predicted_outcome": {"pressure": 0.4, "confidence": 0.9},
                    }
                ]
            },
        },
    )
    assert any(hit["rule_id"] == "AC-013" for hit in pressure["hits"])
    assert pressure["metrics"]["pressure_external_candidate"] > 0.0

    ui_context = {
        "tick_index": 2,
        "state_items": [
            {
                "sa_label": "vision_ui::button::ok",
                "family": "vision_ui",
                "source_type": "vision_numeric",
                "real_energy": 0.9,
                "anchor_meta": {"ui_role": "button", "ui_target": True, "bbox_norm": [0.42, 0.62, 0.12, 0.06], "confidence": 0.92},
                "numeric_features": {"ui.target": 0.92},
            }
        ],
        "feelings": {"channels": {"correctness": 0.9, "pressure": 0.0}},
        "ui_trace": {"safe_to_click": 0.9, "pointer_on_target": 0.8},
        "pointer_trace": {"on_target": 0.88},
    }
    ui = engine.simulate(phase="action_preselect", context=ui_context)
    assert any(hit["rule_id"] == "AC-017" for hit in ui["hits"])
    assert any(hit["rule_id"] == "AC-018" for hit in ui["hits"])
    move = next(row for row in ui["action_nodes"] if row["action_id"] == "action::pointer_move")
    click = next(row for row in ui["action_nodes"] if row["action_id"] == "action::pointer_click")
    assert move["params"]["target"] == "vision_ui::button::ok"
    assert click["params"]["button"] == "left"


def test_runtime_consumes_action_attention_control_on_next_tick() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    runtime.state_pool.apply_external_items(
        [
            {"sa_label": "text::plain", "display_text": "plain", "family": "text", "source_type": "external_text", "real_energy": 0.55},
            {"sa_label": "text::flash", "display_text": "flash", "family": "text", "source_type": "external_text", "real_energy": 0.24},
        ],
        tick_index=0,
    )
    runtime._pending_action_attention_controls = [
        {
            "schema_id": "action_attention_control/v1",
            "source_action_id": "action::focus_anchor",
            "source_tick_index": 0,
            "control_kind": "focus_anchor",
            "boost_labels": ["text::flash"],
            "suppress_labels": [],
            "strength": 0.85,
            "ttl": 1,
            "reason": "test_focus_anchor",
        }
    ]
    runtime.tick_index = 0
    r_state = runtime.state_pool.read_r_state()
    candidates = runtime._r_state_to_attention_candidates(r_state)
    attention = runtime.attention.select(
        candidates,
        action_attention_controls=runtime._consume_pending_action_attention_controls(),
    )
    flash = next(row for row in attention["ranked_items"] if row["sa_label"] == "text::flash")
    assert flash["action_attention_boost"] > 0.0
    assert any(row.get("control_kind") == "focus_anchor" for row in attention["action_attention_controls"])
    assert runtime._pending_action_attention_controls == []


def test_runtime_slow_query_consumes_action_residual_hint_without_fabricating_missing_label() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    runtime.tick_index = 3
    runtime.state_pool.apply_external_items(
        [
            {"sa_label": "text::3", "display_text": "3", "family": "text", "source_type": "external_text", "real_energy": 0.2, "virtual_energy": 0.6},
            {"sa_label": "text::0", "display_text": "0", "family": "text", "source_type": "external_text", "real_energy": 0.7},
        ],
        tick_index=3,
    )
    slow_query = runtime._build_slow_query(
        selected_focus_items=[],
        action_slow_query_hints=[
            {
                "schema_id": "action_slow_query_hint/v1",
                "source_action_id": "action::inspect_residual",
                "control_kind": "inspect_residual",
                "sa_label": "text::3",
                "query_weight": 0.9,
                "virtual_energy": 0.4,
                "ttl": 1,
            },
            {
                "schema_id": "action_slow_query_hint/v1",
                "source_action_id": "action::inspect_residual",
                "control_kind": "inspect_residual",
                "sa_label": "text::0",
                "query_weight": 0.85,
                "virtual_energy": 0.3,
                "ttl": 1,
            },
            {
                "schema_id": "action_slow_query_hint/v1",
                "source_action_id": "action::focus_anchor",
                "control_kind": "focus_anchor",
                "sa_label": "text::missing",
                "query_weight": 1.2,
                "virtual_energy": 0.5,
                "ttl": 1,
            },
        ],
    )
    labels = [row["sa_label"] for row in slow_query]
    assert "text::3" in labels
    assert "text::0" in labels
    assert "text::missing" not in labels
    hinted = [row for row in slow_query if row["sa_label"] in {"text::3", "text::0"}]
    assert all("action_control_hint" in (row.get("query_sources", []) or [row.get("source_type")]) for row in hinted)


def test_action_control_events_enter_full_sa_state_field_learning() -> None:
    from miya_psyarch.memory.store import MemoryStore

    memory = MemoryStore(
        recall_top_k=3,
        predict_top_k=2,
        prediction_energy_scale=0.5,
        max_snapshots_per_kind=16,
        candidate_limit=8,
        scoring_candidate_limit=8,
        online_min_support_to_promote=1,
        online_per_tick_update_limit=32,
    )
    items = [
        {
            "sa_label": "text::context",
            "display_text": "context",
            "source_type": "external_text",
            "family": "text",
            "real_energy": 1.0,
            "virtual_energy": 0.1,
            "cognitive_pressure": 0.9,
        },
        {
            "sa_label": "control::attention_anchor",
            "display_text": "attention anchor",
            "source_type": "action_control",
            "family": "action_control",
            "real_energy": 2.0,
            "virtual_energy": 0.0,
            "cognitive_pressure": 2.0,
        },
    ]
    memory.write_snapshot(tick_index=0, memory_kind="state", items=items, focus_labels=[], source_text="")
    memory.process_idle_index_maintenance(budget=4, max_ms=50.0)
    latest = memory.latest_snapshot("state") or {}
    state_labels = [str(item.get("sa_label", "") or "") for item in latest.get("state_field_items", [])]
    energy = memory.online_embedding_summary()["energy_learning"]
    assert "control::attention_anchor" in state_labels
    assert any(
        "control::" in str(event.get("source", "") or "") or "control::" in str(event.get("target", "") or "")
        for event in energy["last_events"]
    )


def test_action_control_target_modulation_uses_attention_gain_not_concept_energy() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    runtime.state_pool.apply_external_items(
        [{"sa_label": "text::context", "display_text": "context", "source_type": "external_text", "family": "text", "real_energy": 1.0}],
        tick_index=0,
    )
    before = runtime.state_pool.rows_for_labels(["text::context"])[0]
    runtime.state_pool.apply_external_items(
        [
            {
                "sa_label": "text::context",
                "display_text": "context",
                "source_type": "action_control",
                "family": "action_control",
                "attention_gain": 0.5,
                "virtual_energy": 0.9,
                "anchor_meta": {"control_kind": "focus_anchor", "target_modulation": "boost"},
            }
        ],
        tick_index=1,
    )
    after = runtime.state_pool.rows_for_labels(["text::context"])[0]
    assert after["attention_gain"] > before["attention_gain"]
    assert after["virtual_energy"] == before["virtual_energy"]


def test_text_action_actuator_direct_insert_replace_delete_commit() -> None:
    actuator = TextActionActuator()
    inserted = actuator.step(
        tick_index=1,
        input_text="",
        selected_actions=[{"action_id": "action::text_insert", "params": {"token": "hello"}}],
        fast_cn=[],
        slow_cn=[],
        focus_labels=[],
        cognitive_feelings={"channels": {}},
    )
    assert inserted["visible_text"] == "hello"
    assert inserted["output_items"][0]["sa_label"] == "text_action::insert::hello"

    replaced = actuator.step(
        tick_index=2,
        input_text="",
        selected_actions=[{"action_id": "action::text_replace", "params": {"new_text": "hi"}}],
        fast_cn=[],
        slow_cn=[],
        focus_labels=[],
        cognitive_feelings={"channels": {}},
    )
    assert replaced["visible_text"] == "hi"
    assert replaced["revision_detected"] is True
    assert any(row["sa_label"] == "text_action::replace::hi" for row in replaced["output_items"])

    committed = actuator.step(
        tick_index=3,
        input_text="",
        selected_actions=[{"action_id": "action::text_commit", "params": {"target_channel": "draft"}}],
        fast_cn=[],
        slow_cn=[],
        focus_labels=[],
        cognitive_feelings={"channels": {}},
    )
    assert committed["visible_text"] == ""
    assert committed["recent_events"][0]["event_type"] == "commit"
    assert committed["recent_events"][0]["token"] == "hi"
    assert committed["recent_events"][0]["visible_text_after"] == ""
    assert "commit_clears_visible_text_buffer" in committed["recent_events"][0]["notes"]
    assert committed["output_items"][0]["sa_label"] == "text_action::commit"
    assert any(row["sa_label"] == "text_action::sent::hi" for row in committed["output_items"])

    deleted = actuator.step(
        tick_index=4,
        input_text="",
        selected_actions=[{"action_id": "action::text_delete", "params": {}}],
        fast_cn=[],
        slow_cn=[],
        focus_labels=[],
        cognitive_feelings={"channels": {}},
    )
    assert deleted["visible_text"] == ""
    assert deleted["recent_events"][0]["event_type"] == "delete"


def test_timefelt_recall_control_restores_target_delta_snapshot_labels() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    old = runtime.memory.write_snapshot(
        tick_index=4,
        memory_kind="state",
        items=[
            {"sa_label": "text::beat", "family": "text", "source_type": "external_text", "real_energy": 0.9},
            {"sa_label": "text::bass", "family": "text", "source_type": "external_text", "real_energy": 0.7},
        ],
        focus_labels=["text::beat"],
        source_text="beat bass",
    )
    runtime.memory.write_snapshot(
        tick_index=7,
        memory_kind="state",
        items=[
            {"sa_label": "text::noise", "family": "text", "source_type": "external_text", "real_energy": 0.4},
        ],
        focus_labels=["text::noise"],
        source_text="noise",
    )
    runtime.tick_index = 8
    rows = runtime._timefelt_recall_control_rows(
        selected_action={"action_id": "action::recall_by_timefelt", "drive": 0.9, "effective_threshold": 0.3},
        state_snapshot_items=[
            {"sa_label": "text::beat", "family": "text", "source_type": "external_text", "real_energy": 0.8},
        ],
        time_context={"current_tick": 8, "target_delta_t": 4, "time_sigma": 1.0, "confidence": 1.0, "gain": 3.0, "felt_energy": 1.0},
        limit=6,
    )
    labels = [row["sa_label"] for row in rows]
    assert "control::timefelt_recall" in labels
    assert "text::bass" in labels
    meta = rows[0]["anchor_meta"]
    assert old["memory_id"] in meta["source_memory_ids"]
    assert meta["target_delta_t"] == 4.0
    assert meta["learning_boundary"].startswith("timefelt_recall_modulates")


def test_episode_replay_control_summarizes_risk_and_can_raise_safety_review() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    written = runtime.memory.write_snapshot(
        tick_index=3,
        memory_kind="state",
        items=[
            {"sa_label": "text::button", "family": "text", "source_type": "external_text", "real_energy": 0.8},
            {
                "sa_label": "action_feedback::text_commit",
                "display_text": "行动反馈:text_commit",
                "family": "action_feedback",
                "source_type": "action_feedback",
                "real_energy": 0.0,
                "virtual_energy": 0.7,
                "anchor_meta": {
                    "action_id": "action::text_commit",
                    "observed_feedback": {"reward": 0.0, "punishment": 0.8, "correctness": 0.0, "confidence": 0.9},
                    "feedback_energy_semantics": {"punishment_pressure": 0.66},
                },
            },
        ],
        focus_labels=["text::button"],
        source_text="button",
    )
    rows = runtime._episode_replay_control_rows(
        selected_action={
            "action_id": "action::replay_episode",
            "drive": 1.0,
            "effective_threshold": 0.3,
            "params": {"source_memory_id": written["memory_id"], "risk": 0.7},
        },
        expectation_pressure_trace={},
        action_consequence_trace={},
        limit=6,
    )
    control = rows[0]
    assert control["sa_label"] == "control::episode_replay"
    assert control["anchor_meta"]["source_memory_id"] == written["memory_id"]
    assert control["anchor_meta"]["feedback_summary"]["punishment"] > 0.0
    assert control["anchor_meta"]["safety_review_hint"]["requires_external_review"] is True

    gate = SafetyGate(enabled=True, veto_pressure_threshold=0.9, review_pressure_threshold=0.2, min_external_confidence=0.1)
    selected = [
        {
            "action_id": "action::text_commit",
            "actuator_id": "actuator::text_editor",
            "predicted_outcome": {"pressure": 0.0, "punishment": 0.0, "confidence": 0.9},
        }
    ]
    reviewed = gate.review(
        tick_index=4,
        candidates=selected,
        selected_actions=selected,
        cognitive_feelings={"channels": {}},
        emotion_state={},
        action_control_items=rows,
    )
    assert reviewed["vetoed_action_ids"] == ["action::text_commit"] or reviewed["require_review_action_ids"] == ["action::text_commit"]
    assert reviewed["selected_actions"] == []
    assert "action_control_review" in reviewed["reviewed"][0]["reasons"]


def test_wait_control_item_and_feedback_have_wait_semantics() -> None:
    runtime = APV21Runtime(config=RuntimeConfig())
    selected = [
        {
            "action_id": "action::wait",
            "drive": 0.74,
            "effective_threshold": 0.3,
            "effective_decisiveness": 0.44,
            "params": {"duration_ticks": 1, "rhythm_expectation": 0.8, "uncertainty": 0.7},
            "predicted_outcome": {"confidence": 0.5},
        }
    ]
    control = runtime._wait_control_row(selected_action=selected[0])
    assert control["sa_label"] == "control::timing_wait"
    assert control["anchor_meta"]["external_action_review_hint"] > 0.0
    feedback = runtime._observe_action_feedback(
        selected_actions=selected,
        feedback_context={
            "top_labels_after_control": ["control::timing_wait"],
            "focus_labels_after_control": [],
            "action_control_effects": [control["anchor_meta"]],
        },
    )
    assert "timing_wait_semantics" in feedback["notes"]
    assert feedback["reward"] > feedback["punishment"]


def test_text_action_actuator_supports_cursor_span_middle_replace_and_delete() -> None:
    actuator = TextActionActuator(max_visible_buffer=16)
    for idx, token in enumerate("1020", start=1):
        actuator.step(
            tick_index=idx,
            input_text="",
            selected_actions=[{"action_id": "action::text_insert", "params": {"token": token}}],
            fast_cn=[],
            slow_cn=[],
            focus_labels=[],
            cognitive_feelings={"channels": {}},
        )
    replaced = actuator.step(
        tick_index=5,
        input_text="",
        selected_actions=[{"action_id": "action::text_replace", "params": {"span": [1, 3], "new_text": "23"}}],
        fast_cn=[],
        slow_cn=[],
        focus_labels=[],
        cognitive_feelings={"channels": {}},
    )
    assert replaced["visible_text"] == "1230"
    event = replaced["recent_events"][0]
    assert event["span"] == [1, 3]
    assert event["visible_text_before"] == "1020"
    assert event["visible_text_after"] == "1230"

    deleted = actuator.step(
        tick_index=6,
        input_text="",
        selected_actions=[{"action_id": "action::text_delete", "params": {"span": [1, 3]}}],
        fast_cn=[],
        slow_cn=[],
        focus_labels=[],
        cognitive_feelings={"channels": {}},
    )
    assert deleted["visible_text"] == "10"
    assert deleted["recent_events"][0]["token"] == "23"


def test_action_planner_competition_trace_records_suppressed_same_domain_action() -> None:
    planner = ActionConsequencePlanner(
        enabled=True,
        selection_threshold=0.1,
        max_selected_actions=4,
        fatigue_decay=0.9,
        fatigue_step=0.0,
        bias_learning_rate=0.0,
        bias_gain=0.0,
        confidence_gain=0.18,
        wait_base_drive=0.18,
    )
    trace = planner.plan(
        tick_index=1,
        state_snapshot_items=[],
        fast_bn=[],
        fast_cn=[],
        slow_bn=[],
        slow_cn=[],
        cognitive_feelings={"channels": {"dissonance": 1.0, "surprise": 1.0, "pressure": 0.6}},
        rhythm_trace={"channels": {}},
        time_trace={"channels": {}},
        innate_action_nodes=[
            {"action_id": "action::focus_anchor", "actuator_id": "actuator::attention_allocation", "drive": 0.7, "strength": 0.9},
            {"action_id": "action::inspect_residual", "actuator_id": "actuator::attention_allocation", "drive": 0.65, "strength": 0.9},
        ],
    )
    comp = trace["competition_trace"]
    assert comp["schema_id"] == "action_competition_trace/v1"
    attention_domain = next(row for row in comp["domains"] if row["conflict_domain"] == "attention_focus_width_and_anchor")
    assert attention_domain["winner_action_id"] in {"action::focus_anchor", "action::inspect_residual", "action::diverge_attention"}
    assert attention_domain["suppressed_action_ids"]
    selected_attention = [
        row for row in trace["selected_actions"] if row.get("conflict_domain") == "attention_focus_width_and_anchor"
    ]
    assert len(selected_attention) == 1

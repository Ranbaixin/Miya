from __future__ import annotations

from miya_psyarch.memory.short_term.memory_window import ShortTermMemoryWindow


def _item(label: str, *, energy: float = 0.6) -> dict:
    return {
        "sa_label": label,
        "display_text": label,
        "family": "test",
        "source_type": "test",
        "real_energy": energy,
    }


def test_resolve_unfinished_softens_matching_trace_without_queue_semantics() -> None:
    window = ShortTermMemoryWindow(history_limit=8, max_age_ticks=40, fatigue_step=0.0)
    window.observe([_item("task::A"), _item("text::红色苹果")], tick_index=1, source_kind="thought", modality="text")
    mark_a = window.mark_unfinished(tick_index=2, labels=["task::A", "text::红色苹果"], reason="interrupted_A", strength=1.0)
    window.observe([_item("task::B"), _item("text::黄色香蕉")], tick_index=3, source_kind="thought", modality="text")
    mark_b = window.mark_unfinished(tick_index=4, labels=["task::B", "text::黄色香蕉"], reason="interrupted_B", strength=1.0)

    assert mark_a["stored"]
    assert mark_b["stored"]
    before = window.trace(tick_index=4)["unfinished"]["top"]
    assert len(before) == 2

    resolved = window.resolve_unfinished(
        tick_index=5,
        labels=["task::B", "text::黄色香蕉"],
        reason="commit_closed_B",
        amount=1.2,
    )

    assert resolved["resolved"]
    assert resolved["policy"] == "action_feedback_softens_matching_unfinished_traces_not_task_queue_completion"
    assert resolved["remaining_active_count"] == 1
    after = window.trace(tick_index=5)["unfinished"]["top"]
    assert len(after) == 1
    assert after[0]["reason"] == "interrupted_A"
    assert "task::A" in after[0]["labels"]


def test_partial_resolve_leaves_weaker_unfinished_trace_recallable() -> None:
    window = ShortTermMemoryWindow(history_limit=8, max_age_ticks=40, fatigue_step=0.0)
    window.observe([_item("task::A"), _item("text::红色苹果")], tick_index=1, source_kind="thought", modality="text")
    window.mark_unfinished(tick_index=2, labels=["task::A", "text::红色苹果"], reason="interrupted_A", strength=1.0)

    resolved = window.resolve_unfinished(tick_index=3, labels=["task::A"], reason="partly_closed_A", amount=0.35)
    assert resolved["resolved"]

    trace = window.trace(tick_index=3)["unfinished"]["top"]
    assert len(trace) == 1
    assert 0.0 < trace[0]["strength"] < 1.0
    recall = window.recall(tick_index=3, cues=[], limit=4, horizon_ticks=20, reason="no_param_recent_context")
    assert recall["available"]
    assert any("task::A" in event["labels"] for event in recall["selected_events"])

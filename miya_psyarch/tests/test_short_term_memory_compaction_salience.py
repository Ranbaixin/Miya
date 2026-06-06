from __future__ import annotations

from miya_psyarch.memory.short_term.memory_window import ShortTermMemoryWindow


def _item(label: str, *, energy: float) -> dict:
    return {
        "sa_label": label,
        "display_text": label,
        "family": "test",
        "source_type": "test",
        "real_energy": energy,
    }


def test_observe_keeps_late_high_salience_items_before_compaction_limit() -> None:
    window = ShortTermMemoryWindow(history_limit=8, max_age_ticks=40, fatigue_step=0.0, max_items_per_event=4)
    low_energy_prefix = [_item(f"curriculum::{index}", energy=0.05) for index in range(12)]
    stored = window.observe(
        [*low_energy_prefix, _item("task::late_current_focus", energy=0.95)],
        tick_index=1,
        source_kind="thought",
        modality="text",
    )
    assert stored["stored"]

    marked = window.mark_unfinished(
        tick_index=2,
        labels=["task::late_current_focus"],
        reason="interrupted_after_late_salient_focus",
        strength=1.0,
    )

    assert marked["stored"]
    recall = window.recall(tick_index=3, cues=[], limit=4, horizon_ticks=20, reason="no_param_recent_context")
    assert any("task::late_current_focus" in event["labels"] for event in recall["selected_events"])

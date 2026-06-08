"""测试通道: channels 模块集成测试"""

import pytest


class TestRhythmChannel:
    def test_create_and_observe(self):
        from miya_psyarch.channels.rhythm.channel import RhythmChannel

        ch = RhythmChannel(
            enabled=True,
            window=12,
            min_hits=3,
            min_period=2.0,
            max_period=30.0,
            period_sigma_scale=0.3,
            phase_sigma_scale=0.5,
            pulse_threshold=0.5,
            phase_threshold=0.6,
            fatigue_decay=0.9,
            fatigue_step=0.15,
            fatigue_gain=1.0,
            fatigue_max=3.0,
            salience_threshold=0.3,
        )
        for i in range(12):
            ch.observe(tick_index=i, focus_items=[{"sa_label": "test::topic", "focus_score": 0.7 + i * 0.02}])
        result = ch.derive(tick_index=12)
        assert "channels" in result
        # 低 min_hits + 密集观察应产生输出
        assert isinstance(result, dict)

    def test_disabled_returns_empty(self):
        from miya_psyarch.channels.rhythm.channel import RhythmChannel

        ch = RhythmChannel(
            enabled=False,
            window=12,
            min_hits=3,
            min_period=2.0,
            max_period=30.0,
            period_sigma_scale=0.3,
            phase_sigma_scale=0.5,
            pulse_threshold=0.5,
            phase_threshold=0.6,
            fatigue_decay=0.9,
            fatigue_step=0.15,
            fatigue_gain=1.0,
            fatigue_max=3.0,
            salience_threshold=0.3,
        )
        ch.observe(tick_index=0, focus_items=[{"sa_label": "test::topic", "focus_score": 0.8}])
        result = ch.derive(tick_index=1)
        assert result["channels"] == {}


class TestTaskFeelingChannel:
    def test_derive_output_structure(self):
        from miya_psyarch.channels.task_feeling.channel import TaskFeelingChannel

        ch = TaskFeelingChannel()
        state = ch.derive(
            tick_index=0,
            input_packet=None,
            expected_text=None,
            focus_continuation_trace=None,
            short_term_memory_trace=None,
            cognitive_feelings=None,
            residual_summary=None,
        )
        assert "channels" in state
        channels = state["channels"]
        assert "boredom" in channels
        assert "fulfillment" in channels

    def test_idle_yields_boredom(self):
        from miya_psyarch.channels.task_feeling.channel import TaskFeelingChannel

        ch = TaskFeelingChannel()
        state = ch.derive(
            tick_index=5,
            input_packet={"units": [], "normalized_text": ""},
            expected_text={"strength": 0.05, "top_share": 0.0, "dominance_gap": 0.0},
            focus_continuation_trace={"continuation_strength": 0.05},
            short_term_memory_trace={"last_recall": {"selected_events": []}},
            cognitive_feelings={"channels": {}},
            residual_summary={},
        )
        assert state["channels"]["boredom"] > 0

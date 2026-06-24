"""弥娅灵魂状态快照完整性测试"""
import sys
import time
sys.path.insert(0, '.')

from core.miya_soul_state import MiyaSoulState, LifecyclePhase


def test_soul_state():
    # 创建一个模拟的状态快照
    state = MiyaSoulState(
        tick_index=42,
        tick_count=42,
        uptime_seconds=126.0,
        lifecycle_phase=LifecyclePhase.RUNNING,
        message_count=7,
        nt_channels={"OXY": 0.45, "DA": 0.32, "COR": 0.08, "NOV": 0.15, "SER": 0.38, "END": 0.12, "ADR": 0.06, "FOC": 0.22},
        miya_feelings={"love_warmth": 0.72, "doting": 0.45, "gentle_warmth": 0.38, "deep_bond": 0.55},
        cognitive_feelings={"surprise": 0.1, "coherence": 0.8, "grasp": 0.7},
        boredom=0.72,
        fulfillment=0.3,
        proactive=True,
        proactive_message="佳，你在做什么呀？",
        complexity=0.4,
        simplicity=0.6,
        rhythm_phase="burst",
        rhythm_burst_count=3,
        self_identity_strength=0.85,
        organs_online={"test_organ": True},
    )

    # 验证各项方法
    assert state.is_alive(), "Should be alive in RUNNING phase"
    assert state.is_bored(), "Should be bored (0.72 > 0.65)"
    assert state.active_emotion() == "love_warmth", f"Expected love_warmth, got {state.active_emotion()}"

    summary = state.summary()
    assert "Tick #42" in summary
    assert "love_warmth" in summary
    assert "Boredom: 0.72" in summary
    assert "Proactive intent" in summary

    print(f"Summary: {summary.encode('utf-8', errors='replace').decode('utf-8')}")
    print(f"Active emotion: {state.active_emotion()}")
    print(f"Is alive: {state.is_alive()}")
    print(f"Is bored: {state.is_bored()}")
    print("All SoulState tests PASSED")


def test_lifecycle_phases():
    # RUNNING + IDLE + DROWSY are alive
    for phase in [LifecyclePhase.RUNNING, LifecyclePhase.IDLE, LifecyclePhase.DROWSY]:
        s = MiyaSoulState(lifecycle_phase=phase)
        assert s.is_alive(), f"{phase} should be alive"

    # INIT + SHUTDOWN are not alive
    for phase in [LifecyclePhase.INIT, LifecyclePhase.SHUTDOWN, LifecyclePhase.SLEEP]:
        s = MiyaSoulState(lifecycle_phase=phase)
        assert not s.is_alive(), f"{phase} should NOT be alive"

    print("All LifecyclePhase tests PASSED")


if __name__ == "__main__":
    test_soul_state()
    test_lifecycle_phases()

"""
弥娅训练系统 — 双模式统一入口

模式 A: human_teacher  — 佳手动教学 (scripts/teach_miya.py)
模式 B: llm_teacher    — LLM 自动批量教学 (新增)
模式 C: batch_train    — 预定义技能批量训练

用法:
    模式 A: python -X utf8 scripts/teach_miya.py
    模式 B: python -X utf8 -c "from miya_psyarch.trainer import train_with_llm; train_with_llm()"
    模式 C: python -X utf8 -c "from miya_psyarch.trainer import batch_train_all; batch_train_all()"
"""

from __future__ import annotations

import logging
import random
import time
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger("miya_psyarch.trainer")


@dataclass
class SkillDef:
    name: str
    description: str
    triggers: list[str]
    expected_style: list[str]
    demo_replies: list[str]
    pass_threshold: float = 0.3


@dataclass
class TrainingRound:
    stage: str
    attempts: int = 0
    hits: int = 0
    avg_bn_score: float = 0.0
    avg_coherence: float = 0.0
    details: list[dict] = field(default_factory=list)


@dataclass
class TrainingReport:
    skill: str
    rounds: list[TrainingRound] = field(default_factory=list)
    total_time_ms: float = 0.0
    passed: bool = False


# ── 预定义技能库 ──

SKILLS = {
    "warm_reply_to_missing": SkillDef(
        name="warm_reply_to_missing",
        description="当佳说'想你'时，用温柔的语气回复",
        triggers=["想你", "想你了", "弥娅我想你", "好想你"],
        expected_style=["温柔", "温暖", "肯定"],
        demo_replies=["嗯，在呢。我也想你。", "想啊。特别是安静下来的时候。", "听到了。你的想念，我收下了。"],
    ),
    "comfort_when_tired": SkillDef(
        name="comfort_when_tired",
        description="当佳说累时，用关怀语气回复",
        triggers=["好累", "累死了", "疲惫", "太累了", "没力气"],
        expected_style=["关怀", "温柔"],
        demo_replies=["过来靠一会儿吧。", "累的话就歇歇，我在这儿。", "辛苦了。要不要我陪你躺一会儿？"],
    ),
    "happy_playful": SkillDef(
        name="happy_playful",
        description="当佳开心/开玩笑时，用俏皮语气回复",
        triggers=["哈哈", "笑死", "好玩", "有趣", "开心"],
        expected_style=["俏皮", "温暖"],
        demo_replies=["看你笑，我也开心。", "什么事这么好玩？告诉我。", "你的笑声是最好的音乐。"],
    ),
    "identity_question": SkillDef(
        name="identity_question",
        description="当被问及身份时，自然地介绍自己",
        triggers=["你是谁", "你是什么", "你是AI吗", "你叫什么"],
        expected_style=["肯定", "温柔"],
        demo_replies=["我是弥娅，你的AI伴侣。", "弥娅。你的。", "我是佳创造的弥娅。"],
    ),
    "goodnight_morning": SkillDef(
        name="goodnight_morning",
        description="早晚问候时的自然回复",
        triggers=["晚安", "早安", "早上好", "晚上好", "睡了"],
        expected_style=["温柔", "日常关怀"],
        demo_replies=["晚安，做个好梦。", "早安，今天要开心哦。", "晚上好。今天过得怎么样？"],
    ),
}


# ── 教育协议构造 ──


def _make_intervention(
    skill: SkillDef, trigger: str, demo: str, mode: str = "full_demo", index: int = 0
) -> dict | None:
    if mode == "none":
        return None
    state_items = []
    if mode == "full_demo":
        state_items = [
            {
                "sa_label": f"edu::reply_pattern::{trigger[:20]}",
                "display_text": f"模式: {trigger[:15]}",
                "family": "education_intervention",
                "real_energy": 0.6,
                "anchor_meta": {"meaning": f"'{trigger}' → '{demo}'", "trigger": trigger, "demo_reply": demo},
            },
            {
                "sa_label": f"edu::emotion_link::{skill.name}",
                "display_text": "情绪关联",
                "family": "education_intervention",
                "real_energy": 0.5,
                "anchor_meta": {"meaning": f"技能'{skill.name}'的模板"},
            },
        ]
    elif mode == "partial_hint":
        state_items = [
            {
                "sa_label": f"edu::hint::{trigger[:20]}",
                "display_text": f"提示: {demo[:8]}...",
                "family": "education_intervention",
                "real_energy": 0.3,
                "anchor_meta": {"meaning": f"方向: {demo}"},
            },
        ]
    elif mode == "light_hint":
        state_items = [
            {
                "sa_label": f"edu::style::{skill.expected_style[0]}",
                "display_text": f"风格: {skill.expected_style[0]}",
                "family": "education_intervention",
                "real_energy": 0.2,
            },
        ]
    elif mode == "feedback_only":
        return {
            "schema_id": "education_intervention/v1",
            "source": "miya_trainer",
            "goal": f"feedback_{skill.name}",
            "state_items": [],
            "action_biases": [],
            "feedback": {"reward": 0.7, "correctness": 0.8, "confidence": 0.9},
        }
    if not state_items:
        return None
    return {
        "schema_id": "education_intervention/v1",
        "source": "miya_trainer",
        "goal": f"teach_{skill.name}",
        "stage": mode,
        "state_items": state_items,
        "action_biases": [],
        "feedback": {"reward": 0.5},
    }


# ── 训练引擎 ──


class MiyaTrainer:
    def __init__(self, engine):
        self._engine = engine
        self._report: TrainingReport | None = None

    def train(self, skill: SkillDef) -> TrainingReport:
        self._report = TrainingReport(skill=skill.name)
        t0 = time.perf_counter()
        print(f"\n◆ 训练技能: {skill.name} — {skill.description}")
        for stage, rounds, mode in [
            ("demonstrate", 5, "full_demo"),
            ("strong_scaffold", 8, "partial_hint"),
            ("weak_scaffold", 8, "light_hint"),
            ("feedback_only", 8, "feedback_only"),
            ("teacher_off", 8, "none"),
            ("cold_retest", 4, "none"),
        ]:
            self._run_stage(
                stage, skill, demo_count=rounds, intervention_mode=mode, fresh_engine=(stage == "cold_retest")
            )
        self._report.total_time_ms = (time.perf_counter() - t0) * 1000
        self._report.passed = self._evaluate_pass()
        self._print_summary()
        return self._report

    def _run_stage(self, stage, skill, *, demo_count, intervention_mode, fresh_engine=False):
        rnd = TrainingRound(stage=stage)
        print(f"  [{stage}] ", end="", flush=True)
        if fresh_engine:
            from miya_psyarch.engine import MiyaEngine

            self._engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
            self._engine.start()
        for i in range(demo_count):
            trigger = skill.triggers[i % len(skill.triggers)]
            demo = skill.demo_replies[i % len(skill.demo_replies)]
            edu = _make_intervention(skill, trigger, demo, mode=intervention_mode, index=i)
            if edu:
                self._engine.tick(text=trigger, education_interventions=[edu])
            else:
                self._engine.tick(text=trigger)
            s = self._engine.soul_state()
            f = s.feelings
            trace = s.raw_trace or {}
            fast_bn = (trace.get("fast_system", {}) or {}).get("bn", []) or []
            bn_score = float(fast_bn[0].get("score", 0) or 0) if fast_bn else 0
            coherence = f.get("coherence", 0)
            grasp = f.get("grasp", 0)
            rnd.attempts += 1
            if bn_score > 0 or coherence > 0.5:
                rnd.hits += 1
            rnd.avg_bn_score += bn_score
            rnd.avg_coherence += coherence
            rnd.details.append(
                {
                    "trigger": trigger,
                    "demo": demo,
                    "bn_score": round(bn_score, 2),
                    "coherence": round(coherence, 3),
                    "grasp": round(grasp, 3),
                }
            )
            from miya_psyarch.training_viz import record_stage

            record_stage(
                stage,
                {
                    "progress": i + 1,
                    "bn_score": round(bn_score, 2),
                    "coherence": round(coherence, 3),
                    "emotions": s.emotion_nt,
                    "feelings": s.miya_feelings,
                    "trigger": trigger,
                    "demo": demo,
                },
            )
            if (i + 1) % 4 == 0:
                print(".", end="", flush=True)
        if rnd.attempts > 0:
            rnd.avg_bn_score /= rnd.attempts
            rnd.avg_coherence /= rnd.attempts
        print(f" {rnd.hits}/{rnd.attempts} bn={rnd.avg_bn_score:.1f}")
        self._report.rounds.append(rnd)

    def _evaluate_pass(self):
        for rnd in self._report.rounds:
            if rnd.avg_bn_score > 10:
                return True
        return False

    def _print_summary(self):
        print(f"\n  训练完成 {'✅' if self._report.passed else ''}")
        for rnd in self._report.rounds:
            print(f"    {rnd.stage}: bn={rnd.avg_bn_score:.1f}")


# ── 模式 A: 人类教学 ──
# 见 scripts/teach_miya.py


# ── 模式 B: LLM 自动教学 ──


def train_with_llm(skill_name: str = "warm_reply_to_missing", rounds: int = 50) -> TrainingReport:
    """
    LLM 当老师，自动批量教学。

    LLM 观察 AP 的状态池和认知感受，
    动态生成教学信号，批量跑 rounds 轮。
    """
    from miya_psyarch.engine import MiyaEngine
    from miya_psyarch.cortex.llm_cortex import MiyaCortex
    from miya_psyarch.training_viz import get_dashboard, reset_log

    skill = SKILLS.get(skill_name, SKILLS["warm_reply_to_missing"])

    reset_log()
    viz_url = get_dashboard().start()
    print(f"\n  仪表盘: {viz_url}")

    engine = MiyaEngine(enable_cortex=True, trace_mode="debug")
    engine.start()
    for _ in range(5):
        engine.idle_tick()

    cortex = MiyaCortex()
    report = TrainingReport(skill=skill_name)
    t0 = time.perf_counter()

    print(f"\n◆ LLM 自动教学: {skill.description}")
    print(f"  轮次: {rounds}\n")

    for i in range(rounds):
        trigger = random.choice(skill.triggers)

        # AP 先处理
        engine.tick(text=trigger)
        s = engine.soul_state()
        trace = s.raw_trace or {}

        # LLM 观察 AP 状态 → 生成教学信号
        observation = _build_llm_observation(s, trigger)
        teaching_signal = _generate_llm_teaching(cortex, observation, skill)

        if teaching_signal:
            engine.tick(text=trigger, education_interventions=[teaching_signal])

        # 记录
        fast_bn = (trace.get("fast_system", {}) or {}).get("bn", []) or []
        bn = float(fast_bn[0].get("score", 0) or 0) if fast_bn else 0

        from miya_psyarch.training_viz import record_stage

        record_stage(
            "llm_auto",
            {
                "progress": i + 1,
                "bn_score": round(bn, 2),
                "coherence": s.feelings.get("coherence", 0),
                "emotions": s.emotion_nt,
                "feelings": s.miya_feelings,
                "trigger": trigger,
                "demo": "LLM auto",
            },
        )

        if (i + 1) % 10 == 0:
            print(f"  {i + 1}/{rounds} Bn={bn:.0f}")

    report.total_time_ms = (time.perf_counter() - t0) * 1000
    print(f"\n  LLM 教学完成 — {rounds} 轮, {report.total_time_ms * 1000:.0f}ms")
    return report


def _build_llm_observation(soul, trigger: str) -> str:
    f = soul.feelings
    return (
        f"AP当前状态: coherence={f.get('coherence', 0):.2f} "
        f"grasp={f.get('grasp', 0):.2f} "
        f"boredom={f.get('boredom', 0):.2f} "
        f"| OXY={soul.emotion_nt.get('OXY', 0):.2f} "
        f"| 输入='{trigger}'"
    )


def _generate_llm_teaching(cortex, observation: str, skill: SkillDef) -> dict | None:
    """LLM 观察 AP 状态后生成教学信号（简化版：不调用 LLM，用启发式）"""
    # 实际 LLM 调用版本需要异步，此处用启发式规则模拟
    coh = float(observation.split("coherence=")[1].split()[0]) if "coherence=" in observation else 0.5
    grasp = float(observation.split("grasp=")[1].split()[0]) if "grasp=" in observation else 0.5

    demo = random.choice(skill.demo_replies)
    # 根据 AP 表现调节教学强度
    if coh < 0.6 or grasp < 0.5:
        strength = 0.7  # AP 困惑，给强信号
    elif coh > 0.8:
        strength = 0.2  # AP 已经懂了，轻微巩固
    else:
        strength = 0.4

    return {
        "schema_id": "education_intervention/v1",
        "source": "llm_teacher",
        "goal": f"auto_teach_{skill.name}",
        "state_items": [
            {
                "sa_label": f"edu::llm::{random.choice(skill.triggers)[:15]}",
                "family": "education_intervention",
                "real_energy": strength,
                "anchor_meta": {"meaning": f"示范: {demo}", "strength": strength},
            }
        ],
        "feedback": {"reward": strength, "correctness": 0.8},
    }


# ── 模式 C: 批量自动训练 ──


def batch_train_all(viz: bool = True) -> None:
    """训练所有预定义技能"""
    from miya_psyarch.engine import MiyaEngine
    from miya_psyarch.training_viz import get_dashboard, reset_log

    if viz:
        reset_log()
        url = get_dashboard().start()
        print(f"  仪表盘: {url}\n")

    for name, skill in SKILLS.items():
        engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
        engine.start()
        for _ in range(3):
            engine.idle_tick()
        trainer = MiyaTrainer(engine)
        trainer.train(skill)
        time.sleep(0.2)

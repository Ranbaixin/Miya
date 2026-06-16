"""
LLM 教师 — 用 DeepSeek V4 Flash 观察 AP 状态并动态生成教学信号

模拟 APV2.1 原型机的 LLMTeacher 模式：
LLM 读 AP 的状态池/情绪/认知感受 → 决定教学策略 → 生成教育协议信号
"""

from __future__ import annotations

import asyncio
import json
import logging
import random
import time
from io import StringIO
from typing import Any

logger = logging.getLogger("miya_psyarch.llm_teacher")


def _build_teaching_prompt(
    skill_name: str,
    skill_desc: str,
    trigger: str,
    demo: str,
    state_items: list[str],
    feelings: dict[str, float],
    emotions: dict[str, float],
    focus: list[str],
    bn_score: float,
    round_num: int,
) -> str:
    """构建给 LLM 教师的教学 prompt"""
    feel_str = ", ".join(f"{k}:{v:.2f}" for k, v in sorted(feelings.items())[:6])
    emo_str = ", ".join(f"{k}:{v:.1f}" for k, v in sorted(emotions.items())[:5])
    state_str = ", ".join(state_items[:6]) if state_items else "空"
    focus_str = ", ".join(focus[:4]) if focus else "空"

    template = _load_teaching_prompt_template()
    return (
        template.replace("{skill_name}", skill_name)
        .replace("{skill_desc}", skill_desc)
        .replace("{trigger}", trigger)
        .replace("{demo}", demo)
        .replace("{round_num}", str(round_num))
        .replace("{feel_str}", feel_str)
        .replace("{emo_str}", emo_str)
        .replace("{state_str}", state_str)
        .replace("{focus_str}", focus_str)
        .replace("{bn_score:.0f}", f"{bn_score:.0f}")
    )


def _load_teaching_prompt_template() -> str:
    try:
        import json
        from pathlib import Path

        config_path = Path(__file__).parent.parent / "config" / "text_config.json"
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = json.load(f)
        return cfg.get("prompt_templates", {}).get("llm_teacher", {}).get("teaching_prompt", "")
    except Exception:
        pass
    return """你是弥娅(AP白箱认知引擎)的教师。你在教她技能: "{skill_name}"——{skill_desc}。


本轮教学:
  用户说了: "{trigger}"
  正确示范: "{demo}"
  当前是第 {round_num} 轮

AP的当前内部状态:
  认知感受: {feel_str}
  情绪: {emo_str}
  状态池Top: {state_str}
  注意焦点: {focus_str}
  Bn回忆分: {bn_score:.0f}

根据AP当前的认知状态, 你应该:
1. 判断AP学会了多少 (观察Bn分和coherence)
2. 决定教学强度 (level: full_demo/strong_hint/light_hint/feedback_only/teacher_off)
3. 给出feedback奖励 (reward: 0.0-1.0)

如果Bn分>300且coherence>0.8: 她已经会了, 给轻反馈
如果Bn分<100: 她需要完整示范
如果Bn分100-300: 给部分提示

只返回JSON, 不要其他文字:
{{"level": "full_demo|strong_hint|light_hint|feedback_only|teacher_off", "reward": 0.0-1.0, "note": "简短说明为什么选这个级别"}}"""


async def _call_llm_teacher(prompt: str, timeout: float = 10.0) -> dict:
    """调用 DeepSeek V4 做教学判断"""
    import sys

    try:
        from core.model_pool_manager import get_model_pool

        pool = get_model_pool()
        client = pool.create_ai_client(task_type="simple_chat")
        if client is None:
            return _fallback_teaching()

        saved = sys.stdout
        sys.stdout = StringIO()
        try:
            response = await asyncio.wait_for(
                client.chat_with_system_prompt(
                    system_prompt="你是AP认知引擎的教师。只返回JSON。",
                    user_message=prompt,
                    tools=None,
                ),
                timeout=timeout,
            )
        finally:
            sys.stdout = saved

        content = ""
        if hasattr(response, "content"):
            content = str(response.content)
        elif isinstance(response, str):
            content = response

        # 提取 JSON
        import re

        match = re.search(r"\{[^{}]*\}", content)
        if match:
            return json.loads(match.group())
        return _fallback_teaching()

    except (asyncio.TimeoutError, Exception) as e:
        logger.debug(f"LLM teacher call failed: {e}")
        return _fallback_teaching()


def _fallback_teaching() -> dict:
    return {"level": "light_hint", "reward": 0.5, "note": "fallback"}


def _level_to_mode(level: str) -> str:
    mapping = {
        "full_demo": "full_demo",
        "strong_hint": "partial_hint",
        "light_hint": "light_hint",
        "feedback_only": "feedback_only",
        "teacher_off": "none",
    }
    return mapping.get(level, "light_hint")


class LLMTeacher:
    """LLM 教师——调用真实 LLM 做教学决策"""

    def __init__(self, engine, skill):
        self._engine = engine
        self._skill = skill
        self._round = 0
        self._history: list[dict] = []

    def teach_one_round(self) -> dict | None:
        """教一轮——观察 AP 状态 → LLM 决策 → 生成教育信号"""
        self._round += 1

        # 1. 随机选一个触发词
        trigger = random.choice(self._skill.triggers)
        demo = random.choice(self._skill.demo_replies)

        # 2. AP 先自己处理
        self._engine.tick(text=trigger)
        s = self._engine.soul_state()
        trace = s.raw_trace or {}

        # 3. 收集 AP 状态
        pool = self._engine._runtime.state_pool
        state_items = [str(k).replace("text::", "").replace("memory::", "") for k in list(pool._entries.keys())[:10]]
        fast_bn = (trace.get("fast_system", {}) or {}).get("bn", []) or []
        bn_score = float(fast_bn[0].get("score", 0) or 0) if fast_bn else 0

        # 4. 构建 prompt 给 LLM
        prompt = _build_teaching_prompt(
            skill_name=self._skill.name,
            skill_desc=self._skill.description,
            trigger=trigger,
            demo=demo,
            state_items=state_items,
            feelings=s.feelings,
            emotions=s.emotion_nt,
            focus=s.focus_texts,
            bn_score=bn_score,
            round_num=self._round,
        )

        # 5. 调用 LLM 教师
        loop = asyncio.get_event_loop()
        decision = loop.run_until_complete(_call_llm_teacher(prompt))

        # 6. 生成教育信号
        mode = _level_to_mode(decision.get("level", "light_hint"))
        reward = decision.get("reward", 0.5)

        edu = _make_education_from_decision(self._skill, trigger, demo, mode=mode, reward=reward)

        # 7. 注入 AP
        if edu:
            self._engine.tick(text=trigger, education_interventions=[edu])

        # 8. 推送到 LLM 教师仪表盘
        level = decision.get("level", "?")
        note = decision.get("note", "")
        from miya_psyarch.llm_teacher_viz import record_llm_decision

        record_llm_decision(level=level, reward=reward, note=note, bn_score=round(bn_score, 1), trigger=trigger)

        # 9. 记录历史
        self._history.append(
            {
                "round": self._round,
                "trigger": trigger,
                "demo": demo,
                "level": decision.get("level", "?"),
                "reward": reward,
                "bn_score": round(bn_score, 1),
                "note": decision.get("note", ""),
            }
        )

        return edu


def _make_education_from_decision(skill, trigger: str, demo: str, *, mode: str, reward: float) -> dict:
    state_items = []
    if mode == "full_demo":
        state_items = [
            {
                "sa_label": f"edu::reply::{trigger[:20]}",
                "display_text": f"示范: {demo[:30]}",
                "family": "education_intervention",
                "real_energy": 0.6,
                "anchor_meta": {"meaning": f"'{trigger}' → '{demo}'"},
            },
        ]
    elif mode == "partial_hint":
        state_items = [
            {
                "sa_label": f"edu::hint::{trigger[:20]}",
                "display_text": f"提示: {demo[:10]}...",
                "family": "education_intervention",
                "real_energy": 0.35,
                "anchor_meta": {"meaning": f"方向: {demo}"},
            },
        ]
    elif mode == "light_hint":
        style = random.choice(skill.expected_style)
        state_items = [
            {
                "sa_label": f"edu::style::{style}",
                "display_text": f"风格: {style}",
                "family": "education_intervention",
                "real_energy": 0.2,
            },
        ]
    elif mode == "feedback_only" or mode == "none":
        pass

    if not state_items and mode == "none":
        return {"schema_id": "education_intervention/v1", "source": "llm_teacher", "state_items": []}

    return {
        "schema_id": "education_intervention/v1",
        "source": "llm_teacher",
        "goal": f"teach_{skill.name}",
        "stage": mode,
        "state_items": state_items,
        "action_biases": [],
        "feedback": {
            "reward": reward,
            "correctness": 0.8,
            "confidence": 0.9,
            "source": "llm_teacher",
        },
    }


def train_with_llm_teacher(skill_name: str = "warm_reply_to_missing", rounds: int = 50, viz: bool = True) -> None:
    """LLM 教师主入口——真实 LLM 观察 AP 并动态教学"""
    from miya_psyarch.engine import MiyaEngine
    from miya_psyarch.trainer import SKILLS
    from miya_psyarch.training_viz import get_dashboard, reset_log, record_stage

    skill = SKILLS.get(skill_name, SKILLS["warm_reply_to_missing"])

    if viz:
        reset_log()
        from miya_psyarch.llm_teacher_viz import get_llm_dashboard, reset_llm

        reset_llm()
        url = get_llm_dashboard().start()
        print(f"  LLM教师仪表盘: {url}")

    engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
    engine.start()
    for _ in range(5):
        engine.idle_tick()

    teacher = LLMTeacher(engine, skill)
    t0 = time.perf_counter()

    print(f"\n◆ LLM教师 (真实DeepSeek) 教学: {skill.description}")
    print(f"  轮次: {rounds}\n")

    for i in range(rounds):
        teacher.teach_one_round()
        last = teacher._history[-1] if teacher._history else {}

        record_stage(
            "llm_teacher",
            {
                "progress": i + 1,
                "bn_score": last.get("bn_score", 0),
                "coherence": 0.8,
                "emotions": engine.soul_state().emotion_nt,
                "feelings": engine.soul_state().miya_feelings,
                "trigger": last.get("trigger", ""),
                "demo": f"{last.get('level', '?')} | {last.get('note', '')}",
            },
        )

        if (i + 1) % 10 == 0:
            levels = [h["level"] for h in teacher._history[-10:]]
            idx_by_level = {
                "full_demo": "F",
                "strong_hint": "S",
                "light_hint": "L",
                "feedback_only": "B",
                "teacher_off": "O",
            }
            level_str = "".join(idx_by_level.get(l, "?") for l in levels)
            print(f"  {i + 1}/{rounds} Bn={last.get('bn_score', 0):.0f} [{level_str}]")

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"\n  LLM教学完成 — {rounds}轮, {elapsed:.0f}ms")

    # 打印教学策略分布
    level_counts = {}
    for h in teacher._history:
        lv = h.get("level", "?")
        level_counts[lv] = level_counts.get(lv, 0) + 1
    print(f"  教学策略分布: {level_counts}")

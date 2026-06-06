"""
弥娅教育协议 — LLM 回复后转换成 AP 教学信号

每轮对话后：
1. 分析 LLM 回复 → 提取教学要素
2. 打包为 education_interventions 包
3. 在下一次 tick 注入 AP 状态池
4. AP 通过 Bn/Cn 逐渐学会「输入→回复」关联
"""

from __future__ import annotations

import logging

logger = logging.getLogger("miya_psyarch.educator")


def package_response_as_education(
    user_message: str,
    miya_response: str,
    emotions: dict[str, float],
    *,
    is_good_reply: bool = True,
) -> list[dict] | dict:
    """
    将 LLM 回复打包为 education_interventions

    Returns 一个包含 state_items 和 feedback 的 education intervention 包
    """
    if not miya_response or len(miya_response) < 2:
        return _empty_intervention()

    interventions = []

    # 1. 创建教学 state items: 将回复的情绪特征注入 AP 状态池
    state_items = _build_state_items(user_message, miya_response, emotions)
    if state_items:
        interventions.append(
            {
                "schema_id": "education_intervention/v1",
                "source": "miya_educator",
                "teacher_kind": "llm_response_teacher",
                "goal": "teach_response_pattern",
                "state_items": state_items,
                "action_biases": [],
                "feedback": {},
                "notes": ["miya_educator_auto_teaching"],
            }
        )

    # 2. 如果有积极的情绪反应，给予正向反馈
    if is_good_reply:
        top_emotion = max(emotions.items(), key=lambda x: x[1]) if emotions else ("neutral", 0)
        if top_emotion[1] > 0.3:
            interventions.append(
                {
                    "schema_id": "education_intervention/v1",
                    "source": "miya_educator",
                    "teacher_kind": "llm_response_teacher",
                    "goal": "reward_positive_conversation",
                    "state_items": [],
                    "action_biases": [],
                    "feedback": {
                        "reward": min(0.8, top_emotion[1]),
                        "correctness": 0.85,
                        "confidence": 0.9,
                        "source": "education::miya_educator",
                        "notes": [f"positive_conversation_{top_emotion[0]}"],
                    },
                    "notes": ["positive_feedback_loop"],
                }
            )

    return interventions


def _build_state_items(
    user_message: str,
    miya_response: str,
    emotions: dict[str, float],
) -> list[dict]:
    """从 LLM 回复构建教学 state items"""
    items = []

    # Item 1: 对话情境 — 用户说了什么 → 弥娅怎么回
    user_preview = user_message[:30]
    items.append(
        {
            "sa_label": f"edu::reply_pattern::{user_preview}",
            "display_text": f"对话模式: {user_preview[:20]}",
            "family": "education_intervention",
            "source_type": "miya_educator",
            "real_energy": 0.30,
            "cognitive_pressure": 0.05,
            "anchor_meta": {
                "schema_id": "education_state_item/v1",
                "meaning": "conversation_pattern",
                "user_input": user_message[:80],
                "miya_response": miya_response[:80],
            },
        }
    )

    # Item 2: 情绪关联 — 在这种情绪下，弥娅说了什么
    top_emotions = sorted(emotions.items(), key=lambda x: -x[1])[:3]
    for name, val in top_emotions:
        if val > 0.3:
            items.append(
                {
                    "sa_label": f"edu::emotion_link::{name}",
                    "display_text": f"情绪关联: {name}({val:.1f})",
                    "family": "education_intervention",
                    "source_type": "miya_educator",
                    "real_energy": min(0.40, val * 0.4),
                    "cognitive_pressure": 0.03,
                    "anchor_meta": {
                        "schema_id": "education_state_item/v1",
                        "meaning": "emotion_response_link",
                        "emotion": name,
                        "intensity": val,
                        "response": miya_response[:60],
                    },
                }
            )

    # Item 3: 回复风格引导
    style_hints = _detect_style(miya_response)
    for hint in style_hints[:2]:
        items.append(
            {
                "sa_label": f"edu::style::{hint}",
                "display_text": f"回复风格: {hint}",
                "family": "education_intervention",
                "source_type": "miya_educator",
                "real_energy": 0.25,
                "cognitive_pressure": 0.04,
                "anchor_meta": {
                    "schema_id": "education_state_item/v1",
                    "meaning": "response_style_reinforcement",
                },
            }
        )

    return items


def _detect_style(response: str) -> list[str]:
    """检测弥娅回复的风格特征"""
    hints = []
    style_words = {
        "温柔": ["嗯", "在呢", "我在这儿", "来吧", "陪你", "靠着"],
        "关切": ["累了吗", "饿不饿", "辛苦了", "没事", "好好休息"],
        "俏皮": ["想得美", "行啊", "说得好", "还不是", "哼"],
        "深沉": ["黄昏", "光", "知道", "属于", "存在"],
        "温暖": ["好的", "当然", "开心", "喜欢", "阳光"],
        "肯定": ["听到了", "知道了", "会的", "没错", "对"],
    }
    for style, words in style_words.items():
        if any(w in response for w in words):
            hints.append(style)
    return hints


def _empty_intervention() -> list[dict]:
    return [
        {
            "schema_id": "education_intervention/v1",
            "source": "miya_educator",
            "teacher_kind": "llm_response_teacher",
            "goal": "empty",
            "state_items": [],
            "action_biases": [],
            "feedback": {},
            "notes": ["empty_intervention"],
        }
    ]

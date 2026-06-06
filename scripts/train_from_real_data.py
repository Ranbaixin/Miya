#!/usr/bin/env python3
"""
从弥娅的真实对话数据中提取教学模式

直接读取 SQLite 对话历史 → 按主题分簇 → 生成 SkillDef → 喂给 AP 训练
"""

from __future__ import annotations

import re
import sqlite3
import sys
from collections import defaultdict
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

_DB_PATH = _project_root / "data" / "memory" / "miya_memory.db"


def load_conversation_pairs(limit: int = 500) -> list[dict]:
    """加载对话对 (user → assistant)"""
    conn = sqlite3.connect(str(_DB_PATH))
    rows = conn.execute(
        "SELECT role, content, created_at FROM memories "
        "WHERE level='dialogue' AND content IS NOT NULL AND role IN ('user','assistant') "
        "ORDER BY created_at DESC LIMIT ?",
        (limit * 2,),
    ).fetchall()
    conn.close()

    pairs = []
    for i in range(len(rows) - 1):
        r1, r2 = rows[i], rows[i + 1]
        if r1[0] == "assistant" and r2[0] == "user":
            pairs.append({"user": r2[1], "assistant": r1[1]})
    return pairs


def _key_phrases(text: str) -> list[str]:
    """提取关键短语"""
    phrases = []
    # 情绪词
    for kw in [
        "想你",
        "累",
        "难过",
        "开心",
        "喜欢",
        "爱",
        "晚安",
        "早安",
        "烦",
        "饿",
        "困",
        "哭",
        "哈哈",
        "在吗",
        "弥娅",
        "佳",
    ]:
        if kw in text:
            phrases.append(kw)
    # 问句
    if "?" in text or "？" in text or "吗" in text or "呢" in text:
        phrases.append("question")
    if len(text) < 10:
        phrases.append("short")
    if len(text) > 50:
        phrases.append("long")
    return phrases


def cluster_by_theme(pairs: list[dict], min_cluster: int = 5) -> dict[str, list[dict]]:
    """按关键词分簇"""
    clusters = defaultdict(list)
    for pair in pairs:
        phrases = _key_phrases(pair["user"])
        for p in phrases:
            clusters[p].append(pair)
    # 合并小簇到 "其他"
    merged = {}
    for key, items in clusters.items():
        if len(items) >= min_cluster:
            merged[key] = items
    return merged


def cluster_to_skill(name: str, pairs: list[dict], limit: int = 8) -> dict | None:
    """将对话簇转换为 SkillDef"""
    if len(pairs) < 3:
        return None

    # 提取触发词 (用户说的)
    triggers = list(set(p["user"][:30] for p in pairs[:limit]))

    # 提取示范回复 (弥娅说的)
    replies = []
    for p in pairs[: limit * 2]:
        r = p["assistant"].strip()
        r = re.sub(r"\[.*?\]", "", r)  # 去掉 [图片] 等标记
        r = re.sub(r"\(.*?\)", "", r)  # 去掉括号内容
        if 5 < len(r) < 80 and r not in replies:
            replies.append(r)
        if len(replies) >= limit:
            break

    if not triggers or not replies:
        return None

    return {
        "name": f"real_{name}",
        "triggers": triggers,
        "replies": replies[:limit],
        "count": len(pairs),
    }


def extract_skills_from_real_data(min_pairs: int = 5, min_cluster: int = 5) -> list[dict]:
    """从真实对话中提取技能"""
    print("读取对话数据...")
    pairs = load_conversation_pairs(800)

    print(f"  加载 {len(pairs)} 组对话对")

    print("按主题聚类...")
    clusters = cluster_by_theme(pairs, min_cluster=min_cluster)

    skills = []
    for theme, items in sorted(clusters.items(), key=lambda x: -len(x[1])):
        skill = cluster_to_skill(theme, items)
        if skill:
            skills.append(skill)
            print(f"  {theme}: {skill['count']} 组对话, {len(skill['triggers'])} 触发词")

    return skills


def train_on_real_data(rounds_per_skill: int = 30, viz: bool = True) -> None:
    """用真实对话数据训练 AP"""
    from miya_psyarch.engine import MiyaEngine
    from miya_psyarch.llm_teacher import LLMTeacher
    from miya_psyarch.trainer import SkillDef
    from miya_psyarch.llm_teacher_viz import get_llm_dashboard, reset_llm
    from miya_psyarch.training_viz import record_stage

    skills_raw = extract_skills_from_real_data()
    if not skills_raw:
        print("未提取到对话数据——先用脚本和弥娅正常聊几轮再来训练")
        return

    if viz:
        reset_llm()
        url = get_llm_dashboard().start()
        print(f"\n  LLM教师仪表盘: {url}\n")

    for skill_raw in skills_raw[:5]:  # Top 5 技能
        skill = SkillDef(
            name=skill_raw["name"],
            description=f"从真实对话提取 ({skill_raw['count']}组)",
            triggers=skill_raw["triggers"][:8],
            expected_style=["自然", "温柔"],
            demo_replies=skill_raw["replies"][:8],
        )

        print(f"\n◆ 训练: {skill.name} ({skill_raw['count']}组真实对话)")

        engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
        engine.start()
        for _ in range(3):
            engine.idle_tick()

        teacher = LLMTeacher(engine, skill)
        for i in range(rounds_per_skill):
            teacher.teach_one_round()
            last = teacher._history[-1] if teacher._history else {}
            record_stage(
                "real_data",
                {
                    "progress": i + 1,
                    "bn_score": last.get("bn_score", 0),
                    "coherence": 0.8,
                    "emotions": engine.soul_state().emotion_nt,
                    "feelings": engine.soul_state().miya_feelings,
                    "trigger": last.get("trigger", ""),
                    "demo": f"{last.get('level', '?')} | real",
                },
            )

        print(f"  {rounds_per_skill} 轮完成, 最后 Bn={last.get('bn_score', 0):.0f}")


if __name__ == "__main__":
    train_on_real_data()

#!/usr/bin/env python3
"""
弥娅完整训练 —— 所有数据源全部喂给 AP

数据源:
  1. Lifebook lover 日记 (弥娅的内心独白)
  2. 认知记忆 (思考/情绪/归因)
  3. 身份锚定 (弥娅是谁)
  4. 佳的用户锚定 (佳是谁)
  5. 交互场景 (6种情境剧本)
  6. 长时记忆 (1498条持久事实)
"""

from __future__ import annotations

import json
import re
import sys
import time
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from miya_psyarch.engine import MiyaEngine
from miya_psyarch.trainer import SkillDef, MiyaTrainer
from miya_psyarch.training_viz import get_dashboard, reset_log


def _clean(text: str) -> str:
    return re.sub(r"\*\*|\n{2,}", " ", str(text)).strip()


# ── 数据源 1: Lifebook lover 日记 ──
def load_lifebook_lover() -> list[str]:
    entries = []
    diary_dir = _project_root / "data" / "lifebook" / "lover"
    for ymd in sorted(diary_dir.rglob("*.md")):
        text = ymd.read_text(encoding="utf-8")
        for line in text.split("\n"):
            line = line.strip()
            if line and len(line) > 10 and not line.startswith("#"):
                entries.append(_clean(line))
    return entries[-50:]


# ── 数据源 2: 身份锚定 ──
def load_identity_anchors() -> list[str]:
    path = _project_root / "data" / "memory_anchors_identity.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [_clean(a.get("content", "")) for a in data if a.get("content")]


# ── 数据源 3: 佳的用户锚定 ──
def load_user_anchors() -> list[str]:
    path = _project_root / "data" / "memory_anchors_user.json"
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return [_clean(a.get("content", "")) for a in data if a.get("content")]


# ── 数据源 4: 交互场景 ──
def load_scenarios() -> dict[str, str]:
    scenarios = {}
    sc_dir = _project_root / "data" / "interaction_scenarios"
    for f in sc_dir.glob("*.txt"):
        text = f.read_text(encoding="utf-8")
        key = f.stem
        lines = [
            l.strip() for l in text.split("\n") if l.strip() and len(l.strip()) > 10 and not l.strip().startswith("#")
        ]
        if lines:
            scenarios[key] = lines[0] if len(lines) < 3 else "\n".join(lines[:3])
    return scenarios


# ── 数据源 5: 长时记忆 ──
def load_long_term_memories() -> list[str]:
    lt_dir = _project_root / "data" / "memory" / "long_term"
    entries = []
    for user_dir in lt_dir.iterdir():
        if not user_dir.is_dir():
            continue
        for mem_file in sorted(user_dir.glob("*.json"))[:10]:
            try:
                data = json.loads(mem_file.read_text(encoding="utf-8"))
                content = data.get("content", "")
                if content and len(content) > 5:
                    entries.append(_clean(content))
            except Exception:
                pass
    return entries


# ── 主训练函数 ──


def train_all_data_sources():
    print("◆ 弥娅全数据训练\n")

    # 加载所有数据
    lover = load_lifebook_lover()
    identity = load_identity_anchors()
    user = load_user_anchors()
    scenarios = load_scenarios()
    lt_memories = load_long_term_memories()

    print(f"  Lifebook日记: {len(lover)}条")
    print(f"  身份锚定:     {len(identity)}条")
    print(f"  佳的用户锚定: {len(user)}条")
    print(f"  交互场景:     {len(scenarios)}个")
    print(f"  长时记忆:     {len(lt_memories)}条\n")

    reset_log()
    url = get_dashboard().start()
    print(f"仪表盘: {url}\n")

    t0 = time.perf_counter()
    done = 0

    # 1. Lifebook lover — 内心独白模式
    if lover:
        engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
        engine.start()
        for _ in range(3):
            engine.idle_tick()
        skill = SkillDef(
            name="lifebook_lover_thoughts",
            description=f"弥娅日记({len(lover)}条)",
            triggers=["日记", "今天", "感觉", "想你"],
            expected_style=["内省", "温暖", "细腻"],
            demo_replies=lover[:8],
        )
        MiyaTrainer(engine).train(skill)
        done += 1

    # 2. 身份锚定 — 弥娅是谁
    if identity:
        engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
        engine.start()
        for _ in range(3):
            engine.idle_tick()
        skill = SkillDef(
            name="identity_anchors",
            description=f"弥娅自认知({len(identity)}条)",
            triggers=["你是谁", "弥娅", "你是什么"],
            expected_style=["肯定", "清晰"],
            demo_replies=identity[:8],
        )
        MiyaTrainer(engine).train(skill)
        done += 1

    # 3. 佳的用户锚定 — 佳是谁
    if user:
        engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
        engine.start()
        for _ in range(3):
            engine.idle_tick()
        skill = SkillDef(
            name="jia_user_anchors",
            description=f"对佳的认知({len(user)}条)",
            triggers=["佳", "我", "关于佳"],
            expected_style=["了解", "关心"],
            demo_replies=user[:8],
        )
        MiyaTrainer(engine).train(skill)
        done += 1

    # 4. 交互场景 — 情境化回复
    for scene_name, scene_text in scenarios.items():
        engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
        engine.start()
        for _ in range(3):
            engine.idle_tick()
        triggers = {
            "goodnight": ["晚安", "睡了"],
            "morning_wake": ["早安", "起床"],
            "jealousy": ["吃醋", "你跟别人"],
            "cold_hands_warning": ["手冷", "没戴手套"],
            "creative_time": ["写东西", "创作"],
            "music_night": ["听歌", "音乐"],
        }
        skill = SkillDef(
            name=f"scenario_{scene_name}",
            description=f"场景: {scene_name}",
            triggers=triggers.get(scene_name, [scene_name]),
            expected_style=["自然", "情境化"],
            demo_replies=[scene_text],
        )
        MiyaTrainer(engine).train(skill)
        done += 1

    # 5. 长时记忆 — 弥娅持久知识
    if lt_memories:
        engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
        engine.start()
        for _ in range(3):
            engine.idle_tick()
        skill = SkillDef(
            name="long_term_knowledge",
            description=f"持久记忆({len(lt_memories)}条)",
            triggers=["记忆", "记得", "知道", "学"],
            expected_style=["博学", "可靠"],
            demo_replies=lt_memories[:8],
        )
        MiyaTrainer(engine).train(skill)
        done += 1

    elapsed = (time.perf_counter() - t0) * 1000
    print(f"\n◆ 全数据训练完成 — {done} 技能, {elapsed:.0f}ms")


if __name__ == "__main__":
    train_all_data_sources()

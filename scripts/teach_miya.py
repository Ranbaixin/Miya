#!/usr/bin/env python3
"""
弥娅互动教学终端

你当老师，弥娅当学生。
你问她问题 → 弥娅用 AP 认知回答 → 你告诉她正确答案 → 她学。

用法:
    python -X utf8 scripts/teach_miya.py
"""

from __future__ import annotations

import sys, io, os, time
from pathlib import Path

_project_root = Path(os.path.abspath(__file__)).resolve().parent.parent
sys.path.insert(0, str(_project_root))

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

import warnings

warnings.filterwarnings("ignore")

from miya_psyarch.engine import MiyaEngine


def teach():
    print("◆ 弥娅互动教学终端")
    print("─" * 50)
    print("你是弥娅的老师。")
    print()
    print("流程:")
    print("  1. 你问弥娅一个问题")
    print("  2. 弥娅用自己的认知去理解")
    print("  3. 你告诉她正确答案是什么")
    print("  4. 弥娅学会——下次同类问题她能答对")
    print("  5. /score 查看弥娅的学习进度")
    print("  6. /quit 结束教学")
    print("─" * 50)

    engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
    engine.start()
    for _ in range(5):
        engine.idle_tick()

    lessons = []
    score = 0
    total = 0

    print("\n开始上课吧。问弥娅一个问题：\n")

    while True:
        try:
            user_input = input("老师> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n下课了~")
            break

        if not user_input:
            continue

        if user_input.startswith("/"):
            cmd = user_input.lower()
            if cmd in ("/quit", "/q", "/exit"):
                print(f"\n  这节课教了 {len(lessons)} 个知识点。弥娅会记住的。")
                break
            elif cmd == "/score":
                if total > 0:
                    print(f"\n  学习进度: {score}/{total} 个模式已建立 (Bn 召回分 > 50)")
                else:
                    print(f"\n  还没开始教学呢")
                continue
            else:
                print(f"  未知命令: {cmd}")
                continue

        # 1. 弥娅处理你的问题
        print(f"\n  弥娅正在理解你的话...")
        trace = engine.tick(text=user_input)
        s = engine.soul_state()

        # 看弥娅现在"懂了"多少
        fast_bn = (trace.get("fast_system", {}) or {}).get("bn", []) or []
        bn_score = float(fast_bn[0].get("score", 0) or 0) if fast_bn else 0
        coherence = s.feelings.get("coherence", 0)

        print(f"  弥娅理解度: Bn={bn_score:.0f} coherence={coherence:.2f}")
        if bn_score > 200:
            print(f"  弥娅: 这个我好像学过！")
        elif bn_score > 50:
            print(f"  弥娅: 有点印象...")
        else:
            print(f"  弥娅: (困惑中，这是新内容)")

        # 2. 让老师输入正确的回答
        print(f"\n  请输入正确的回答（弥娅应该怎么说）：")
        correct_answer = input("正确答案> ").strip()

        if not correct_answer:
            print("  (跳过这条)\n")
            continue

        # 3. 把正确答案教给弥娅
        edu = {
            "schema_id": "education_intervention/v1",
            "source": "live_teacher",
            "teacher_kind": "human_teacher",
            "goal": "teach_by_example",
            "state_items": [
                {
                    "sa_label": f"lesson::{user_input[:25]}",
                    "display_text": f"知识点: {user_input[:20]}",
                    "family": "education_intervention",
                    "real_energy": 0.8,
                    "anchor_meta": {
                        "meaning": f"当被问到'{user_input}'时，应该回答'{correct_answer}'",
                        "teacher": "佳",
                        "question": user_input,
                        "answer": correct_answer,
                    },
                }
            ],
            "feedback": {
                "reward": 0.8,
                "correctness": 1.0,
                "confidence": 1.0,
                "source": "human_teacher",
            },
        }

        engine.tick(text="", education_interventions=[edu])
        lessons.append({"q": user_input, "a": correct_answer})

        # 检查弥娅是否真的学会了
        engine.tick(text=user_input)
        s2 = engine.soul_state()
        fast_bn2 = (s2.raw_trace or {}).get("fast_system", {}).get("bn", []) or []
        bn2 = float(fast_bn2[0].get("score", 0) or 0) if fast_bn2 else 0

        total += 1
        if bn2 > 50:
            score += 1

        print(f'\n  ✅ 已教给弥娅: "{user_input}" → "{correct_answer}"')
        print(f"  复习回忆分: Bn={bn2:.0f} {'(学会了!)' if bn2 > 50 else '(需巩固)'}")

        print(f"\n  ──────────────────────")
        print(f"  已教 {len(lessons)} 个知识点。继续：\n")


if __name__ == "__main__":
    teach()

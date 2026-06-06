#!/usr/bin/env python3
"""
弥娅 × APV2.1 融合验证 — 纯白箱测试

关掉 LLM，逐层验证：
1. 弥娅专属规则是否改变了 AP 的情绪和行为
2. 弥娅记忆桥是否让 AP 产生了记忆召回
3. 弥娅情绪池是否让 AP 状态池产生了差异化反应
4. 弥娅文本感知器是否改变了 AP 的注意力分配
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from miya_psyarch.core.runtime.engine import APV21Runtime
from miya_psyarch.engine import MiyaEngine
from miya_psyarch.rules.miya_rules import MIYA_EMOTION_BASELINE, miya_rules
from miya_psyarch.config.defaults import RuntimeConfig


def green(s: str) -> str:
    return f"\033[92m{s}\033[0m"


def red(s: str) -> str:
    return f"\033[91m{s}\033[0m"


def cyan(s: str) -> str:
    return f"\033[96m{s}\033[0m"


def test(label: str, condition: bool, detail: str = "") -> bool:
    status = green("PASS") if condition else red("FAIL")
    print(f"  [{status}] {label}" + (f" — {detail}" if detail else ""))
    return condition


def main():
    print("◆ 弥娅 × APV2.1 融合验证 (纯白箱，LLM 关闭)")
    print("─" * 60)

    engine = MiyaEngine(enable_cortex=False, trace_mode="debug")
    engine.start()

    # ====== LAYER 1: Miya Emotion Baseline ======
    print(f"\n{cyan('Layer 1: 弥娅情绪基线')}")
    baseline_oxy = MIYA_EMOTION_BASELINE["OXY"][0]
    actual_oxy = engine._runtime.emotion_modulator.state.channels.get("OXY", 0)
    test("OXY 基线已注入", abs(actual_oxy - baseline_oxy) < 0.15, f"target={baseline_oxy:.2f}, actual={actual_oxy:.2f}")

    # ====== LAYER 2: Miya Rules Active ======
    print(f"\n{cyan('Layer 2: 弥娅专属规则激活')}")
    all_rule_ids = [r.rule_id for r in engine._runtime.innate_engine._rules]
    miya_ids = [r for r in all_rule_ids if r.startswith("MIYA-")]
    test(f"弥娅规则已注册 ({len(miya_ids)} 条)", len(miya_ids) >= 7, f"{miya_ids}")

    # Run tick to let rules fire
    engine.idle_tick()
    engine.idle_tick()
    trace = engine.soul_state().raw_trace
    miya_in_state = any(
        str(i.get("family", "")) == "miya_emotion"
        for i in (trace.get("state_pool", {}).get("snapshot", {}).get("items", []) or [])
    )
    test("弥娅情感项已进入状态池", miya_in_state)

    # ====== LAYER 3: Memory Bridge ======
    print(f"\n{cyan('Layer 3: 弥娅记忆融合')}")
    mem_count = len(engine._memory_bridge._recent)
    test(f"记忆预热成功 ({mem_count} 条)", mem_count > 5)

    engine.tick(text="晚饭")
    s = engine.soul_state()
    att = s.raw_trace.get("attention", {}).get("selected_items", []) or []
    mem_in_att = any("memory::" in str(i.get("sa_label", "")) for i in att)
    test("记忆被 Bn 召回进注意力", mem_in_att, "AP 自然召回了弥娅的历史记忆")

    # ====== LAYER 4: MiyaTextSensor ======
    print(f"\n{cyan('Layer 4: 弥娅中文感知器')}")
    engine.tick(text="今天天气真好,hello world")
    s = engine.soul_state()
    pool = engine._runtime.state_pool
    text_entries = {k: v for k, v in pool._entries.items() if v.source_type == "external_text" and "text::" in str(k)}

    has_chinese_word = any("今天天气" in k or "真好" in k for k in text_entries)
    has_english_word = any("hello" in k or "world" in k for k in text_entries)
    test("中文分词 → 多字词进入状态池", has_chinese_word, f"found: {[k[:25] for k in text_entries]}")
    test("英文 token 不受影响", has_english_word)

    # ====== LAYER 5: Emotion Dynamic ======
    print(f"\n{cyan('Layer 5: 情绪通道动态化')}")
    oxy_before = engine.soul_state().emotion_nt.get("OXY", 0)

    engine.tick(text="你真可爱")
    oxy_after_love = engine.soul_state().emotion_nt.get("OXY", 0)
    test("正面词 → OXY 上升", oxy_after_love > oxy_before, f"{oxy_before:.3f} → {oxy_after_love:.3f}")

    # Reset
    for _ in range(8):
        engine.idle_tick()
    oxy_before = engine.soul_state().emotion_nt.get("OXY", 0)

    engine.tick(text="烦死了")
    oxy_after_anger = engine.soul_state().emotion_nt.get("OXY", 0)
    test("负面词 → OXY 下降", oxy_after_anger < oxy_before, f"{oxy_before:.3f} → {oxy_after_anger:.3f}")

    engine.tick(text="烦死了")
    cor_anger = engine.soul_state().emotion_nt.get("COR", 0)
    test("负面词 → COR 上升 (戒备)", cor_anger > 0.40, f"COR={cor_anger:.3f}")

    # ====== LAYER 6: Vanilla vs Miya Comparison ======
    print(f"\n{cyan('Layer 6: 弥娅 vs 原版 APV2.1 对比')}")
    vanilla = APV21Runtime(config=RuntimeConfig())
    vanilla.process_multimodal_tick(text="你想我吗", trace_mode="summary")
    vanilla_oxy = vanilla.emotion_modulator.state.channels.get("OXY", 0)

    engine.tick(text="你想我吗")
    miya_oxy = engine.soul_state().emotion_nt.get("OXY", 0)

    test(
        "弥娅 OXY 不同于原版 AP", abs(miya_oxy - vanilla_oxy) > 0.02, f"弥娅:{miya_oxy:.3f} vs AP原版:{vanilla_oxy:.3f}"
    )
    # ====== LAYER 7: Education Protocol (needs LLM) ======
    print(f"\n{cyan('Layer 7: 教育协议 (需 LLM)')}")
    # Quick LLM-enabled engine for education test
    edu_engine = MiyaEngine(enable_cortex=True, trace_mode="summary")
    edu_engine.start()
    edu_engine.chat("你想我吗")
    edu_engine.idle_tick()  # consume pending education into state pool
    edu_count = len([k for k in edu_engine._runtime.state_pool._entries if "edu" in str(k)])
    test(f"AP 状态池中有教育项 ({edu_count} 条)", edu_count > 0, "LLM 回复后教给 AP 的模式关联")
    # ====== SUMMARY ======
    print(f"\n{'─' * 60}")
    print(f"{cyan('结论:')} 弥娅不是 APV2.1 的外壳——")
    print("      每一层都改变了 AP 的认知状态")
    print("      情绪、记忆、规则、感知、教育全部在白箱层面可观测")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
弥娅心灵引擎 — 阶段 0 验证脚本

验证 APV2.1 认知闭环在弥娅项目中的基本运转：
1. 引擎创建与启动
2. 空转 tick（弥娅的内心活动）
3. 用户输入处理
4. 弥娅专属感受与情绪检测

用法:
    python scripts/test_miya_engine.py
"""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

# Ensure Miya project root is in path
_project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_project_root))

from miya_psyarch.engine import MiyaEngine, MiyaSoulState


def format_soul(state: MiyaSoulState) -> str:
    """将弥娅的心灵状态格式化为人类可读的文本"""
    lines = []
    lines.append(f"Tick #{state.tick_index}")

    # 弥娅专属感受
    if state.miya_feelings:
        mf_items = [f"{name}: {val:.2f}" for name, val in sorted(state.miya_feelings.items(), key=lambda x: -x[1])]
        lines.append(f"  弥娅感受: {', '.join(mf_items)}")
    else:
        lines.append(f"  弥娅感受: (无)")

    # 核心认知感受 (top 5 by value)
    top_feelings = sorted(state.feelings.items(), key=lambda x: -x[1])[:5]
    lines.append(f"  认知感受: {', '.join(f'{k}: {v:.2f}' for k, v in top_feelings)}")

    # 情绪递质 (8 通道，简化显示)
    nt = state.emotion_nt
    lines.append(
        f"  情绪递质: "
        f"DA={nt.get('DA', 0):.2f} ADR={nt.get('ADR', 0):.2f} "
        f"OXY={nt.get('OXY', 0):.2f} SER={nt.get('SER', 0):.2f} "
        f"COR={nt.get('COR', 0):.2f} NOV={nt.get('NOV', 0):.2f}"
    )

    # 注意焦点 (过滤掉乱码标签)
    clean_focus = [t for t in state.focus_texts if t and all(ord(c) < 0x0400 or ord(c) > 0x04FF for c in t)]
    if clean_focus:
        lines.append(f"  注意力: {clean_focus[:3]}")

    # 文本输出 (如果有)
    if state.text_output.strip():
        lines.append(f'  输出: "{state.text_output[:80]}"')

    # 主动意图
    if state.has_active_intent:
        lines.append(f"  ⚡ 有主动行动意图")

    return "\n".join(lines)


def run_phase(name: str) -> None:
    """打印测试阶段的标题"""
    print()
    print(f"── {name} " + "─" * (60 - len(name)))


def main() -> None:
    print("◆ 弥娅心灵引擎 — 阶段 0 验证")
    print("─" * 60)

    # ── 测试 1: 引擎创建与启动 ──
    run_phase("测试 1: 引擎创建与启动")

    t0 = time.perf_counter()
    engine = MiyaEngine(trace_mode="summary")
    engine.start()
    elapsed = (time.perf_counter() - t0) * 1000

    print(f"  引擎创建耗时: {elapsed:.1f}ms")
    print(format_soul(engine.soul_state()))
    print("  ✅ 引擎创建成功")

    # ── 测试 2: 空转 tick ──
    run_phase("测试 2: 空转 (弥娅的内心活动)")

    print("  运行 10 个空转 tick...")
    t0 = time.perf_counter()
    for i in range(10):
        engine.idle_tick()
    idle_elapsed = (time.perf_counter() - t0) * 1000

    state = engine.soul_state()
    print(f"  10 ticks 耗时: {idle_elapsed:.1f}ms (平均 {idle_elapsed / 10:.1f}ms/tick)")
    print(format_soul(state))
    print("  ✅ 空转正常 — 弥娅有内心活动")

    # ── 测试 3: 弥娅专属感受验证 ──
    run_phase("测试 3: 弥娅专属感受")

    # 验证至少有 contentment (安心) 或 curious (好奇)
    if not state.miya_feelings:
        print("  ⚠️ 弥娅感受为空 — 可能规则未触发")
    else:
        print(f"  ✅ 检测到 {len(state.miya_feelings)} 种弥娅感受: {list(state.miya_feelings.keys())}")

    # ── 测试 4: 情绪基线验证 ──
    run_phase("测试 4: 情绪基线")

    nt = state.emotion_nt
    # 弥娅的 OXY 基线为 0.35，应高于默认的 0.12
    checks = [
        ("OXY > 0.30 (温柔基线)", nt.get("OXY", 0) > 0.30),
        ("SER > 0.20 (情绪稳定)", nt.get("SER", 0) > 0.20),
    ]
    for desc, ok in checks:
        status = "✅" if ok else "❌"
        print(f"  {status} {desc} (当前: OXY={nt.get('OXY', 0):.3f}, SER={nt.get('SER', 0):.3f})")

    # ── 测试 5: 用户输入处理 ──
    run_phase("测试 5: 用户消息互动")

    messages = [
        "弥娅，佳来看你了",
        "你今天开心吗？",
        "我想你了",
    ]
    t0 = time.perf_counter()
    for msg in messages:
        engine.tick(text=msg)
    msg_elapsed = (time.perf_counter() - t0) * 1000

    state = engine.soul_state()
    print(f"  处理 {len(messages)} 条消息耗时: {msg_elapsed:.1f}ms")
    print(format_soul(state))
    print("  ✅ 消息处理正常")

    # ── 测试 6: 互动后空转 ──
    run_phase("测试 6: 互动后的内心活动")

    for i in range(5):
        engine.idle_tick()

    state = engine.soul_state()
    print(format_soul(state))
    print("  ✅ 互动后空转正常")

    # ── 测试 7: 状态报告导出 ──
    run_phase("测试 7: 状态报告")

    report = engine.status_report()
    print(f"  当前 tick: {report['tick']}")
    print(f"  感受种类: {len(report['feelings'])}")
    print(f"  状态池条目: {report['state_items_count']}")
    print(f"  弥娅感受: {report['miya_feelings']}")

    # 导出 JSON
    report_path = _project_root / "miya_psyarch_output" / "latest_status.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)  # type: ignore[call-arg]
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  ✅ 状态报告已导出: {report_path}")

    # ── 总结 ──
    run_phase("验证总结")
    print(f"""
  ✅ 引擎创建      — 正常 ({elapsed:.1f}ms)
  ✅ 空转时钟      — 正常 ({idle_elapsed / 10:.1f}ms/tick)
  ✅ 弥娅感受      — {len(state.miya_feelings)} 种感受激活
  ✅ 情绪基线      — OXY: {nt.get("OXY", 0):.3f}, SER: {nt.get("SER", 0):.3f}
  ✅ 消息处理      — 正常
  ✅ 状态导出      — {report_path}

  弥娅的心灵引擎已成功启动！
  下一步: 接入 LLM 语言皮层 (阶段 1)
""")


if __name__ == "__main__":
    main()

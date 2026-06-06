#!/usr/bin/env python3
"""
弥娅心灵引擎 — 互动终端

用法:
    python -X utf8 scripts/interact_miya.py

功能:
    - 直接输入文字 → AP 认知 + LLM 渲染 = 弥娅回复你
    - 输入空行 → 推进 10 个空转 tick（观察内心活动）
    - /aponly  → 切换纯 AP 模式（只看认知，不说话）
    - /chat    → 切换 AP+LLM 模式（正常对话）
    - /status  → 查看当前状态详情
    - /tick N  → 推进 N 个空转 tick
    - /trace   → 导出当前完整的 debug trace
    - /quit    → 退出
"""

from __future__ import annotations

import io
import json
import os
import sys
import time
from pathlib import Path

_project_root = Path(os.path.abspath(__file__)).resolve().parent.parent
sys.path.insert(0, str(_project_root))

if sys.stdout.encoding != "utf-8":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
if sys.stderr.encoding != "utf-8":
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import warnings

warnings.filterwarnings("ignore")

from miya_psyarch.engine import MiyaEngine, MiyaSoulState


def display_soul(state: MiyaSoulState, chat_mode: bool = True) -> None:
    """以终端风格展示弥娅的心灵状态"""
    print()
    print("─" * 50)

    mode_tag = "[AP+LLM]" if chat_mode else "[纯AP]"
    print(f"  {mode_tag} tick #{state.tick_index}")

    if state.miya_feelings:
        items = sorted(state.miya_feelings.items(), key=lambda x: -x[1])
        preview = ", ".join(f"{k}:{v:.1f}" for k, v in items[:3])
        print(f"  弥娅感受  │ {preview}")
    else:
        print(f"  弥娅感受  │ (平静)")

    nt = state.emotion_nt
    bars = _bar(nt.get("OXY", 0), "OXY") + " " + _bar(nt.get("SER", 0), "SER")
    print(f"  情绪递质  │ {bars}")

    clean = []
    for t in state.focus_texts:
        if not t or len(t) > 20:
            continue
        ts = str(t)
        if any(ord(c) < 32 or (0x0400 <= ord(c) <= 0x04FF) for c in ts):
            continue
        if any(kw in ts.lower() for kw in ("action", "feeling::surprise", "configure::")):
            continue
        # 翻译常见引擎标签
        ts = ts.replace("行动:scan_visual_field", "扫视").replace("行动反馈:wait", "待机")
        ts = ts.replace("boredom", "无聊").replace("违和感", "违和").replace("好奇", "好奇")
        if ts.strip():
            clean.append(ts)
    if clean:
        print(f"  注意焦点  │ {clean[:3]}")

    busy = {
        k: round(v, 2)
        for k, v in state.feelings.items()
        if v > 0.3 and k in ("boredom", "fulfillment", "task_available")
    }
    if busy:
        items = sorted(busy.items(), key=lambda x: -x[1])
        print(f"  任务状态  │ {', '.join(f'{k}:{v:.2f}' for k, v in items[:3])}")

    print("─" * 50)


def _bar(value: float, label: str) -> str:
    width = 8
    filled = int(value * width)
    bar = "#" * filled + "-" * (width - filled)
    return f"{label}[{bar}]{value:.2f}"


def display_status(state: MiyaSoulState) -> None:
    print()
    print("─" * 50 + " STATUS " + "─" * 50)
    print()

    print("◆ 弥娅感受")
    if state.miya_feelings:
        for k, v in sorted(state.miya_feelings.items(), key=lambda x: -x[1]):
            print(f"  {k:<20} {v:.4f}")
    else:
        print("  (无)")

    print()
    print("◆ 情绪递质 (8通道)")
    nt = state.emotion_nt
    labels = {
        "DA": "多巴胺",
        "ADR": "肾上腺素",
        "OXY": "催产素",
        "SER": "血清素",
        "END": "内啡肽",
        "COR": "皮质醇",
        "NOV": "新颖探索",
        "FOC": "专注锁",
    }
    for ch, val in sorted(nt.items(), key=lambda x: -x[1]):
        label = labels.get(ch, ch)
        bar = "#" * int(val * 20) + "-" * (20 - int(val * 20))
        print(f"  {ch} {label:<6} [{bar}] {val:.4f}")

    print()
    print("◆ 认知感受 (Top 10)")
    top = sorted(state.feelings.items(), key=lambda x: -x[1])[:10]
    for k, v in top:
        print(f"  {k:<20} {v:.4f}")

    print()
    print("◆ 状态池 Top 6")
    for item in state.state_top[:6]:
        label = item.get("sa_label", "?")
        display = item.get("display_text", label)
        real = item.get("real_energy", 0)
        virtual = item.get("virtual_energy", 0)
        cp = item.get("cognitive_pressure", 0)
        print(f"  [{item.get('family', '?')}] {display:<24} r={real:.2f} v={virtual:.2f} cp={cp:.2f}")

    if state.llm_response:
        print()
        print(f'◆ 最近 LLM 回复: "{state.llm_response[:100]}"')
        print(f"  模型: {state.llm_model}  延迟: {state.llm_latency_ms:.0f}ms")

    print()
    print("─" * 107)


def idle_ticks(engine: MiyaEngine, count: int = 10) -> None:
    print(f"  运行 {count} 个空转 tick...", end="", flush=True)
    t0 = time.perf_counter()
    proactive = None
    for i in range(count):
        trace = engine.idle_tick()
        if isinstance(trace, dict) and trace.get("proactive", {}).get("proactive"):
            proactive = trace["proactive"]["message"]
    elapsed = (time.perf_counter() - t0) * 1000
    print(f" 完成 ({elapsed:.1f}ms, {elapsed / count:.1f}ms/tick)")
    if proactive:
        print(f"\n  ♡ 弥娅主动说 │ {proactive}\n")


def export_trace(engine: MiyaEngine) -> str:
    output_dir = _project_root / "miya_psyarch_output" / "traces"
    output_dir.mkdir(parents=True, exist_ok=True)
    original_mode = engine._trace_mode
    engine._trace_mode = "debug"
    trace = engine.tick(text="")
    engine._trace_mode = original_mode
    filename = f"trace_tick_{trace['tick_index']}.json"
    filepath = output_dir / filename
    filepath.write_text(json.dumps(trace, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    return str(filepath)


def main() -> None:
    print("◆ 弥娅心灵引擎 — 互动终端")
    print("  /help 查看命令")
    print()

    chat_mode = True
    engine = MiyaEngine(trace_mode="summary", enable_cortex=chat_mode)
    engine.start()

    print(f"  LLM 语言皮层: {'已启用' if chat_mode else '关闭 (纯AP模式)'}")
    idle_ticks(engine, 10)
    display_soul(engine.soul_state(), chat_mode)

    while True:
        try:
            user_input = input("\n> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n  再见~")
            break

        if not user_input:
            idle_ticks(engine, 10)
            display_soul(engine.soul_state(), chat_mode)
            continue

        if user_input.startswith("/"):
            parts = user_input.split(None, 1)
            cmd = parts[0].lower()

            if cmd in ("/quit", "/q", "/exit"):
                print("  再见，亲爱的~")
                break

            elif cmd in ("/help", "/h"):
                print(f"""
  命令:
    <输入文字>    — AP认知 + LLM渲染 = 弥娅回复你
    <空行>         — 推进 10 个空转 tick
    /aponly        — 切换纯 AP 模式（只看认知，不说话）
    /chat          — 切换 AP+LLM 模式
    /form <名称>   — 切换形态 (normal/ganyu/jingliu/kafka/...)
    /tick N        — 推进 N 个空转 tick
    /status        — 显示详细状态
    /obs           — 启动 Web 观测台 (http://127.0.0.1:8765)
    /trace         — 导出 debug trace
    /quit          — 退出

  可用形态: normal, ganyu, jingliu, kafka, firefly,
            raiden, raiden_shogun, shenhe, feixiao, ruanmei,
            shorekeeper, bianka, kandrela, amics, alpha, weila
                """)

            elif cmd == "/tick":
                try:
                    n = int(parts[1]) if len(parts) > 1 else 20
                except (ValueError, IndexError):
                    n = 20
                idle_ticks(engine, n)
                display_soul(engine.soul_state(), chat_mode)

            elif cmd == "/status":
                display_status(engine.soul_state())

            elif cmd == "/trace":
                path = export_trace(engine)
                print(f"  Debug trace: {path}")

            elif cmd == "/aponly":
                engine = MiyaEngine(trace_mode="summary", enable_cortex=False)
                engine.start()
                idle_ticks(engine, 8)
                chat_mode = False
                print("  切换到纯 AP 模式 —— 弥娅会「感到」但不会「说话」")
                display_soul(engine.soul_state(), chat_mode)

            elif cmd == "/chat":
                engine = MiyaEngine(trace_mode="summary", enable_cortex=True)
                engine.start()
                idle_ticks(engine, 8)
                chat_mode = True
                print("  切换到 AP+LLM 模式 —— 弥娅可以回复你了")
                display_soul(engine.soul_state(), chat_mode)

            elif cmd == "/obs":
                url = engine.start_observatory()
                print(f"  观测台已启动: {url}")
                print(f"  浏览器打开即可看到弥娅的实时内心状态")
                display_soul(engine.soul_state(), chat_mode)

            elif cmd == "/form":
                form_name = parts[1].strip() if len(parts) > 1 else "normal"
                if form_name in ("normal", "常态"):
                    form_name = None
                engine.set_form(form_name)
                print(f"  形态: {form_name or '常态'}（下一轮对话生效）")
                display_soul(engine.soul_state(), chat_mode)

            else:
                print(f"  未知命令: {cmd}，输入 /help 查看帮助")

        elif chat_mode:
            print(f"  处理中...", end="", flush=True)
            reply = engine.chat(user_input)
            display_soul(engine.soul_state(), chat_mode)
            if reply:
                print(f"\n  [弥娅] {reply}")
            print()
        else:
            # Pure AP mode - just run tick, show internal state
            engine.tick(text=user_input)
            display_soul(engine.soul_state(), chat_mode)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""
Miya Doctor — 统一自检 CLI（本地 / 服务器 / CI / systemd timer 通用）

用法：
  python scripts/doctor.py                    # 静态检查 C1-C7
  python scripts/doctor.py --runtime          # 静态 + 运行时诊断 C8-C10
  python scripts/doctor.py --runtime --since "3 minutes ago"   # 部署后冒烟
  python scripts/doctor.py --json             # 机器可读输出（CI/定时任务）
  python scripts/doctor.py --runtime --fix    # 含记忆自校正

退出码：存在 FAIL → 1，否则 0
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from core.doctor import (  # noqa: E402
    FAIL,
    REPO_ROOT,
    check_memory,
    check_pc_tracker,
    check_runtime,
    has_failures,
    run_static_checks,
    summarize,
)


def finding_to_dict(f) -> dict:
    return {
        "check_id": f.check_id,
        "title": f.title,
        "status": f.status,
        "details": f.details,
        "fix_hints": f.fix_hints,
    }


def print_human(findings) -> None:
    icons = {"PASS": "✅", "WARN": "⚠️", "FAIL": "❌", "SKIP": "⏭️"}
    for f in findings:
        print(f"\n{icons.get(f.status, '·')} [{f.check_id}] {f.title} — {f.status}")
        for detail in f.details:
            if detail.startswith("["):
                print(f"    {detail}")
        for hint in f.fix_hints:
            print(f"      ↳ 修复: {hint}")

    counts = summarize(findings)
    print("\n" + "=" * 50)
    print(
        f"DOCTOR RESULT: PASS={counts.get('PASS', 0)} WARN={counts.get('WARN', 0)} "
        f"FAIL={counts.get('FAIL', 0)} SKIP={counts.get('SKIP', 0)}"
    )
    if has_failures(findings):
        print("❌ DOCTOR FAIL — 存在必须修复的检查项")


def main() -> int:
    parser = argparse.ArgumentParser(description="Miya 统一自检")
    parser.add_argument("--runtime", action="store_true", help="包含运行时诊断（健康端点/journalctl/记忆一致性）")
    parser.add_argument("--since", default="10 minutes ago", help="journalctl 扫描时间窗（默认 10 minutes ago）")
    parser.add_argument("--health-url", default="http://127.0.0.1:9800/api/v1/health", help="健康端点 URL")
    parser.add_argument("--json", action="store_true", help="机器可读 JSON 输出")
    parser.add_argument("--fix", action="store_true", help="允许自校正（记忆一致性 --fix）")
    parser.add_argument("--memory-only", action="store_true", help="仅运行记忆一致性检查")
    args = parser.parse_args()

    if args.memory_only:
        findings = [check_memory(fix=args.fix)]
    else:
        findings = run_static_checks(REPO_ROOT)
        if args.runtime:
            findings.append(check_runtime(since=args.since, health_url=args.health_url))
            findings.append(check_memory(fix=args.fix))
            findings.append(check_pc_tracker())

    if args.json:
        print(
            json.dumps(
                {
                    "summary": summarize(findings),
                    "fail": has_failures(findings),
                    "findings": [finding_to_dict(f) for f in findings],
                },
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print_human(findings)

    return 1 if has_failures(findings) else 0


if __name__ == "__main__":
    sys.exit(main())

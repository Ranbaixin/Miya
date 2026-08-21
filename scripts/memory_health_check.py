#!/usr/bin/env python3
"""记忆健康检查（2026-08 自动化）

daemon 启动时自动执行：
1. index.json 覆盖度 < 50% → 自动重建（调用 rebuild_memory_index.py）
2. 双库 level 漂移检查（只读，输出漂移数；>0 提示 --fix）

用法: python scripts/memory_health_check.py
"""

import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).parent.parent
MEM_DIR = ROOT / "data" / "memory"
LEVEL_DIRS = ["dialogue", "short_term", "long_term", "semantic", "knowledge"]


def _count_disk_files() -> int:
    total = 0
    for level in LEVEL_DIRS:
        d = MEM_DIR / level
        if d.exists():
            total += sum(1 for _ in d.rglob("*.json"))
    return total


def _count_index() -> int:
    idx = MEM_DIR / "index.json"
    if not idx.exists():
        return 0
    try:
        return len(json.loads(idx.read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return 0


def main() -> int:
    if not MEM_DIR.exists():
        print("[memory-health] 无记忆目录，跳过")
        return 0

    n_index = _count_index()
    n_files = _count_disk_files()
    print(f"[memory-health] 索引 {n_index} / 磁盘 {n_files}")

    if n_files > 0 and n_index < n_files * 0.5:
        print("[memory-health] 索引覆盖度过低，自动重建...")
        subprocess.run(
            [sys.executable, str(ROOT / "scripts" / "rebuild_memory_index.py")],
            check=False,
        )

    # 双库一致性（只读报告）
    cp = subprocess.run(
        [sys.executable, str(ROOT / "scripts" / "check_memory_consistency.py")],
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    out = (cp.stdout or "").strip()
    print(out)
    if "漂移: 0 条" not in out:
        print("[memory-health] WARNING: 检测到 level 漂移，可运行 "
              "python scripts/check_memory_consistency.py --fix 校正")
    return 0


if __name__ == "__main__":
    sys.exit(main())

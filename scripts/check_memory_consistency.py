#!/usr/bin/env python3
"""记忆双库一致性检查与校正（2026-08）

对比 JSON 文件内容与 SQLite 的记忆 level 字段：
- --fix: 以 JSON 为准校正 SQLite 的 level（默认只报告）

用法:
  python scripts/check_memory_consistency.py          # 只报告
  python scripts/check_memory_consistency.py --fix    # 校正 SQLite
"""

import argparse
import json
import pathlib
import sqlite3
import sys

MEM_DIR = pathlib.Path(__file__).parent.parent / "data" / "memory"
DB_PATH = MEM_DIR / "miya_memory.db"
LEVEL_DIRS = ["dialogue", "short_term", "long_term", "semantic", "knowledge"]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true", help="以 JSON 为准校正 SQLite")
    args = parser.parse_args()

    if not DB_PATH.exists():
        print("[check] 未找到 SQLite:", DB_PATH)
        return 1

    # JSON 文件内容的 level（以文件字段为准）
    json_levels = {}
    for level in LEVEL_DIRS:
        for f in (MEM_DIR / level).rglob("*.json"):
            try:
                d = json.loads(f.read_text(encoding="utf-8"))
                json_levels[d.get("id", f.stem)] = d.get("level", level)
            except (OSError, ValueError):
                pass

    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    sqlite_rows = {
        r["id"]: r for r in conn.execute("SELECT id, level, content FROM memories").fetchall()
    }

    drift = []
    only_json = []
    for mid, jl in json_levels.items():
        row = sqlite_rows.get(mid)
        if row is None:
            only_json.append(mid)
        elif row["level"] != jl:
            drift.append((mid, jl, row["level"]))
    only_sqlite = [mid for mid in sqlite_rows if mid not in json_levels]

    print(f"[check] JSON 文件: {len(json_levels)} 条 | SQLite: {len(sqlite_rows)} 条")
    print(f"[check] level 漂移: {len(drift)} 条 | 仅 JSON: {len(only_json)} 条 | 仅 SQLite: {len(only_sqlite)} 条")

    if args.fix and drift:
        fixed = 0
        for mid, jl, _sl in drift:
            conn.execute("UPDATE memories SET level=? WHERE id=?", (jl, mid))
            fixed += 1
        conn.commit()
        print(f"[check] 已校正 {fixed} 条 SQLite level（以 JSON 为准）")
    elif drift:
        print("[check] 提示: 运行 --fix 以 JSON 为准校正 SQLite level")
        for mid, jl, sl in drift[:8]:
            print(f"    {mid}: JSON={jl} SQLite={sl}")

    conn.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())

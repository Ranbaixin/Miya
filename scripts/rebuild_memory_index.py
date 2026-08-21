#!/usr/bin/env python3
"""重建记忆 JSON 索引（2026-08 诊断修复）

背景：data/memory/index.json 仅剩 2 条 test 索引（磁盘 2834 个 JSON 文件），
导致 JSON 后端按索引检索失效、get_statistics() 的 by_level/by_user 统计失真。

用法: python scripts/rebuild_memory_index.py
说明: 遍历 data/memory/{dialogue,short_term,long_term,semantic,knowledge}/**/*.json，
重建 index.json 与 tag_index.json。原文件备份为 .bak。
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent.parent
MEM_DIR = ROOT / "data" / "memory"
LEVEL_DIRS = ["dialogue", "short_term", "long_term", "semantic", "knowledge"]


def main() -> int:
    if not MEM_DIR.exists():
        print(f"[rebuild] 未找到记忆目录: {MEM_DIR}")
        return 1

    index: dict = {}
    tag_index: dict = {}
    skipped = 0

    for level in LEVEL_DIRS:
        level_dir = MEM_DIR / level
        if not level_dir.exists():
            continue
        for f in sorted(level_dir.rglob("*.json")):
            try:
                data = json.loads(f.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                skipped += 1
                continue
            mid = data.get("id", f.stem)
            tags = data.get("tags", []) or []
            index[mid] = {
                "level": data.get("level", level),
                "user_id": data.get("user_id", ""),
                "session_id": data.get("session_id", ""),
                "group_id": data.get("group_id", ""),
                "tags": tags,
                "created_at": data.get("created_at", ""),
                "file_path": str(f).replace("\\", "/"),
                "priority": data.get("priority", 0.5),
            }
            for tag in tags:
                tag_index.setdefault(tag, []).append(mid)

    # 备份并写回
    for name in ("index.json", "tag_index.json"):
        p = MEM_DIR / name
        if p.exists():
            shutil.copy2(p, str(p) + ".bak")

    (MEM_DIR / "index.json").write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    (MEM_DIR / "tag_index.json").write_text(
        json.dumps(tag_index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    print(f"[rebuild] 完成: index {len(index)} 条, tags {len(tag_index)} 个, 跳过损坏 {skipped} 个")
    print(f"[rebuild] 备份: index.json.bak / tag_index.json.bak")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

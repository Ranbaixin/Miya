#!/usr/bin/env python3
"""本地记忆转存 Neo4j 知识图谱（2026-08）

设计约束（用户批准项）：
- 本地记忆数据库（SQLite/JSON）严格只读：SQLite 用 mode=ro URI 打开，绝无写操作
- 写入仅发生：① Neo4j（MERGE 幂等）② 新增 checkpoint 文件 data/neo4j_migration_checkpoint.json

用法:
  python scripts/migrate_memory_to_neo4j.py --dry-run --stats   # 只统计候选，不写任何数据
  python scripts/migrate_memory_to_neo4j.py --limit 20           # 试跑前 20 条
  python scripts/migrate_memory_to_neo4j.py --no-llm             # 纯规则提取（零 LLM 成本）
  python scripts/migrate_memory_to_neo4j.py --reset-checkpoint   # 清 checkpoint 重新全量
  python scripts/migrate_memory_to_neo4j.py --stats              # 迁移后统计
"""

import argparse
import asyncio
import json
import sqlite3
import sys
import time
from pathlib import Path

ROOT = Path(__file__).parent.parent
DB_PATH = ROOT / "data" / "memory" / "miya_memory.db"
CHECKPOINT_PATH = ROOT / "data" / "neo4j_migration_checkpoint.json"

# 排除的对话型前缀（这些不是知识事实）
EXCLUDE_PREFIXES = (
    "[弥娅说]",
    "[弥娅自我认知]",
    "[AI学习]",
    "【情绪记录】",
    "【认知记录】",
    "[情绪记录]",
    "[认知记录]",
)

# 白名单标签：规则提取不到时用 LLM 深度提取
LLM_TAG_WHITELIST = {
    "喜好", "信息", "identity", "重要", "self_awareness",
    "类型_自我认知", "学习", "纠正学习",
}


def _read_neo4j_env() -> dict:
    env = {}
    for line in (ROOT / "config" / ".env").read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("NEO4J_"):
            k, _, v = line.partition("=")
            env[k.split("_", 1)[1].lower()] = v.strip()
    return env


def _load_checkpoint() -> dict:
    if CHECKPOINT_PATH.exists():
        try:
            return json.loads(CHECKPOINT_PATH.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {"processed": [], "updated_at": ""}


def _save_checkpoint(cp: dict) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    CHECKPOINT_PATH.write_text(
        json.dumps(cp, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def _load_candidates(only_ids: set | None = None) -> list[dict]:
    """从 SQLite 只读加载候选记忆（mode=ro URI + 绝对路径，机制级保证不写本地库）"""
    import urllib.parse

    abs_path = str(DB_PATH.resolve()).replace(chr(92), "/")
    uri = "file:" + urllib.parse.quote(abs_path, safe="/:") + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    conn.row_factory = sqlite3.Row
    try:
        sql = (
            "SELECT id, content, level, priority, tags, user_id, created_at, "
            "expires_at, is_archived FROM memories "
            "WHERE level='long_term' OR (level='short_term' AND priority>=0.7)"
        )
        rows = conn.execute(sql).fetchall()
    finally:
        conn.close()

    import time as _t

    now = _t.time()
    candidates = []
    for r in rows:
        mid = r["id"]
        if only_ids is not None and mid not in only_ids:
            continue
        content = (r["content"] or "").strip()
        # 排除对话型 / 空内容 / 归档 / 过期
        if not content:
            continue
        if content.startswith(EXCLUDE_PREFIXES):
            continue
        if r["is_archived"]:
            continue
        exp = r["expires_at"]
        if exp:
            try:
                from datetime import datetime

                exp_dt = datetime.fromisoformat(exp)
                if exp_dt.timestamp() < now:
                    continue
            except (ValueError, TypeError):
                pass
        try:
            tags = json.loads(r["tags"]) if r["tags"] else []
        except (ValueError, TypeError):
            tags = []
        candidates.append(
            {
                "id": mid,
                "content": content,
                "level": r["level"],
                "priority": r["priority"],
                "tags": [str(t) for t in tags],
                "user_id": r["user_id"],
                "created_at": r["created_at"],
            }
        )
    return candidates


async def _extract_and_store(grag, cand: dict, use_llm: bool) -> tuple[int, str]:
    """对单条记忆提取并入库，返回 (提取数量, 方式)"""
    # 1. 规则优先（免费）
    quintuples = grag._rule_based_extraction(cand["content"])
    method = "rule"
    # 2. 规则为空且允许 LLM 且标签命中白名单 → LLM 深度提取
    if not quintuples and use_llm and any(t in LLM_TAG_WHITELIST for t in cand["tags"]):
        quintuples = await grag._extract_quintuples_sync(cand["content"])
        method = "llm"

    stored = 0
    for q in quintuples:
        # 标注来源（记忆 id），便于追溯
        q.context = (q.context or "") + f" [来源记忆:{cand['id']}]"
        if await grag.store_quintuple(q):
            stored += 1
    return stored, method


async def migrate(args) -> int:
    cp = {} if args.reset_checkpoint else _load_checkpoint()
    processed = set(cp.get("processed", []))

    # 候选：增量模式只取未处理的（checkpoint 已处理 id 跳过）
    all_cands = _load_candidates(only_ids=None)
    pending = [c for c in all_cands if c["id"] not in processed]

    print(f"[migrate] 候选总数: {len(all_cands)} | 已处理: {len(processed)} | 待处理: {len(pending)}")

    if args.dry_run:
        by_level = {}
        for c in pending:
            by_level[c["level"]] = by_level.get(c["level"], 0) + 1
        llm_cands = sum(1 for c in pending if any(t in LLM_TAG_WHITELIST for t in c["tags"]))
        print(f"[dry-run] 将迁移 {len(pending)} 条 (long_term={by_level.get('long_term',0)}, "
              f"short_term>=0.7={by_level.get('short_term',0)}) | 其中 {llm_cands} 条将走 LLM 提取")
        print("[dry-run] 未写入任何数据（Neo4j / checkpoint 均未触碰）")
        return 0

    # 加载 Neo4j（只写目标）
    env = _read_neo4j_env()
    from core.grag_memory import initialize_grag

    cfg = {"enabled": True}
    for k, v in env.items():
        cfg[f"neo4j_{k}"] = v
    grag = await initialize_grag(cfg)
    if not grag.neo4j_driver:
        print("[migrate] ❌ Neo4j 不可用（未连接），中止（本地库未改动）")
        return 1

    stats = {"rule": 0, "llm": 0, "stored": 0, "skipped": 0, "processed_new": 0}
    t0 = time.time()
    limit = args.limit or len(pending)
    for i, cand in enumerate(pending[:limit]):
        try:
            stored, method = await _extract_and_store(grag, cand, use_llm=not args.no_llm)
            stats[method] += 1 if method == "llm" else 0
            if method == "rule" and stored:
                stats["rule"] += 1
            stats["stored"] += stored
            if stored == 0:
                stats["skipped"] += 1
            processed.add(cand["id"])
            stats["processed_new"] += 1
        except Exception as e:  # noqa: BLE001 — 单条失败跳过，不中断
            print(f"  [skip] {cand['id']}: {type(e).__name__}: {str(e)[:80]}")
            continue

        if (i + 1) % 20 == 0:
            _save_checkpoint({"processed": sorted(processed), "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
            print(f"  ... {i+1}/{min(limit, len(pending))} 条已处理 (checkpoint 已保存)")

    _save_checkpoint({"processed": sorted(processed), "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S")})
    elapsed = time.time() - t0

    print(f"[migrate] 完成: 处理 {stats['processed_new']} 条 | 入库五元组 {stats['stored']} | "
          f"规则提取 {stats['rule']} | LLM 提取 {stats['llm']} | 无结果 {stats['skipped']} | 耗时 {elapsed:.1f}s")

    if args.stats:
        gs = await grag.get_stats()
        print(f"[stats] Neo4j: {gs}")

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="本地记忆转存 Neo4j（只读源，只写图）")
    parser.add_argument("--dry-run", action="store_true", help="只统计候选，不写任何数据")
    parser.add_argument("--no-llm", action="store_true", help="禁用 LLM 提取（纯规则，零成本）")
    parser.add_argument("--limit", type=int, default=0, help="本次最多处理 N 条（0=全部）")
    parser.add_argument("--reset-checkpoint", action="store_true", help="清空 checkpoint 重新全量")
    parser.add_argument("--stats", action="store_true", help="完成后输出 Neo4j 统计")
    args = parser.parse_args()

    try:
        return asyncio.run(migrate(args))
    except KeyboardInterrupt:
        print("[migrate] 中断（checkpoint 已按批保存，可续跑）")
        return 130


if __name__ == "__main__":
    sys.exit(main())

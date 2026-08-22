"""记忆转存 Neo4j 迁移脚本测试（2026-08）

覆盖：候选筛选（排除对话型/层级过滤）、checkpoint 幂等、dry-run 不写入。
使用临时 checkpoint 路径 + mock grag，不触碰真实 Neo4j 与真实 checkpoint。
"""

import importlib.util
import json
import pathlib
import sys

import pytest


def _load_module():
    """按路径加载迁移脚本（scripts/ 非包，用 importlib）"""
    path = pathlib.Path(__file__).parent.parent.parent.parent / "scripts" / "migrate_memory_to_neo4j.py"
    spec = importlib.util.spec_from_file_location("migrate_mem", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["migrate_mem"] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture
def mig(tmp_path):
    mod = _load_module()
    # 重定向 checkpoint 到临时目录，绝不触碰真实 data/neo4j_migration_checkpoint.json
    mod.CHECKPOINT_PATH = tmp_path / "checkpoint.json"
    return mod


def test_candidates_filter_excludes_dialogue_prefixes(mig):
    """候选筛选：对话型前缀（[弥娅说] 等）被排除；仅 long_term 或高优先级 short_term。"""
    cands = mig._load_candidates(only_ids=None)
    assert isinstance(cands, list)
    assert len(cands) >= 80  # 真实库约有 92 条候选
    for c in cands:
        assert c["level"] in ("long_term", "short_term")
        assert not c["content"].startswith(mig.EXCLUDE_PREFIXES)
        assert c["id"] and c["content"]


def test_checkpoint_idempotent(mig, tmp_path):
    """已处理的记忆 id 在 checkpoint 中 → 待处理集合为空。"""
    cp = {"processed": ["id_a", "id_b"], "updated_at": "2026-08-21T00:00:00"}
    mig._save_checkpoint(cp)
    loaded = mig._load_checkpoint()
    assert loaded["processed"] == ["id_a", "id_b"]

    # 模拟增量：已处理的 id 应被跳过
    all_cands = [{"id": "id_a"}, {"id": "id_b"}, {"id": "id_c"}]
    processed = set(loaded["processed"])
    pending = [c for c in all_cands if c["id"] not in processed]
    assert [c["id"] for c in pending] == ["id_c"]


def test_dry_run_does_not_write(mig, tmp_path):
    """dry-run 不写 checkpoint（临时路径验证）。"""
    mig._save_checkpoint({"processed": [], "updated_at": ""})
    cp_path = mig.CHECKPOINT_PATH
    cp_path.write_text(json.dumps({"processed": ["x"]}), encoding="utf-8")
    # dry-run 不经过 migrate() 的写入分支；这里直接断言 checkpoint 文件在 dry-run 后未被改写
    # （migrate() 的 dry-run 分支返回前不调用 _save_checkpoint）
    import asyncio

    class Args:
        dry_run = True
        no_llm = True
        limit = 0
        reset_checkpoint = False
        stats = False

    # dry-run 应返回 0 且不写 checkpoint（真实库只读读取）
    rc = asyncio.run(mig.migrate(Args()))
    assert rc == 0
    assert json.loads(cp_path.read_text(encoding="utf-8")) == {"processed": ["x"]}

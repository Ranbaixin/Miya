"""A6 SQLite 图存储测试（2026-09）。

覆盖：
- SQLiteGraphStore CRUD：写入 / 关键词查询 / 实体查询 / 最近查询
- 幂等写入（同 SPO 去重，对齐 Neo4j MERGE）
- KnowledgeGraphManager 走 graph_store 后端 + format_knowledge_for_prompt
- GRAGMemoryManager.store_quintuple 默认写 graph_store（不依赖 Neo4j）
"""

import shutil
import tempfile
import time
from pathlib import Path

import pytest

from core.grag_memory import GRAGMemoryManager, Quintuple
from core.knowledge_graph import KnowledgeGraphManager, format_knowledge_for_prompt
from memory.graph_store import SQLiteGraphStore


@pytest.fixture
def store():
    tmp = tempfile.mkdtemp()
    s = SQLiteGraphStore(str(Path(tmp) / "graph.db"))
    yield s
    s._conn.close() if s._conn else None
    shutil.rmtree(tmp, ignore_errors=True)


async def test_store_and_query_by_keywords(store):
    ok = await store.store_quintuple(
        subject="然鑫", relation="喜欢", object_="科幻电影",
        context="聊天中提到", timestamp=time.time(),
        subject_type="人物", object_type="事物",
    )
    assert ok is True

    rows = await store.query_by_keywords(["科幻"])
    assert len(rows) == 1
    r = rows[0]
    assert r["subject"] == "然鑫"
    assert r["relation"] == "喜欢" and r["predicate"] == "喜欢"
    assert r["object"] == "科幻电影"
    assert r["subject_type"] == "人物"
    assert r["object_type"] == "事物"
    assert r["context"] == "聊天中提到"


async def test_query_by_entity(store):
    await store.store_quintuple("然鑫", "住在", "成都", timestamp=1.0)
    await store.store_quintuple("成都", "位于", "四川", timestamp=2.0)

    rows = await store.query_by_entity("成都")
    assert len(rows) == 2, "subject/object 命中均应返回"

    rows_filtered = await store.query_by_entity("成都", relation="位于")
    assert len(rows_filtered) == 1
    assert rows_filtered[0]["predicate"] == "位于"


async def test_idempotent_upsert(store):
    """同 (subject, predicate, object) 重复写入不产生重复边。"""
    await store.store_quintuple("然鑫", "喜欢", "科幻电影", context="第一次", timestamp=1.0)
    await store.store_quintuple("然鑫", "喜欢", "科幻电影", context="第二次", timestamp=2.0)

    rows = await store.query_by_keywords(["科幻"])
    assert len(rows) == 1, "同 SPO 应去重"
    assert rows[0]["context"] == "第二次", "应更新为最新内容"

    stats = await store.get_stats()
    assert stats["entities"] == 2
    assert stats["relations"] == 1


async def test_get_recent(store):
    await store.store_quintuple("A", "认识", "B", session_id="s1", timestamp=1.0)
    await store.store_quintuple("C", "认识", "D", session_id="s2", timestamp=2.0)

    all_recent = await store.get_recent(limit=10)
    assert len(all_recent) == 2
    assert all_recent[0]["subject"] == "C", "按时间倒序"

    s1_recent = await store.get_recent(session_id="s1", limit=10)
    assert len(s1_recent) == 1
    assert s1_recent[0]["subject"] == "A"


async def test_knowledge_graph_manager_graph_store_backend(store):
    """KnowledgeGraphManager 走 graph_store 后端，查询结果可直接进提示词。"""
    kg = KnowledgeGraphManager(graph_store=store)
    assert kg.enabled

    from core.quintuple_extractor import Quintuple as ExtQuintuple

    q = ExtQuintuple(
        subject="然鑫", subject_type="人物", predicate="喜欢",
        object="科幻电影", object_type="事物", context="聊天",
    )
    assert await kg.add_quintuples([q], session_id="s1") is True

    knowledge = await kg.query_by_keywords(["科幻"])
    assert len(knowledge) == 1

    prompt = format_knowledge_for_prompt(knowledge)
    assert "【相关记忆】" in prompt
    assert "然鑫(人物) 喜欢 科幻电影(事物)" in prompt, f"格式化输出: {prompt}"


async def test_grag_stores_to_graph_store_by_default(store):
    """GRAG 默认后端为 graph_store：store → query 全链路不依赖 Neo4j。"""
    mgr = GRAGMemoryManager({"enabled": True})
    assert mgr.use_neo4j is False
    mgr._graph_store = store  # 注入临时库，避免写生产 miya_memory.db

    ok = await mgr.store_quintuple(
        Quintuple(
            subject="弥娅", relation="记得", object="然鑫的生日",
            attributes={}, context="对话", timestamp=time.time(),
        )
    )
    assert ok is True

    rows = await mgr.query_by_keywords(["生日"])
    assert len(rows) == 1
    assert rows[0]["object"] == "然鑫的生日"

    stats = await mgr.get_stats()
    assert stats["backend"] == "sqlite_graph"
    assert stats["relations"] == 1

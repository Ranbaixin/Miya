"""
知识图谱管理器 - 五元组存储与检索

2026-09：默认后端为 memory.graph_store.SQLiteGraphStore（Neo4j 读取链路
此前断裂——同步 Session 被 async with 调用，每次查询抛异常被吞返回空）。
Neo4j driver 入参保留兼容，显式传入时仍走原路径。
"""

import asyncio
import logging
import time
from typing import Dict, List, Optional

from core.quintuple_extractor import Quintuple

logger = logging.getLogger(__name__)


class KnowledgeGraphManager:
    """知识图谱管理器 - 管理五元组的存储和检索"""

    def __init__(self, neo4j_driver=None, graph_store=None):
        self.driver = neo4j_driver
        # 2026-09：SQLite 图存储后端（默认）
        self.graph_store = graph_store
        self.enabled = neo4j_driver is not None or graph_store is not None
        self._extraction_queue = asyncio.Queue()
        self._processing = False

    async def add_quintuples(self, quintuples: List[Quintuple], session_id: str = "default") -> bool:
        """
        将五元组添加到知识图谱

        Args:
            quintuples: 五元组列表
            session_id: 会话ID

        Returns:
            是否成功
        """
        if not self.enabled or not quintuples:
            return False

        if self.graph_store is not None:
            ok = True
            for q in quintuples:
                stored = await self.graph_store.store_quintuple(
                    subject=q.subject,
                    relation=q.predicate,
                    object_=q.object,
                    context=getattr(q, "context", ""),
                    session_id=session_id,
                    attributes={},
                    timestamp=time.time(),
                    subject_type=getattr(q, "subject_type", "") or "实体",
                    object_type=getattr(q, "object_type", "") or "实体",
                )
                ok = ok and stored
            logger.info(f"[知识图谱] 添加了 {len(quintuples)} 个五元组（graph_store）")
            return ok

        try:
            async with self.driver.session() as session:
                for q in quintuples:
                    # 创建实体节点
                    await session.run(
                        """
                        MERGE (s:Entity {name: $subject, type: $subject_type})
                        MERGE (o:Entity {name: $object, type: $object_type})
                        """,
                        subject=q.subject,
                        subject_type=q.subject_type,
                        object=q.object,
                        object_type=q.object_type,
                    )

                    # 创建关系
                    await session.run(
                        """
                        MATCH (s:Entity {name: $subject}), (o:Entity {name: $object})
                        MERGE (s)-[r:RELATES {predicate: $predicate, session: $session_id, timestamp: timestamp()}]->(o)
                        """,
                        subject=q.subject,
                        object=q.object,
                        predicate=q.predicate,
                        session_id=session_id,
                    )

            logger.info(f"[知识图谱] 添加了 {len(quintuples)} 个五元组")
            return True

        except Exception as e:  # noqa: BLE001 — 添加五元组失败
            logger.error(f"[知识图谱] 添加五元组失败: {e}")
            return False

    async def query_by_keywords(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """
        通过关键词查询知识图谱

        Args:
            keywords: 关键词列表
            limit: 返回数量限制

        Returns:
            五元组列表
        """
        if not self.enabled or not keywords:
            return []

        if self.graph_store is not None:
            return await self.graph_store.query_by_keywords(keywords, limit)

        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MATCH (s:Entity)-[r:RELATES]->(o:Entity)
                    WHERE s.name CONTAINS $keyword OR o.name CONTAINS $keyword
                    RETURN s.name as subject, s.type as subject_type,
                           r.predicate as predicate, o.name as object, o.type as object_type
                    LIMIT $limit
                    """,
                    keyword=keywords[0],
                    limit=limit,
                )

                records = await result.data()
                return [
                    {
                        "subject": r["subject"],
                        "subject_type": r["subject_type"],
                        "predicate": r["predicate"],
                        "object": r["object"],
                        "object_type": r["object_type"],
                    }
                    for r in records
                ]

        except Exception as e:  # noqa: BLE001 — 查询失败
            logger.error(f"[知识图谱] 查询失败: {e}")
            return []

    async def query_by_entity(self, entity_name: str, limit: int = 10) -> List[Dict]:
        """
        通过实体查询相关知识

        Args:
            entity_name: 实体名称
            limit: 返回数量限制

        Returns:
            相关的五元组
        """
        if not self.enabled or not entity_name:
            return []

        if self.graph_store is not None:
            return await self.graph_store.query_by_entity(entity_name, limit=limit)

        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MATCH (s:Entity)-[r:RELATES]->(o:Entity)
                    WHERE s.name = $entity OR o.name = $entity
                    RETURN s.name as subject, s.type as subject_type,
                           r.predicate as predicate, o.name as object, o.type as object_type,
                           r.timestamp as timestamp
                    ORDER BY r.timestamp DESC
                    LIMIT $limit
                    """,
                    entity=entity_name,
                    limit=limit,
                )

                records = await result.data()
                return [
                    {
                        "subject": r["subject"],
                        "subject_type": r["subject_type"],
                        "predicate": r["predicate"],
                        "object": r["object"],
                        "object_type": r["object_type"],
                        "timestamp": r.get("timestamp"),
                    }
                    for r in records
                ]

        except Exception as e:  # noqa: BLE001 — 实体查询失败
            logger.error(f"[知识图谱] 实体查询失败: {e}")
            return []

    async def get_recent_knowledge(self, session_id: str = "default", limit: int = 10) -> List[Dict]:
        """获取最近的记忆"""
        if not self.enabled:
            return []

        if self.graph_store is not None:
            return await self.graph_store.get_recent(session_id=session_id, limit=limit)

        try:
            async with self.driver.session() as session:
                result = await session.run(
                    """
                    MATCH (s:Entity)-[r:RELATES]->(o:Entity)
                    WHERE r.session = $session_id
                    RETURN s.name as subject, s.type as subject_type,
                           r.predicate as predicate, o.name as object, o.type as object_type
                    ORDER BY r.timestamp DESC
                    LIMIT $limit
                    """,
                    session_id=session_id,
                    limit=limit,
                )

                records = await result.data()
                return [
                    {
                        "subject": r["subject"],
                        "subject_type": r["subject_type"],
                        "predicate": r["predicate"],
                        "object": r["object"],
                        "object_type": r["object_type"],
                    }
                    for r in records
                ]

        except Exception as e:  # noqa: BLE001 — 获取最近记忆失败
            logger.error(f"[知识图谱] 获取最近记忆失败: {e}")
            return []


def format_knowledge_for_prompt(knowledge: List[Dict]) -> str:
    """将知识图谱查询结果格式化为提示词"""
    if not knowledge:
        return ""

    lines = ["【相关记忆】"]
    for k in knowledge[:8]:
        lines.append(f"- {k['subject']}({k['subject_type']}) {k['predicate']} {k['object']}({k['object_type']})")

    return "\n".join(lines)

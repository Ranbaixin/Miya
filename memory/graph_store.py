"""
弥娅知识图谱 SQLite 存储（2026-09）

替代 Neo4j 的图存储：当前用例（关键词/实体一跳查询）用不到图数据库的
多跳遍历与图算法，SQLite 表 + 索引即可覆盖，免去独立服务部署与
"同步 Session 被 async with 调用导致读取链路全断"的隐性故障。

表结构（建在 miya_memory.db 内，复用 sqlite_backend 的 pragma 配置）：
- kg_entities(name TEXT PRIMARY KEY, type TEXT)
- kg_edges(subject, predicate, object, context, session_id, attributes, timestamp)
  + UNIQUE(subject, predicate, object) —— 与 Neo4j MERGE 对齐的幂等写入
"""

import json
import logging
import sqlite3
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


def _load_graph_config() -> dict:
    """从 text_config.json 加载 graph_store 配置（统一缓存）"""
    from memory.memory_config import get_memory_section

    return get_memory_section("graph_store")


class SQLiteGraphStore:
    """知识图谱 SQLite 存储"""

    def __init__(self, db_path: Optional[str] = None):
        self._config = _load_graph_config()
        self._enabled = bool(self._config.get("enabled", True))

        if not self._enabled:
            logger.info("[GraphStore] 未启用，跳过初始化")
            self._conn: Optional[sqlite3.Connection] = None
            return

        cfg_path = db_path or self._config.get("db_path", "data/memory/miya_memory.db")
        self.db_path = Path(cfg_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = None
        self._init_db()

    @property
    def enabled(self) -> bool:
        return self._enabled and self._conn is not None

    def _get_conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            self._conn.execute("PRAGMA journal_mode=WAL")
            self._conn.execute("PRAGMA busy_timeout=5000")
            self._apply_pragma()
        return self._conn

    def _apply_pragma(self):
        """复用 sqlite_backend 的 pragma 配置（cache_size 等）"""
        from memory.memory_config import get_memory_section

        pragma = get_memory_section("sqlite_backend").get("pragma", {})
        for key, value in pragma.items():
            if isinstance(value, bool):
                value = 1 if value else 0
            self._conn.execute(f"PRAGMA {key}={value}")

    def _init_db(self):
        conn = self._get_conn()
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kg_entities (
                name TEXT PRIMARY KEY,
                type TEXT NOT NULL DEFAULT '实体'
            )
            """)
        conn.execute("""
            CREATE TABLE IF NOT EXISTS kg_edges (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject TEXT NOT NULL,
                predicate TEXT NOT NULL,
                object TEXT NOT NULL,
                context TEXT DEFAULT '',
                session_id TEXT DEFAULT '',
                attributes TEXT DEFAULT '{}',
                timestamp REAL DEFAULT 0
            )
            """)
        # 幂等写入：同 (subject, predicate, object) 只保留一条（对齐 Neo4j MERGE）
        conn.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_kg_edges_spo
            ON kg_edges(subject, predicate, object)
            """)
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_subject ON kg_edges(subject)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_object ON kg_edges(object)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_kg_edges_timestamp ON kg_edges(timestamp)")
        conn.commit()
        logger.info(f"[GraphStore] 知识图谱存储初始化完成: {self.db_path}")

    # ==================== 写入 ====================

    async def store_quintuple(
        self,
        subject: str,
        relation: str,
        object_: str,
        context: str = "",
        session_id: str = "",
        attributes: Optional[Dict[str, Any]] = None,
        timestamp: Optional[float] = None,
        subject_type: str = "实体",
        object_type: str = "实体",
    ) -> bool:
        """存储五元组（幂等：同 SPO 更新而非重复插入）"""
        if not self.enabled or not subject or not relation:
            return False
        try:
            conn = self._get_conn()
            conn.execute(
                "INSERT OR IGNORE INTO kg_entities(name, type) VALUES (?, ?)",
                (subject, subject_type or "实体"),
            )
            conn.execute(
                "INSERT OR IGNORE INTO kg_entities(name, type) VALUES (?, ?)",
                (object_, object_type or "实体"),
            )
            conn.execute(
                """
                INSERT INTO kg_edges(subject, predicate, object, context, session_id, attributes, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(subject, predicate, object) DO UPDATE SET
                    context=excluded.context,
                    session_id=excluded.session_id,
                    attributes=excluded.attributes,
                    timestamp=excluded.timestamp
                """,
                (
                    subject,
                    relation,
                    object_,
                    context or "",
                    session_id or "",
                    json.dumps(attributes or {}, ensure_ascii=False),
                    float(timestamp if timestamp is not None else time.time()),
                ),
            )
            conn.commit()
            return True
        except Exception as e:  # noqa: BLE001 — 存储失败返回 False，由调用方检查
            logger.error(f"[GraphStore] 存储五元组失败: {e}")
            return False

    # ==================== 查询 ====================

    @staticmethod
    def _row_to_dict(row) -> Dict[str, Any]:
        # 同时提供 predicate（knowledge_graph 消费）与 relation（grag 消费）
        d = dict(row)
        d.setdefault("relation", d.get("predicate", ""))
        d.setdefault("predicate", d.get("relation", ""))
        return d

    async def query_by_keywords(self, keywords: List[str], limit: int = 10) -> List[Dict]:
        """关键词查询：subject/object/predicate LIKE 任一命中"""
        if not self.enabled or not keywords:
            return []
        try:
            conn = self._get_conn()
            conditions = []
            params: List[Any] = []
            for kw in keywords:
                if not kw:
                    continue
                pattern = f"%{kw}%"
                conditions.append("(ed.subject LIKE ? OR ed.object LIKE ? OR ed.predicate LIKE ?)")
                params.extend([pattern, pattern, pattern])
            if not conditions:
                return []
            sql = (
                f"SELECT e1.name AS subject, e1.type AS subject_type, "
                f"ed.predicate AS predicate, e2.name AS object, e2.type AS object_type, "
                f"ed.context AS context, ed.timestamp AS timestamp "
                f"FROM kg_edges ed "
                f"JOIN kg_entities e1 ON e1.name = ed.subject "
                f"JOIN kg_entities e2 ON e2.name = ed.object "
                f"WHERE {' OR '.join(conditions)} "
                f"ORDER BY ed.timestamp DESC LIMIT ?"
            )
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:  # noqa: BLE001 — 查询失败返回空列表，由调用方降级
            logger.error(f"[GraphStore] 关键词查询失败: {e}")
            return []

    async def query_by_entity(self, entity: str, relation: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """实体一跳查询（subject 或 object 精确匹配）"""
        if not self.enabled or not entity:
            return []
        try:
            conn = self._get_conn()
            sql = (
                f"SELECT e1.name AS subject, e1.type AS subject_type, "
                f"ed.predicate AS predicate, e2.name AS object, e2.type AS object_type, "
                f"ed.context AS context, ed.timestamp AS timestamp "
                f"FROM kg_edges ed "
                f"JOIN kg_entities e1 ON e1.name = ed.subject "
                f"JOIN kg_entities e2 ON e2.name = ed.object "
                f"WHERE (ed.subject = ? OR ed.object = ?)"
            )
            params: List[Any] = [entity, entity]
            if relation:
                sql += " AND ed.predicate = ?"
                params.append(relation)
            sql += " ORDER BY ed.timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:  # noqa: BLE001 — 实体查询失败返回空列表
            logger.error(f"[GraphStore] 实体查询失败: {e}")
            return []

    async def get_recent(self, session_id: Optional[str] = None, limit: int = 10) -> List[Dict]:
        """最近写入的五元组（可按会话过滤）"""
        if not self.enabled:
            return []
        try:
            conn = self._get_conn()
            sql = (
                f"SELECT e1.name AS subject, e1.type AS subject_type, "
                f"ed.predicate AS predicate, e2.name AS object, e2.type AS object_type, "
                f"ed.context AS context, ed.timestamp AS timestamp "
                f"FROM kg_edges ed "
                f"JOIN kg_entities e1 ON e1.name = ed.subject "
                f"JOIN kg_entities e2 ON e2.name = ed.object"
            )
            params: List[Any] = []
            if session_id:
                sql += " WHERE ed.session_id = ?"
                params.append(session_id)
            sql += " ORDER BY ed.timestamp DESC LIMIT ?"
            params.append(limit)
            rows = conn.execute(sql, params).fetchall()
            return [self._row_to_dict(r) for r in rows]
        except Exception as e:  # noqa: BLE001 — 查询失败返回空列表
            logger.error(f"[GraphStore] 最近知识查询失败: {e}")
            return []

    async def get_stats(self) -> Dict[str, Any]:
        """统计信息"""
        if not self.enabled:
            return {"enabled": False, "backend": "sqlite_graph"}
        try:
            conn = self._get_conn()
            entities = conn.execute("SELECT COUNT(*) FROM kg_entities").fetchone()[0]
            relations = conn.execute("SELECT COUNT(*) FROM kg_edges").fetchone()[0]
            return {
                "enabled": True,
                "backend": "sqlite_graph",
                "entities": entities,
                "relations": relations,
            }
        except Exception as e:  # noqa: BLE001 — 统计失败返回错误状态
            return {"enabled": True, "backend": "sqlite_graph", "error": str(e)}

    async def close(self):
        if self._conn:
            self._conn.close()
            self._conn = None


# 全局实例
_graph_store: Optional[SQLiteGraphStore] = None


def get_graph_store() -> SQLiteGraphStore:
    """获取全局 graph_store 单例（None-safe：未启用时返回未启用的实例）"""
    global _graph_store
    if _graph_store is None:
        _graph_store = SQLiteGraphStore()
    return _graph_store

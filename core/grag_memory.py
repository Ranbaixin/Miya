"""
弥娅 GRAG 知识图谱记忆系统

从 NagaAgent 引入的 Graph-RAG 记忆系统：
- 五元组 (主体, 关系, 客体, 属性, 上下文) 知识图谱
- Neo4j 图数据库存储
- 向量检索增强
- 自动从对话中提取知识

特点：
- 惰性连接 Neo4j（避免误触本地连接）
- 异步任务队列处理
- 语义+图谱双检索
"""

import asyncio
import logging
import os
import time
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass
import hashlib
import json

logger = logging.getLogger(__name__)

# 默认配置
DEFAULT_CONFIG = {
    "enabled": True,
    "auto_extract": True,
    "context_length": 20,
    "similarity_threshold": 0.7,
    "neo4j_uri": "bolt://localhost:7687",
    "neo4j_user": "neo4j",
    "neo4j_password": "",
    "embedding_model": "text-embedding-3-small",
    "max_workers": 3,
    "max_queue_size": 100,
    "task_timeout": 30,
    "auto_cleanup_hours": 24,
}


@dataclass
class Quintuple:
    """五元组：主体、关系、客体、属性、上下文"""

    subject: str
    relation: str
    object: str
    attributes: Dict[str, Any]
    context: str
    timestamp: float


class GRAGMemoryManager:
    """GRAG 知识图谱记忆管理器"""

    _instance = None

    @classmethod
    def get_instance(cls, config: Optional[Dict] = None) -> "GRAGMemoryManager":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(config or DEFAULT_CONFIG)
        return cls._instance

    def __init__(self, config: Dict):
        """初始化 GRAG 记忆系统"""
        self.config = {**DEFAULT_CONFIG, **config}
        self.enabled = self.config.get("enabled", True)
        self.auto_extract = self.config.get("auto_extract", True)
        self.context_length = self.config.get("context_length", 20)
        self.similarity_threshold = self.config.get("similarity_threshold", 0.7)

        # 最近对话上下文
        self.recent_context: List[str] = []

        # 提取缓存（避免重复提取）
        self._extraction_cache: set = set()

        # Neo4j 连接（惰性初始化）
        self._neo4j_driver = None
        self._neo4j_initialized = False

        # 任务管理器集成
        self._task_manager = None

        logger.info("[GRAG] 记忆系统初始化完成")

    @property
    def neo4j_driver(self):
        """惰性初始化 Neo4j 连接"""
        if not self._neo4j_initialized:
            try:
                from neo4j import GraphDatabase

                uri = self.config.get("neo4j_uri", "bolt://localhost:7687")
                user = self.config.get("neo4j_user", "neo4j")
                password = self.config.get("neo4j_password", "")

                self._neo4j_driver = GraphDatabase.driver(uri, auth=(user, password))
                self._neo4j_initialized = True
                logger.info("[GRAG] Neo4j 连接成功")
            except Exception as e:
                logger.warning(f"[GRAG] Neo4j 连接失败: {e}")
                self._neo4j_initialized = True  # 只警告一次

        return self._neo4j_driver

    async def initialize(self) -> None:
        """初始化异步组件"""
        if not self.enabled:
            logger.info("[GRAG] GRAG 记忆系统已禁用")
            return

        # 导入任务管理器
        try:
            from core.task_manager import get_task_manager, start_task_manager

            self._task_manager = get_task_manager()

            # 注册五元组提取处理器
            async def handle_quintuple_extract(payload: Dict) -> List[Quintuple]:
                text = payload.get("text", "")
                return await self._extract_quintuples_sync(text)

            self._task_manager.register_handler(
                "quintuple_extract", handle_quintuple_extract
            )

            # 启动任务管理器
            await start_task_manager()

            logger.info("[GRAG] 任务管理器集成完成")
        except Exception as e:
            logger.warning(f"[GRAG] 任务管理器集成失败: {e}")

    async def add_conversation_memory(self, user_input: str, ai_response: str) -> bool:
        """添加对话记忆到知识图谱"""
        if not self.enabled:
            return False

        try:
            conversation_text = f"用户: {user_input}\n弥娅: {ai_response}"
            logger.debug(f"[GRAG] 添加对话: {conversation_text[:50]}...")

            # 更新最近上下文
            self.recent_context.append(conversation_text)
            if len(self.recent_context) > self.context_length:
                self.recent_context = self.recent_context[-self.context_length :]

            # 自动提取五元组
            if self.auto_extract and self._task_manager:
                try:
                    task_id = await self._task_manager.add_task(
                        task_type="quintuple_extract",
                        payload={"text": conversation_text},
                        max_retries=3,
                    )
                    logger.info(f"[GRAG] 已提交提取任务: {task_id}")
                    return True
                except Exception as e:
                    logger.error(f"[GRAG] 提交提取任务失败: {e}")
                    # 同步回退
                    await self._extract_and_store_quintuples_sync(conversation_text)

            return True
        except Exception as e:
            logger.error(f"[GRAG] 添加对话记忆失败: {e}")
            return False

    async def _extract_and_store_quintuples_sync(self, text: str) -> List[Quintuple]:
        """同步提取并存储五元组（回退方案）"""
        quintuples = await self._extract_quintuples_sync(text)
        for q in quintuples:
            await self.store_quintuple(q)
        return quintuples

    async def _extract_quintuples_sync(self, text: str) -> List[Quintuple]:
        """同步提取五元组"""
        # 检查缓存
        text_hash = hashlib.md5(text.encode()).hexdigest()
        if text_hash in self._extraction_cache:
            return []

        self._extraction_cache.add(text_hash)

        # 简单的五元组提取（基于规则，后续可接入LLM）
        quintuples = []

        # 示例：从文本中提取实体和关系
        # 实际应用中可以使用 LLM 或正则表达式
        try:
            # 从模型池获取客户端（优先使用成本低的模型）
            from core.model_pool_compat import get_model_pool

            pool = get_model_pool()
            client = pool.create_ai_client(task_type="simple_chat", endpoint="qq")

            if not client:
                raise ValueError("无法从模型池创建客户端")

            prompt = f"""从以下对话中提取知识五元组（主体, 关系, 客体, 属性, 上下文）。
返回JSON数组格式。

对话：
{text}

要求：
- 主体：实体或角色
- 关系：动作或关联
- 客体：被影响的对象
- 属性：额外描述
- 上下文：对话背景

只返回JSON数组，不要其他内容。
"""

            from core.ai_client import AIMessage

            response = await client.chat([AIMessage(role="user", content=prompt)])

            content = (
                response.content if hasattr(response, "content") else str(response)
            )

            # 解析JSON
            try:
                data = json.loads(content)
                for item in data:
                    q = Quintuple(
                        subject=item.get("subject", ""),
                        relation=item.get("relation", ""),
                        object=item.get("object", ""),
                        attributes=item.get("attributes", {}),
                        context=item.get("context", ""),
                        timestamp=time.time(),
                    )
                    if q.subject and q.relation:
                        quintuples.append(q)
            except json.JSONDecodeError:
                logger.warning(f"[GRAG] 解析五元组失败: {content[:100]}")

        except Exception as e:
            logger.warning(f"[GRAG] LLM提取失败，使用规则: {e}")
            # 简单的规则提取作为回退
            quintuples = self._rule_based_extraction(text)

        return quintuples

    def _rule_based_extraction(self, text: str) -> List[Quintuple]:
        """基于规则的五元组提取（简单实现）"""
        quintuples = []

        # 提取"是"关系
        import re

        patterns = [
            r"(.+?)是(.+?)(?:，|,|$)",
            r"(.+?)叫(.+?)(?:，|,|$)",
            r"(.+?)喜欢(.+?)(?:，|,|$)",
        ]

        for pattern in patterns:
            matches = re.finditer(pattern, text)
            for match in matches:
                groups = match.groups()
                if len(groups) >= 2:
                    q = Quintuple(
                        subject=groups[0].strip(),
                        relation="是"
                        if "是" in pattern
                        else "叫"
                        if "叫" in pattern
                        else "喜欢",
                        object=groups[1].strip(),
                        attributes={},
                        context=text[:100],
                        timestamp=time.time(),
                    )
                    if q.subject and q.object:
                        quintuples.append(q)

        return quintuples

    async def store_quintuple(self, quintuple: Quintuple) -> bool:
        """存储五元组到图数据库"""
        if not self.enabled:
            return False

        driver = self.neo4j_driver
        if not driver:
            logger.warning("[GRAG] Neo4j 不可用，跳过存储")
            return False

        try:
            # FIX: GraphDatabase.driver 创建的是同步 driver；不能使用 async with/await session.run。
            # 为避免阻塞事件循环，这里把同步的 Neo4j I/O 放入线程池执行。
            def _run():
                with driver.session() as session:
                    session.run(
                        """
                        MERGE (s:Entity {name: $subject})
                        MERGE (o:Entity {name: $object})
                        MERGE (s)-[r:RELATION {type: $relation}]->(o)
                        SET r.timestamp = $timestamp,
                            r.context = $context,
                            r.attributes = $attributes
                        """,
                        subject=quintuple.subject,
                        relation=quintuple.relation,
                        object=quintuple.object,
                        timestamp=quintuple.timestamp,
                        context=quintuple.context,
                        attributes=json.dumps(quintuple.attributes),
                    )

            await asyncio.to_thread(_run)

            logger.debug(
                f"[GRAG] 已存储五元组: {quintuple.subject} - {quintuple.relation} -> {quintuple.object}"
            )
            return True
        except Exception as e:
            logger.error(f"[GRAG] 存储五元组失败: {e}")
            return False

    async def query_by_keywords(
        self, keywords: List[str], limit: int = 10
    ) -> List[Dict]:
        """通过关键词查询知识图谱"""
        driver = self.neo4j_driver
        if not driver:
            return []

        try:
            # FIX: 同步 Neo4j driver + 异步调用混用会报错；在线程中执行同步查询。
            def _run() -> List[Dict]:
                with driver.session() as session:
                    result = session.run(
                        """
                        MATCH (s:Entity)-[r:RELATION]->(o:Entity)
                        WHERE s.name CONTAINS $keyword OR o.name CONTAINS $keyword
                           OR r.type CONTAINS $keyword
                        RETURN s.name as subject, r.type as relation, o.name as object,
                               r.timestamp as timestamp, r.context as context
                        LIMIT $limit
                        """,
                        keyword=keywords[0] if keywords else "",
                        limit=limit,
                    )
                    return result.data()

            return await asyncio.to_thread(_run)
        except Exception as e:
            logger.error(f"[GRAG] 查询失败: {e}")
            return []

    async def query_by_entity(
        self, entity: str, relation: Optional[str] = None
    ) -> List[Dict]:
        """通过实体查询"""
        driver = self.neo4j_driver
        if not driver:
            return []

        try:
            # FIX: 同步 Neo4j driver + 异步调用混用会报错；在线程中执行同步查询。
            def _run() -> List[Dict]:
                with driver.session() as session:
                    if relation:
                        result = session.run(
                            """
                            MATCH (s:Entity {name: $entity})-[r:RELATION {type: $relation}]->(o:Entity)
                            RETURN s.name as subject, r.type as relation, o.name as object
                            """,
                            entity=entity,
                            relation=relation,
                        )
                    else:
                        result = session.run(
                            """
                            MATCH (s:Entity {name: $entity})-[r:RELATION]->(o:Entity)
                            RETURN s.name as subject, r.type as relation, o.name as object
                            """,
                            entity=entity,
                        )
                    return result.data()

            return await asyncio.to_thread(_run)
        except Exception as e:
            logger.error(f"[GRAG] 实体查询失败: {e}")
            return []

    async def get_context(self, query: str, limit: int = 5) -> str:
        """获取记忆上下文（用于增强LLM提示）"""
        # 提取关键词
        keywords = query.split()[:3]

        # 知识图谱查询
        graph_results = await self.query_by_keywords(keywords, limit)

        if not graph_results:
            return ""

        # 构建上下文
        context_parts = ["知识图谱记忆:"]
        for r in graph_results:
            context_parts.append(f"- {r['subject']} {r['relation']} {r['object']}")

        return "\n".join(context_parts)

    async def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        driver = self.neo4j_driver
        if not driver:
            return {"enabled": self.enabled, "neo4j": "disconnected"}

        try:
            # FIX: 同步 Neo4j driver + 异步调用混用会报错；在线程中执行同步查询。
            def _run() -> Dict[str, Any]:
                with driver.session() as session:
                    result = session.run(
                        """
                        MATCH (n:Entity)
                        OPTIONAL MATCH ()-[r:RELATION]->()
                        RETURN count(DISTINCT n) as entities, count(r) as relations
                        """
                    )
                    record = result.single()
                    return {
                        "enabled": self.enabled,
                        "neo4j": "connected",
                        "entities": record["entities"] if record else 0,
                        "relations": record["relations"] if record else 0,
                        "context_length": len(self.recent_context),
                    }

            return await asyncio.to_thread(_run)
        except Exception as e:
            return {"enabled": self.enabled, "neo4j": "error", "error": str(e)}

    async def close(self) -> None:
        """关闭连接"""
        if self._neo4j_driver:
            # FIX: GraphDatabase.driver 返回同步 driver；close() 不是 awaitable。
            await asyncio.to_thread(self._neo4j_driver.close)
            self._neo4j_driver = None
            self._neo4j_initialized = False


# 全局实例
_grag_instance: Optional[GRAGMemoryManager] = None


def get_grag_memory() -> GRAGMemoryManager:
    """获取 GRAG 记忆系统全局实例"""
    global _grag_instance
    if _grag_instance is None:
        _grag_instance = GRAGMemoryManager.get_instance()
    return _grag_instance


async def initialize_grag(config: Optional[Dict] = None) -> GRAGMemoryManager:
    """初始化 GRAG 记忆系统（便捷函数）"""
    global _grag_instance
    if _grag_instance is None:
        _grag_instance = GRAGMemoryManager.get_instance(config)
    await _grag_instance.initialize()
    return _grag_instance


# 使用示例
if __name__ == "__main__":

    async def main():
        # 初始化
        grag = await initialize_grag()

        # 添加对话
        await grag.add_conversation_memory(
            user_input="我喜欢看电影，尤其是科幻电影",
            ai_response="科幻电影确实很有想象力。你喜欢哪部？",
        )

        # 查询
        results = await grag.query_by_keywords(["电影"])
        print(f"查询结果: {results}")

        # 统计
        stats = await grag.get_stats()
        print(f"统计: {stats}")

        # 关闭
        await grag.close()

    asyncio.run(main())

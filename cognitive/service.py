"""认知记忆服务

借鉴 Undefined 的 cognitive/service.py 门面模式：
- 聚合 job_queue, vector_store, profile_storage
- 提供 enqueue / search / build_context 统一入口
"""

from __future__ import annotations

import logging
import time
from typing import Any, Callable

from cognitive.job_queue import JobQueue
from cognitive.vector_store import CognitiveVectorStore
from cognitive.profile_storage import ProfileStorage

logger = logging.getLogger(__name__)


class CognitiveService:
    """认知记忆服务门面

    用法:
        svc = CognitiveService(config)
        await svc.initialize()

        # 记录观察
        await svc.record_observation(group_id=123, user_id=456, text="佳喜欢咖啡")

        # 检索上下文
        context = await svc.build_context(group_id=123, user_id=456, query="咖啡")

        # 搜索事件
        events = await svc.search_events(query="咖啡", top_k=5)
    """

    def __init__(
        self,
        vector_store: CognitiveVectorStore,
        job_queue: JobQueue,
        profile_storage: ProfileStorage,
        get_embedding: Callable[[str], list[float]] | None = None,
        top_k: int = 5,
        enable_rerank: bool = True,
        time_decay_enabled: bool = True,
        time_decay_half_life_days: float = 14.0,
        enable_mmr: bool = True,
    ) -> None:
        self.vector_store = vector_store
        self.job_queue = job_queue
        self.profile_storage = profile_storage
        self._get_embedding = get_embedding or self._default_embedding
        self.top_k = top_k
        self.enable_rerank = enable_rerank
        self.time_decay_enabled = time_decay_enabled
        self.time_decay_half_life_days = time_decay_half_life_days
        self.enable_mmr = enable_mmr

    @classmethod
    def from_config(
        cls,
        job_queue: "JobQueue" = None,
        vector_store: "CognitiveVectorStore" = None,
        profile_storage: "ProfileStorage" = None,
        get_embedding=None,
    ) -> "CognitiveService":
        from config.config_utils import get_cognitive_config

        cfg = get_cognitive_config()
        retrieval = cfg.get("retrieval", {})
        time_decay = cfg.get("time_decay", {})

        return cls(
            vector_store=vector_store,
            job_queue=job_queue,
            profile_storage=profile_storage,
            get_embedding=get_embedding,
            top_k=retrieval.get("auto_top_k", 5),
            enable_rerank=retrieval.get("enable_rerank", True),
            time_decay_enabled=time_decay.get("enabled", True),
            time_decay_half_life_days=time_decay.get("half_life_days_auto", 14.0),
            enable_mmr=retrieval.get("enable_mmr", True),
        )

    async def initialize(self) -> None:
        """初始化向量存储和恢复过期任务"""
        await self.vector_store.initialize()
        await self.job_queue.recover_stale()

    def _default_embedding(self, text: str) -> list[float]:
        """默认嵌入 (需外部注入实际嵌入模型)"""
        logger.warning("[Cognitive] 未注入嵌入模型，使用零向量")
        return [0.0] * 768

    # ========================================================================
    # 事件记录
    # ========================================================================

    async def record_observation(
        self,
        text: str,
        group_id: int | None = None,
        user_id: int | None = None,
        sender_id: int | None = None,
        request_id: str = "",
        source_type: str = "chat",
        importance: float = 0.5,
    ) -> str:
        """记录一条观察，投递到后台史官异步处理"""
        job_id = f"{request_id or 'direct'}_{int(time.time() * 1000)}"
        job_data = {
            "job_id": job_id,
            "type": "observation",
            "text": text,
            "group_id": group_id,
            "user_id": user_id,
            "sender_id": sender_id,
            "request_id": request_id,
            "source_type": source_type,
            "importance": importance,
            "timestamp": time.time(),
            "_retry_count": 0,
        }
        await self.job_queue.enqueue(job_data)
        logger.debug("[Cognitive] 观察已入队: %s", job_id)
        return job_id

    async def add_event_directly(
        self,
        event_id: str,
        text: str,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """直接添加向量事件 (跳过史官队列)"""
        embedding = self._get_embedding(text)
        meta = metadata or {}
        meta["timestamp"] = meta.get("timestamp", time.time())
        await self.vector_store.add_event(
            event_id=event_id,
            text=text,
            embedding=embedding,
            metadata=meta,
        )

    # ========================================================================
    # 上下文构建
    # ========================================================================

    async def build_context(
        self,
        query: str = "",
        group_id: int | None = None,
        user_id: int | None = None,
        include_profile: bool = True,
        include_events: bool = True,
        event_top_k: int = 5,
    ) -> str:
        """构建认知记忆上下文 (XML 块)，注入到 AI 提示词中"""
        parts: list[str] = []

        query_embedding = (
            self._get_embedding(query)
            if query
            else self._get_embedding(f"group:{group_id} user:{user_id}")
        )

        # 侧写
        if include_profile:
            profile_text = await self._build_profile_context(group_id, user_id)
            if profile_text:
                parts.append(profile_text)

        # 事件
        if include_events:
            event_text = await self._build_event_context(
                query_embedding, group_id, user_id, event_top_k
            )
            if event_text:
                parts.append(event_text)

        if not parts:
            return ""

        return "<cognitive_memory>\n" + "\n".join(parts) + "\n</cognitive_memory>"

    async def _build_profile_context(
        self, group_id: int | None, user_id: int | None
    ) -> str:
        profile_parts = []
        if group_id:
            gp = await self.profile_storage.read_profile("group", group_id)
            if gp and gp.get("_body"):
                profile_parts.append(f"<!-- 群 {group_id} 侧写 -->\n{gp['_body']}")
        if user_id:
            up = await self.profile_storage.read_profile("user", user_id)
            if up and up.get("_body"):
                profile_parts.append(f"<!-- 用户 {user_id} 侧写 -->\n{up['_body']}")
        if not profile_parts:
            return ""
        return "<profiles>\n" + "\n---\n".join(profile_parts) + "\n</profiles>"

    async def _build_event_context(
        self,
        query_embedding: list[float],
        group_id: int | None,
        user_id: int | None,
        top_k: int,
    ) -> str:
        where: dict[str, Any] | None = None
        if group_id and user_id:
            where = {
                "$or": [
                    {"group_id": str(group_id)},
                    {"user_id": str(user_id)},
                ]
            }
        elif group_id:
            where = {"group_id": str(group_id)}
        elif user_id:
            where = {"user_id": str(user_id)}

        events = await self.vector_store.query_events(
            query_embedding=query_embedding,
            top_k=top_k,
            where=where,
            enable_rerank=self.enable_rerank,
            enable_time_decay=self.time_decay_enabled,
            time_decay_half_life_days=self.time_decay_half_life_days,
            enable_mmr=self.enable_mmr,
        )

        if not events:
            return ""

        lines = ["<events>"]
        for ev in events:
            meta = ev.get("metadata", {})
            ts = meta.get("timestamp", 0)
            ts_str = (
                time.strftime("%Y-%m-%d %H:%M", time.localtime(ts))
                if ts
                else "未知时间"
            )
            lines.append(
                f"- [{ts_str}] {ev.get('text', '')} (score={ev.get('score', 0):.3f})"
            )
        lines.append("</events>")
        return "\n".join(lines)

    # ========================================================================
    # 搜索
    # ========================================================================

    async def search_events(
        self,
        query: str,
        top_k: int = 10,
        group_id: int | None = None,
        user_id: int | None = None,
    ) -> list[dict[str, Any]]:
        """搜索相关认知事件"""
        query_embedding = self._get_embedding(query)
        where: dict[str, Any] | None = None
        if group_id:
            where = {"group_id": str(group_id)}
        elif user_id:
            where = {"user_id": str(user_id)}

        return await self.vector_store.query_events(
            query_embedding=query_embedding,
            top_k=top_k,
            where=where,
            enable_rerank=self.enable_rerank,
            enable_time_decay=self.time_decay_enabled,
            time_decay_half_life_days=self.time_decay_half_life_days,
            enable_mmr=self.enable_mmr,
        )

    async def search_profiles(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """搜索用户/群侧写"""
        query_embedding = self._get_embedding(query)
        return await self.vector_store.query_profiles(
            query_embedding=query_embedding, top_k=top_k
        )

    async def update_profile(
        self,
        entity_type: str,
        entity_id: int,
        profile_data: dict[str, Any],
        body: str,
        embedding: list[float] | None = None,
    ) -> None:
        """更新侧写档案 + 向量索引"""
        await self.profile_storage.write_profile(
            entity_type, entity_id, profile_data, body
        )
        if embedding is None:
            embedding = self._get_embedding(body)
        await self.vector_store.upsert_profile(
            profile_id=f"{entity_type}:{entity_id}",
            text=body,
            embedding=embedding,
            metadata={
                "entity_type": entity_type,
                "entity_id": str(entity_id),
                "display_name": profile_data.get("display_name", ""),
            },
        )

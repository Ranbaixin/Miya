"""认知记忆 - ChromaDB 向量存储

借鉴 Undefined 的 vector_store.py 设计：
- 双 Collection (events + profiles)
- MMR (Maximal Marginal Relevance) 多样性去重
- 时间衰减加权
- 查询向量缓存
"""

from __future__ import annotations

import asyncio
import logging
import math
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

try:
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    HAS_CHROMADB = True
except ImportError:
    HAS_CHROMADB = False
    chromadb = None  # type: ignore


class CognitiveVectorStore:
    """认知记忆向量存储

    特性:
        - 双 Collection 设计 (events / profiles)
        - 查询向量缓存 (TTL=60s, LRU=256)
        - 检索管线: 向量召回 → 重排(可选) → 时间衰减(可选) → MMR多样性(可选)
    """

    def __init__(
        self,
        persist_directory: str | Path = "data/cognitive/chromadb",
        collection_prefix: str = "miya_cognitive",
    ) -> None:
        if not HAS_CHROMADB:
            raise ImportError("chromadb 未安装，请运行: pip install chromadb")

        self.persist_directory = str(persist_directory)
        self.collection_prefix = collection_prefix
        self._client: Any = None
        self._events_collection: Any = None
        self._profiles_collection: Any = None
        self._embedding_cache: dict[str, tuple[list[float], float]] = {}
        self._cache_max_size = 256
        self._cache_ttl = 60.0
        self._cache_lock = asyncio.Lock()

    async def initialize(self) -> None:
        """初始化 ChromaDB 连接和 Collection"""
        await asyncio.to_thread(self._initialize_sync)

    def _initialize_sync(self) -> None:
        Path(self.persist_directory).mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(
            path=self.persist_directory,
            settings=ChromaSettings(anonymized_telemetry=False),
        )

        events_name = f"{self.collection_prefix}_events"
        profiles_name = f"{self.collection_prefix}_profiles"

        try:
            self._events_collection = self._client.get_collection(name=events_name)
        except Exception:
            self._events_collection = self._client.create_collection(
                name=events_name,
                metadata={"hnsw:space": "cosine"},
            )

        try:
            self._profiles_collection = self._client.get_collection(name=profiles_name)
        except Exception:
            self._profiles_collection = self._client.create_collection(
                name=profiles_name,
                metadata={"hnsw:space": "cosine"},
            )

    # ========================================================================
    # 事件 CRUD
    # ========================================================================

    async def add_event(
        self,
        event_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加认知记忆事件"""
        meta = self._sanitize_metadata(metadata or {})
        meta["text"] = text
        await asyncio.to_thread(
            self._events_collection.add,
            ids=[event_id],
            embeddings=[embedding],
            metadatas=[meta],
        )

    async def update_event(
        self,
        event_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """更新已有事件"""
        meta = self._sanitize_metadata(metadata or {})
        meta["text"] = text
        await asyncio.to_thread(
            self._events_collection.update,
            ids=[event_id],
            embeddings=[embedding],
            metadatas=[meta],
        )

    async def delete_event(self, event_id: str) -> None:
        """删除事件"""
        await asyncio.to_thread(self._events_collection.delete, ids=[event_id])

    async def query_events(
        self,
        query_embedding: list[float],
        top_k: int = 10,
        where: dict[str, Any] | None = None,
        enable_rerank: bool = True,
        enable_time_decay: bool = True,
        time_decay_half_life_days: float = 14.0,
        time_decay_boost: float = 0.2,
        time_decay_min_similarity: float = 0.35,
        enable_mmr: bool = True,
        mmr_lambda: float = 0.5,
    ) -> list[dict[str, Any]]:
        """检索相关事件

        管线: 向量召回 → 重排 → 时间衰减 → MMR多样性
        """
        n_results = top_k * 3 if (enable_rerank or enable_mmr) else top_k
        results = await asyncio.to_thread(
            self._query_events_sync,
            query_embedding,
            n_results,
            where,
        )

        if not results:
            return []

        # 时间衰减
        if enable_time_decay:
            results = self._apply_time_decay(
                results,
                half_life_days=time_decay_half_life_days,
                boost=time_decay_boost,
                min_similarity=time_decay_min_similarity,
            )

        # 按分数排序
        results.sort(key=lambda x: x.get("score", 0.0), reverse=True)

        # MMR 多样性去重
        if enable_mmr and len(results) > top_k:
            results = self._mmr_select(
                query_embedding, results, top_k, lambda_param=mmr_lambda
            )

        return results[:top_k]

    def _query_events_sync(
        self,
        query_embedding: list[float],
        n_results: int,
        where: dict[str, Any] | None,
    ) -> list[dict[str, Any]]:
        try:
            result = self._events_collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=where,
                include=["embeddings", "metadatas", "distances"],
            )
        except Exception:
            logger.debug("向量查询失败", exc_info=True)
            return []

        items = []
        for i in range(len(result.get("ids", [[]])[0])):
            distance = result["distances"][0][i]
            similarity = 1.0 - distance  # cosine distance → similarity
            metadata = result["metadatas"][0][i]
            items.append(
                {
                    "id": result["ids"][0][i],
                    "text": metadata.get("text", ""),
                    "metadata": {k: v for k, v in metadata.items() if k != "text"},
                    "similarity": similarity,
                    "score": similarity,
                    "embedding": result["embeddings"][0][i],
                }
            )
        return items

    def _apply_time_decay(
        self,
        items: list[dict[str, Any]],
        half_life_days: float,
        boost: float,
        min_similarity: float,
    ) -> list[dict[str, Any]]:
        """时间衰减: score *= (1 + boost * decay)"""
        half_life_seconds = half_life_days * 86400
        now = time.time()
        for item in items:
            similarity = item["similarity"]
            if similarity < min_similarity:
                continue
            timestamp = item.get("metadata", {}).get("timestamp", 0)
            age_seconds = max(0, now - float(timestamp))
            decay = 0.5 ** (age_seconds / half_life_seconds)
            item["score"] = similarity * (1.0 + boost * decay)
        return items

    def _mmr_select(
        self,
        query_embedding: list[float],
        items: list[dict[str, Any]],
        top_k: int,
        lambda_param: float = 0.5,
    ) -> list[dict[str, Any]]:
        """MMR (Maximal Marginal Relevance) 多样性选择"""
        if len(items) <= top_k:
            return items

        selected: list[dict[str, Any]] = []
        remaining = list(items)

        while len(selected) < top_k and remaining:
            best_item = None
            best_score = float("-inf")
            for item in remaining:
                query_sim = item["score"]  # 与查询的相似度
                max_sel_sim = 0.0
                if selected:
                    for sel in selected:
                        sim = self._cosine_similarity(
                            query_embedding, sel.get("embedding", [])
                        )
                        if sim is not None:
                            max_sel_sim = max(max_sel_sim, sim)
                mmr_score = (
                    lambda_param * query_sim - (1.0 - lambda_param) * max_sel_sim
                )
                if mmr_score > best_score:
                    best_score = mmr_score
                    best_item = item
            if best_item:
                selected.append(best_item)
                remaining.remove(best_item)
            else:
                break

        return selected

    def _cosine_similarity(self, a: list[float], b: list[float]) -> float | None:
        if not a or not b or len(a) != len(b):
            return None
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 0.0
        return dot / (na * nb)

    # ========================================================================
    # 侧写 Profile CRUD
    # ========================================================================

    async def upsert_profile(
        self,
        profile_id: str,
        text: str,
        embedding: list[float],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """添加或更新用户/群侧写"""
        meta = self._sanitize_metadata(metadata or {})
        meta["text"] = text[:8000]  # 限制侧写文本长度
        await asyncio.to_thread(
            self._profiles_collection.upsert,
            ids=[profile_id],
            embeddings=[embedding],
            metadatas=[meta],
        )

    async def delete_profile(self, profile_id: str) -> None:
        """删除侧写"""
        await asyncio.to_thread(self._profiles_collection.delete, ids=[profile_id])

    async def query_profiles(
        self,
        query_embedding: list[float],
        top_k: int = 5,
        where: dict[str, Any] | None = None,
    ) -> list[dict[str, Any]]:
        """检索相关侧写"""
        try:
            result = await asyncio.to_thread(
                self._profiles_collection.query,
                query_embeddings=[query_embedding],
                n_results=top_k,
                where=where,
                include=["metadatas", "distances"],
            )
        except Exception:
            logger.debug("侧写查询失败", exc_info=True)
            return []

        items = []
        for i in range(len(result.get("ids", [[]])[0])):
            distance = result["distances"][0][i]
            metadata = result["metadatas"][0][i]
            items.append(
                {
                    "id": result["ids"][0][i],
                    "text": metadata.get("text", ""),
                    "metadata": {k: v for k, v in metadata.items() if k != "text"},
                    "similarity": 1.0 - distance,
                }
            )
        return items

    # ========================================================================
    # 查询向量缓存
    # ========================================================================

    async def get_cached_embedding(self, text: str) -> list[float] | None:
        """获取缓存的查询向量"""
        async with self._cache_lock:
            if text in self._embedding_cache:
                emb, cached_time = self._embedding_cache[text]
                if time.time() - cached_time < self._cache_ttl:
                    return emb
                del self._embedding_cache[text]
            return None

    async def cache_embedding(self, text: str, embedding: list[float]) -> None:
        """缓存查询向量"""
        async with self._cache_lock:
            if len(self._embedding_cache) >= self._cache_max_size:
                oldest = min(
                    self._embedding_cache.items(),
                    key=lambda x: x[1][1],
                )
                del self._embedding_cache[oldest[0]]
            self._embedding_cache[text] = (embedding, time.time())

    @staticmethod
    def _sanitize_metadata(
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """清洗元数据，确保 ChromaDB 兼容"""
        safe: dict[str, Any] = {}
        for k, v in metadata.items():
            if isinstance(v, (str, int, float, bool)):
                safe[k] = v
            elif isinstance(v, list):
                safe[k] = [x for x in v if isinstance(x, (str, int, float))]
        return safe

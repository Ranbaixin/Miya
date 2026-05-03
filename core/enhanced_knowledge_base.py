"""
知识库增强模块

整合 Miya Memory 和 AstrBot KnowledgeBase
提供高级检索能力
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class RetrievalMethod(Enum):
    """检索方法"""

    VECTOR = "vector"
    SPARSE = "sparse"
    HYBRID = "hybrid"
    SEMANTIC = "semantic"


@dataclass
class SearchResult:
    """搜索结果"""

    content: str
    source: str
    score: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class KnowledgeBaseConfig:
    """知识库配置"""

    default_method: RetrievalMethod = RetrievalMethod.HYBRID
    top_k: int = 5
    similarity_threshold: float = 0.7
    enable_rerank: bool = True
    max_chunks: int = 10


class EnhancedKnowledgeBase:
    """
    增强知识库

    功能：
    - 双知识库整合
    - 高级检索方法
    - 智能重排序
    - 结果融合
    """

    def __init__(self):
        self._miya_kb = None
        self._astrbot_kb = None
        self._config = KnowledgeBaseConfig()
        self._initialized = False

    async def initialize(self):
        """初始化知识库"""
        logger.info("[EnhancedKnowledgeBase] 初始化...")

        await self._init_miya_kb()
        await self._init_astrbot_kb()

        self._initialized = True
        logger.info("[EnhancedKnowledgeBase] 初始化完成")

    async def _init_miya_kb(self):
        """初始化Miya知识库"""
        try:
            from memory.unified_memory import UnifiedMemory

            self._miya_kb = UnifiedMemory()
            logger.info("[EnhancedKnowledgeBase] Miya知识库已加载")
        except Exception as e:
            logger.info(f"[EnhancedKnowledgeBase] Miya知识库加载失败: {e}"))

    async def _init_astrbot_kb(self):
        """初始化AstrBot知识库"""
        try:
            from core.knowledge_base_astrbot.kb_mgr import KnowledgeBaseManager

            self._astrbot_kb = KnowledgeBaseManager()
            logger.info("[EnhancedKnowledgeBase] AstrBot知识库已加载")
        except Exception as e:
            logger.info(f"[EnhancedKnowledgeBase] AstrBot知识库加载失败: {e}"))

    async def search(
        self,
        query: str,
        method: RetrievalMethod = None,
        top_k: int = None,
        sources: Optional[List[str]] = None,
    ) -> List[SearchResult]:
        """搜索知识库"""
        if not self._initialized:
            return []

        method = method or self._config.default_method
        top_k = top_k or self._config.top_k

        results = []

        if not sources or "miya" in sources:
            miya_results = await self._search_miya(query, method, top_k)
            results.extend(miya_results)

        if not sources or "astrbot" in sources:
            astrbot_results = await self._search_astrbot(query, method, top_k)
            results.extend(astrbot_results)

        if self._config.enable_rerank:
            results = await self._rerank_results(query, results)

        results = sorted(results, key=lambda r: r.score, reverse=True)[:top_k]

        return results

    async def _search_miya(
        self, query: str, method: RetrievalMethod, top_k: int
    ) -> List[SearchResult]:
        """搜索Miya知识库"""
        try:
            if self._miya_kb and hasattr(self._miya_kb, "search"):
                results = await self._miya_kb.search(query, top_k)
                return [
                    SearchResult(
                        content=r.get("content", ""),
                        source="miya",
                        score=r.get("score", 0.0),
                        metadata=r.get("metadata", {}),
                    )
                    for r in results
                ]
        except Exception as e:
            logger.warning(f"[EnhancedKnowledgeBase] Miya搜索失败: {e}")

        return []

    async def _search_astrbot(
        self, query: str, method: RetrievalMethod, top_k: int
    ) -> List[SearchResult]:
        """搜索AstrBot知识库"""
        try:
            if self._astrbot_kb:
                if method == RetrievalMethod.VECTOR:
                    return await self._vector_search_astrbot(query, top_k)
                elif method == RetrievalMethod.SPARSE:
                    return await self._sparse_search_astrbot(query, top_k)
                elif method == RetrievalMethod.HYBRID:
                    return await self._hybrid_search_astrbot(query, top_k)
        except Exception as e:
            logger.warning(f"[EnhancedKnowledgeBase] AstrBot搜索失败: {e}")

        return []

    async def _vector_search_astrbot(
        self, query: str, top_k: int
    ) -> List[SearchResult]:
        """向量搜索"""
        return []

    async def _sparse_search_astrbot(
        self, query: str, top_k: int
    ) -> List[SearchResult]:
        """稀疏检索"""
        return []

    async def _hybrid_search_astrbot(
        self, query: str, top_k: int
    ) -> List[SearchResult]:
        """混合搜索"""
        vector_results = await self._vector_search_astrbot(query, top_k)
        sparse_results = await self._sparse_search_astrbot(query, top_k)

        fused = self._fuse_results(vector_results, sparse_results)
        return fused[:top_k]

    def _fuse_results(
        self, results1: List[SearchResult], results2: List[SearchResult]
    ) -> List[SearchResult]:
        """融合结果"""
        seen = {}

        for r in results1 + results2:
            key = r.content[:100]
            if key not in seen:
                seen[key] = r
            else:
                if r.score > seen[key].score:
                    seen[key] = r

        return list(seen.values())

    async def _rerank_results(
        self, query: str, results: List[SearchResult]
    ) -> List[SearchResult]:
        """重排序结果"""
        try:
            if not results:
                return results

            query_terms = set(query.lower().split())

            for result in results:
                content_terms = set(result.content.lower().split())
                overlap = len(query_terms & content_terms)
                bonus = overlap / max(len(query_terms), 1)
                result.score = result.score * 0.7 + bonus * 0.3

            return results
        except Exception:
            return results

    async def add_document(
        self,
        content: str,
        source: str = "miya",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """添加文档"""
        try:
            if source == "miya" and self._miya_kb:
                if hasattr(self._miya_kb, "add"):
                    return await self._miya_kb.add(content, metadata)
            elif source == "astrbot" and self._astrbot_kb:
                if hasattr(self._astrbot_kb, "add_document"):
                    return await self._astrbot_kb.add_document(content, metadata)

            return {"success": False, "error": "知识库不可用"}
        except Exception as e:
            logger.error(f"[EnhancedKnowledgeBase] 添加文档失败: {e}")
            return {"success": False, "error": str(e)}

    async def delete_document(
        self, doc_id: str, source: str = "miya"
    ) -> Dict[str, Any]:
        """删除文档"""
        return {"success": True, "message": "删除功能待实现"}

    async def list_documents(
        self, source: Optional[str] = None, limit: int = 100
    ) -> List[Dict[str, Any]]:
        """列出文档"""
        docs = []

        if not source or source == "miya":
            if self._miya_kb and hasattr(self._miya_kb, "list_documents"):
                miya_docs = await self._miya_kb.list_documents(limit)
                docs.extend(miya_docs)

        if not source or source == "astrbot":
            if self._astrbot_kb:
                docs.append({"source": "astrbot", "count": "unknown"})

        return docs

    def set_config(self, config: KnowledgeBaseConfig):
        """设置配置"""
        self._config = config

    def get_config(self) -> KnowledgeBaseConfig:
        """获取配置"""
        return self._config


_enhanced_knowledge_base: Optional[EnhancedKnowledgeBase] = None


def get_enhanced_knowledge_base() -> EnhancedKnowledgeBase:
    """获取全局增强知识库"""
    global _enhanced_knowledge_base
    if _enhanced_knowledge_base is None:
        _enhanced_knowledge_base = EnhancedKnowledgeBase()
    return _enhanced_knowledge_base

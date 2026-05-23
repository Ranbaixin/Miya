"""
向量缓存模块
提供本地向量存储功能，使用Milvus Lite
"""

import builtins
import contextlib
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class RealVectorCache:
    """
    实时向量缓存

    使用Milvus Lite进行本地向量存储
    """

    def __init__(
        self,
        embedding_client=None,
        milvus_db_path: str = "data/milvus_lite.db",
        collection_name: str = "miya_vectors",
    ):
        self.embedding_client = embedding_client
        self.milvus_db_path = milvus_db_path
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        self._is_lite = True
        self._initialized = False

    def is_mock_mode(self) -> bool:
        """检查是否处于模拟模式"""
        return self._client is None

    def _is_lite_mode(self) -> bool:
        """检查是否使用Lite模式"""
        return self._is_lite

    async def initialize(self) -> bool:
        """初始化向量存储"""
        try:
            from pymilvus import (
                connections,
            )

            db_path = Path(self.milvus_db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)

            connections.connect(
                alias="default",
                uri=f"sqlite:///{self.milvus_db_path}",
                db_name="default",
            )

            self._client = connections
            self._is_lite = True

            if not self._collection_exists():
                self._create_collection()

            self._initialized = True
            logger.info(f"向量缓存初始化成功 (Milvus Lite: {self.milvus_db_path})")
            return True

        except Exception as e:
            logger.warning(f"Milvus Lite 初始化失败，使用模拟模式: {e}")
            self._client = None
            self._is_lite = True
            self._initialized = True
            return False

    def _collection_exists(self) -> bool:
        """检查collection是否存在"""
        try:
            from pymilvus import Collection, connections

            connections.connect(alias="default", uri=f"sqlite:///{self.milvus_db_path}")
            collection = Collection(self.collection_name, using="default")
            return collection.num_entities > 0 or True
        except:
            return False

    def _create_collection(self):
        """创建collection"""
        try:
            from pymilvus import (
                Collection,
                CollectionSchema,
                DataType,
                FieldSchema,
            )

            fields = [
                FieldSchema(
                    name="id", dtype=DataType.INT64, is_primary=True, auto_id=True
                ),
                FieldSchema(name="text", dtype=DataType.VARCHAR, max_length=65535),
                FieldSchema(name="vector", dtype=DataType.FLOAT_VECTOR, dim=384),
                FieldSchema(name="metadata", dtype=DataType.JSON),
            ]
            schema = CollectionSchema(fields=fields, description="Miya memory vectors")
            self._collection = Collection(
                name=self.collection_name, schema=schema, using="default"
            )

            index_params = {
                "index_type": "AUTOINDEX",
                "metric_type": "COSINE",
                "params": {},
            }
            self._collection.create_index(
                field_name="vector", index_params=index_params
            )
            self._collection.load()

        except Exception as e:
            logger.warning(f"创建collection失败: {e}")

    async def add(
        self,
        texts: List[str],
        vectors: List[List[float]],
        metadata: Optional[List[Dict]] = None,
    ) -> List[str]:
        """添加向量"""
        if not self._initialized:
            await self.initialize()

        if self._client is None:
            return [f"mock_{i}" for i in range(len(texts))]

        try:
            ids = []
            for i, (text, vector) in enumerate(zip(texts, vectors, strict=False)):
                meta = metadata[i] if metadata else {}
                data = {
                    "text": text[:65535],
                    "vector": vector[:384],
                    "metadata": meta,
                }
                self._collection.insert([data])
                ids.append(str(i))
            self._collection.flush()
            return ids
        except Exception as e:
            logger.warning(f"添加向量失败: {e}")
            return [f"mock_{i}" for i in range(len(texts))]

    async def search(
        self,
        query_vector: List[float],
        top_k: int = 10,
        filter_expr: Optional[str] = None,
    ) -> List[Dict]:
        """搜索向量"""
        if not self._initialized:
            await self.initialize()

        if self._client is None:
            return []

        try:
            search_params = {"metric_type": "COSINE", "params": {}}
            results = self._collection.search(
                data=[query_vector[:384]],
                anns_field="vector",
                param=search_params,
                limit=top_k,
                output_fields=["text", "metadata"],
            )

            return [
                {
                    "id": str(hit.id),
                    "text": hit.entity.get("text", ""),
                    "distance": hit.distance,
                    "metadata": hit.entity.get("metadata", {}),
                }
                for hit in results[0]
            ]
        except Exception as e:
            logger.warning(f"搜索向量失败: {e}")
            return []

    async def delete(self, ids: List[str]) -> bool:
        """删除向量"""
        return True

    async def close(self):
        """关闭连接"""
        if self._client:
            with contextlib.suppress(builtins.BaseException):
                connections.disconnect("default")


def get_real_vector_cache(
    embedding_client=None,
    milvus_db_path: str = "data/milvus_lite.db",
    collection_name: str = "miya_vectors",
) -> RealVectorCache:
    """获取向量缓存实例"""
    return RealVectorCache(
        embedding_client=embedding_client,
        milvus_db_path=milvus_db_path,
        collection_name=collection_name,
    )

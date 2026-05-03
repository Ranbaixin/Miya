"""
弥娅知识库集成模块

集成 AstrBot 的 RAG 能力到弥娅系统。
提供文档解析、分块、检索等功能。
"""

import logging
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent
KNOWLEDGE_DIR = PROJECT_ROOT / "knowledge"
DATA_DIR = PROJECT_ROOT / "data" / "knowledge"


@dataclass
class Document:
    """文档"""

    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class Chunk:
    """文档块"""

    chunk_id: str
    doc_id: str
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None


@dataclass
class SearchResult:
    """搜索结果"""

    chunk: Chunk
    score: float
    rank: int = 0


class BaseParser(ABC):
    """解析器基类"""

    @abstractmethod
    async def parse(self, file_path: Path) -> List[Document]:
        """解析文件"""
        pass

    @abstractmethod
    def supports(self, file_path: Path) -> bool:
        """检查是否支持该文件类型"""
        pass


class TextParser(BaseParser):
    """文本解析器"""

    async def parse(self, file_path: Path) -> List[Document]:
        """解析文本文件"""
        try:
            content = file_path.read_text(encoding="utf-8")
            return [
                Document(
                    doc_id=file_path.stem,
                    content=content,
                    metadata={"source": str(file_path), "type": "text"},
                )
            ]
        except Exception as e:
            logger.error(f"解析文本文件失败 {file_path}: {e}")
            return []

    def supports(self, file_path: Path) -> bool:
        """检查是否支持该文件类型"""
        return file_path.suffix.lower() in [".txt", ".md", ".markdown"]


class BaseChunker(ABC):
    """分块器基类"""

    @abstractmethod
    async def chunk(
        self, document: Document, chunk_size: int = 1000, overlap: int = 200
    ) -> List[Chunk]:
        """将文档分块"""
        pass


class RecursiveChunker(BaseChunker):
    """递归字符分块器"""

    async def chunk(
        self, document: Document, chunk_size: int = 1000, overlap: int = 200
    ) -> List[Chunk]:
        """将文档分块"""
        chunks = []
        content = document.content

        # 简单的分块逻辑
        start = 0
        chunk_id = 0

        while start < len(content):
            end = start + chunk_size

            # 提取块
            chunk_content = content[start:end]

            # 创建块
            chunks.append(
                Chunk(
                    chunk_id=f"{document.doc_id}_chunk_{chunk_id}",
                    doc_id=document.doc_id,
                    content=chunk_content,
                    metadata={**document.metadata, "chunk_index": chunk_id},
                )
            )

            # 移动到下一个位置
            start = end - overlap
            chunk_id += 1

        return chunks


class BaseRetriever(ABC):
    """检索器基类"""

    @abstractmethod
    async def index(self, chunks: List[Chunk]) -> bool:
        """索引块"""
        pass

    @abstractmethod
    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """搜索"""
        pass


class SimpleRetriever(BaseRetriever):
    """简单检索器（基于关键词匹配）"""

    def __init__(self):
        self._index: Dict[str, Chunk] = {}

    async def index(self, chunks: List[Chunk]) -> bool:
        """索引块"""
        for chunk in chunks:
            self._index[chunk.chunk_id] = chunk
        return True

    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """搜索"""
        results = []
        query_lower = query.lower()

        for chunk_id, chunk in self._index.items():
            # 简单的关键词匹配
            if query_lower in chunk.content.lower():
                score = 1.0
                results.append(SearchResult(chunk=chunk, score=score))

        # 按分数排序
        results.sort(key=lambda x: x.score, reverse=True)

        # 返回前 top_k 个结果
        return results[:top_k]


class KnowledgeBase:
    """知识库"""

    def __init__(self, kb_id: str, name: str, description: str = ""):
        self.kb_id = kb_id
        self.name = name
        self.description = description
        self.documents: Dict[str, Document] = {}
        self.chunks: Dict[str, Chunk] = {}
        self.parser = TextParser()
        self.chunker = RecursiveChunker()
        self.retriever = SimpleRetriever()

    async def add_document(self, file_path: Path) -> bool:
        """添加文档"""
        try:
            # 解析文档
            documents = await self.parser.parse(file_path)
            if not documents:
                return False

            # 添加文档
            for doc in documents:
                self.documents[doc.doc_id] = doc

                # 分块
                chunks = await self.chunker.chunk(doc)

                # 添加块
                for chunk in chunks:
                    self.chunks[chunk.chunk_id] = chunk

                # 索引
                await self.retriever.index(chunks)

            logger.info(f"添加文档成功: {file_path}")
            return True

        except Exception as e:
            logger.error(f"添加文档失败 {file_path}: {e}")
            return False

    async def add_text(self, text: str, doc_id: str = None) -> bool:
        """添加文本"""
        try:
            # 创建文档
            doc = Document(
                doc_id=doc_id or f"text_{len(self.documents)}",
                content=text,
                metadata={"source": "text", "type": "text"},
            )

            # 添加文档
            self.documents[doc.doc_id] = doc

            # 分块
            chunks = await self.chunker.chunk(doc)

            # 添加块
            for chunk in chunks:
                self.chunks[chunk.chunk_id] = chunk

            # 索引
            await self.retriever.index(chunks)

            logger.info(f"添加文本成功: {doc.doc_id}")
            return True

        except Exception as e:
            logger.error(f"添加文本失败: {e}")
            return False

    async def search(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """搜索"""
        return await self.retriever.search(query, top_k)

    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "kb_id": self.kb_id,
            "name": self.name,
            "documents": len(self.documents),
            "chunks": len(self.chunks),
        }


class KnowledgeBaseManager:
    """知识库管理器"""

    def __init__(self):
        self._knowledge_bases: Dict[str, KnowledgeBase] = {}
        self._data_dir = DATA_DIR
        self._data_dir.mkdir(parents=True, exist_ok=True)

    async def create_kb(self, name: str, description: str = "") -> KnowledgeBase:
        """创建知识库"""
        kb_id = f"kb_{len(self._knowledge_bases)}"
        kb = KnowledgeBase(kb_id, name, description)
        self._knowledge_bases[kb_id] = kb
        logger.info(f"创建知识库: {name} ({kb_id})")
        return kb

    async def get_kb(self, kb_id: str) -> Optional[KnowledgeBase]:
        """获取知识库"""
        return self._knowledge_bases.get(kb_id)

    async def list_kbs(self) -> List[Dict[str, Any]]:
        """列出所有知识库"""
        return [kb.get_stats() for kb in self._knowledge_bases.values()]

    async def delete_kb(self, kb_id: str) -> bool:
        """删除知识库"""
        if kb_id in self._knowledge_bases:
            del self._knowledge_bases[kb_id]
            logger.info(f"删除知识库: {kb_id}")
            return True
        return False

    async def search(
        self, kb_id: str, query: str, top_k: int = 10
    ) -> List[SearchResult]:
        """在指定知识库中搜索"""
        kb = await self.get_kb(kb_id)
        if not kb:
            return []
        return await kb.search(query, top_k)

    async def search_all(self, query: str, top_k: int = 10) -> List[SearchResult]:
        """在所有知识库中搜索"""
        all_results = []

        for kb in self._knowledge_bases.values():
            results = await kb.search(query, top_k)
            all_results.extend(results)

        # 按分数排序
        all_results.sort(key=lambda x: x.score, reverse=True)

        # 返回前 top_k 个结果
        return all_results[:top_k]


# 全局实例
_kb_manager: Optional[KnowledgeBaseManager] = None


def get_knowledge_base_manager() -> KnowledgeBaseManager:
    """获取全局知识库管理器"""
    global _kb_manager
    if _kb_manager is None:
        _kb_manager = KnowledgeBaseManager()
    return _kb_manager


# 导出
__all__ = [
    "Document",
    "Chunk",
    "SearchResult",
    "BaseParser",
    "TextParser",
    "BaseChunker",
    "RecursiveChunker",
    "BaseRetriever",
    "SimpleRetriever",
    "KnowledgeBase",
    "KnowledgeBaseManager",
    "get_knowledge_base_manager",
]

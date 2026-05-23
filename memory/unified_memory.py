"""
统一记忆系统 - 已迁移到新版MiyaMemoryCore
兼容旧接口
"""

import enum
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class MemoryCategory(enum.Enum):
    """记忆分类枚举"""

    IMPORTANT = "important"
    EMOTION = "emotion"
    CONVERSATION = "conversation"
    FACT = "fact"
    PERSONAL = "personal"


class UnifiedMemory:
    """
    统一记忆系统 - 兼容旧接口

    已迁移到 MiyaMemoryCore
    """

    def __init__(self, data_dir: str = "data/memory", config: Optional[Dict] = None):
        self.data_dir = Path(data_dir)
        self.config = config or {}
        self._core = None
        self._initialized = False

    async def initialize(self) -> bool:
        """初始化"""
        from memory import get_memory_core

        self._core = await get_memory_core(str(self.data_dir))
        self._initialized = True
        logger.info("统一记忆系统初始化成功")
        return True

    async def add_memory(self, content: str, user_id: str, **kwargs) -> str:
        """添加记忆"""
        from memory import store_important

        tags = kwargs.get("tags", [])
        return await store_important(content, user_id, tags=tags)

    async def search_memory(
        self, query: str, user_id: Optional[str] = None
    ) -> List[Dict]:
        """搜索记忆"""
        from memory import search_memory

        results = await search_memory(query, user_id=user_id)
        return [{"content": r.content, "tags": r.tags} for r in results]

    async def get_all(
        self, user_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """获取所有记忆"""
        from memory import get_user_memories

        results = await get_user_memories(user_id, limit=limit)
        return [{"content": r.content, "tags": r.tags} for r in results]

    async def add_short_term(
        self, content: str, user_id: str, ttl: int = 3600, **kwargs
    ) -> str:
        """添加短期记忆"""
        from memory import store_auto

        tags = kwargs.get("tags", [])
        return await store_auto(content, user_id, tags=tags)


_unified_memory_instance: Optional[UnifiedMemory] = None


def get_unified_memory(
    data_dir: str = "data/memory", config: Optional[Dict] = None
) -> UnifiedMemory:
    """获取统一记忆实例"""
    global _unified_memory_instance
    if _unified_memory_instance is None:
        _unified_memory_instance = UnifiedMemory(data_dir, config)
    return _unified_memory_instance


def init_unified_memory(
    data_dir: str = "data/memory", config: Optional[Dict] = None
) -> UnifiedMemory:
    """初始化统一记忆"""
    return get_unified_memory(data_dir, config)

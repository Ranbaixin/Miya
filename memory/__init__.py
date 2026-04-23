"""
================================================================
        弥娅统一记忆系统 (Miya Unified Memory System)
================================================================

这是弥娅的**唯一**记忆系统，所有代码必须使用此类。

使用示例：
```python
from memory import MiyaMemory

# 初始化
memory = await MiyaMemory.get_instance()

# 存储对话
await memory.store_dialogue("你好", role="user", user_id="123")

# 存储重要记忆
await memory.store_important("我喜欢唱歌", user_id="123", tags=["偏好"])

# 搜索
results = await memory.search("唱歌", user_id="123")

# 获取用户画像
profile = await memory.get_profile("123")
```

作者: 编程大师
================================================================
"""

from memory.core import (
    MiyaMemoryCore,
    get_memory_core,
    reset_memory_core,
    MemoryItem,
    MemoryQuery,
    MemoryLevel,
    MemoryPriority,
    MemorySource,
    MemoryBackend,
    JsonBackend,
)
from memory.cognitive_engine import CognitiveEngine, get_cognitive_engine

import logging
from typing import Dict, List, Optional, Any, Union
from pathlib import Path

logger = logging.getLogger(__name__)


# ==================== 便捷存储函数 ====================


async def store_dialogue(
    content: str,
    role: str,
    user_id: str,
    session_id: str,
    platform: str = "unknown",
    metadata: Optional[Dict] = None,
) -> str:
    """存储对话"""
    core = await get_memory_core()
    return await core.store(
        content=content,
        level=MemoryLevel.DIALOGUE,
        user_id=user_id,
        session_id=session_id,
        platform=platform,
        source=MemorySource.DIALOGUE,
        role=role,
        metadata=metadata,
    )


async def store_important(
    content: str,
    user_id: str,
    tags: List[str],
    priority: float = 0.7,
    metadata: Optional[Dict] = None,
) -> str:
    """存储重要记忆"""
    core = await get_memory_core()
    return await core.store(
        content=content,
        level=MemoryLevel.LONG_TERM,
        priority=priority,
        tags=tags,
        user_id=user_id,
        source=MemorySource.MANUAL,
        metadata=metadata,
    )


async def store_auto(
    content: str,
    user_id: str,
    tags: List[str],
    priority: float = 0.5,
    metadata: Optional[Dict] = None,
) -> str:
    """自动提取存储"""
    core = await get_memory_core()
    return await core.store(
        content=content,
        priority=priority,
        tags=tags,
        user_id=user_id,
        source=MemorySource.AUTO_EXTRACT,
        metadata=metadata,
    )


async def store_knowledge(
    subject: str,
    predicate: str,
    obj: str,
    context: str,
    user_id: str = "global",
    metadata: Optional[Dict] = None,
) -> str:
    """存储知识图谱"""
    core = await get_memory_core()
    return await core.store(
        content=context,
        level=MemoryLevel.KNOWLEDGE,
        user_id=user_id,
        source=MemorySource.SYSTEM,
        subject=subject,
        predicate=predicate,
        obj=obj,
        metadata=metadata,
    )


# ==================== 检索函数 ====================


async def search_memory(
    query: str,
    user_id: Optional[str] = None,
    tags: Optional[List[str]] = None,
    level: Optional[MemoryLevel] = None,
    limit: int = 20,
) -> List[MemoryItem]:
    """搜索记忆"""
    core = await get_memory_core()
    return await core.retrieve(
        query=query,
        user_id=user_id,
        tags=tags,
        level=level,
        limit=limit,
    )


async def get_user_memories(
    user_id: str,
    level: Optional[MemoryLevel] = None,
    limit: int = 20,
) -> List[MemoryItem]:
    """获取用户记忆"""
    core = await get_memory_core()
    return await core.search_by_user(user_id, level=level, limit=limit)


async def get_dialogue_history(
    session_id: str,
    platform: str = "unknown",
    limit: int = 50,
) -> List[MemoryItem]:
    """获取对话历史"""
    core = await get_memory_core()
    return await core.get_dialogue(session_id, platform=platform, limit=limit)


# ==================== 用户画像 ====================


async def get_user_profile(user_id: str) -> Dict:
    """获取用户画像"""
    core = await get_memory_core()
    return await core.get_user_profile(user_id)


# ==================== 管理函数 ====================


async def update_memory(
    memory_id: str,
    content: Optional[str] = None,
    tags: Optional[List[str]] = None,
    priority: Optional[float] = None,
    is_pinned: Optional[bool] = None,
) -> bool:
    """更新记忆"""
    core = await get_memory_core()
    return await core.update(memory_id, content, tags, priority, is_pinned)


async def delete_memory(memory_id: str) -> bool:
    """删除记忆"""
    core = await get_memory_core()
    return await core.delete(memory_id)


async def cleanup_expired() -> int:
    """清理过期记忆"""
    core = await get_memory_core()
    return await core.delete_expired()


# ==================== 统计 ====================


async def get_memory_stats() -> Dict:
    """获取统计"""
    core = await get_memory_core()
    return await core.get_statistics()


# ==================== 主类 (兼容旧接口) ====================


class MiyaMemory:
    """
    弥娅统一记忆系统主类

    此类是整个系统的唯一入口，兼容所有旧接口。
    """

    _instance: Optional["MiyaMemory"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._core: Optional[MiyaMemoryCore] = None
        self._initialized = True

    async def get_instance(
        cls,
        data_dir: Union[str, Path] = "data/memory",
    ) -> "MiyaMemory":
        """获取实例"""
        if cls._instance is None:
            cls._instance = cls()

        if cls._instance._core is None:
            cls._instance._core = await get_memory_core(
                data_dir=data_dir,
            )

        return cls._instance

    # 存储方法
    async def store(self, *args, **kwargs) -> str:
        return await self._core.store(*args, **kwargs)

    async def store_dialogue(self, *args, **kwargs) -> str:
        return await store_dialogue(*args, **kwargs)

    async def store_important(self, *args, **kwargs) -> str:
        return await store_important(*args, **kwargs)

    # 检索方法
    async def retrieve(self, *args, **kwargs) -> List[MemoryItem]:
        return await self._core.retrieve(*args, **kwargs)

    async def search(self, *args, **kwargs) -> List[MemoryItem]:
        return await search_memory(*args, **kwargs)

    async def get_user_profile(self, *args, **kwargs) -> Dict:
        return await get_user_profile(*args, **kwargs)

    # 管理方法
    async def update(self, *args, **kwargs) -> bool:
        return await update_memory(*args, **kwargs)

    async def delete(self, *args, **kwargs) -> bool:
        return await delete_memory(*args, **kwargs)

    async def get_statistics(self, *args, **kwargs) -> Dict:
        return await get_memory_stats(*args, **kwargs)


# ==================== 向后兼容 ====================


class MemoryAdapter:
    """
    旧系统适配器

    此类将新系统适配为旧接口，确保向后兼容。
    """

    def __init__(self):
        self._core: Optional[MiyaMemoryCore] = None

    async def initialize(self):
        """初始化"""
        self._core = await get_memory_core()
        return self

    @property
    def core(self) -> MiyaMemoryCore:
        if self._core is None:
            raise RuntimeError("MemoryAdapter 未初始化")
        return self._core

    # 兼容旧接口
    async def add_message(
        self, session_id: str, role: str, content: str, **kwargs
    ) -> str:
        """添加消息 (旧接口)"""
        user_id = kwargs.get("user_id", "unknown")
        platform = kwargs.get("platform", "qq")

        return await store_dialogue(
            content=content,
            role=role,
            user_id=user_id,
            session_id=session_id,
            platform=platform,
            metadata=kwargs,
        )

    async def get_history(
        self, session_id: str, limit: int = 20, **kwargs
    ) -> List[Dict]:
        """获取历史 (旧接口)"""
        platform = kwargs.get("platform", "unknown")
        memories = await get_dialogue_history(
            session_id, platform=platform, limit=limit
        )

        return [
            {
                "role": m.role,
                "content": m.content,
                "timestamp": m.created_at,
                "session_id": m.session_id,
            }
            for m in memories
        ]

    async def add_memory(
        self, fact: str, tags: Optional[List[str]] = None, **kwargs
    ) -> str:
        """添加记忆 (旧接口)"""
        user_id = kwargs.get("user_id", "global")
        return await store_important(fact, user_id, tags or [])

    async def search(self, keyword: str, limit: int = 20, **kwargs) -> List[Dict]:
        """搜索 (旧接口)"""
        user_id = kwargs.get("user_id")
        memories = await search_memory(keyword, user_id=user_id, limit=limit)

        return [
            {
                "id": m.id,
                "content": m.content,
                "tags": m.tags,
                "priority": m.priority,
                "created_at": m.created_at,
                "level": m.level.value,
            }
            for m in memories
        ]

    async def get_all(
        self, user_id: Optional[str] = None, limit: int = 100
    ) -> List[Dict]:
        """获取所有 (旧接口)"""
        memories = await get_user_memories(user_id, limit=limit)

        return [
            {
                "id": m.id,
                "content": m.content,
                "tags": m.tags,
                "created_at": m.created_at,
            }
            for m in memories
        ]

    async def get_statistics(self) -> Dict:
        """获取统计 (旧接口)"""
        return await get_memory_stats()


# ==================== 全局单例 ====================

_memory_adapter: Optional[MemoryAdapter] = None


async def get_memory_adapter() -> MemoryAdapter:
    """获取适配器实例"""
    global _memory_adapter

    if _memory_adapter is None:
        _memory_adapter = MemoryAdapter()
        await _memory_adapter.initialize()

    return _memory_adapter


def reset_memory_adapter():
    """重置适配器"""
    global _memory_adapter
    _memory_adapter = None


# ==================== 旧接口兼容层 ====================

# 全局同步单例 - 供旧代码同步调用
_unified_memory_sync: Optional["MiyaMemoryCore"] = None


class MemoryCategory:
    """旧接口兼容 - 记忆分类"""

    IMPORTANT = "important"
    EMOTION = "emotion"
    DIALOGUE = "dialogue"
    KNOWLEDGE = "knowledge"


def get_unified_memory(data_dir="data/memory"):
    """旧接口兼容 - 同步/异步安全获取统一记忆"""
    global _unified_memory_sync
    if _unified_memory_sync is None:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 在异步上下文中，创建任务并等待
                import concurrent.futures

                # 直接同步初始化，避免在异步上下文中调用 run_until_complete
                _unified_memory_sync = MiyaMemoryCore(data_dir)
            else:
                _unified_memory_sync = loop.run_until_complete(
                    get_memory_core(data_dir)
                )
        except RuntimeError:
            # 没有事件循环，直接同步初始化
            _unified_memory_sync = MiyaMemoryCore(data_dir)
    return _unified_memory_sync


async def init_unified_memory(data_dir="data/memory"):
    """旧接口兼容 - 初始化统一记忆"""
    return get_unified_memory(data_dir)


def get_undefined_memory_adapter():
    """旧接口兼容 - 同步/异步安全获取适配器"""
    global _memory_adapter
    if _memory_adapter is None:
        import asyncio

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                _memory_adapter = MemoryAdapter()
            else:
                _memory_adapter = loop.run_until_complete(get_memory_adapter())
        except RuntimeError:
            _memory_adapter = MemoryAdapter()
    return _memory_adapter


async def create_memory_adapter():
    """旧接口兼容 - 创建适配器"""
    return await get_memory_adapter()


# ==================== 导出 ====================

__all__ = [
    # 核心
    "MiyaMemoryCore",
    "get_memory_core",
    "reset_memory_core",
    # 数据结构
    "MemoryItem",
    "MemoryQuery",
    "MemoryLevel",
    "MemoryPriority",
    "MemorySource",
    # 主类
    "MiyaMemory",
    # 适配器
    "MemoryAdapter",
    "get_memory_adapter",
    "reset_memory_adapter",
    # 便捷函数
    "store_dialogue",
    "store_important",
    "store_auto",
    "store_knowledge",
    "search_memory",
    "get_user_memories",
    "get_dialogue_history",
    "get_user_profile",
    "update_memory",
    "delete_memory",
    "cleanup_expired",
    "get_memory_stats",
    # 兼容
    "MemoryCategory",
    "get_unified_memory",
    "init_unified_memory",
    "get_undefined_memory_adapter",
    "create_memory_adapter",
]

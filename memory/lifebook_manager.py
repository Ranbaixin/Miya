"""
Legacy lifebook_manager - 已迁移到新版记忆系统

兼容旧接口的空实现
"""

from enum import Enum
from typing import Dict, List, Optional


class MemoryLevel(Enum):
    """记忆层级"""

    DIALOGUE = "dialogue"
    SHORT_TERM = "short_term"
    LONG_TERM = "long_term"
    SEMANTIC = "semantic"
    KNOWLEDGE = "knowledge"


class NodeType(Enum):
    """节点类型"""

    CHARACTER = "character"
    STAGE = "stage"
    CHAPTER = "chapter"


class Node:
    """节点"""

    def __init__(self, node_type: str, name: str, **kwargs):
        self.node_type = node_type
        self.name = name
        self.metadata = kwargs


class LifeBookManager:
    """LifeBook管理器 - 兼容旧接口"""

    def __init__(self, data_dir: str = "data/lifebook"):
        self.data_dir = data_dir
        self.nodes: Dict[str, Node] = {}

    async def initialize(self):
        """初始化"""
        pass

    async def create_node(self, node_type: str, name: str, **kwargs) -> str:
        """创建节点"""
        node = Node(node_type, name, **kwargs)
        self.nodes[name] = node
        return name

    async def get_node(self, name: str) -> Optional[Node]:
        """获取节点"""
        return self.nodes.get(name)

    async def list_nodes(self, node_type: Optional[str] = None) -> List[Node]:
        """列出节点"""
        if node_type:
            return [n for n in self.nodes.values() if n.node_type == node_type]
        return list(self.nodes.values())

    async def add_memory(self, content: str, user_id: str, **kwargs) -> str:
        """添加记忆 - 使用新版系统"""
        from memory import store_important

        return await store_important(content, user_id, tags=["lifebook"])

    async def get_memories(self, user_id: str, **kwargs) -> List[Dict]:
        """获取记忆"""
        from memory import get_user_memories

        mems = await get_user_memories(user_id)
        return [{"content": m.content, "tags": m.tags} for m in mems]


# 便捷函数
def get_lifebook_manager():
    """获取LifeBook管理器"""
    return LifeBookManager()


__all__ = [
    "LifeBookManager",
    "MemoryLevel",
    "NodeType",
    "Node",
    "get_lifebook_manager",
]

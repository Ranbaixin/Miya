"""
工具管理器 - Tools
"""

import logging
from typing import Dict, List, Any

logger = logging.getLogger("miya.tools")


TOOL_CATEGORIES = {
    "qq": "QQ 相关工具",
    "network": "网络工具",
    "social": "社交工具",
    "office": "办公工具",
    "scheduler": "调度工具",
    "visualization": "可视化工具",
    "bilibili": "B站工具",
    "reporting": "报告工具",
}


class ToolManager:
    """工具管理器"""

    def __init__(self) -> None:
        self._tools: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """初始化"""
        logger.info("[Tools] 初始化工具集...")
        # 加载内置工具
        logger.info(f"[Tools] 已加载 {len(TOOL_CATEGORIES)} 个工具分类")

    def register(self, name: str, tool: Any) -> None:
        """注册工具"""
        self._tools[name] = tool

    def get(self, name: str) -> Any:
        """获取工具"""
        return self._tools.get(name)

    def list_all(self) -> Dict[str, str]:
        """列出所有工具"""
        return TOOL_CATEGORIES.copy()


_tool_manager: Any = None


def get_tool_manager() -> ToolManager:
    global _tool_manager
    if _tool_manager is None:
        _tool_manager = ToolManager()
    return _tool_manager


__all__ = ["ToolManager", "get_tool_manager", "TOOL_CATEGORIES"]

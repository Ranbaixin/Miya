"""
插件管理器 - Plugins
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("miya.plugins")


class PluginManager:
    """插件管理器"""

    def __init__(self) -> None:
        self._plugins: Dict[str, Any] = {}
        self._commands: Dict[str, Any] = {}

    async def initialize(self) -> None:
        """初始化"""
        # 加载内置命令
        try:
            from core.commands import list_commands

            self._commands = {c["name"]: c for c in list_commands()}
            logger.info(f"[Plugin] 已加载 {len(self._commands)} 个内置命令")
        except Exception as e:
            logger.warning(f"[Plugin] 加载内置命令失败: {e}")

    def register(self, name: str, handler: Any) -> None:
        """注册插件"""
        self._plugins[name] = handler

    def get_command(self, name: str) -> Optional[Any]:
        """获取命令"""
        return self._commands.get(name)

    def list_commands(self) -> List[Dict]:
        """列出所有命令"""
        return list(self._commands.values())


_plugin_manager: Optional[PluginManager] = None


def get_plugin_manager() -> PluginManager:
    global _plugin_manager
    if _plugin_manager is None:
        _plugin_manager = PluginManager()
    return _plugin_manager


__all__ = ["PluginManager", "get_plugin_manager"]

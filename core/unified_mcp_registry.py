"""
MCP 双通道整合模块

统一 Miya 原生MCP 和 AstrBot MCP 工具系统
"""

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class MCPChannel(Enum):
    """MCP通道类型"""

    MIYA = "miya"
    ASTRBOT = "astrbot"
    BOTH = "both"


@dataclass
class MCPServerConfig:
    """MCP服务器配置"""

    name: str
    command: str
    args: List[str] = field(default_factory=list)
    env: Dict[str, str] = field(default_factory=dict)
    channel: MCPChannel = MCPChannel.BOTH


@dataclass
class MCPToolInfo:
    """MCP工具信息"""

    name: str
    description: str
    input_schema: Dict[str, Any]
    server: str
    channel: MCPChannel


class UnifiedMCPRegistry:
    """
    统一的MCP注册表

    功能：
    - 双通道MCP管理
    - 工具统一注册
    - 热重载支持
    """

    def __init__(self):
        self._miya_servers: Dict[str, Any] = {}
        self._astrbot_servers: Dict[str, Any] = {}
        self._tools: Dict[str, MCPToolInfo] = {}
        self._initialized = False

    async def initialize(self):
        """初始化MCP注册表"""
        logger.info("[UnifiedMCPRegistry] 初始化...")

        await self._init_miya_mcp()
        await self._init_astrbot_mcp()

        self._initialized = True
        logger.info(f"[UnifiedMCPRegistry] 初始化完成，共 {len(self._tools)} 个MCP工具")

    async def _init_miya_mcp(self):
        """初始化Miya原生MCP"""
        try:
            from core.mcp_client import get_global_mcp_registry as get_miya_mcp

            miya_mcp = get_miya_mcp()
            if miya_mcp and hasattr(miya_mcp, "list_tools"):
                tools = miya_mcp.list_tools()
                for tool in tools:
                    self._register_tool(
                        name=tool.get("name", ""),
                        description=tool.get("description", ""),
                        input_schema=tool.get("inputSchema", {}),
                        server=tool.get("server", "miya"),
                        channel=MCPChannel.MIYA,
                    )
                logger.info(f"[UnifiedMCPRegistry] 已注册 {len(tools)} 个Miya MCP工具")
        except Exception as e:
            logger.warning(f"[UnifiedMCPRegistry] Miya MCP初始化失败: {e}")

    async def _init_astrbot_mcp(self):
        """初始化AstrBot MCP"""
        try:
            from astrbot.core.agent.mcp_client import MCPToolRegistry

            self._astrbot_servers = {"default": MCPToolRegistry()}
            logger.info("[UnifiedMCPRegistry] AstrBot MCP已加载")
        except Exception as e:
            logger.warning(f"[UnifiedMCPRegistry] AstrBot MCP初始化失败: {e}")

    def _register_tool(
        self,
        name: str,
        description: str,
        input_schema: Dict[str, Any],
        server: str,
        channel: MCPChannel,
    ):
        """注册MCP工具"""
        if not name:
            return

        self._tools[name] = MCPToolInfo(
            name=name,
            description=description,
            input_schema=input_schema,
            server=server,
            channel=channel,
        )

    async def add_server(self, config: MCPServerConfig) -> Dict[str, Any]:
        """添加MCP服务器"""
        try:
            if config.channel in [MCPChannel.MIYA, MCPChannel.BOTH]:
                await self._add_miya_server(config)

            if config.channel in [MCPChannel.ASTRBOT, MCPChannel.BOTH]:
                await self._add_astrbot_server(config)

            return {"success": True, "message": f"MCP服务器 {config.name} 已添加"}

        except Exception as e:
            logger.error(f"[UnifiedMCPRegistry] 添加服务器失败: {e}")
            return {"success": False, "error": str(e)}

    async def _add_miya_server(self, config: MCPServerConfig):
        """添加Miya MCP服务器"""
        self._miya_servers[config.name] = config
        logger.info(f"[UnifiedMCPRegistry] Miya MCP服务器已添加: {config.name}")

    async def _add_astrbot_server(self, config: MCPServerConfig):
        """添加AstrBot MCP服务器"""
        self._astrbot_servers[config.name] = config
        logger.info(f"[UnifiedMCPRegistry] AstrBot MCP服务器已添加: {config.name}")

    async def remove_server(self, name: str) -> Dict[str, Any]:
        """移除MCP服务器"""
        removed = False

        if name in self._miya_servers:
            del self._miya_servers[name]
            removed = True

        if name in self._astrbot_servers:
            del self._astrbot_servers[name]
            removed = True

        tools_to_remove = [t for t in self._tools.values() if t.server == name]
        for tool in tools_to_remove:
            del self._tools[tool.name]

        return {"success": True, "removed": removed}

    async def call_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用MCP工具"""
        if tool_name not in self._tools:
            return {"success": False, "error": f"工具不存在: {tool_name}"}

        tool_info = self._tools[tool_name]

        try:
            if tool_info.channel == MCPChannel.MIYA:
                return await self._call_miya_tool(tool_name, arguments)
            elif tool_info.channel == MCPChannel.ASTRBOT:
                return await self._call_astrbot_tool(tool_name, arguments)
            else:
                return await self._call_both_channel_tool(tool_name, arguments)
        except Exception as e:
            logger.error(f"[UnifiedMCPRegistry] 工具调用失败: {e}")
            return {"success": False, "error": str(e)}

    async def _call_miya_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用Miya MCP工具"""
        try:
            from core.mcp_client import get_global_mcp_registry

            mcp = get_global_mcp_registry()
            if mcp and hasattr(mcp, "call_tool"):
                return await mcp.call_tool(tool_name, arguments)

            return {"success": False, "error": "Miya MCP不可用"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _call_astrbot_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """调用AstrBot MCP工具"""
        return {"success": False, "error": "AstrBot MCP调用待实现"}

    async def _call_both_channel_tool(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> Dict[str, Any]:
        """双通道调用"""
        result = await self._call_miya_tool(tool_name, arguments)
        if result.get("success"):
            return result

        return await self._call_astrbot_tool(tool_name, arguments)

    def list_tools(self, channel: Optional[MCPChannel] = None) -> List[Dict[str, Any]]:
        """列出MCP工具"""
        if channel:
            return [
                {
                    "name": t.name,
                    "description": t.description,
                    "server": t.server,
                    "channel": t.channel.value,
                }
                for t in self._tools.values()
                if t.channel == channel
            ]

        return [
            {
                "name": t.name,
                "description": t.description,
                "server": t.server,
                "channel": t.channel.value,
            }
            for t in self._tools.values()
        ]

    def list_servers(self) -> List[str]:
        """列出MCP服务器"""
        servers = list(self._miya_servers.keys())
        servers.extend(list(self._astrbot_servers.keys()))
        return list(set(servers))

    async def reload_server(self, name: str) -> Dict[str, Any]:
        """重载MCP服务器"""
        await self.remove_server(name)
        config = self._miya_servers.get(name) or self._astrbot_servers.get(name)
        if config:
            return await self.add_server(config)
        return {"success": False, "error": "配置不存在"}


_unified_mcp_registry: Optional[UnifiedMCPRegistry] = None


def get_unified_mcp_registry() -> UnifiedMCPRegistry:
    """获取全局统一MCP注册表"""
    global _unified_mcp_registry
    if _unified_mcp_registry is None:
        _unified_mcp_registry = UnifiedMCPRegistry()
    return _unified_mcp_registry

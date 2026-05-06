"""MCP Agent 私有化配置

借鉴 Undefined 的 per-Agent MCP 设计：
- 每个 Agent 可独立配置 MCP Server
- 按需加载释放，减少不必要连接
- 工具名称映射 (. → -_-)

用法:
    registry = AgentMCPRegistry()
    registry.register("web_agent", Path("skills/agents/web_agent/mcp.json"))
    tools = await registry.get_tools("web_agent")
"""

from __future__ import annotations

import asyncio
import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# 尝试导入 fastmcp，未安装时降级
try:
    from mcp import ClientSession
    from mcp.client.stdio import stdio_client, StdioServerParameters

    HAS_MCP = True
except ImportError:
    HAS_MCP = False
    ClientSession = None  # type: ignore
    stdio_client = None  # type: ignore
    StdioServerParameters = None  # type: ignore


class AgentMCPRegistry:
    """Per-Agent MCP 配置注册表

    特性:
        - 每个 Agent 独立 MCP 配置
        - 懒加载：首次访问时才连接
        - 自动释放：Agent 不再需要时断开
        - 工具名称转义 (. → -_-)
    """

    def __init__(self, dot_delimiter: str = "-_-"):
        self._configs: dict[str, dict[str, Any]] = {}
        self._sessions: dict[str, list[ClientSession]] = {}
        self._tools_cache: dict[str, list[dict[str, Any]]] = {}
        self.dot_delimiter = dot_delimiter
        self._lock = asyncio.Lock()

    def register(self, agent_name: str, mcp_config_path: Path | str) -> None:
        """为 Agent 注册 MCP 配置"""
        path = Path(mcp_config_path)
        if not path.exists():
            logger.debug("[AgentMCP] %s: MCP 配置不存在: %s", agent_name, path)
            return

        try:
            config = json.loads(path.read_text(encoding="utf-8"))
            self._configs[agent_name] = config
            # 清除旧缓存
            self._tools_cache.pop(agent_name, None)
            logger.info("[AgentMCP] %s: MCP 配置已注册", agent_name)
        except json.JSONDecodeError as e:
            logger.warning("[AgentMCP] %s: MCP 配置解析失败: %s", agent_name, e)

    def unregister(self, agent_name: str) -> None:
        """注销 Agent MCP 配置并释放连接"""
        self._configs.pop(agent_name, None)
        self._tools_cache.pop(agent_name, None)
        sessions = self._sessions.pop(agent_name, [])
        for session in sessions:
            asyncio.create_task(self._close_session(session))

    async def _close_session(self, session: Any) -> None:
        try:
            await session.__aexit__(None, None, None)
        except Exception:
            pass

    async def get_tools(self, agent_name: str) -> list[dict[str, Any]]:
        """获取 Agent 的 MCP 工具列表 (懒加载)"""
        if not HAS_MCP:
            return []

        # 缓存命中
        if agent_name in self._tools_cache:
            return self._tools_cache[agent_name]

        config = self._configs.get(agent_name)
        if not config:
            return []

        async with self._lock:
            # 双重检查
            if agent_name in self._tools_cache:
                return self._tools_cache[agent_name]

            tools = await self._fetch_tools(config)
            self._tools_cache[agent_name] = tools
            return tools

    async def _fetch_tools(self, config: dict[str, Any]) -> list[dict[str, Any]]:
        """连接 MCP Server 并获取工具列表"""
        tools: list[dict[str, Any]] = []
        mcp_servers = config.get("mcpServers", config)

        for server_name, server_config in mcp_servers.items():
            if isinstance(server_config, dict):
                try:
                    server_tools = await self._connect_and_list(server_config)
                    for tool in server_tools:
                        # 工具名映射: . → delimiter
                        name = tool.get("name", "")
                        mapped_name = self._map_name(server_name, name)
                        tools.append(
                            {
                                "type": "function",
                                "function": {
                                    "name": mapped_name,
                                    "description": tool.get("description", ""),
                                    "parameters": tool.get("inputSchema", {}),
                                },
                            }
                        )
                except Exception as e:
                    logger.warning(
                        "[AgentMCP] MCP Server %s 连接失败: %s",
                        server_name,
                        e,
                    )

        return tools

    async def _connect_and_list(
        self, server_config: dict[str, Any]
    ) -> list[dict[str, Any]]:
        """连接单个 MCP Server 并列出工具"""
        command = server_config.get("command", "")
        args = server_config.get("args", [])
        env = server_config.get("env", {})

        if not command:
            return []

        params = StdioServerParameters(
            command=command,
            args=args,
            env={**__import__("os").environ, **env},
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.list_tools()
                return [
                    {
                        "name": t.name,
                        "description": t.description or "",
                        "inputSchema": t.inputSchema or {},
                    }
                    for t in result.tools
                ]

    def _map_name(self, server_name: str, tool_name: str) -> str:
        """将 server.tool → server-delimiter-tool"""
        safe_server = server_name.replace(".", self.dot_delimiter)
        safe_tool = tool_name.replace(".", self.dot_delimiter)
        return f"{safe_server}{self.dot_delimiter}{safe_tool}"

    async def invoke_tool(
        self, agent_name: str, tool_name: str, arguments: dict[str, Any]
    ) -> Any:
        """调用 Agent MCP 工具"""
        if not HAS_MCP:
            raise RuntimeError("MCP 未安装, pip install mcp")

        config = self._configs.get(agent_name)
        if not config:
            raise ValueError(f"Agent {agent_name} 未注册 MCP")

        # 逆向映射：找出原始服务器和工具名
        parts = tool_name.split(self.dot_delimiter)
        # 简化处理：假设格式为 server_name_delimiter_tool_name
        server_name = parts[0]
        original_tool = self.dot_delimiter.join(parts[1:])

        server_config = config.get("mcpServers", config).get(server_name)
        if not server_config:
            raise ValueError(f"找不到 MCP Server: {server_name}")

        params = StdioServerParameters(
            command=server_config["command"],
            args=server_config.get("args", []),
            env=server_config.get("env", {}),
        )

        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                result = await session.call_tool(original_tool, arguments=arguments)
                return result

    def dispose(self) -> None:
        """释放所有 MCP 连接"""
        for agent_name in list(self._sessions.keys()):
            self.unregister(agent_name)
        self._configs.clear()
        self._tools_cache.clear()

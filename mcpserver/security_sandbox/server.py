"""
Security Sandbox MCP Server

基于 MCP 协议的安全沙箱服务入口点。
提供 Docker 容器隔离执行能力，用于安全工具运行。
"""

import asyncio
import json
import logging
import sys

from mcp.server import Server
from mcp.server.stdio import stdio_server

from .service import SecuritySandboxService

logger = logging.getLogger(__name__)


def create_server() -> Server:
    server = Server("security_sandbox")
    svc = SecuritySandboxService()

    @server.list_tools()
    async def list_tools():
        return [
            {
                "name": "security_sandbox_exec",
                "description": "在 Docker 容器中安全执行命令。支持 Kali Linux 渗透测试镜像和通用 Debian 镜像",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "command": {"type": "string", "description": "要执行的命令"},
                        "image": {"type": "string", "description": "Docker 镜像名，默认 kalilinux/kali-rolling"},
                        "timeout": {"type": "number", "description": "超时秒数，默认 120，最大 300"},
                    },
                    "required": ["command"],
                },
            },
            {
                "name": "security_sandbox_get_logs",
                "description": "获取容器执行日志",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "container_id": {"type": "string", "description": "容器 ID"},
                    },
                    "required": ["container_id"],
                },
            },
            {
                "name": "security_sandbox_list_containers",
                "description": "列出当前活跃的沙箱容器",
                "inputSchema": {"type": "object", "properties": {}},
            },
            {
                "name": "security_sandbox_stop_container",
                "description": "停止指定的沙箱容器",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "container_id": {"type": "string", "description": "要停止的容器 ID"},
                    },
                    "required": ["container_id"],
                },
            },
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> str:
        result = await svc.handle_handoff({"tool_name": name, "arguments": arguments})
        return result

    return server


async def main():
    server = create_server()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())

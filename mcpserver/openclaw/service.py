#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw MCP 服务 - 弥娅 AI 电脑控制引擎

让弥娅通过 OpenClaw Gateway 获得 AI 电脑控制能力：
- 文件读写操作
- 命令执行
- 浏览器自动化
- 桌面应用控制
- 代码生成与执行

集成到 Miya MCP 框架，通过 MCPManager 自动发现注册。
"""

import json
import logging
from typing import Dict, Any, Optional

from .runtime import get_runtime
from .client import OpenClawClient

logger = logging.getLogger("openclaw.service")


class OpenClawService:
    """
    OpenClaw MCP 服务 - 弥娅的 AI 电脑控制引擎。

    通过 MCPManager 的 handle_handoff 接收工具调用，
    工具列表在 agent-manifest.json 中定义。
    """

    def __init__(self):
        self.name = "openclaw"
        self.description = (
            "AI 电脑控制引擎 - 读/写文件、执行命令、浏览器自动化、桌面控制"
        )
        self.version = "1.0.0"

        self._client: Optional[OpenClawClient] = None
        self._runtime = get_runtime()

    async def handle_handoff(self, tool_call: Dict[str, Any]) -> str:
        """
        处理 MCP 工具调用。

        根据 tool_name 路由到具体处理方法。
        """
        tool_name = tool_call.get("tool_name", "").lower()

        try:
            if "send" in tool_name or "message" in tool_name:
                return await self._send_message(tool_call)
            elif "start" in tool_name or "launch" in tool_name:
                return await self._start_gateway(tool_call)
            elif "stop" in tool_name or "kill" in tool_name:
                return await self._stop_gateway(tool_call)
            elif "status" in tool_name or "health" in tool_name:
                return await self._get_status(tool_call)
            elif "history" in tool_name or "session" in tool_name:
                return await self._get_history(tool_call)
            else:
                return json.dumps(
                    {
                        "error": f"未知工具: {tool_name}",
                        "available": [
                            "send_message",
                            "start_gateway",
                            "stop_gateway",
                            "get_status",
                            "get_history",
                        ],
                    },
                    ensure_ascii=False,
                )
        except Exception as e:
            logger.exception(f"[OpenClaw] 工具调用异常: {tool_name}")
            return json.dumps({"error": str(e)}, ensure_ascii=False)

    # ===== 工具实现 =====

    async def _send_message(self, tool_call: Dict[str, Any]) -> str:
        """
        向 OpenClaw Agent 发送任务消息。

        这是最核心的工具——弥娅通过它让 AI 在电脑上执行各类操作。
        """
        message = tool_call.get("message", "")
        if not message:
            return json.dumps({"error": "缺少 message 参数"}, ensure_ascii=False)

        session_key = tool_call.get("session_key", "")
        workspace = tool_call.get("workspace", "")
        timeout = tool_call.get("timeout", 120)

        if not self._runtime.is_running:
            logger.info("[OpenClaw] Gateway 未运行，尝试启动...")
            started = await self._runtime.start()
            if not started:
                return json.dumps(
                    {
                        "error": "OpenClaw Gateway 未运行且启动失败",
                        "hint": "请先调用 start_gateway 或手动安装 openclaw: npm install -g openclaw",
                    },
                    ensure_ascii=False,
                )

        if self._client is None:
            self._client = OpenClawClient()

        result = await self._client.send_message(
            message=message,
            session_key=session_key or "",
            workspace=workspace or "",
            timeout_seconds=int(timeout),
        )

        logger.info(f"[OpenClaw] 消息结果: success={result.get('success')}")
        return json.dumps(result, ensure_ascii=False, default=str)

    async def _start_gateway(self, tool_call: Dict[str, Any]) -> str:
        """启动 OpenClaw Gateway"""
        result = await self._runtime.start()

        status = await self._runtime.get_status()
        return json.dumps(
            {
                "success": result,
                "message": "Gateway 已启动" if result else "Gateway 启动失败",
                "status": status,
            },
            ensure_ascii=False,
        )

    async def _stop_gateway(self, tool_call: Dict[str, Any]) -> str:
        """停止 OpenClaw Gateway"""
        if self._client:
            await self._client.close()
            self._client = None

        result = await self._runtime.stop()
        return json.dumps(
            {
                "success": result,
                "message": "Gateway 已停止" if result else "Gateway 停止失败",
            },
            ensure_ascii=False,
        )

    async def _get_status(self, tool_call: Dict[str, Any]) -> str:
        """获取 OpenClaw Gateway 运行状态"""
        runtime_status = await self._runtime.get_status()

        health = {"success": False}
        if self._runtime.is_running:
            client = OpenClawClient()
            health = await client.health_check()
            await client.close()

        return json.dumps(
            {
                "runtime": runtime_status,
                "health": health,
                "available": self._runtime.is_available,
            },
            ensure_ascii=False,
        )

    async def _get_history(self, tool_call: Dict[str, Any]) -> str:
        """获取会话历史记录"""
        session_key = tool_call.get("session_key", "")
        if not session_key:
            return json.dumps({"error": "缺少 session_key 参数"}, ensure_ascii=False)

        limit = tool_call.get("limit", 20)

        if not self._runtime.is_running:
            return json.dumps({"error": "Gateway 未运行"}, ensure_ascii=False)

        if self._client is None:
            self._client = OpenClawClient()

        result = await self._client.get_history(
            session_key=str(session_key),
            limit=int(limit),
        )

        return json.dumps(result, ensure_ascii=False, default=str)

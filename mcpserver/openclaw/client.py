#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw HTTP 客户端

与 OpenClaw Gateway (http://127.0.0.1:20789) 通信：
- 发送消息给 Agent
- 获取会话历史
- 直接工具调用
- Gateway 状态查询
"""

import json
import logging
import asyncio
import uuid
from datetime import datetime
from typing import Dict, Any, Optional, List

import httpx

from .config_bridge import get_config_tokens, DEFAULT_GATEWAY_PORT

logger = logging.getLogger("openclaw.client")


class OpenClawClient:
    """
    OpenClaw Gateway HTTP 客户端。

    通过 Gateway 的 /hooks 和 /tools 端点与 AI Agent 交互。
    """

    def __init__(
        self,
        gateway_url: Optional[str] = None,
        gateway_token: Optional[str] = None,
        hooks_token: Optional[str] = None,
        hooks_path: str = "/hooks",
        timeout: int = 120,
    ):
        tokens = get_config_tokens()
        port = (
            tokens.get("gateway_port", DEFAULT_GATEWAY_PORT)
            if tokens
            else DEFAULT_GATEWAY_PORT
        )

        self._gateway_url = (gateway_url or f"http://127.0.0.1:{port}").rstrip("/")
        self._gateway_token = gateway_token or (
            tokens.get("gateway_token", "") if tokens else ""
        )
        self._hooks_token = hooks_token or (
            tokens.get("hooks_token", "") if tokens else ""
        )
        self._hooks_path = hooks_path or (
            tokens.get("hooks_path", "/hooks") if tokens else "/hooks"
        )
        self._timeout = timeout
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def gateway_url(self) -> str:
        return self._gateway_url

    @property
    def hooks_url(self) -> str:
        return f"{self._gateway_url}{self._hooks_path}"

    async def _ensure_client(self) -> httpx.AsyncClient:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)
        return self._client

    # ===== 主要 API =====

    async def send_message(
        self,
        message: str,
        session_key: Optional[str] = None,
        workspace: Optional[str] = None,
        name: Optional[str] = None,
        channel: str = "last",
        model: Optional[str] = None,
        timeout_seconds: int = 120,
    ) -> Dict[str, Any]:
        """
        向 OpenClaw Agent 发送消息。

        Args:
            message: 要执行的任务描述
            session_key: 会话键（可选，为空则创建新会话）
            workspace: 工作目录（可选）
            name: Agent 名称（可选）
            channel: 通道类型
            model: 模型覆盖（可选）
            timeout_seconds: 超时秒数

        Returns:
            {
                "success": bool,
                "session_key": str,
                "reply": str | None,
                "status": "completed" | "accepted" | "error",
                "task_id": str,
            }
        """
        client = await self._ensure_client()

        payload = {
            "message": message,
            "sessionKey": session_key or "",
            "channel": channel,
            "timeoutSeconds": timeout_seconds,
        }

        if workspace:
            payload["workspace"] = workspace
        if name:
            payload["name"] = name
        if model:
            payload["model"] = model

        headers = {"Content-Type": "application/json"}
        if self._hooks_token:
            headers["Authorization"] = f"Bearer {self._hooks_token}"

        logger.info(f"[OpenClaw] 发送消息: {message[:100]}...")

        try:
            response = await client.post(
                f"{self.hooks_url}/agent",
                json=payload,
                headers=headers,
                timeout=self._timeout,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "session_key": session_key or data.get("sessionKey", ""),
                    "reply": data.get("reply")
                    or data.get("content", {}).get("text", str(data)),
                    "status": "completed",
                    "task_id": str(uuid.uuid4()),
                    "raw": data,
                }
            elif response.status_code == 202:
                # Gateway 接受了请求但异步处理
                data = response.json()
                # 尝试轮询获取结果
                result = await self._poll_result(session_key, timeout_seconds)
                return result
            else:
                error_text = response.text[:500]
                logger.error(
                    f"[OpenClaw] Gateway 返回错误 {response.status_code}: {error_text}"
                )
                return {
                    "success": False,
                    "error": f"Gateway 返回 {response.status_code}: {error_text}",
                    "status": "error",
                    "task_id": str(uuid.uuid4()),
                }

        except httpx.TimeoutException:
            return {
                "success": False,
                "error": f"请求超时 ({timeout_seconds}s)",
                "status": "error",
                "task_id": str(uuid.uuid4()),
            }
        except httpx.ConnectError:
            return {
                "success": False,
                "error": "无法连接到 OpenClaw Gateway，请确认 Gateway 已启动",
                "status": "error",
                "task_id": str(uuid.uuid4()),
            }
        except Exception as e:
            logger.error(f"[OpenClaw] 发送消息异常: {e}")
            return {
                "success": False,
                "error": str(e),
                "status": "error",
                "task_id": str(uuid.uuid4()),
            }

    async def get_history(
        self,
        session_key: str,
        limit: int = 20,
    ) -> Dict[str, Any]:
        """
        获取会话历史记录。

        Args:
            session_key: 会话键
            limit: 返回条数

        Returns:
            {"success": bool, "messages": [...], "session_key": str}
        """
        client = await self._ensure_client()

        headers = {}
        if self._gateway_token:
            headers["Authorization"] = f"Bearer {self._gateway_token}"

        payload = {
            "tool": "sessions_history",
            "action": "get",
            "args": {"sessionKey": session_key, "limit": limit},
            "sessionKey": session_key,
            "dryRun": False,
        }

        try:
            response = await client.post(
                f"{self._gateway_url}/tools/invoke",
                json=payload,
                headers=headers,
                timeout=30,
            )

            if response.status_code == 200:
                data = response.json()
                return {
                    "success": True,
                    "session_key": session_key,
                    "messages": data.get("result", data.get("messages", [])),
                    "raw": data,
                }
            else:
                return {
                    "success": False,
                    "error": f"获取历史失败: {response.status_code}",
                    "messages": [],
                    "session_key": session_key,
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "messages": [],
                "session_key": session_key,
            }

    async def invoke_tool(
        self,
        tool: str,
        args: Dict[str, Any],
        session_key: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        直接调用 OpenClaw 工具。

        Args:
            tool: 工具名称（如 web_search, Read, Write 等）
            args: 工具参数
            session_key: 会话键

        Returns:
            工具执行结果
        """
        client = await self._ensure_client()

        headers = {}
        if self._gateway_token:
            headers["Authorization"] = f"Bearer {self._gateway_token}"

        payload = {
            "tool": tool,
            "action": "invoke",
            "args": args,
            "sessionKey": session_key or "",
            "dryRun": False,
        }

        try:
            response = await client.post(
                f"{self._gateway_url}/tools/invoke",
                json=payload,
                headers=headers,
                timeout=60,
            )

            if response.status_code == 200:
                return {"success": True, "result": response.json()}
            else:
                return {
                    "success": False,
                    "error": f"工具调用失败: {response.status_code}",
                    "detail": response.text[:500],
                }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def health_check(self) -> Dict[str, Any]:
        """检查 Gateway 健康状态"""
        client = await self._ensure_client()
        try:
            response = await client.get(
                f"{self._gateway_url}/health",
                timeout=5,
            )
            return {
                "success": True,
                "status": response.status_code,
                "gateway_url": self._gateway_url,
            }
        except httpx.ConnectError:
            return {"success": False, "error": "Gateway 未运行或无法连接"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    # ===== 内部方法 =====

    async def _poll_result(
        self,
        session_key: Optional[str],
        timeout_seconds: int,
    ) -> Dict[str, Any]:
        """轮询异步任务结果（指数退避 + 智能检测 agent 回复）"""
        if not session_key:
            return {
                "success": False,
                "error": "无会话键，无法轮询异步结果",
                "status": "error",
                "task_id": str(uuid.uuid4()),
            }

        waited = 0.0
        poll_interval = 2.0

        while waited < timeout_seconds:
            history = await self.get_history(session_key, limit=10)
            if history.get("success") and history.get("messages"):
                messages = history["messages"]
                if isinstance(messages, list) and len(messages) > 0:
                    # 倒序查找最后一条 agent/assistant 消息（跳过 tool/user 消息）
                    for msg in reversed(messages):
                        if not isinstance(msg, dict):
                            continue
                        role = msg.get("role", "")
                        content = msg.get("content", "")
                        if isinstance(content, dict):
                            content = content.get("text", str(content))
                        # 只取 assistant 的最终文本回复（不含 tool_calls）
                        if (
                            role in ("assistant", "agent")
                            and content
                            and not msg.get("tool_calls")
                        ):
                            return {
                                "success": True,
                                "session_key": session_key,
                                "reply": str(content),
                                "status": "completed",
                                "task_id": str(uuid.uuid4()),
                                "messages": messages,
                            }

            await asyncio.sleep(poll_interval)
            waited += poll_interval
            # 指数退避: 2s → 3.5s → 5s (max)，减少无效轮询
            poll_interval = min(poll_interval * 1.5, 5.0)

        return {
            "success": False,
            "error": f"轮询超时 ({timeout_seconds}s)，任务可能仍在执行中",
            "status": "running",
            "task_id": str(uuid.uuid4()),
        }

    async def close(self):
        """关闭客户端"""
        if self._client:
            await self._client.aclose()
            self._client = None

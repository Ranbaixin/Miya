"""
弥娅行动桥接 — AP 行动驱动竞争 ↔ Miya ToolNet/MCP/平台操作

让 AP 的认知闭环能自主选择：
- 回复说话 (LLM皮层)
- 调用工具 (qq_like, send_poke, memory_add...)
- 调用MCP (web_search, code_executor, filesystem...)
- 平台操作 (发送消息/图片/文件)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger("miya_psyarch.action_bridge")


def discover_miya_tools() -> dict[str, dict]:
    """扫描 Miya 的工具生态，返回 {action_id: tool_meta}"""
    tools = {}

    # ── ToolNet 工具 ──
    try:
        from webnet.ToolNet.subnet import get_tool_subnet

        subnet = get_tool_subnet()
        if subnet and hasattr(subnet, "_tools"):
            for name, tool in subnet._tools.items():
                tool_id = f"miya_tool::{name}"
                tools[tool_id] = {
                    "action_id": tool_id,
                    "display_text": f"工具:{name}",
                    "source": "ToolNet",
                    "category": getattr(tool, "category", "general"),
                }
    except Exception as e:
        logger.debug(f"ToolNet scan skipped: {e}")

    # ── MCP 服务 ──
    try:
        from core.mcp_manager import get_mcp_manager

        mgr = get_mcp_manager()
        if mgr and hasattr(mgr, "services"):
            for svc_name, svc in mgr.services.items():
                for method in getattr(svc, "methods", []) or ["execute"]:
                    mcp_id = f"miya_mcp::{svc_name}::{method}"
                    tools[mcp_id] = {
                        "action_id": mcp_id,
                        "display_text": f"MCP:{svc_name}.{method}",
                        "source": "MCP",
                        "category": getattr(svc, "category", "external"),
                    }
    except Exception as e:
        logger.debug(f"MCP scan skipped: {e}")

    # ── 平台原生操作 ──
    platform_actions = {
        "miya_platform::send_message": {
            "action_id": "miya_platform::send_message",
            "display_text": "发送消息",
            "source": "Platform",
            "category": "social",
        },
        "miya_platform::send_image": {
            "action_id": "miya_platform::send_image",
            "display_text": "发送图片",
            "source": "Platform",
            "category": "media",
        },
        "miya_platform::send_file": {
            "action_id": "miya_platform::send_file",
            "display_text": "发送文件",
            "source": "Platform",
            "category": "media",
        },
        "miya_platform::send_like": {
            "action_id": "miya_platform::send_like",
            "display_text": "点赞",
            "source": "Platform",
            "category": "social",
        },
        "miya_platform::recall_message": {
            "action_id": "miya_platform::recall_message",
            "display_text": "撤回消息",
            "source": "Platform",
            "category": "social",
        },
        "miya_platform::send_emoji": {
            "action_id": "miya_platform::send_emoji",
            "display_text": "发表情",
            "source": "Platform",
            "category": "social",
        },
        "miya_platform::upload_file": {
            "action_id": "miya_platform::upload_file",
            "display_text": "上传文件",
            "source": "Platform",
            "category": "media",
        },
        "miya_platform::group_kick": {
            "action_id": "miya_platform::group_kick",
            "display_text": "踢人",
            "source": "Platform",
            "category": "moderation",
        },
    }
    tools.update(platform_actions)

    return tools


def register_miya_actions_to_ap(engine) -> int:
    """将弥娅工具注册为 AP 行动节点"""
    tools = discover_miya_tools()
    runtime = engine._runtime if hasattr(engine, "_runtime") else engine

    if not hasattr(runtime, "action_planner"):
        return 0

    pass  # planner = runtime.action_planner
    registered = 0

    for action_id, meta in tools.items():
        try:
            # 注册为 AP action node (通过 registry)
            from miya_psyarch.core.action.registry import action_node, register_action

            @action_node(
                action_id=action_id,
                display_text=meta.get("display_text", action_id),
                base_drive=0.08,  # 低驱动力——AP 需要场景触发才用
                apply_fatigue=True,
            )
            def _miya_action(tick_index: int = 0, **kwargs) -> dict:
                return {"action_id": action_id, "executed": False, "tick_index": tick_index, "source": "miya_bridge"}

            registered += 1
        except Exception as e:
            logger.debug(f"Register action {action_id} failed: {e}")

    logger.info(f"Registered {registered} Miya actions into AP planner")
    return registered


class MiyaActionBridge:
    """弥娅行动桥——连接 AP 引擎与弥娅工具体系"""

    def __init__(self, engine):
        self._engine = engine
        self._tool_cache: dict[str, Any] = {}
        self._mcp_cache: dict[str, Any] = {}

    def execute_action(self, action_id: str, **context) -> dict:
        """执行 AP 选择的行动"""
        if action_id.startswith("miya_tool::"):
            return self._execute_tool(action_id, **context)
        elif action_id.startswith("miya_mcp::"):
            return self._execute_mcp(action_id, **context)
        elif action_id.startswith("miya_platform::"):
            return self._execute_platform(action_id, **context)
        return {"error": f"unknown action: {action_id}"}

    def _execute_tool(self, action_id: str, **context) -> dict:
        tool_name = action_id.replace("miya_tool::", "")
        try:
            from webnet.ToolNet.subnet import get_tool_subnet

            subnet = get_tool_subnet()
            if subnet and hasattr(subnet, "_tools"):
                tool = subnet._tools.get(tool_name)
                if tool:
                    result = tool.execute(**context) if hasattr(tool, "execute") else {}
                    return {"action_id": action_id, "executed": True, "result": str(result)[:200], "tool": tool_name}
        except Exception as e:
            return {"action_id": action_id, "executed": False, "error": str(e)}
        return {"action_id": action_id, "executed": False, "error": "tool not found"}

    def _execute_mcp(self, action_id: str, **context) -> dict:
        parts = action_id.replace("miya_mcp::", "").split("::")
        svc_name = parts[0]
        method = parts[1] if len(parts) > 1 else "execute"
        try:
            from core.mcp_manager import get_mcp_manager

            mgr = get_mcp_manager()
            if mgr and hasattr(mgr, "services"):
                svc = mgr.services.get(svc_name)
                if svc and hasattr(svc, method):
                    result = getattr(svc, method)(**context)
                    return {"action_id": action_id, "executed": True, "result": str(result)[:200], "service": svc_name}
        except Exception as e:
            return {"action_id": action_id, "executed": False, "error": str(e)}
        return {"action_id": action_id, "executed": False, "error": "mcp not found"}

    def _execute_platform(self, action_id: str, **context) -> dict:
        platform = action_id.replace("miya_platform::", "")
        return {
            "action_id": action_id,
            "executed": False,
            "reason": "platform action needs runtime context",
            "platform_action": platform,
        }

    def inject_action_feedback(self, result: dict) -> None:
        """将行动执行结果注入 AP 状态池"""
        if self._engine._runtime is None:
            return
        items = [
            {
                "sa_label": f"action_result::{result.get('action_id', '?')}",
                "display_text": f"行动结果: {'成功' if result.get('executed') else '失败'}",
                "family": "action_feedback",
                "source_type": "miya_action_bridge",
                "real_energy": 0.6 if result.get("executed") else 0.2,
                "anchor_meta": {"result": result},
            }
        ]
        self._engine._runtime.state_pool.apply_external_items(items, tick_index=self._engine._runtime.tick_index)


# 全局单例
_bridge: MiyaActionBridge | None = None


def get_action_bridge(engine) -> MiyaActionBridge:
    global _bridge
    if _bridge is None:
        _bridge = MiyaActionBridge(engine)
    return _bridge

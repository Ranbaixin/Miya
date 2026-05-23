"""
发送戳一戳工具
"""

import logging
from typing import Any, Dict

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class SendPokeTool(BaseTool):
    """戳一戳工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "send_poke",
            "description": "发送戳一戳消息。当用户说'戳一下'、'拍一拍'、'戳'时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "user_id": {
                        "type": "integer",
                        "description": "目标用户QQ号，默认为消息发送者",
                    },
                    "group_id": {"type": "integer", "description": "群号"},
                },
            },
        }

    async def execute(self, context: ToolContext, **kwargs) -> str:
        args = kwargs.get("args", {}) if kwargs else {}

        user_id = args.get("user_id", context.user_id)
        group_id = args.get("group_id", context.group_id)

        if not user_id:
            return "请指定要戳的用户"

        try:
            if context.qq_net and hasattr(context.qq_net, "onebot_client"):
                client = context.qq_net.onebot_client
                if group_id:
                    await client.send_poke(user_id, group_id)
                    return f"戳了戳 {user_id}"
                else:
                    return "戳一戳仅支持群聊"
            return "戳一戳功能暂不可用"
        except Exception as e:
            logger.error(f"戳一戳失败: {e}")
            return f"戳一戳失败: {str(e)[:50]}"


def get_send_poke_tool():
    return SendPokeTool()

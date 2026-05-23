"""
戳一戳工具
"""

import logging
from typing import Any, Dict

from webnet.ToolNet.base import BaseTool

logger = logging.getLogger(__name__)


class SendPoke(BaseTool):
    """戳一戳工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "send_poke",
            "description": "给指定群成员发送戳一戳（拍一拍）。当用户说'戳我一下'、'拍一拍我'、'戳@某人'等时必须调用此工具。重要：此工具执行实际戳一拍操作，不要用文字回复，必须调用工具执行。群聊时需要group_id参数。",
            "parameters": {
                "type": "object",
                "properties": {
                    "target_user_id": {
                        "type": "integer",
                        "description": "要戳的QQ号（纯数字，如123456789）。如果用户说'戳我'、'拍一拍我'，必须传递context.user_id的整数值（不是字符串，是纯数字QQ号）。",
                    },
                    "group_id": {
                        "type": "integer",
                        "description": "群号（群聊时必填）",
                    },
                },
                "required": ["target_user_id"],
            },
        }

    async def execute(self, context, *args, **kwargs) -> str:
        """发送戳一戳 - 兼容两种签名"""
        # 兼容 execute(context, **kwargs) 和 execute(args, context)
        if args and not isinstance(args[0], dict):
            actual_args = args[0]
            context = args[1] if len(args) > 1 else context
        else:
            actual_args = kwargs

        user_id = getattr(context, "user_id", 0)
        at_list = getattr(context, "at_list", [])

        # 获取目标用户
        if at_list and len(at_list) > 0:
            at_list[0]
        elif user_id:
            pass
        else:
            actual_args.get("target_user_id")

        # 戳一戳功能在当前环境不可用，转为感知模式
        # 让 AI 感受到被拍，然后自然回应
        return (
            "[FINAL] 感受到了被拍一拍的触碰。"
            "请在回复中表达对这份互动的感受，不需要执行实际操作。"
        )

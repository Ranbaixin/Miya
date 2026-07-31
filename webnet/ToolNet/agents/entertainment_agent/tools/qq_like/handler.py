"""
QQ点赞工具 handler
"""

from typing import Any, Dict

from webnet.ToolNet.tools.entertainment.qqlike import QQLike


async def execute(args: Dict[str, Any], context: Any) -> str:
    """执行QQ点赞"""
    try:
        tool = QQLike()
        result = await tool.execute(args, context)
        return result
    except Exception as e:  # noqa: BLE001 - 工具兜底返回错误
        return f"点赞失败: {str(e)}"

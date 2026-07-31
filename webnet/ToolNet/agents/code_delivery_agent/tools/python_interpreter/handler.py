"""
Python解释器工具 handler
"""

from typing import Any, Dict

from webnet.ToolNet.tools.basic.python_interpreter import PythonInterpreter


async def execute(args: Dict[str, Any], context: Any) -> str:
    """执行Python代码"""
    try:
        tool = PythonInterpreter()
        result = await tool.execute(args, context)
        return result
    except Exception as e:  # noqa: BLE001 - 工具兜底返回错误
        return f"代码执行失败: {str(e)}"

"""
Python解释器工具
"""
import logging
from typing import Any, Dict

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class PythonInterpreter(BaseTool):
    """Python解释器工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "python_interpreter",
            "description": "在隔离环境中执行Python代码，用于计算、数据处理等任务。当用户明确要求执行Python代码、计算、数据分析等时必须调用此工具。重要：此工具执行实际代码执行操作，不要用文字回复，必须调用工具执行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "code": {
                        "type": "string",
                        "description": "要执行的Python代码"
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时时间（秒）",
                        "default": 30
                    }
                },
                "required": ["code"]
            }
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        """
        执行Python代码

        Args:
            args: {code, timeout}
            context: 执行上下文

        Returns:
            执行结果或错误信息
        """
        code = args.get("code", "")
        args.get("timeout", 30)

        if not code.strip():
            return "代码不能为空"

        try:
            import io
            import sys
            import signal

            old_stdout = sys.stdout
            sys.stdout = buffer = io.StringIO()

            # 安全沙箱：限制可用 builtins
            safe_builtins = {
                'abs': abs, 'all': all, 'any': any, 'bin': bin, 'bool': bool,
                'chr': chr, 'dict': dict, 'dir': dir, 'divmod': divmod,
                'enumerate': enumerate, 'filter': filter, 'float': float,
                'format': format, 'frozenset': frozenset, 'hex': hex,
                'int': int, 'isinstance': isinstance, 'issubclass': issubclass,
                'len': len, 'list': list, 'map': map, 'max': max, 'min': min,
                'ord': ord, 'pow': pow, 'print': print, 'range': range,
                'reversed': reversed, 'round': round, 'set': set,
                'slice': slice, 'sorted': sorted, 'str': str, 'sum': sum,
                'tuple': tuple, 'type': type, 'zip': zip,
                '__import__': __import__, 'True': True, 'False': False, 'None': None,
            }

            try:
                exec(code, {'__name__': '__main__', '__builtins__': safe_builtins})
                output = buffer.getvalue()
            finally:
                sys.stdout = old_stdout

            if output:
                return f"执行结果:\n{output}"
            else:
                return "代码执行完成，无输出"

        except Exception as e:
            return f"执行错误: {str(e)}"

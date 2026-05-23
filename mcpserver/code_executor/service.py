#!/usr/bin/env python3
"""
MCP Code Executor 服务 - 代码执行
"""

import asyncio
import json
import os
import tempfile
from typing import Any, Dict


class CodeExecutorService:
    """MCP Code Executor 服务"""

    def __init__(self):
        self.name = "code_executor"
        self.description = "代码执行服务 - 运行 Python/JS/Shell 代码"
        self.version = "1.0.0"

    async def handle_handoff(self, tool_call: Dict[str, Any]) -> str:
        """处理工具调用"""
        tool_name = tool_call.get("tool_name", "")

        if "execute" in tool_name.lower() or "run" in tool_name.lower():
            return await self._execute_code(tool_call)
        else:
            return json.dumps({"error": f"未知工具: {tool_name}"})

    async def _execute_code(self, tool_call: Dict[str, Any]) -> str:
        """执行代码"""
        code = tool_call.get("code", "")
        language = tool_call.get("language", "python")
        timeout = tool_call.get("timeout", 30)

        if not code:
            return json.dumps({"error": "缺少 code 参数"})

        try:
            if language == "python":
                return await self._run_python(code, timeout)
            elif language in ["javascript", "js", "node"]:
                return await self._run_node(code, timeout)
            elif language == "shell" or language == "bash":
                return await self._run_shell(code, timeout)
            else:
                return json.dumps({"error": f"不支持的语言: {language}"})
        except Exception as e:
            return json.dumps({"error": str(e)})

    async def _run_python(self, code: str, timeout: int) -> str:
        """运行 Python 代码"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = await asyncio.create_subprocess_exec(
                "python",
                temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=timeout
            )

            return json.dumps(
                {
                    "success": result.returncode == 0,
                    "language": "python",
                    "stdout": stdout.decode("utf-8", errors="ignore"),
                    "stderr": stderr.decode("utf-8", errors="ignore"),
                    "exit_code": result.returncode,
                }
            )
        except asyncio.TimeoutError:
            return json.dumps({"error": f"执行超时 ({timeout}s)"})
        finally:
            os.unlink(temp_file)

    async def _run_node(self, code: str, timeout: int) -> str:
        """运行 Node.js 代码"""
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".js", delete=False, encoding="utf-8"
        ) as f:
            f.write(code)
            temp_file = f.name

        try:
            result = await asyncio.create_subprocess_exec(
                "node",
                temp_file,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=timeout
            )

            return json.dumps(
                {
                    "success": result.returncode == 0,
                    "language": "javascript",
                    "stdout": stdout.decode("utf-8", errors="ignore"),
                    "stderr": stderr.decode("utf-8", errors="ignore"),
                    "exit_code": result.returncode,
                }
            )
        except asyncio.TimeoutError:
            return json.dumps({"error": f"执行超时 ({timeout}s)"})
        finally:
            os.unlink(temp_file)

    async def _run_shell(self, code: str, timeout: int) -> str:
        """运行 Shell 命令"""
        try:
            result = await asyncio.create_subprocess_exec(
                "bash",
                "-c",
                code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(
                result.communicate(), timeout=timeout
            )

            return json.dumps(
                {
                    "success": result.returncode == 0,
                    "language": "shell",
                    "stdout": stdout.decode("utf-8", errors="ignore"),
                    "stderr": stderr.decode("utf-8", errors="ignore"),
                    "exit_code": result.returncode,
                }
            )
        except asyncio.TimeoutError:
            return json.dumps({"error": f"执行超时 ({timeout}s)"})


service = CodeExecutorService()


if __name__ == "__main__":
    import asyncio

    async def test():
        result = await service.handle_handoff(
            {"tool_name": "execute", "code": "print(1+1)", "language": "python"}
        )
        print(result)

    asyncio.run(test())

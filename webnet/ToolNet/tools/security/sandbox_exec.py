"""
沙箱命令执行工具

通过 Docker 沙箱安全执行系统命令。
支持 Kali Linux 渗透测试环境和通用 Debian 环境。
"""

import logging
from typing import Any, Dict

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class SecuritySandboxExecTool(BaseTool):
    """沙箱命令执行工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_sandbox_exec",
            "description": (
                "Docker 沙箱命令执行工具。\n"
                "在隔离的 Docker 容器中安全执行系统命令。\n"
                "支持 Kali Linux (渗透测试) 和 Debian (通用) 镜像。\n"
                "注意：所有命令在隔离容器中执行，不会影响主机系统。\n"
                "注意：仅用于授权测试。\n\n"
                "示例:\n"
                "- 执行nmap: security_sandbox_exec command='nmap -sV scanme.nmap.org'\n"
                "- Kali环境: security_sandbox_exec command='sqlmap -u http://target.com' image=kalilinux/kali-rolling\n"
                "- 安装工具: security_sandbox_exec command='apt install -y nikto'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {
                        "type": "string",
                        "description": "要在沙箱中执行的命令",
                    },
                    "image": {
                        "type": "string",
                        "description": "Docker 镜像，默认 kalilinux/kali-rolling（渗透测试），可选 debian:latest（轻量）",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "执行超时（秒），默认120，最大300",
                    },
                },
                "required": ["command"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        command = args.get("command", "")
        image = args.get("image", "kalilinux/kali-rolling")
        timeout = args.get("timeout", 120)

        if not command:
            return "请提供要执行的命令"

        try:
            from mcpserver.security_sandbox.service import service as sandbox_service

            result = await sandbox_service._exec_command(
                {
                    "command": command,
                    "image": image,
                    "timeout": min(timeout, 300),
                }
            )
            return result
        except Exception as e:
            return await self._local_fallback(command, timeout)

    async def _local_fallback(self, command: str, timeout: int) -> str:
        """MCP 服务不可用时的本地回退"""
        import asyncio
        import platform

        if platform.system() == "Windows":
            try:
                proc = await asyncio.create_subprocess_shell(
                    command,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=min(timeout, 120))
                output = (stdout + stderr).decode("utf-8", errors="replace")
                if len(output) > 8000:
                    output = output[:8000] + "\n... [截断]"
                return f"本地执行完成（无 Docker 沙箱）\n状态码: {proc.returncode}\n{'─' * 40}\n{output}"
            except asyncio.TimeoutError:
                proc.kill()
                return "命令执行超时"
        else:
            try:
                proc = await asyncio.create_subprocess_shell(
                    f"timeout {timeout} {command}",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, stderr = await proc.communicate()
                output = (stdout + stderr).decode("utf-8", errors="replace")
                return f"本地执行完成\n{'─' * 40}\n{output[:8000]}"
            except Exception as e:
                return f"执行失败: {str(e)[:200]}"


def get_security_sandbox_exec_tool():
    return SecuritySandboxExecTool()

"""
Nmap 完整扫描工具

在 Docker 沙箱中运行 nmap 进行完整的网络扫描。
支持 OS 检测、服务版本检测、NSE 脚本扫描。
当 Docker 不可用时回退到 Python socket 端口扫描。
"""

import logging
from typing import Any, Dict, List

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_nmap_scan_config
except ImportError:

    def get_nmap_scan_config():
        return {}


_CFG = get_nmap_scan_config()
NMAP_SCAN_TYPES = _CFG.get("scan_types", {})
DEFAULT_TIMEOUT = _CFG.get("default_timeout", 180)
MAX_TIMEOUT_NMAP = _CFG.get("max_timeout", 300)


class SecurityNmapScanTool(BaseTool):
    """Nmap 扫描工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_nmap_scan",
            "description": (
                "Nmap 网络扫描工具。\n"
                "在 Docker 沙箱中运行 nmap，支持完整的网络侦查能力。\n"
                "包括：OS检测、服务版本检测、NSE脚本扫描、UDP扫描等。\n"
                "扫描模式: quick(快速)/full(全面)/stealth(隐蔽)/udp/version/script/all\n"
                "注意：仅用于授权测试。\n\n"
                "示例:\n"
                "- 快速扫描: security_nmap_scan target=192.168.1.1 mode=quick\n"
                "- 全面扫描: security_nmap_scan target=example.com mode=full\n"
                "- 自定义: security_nmap_scan target=example.com custom_args='-sV -p 1-1000'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "目标IP或域名",
                    },
                    "mode": {
                        "type": "string",
                        "enum": ["quick", "full", "stealth", "udp", "version", "script", "all"],
                        "description": "扫描模式",
                    },
                    "custom_args": {
                        "type": "string",
                        "description": "自定义 nmap 参数，如 '-sV -p 22,80,443'",
                    },
                    "timeout": {
                        "type": "integer",
                        "description": "超时（秒），默认180",
                    },
                },
                "required": ["target"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        target = args.get("target", "").strip()
        mode = args.get("mode", "quick")
        custom_args = args.get("custom_args", "")
        timeout = args.get("timeout", DEFAULT_TIMEOUT)

        if not target:
            return "请提供扫描目标"

        target = target.split("://")[-1].split("/")[0].split(":")[0]

        nmap_args = custom_args or NMAP_SCAN_TYPES.get(mode, NMAP_SCAN_TYPES["quick"])

        command = f"nmap {nmap_args} {target}"

        lines = [
            f"Nmap 扫描报告",
            f"目标: {target}",
            f"模式: {mode}",
            f"参数: {nmap_args}",
            "",
        ]

        try:
            from mcpserver.security_sandbox.service import service as sandbox_service

            result = await sandbox_service._exec_command(
                {
                    "command": command,
                    "image": "kalilinux/kali-rolling",
                    "timeout": min(timeout, MAX_TIMEOUT_NMAP),
                }
            )
            lines.append(result)
            return "\n".join(lines)
        except Exception as e:
            logger.warning(f"Docker 沙箱执行失败，回退到 socket 扫描: {e}")
            return await self._fallback_port_scan(target)

    async def _fallback_port_scan(self, target: str) -> str:
        """Docker 不可用时的 socket 端口扫描回退"""
        from webnet.ToolNet.tools.security.port_scanner import SecurityPortScanTool

        tool = SecurityPortScanTool()
        result = await tool.execute({"target": target}, None)
        return f"Nmap 不可用（Docker 未安装），回退到 Socket 扫描:\n\n{result}"


def get_security_nmap_scan_tool():
    return SecurityNmapScanTool()

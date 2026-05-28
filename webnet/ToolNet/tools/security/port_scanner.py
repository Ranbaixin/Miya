"""
端口扫描工具

使用 Python socket 进行 TCP 端口连通性检测。
支持单端口和端口范围扫描，自动识别常见服务。
"""

import asyncio
import logging
import socket
from typing import Any, Dict, List

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_port_scanner_config
except ImportError:
    get_port_scanner_config = lambda: {}

_CFG = get_port_scanner_config()
COMMON_PORTS = _CFG.get("common_ports", {})
MAX_PORTS = _CFG.get("max_ports", 100)
CONNECT_TIMEOUT = _CFG.get("connect_timeout", 3.0)
BANNER_TIMEOUT = _CFG.get("banner_timeout", 2.0)

SERVICE_BANNERS = {
    22: b"SSH",
    80: b"HTTP",
    443: b"",  # TLS handshake needed
    3306: b"",  # MySQL handshake
    5432: b"",  # PostgreSQL handshake
    6379: b"",  # Redis with PING
}


class SecurityPortScanTool(BaseTool):
    """TCP 端口扫描工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_port_scan",
            "description": (
                "网络安全端口扫描工具。\n"
                "当用户需要对目标主机进行端口检测、服务识别时使用此工具。\n"
                "支持常见端口扫描（22/80/443/3306/6379/8080等）和自定义端口范围。\n"
                "注意：仅用于授权测试，请确保有合法授权。\n\n"
                "示例:\n"
                "- 扫描常见端口: security_port_scan example.com\n"
                "- 指定端口扫描: security_port_scan example.com ports=22,80,443,8080\n"
                "- 端口范围扫描: security_port_scan example.com start_port=1 end_port=1024"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "target": {
                        "type": "string",
                        "description": "目标主机IP或域名，如 example.com 或 192.168.1.1",
                    },
                    "ports": {
                        "type": "string",
                        "description": "要扫描的端口列表，逗号分隔，如 '22,80,443,8080'",
                    },
                    "start_port": {
                        "type": "integer",
                        "description": "起始端口（端口范围模式），默认1",
                    },
                    "end_port": {
                        "type": "integer",
                        "description": "结束端口（端口范围模式），默认1024",
                    },
                },
                "required": ["target"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        target = args.get("target", "").strip()
        ports_str = args.get("ports", "")
        start_port = args.get("start_port")
        end_port = args.get("end_port")

        if not target:
            return "请提供要扫描的目标主机"

        hostname = target.split("://")[-1].split("/")[0].split(":")[0]

        try:
            ip = socket.gethostbyname(hostname)
        except socket.gaierror:
            return f"无法解析目标主机: {hostname}"

        # 确定扫描的端口列表
        if ports_str:
            try:
                ports = [int(p.strip()) for p in ports_str.split(",") if p.strip()]
            except ValueError:
                return "端口格式错误，请使用逗号分隔的数字，如 '22,80,443'"
        elif start_port is not None and end_port is not None:
            if start_port < 1 or end_port > 65535 or start_port > end_port:
                return "端口范围无效，须在 1-65535 之间且 start <= end"
            ports = list(range(start_port, end_port + 1))
        else:
            # 默认扫描常见端口
            ports = sorted(COMMON_PORTS.keys())

        if len(ports) > MAX_PORTS:
            return f"端口数量过多 ({len(ports)})，建议缩小范围（如常见端口或指定端口范围）"

        # 异步扫描
        open_ports = []
        for port in ports:
            try:
                result = await self._check_port(ip, port, timeout=CONNECT_TIMEOUT)
                if result["open"]:
                    service = COMMON_PORTS.get(port, result.get("banner", "unknown"))
                    open_ports.append(
                        {
                            "port": port,
                            "service": service,
                            "banner": result.get("banner", ""),
                        }
                    )
            except Exception as e:
                logger.debug(f"扫描端口 {ip}:{port} 出错: {e}")

        # 生成报告
        lines = [
            f"端口扫描报告",
            f"目标: {hostname} ({ip})",
            f"扫描端口数: {len(ports)}",
            f"开放端口数: {len(open_ports)}",
            "",
        ]

        if open_ports:
            lines.append("| 端口 | 服务 |")
            lines.append("|------|------|")
            for p in open_ports:
                lines.append(f"| {p['port']} | {p['service']} |")

            lines.append("")
            lines.append("开放端口详情:")
            for p in open_ports:
                banner_info = f" ({p['banner']})" if p["banner"] else ""
                lines.append(f"  - {p['port']}/tcp: {p['service']}{banner_info}")

            lines.append("")
            lines.append("建议关注:")
            if any(p["port"] == 22 for p in open_ports):
                lines.append("  - SSH(22)开放：检查是否允许密码登录，建议使用密钥认证")
            if any(p["port"] == 80 for p in open_ports):
                lines.append("  - HTTP(80)开放：检查是否强制跳转HTTPS")
            if any(p["port"] in (3306, 5432, 1433, 6379, 9200, 27017) for p in open_ports):
                lines.append("  - 数据库端口开放：检查是否暴露在公网，应限制访问来源IP")
        else:
            lines.append("未发现开放端口")

        return "\n".join(lines)

    async def _check_port(self, ip: str, port: int, timeout: float = 3.0) -> Dict[str, Any]:
        """检查单个端口是否开放"""
        loop = asyncio.get_event_loop()
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = await loop.run_in_executor(None, lambda: sock.connect_ex((ip, port)))
            if result == 0:
                banner = ""
                try:
                    sock.settimeout(BANNER_TIMEOUT)
                    data = await loop.run_in_executor(None, lambda: sock.recv(1024))
                    if data:
                        banner = data.decode("utf-8", errors="replace")[:200].strip()
                        banner = banner.replace("\r\n", " ").replace("\n", " ")
                except Exception:
                    pass
                sock.close()
                return {"open": True, "banner": banner}
            sock.close()
            return {"open": False, "banner": ""}
        except Exception as e:
            return {"open": False, "banner": str(e)}


def get_security_port_scan_tool():
    return SecurityPortScanTool()

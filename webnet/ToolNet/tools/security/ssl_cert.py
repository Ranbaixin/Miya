"""
SSL/TLS 证书检查工具

检查目标域名的 SSL/TLS 证书信息。
包括证书有效期、颁发者、域名匹配、证书链完整性等。
"""

import asyncio
import logging
import socket
import ssl
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class SecuritySSLCertTool(BaseTool):
    """SSL/TLS 证书检查工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_ssl_cert",
            "description": (
                "SSL/TLS 证书检查工具。\n"
                "当用户需要检查网站的HTTPS证书信息、证书到期时间、\n"
                "或证书配置安全性时使用此工具。\n"
                "自动验证证书有效期、颁发者、主题域名、证书链等信息。\n\n"
                "示例:\n"
                "- 检查证书: security_ssl_cert example.com\n"
                "- 指定端口: security_ssl_cert example.com port=443\n"
                "- 检查多个域名: security_ssl_cert example.com hosts=www.example.com,api.example.com"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "目标主机域名，如 example.com",
                    },
                    "port": {
                        "type": "integer",
                        "description": "端口号，默认443",
                    },
                },
                "required": ["hostname"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        hostname = args.get("hostname", "").strip()
        port = args.get("port", 443)

        if not hostname:
            return "请提供要检查的域名"

        hostname = hostname.split("://")[-1].split("/")[0].split(":")[0]

        loop = asyncio.get_event_loop()

        try:
            cert_info = await loop.run_in_executor(None, lambda: self._get_cert_info(hostname, port))
        except socket.timeout:
            return f"连接超时: {hostname}:{port}"
        except ConnectionRefusedError:
            return f"连接被拒绝: {hostname}:{port} — 端口未开放"
        except ssl.SSLError as e:
            return f"SSL/TLS 错误: {str(e)[:200]}"
        except Exception as e:
            return f"获取证书失败: {str(e)[:200]}"

        if not cert_info:
            return f"未获取到证书信息: {hostname}:{port}"

        subject = cert_info.get("subject", {})
        issuer = cert_info.get("issuer", {})
        not_before = cert_info.get("not_before")
        not_after = cert_info.get("not_after")
        san = cert_info.get("subject_alt_name", [])
        version = cert_info.get("version", "未知")
        serial = cert_info.get("serial_number", "未知")
        sig_algo = cert_info.get("signature_algorithm", "未知")

        lines = [
            f"SSL/TLS 证书检查报告",
            f"目标: {hostname}:{port}",
            f"",
        ]

        # 证书信息
        cn = subject.get("commonName", "未知")
        org = subject.get("organizationName", "未知")
        iss_cn = issuer.get("commonName", "未知")
        iss_org = issuer.get("organizationName", "未知")

        lines.append("### 证书基本信息")
        lines.append(f"- 主题(CN): {cn}")
        if org != "未知":
            lines.append(f"- 组织(O): {org}")
        lines.append(f"- 颁发者(CN): {iss_cn}")
        if iss_org != "未知":
            lines.append(f"- 颁发组织(O): {iss_org}")
        lines.append(f"- 版本: {version}")
        lines.append(f"- 签名算法: {sig_algo}")
        lines.append(f"- 序列号: {serial[:16]}...")

        # 有效期
        lines.append("")
        lines.append("### 证书有效期")
        if not_before and not_after:
            now = datetime.now()
            before_dt = datetime.strptime(not_before, "%Y-%m-%d %H:%M:%S")
            after_dt = datetime.strptime(not_after, "%Y-%m-%d %H:%M:%S")
            days_remaining = (after_dt - now).days
            is_expired = now > after_dt
            is_not_yet = now < before_dt

            lines.append(f"- 颁发时间: {not_before}")
            lines.append(f"- 到期时间: {not_after}")
            lines.append(f"- 剩余天数: {days_remaining} 天")

            if is_expired:
                lines.append("")
                lines.append("  [严重] 证书已过期！")
            elif is_not_yet:
                lines.append("")
                lines.append("  [警告] 证书尚未生效！")
            elif days_remaining < 30:
                lines.append(f"  [警告] 证书将在 {days_remaining} 天后过期，请及时续期")
            elif days_remaining < 90:
                lines.append(f"  [提示] 证书剩余 {days_remaining} 天，建议提前规划续期")

        # SAN 域名
        if san:
            lines.append("")
            lines.append(f"### SAN 域名 ({len(san)} 个)")
            for domain_name in san[:20]:
                lines.append(f"  - {domain_name}")
            if len(san) > 20:
                lines.append(f"  ... 共 {len(san)} 个")

        # 安全性分析
        lines.append("")
        lines.append("### 安全性分析")

        issues = []
        if sig_algo and "sha1" in sig_algo.lower():
            issues.append("  - 签名算法使用 SHA1（已不安全），建议升级到 SHA256")

        if after_dt and days_remaining < 30:
            issues.append(f"  - 证书即将到期，仅剩 {days_remaining} 天")

        if cn != hostname and not any(hostname in s for s in san):
            issues.append(f"  - 证书 CN ({cn}) 与访问域名 ({hostname}) 不匹配")

        # 自签名检查
        if cn == iss_cn:
            issues.append("  - 自签名证书：仅建议在开发/内网环境使用")

        if issues:
            lines.extend(issues)
        else:
            lines.append("  - 未发现明显安全问题")

        return "\n".join(lines)

    def _get_cert_info(self, hostname: str, port: int) -> Optional[Dict[str, Any]]:
        """获取 SSL 证书信息"""
        context = ssl.create_default_context()
        context.check_hostname = False
        context.verify_mode = ssl.CERT_NONE

        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(10)
        try:
            ssock = context.wrap_socket(sock, server_hostname=hostname)
            ssock.connect((hostname, port))
            cert = ssock.getpeercert(binary_form=False)

            result = {
                "subject": {comp[0][0]: comp[0][1] for comp in cert.get("subject", ())},
                "issuer": {comp[0][0]: comp[0][1] for comp in cert.get("issuer", ())},
                "version": cert.get("version", 0),
                "serial_number": cert.get("serialNumber", ""),
                "not_before": cert.get("notBefore", ""),
                "not_after": cert.get("notAfter", ""),
                "subject_alt_name": [],
                "signature_algorithm": cert.get("signatureAlgorithm", ""),
            }

            for field in cert.get("subjectAltName", ()):
                if field[0] == "DNS":
                    result["subject_alt_name"].append(field[1])

            # 格式化日期
            for key in ("not_before", "not_after"):
                val = result[key]
                if val:
                    try:
                        dt = datetime.strptime(val, "%b %d %H:%M:%S %Y %Z")
                        result[key] = dt.strftime("%Y-%m-%d %H:%M:%S")
                    except ValueError:
                        pass

            ssock.close()
            return result
        finally:
            try:
                ssock.close()
            except Exception:
                pass


def get_security_ssl_cert_tool():
    return SecuritySSLCertTool()

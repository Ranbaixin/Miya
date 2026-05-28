"""
DNS 枚举工具

枚举目标域名的 DNS 记录类型（A、AAAA、MX、NS、CNAME、TXT、SOA）。
使用标准 DNS 解析进行查询。
"""

import asyncio
import logging
import socket
from typing import Any, Dict, List

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class SecurityDNSEnumTool(BaseTool):
    """DNS 枚举工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_dns_enum",
            "description": (
                "DNS 记录枚举工具。\n"
                "当用户需要查询域名的 DNS 解析记录、邮件服务器、\n"
                "SPF/DMARC 邮件安全策略时使用此工具。\n"
                "自动查询 A/AAAA/MX/NS/CNAME/TXT/SOA 等常见记录类型。\n"
                "注意：仅用于授权测试。\n\n"
                "示例:\n"
                "- 枚举DNS记录: security_dns_enum example.com\n"
                "- 指定记录类型: security_dns_enum example.com types=A,MX,TXT"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "目标域名，如 example.com",
                    },
                    "types": {
                        "type": "string",
                        "description": "要查询的记录类型（逗号分隔），如 'A,MX,TXT'。不填则查询全部常见类型",
                    },
                },
                "required": ["domain"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        domain = args.get("domain", "").strip()
        types_str = args.get("types", "")

        if not domain:
            return "请提供要查询的目标域名"

        domain = domain.split("://")[-1].split("/")[0].split(":")[0]

        record_types = (
            [t.strip().upper() for t in types_str.split(",") if t.strip()]
            if types_str
            else ["A", "AAAA", "MX", "NS", "CNAME", "TXT", "SOA"]
        )

        results: Dict[str, List[str]] = {}
        for rtype in record_types:
            records = await self._dns_query(domain, rtype)
            if records:
                results[rtype] = records

        lines = [
            f"DNS 枚举报告",
            f"目标域名: {domain}",
            f"查询类型: {', '.join(record_types)}",
            "",
        ]

        if not results:
            return "\n".join(lines + ["未获取到任何DNS记录"])

        for rtype, records in results.items():
            lines.append(f"### {rtype} 记录")
            for r in records[:10]:
                lines.append(f"  {r}")
            if len(records) > 10:
                lines.append(f"  ... 共 {len(records)} 条")
            lines.append("")

        # 安全分析
        warnings = []
        if "MX" in results and not results["MX"]:
            warnings.append("  - 未配置 MX 记录：可能未启用企业邮箱")

        spf_found = False
        dmarc_found = False
        if "TXT" in results:
            for txt_record in results["TXT"]:
                if "v=spf1" in txt_record:
                    spf_found = True
                    if "?all" in txt_record or "+all" in txt_record:
                        warnings.append("  - SPF 策略过于宽松（使用 ?all 或 +all），建议使用 -all")
                    elif "~all" in txt_record:
                        warnings.append("  - SPF 策略使用 softfail(~all)，建议使用严格模式 -all")
                if "v=DMARC1" in txt_record:
                    dmarc_found = True

        if not spf_found:
            warnings.append("  - 未配置 SPF 记录：存在邮件伪造风险")
        if not dmarc_found:
            warnings.append("  - 未配置 DMARC 记录：建议配置以增强邮件安全")

        if warnings:
            lines.append("### 安全提醒")
            lines.extend(warnings)

        return "\n".join(lines)

    async def _dns_query(self, domain: str, record_type: str) -> List[str]:
        """执行 DNS 查询"""
        results = []
        loop = asyncio.get_event_loop()

        if record_type in ("A", "AAAA"):
            try:
                if record_type == "A":
                    info = await loop.run_in_executor(None, lambda: socket.getaddrinfo(domain, None, socket.AF_INET))
                else:
                    info = await loop.run_in_executor(None, lambda: socket.getaddrinfo(domain, None, socket.AF_INET6))
                for item in info:
                    addr = item[4][0]
                    if addr not in results:
                        results.append(addr)
            except socket.gaierror:
                pass
            return results

        if record_type in ("MX", "NS", "CNAME", "TXT", "SOA"):
            try:
                import dns.resolver

                resolver = dns.resolver.Resolver()
                resolver.timeout = 5
                resolver.lifetime = 5

                def resolve_sync():
                    answers = resolver.resolve(domain, record_type)
                    return [
                        str(rdata.to_text().strip('"') if record_type in ("TXT",) else rdata.to_text())
                        for rdata in answers
                    ]

                results = await loop.run_in_executor(None, resolve_sync)
                return results
            except ImportError:
                return ["DNS 库 (dnspython) 未安装，无法解析该记录类型"]
            except Exception as e:
                error_msg = str(e)
                if "NXDOMAIN" in error_msg:
                    pass
                else:
                    logger.debug(f"DNS 查询 {record_type} 失败: {error_msg}")
                return []
        return results


def get_security_dns_enum_tool():
    return SecurityDNSEnumTool()

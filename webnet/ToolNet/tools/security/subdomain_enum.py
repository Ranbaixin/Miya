"""
子域名枚举工具

通过 DNS 查询和字典爆破枚举目标域名的子域名。
支持自定义字典和结果验证。
"""

import asyncio
import logging
import socket
from typing import Any, Dict, List

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_subdomain_enum_config
except ImportError:
    get_subdomain_enum_config = lambda: {}

_CFG = get_subdomain_enum_config()
DEFAULT_SUBDOMAINS = _CFG.get("default_subdomains", [])
DEEP_SUBDOMAINS = _CFG.get("deep_subdomains", [])


class SecuritySubdomainEnumTool(BaseTool):
    """子域名枚举工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_subdomain_enum",
            "description": (
                "子域名枚举工具。\n"
                "当用户需要发现目标域名的子域名、资产测绘时使用此工具。\n"
                "通过DNS解析验证子域名是否存在，覆盖常见服务名称。\n"
                "注意：仅用于授权测试。\n\n"
                "示例:\n"
                "- 枚举子域名: security_subdomain_enum example.com\n"
                "- 使用自定义子域名: security_subdomain_enum example.com subdomains=dev,test,api,admin\n"
                "- 深度枚举: security_subdomain_enum example.com deep=true"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "目标域名，如 example.com",
                    },
                    "subdomains": {
                        "type": "string",
                        "description": "自定义子域名前缀列表（逗号分隔），如 'dev,test,api,admin'。不填则使用内置字典",
                    },
                    "deep": {
                        "type": "boolean",
                        "description": "是否深度枚举（使用300+子域名字典），默认false",
                    },
                },
                "required": ["domain"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        domain = args.get("domain", "").strip()
        custom_subdomains = args.get("subdomains", "")
        deep = args.get("deep", False)

        if not domain:
            return "请提供要枚举的目标域名"

        domain = domain.split("://")[-1].split("/")[0].split(":")[0]

        if custom_subdomains:
            prefixes = [s.strip().lower() for s in custom_subdomains.split(",") if s.strip()]
        elif deep:
            prefixes = DEFAULT_SUBDOMAINS + DEEP_SUBDOMAINS
        else:
            prefixes = DEFAULT_SUBDOMAINS

        # 容错：如果 DNS 解析失败，尝试降级
        found = []
        for prefix in prefixes:
            hostname = f"{prefix}.{domain}"
            try:
                ip = socket.gethostbyname(hostname)
                found.append({"hostname": hostname, "ip": ip})
            except socket.gaierror:
                pass
            except Exception as e:
                logger.debug(f"枚举 {hostname} 失败: {e}")

        lines = [
            f"子域名枚举报告",
            f"目标域名: {domain}",
            f"扫描前缀数: {len(prefixes)}",
            f"发现子域名: {len(found)}",
            "",
        ]

        if found:
            # 按类型分组
            www_found = [f for f in found if f["hostname"].startswith("www")]
            mail_found = [f for f in found if "mail" in f["hostname"]]
            dev_found = [
                f for f in found if any(kw in f["hostname"] for kw in ["dev", "test", "stage", "staging", "beta"])
            ]
            admin_found = [
                f for f in found if any(kw in f["hostname"] for kw in ["admin", "manage", "cpanel", "dashboard"])
            ]
            api_found = [f for f in found if "api" in f["hostname"]]
            other_found = [f for f in found if f not in www_found + mail_found + dev_found + admin_found + api_found]

            lines.append("| 子域名 | IP |")
            lines.append("|--------|----|")
            for f in found:
                lines.append(f"| {f['hostname']} | {f['ip']} |")

            lines.append("")
            warnings = []
            if dev_found:
                warnings.append(f"  - 发现开发/测试环境: {', '.join(f['hostname'] for f in dev_found)}")
            if admin_found:
                warnings.append(f"  - 发现管理后台（应限制访问）: {', '.join(f['hostname'] for f in admin_found)}")
            if "git." + domain in [f["hostname"] for f in found]:
                warnings.append("  - 发现Git服务：检查是否暴露.git目录")
            if "jenkins." + domain in [f["hostname"] for f in found]:
                warnings.append("  - 发现Jenkins服务：检查CI/CD安全配置")

            if warnings:
                lines.append("安全提醒:")
                lines.extend(warnings)
        else:
            lines.append("未发现任何子域名")

        return "\n".join(lines)


def get_security_subdomain_enum_tool():
    return SecuritySubdomainEnumTool()

"""
HTTP 响应头安全分析工具

检查目标 URL 的 HTTP 响应头，识别常见安全配置问题。
包括：CSP、HSTS、X-Frame-Options、X-Content-Type-Options 等。
"""

import asyncio
import logging
import ssl
from typing import Any, Dict, List, Tuple

import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_http_headers_config
except ImportError:

    def get_http_headers_config():
        return {}


_CFG = get_http_headers_config()
SECURITY_HEADER_CHECKS = _CFG.get("security_checks", [])
INFO_LEAK_HEADERS = _CFG.get("info_leak_headers", [])
REQ_TIMEOUT_HTTP = _CFG.get("request_timeout", 15.0)


class SecurityHTTPHeadersTool(BaseTool):
    """HTTP响应头安全分析工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_http_headers",
            "description": (
                "HTTP响应头安全分析工具。\n"
                "当用户需要检查网站的安全响应头配置时使用此工具。\n"
                "自动检测 CSP、HSTS、X-Frame-Options 等安全头的配置情况，\n"
                "并识别信息泄露风险（如 Server、X-Powered-By）。\n"
                "注意：仅用于授权测试。\n\n"
                "示例:\n"
                "- 分析HTTP头: security_http_headers https://example.com\n"
                "- 深度分析: security_http_headers https://example.com detail=true"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "目标 URL，如 https://example.com。必须包含协议(http/https)",
                    },
                    "detail": {
                        "type": "boolean",
                        "description": "是否显示完整响应头详情",
                    },
                },
                "required": ["url"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        url = args.get("url", "").strip()
        show_detail = args.get("detail", False)

        if not url:
            return "请提供要分析的目标URL"

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        try:
            async with httpx.AsyncClient(
                timeout=15.0,
                follow_redirects=True,
                verify=False,
            ) as client:
                response = await client.get(url)
                headers = {k.lower(): v for k, v in response.headers.items()}
        except httpx.TimeoutException:
            return f"请求超时: {url}"
        except httpx.ConnectError:
            return f"无法连接到: {url}"
        except Exception as e:
            return f"请求失败: {str(e)}"

        status_code = response.status_code
        lines = [
            f"HTTP 响应头安全分析报告",
            f"目标: {url}",
            f"状态码: {status_code}",
            "",
        ]

        # 检查安全头
        missing_headers = []
        present_headers = []

        for header_name, severity, label, advice in SECURITY_HEADER_CHECKS:
            value = headers.get(header_name)
            if value:
                present_headers.append((label, value, severity))
            else:
                missing_headers.append((label, severity, advice))

        # 检查信息泄露头
        leaking_headers = []
        for header_name, severity, label, advice in INFO_LEAK_HEADERS:
            value = headers.get(header_name)
            if value:
                leaking_headers.append((label, value, severity, advice))

        # 检查 Cookie 安全属性
        cookie_header = headers.get("set-cookie", "")
        cookie_issues = []
        if cookie_header:
            cookie_value = cookie_header if isinstance(cookie_header, str) else str(cookie_header)
            if "secure" not in cookie_value.lower():
                cookie_issues.append("Cookie 缺少 Secure 属性（仅通过HTTPS传输）")
            if "httponly" not in cookie_value.lower():
                cookie_issues.append("Cookie 缺少 HttpOnly 属性（防止JS访问）")
            if "samesite" not in cookie_value.lower():
                cookie_issues.append("Cookie 缺少 SameSite 属性（防止CSRF）")

        # 评分
        total_checks = len(SECURITY_HEADER_CHECKS) + len(INFO_LEAK_HEADERS) + (1 if cookie_header else 0)
        passed = len(present_headers) + (4 - len(leaking_headers)) + (3 - len(cookie_issues) if cookie_header else 0)
        score = min(100, int(passed / max(total_checks, 1) * 100))
        grade = "A" if score >= 90 else "B" if score >= 75 else "C" if score >= 60 else "D" if score >= 40 else "F"

        lines.append(f"## 安全评分: {grade} ({score}/100)")
        lines.append("")

        if missing_headers:
            lines.append(f"### 缺失的安全头 ({len(missing_headers)})")
            lines.append("")
            for label, severity, advice in missing_headers:
                sev_icon = "[高]" if severity == "high" else "[中]" if severity == "medium" else "[低]"
                lines.append(f"- {sev_icon} **{label}**: {advice}")

        if leaking_headers:
            lines.append("")
            lines.append(f"### 信息泄露风险 ({len(leaking_headers)})")
            lines.append("")
            for label, value, severity, advice in leaking_headers:
                lines.append(f"- **{label}**: 当前值=`{value[:80]}` → {advice}")

        if cookie_issues:
            lines.append("")
            lines.append(f"### Cookie 安全问题 ({len(cookie_issues)})")
            lines.append("")
            for issue in cookie_issues:
                lines.append(f"- {issue}")

        if present_headers:
            lines.append("")
            lines.append(f"### 已配置的安全头 ({len(present_headers)})")
            lines.append("")
            for label, value, severity in present_headers:
                lines.append(f"- {label}: `{value[:100]}`")

        if show_detail and headers:
            lines.append("")
            lines.append("### 完整响应头")
            lines.append("")
            lines.append("```")
            for key, val in sorted(headers.items()):
                lines.append(f"{key}: {val}")
            lines.append("```")

        lines.append("")
        lines.append(f"*安全评分基于 OWASP 推荐的安全头部配置标准*")

        return "\n".join(lines)


def get_security_http_headers_tool():
    return SecurityHTTPHeadersTool()

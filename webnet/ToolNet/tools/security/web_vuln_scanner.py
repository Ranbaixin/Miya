"""
Web 漏洞基础扫描工具

对目标 URL 进行基础的 Web 安全漏洞检测。
包括：SQL 注入检测点识别、XSS 反射点检测、信息泄露检查。
"""

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_web_vuln_scanner_config
except ImportError:

    def get_web_vuln_scanner_config():
        return {}


_CFG = get_web_vuln_scanner_config()
SQL_PAYLOADS = _CFG.get("sql_payloads", [])
XSS_PAYLOADS = _CFG.get("xss_payloads", [])
LEAK_PATTERNS = _CFG.get("leak_patterns", [])
SQL_ERROR_PATTERNS = _CFG.get("sql_error_patterns", [])
ERROR_PAGE_PATTERNS = _CFG.get("error_page_patterns", [])
REQ_TIMEOUT = _CFG.get("request_timeout", 15.0)

# XSS 测试 payload
XSS_PAYLOADS = [
    ("<script>alert(1)</script>", "基础XSS"),
    ("<img src=x onerror=alert(1)>", "IMG事件XSS"),
    ("<svg onload=alert(1)>", "SVG事件XSS"),
    ("javascript:alert(1)", "JS协议XSS"),
]

# 信息泄露模式
LEAK_PATTERNS = [
    (r"(?:password|passwd|pwd)\s*[:=]\s*['\"]?\w+['\"]?", "硬编码密码", "critical"),
    (r"(?:api[_-]?key|apikey|secret)\s*[:=]\s*['\"]?\w+['\"]?", "API密钥泄露", "critical"),
    (r"(?:jdbc:|mongodb://|mysql://|postgresql://|redis://)\S+", "数据库连接串泄露", "high"),
    (r"(?:aws_access_key|AWS_ACCESS_KEY)\s*[:=]\s*['\"]?\w+['\"]?", "AWS密钥泄露", "critical"),
    (r"(?:-----BEGIN\s(?:RSA\s)?PRIVATE\sKEY-----)", "私钥泄露", "critical"),
    (r"<!--[\s\S]*?(?:TODO|FIXME|HACK|BUG)[\s\S]*?-->", "注释中的敏感信息", "medium"),
    (r"stack\s*trace:", "错误堆栈泄露", "medium"),
    (r"(?:\d{1,3}\.){3}\d{1,3}", "内部IP泄露", "low"),
]


class SecurityWebVulnScannerTool(BaseTool):
    """Web 漏洞扫描工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_web_vuln_scanner",
            "description": (
                "Web 漏洞基础扫描工具。\n"
                "对目标 URL 进行基础的安全漏洞检测，包括：\n"
                "- SQL 注入检测点识别\n"
                "- XSS 反射点检测\n"
                "- 信息泄露检查（密码/密钥/连接串）\n"
                "- 错误页面分析\n"
                "注意：仅发送低危害测试 payload，不会造成实际损害。\n"
                "注意：仅用于授权测试。\n\n"
                "示例:\n"
                "- 基础扫描: security_web_vuln_scanner https://example.com/page?id=1\n"
                "- 表单扫描: security_web_vuln_scanner https://example.com/login method=POST"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "目标URL，包含查询参数如 https://example.com/page?id=1",
                    },
                    "method": {
                        "type": "string",
                        "enum": ["GET", "POST"],
                        "description": "请求方法，默认 GET",
                    },
                    "body": {
                        "type": "string",
                        "description": "POST 请求体（仅 method=POST 时使用）",
                    },
                },
                "required": ["url"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        url = args.get("url", "").strip()
        method = args.get("method", "GET").upper()
        body = args.get("body", "")

        if not url:
            return "请提供目标 URL"

        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        base_url = url
        findings: List[Dict[str, Any]] = []

        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=False,
            verify=False,
            headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0"},
        ) as client:
            # 1. 获取基准响应
            try:
                if method == "POST":
                    base_resp = await client.post(base_url, data=body or {})
                else:
                    base_resp = await client.get(base_url)
                base_body = base_resp.text
            except Exception as e:
                return f"无法访问目标: {str(e)[:200]}"

            # 2. SQL 注入检测
            if "?" in url or body:
                for payload, desc in SQL_PAYLOADS:
                    try:
                        if method == "POST":
                            test_resp = await client.post(base_url, data=body + payload if body else payload)
                        else:
                            test_url = url + payload
                            test_resp = await client.get(test_url)

                        errors = self._check_sql_errors(test_resp.text)
                        if errors:
                            findings.append(
                                {
                                    "type": "SQL 注入检测点",
                                    "payload": payload[:50],
                                    "description": desc,
                                    "evidence": errors[:200],
                                    "severity": "critical" if "syntax" not in errors.lower() else "medium",
                                }
                            )
                            break
                    except Exception:
                        pass

            # 3. XSS 反射检测
            for payload, desc in XSS_PAYLOADS:
                try:
                    if method == "POST":
                        test_resp = await client.post(base_url, data=body + payload)
                    else:
                        test_url = url + payload
                        test_resp = await client.get(test_url)

                    if payload in test_resp.text:
                        findings.append(
                            {
                                "type": "XSS 反射点",
                                "payload": payload[:30],
                                "description": desc,
                                "evidence": f"Payload 原样反射在响应中",
                                "severity": "high" if "<script>" in payload else "medium",
                            }
                        )
                        break
                except Exception:
                    pass

            # 4. 信息泄露检查
            for entry in LEAK_PATTERNS:
                pattern = entry.get("regex")
                label = entry.get("label", "")
                severity = entry.get("severity", "info")
                if not pattern:
                    continue
                matches = re.findall(pattern, base_body, re.IGNORECASE)
                if matches:
                    findings.append(
                        {
                            "type": label,
                            "description": f"在响应中发现 {len(matches)} 处匹配",
                            "evidence": str(matches[0])[:100] if isinstance(matches[0], str) else "匹配内容已脱敏",
                            "severity": severity,
                        }
                    )

            # 5. 错误页面检查
            for error_path in [
                f"{base_url.rsplit('/', 1)[0]}/nonexistent_404_test",
                f"{base_url}/'",
                f"{base_url}/%00",
            ]:
                try:
                    err_resp = await client.get(error_path)
                    error_info = self._check_error_page(err_resp.text, err_resp.status_code)
                    if error_info:
                        findings.append(error_info)
                        break
                except Exception:
                    pass

        lines = [
            f"Web 漏洞扫描报告",
            f"目标: {base_url}",
            f"请求方式: {method}",
            f"发现总数: {len(findings)}",
            "",
        ]

        if findings:
            severities = {"critical": 0, "high": 0, "medium": 0, "low": 0, "info": 0}
            for f in findings:
                severities[f.get("severity", "info")] = severities.get(f.get("severity", "info"), 0) + 1

            lines.append(
                f"严重:{severities['critical']} | 高危:{severities['high']} | "
                f"中危:{severities['medium']} | 低危:{severities['low']}"
            )
            lines.append("")

            for i, finding in enumerate(findings, 1):
                sev = finding.get("severity", "info").upper()
                lines.append(f"### {i}. [{sev}] {finding['type']}")
                lines.append(f"- 描述: {finding.get('description', 'N/A')}")
                lines.append(f"- 证据: {finding.get('evidence', 'N/A')[:200]}")
                if finding.get("payload"):
                    lines.append(f"- 测试Payload: `{finding['payload']}`")
                lines.append("")

            if severities["critical"] > 0 or severities["high"] > 0:
                lines.append("警告：发现了高危及以上风险，建议进行专业渗透测试验证。")
        else:
            lines.append("未发现明显的 Web 安全漏洞。")
            lines.append("注意：这是基础自动化检测，不能替代专业渗透测试。")

        lines.append("")
        lines.append("*仅用于授权安全评估，基础自动化检测结果仅供参考*")

        return "\n".join(lines)

    def _check_sql_errors(self, text: str) -> Optional[str]:
        for pattern in SQL_ERROR_PATTERNS:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def _check_error_page(self, text: str, status_code: int) -> Optional[Dict[str, Any]]:
        if status_code == 500:
            return {
                "type": "服务器内部错误",
                "description": "服务器返回 500 状态码",
                "evidence": f"HTTP {status_code}",
                "severity": "medium",
            }
        for entry in ERROR_PAGE_PATTERNS:
            pattern = entry.get("regex", "")
            label = entry.get("label", "")
            severity = entry.get("severity", "low")
            if pattern and re.search(pattern, text):
                return {
                    "type": label,
                    "description": f"错误页面中检测到 {label}",
                    "evidence": re.search(pattern, text).group(0)[:100] if re.search(pattern, text) else "",
                    "severity": severity,
                }
        return None


def get_security_web_vuln_scanner_tool():
    return SecurityWebVulnScannerTool()

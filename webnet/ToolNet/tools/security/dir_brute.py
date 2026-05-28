"""
目录爆破工具

对目标 Web 服务器进行目录/文件路径枚举。
使用内置字典检测常见路径是否存在。
"""

import asyncio
import logging
from typing import Any, Dict, List

import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_dir_brute_config
except ImportError:
    get_dir_brute_config = lambda: {}

_CFG = get_dir_brute_config()
COMMON_PATHS = _CFG.get("common_paths", [])
COMMON_EXTENSIONS = _CFG.get("common_extensions", [])
MAX_CONCURRENT = _CFG.get("max_concurrent", 10)
MAX_PATHS_QUICK = _CFG.get("max_paths_quick", 40)
MAX_PATHS_DEEP = _CFG.get("max_paths_deep", 80)
REQ_TIMEOUT = _CFG.get("request_timeout", 10.0)
CRITICAL_PATHS = _CFG.get("critical_paths", [])
ATTENTION_PATHS = _CFG.get("attention_paths", [])


class SecurityDirBruteTool(BaseTool):
    """目录爆破工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_dir_brute",
            "description": (
                "Web 目录/文件枚举工具。\n"
                "对目标 Web 服务器进行常见的目录和文件路径探测。\n"
                "使用内置 70+ 字典检测管理后台、配置文件、备份文件等。\n"
                "注意：较高频次的请求可能触发 WAF 或速率限制。\n"
                "注意：仅用于授权测试。\n\n"
                "示例:\n"
                "- 基础扫描: security_dir_brute https://example.com\n"
                "- 自定义路径: security_dir_brute https://example.com paths='/admin,/api,/config'\n"
                "- 检测备份: security_dir_brute https://example.com deep=true"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "目标URL，如 https://example.com",
                    },
                    "paths": {
                        "type": "string",
                        "description": "自定义路径列表（逗号分隔），如 '/admin,/api,/config'",
                    },
                    "deep": {
                        "type": "boolean",
                        "description": "深度扫描（增加备份文件扩展名检测，请求量更大）",
                    },
                },
                "required": ["url"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        url = args.get("url", "").strip()
        custom_paths = args.get("paths", "")
        deep = args.get("deep", False)

        if not url:
            return "请提供目标 URL"

        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        base_url = url.rstrip("/")

        if custom_paths:
            paths = [p.strip() for p in custom_paths.split(",") if p.strip()]
        else:
            paths = COMMON_PATHS.copy()
            if deep:
                extra_paths = []
                for p in COMMON_PATHS:
                    for ext in COMMON_EXTENSIONS:
                        extra_paths.append(p + ext)
                paths.extend(extra_paths)

        max_requests = 40 if not deep else 80
        if len(paths) > max_requests:
            paths = paths[:max_requests]

        found: List[Dict[str, Any]] = []
        sem = asyncio.Semaphore(10)

        async with httpx.AsyncClient(timeout=10.0, follow_redirects=False, verify=False) as client:

            async def check_path(path: str):
                async with sem:
                    try:
                        resp = await client.get(
                            f"{base_url}{path}",
                            headers={
                                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; rv:120.0) Gecko/20100101 Firefox/120.0",
                            },
                        )
                        if resp.status_code in (200, 301, 302, 403, 401, 500):
                            found.append(
                                {
                                    "path": path,
                                    "status": resp.status_code,
                                    "length": len(resp.content),
                                    "redirect": resp.headers.get("location", ""),
                                    "server": resp.headers.get("server", ""),
                                }
                            )
                    except Exception:
                        pass

            tasks = [check_path(p) for p in paths]
            await asyncio.gather(*tasks)

        # 过滤可能的误报（404 页面返回 200 的情况）
        if found:
            lengths = [f["length"] for f in found if f["status"] == 200]
            if lengths:
                most_common_len = max(set(lengths), key=lengths.count)
                found = [
                    f for f in found if not (f["status"] == 200 and f["length"] == most_common_len and len(lengths) > 3)
                ]

        found.sort(key=lambda x: x["status"])

        lines = [
            f"目录爆破报告",
            f"目标: {base_url}",
            f"扫描路径数: {len(paths)}",
            f"发现总数: {len(found)}",
            "",
        ]

        if found:
            lines.append("| 状态码 | 路径 | 大小 | 跳转 |")
            lines.append("|--------|------|------|------|")
            for f in found:
                length_kb = f"{(f['length'] / 1024):.1f}KB" if f["length"] > 1024 else f"{f['length']}B"
                redirect = f["redirect"][:30] if f["redirect"] else "-"
                lines.append(f"| {f['status']} | {f['path']} | {length_kb} | {redirect} |")

            lines.append("")
            lines.append("关注发现:")
            for f in found:
                matched = False
                for cp in CRITICAL_PATHS:
                    if cp[0] == f["path"]:
                        lines.append(f"  [严重] {f['path']} - {cp[1]}")
                        matched = True
                        break
                if matched:
                    continue
                for ap in ATTENTION_PATHS:
                    if ap[0] == f["path"]:
                        lines.append(f"  [注意] {f['path']} - {ap[1]}")
                        matched = True
                        break
                if matched:
                    continue
                if f["path"].endswith(tuple(COMMON_EXTENSIONS)):
                    lines.append(f"  [警告] {f['path']} - 备份文件可能含有敏感信息")
        else:
            lines.append("未发现任何可访问路径（404/超时）")

        lines.append(f"\n*扫描用时取决于目标响应速度，未包含所有可能路径*")

        return "\n".join(lines)


def get_security_dir_brute_tool():
    return SecurityDirBruteTool()

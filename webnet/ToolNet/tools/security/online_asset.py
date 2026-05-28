"""
在线资产搜索工具

集成 FOFA、Shodan、Censys 等网络空间搜索引擎。
通过 API 接口查询互联网暴露的设备和资产信息。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_online_asset_config
except ImportError:

    def get_online_asset_config():
        return {}


_CFG = get_online_asset_config()
SUPPORTED_SERVICES = _CFG.get("supported_services", {})
REQ_TIMEOUT_OA = _CFG.get("request_timeout", 20.0)


class SecurityOnlineAssetTool(BaseTool):
    """在线资产搜索工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_online_asset",
            "description": (
                "互联网资产搜索引擎工具。\n"
                "当用户需要在全球互联网上搜索目标资产、开放服务、设备信息时使用此工具。\n"
                "支持 FOFA / Shodan / Censys / Quake / ZoomEye 五种搜索引擎。\n"
                "需要配置对应服务的 API Key（在 config/system_constants.json 中设置）。\n"
                "注意：仅用于授权测试，查询结果遵循各平台使用条款。\n\n"
                "示例:\n"
                "- FOFA搜索: security_online_asset service=fofa query='domain=example.com'\n"
                "- Shodan搜索: security_online_asset service=shodan query='apache port:80'\n"
                "- 显示可用服务: security_online_asset service=list"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "service": {
                        "type": "string",
                        "enum": ["fofa", "shodan", "censys", "quake", "zoomeye", "list"],
                        "description": "搜索引擎: fofa/shodan/censys/quake/zoomeye 或 list 查看可用服务",
                    },
                    "query": {
                        "type": "string",
                        "description": "搜索查询语句，如 'domain=example.com' 或 'apache port:80'",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回结果数上限，默认10",
                    },
                },
                "required": [],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        service = args.get("service", "list").strip().lower()
        query = args.get("query", "").strip()
        limit = args.get("limit", 10)

        if service == "list":
            return self._list_services()

        if service not in SUPPORTED_SERVICES:
            return f"不支持的搜索引擎: {service}\n{self._list_services()}"

        if not query:
            return f"请提供搜索查询。各引擎语法示例:\n- FOFA: domain=example.com\n- Shodan: apache port:80\n- Censys: services.service_name=HTTP"

        svc = SUPPORTED_SERVICES[service]
        lines = [
            f"在线资产搜索报告",
            f"引擎: {svc['name']} ({svc['desc']})",
            f"查询: {query}",
            "",
        ]

        try:
            api_key = self._get_api_key(service)
            if not api_key:
                lines.append(
                    f"[警告] 未配置 {svc['name']} API Key。\n"
                    f"请在 config/system_constants.json 中设置: security.{service}_api_key\n"
                    f"获取方式:\n"
                    f"  - FOFA: https://fofa.info/ (注册后获取)\n"
                    f"  - Shodan: https://account.shodan.io/ (注册后获取)\n"
                    f"  - Censys: https://search.censys.io/account/api\n"
                    f"  - Quake: https://quake.360.cn/\n"
                    f"  - ZoomEye: https://www.zoomeye.org/"
                )
                return "\n".join(lines)

            results = await self._search_service(service, query, api_key, limit)
            lines.append(f"结果数: {results.get('total', len(results.get('items', [])))}")
            lines.append("")

            items = results if isinstance(results, list) else results.get("items", [])
            if not items:
                lines.append("未找到匹配结果")

            for i, item in enumerate(items[:limit], 1):
                ip = item.get("ip", item.get("ip_str", ""))
                port = item.get("port", "")
                org = item.get("org", item.get("isp", ""))
                hostname = item.get("hostnames", item.get("domains", []))
                if isinstance(hostname, list):
                    hostname = hostname[0] if hostname else ""

                lines.append(f"**{i}. {ip}:{port}**")
                if hostname:
                    lines.append(f"   - 域名: {hostname}")
                if org:
                    lines.append(f"   - 组织: {org}")
                if item.get("product"):
                    lines.append(f"   - 产品: {item.get('product', '')} {item.get('version', '')}")
                if item.get("os"):
                    lines.append(f"   - 系统: {item.get('os', '')}")
                lines.append(f"   - 时间: {item.get('timestamp', item.get('updated_at', ''))}")
                lines.append("")

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                lines.append(f"API Key 验证失败。请检查 {service} API Key 配置是否正确。")
            elif e.response.status_code == 429:
                lines.append("API 请求达到速率限制，请稍后重试。")
            else:
                lines.append(f"API 请求失败: HTTP {e.response.status_code}")
        except Exception as e:
            logger.error(f"{service} 搜索失败: {e}")
            lines.append(f"搜索失败: {str(e)[:200]}")

        lines.append(f"*数据来源: {svc['name']} 网络空间搜索引擎*")
        return "\n".join(lines)

    def _list_services(self) -> str:
        lines = ["支持的在线资产搜索引擎:", ""]
        for key, svc in SUPPORTED_SERVICES.items():
            lines.append(f"  - **{key}** ({svc.get('name', key)}): {svc.get('desc', '')}")
            lines.append(f"    认证: {svc.get('auth_type', 'api_key')}")
            if svc.get("register_url"):
                lines.append(f"    注册: {svc.get('register_url')}")
        lines.append("")
        lines.append("使用方式: security_online_asset service=<引擎> query=<查询>")
        lines.append("配置 API Key: config/system_constants.json → security.{服务名}_api_key")
        return "\n".join(lines)

    def _get_api_key(self, service: str) -> Optional[str]:
        """从配置文件获取 API Key"""
        try:
            import json
            from pathlib import Path

            constants_path = Path(__file__).parent.parent.parent.parent.parent / "config" / "system_constants.json"
            if constants_path.exists():
                with open(constants_path, "r", encoding="utf-8") as f:
                    constants = json.load(f)
                keys = constants.get("security", {})
                key_map = {
                    "fofa": keys.get("fofa_api_key", keys.get("fofa_email")),
                    "shodan": keys.get("shodan_api_key"),
                    "censys": (keys.get("censys_api_id"), keys.get("censys_api_secret")),
                    "quake": keys.get("quake_api_key"),
                    "zoomeye": keys.get("zoomeye_api_key"),
                }
                return key_map.get(service)
        except Exception:
            pass
        return None

    async def _search_service(self, service: str, query: str, api_key: Any, limit: int) -> Dict[str, Any]:
        """调用各搜索引擎 API"""
        headers = {"User-Agent": "Miya-SecurityNet/1.0"}
        timeout = REQ_TIMEOUT_OA

        async with httpx.AsyncClient(timeout=timeout) as client:
            if service == "fofa":
                email = api_key if isinstance(api_key, str) else ""
                key = ""
                if isinstance(api_key, dict):
                    email = api_key.get("email", "")
                    key = api_key.get("key", "")

                resp = await client.get(
                    SUPPORTED_SERVICES["fofa"]["base_url"],
                    params={
                        "email": email,
                        "key": key,
                        "qbase64": query,
                        "size": min(limit, 100),
                    },
                )
                data = resp.json()
                return {"items": data.get("results", []), "total": data.get("size", 0)}

            elif service == "shodan":
                key = api_key if isinstance(api_key, str) else ""
                resp = await client.get(
                    SUPPORTED_SERVICES["shodan"]["base_url"],
                    params={"key": key, "query": query, "minify": True},
                )
                data = resp.json()
                matches = data.get("matches", [])
                items = [
                    {
                        "ip": m.get("ip_str", ""),
                        "port": m.get("port", ""),
                        "org": m.get("org", ""),
                        "hostnames": m.get("hostnames", []),
                        "product": m.get("product", ""),
                        "os": m.get("os", ""),
                        "timestamp": m.get("timestamp", ""),
                    }
                    for m in matches
                ]
                return {"items": items, "total": data.get("total", len(items))}

            elif service == "censys":
                api_id, api_secret = api_key if isinstance(api_key, tuple) else ("", "")
                auth = httpx.BasicAuth(api_id, api_secret)
                resp = await client.post(
                    SUPPORTED_SERVICES["censys"]["base_url"],
                    json={"q": query, "per_page": min(limit, 50)},
                    auth=auth,
                )
                data = resp.json()
                hits = data.get("result", {}).get("hits", [])
                items = [
                    {
                        "ip": h.get("ip", ""),
                        "port": (h.get("services", [{}]) or [{}])[0].get("port", ""),
                        "timestamp": h.get("updated_at", ""),
                    }
                    for h in hits
                ]
                return {"items": items, "total": data.get("result", {}).get("total", 0)}

            elif service == "quake":
                key = api_key if isinstance(api_key, str) else ""
                headers["X-QuakeToken"] = key
                resp = await client.get(
                    SUPPORTED_SERVICES["quake"]["base_url"],
                    params={"query": query, "size": min(limit, 50)},
                    headers=headers,
                )
                data = resp.json()
                return {"items": data.get("data", []), "total": data.get("meta", {}).get("total", 0)}

            elif service == "zoomeye":
                key = api_key if isinstance(api_key, str) else ""
                headers["API-KEY"] = key
                resp = await client.get(
                    SUPPORTED_SERVICES["zoomeye"]["base_url"],
                    params={"query": query, "page": 1, "pagesize": min(limit, 50)},
                    headers=headers,
                )
                data = resp.json()
                return {"items": data.get("matches", []), "total": data.get("total", 0)}

        return {"items": [], "total": 0}


def get_security_online_asset_tool():
    return SecurityOnlineAssetTool()

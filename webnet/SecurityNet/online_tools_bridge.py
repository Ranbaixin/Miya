"""
Online_tools (HexStrike) 桥接模块

将弥娅 SecurityNet 连接到 HexStrike 的 160+ REST API 端点，
使 308+ 安全工具可通过弥娅的安全中心直接访问。

HexStrike 服务地址可通过环境变量 MIYA_HEXSTRIKE_URL 配置，
例如: http://localhost:9090
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_HEXSTRIKE_URL = os.environ.get("MIYA_HEXSTRIKE_URL", "http://localhost:9090")
_TIMEOUT = float(os.environ.get("MIYA_HEXSTRIKE_TIMEOUT", "30"))


class HexStrikeClient:
    """HexStrike / Online_tools HTTP API 客户端

    连接到 hexstrike_server.py (Flask) 服务。
    所有调用都是 fire-and-forget + graceful fallback 模式。
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or _HEXSTRIKE_URL).rstrip("/")
        self.available = False
        self._session = None

    async def _ensure_session(self):
        if self._session is None:
            import aiohttp

            self._session = aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=_TIMEOUT))

    async def health_check(self) -> bool:
        """检查 HexStrike 服务是否可用"""
        try:
            await self._ensure_session()
            async with self._session.get(f"{self.base_url}/health") as resp:
                self.available = resp.status == 200
            return self.available
        except Exception:
            self.available = False
            return False

    async def call_tool(self, tool_name: str, params: Dict[str, Any]) -> Optional[str]:
        """调用 HexStrike 工具

        Args:
            tool_name: 工具名称 (如 "nmap", "nuclei", "sqlmap")
            params: 工具参数 (target, url, domain 等)

        Returns:
            工具执行结果文本，或 None
        """
        if not self.available:
            return None

        try:
            await self._ensure_session()
            endpoint = f"{self.base_url}/api/tools/{tool_name}"
            async with self._session.post(endpoint, json=params) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    logger.warning(f"HexStrike [{tool_name}] 返回 {resp.status}: {body[:200]}")
                    return None
                data = await resp.json()
                return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.debug(f"HexStrike [{tool_name}] 调用失败: {e}")
            return None

    async def intelligence_analyze(self, target: str) -> Optional[str]:
        """AI 智能分析目标"""
        try:
            await self._ensure_session()
            async with self._session.post(
                f"{self.base_url}/api/intelligence/analyze-target", json={"target": target}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as __e:
            logger.debug(f"[online_tools_bridge] 分析目标失败: {__e}")
        return None

    async def smart_scan(self, target: str, mode: str = "quick") -> Optional[str]:
        """AI 智能全自动扫描"""
        try:
            await self._ensure_session()
            async with self._session.post(
                f"{self.base_url}/api/intelligence/smart-scan", json={"target": target, "mode": mode}
            ) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    return json.dumps(data, ensure_ascii=False, indent=2)
        except Exception as __e:
            logger.debug(f"[online_tools_bridge] 智能扫描失败: {__e}")
        return None

    async def search_tools(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """搜索 HexStrike 工具目录"""
        try:
            await self._ensure_session()
            async with self._session.get(
                f"{self.base_url}/api/intelligence/select-tools", params={"query": query}
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as __e:
            logger.debug(f"[online_tools_bridge] 搜索工具失败: {__e}")
        return None

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None


# 全局单例
_hexstrike: Optional[HexStrikeClient] = None


def get_hexstrike_client() -> HexStrikeClient:
    global _hexstrike
    if _hexstrike is None:
        _hexstrike = HexStrikeClient()
    return _hexstrike


async def try_hexstrike_tool(tool_name: str, params: Dict[str, Any]) -> Optional[str]:
    """尝试通过 HexStrike 执行安全工具（graceful fallback）"""
    client = get_hexstrike_client()
    if not client.available:
        await client.health_check()
    if not client.available:
        return None
    return await client.call_tool(tool_name, params)


# 弥娅安全工具 → HexStrike 工具名映射
MIYA_TO_HEXSTRIKE: Dict[str, str] = {
    "security_port_scan": "nmap",
    "security_nmap_scan": "nmap-advanced",
    "security_subdomain_enum": "subfinder",
    "security_dns_enum": "naabu",
    "security_http_headers": "httpx",
    "security_ssl_cert": "nuclei",
    "security_vuln_lookup": "nuclei",
    "security_sploitus_search": "nuclei",
    "security_dir_brute": "gobuster",
    "security_web_vuln_scanner": "nuclei",
    "security_sandbox_exec": "metasploit",
}

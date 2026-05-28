"""
PentAGI 桥接模块

将弥娅 SecurityNet 连接到 PentAGI 的多智能体渗透测试框架。
PentAGI 提供 GraphQL API 和 REST API，本模块作为客户端桥接。

PentAGI 服务地址可通过环境变量 MIYA_PENTAGI_URL 配置，
例如: https://localhost:8443
"""

import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

_PENTAGI_URL = os.environ.get("MIYA_PENTAGI_URL", "https://localhost:8443")
_TIMEOUT = float(os.environ.get("MIYA_PENTAGI_TIMEOUT", "60"))


class PentAGIClient:
    """PentAGI HTTP / GraphQL 客户端

    PentAGI 的 REST API 在 /api/v1/ 下，GraphQL 在 /api/v1/graphql。
    通过环境变量 MIYA_PENTAGI_TOKEN 配置 API Token。
    """

    def __init__(self, base_url: Optional[str] = None):
        self.base_url = (base_url or _PENTAGI_URL).rstrip("/")
        self.token = os.environ.get("MIYA_PENTAGI_TOKEN", "")
        self.available = False
        self._session = None

    async def _ensure_session(self):
        if self._session is None:
            import aiohttp
            import ssl

            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=_TIMEOUT),
            )

    @property
    def _headers(self) -> Dict[str, str]:
        h = {"Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    async def health_check(self) -> bool:
        """检查 PentAGI 服务是否可用"""
        try:
            await self._ensure_session()
            async with self._session.get(
                f"{self.base_url}/api/v1/info",
                headers=self._headers,
            ) as resp:
                self.available = resp.status == 200
            return self.available
        except Exception:
            self.available = False
            return False

    async def graphql_query(self, query: str, variables: Optional[Dict] = None) -> Optional[Dict]:
        """执行 GraphQL 查询"""
        if not self.available:
            return None
        try:
            await self._ensure_session()
            payload = {"query": query}
            if variables:
                payload["variables"] = variables
            async with self._session.post(
                f"{self.base_url}/api/v1/graphql",
                json=payload,
                headers=self._headers,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as e:
            logger.debug(f"PentAGI GraphQL 查询失败: {e}")
        return None

    async def create_flow(
        self, title: str, model: str = "gpt-4o", provider: str = "openai"
    ) -> Optional[Dict[str, Any]]:
        """创建一个新的渗透测试任务"""
        mutation = """
        mutation createFlow($input: FlowCreateInput!) {
            createFlow(input: $input) {
                id
                title
                status
                model
            }
        }
        """
        variables = {
            "input": {
                "title": title,
                "model": model,
                "model_provider_name": provider,
            }
        }
        result = await self.graphql_query(mutation, variables)
        if result and "data" in result:
            flow = result["data"].get("createFlow")
            logger.info(f"PentAGI: 创建测试任务 {title} (ID: {flow.get('id')})")
            return flow
        return None

    async def create_assistant(self, flow_id: str, title: str, model: str = "gpt-4o") -> Optional[Dict[str, Any]]:
        """创建交互式助手"""
        mutation = """
        mutation createAssistant($input: AssistantCreateInput!) {
            createAssistant(input: $input) {
                id
                title
                status
            }
        }
        """
        variables = {"input": {"flow_id": flow_id, "title": title, "model": model}}
        return await self.graphql_query(mutation, variables)

    async def list_providers(self) -> Optional[List[Dict]]:
        """列出可用的 LLM providers"""
        try:
            await self._ensure_session()
            async with self._session.get(
                f"{self.base_url}/api/v1/providers",
                headers=self._headers,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as __e:
            logger.debug(f"[pentagi_bridge] 获取providers失败: {__e}")
        return None

    async def get_usage_stats(self) -> Optional[Dict]:
        """获取使用统计"""
        try:
            await self._ensure_session()
            async with self._session.get(
                f"{self.base_url}/api/v1/usage",
                headers=self._headers,
            ) as resp:
                if resp.status == 200:
                    return await resp.json()
        except Exception as __e:
            logger.debug(f"[pentagi_bridge] 获取usage失败: {__e}")
        return None

    async def close(self):
        if self._session:
            await self._session.close()
            self._session = None


# 全局单例
_pentagi: Optional[PentAGIClient] = None


def get_pentagi_client() -> PentAGIClient:
    global _pentagi
    if _pentagi is None:
        _pentagi = PentAGIClient()
    return _pentagi


async def try_pentagi_penetration_test(target: str) -> Optional[str]:
    """尝试通过 PentAGI 启动自动化渗透测试（graceful fallback）"""
    client = get_pentagi_client()
    if not client.available:
        await client.health_check()
    if not client.available:
        return None

    flow = await client.create_flow(
        title=f"Miya Security Audit: {target}",
        model="gpt-4o",
        provider="openai",
    )
    if flow:
        return json.dumps(
            {
                "source": "PentAGI",
                "flow_id": flow.get("id"),
                "status": flow.get("status"),
                "message": "自动化渗透测试任务已创建，正在由 AI Agent 团队执行",
            },
            ensure_ascii=False,
            indent=2,
        )
    return None

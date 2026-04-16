"""
弥娅功能适配层 - 为桌面端提供弥娅核心功能
支持双端口连接:
- localhost:8000 (Web API) - 聊天
- localhost:8001 (Runtime API) - 完整功能(personality, tools等)
"""

import logging
import httpx
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

CHAT_API_BASE = "http://localhost:8000"
RUNTIME_API_BASE = "http://localhost:8001"


class MiyaFeatureAdapter:
    """弥娅功能适配器"""

    def __init__(self):
        self.chat_base = CHAT_API_BASE
        self.runtime_base = RUNTIME_API_BASE
        logger.info("[MiyaAdapter] 双端口适配器已初始化")

    def _request(
        self,
        method: str,
        endpoint: str,
        data: Optional[Dict] = None,
        use_runtime: bool = False,
    ) -> Dict:
        """发送请求"""
        base = self.runtime_base if use_runtime else self.chat_base
        url = f"{base}{endpoint}"
        try:
            if method == "GET":
                resp = httpx.get(url, timeout=10)
            else:
                resp = httpx.post(url, json=data or {}, timeout=30)
            return resp.json() if resp.status_code == 200 else {}
        except Exception as e:
            logger.error(f"API请求失败: {e}")
            return {"error": str(e)}

    def chat(
        self, message: str, session_id: str = "desktop", platform: str = "desktop"
    ) -> Dict:
        return self._request(
            "POST",
            "/api/chat",
            {"message": message, "session_id": session_id, "platform": platform},
        )

    def get_chat_status(self) -> Dict:
        return self._request("GET", "/api/status")

    def get_status(self) -> Dict:
        return self._request("GET", "/api/status", use_runtime=True)

    def get_identity(self) -> Dict:
        status = self.get_status()
        return status.get("identity", {})

    def get_emotion(self) -> Dict:
        status = self.get_status()
        return status.get("emotion", {})

    def get_personality(self) -> Dict:
        return self._request("GET", "/api/miya/personality", use_runtime=True)

    def get_memory(self) -> Dict:
        return self._request("GET", "/api/miya/memory", use_runtime=True)

    def get_tools(self) -> list:
        result = self._request("GET", "/api/miya/tools", use_runtime=True)
        return result.get("tools", [])

    def get_models(self) -> list:
        result = self._request("GET", "/api/miya/models", use_runtime=True)
        return result.get("models", [])


_miya_adapter: Optional[MiyaFeatureAdapter] = None


def get_miya_adapter() -> MiyaFeatureAdapter:
    global _miya_adapter
    if _miya_adapter is None:
        _miya_adapter = MiyaFeatureAdapter()
    return _miya_adapter


def miya_chat(message: str, session_id: str = "desktop") -> str:
    result = get_miya_adapter().chat(message, session_id, "desktop")
    return result.get("response", result.get("error", "发送失败"))


def get_miya_personality() -> Dict:
    return get_miya_adapter().get_personality()


def get_miya_emotion() -> Dict:
    return get_miya_adapter().get_emotion()


def get_miya_tools() -> list:
    return get_miya_adapter().get_tools()


def get_miya_identity() -> Dict:
    return get_miya_adapter().get_identity()

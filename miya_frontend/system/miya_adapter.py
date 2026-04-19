"""
弥娅功能适配层 - 为桌面端提供弥娅核心功能
统一接口层，自动检测并连接弥娅后端服务

特性:
- 自动检测可用端口(8000/8001)
- 双端口协同: Web API(聊天) + Runtime API(管理)
- 完整的类型提示
- 连接状态检测
"""

import logging
import socket
import httpx
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

# 默认端口
DEFAULT_CHAT_PORT = 8000
DEFAULT_RUNTIME_PORT = 8001
REQUEST_TIMEOUT = 30


def find_available_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """查找可用的 API 端口，优先检测8003"""
    # 优先检测常用端口
    for port in [8003, 8000, 8001, 8002, 8004, 8005]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    try:
                        resp = httpx.get(
                            f"http://127.0.0.1:{port}/api/health", timeout=1
                        )
                        if resp.status_code == 200:
                            logger.info(f"[MiyaAdapter] 检测到可用API端口: {port}")
                            return port
                    except:
                        pass
        except:
            pass
    return 8003  # 默认返回8003


class MiyaFeatureAdapter:
    """弥娅功能适配器 - 统一接口层"""

    def __init__(self, chat_port: int = None, runtime_port: int = None):
        # 自动检测可用端口
        self.chat_port = chat_port or find_available_port(DEFAULT_CHAT_PORT)
        self.runtime_port = runtime_port or find_available_port(DEFAULT_RUNTIME_PORT)

        self.chat_base = f"http://localhost:{self.chat_port}"
        self.runtime_base = f"http://localhost:{self.runtime_port}"

        self._connected = False
        self._check_connection()

        logger.info(
            f"[MiyaAdapter] 初始化完成 - Chat: {self.chat_port}, Runtime: {self.runtime_port}"
        )

    def _check_connection(self):
        """检查连接状态"""
        try:
            resp = httpx.get(f"{self.chat_base}/api/health", timeout=5)
            self._connected = resp.status_code == 200
        except:
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

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

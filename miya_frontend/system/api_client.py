"""
弥娅前端 API 客户端
提供统一的接口连接弥娅核心服务
"""

import json
import logging
import asyncio
import socket
from typing import Optional, Dict, Any, Callable
from urllib.request import Request, urlopen, URLError
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

# API 配置
DEFAULT_API_BASE = "http://localhost:8000"
DEFAULT_TIMEOUT = 30


def find_available_api_port(start_port: int = 8000, max_attempts: int = 10) -> int:
    """查找可用的 API 端口"""
    # 优先检测常用端口
    for port in [8003, 8000, 8001, 8002, 8004, 8005]:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(0.5)
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    # 端口可用，尝试发送请求确认是弥娅 API
                    try:
                        import httpx

                        resp = httpx.get(
                            f"http://127.0.0.1:{port}/api/status", timeout=1
                        )
                        if resp.status_code == 200:
                            logger.info(f"[API] 找到可用的弥娅 API 端口: {port}")
                            return port
                    except:
                        pass
        except:
            pass
    return 8003  # 返回默认端口


class MiyaAPIClient:
    """弥娅 API 客户端"""

    def __init__(
        self,
        api_base: str = None,
        timeout: int = DEFAULT_TIMEOUT,
        platform: str = "desktop",
    ):
        # 自动检测可用端口
        if api_base is None:
            port = find_available_api_port()
            api_base = f"http://localhost:{port}"
        self.api_base = api_base.rstrip("/")
        self.timeout = timeout
        self.platform = platform
        self._emotion_callback: Optional[Callable] = None
        self._message_callback: Optional[Callable] = None
        logger.info(f"[MiyaAPIClient] 连接到: {self.api_base}")

    def set_emotion_callback(self, callback: Callable):
        """设置情绪回调"""
        self._emotion_callback = callback

    def set_message_callback(self, callback: Callable):
        """设置消息回调"""
        self._message_callback = callback

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """同步 POST 请求"""
        url = f"{self.api_base}{endpoint}"
        try:
            body = json.dumps(data).encode("utf-8")
            req = Request(
                url,
                data=body,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urlopen(req, timeout=self.timeout) as response:
                return json.loads(response.read().decode("utf-8"))
        except URLError as e:
            logger.error(f"API 请求失败: {e}")
            return {"status": "error", "error": str(e)}
        except Exception as e:
            logger.error(f"未知错误: {e}")
            return {"status": "error", "error": str(e)}

    def _post_async(self, endpoint: str, data: Dict[str, Any]) -> asyncio.Task:
        """异步 POST 请求"""
        return asyncio.create_task(self._post_async_core(endpoint, data))

    async def _post_async_core(
        self, endpoint: str, data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """异步 POST 请求核心"""
        import httpx

        url = f"{self.api_base}{endpoint}"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=data)
                return response.json()
        except Exception as e:
            logger.error(f"API 请求失败: {e}")
            return {"status": "error", "error": str(e)}

    def chat(
        self,
        message: str,
        session_id: str = "desktop",
        user_id: str = "desktop_user",
    ) -> Dict[str, Any]:
        """同步聊天"""
        return self._post(
            "/api/chat",
            {
                "message": message,
                "session_id": session_id,
                "user_id": user_id,
                "platform": self.platform,
            },
        )

    async def chat_async(
        self,
        message: str,
        session_id: str = "desktop",
        user_id: str = "desktop_user",
    ) -> Dict[str, Any]:
        """异步聊天"""
        import httpx

        url = f"{self.api_base}/api/chat"
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json={
                        "message": message,
                        "session_id": session_id,
                        "user_id": user_id,
                        "platform": self.platform,
                    },
                )
                result = response.json()

                # 处理情绪回调
                if self._emotion_callback and "emotion" in result:
                    try:
                        self._emotion_callback(result["emotion"])
                    except Exception as e:
                        logger.warning(f"情绪回调失败: {e}")

                return result
        except Exception as e:
            logger.error(f"聊天请求失败: {e}")
            return {"status": "error", "error": str(e)}

    def send_message(
        self,
        message: str,
        target_id: str = "desktop_user",
    ) -> Dict[str, Any]:
        """发送消息到客户端"""
        return self._post(
            "/api/frontend/send",
            {
                "message": message,
                "target_id": target_id,
                "platform": self.platform,
            },
        )

    def get_status(self) -> Dict[str, Any]:
        """获取系统状态"""
        return self._post("/api/status", {})

    def get_models(self) -> Dict[str, Any]:
        """获取可用模型"""
        return self._post("/api/miya/models", {})

    def get_personality(self) -> Dict[str, Any]:
        """获取当前人格"""
        return self._post("/api/miya/personality", {})

    def switch_personality(self, personality: str) -> Dict[str, Any]:
        """切换人格"""
        return self._post(
            "/api/miya/personality",
            {"personality": personality},
        )

    def get_memory(self, limit: int = 10) -> Dict[str, Any]:
        """获取记忆"""
        return self._post(
            "/api/miya/memory",
            {"limit": limit},
        )

    def get_tools(self) -> Dict[str, Any]:
        """获取可用工具"""
        return self._post("/api/miya/tools", {})


class MiyaAPIConnection:
    """API 连接管理器 - 负责与弥娅核心服务保持连接"""

    def __init__(self, client: Optional[MiyaAPIClient] = None):
        self.client = client or MiyaAPIClient()
        self._connected = False
        self._last_heartbeat = 0

    def is_connected(self) -> bool:
        """检查连接状态"""
        try:
            status = self.client.get_status()
            self._connected = status.get("status") == "success"
            return self._connected
        except:
            self._connected = False
            return False

    async def connect(self) -> bool:
        """异步连接"""
        try:
            status = await asyncio.wait_for(
                asyncio.to_thread(self.client.get_status),
                timeout=5,
            )
            self._connected = status.get("status") == "success"
            return self._connected
        except:
            self._connected = False
            return False

    @property
    def connected(self) -> bool:
        return self._connected


# 全局实例
_api_client: Optional[MiyaAPIClient] = None


def get_api_client() -> MiyaAPIClient:
    """获取全局 API 客户端"""
    global _api_client
    if _api_client is None:
        _api_client = MiyaAPIClient()
    return _api_client


def init_api_client(
    api_base: str = DEFAULT_API_BASE,
    platform: str = "desktop",
    timeout: int = DEFAULT_TIMEOUT,
) -> MiyaAPIClient:
    """初始化 API 客户端"""
    global _api_client
    _api_client = MiyaAPIClient(
        api_base=api_base,
        platform=platform,
        timeout=timeout,
    )
    logger.info(f"[API] 初始化完成: {api_base}, platform={platform}")
    return _api_client

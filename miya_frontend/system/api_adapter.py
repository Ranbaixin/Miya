"""
弥娅 API 适配层
将前端请求格式转换为弥娅核心 API 格式
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class MiyaAPIAdapter:
    """弥娅 API 适配器"""

    def __init__(self, api_base: str = "http://localhost:8000"):
        self.api_base = api_base.rstrip("/")

    def build_chat_request(
        self,
        message: str,
        session_id: str = "desktop",
        platform: str = "desktop",
        stream: bool = False,
    ) -> Dict[str, Any]:
        """构建聊天请求

        将前端格式转换为弥娅核心 API 格式
        """
        return {
            "message": message,
            "session_id": session_id,
            "platform": platform,
        }

    def build_chat_url(self, endpoint: str = "/chat") -> str:
        """构建完整的 API URL"""
        return f"{self.api_base}{endpoint}"

    def parse_chat_response(self, response: Dict[str, Any]) -> Dict[str, Any]:
        """解析聊天响应

        提取响应消息、情绪等信息
        """
        result = {
            "message": response.get("message", ""),
            "emotion": response.get("emotion"),
            "personality": response.get("personality"),
        }

        # 处理可能的响应字段名
        if not result["message"]:
            result["message"] = response.get("response", "")

        return result


# 全局适配器实例
_adapter: Optional[MiyaAPIAdapter] = None


def get_adapter() -> MiyaAPIAdapter:
    """获取全局适配器实例"""
    global _adapter
    if _adapter is None:
        _adapter = MiyaAPIAdapter()
    return _adapter


def init_adapter(api_base: str = "http://localhost:8001") -> MiyaAPIAdapter:
    """初始化适配器"""
    global _adapter
    _adapter = MiyaAPIAdapter(api_base)
    logger.info(f"[API Adapter] 初始化完成: {api_base}")
    return _adapter


def build_chat_request(
    message: str,
    session_id: str = "desktop",
    platform: str = "desktop",
) -> Dict[str, Any]:
    """快捷方法：构建聊天请求"""
    return get_adapter().build_chat_request(message, session_id, platform)


def build_chat_url(endpoint: str = "/chat") -> str:
    """快捷方法：构建 API URL"""
    return get_adapter().build_chat_url(endpoint)


def parse_chat_response(response: Dict[str, Any]) -> Dict[str, Any]:
    """快捷方法：解析聊天响应"""
    return get_adapter().parse_chat_response(response)

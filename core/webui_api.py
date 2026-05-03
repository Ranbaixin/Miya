"""
WebUI API - ChatUI 风格

快速 API 端点用于 Web 聊天界面
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

logger = logging.getLogger("miya.webui")


@dataclass
class ChatMessage:
    """聊天消息"""

    id: str
    role: str  # user, assistant
    content: str
    timestamp: datetime = field(default_factory=datetime.now)


@dataclass
class ChatSession:
    """聊天会话"""

    id: str
    user_id: str
    title: str = "新对话"
    messages: List[ChatMessage] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)


class WebUIAPI:
    """WebUI API"""

    def __init__(self) -> None:
        self._sessions: Dict[str, ChatSession] = {}
        self._current_session: Optional[str] = None

    async def create_session(self, user_id: str) -> str:
        """创建会话"""
        import uuid

        session_id = str(uuid.uuid4())
        session = ChatSession(id=session_id, user_id=user_id)
        self._sessions[session_id] = session
        self._current_session = session_id
        logger.info(f"[WebUI] 创建会话: {session_id}")
        return session_id

    async def get_session(self, session_id: str) -> Optional[ChatSession]:
        """获取会话"""
        return self._sessions.get(session_id)

    async def delete_session(self, session_id: str) -> bool:
        """删除会话"""
        if session_id in self._sessions:
            del self._sessions[session_id]
            return True
        return False

    async def add_message(
        self,
        session_id: str,
        role: str,
        content: str,
    ) -> Optional[ChatMessage]:
        """添加消息"""
        import uuid

        session = self._sessions.get(session_id)
        if not session:
            return None

        message = ChatMessage(
            id=str(uuid.uuid4()),
            role=role,
            content=content,
        )
        session.messages.append(message)
        return message

    async def list_sessions(self, user_id: str) -> List[Dict]:
        """列出用户的会话"""
        return [
            {
                "id": s.id,
                "title": s.title,
                "message_count": len(s.messages),
                "created_at": s.created_at.isoformat(),
            }
            for s in self._sessions.values()
            if s.user_id == user_id
        ]

    async def chat(
        self,
        session_id: str,
        user_message: str,
        chat_handler=None,
    ) -> str:
        """聊天"""
        session = self._sessions.get(session_id)
        if not session:
            return "会话不存在"

        # 添加用户消息
        await self.add_message(session_id, "user", user_message)

        # 获取 AI 响应 (简化版)
        response = "你好！我是弥娅～"

        # 添加助手消息
        await self.add_message(session_id, "assistant", response)

        return response


# 全局实例
_webui_api: Optional[WebUIAPI] = None


def get_webui_api() -> WebUIAPI:
    """获取全局实例"""
    global _webui_api
    if _webui_api is None:
        _webui_api = WebUIAPI()
    return _webui_api


# FastAPI 路由示例
def setup_routes(app):
    """设��路由"""
    from fastapi import APIRouter, HTTPException

    router = APIRouter()
    api = get_webui_api()

    @router.post("/chat/sessions")
    async def create_chat_session(body: dict):
        session_id = await api.create_session(body.get("user_id", "anonymous"))
        return {"session_id": session_id}

    @router.get("/chat/sessions")
    async def list_chat_sessions(user_id: str = "anonymous"):
        sessions = await api.list_sessions(user_id)
        return {"sessions": sessions}

    @router.post("/chat/sessions/{session_id}/messages")
    async def send_message(session_id: str, body: dict):
        message = body.get("message", "")
        response = await api.chat(session_id, message)
        return {"response": response, "session_id": session_id}

    @router.delete("/chat/sessions/{session_id}")
    async def delete_chat_session(session_id: str):
        success = await api.delete_session(session_id)
        if not success:
            raise HTTPException(status_code=404, detail="Session not found")
        return {"success": True}

    app.include_router(router, prefix="/api")
    logger.info("[WebUI] API 路由已设置")


__all__ = [
    "WebUIAPI",
    "ChatMessage",
    "ChatSession",
    "get_webui_api",
    "setup_routes",
]

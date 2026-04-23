"""
弥娅 Web API 路由器 - 重构版
为 Web 端提供 HTTP 接口，支持模块化架构
"""

import logging
from typing import Any, Optional


def _is_process_running(process):
    """安全地检查进程状态"""
    try:
        import psutil

        return process.status() == "running"
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
        return False


try:
    from fastapi import APIRouter, HTTPException

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = object
    HTTPException = Exception

logger = logging.getLogger(__name__)

from datetime import datetime

# 导入模型（向后兼容）
from .models import (
    BlogPostCreate,
    BlogPostUpdate,
    UserRegister,
    UserLogin,
    ChatRequest,
    TerminalChatRequest,
    SecurityScanRequest,
    IPBlockRequest,
    GitHubConfig,
    ToolExecuteRequest,
)


class WebAPI:
    """Web API 路由器（重构版）

    职责：
    - 提供 HTTP RESTful 接口
    - 认证和授权
    - 调用 WebNet 和 DecisionHub
    - 安全检查
    """

    def __init__(self, web_net: Any, decision_hub: Any, github_store: Any = None):
        """初始化 API 路由器

        Args:
            web_net: WebNet 实例
            decision_hub: DecisionHub 实例
            github_store: GitHubStore 实例 (可选)
        """
        self.web_net = web_net
        self.decision_hub = decision_hub
        self.github_store = github_store

        # 初始化多Agent协作系统
        try:
            from core.multi_agent_orchestrator import MultiAgentOrchestrator

            self.multi_agent_orchestrator = MultiAgentOrchestrator()
        except:
            self.multi_agent_orchestrator = None

        if not FASTAPI_AVAILABLE:
            logger.warning("[WebAPI] FastAPI 不可用，API 功能将被禁用")
            self.router = None
            return

        self.router = APIRouter(prefix="", tags=["Web"])

        # 初始化子路由
        self._init_subroutes()

        # 设置路由
        self._setup_routes()

    def _init_subroutes(self):
        """初始化子路由模块"""
        try:
            from .auth import AuthRoutes
            from .blogs import BlogRoutes
            from .chat import ChatRoutes

            # 终端路由已迁移至 Open-ClaudeCode
            from .system import SystemRoutes
            from .desktop import DesktopRoutes
            from .tools import ToolRoutes
            from .security import SecurityRoutes
            # 跨终端路由已迁移至 Open-ClaudeCode

            # 初始化路由模块
            self.auth_routes = AuthRoutes(self.web_net, self.decision_hub)
            self.blogs_routes = BlogRoutes(self.web_net, self.decision_hub)
            self.chat_routes = ChatRoutes(self.web_net, self.decision_hub)
            # 终端/跨终端路由已迁移至 Open-ClaudeCode
            self.terminal_routes = None
            self.cross_terminal_routes = None
            self.system_routes = SystemRoutes(self.web_net, self.decision_hub)
            self.desktop_routes = DesktopRoutes(self.web_net, self.decision_hub)
            self.tools_routes = ToolRoutes(self.web_net, self.decision_hub)
            self.security_routes = SecurityRoutes(self.web_net)

            logger.info("[WebAPI] 所有子路由初始化成功")

        except Exception as e:
            logger.error(f"[WebAPI] 子路由初始化失败: {e}", exc_info=True)
            self.auth_routes = None
            self.blogs_routes = None
            self.chat_routes = None
            self.terminal_routes = None
            self.system_routes = None
            self.desktop_routes = None
            self.tools_routes = None
            self.security_routes = None
            self.cross_terminal_routes = None

    def _setup_routes(self):
        """设置 API 路由"""

        # 注册子路由到主路由器
        if self.auth_routes and self.auth_routes.get_router():
            self.router.include_router(self.auth_routes.get_router())

        if self.blogs_routes and self.blogs_routes.get_router():
            self.router.include_router(self.blogs_routes.get_router())

        if self.chat_routes and self.chat_routes.get_router():
            self.router.include_router(self.chat_routes.get_router())

        if self.terminal_routes and self.terminal_routes.get_router():
            self.router.include_router(self.terminal_routes.get_router())

        if self.system_routes and self.system_routes.get_router():
            self.router.include_router(self.system_routes.get_router())

        if self.desktop_routes and self.desktop_routes.get_router():
            self.router.include_router(self.desktop_routes.get_router())

        if self.tools_routes and self.tools_routes.get_router():
            self.router.include_router(self.tools_routes.get_router())

        if self.security_routes and self.security_routes.get_router():
            self.router.include_router(self.security_routes.get_router())

        if self.cross_terminal_routes and self.cross_terminal_routes.get_router():
            self.router.include_router(self.cross_terminal_routes.get_router())

        # ========== 兼容旧API路径 ==========

        @self.router.get("/api/status")
        async def get_legacy_system_status():
            """获取系统状态（兼容旧API路径，重定向到新路径）"""
            try:
                if hasattr(self.decision_hub, "miya_instance"):
                    miya = self.decision_hub.miya_instance
                    status = miya.get_system_status()

                    from hub.platform_adapters import get_adapter

                    web_adapter = get_adapter("web")
                    platform_info = web_adapter.get_platform_info()

                    return {
                        "identity": status.get("identity", {}),
                        "personality": status.get("personality", {}),
                        "emotion": status.get("emotion", {}),
                        "memory_stats": status.get("memory_stats", {}),
                        "stats": status.get("stats", {}),
                        "platform_info": platform_info,
                        "system_capabilities": platform_info.get(
                            "system_capabilities", {}
                        ),
                        "available_tools": platform_info.get("available_tools", []),
                        "capabilities": platform_info.get("capabilities", {}),
                        "timestamp": datetime.utcnow().isoformat(),
                    }
                return {"error": "System not initialized"}
            except Exception as e:
                logger.error(f"[WebAPI] 获取系统状态失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.get("/api/emotion")
        async def get_legacy_emotion():
            """获取情绪状态（兼容旧API路径）"""
            try:
                emotion_state = self.web_net.emotion_manager.get_emotion_state()
                return emotion_state
            except Exception as e:
                logger.error(f"[WebAPI] 获取情绪状态失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # ========== Web 端对话路由 (兼容旧API) ==========

        @self.router.post("/api/chat")
        async def web_chat(request: ChatRequest):
            """Web 端对话接口（兼容旧API）"""
            try:
                from mlink.message import Message

                platform = request.platform or "web"

                # 用户身份链接处理
                # 优先使用 user_id 字段（桌面端专用），其次用 session_id
                lookup_id = request.user_id or request.session_id
                user_id = lookup_id
                sender_name = f"{platform}用户-{lookup_id[:8]}"

                # 从 permissions.json 检查用户链接配置
                try:
                    import json
                    from pathlib import Path

                    perms_file = Path("config/permissions.json")
                    if perms_file.exists():
                        perms_data = json.loads(perms_file.read_text(encoding="utf-8"))
                        users = perms_data.get("users", [])
                        for u in users:
                            if u.get("user_id") == lookup_id:
                                linked_to = u.get("linked_to")
                                if linked_to:
                                    user_id = linked_to
                                    sender_name = u.get("username", sender_name)
                                break
                except Exception:
                    pass

                perception = {
                    "platform": platform,
                    "content": request.message,
                    "user_id": user_id,
                    "sender_name": sender_name,
                }

                message = Message(
                    msg_type="data",
                    content=perception,
                    source="web_api",
                    destination="decision_hub",
                )

                emotion_before = (
                    self.decision_hub.emotion.get_emotion_state()
                    if self.decision_hub.emotion
                    else None
                )
                personality_before = (
                    self.decision_hub.personality.get_profile()
                    if self.decision_hub.personality
                    else None
                )

                response = await self.decision_hub.process_perception_cross_platform(
                    message
                )

                if not response:
                    response = "抱歉，我无法处理您的请求。"

                emotion_after = (
                    self.decision_hub.emotion.get_emotion_state()
                    if self.decision_hub.emotion
                    else None
                )
                personality_after = (
                    self.decision_hub.personality.get_profile()
                    if self.decision_hub.personality
                    else None
                )

                emotion_result = None
                if emotion_after:
                    emotion_result = {
                        "dominant": emotion_after.get("dominant", "平静"),
                        "intensity": emotion_after.get("intensity", 0.5),
                    }

                personality_result = None
                if personality_after:
                    personality_result = {
                        "state": personality_after.get("dominant", "empathy"),
                        "vectors": personality_after.get(
                            "vectors",
                            {
                                "warmth": 0.5,
                                "logic": 0.5,
                                "creativity": 0.5,
                                "empathy": 0.5,
                                "resilience": 0.5,
                            },
                        ),
                    }

                return {
                    "response": response,
                    "timestamp": datetime.utcnow().isoformat(),
                    "emotion": emotion_result,
                    "personality": personality_result,
                    "tools_used": getattr(self.decision_hub, "_last_tools_used", []),
                    "memory_retrieved": getattr(
                        self.decision_hub, "_last_memory_retrieved", False
                    ),
                }
            except Exception as e:
                logger.error(f"[WebAPI] Web聊天处理失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        # ========== 健康检查 ==========

        @self.router.get("/health")
        async def health_check():
            """健康检查"""
            from datetime import datetime

            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "miya-web-api",
            }

        @self.router.get("/api/health")
        async def api_health_check():
            """API健康检查"""
            from datetime import datetime

            return {
                "status": "ok",
                "timestamp": datetime.utcnow().isoformat(),
                "service": "miya-web-api",
            }

    def get_router(self):
        """获取 API 路由器"""
        return self.router


# 公开接口列表
__all__ = [
    "WebAPI",
    "create_web_api",
    # 模型
    "BlogPostCreate",
    "BlogPostUpdate",
    "UserRegister",
    "UserLogin",
    "ChatRequest",
    "TerminalChatRequest",
    "SecurityScanRequest",
    "IPBlockRequest",
    "GitHubConfig",
    "ToolExecuteRequest",
]


# 向后兼容：创建函数式接口
def create_web_api(
    web_net: Any, decision_hub: Any, github_store: Any = None
) -> Optional[WebAPI]:
    """创建 Web API 实例（向后兼容）

    Args:
        web_net: WebNet 实例
        decision_hub: DecisionHub 实例
        github_store: GitHubStore 实例 (可选)

    Returns:
        WebAPI 实例，如果 FastAPI 不可用则返回 None
    """
    try:
        return WebAPI(web_net, decision_hub, github_store)
    except Exception as e:
        logger.error(f"[WebAPI] 创建失败: {e}")
        return None

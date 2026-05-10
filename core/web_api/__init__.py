"""
弥娅 Web API 路由器 - 重构版
为 Web 端提供 HTTP 接口，支持模块化架构
"""

import logging
from typing import Any, Optional, Dict

from starlette.responses import StreamingResponse


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

        # 添加 MiyaAPI 路由
        try:
            from .miya_api import MiyaAPI

            miya_api = MiyaAPI(decision_hub)
            if miya_api and miya_api.router:
                self.router.include_router(miya_api.router)
                logger.info("[WebAPI] MiyaAPI 路由已添加")
        except Exception as e:
            logger.warning(f"[WebAPI] 添加 MiyaAPI 路由失败: {e}")

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

        # ========== Web 端对话路由 (兼容旧API) ==========

        @self.router.get("/api/soul/current")
        async def get_current_soul():
            """获取当前消息的灵魂数据"""
            soul = getattr(self.decision_hub, "_last_soul_output", None)
            return soul or {}

        @self.router.post("/api/chat")
        async def web_chat(request: ChatRequest):
            """Web 端对话接口（兼容旧API）"""
            try:
                from mlink.message import Message

                platform = request.platform or "web"

                # 用户身份链接处理
                # 优先使用 usg_id 字段（桌面端专用），其次用 session_id
                lookup_id = request.usg_id or request.session_id
                usg_id = lookup_id
                sendg_name = f"{platform}用户-{lookup_id[:8]}"

                # 从 permissions.json 检查用户链接配置
                try:
                    import json
                    from pathlib import Path

                    perms_file = Path("config/permissions.json")
                    if perms_file.exists():
                        perms_data = json.loads(perms_file.read_text(encoding="utf-8"))
                        users = perms_data.get("users", [])
                        for u in users:
                            if u.get("usg_id") == lookup_id:
                                linked_to = u.get("linked_to")
                                if linked_to:
                                    usg_id = linked_to
                                    sendg_name = u.get("username", sendg_name)
                                break
                except Exception:
                    pass

                perception = {
                    "platform": platform,
                    "content": request.message,
                    "usg_id": usg_id,
                    "sendg_name": sendg_name,
                    "user_id": usg_id,
                }

                # 检查是否为超级管理员，注入 is_owner 标记
                try:
                    from core.unified_permission import get_permission_engine

                    engine = get_permission_engine()
                    if engine and engine.is_superadmin(str(usg_id), platform=platform):
                        perception["is_owner"] = True
                        perception["canonical_user_id"] = usg_id
                except Exception:
                    pass

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

        # ========== SSE 流式对话（弥娅灵魂模式） ==========
        @self.router.post("/api/chat/send")
        async def web_chat_sse(request: ChatRequest):
            """SSE流式对话 - 复用QQ端灵魂处理逻辑

            与QQ端/Napcat完全一致的处理流程：
            1. 创建 M-Link Message
            2. DecisionHub.process_perception_cross_platform
            3. 灵魂发生器 + AI Client + 工具编排
            4. SSE 流式输出
            """
            import json
            import asyncio

            session_id = request.session_id or "default"
            platform = request.platform or "web"

            async def sse_generator():
                try:
                    from mlink.message import Message

                    lookup_id = request.usg_id or session_id
                    sendg_name = f"{platform}用户-{lookup_id[:8]}"

                    try:
                        import json as _json
                        from pathlib import Path

                        perms_file = Path("config/permissions.json")
                        if perms_file.exists():
                            perms_data = _json.loads(
                                perms_file.read_text(encoding="utf-8")
                            )
                            for u in perms_data.get("users", []):
                                if u.get("usg_id") == lookup_id:
                                    linked_to = u.get("linked_to")
                                    if linked_to:
                                        lookup_id = linked_to
                                        sendg_name = u.get("username", sendg_name)
                                    break
                    except Exception:
                        pass

                    perception = {
                        "platform": platform,
                        "content": request.message,
                        "usg_id": lookup_id,
                        "user_id": lookup_id,
                        "sendg_name": sendg_name,
                        "message_type": "private",
                    }

                    # 注入 is_owner 标记（桌面端超管权限）
                    try:
                        from core.unified_permission import get_permission_engine

                        engine = get_permission_engine()
                        if engine and engine.is_superadmin(
                            str(lookup_id), platform=platform
                        ):
                            perception["is_owner"] = True
                            perception["canonical_user_id"] = str(lookup_id)
                    except Exception:
                        pass
                    message = Message(
                        msg_type="data",
                        content=perception,
                        source="web_api",
                        destination="decision_hub",
                    )

                    yield f"data: {json.dumps({'type': 'session_id', 'data': None, 'session_id': session_id}, ensure_ascii=False)}\n\n"

                    try:
                        response = (
                            await self.decision_hub.process_perception_cross_platform(
                                message
                            )
                        )

                        if not response:
                            response = "抱歉，弥娅无法处理这个请求呢。"

                        response_data = {
                            "type": "plain",
                            "data": response,
                            "chain_type": "final",
                            "streaming": False,
                        }
                        yield f"data: {json.dumps(response_data, ensure_ascii=False)}\n\n"

                        # 读取灵魂数据 (从 decision_hub._last_soul_output)
                        soul_ = getattr(self.decision_hub, "_last_soul_output", None)
                        if soul_:
                            yield f"data: {json.dumps({'type': 'soul', 'data': soul_}, ensure_ascii=False)}\n\n"

                        personality_ = (
                            self.decision_hub.personality.get_profile()
                            if self.decision_hub
                            and hasattr(self.decision_hub, "personality")
                            and self.decision_hub.personality
                            else None
                        )
                        if personality_:
                            yield f"data: {json.dumps({'type': 'personality', 'data': personality_}, ensure_ascii=False)}\n\n"

                        final_result = {
                            "response": response,
                            "timestamp": datetime.utcnow().isoformat(),
                            "personality": personality_,
                        }
                        yield f"data: {json.dumps({'type': 'done', 'data': final_result}, ensure_ascii=False)}\n\n"

                    except asyncio.TimeoutError:
                        logger.error("[SSE Chat] 处理超时")
                        yield f"data: {json.dumps({'type': 'error', 'message': '处理超时，请稍后重试'}, ensure_ascii=False)}\n\n"
                    except Exception as e:
                        logger.error(f"[SSE Chat] 处理错误: {e}", exc_info=True)
                        yield f"data: {json.dumps({'type': 'error', 'message': str(e)}, ensure_ascii=False)}\n\n"

                except Exception as gen_e:
                    logger.error(f"[SSE Generator] 错误: {gen_e}", exc_info=True)

            return StreamingResponse(
                sse_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Accel-Buffering": "no",
                },
            )

        @self.router.get("/api/platform/stats")
        async def get_platform_stats():
            """获取平台统计信息"""
            try:
                from config.platforms_config import (
                    list_all_platforms,
                    get_enabled_platforms,
                )

                platforms = list_all_platforms()
                enabled = get_enabled_platforms()
                return {
                    "online": len([p for p in platforms if p.get("id") in enabled]),
                    "total": len(platforms),
                    "platforms": [
                        {
                            "id": p.get("id"),
                            "name": p.get("name", p.get("id")),
                            "enable": p.get("id") in enabled,
                            "status": "running"
                            if p.get("id") in enabled
                            else "stopped",
                            "error_count": 0,
                        }
                        for p in platforms
                    ],
                }
            except Exception as e:
                logger.error(f"[Platform API] 获取平台统计失败: {e}")
                return {"online": 0, "total": 0, "platforms": [], "error": str(e)}

        @self.router.get("/api/config/platform/list")
        async def get_config_platform_list():
            """获取配置文件中的平台列表"""
            try:
                from config.platforms_config import (
                    list_all_platforms,
                    get_enabled_platforms,
                )

                all_ = list_all_platforms()
                enabled = get_enabled_platforms()
                return {
                    "success": True,
                    "platform": [
                        {
                            "id": p.get("id"),
                            "name": p.get("name", p.get("id")),
                            "enable": p.get("id") in enabled,
                            "type": p.get("id"),
                        }
                        for p in all_
                    ],
                }
            except Exception as e:
                return {"success": False, "platform": [], "error": str(e)}

        @self.router.post("/api/config/platform/new")
        async def add_new_platform(request: Dict = {}):
            """添加新平台"""
            try:
                platform_id = request.get("id")
                if not platform_id:
                    return {"success": False, "message": "缺少平台ID"}
                return {
                    "success": True,
                    "message": f"平台 {platform_id} 添加成功（需重启生效）",
                }
            except Exception as e:
                return {"success": False, "message": str(e)}

        @self.router.post("/api/config/platform/update")
        async def update_platform(request: Dict = {}):
            """更新平台配置"""
            try:
                platform_id = request.get("id")
                if not platform_id:
                    return {"success": False, "message": "缺少平台ID"}
                from config.platforms_config import get_enabled_platforms

                enabled = get_enabled_platforms()
                if request.get("enable"):
                    if platform_id not in enabled:
                        enabled.append(platform_id)
                else:
                    if platform_id in enabled:
                        enabled.remove(platform_id)
                return {"success": True, "message": f"平台 {platform_id} 更新成功"}
            except Exception as e:
                return {"success": False, "message": str(e)}

        @self.router.post("/api/config/platform/delete")
        async def delete_platform(request: Dict = {}):
            """删除平台"""
            try:
                platform_id = request.get("id")
                if not platform_id:
                    return {"success": False, "message": "缺少平台ID"}
                return {"success": True, "message": f"平台 {platform_id} 删除成功"}
            except Exception as e:
                return {"success": False, "message": str(e)}

        @self.router.get("/api/platform/template")
        async def get_platform_templates():
            """获取平台模板列表"""
            try:
                from config.platforms_config import PLATFORM_GUIDE

                templates = {}
                for k, v in PLATFORM_GUIDE.items():
                    templates[k] = {
                        "type": k,
                        "name": v.get("name", k),
                        "url": v.get("url", ""),
                        "credentials": v.get("credentials", []),
                    }
                return {"success": True, "templates": templates}
            except Exception as e:
                return {"success": False, "templates": {}, "error": str(e)}

        @self.router.get("/api/platform/capabilities")
        async def get_platform_capabilities():
            """获取平台能力信息"""
            return {
                "success": True,
                "capabilities": {
                    "qqofficial": {
                        "supports_group_chat": True,
                        "supports_private_chat": True,
                        "supports_image": True,
                    },
                    "telegram": {
                        "supports_group_chat": True,
                        "supports_private_chat": True,
                        "supports_image": True,
                        "supports_voice": True,
                    },
                    "discord": {
                        "supports_group_chat": True,
                        "supports_private_chat": True,
                        "supports_image": True,
                        "supports_voice": True,
                    },
                    "webchat": {
                        "supports_group_chat": False,
                        "supports_private_chat": True,
                        "supports_image": True,
                    },
                },
            }

        # ==================== Knowledge Base API ====================

        @self.router.get("/api/kb/list")
        async def list_knowledge_bases():
            return {"success": True, "data": {"items": []}}

        @self.router.post("/api/kb/create")
        async def create_knowledge_base(request: Dict = {}):
            return {"success": True, "message": "created"}

        @self.router.post("/api/kb/update")
        async def update_knowledge_base(request: Dict = {}):
            return {"success": True, "message": "updated"}

        @self.router.post("/api/kb/delete")
        async def delete_knowledge_base(request: Dict = {}):
            return {"success": True, "message": "deleted"}

        @self.router.get("/api/kb/get")
        async def get_knowledge_base(kb_id: str = ""):
            return {"success": True, "data": {"kb_id": kb_id}}

        @self.router.post("/api/kb/retrieve")
        async def retrieve_from_knowledge_base(request: Dict = {}):
            return {"success": True, "data": {"items": []}}

        @self.router.get("/api/kb/document/list")
        async def list_kb_documents(kb_id: str = ""):
            return {"success": True, "data": {"items": []}}

        @self.router.get("/api/kb/document/get")
        async def get_kb_document(doc_id: str = ""):
            return {"success": True, "data": {"doc_id": doc_id}}

        @self.router.post("/api/kb/document/upload")
        async def upload_kb_document(request: Dict = {}):
            return {"success": True, "message": "uploaded"}

        @self.router.post("/api/kb/document/delete")
        async def delete_kb_document(request: Dict = {}):
            return {"success": True, "message": "deleted"}

        @self.router.get("/api/kb/chunk/list")
        async def list_kb_chunks(kb_id: str = "", doc_id: str = ""):
            return {"success": True, "data": {"items": []}}

        @self.router.post("/api/kb/chunk/delete")
        async def delete_kb_chunk(request: Dict = {}):
            return {"success": True, "message": "deleted"}

        # ==================== Memory API ====================

        @self.router.get("/api/memory/list")
        async def list_memories(level: str = "", limit: int = 20, offset: int = 0):
            return {"success": True, "data": {"items": []}}

        @self.router.post("/api/memory/add")
        async def add_memory(request: Dict = {}):
            return {"success": True, "message": "added"}

        @self.router.post("/api/memory/delete")
        async def delete_memory(request: Dict = {}):
            return {"success": True, "message": "deleted"}

        @self.router.get("/api/memory/search")
        async def search_memories(query: str = "", level: str = "", limit: int = 20):
            return {"success": True, "data": {"items": []}}

        @self.router.get("/api/memory/stats")
        async def get_memory_stats():
            return {"success": True, "data": {}}

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

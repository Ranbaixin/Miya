"""MIYA Dashboard API Server - 弥娅真实数据版"""

import asyncio
import logging
import sys
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, List, Optional

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

START_TIME = time.time()


class MIYADashboardAPI:
    """MIYA Dashboard API - 使用真实数据"""

    def __init__(self):
        self.miya = None
        self.conversations: List[Dict] = []
        self.sessions: List[Dict] = []
        self.conversation_id_counter = 1

    async def init(self):
        """初始化并获取 MIYA 核心"""
        try:
            from core.miya_core import init_miya_core

            self.miya = init_miya_core()
            await self.miya.init()
            logger.info("✅ MIYA Core 已连接")
        except Exception as e:
            logger.warning(f"⚠️ MIYA Core 初始化失败: {e}")
            self.miya = None

    def _get_conversations(self) -> List[Dict]:
        """获取对话列表"""
        return self.conversations

    def _get_plugins(self) -> List[Dict]:
        """获取插件列表 - 从 Star 系统"""
        if self.miya and self.miya.star_manager:
            try:
                stars = self.miya.star_manager.list_stars()
                return [
                    {
                        "id": star.get("name", star.get("id", "")),
                        "name": star.get("name", "未知"),
                        "description": star.get("description", ""),
                        "version": star.get("version", "1.0.0"),
                        "author": star.get("author", ""),
                        "enabled": star.get("enabled", True),
                        "loaded": star.get("loaded", True),
                    }
                    for star in stars
                ]
            except:
                pass
        return []

    def _get_providers(self) -> List[Dict]:
        """获取提供商列表"""
        if self.miya and self.miya.provider_manager:
            try:
                return self.miya.provider_manager.get_providers_list()
            except:
                pass
        return []

    def _get_platforms(self) -> List[Dict]:
        """获取平台列表"""
        if self.miya and self.miya.platform_manager:
            try:
                return self.miya.platform_manager.get_platforms_list()
            except:
                pass
        return []

    def _get_knowledge_bases(self) -> List[Dict]:
        """获取知识库列表"""
        if self.miya and self.miya.knowledge_base:
            try:
                return self.miya.knowledge_base.list_knowledge_bases()
            except:
                pass
        return []

    def _get_skills(self) -> List[Dict]:
        """获取技能列表"""
        if self.miya and self.miya.star_manager:
            try:
                stars = self.miya.star_manager.list_stars()
                return [
                    {
                        "id": f"skill_{star.get('name', '')}",
                        "name": star.get("name", "未知技能"),
                        "description": star.get("description", ""),
                        "enabled": star.get("enabled", True),
                    }
                    for star in stars
                    if star.get("type") == "skill"
                    or "skill" in star.get("name", "").lower()
                ]
            except:
                pass
        return []

    def _get_personas(self) -> List[Dict]:
        """获取人格列表"""
        return []

    def _get_cron_jobs(self) -> List[Dict]:
        """获取定时任务列表"""
        return []

    def _get_stats(self) -> Dict:
        """获取统计信息"""
        return {
            "total_conversations": len(self.conversations),
            "total_sessions": len(self.sessions),
            "total_plugins": len(self._get_plugins()),
            "total_providers": len(self._get_providers()),
            "total_platforms": len(self._get_platforms()),
            "total_knowledge_bases": len(self._get_knowledge_bases()),
            "uptime": int(time.time() - START_TIME),
            "messages_today": 0,
            "users_today": 0,
        }

    def _get_status(self) -> Dict:
        """获取 MIYA 状态"""
        if self.miya:
            return self.miya.get_status()
        return {
            "name": "MIYA",
            "version": "1.0.0",
            "running": True,
            "initialized": False,
        }


async def main():
    logger.info("=" * 50)
    logger.info("  🎭 MIYA Dashboard API Server")
    logger.info("  (弥娅真实数据版)")
    logger.info("=" * 50)

    try:
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn

        api = MIYADashboardAPI()
        await api.init()

        app = FastAPI(title="MIYA Dashboard API")

        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # ==================== 认证 ====================
        @app.post("/api/auth/login")
        async def login(request: Request):
            try:
                body = await request.json()
            except:
                body = {}
            username = body.get("username", "")
            password = body.get("password", "")

            # 支持 miya/miya 或 astrbot/astrbot
            if (username == "miya" and password == "miya") or (
                username == "astrbot" and password == "astrbot"
            ):
                return {
                    "status": "ok",
                    "data": {
                        "username": username,
                        "token": "miya_token_" + str(hash(username + password))[:16],
                        "change_pwd_hint": False,
                    },
                }
            return {"status": "error", "message": "用户名或密码错误"}

        @app.get("/api/auth/has_token")
        async def has_token(request: Request):
            auth = request.headers.get("authorization", "")
            if auth and auth.startswith("Bearer "):
                token = auth[7:]
                if token:
                    return {"has_token": True, "username": "miya"}
            return {"has_token": False}

        # ==================== MIYA 状态 ====================
        @app.get("/health")
        async def health():
            return {"status": "ok", "service": "MIYA"}

        @app.get("/api/miya/status")
        async def miya_status():
            return {
                "data": {
                    "version": "1.0.0",
                    "name": "MIYA",
                    "core_status": api._get_status(),
                    "uptime": int(time.time() - START_TIME),
                }
            }

        # ==================== 统计 ====================
        @app.get("/api/stat/version")
        async def get_version():
            return {
                "data": {
                    "version": "1.0.0",
                    "dashboard_version": "1.0.0",
                    "core_version": "MIYA",
                    "is_new_version": False,
                    "latest_version": "1.0.0",
                }
            }

        @app.get("/api/stat/start-time")
        async def get_start_time():
            return {
                "data": {
                    "start_time": int(START_TIME * 1000),
                    "running_time": int(time.time() - START_TIME),
                }
            }

        @app.get("/api/stat/get")
        async def stat_get(request: Request):
            return {"data": api._get_stats()}

        @app.get("/api/stat/provider-tokens")
        async def stat_provider_tokens(request: Request):
            return {"data": {"tokens": [], "total": 0}}

        # ==================== 对话管理 ====================
        @app.get("/api/conversation/list")
        async def conversation_list(request: Request):
            page = int(request.query_params.get("page", 1))
            page_size = int(request.query_params.get("page_size", 20))
            conversations = api._get_conversations()
            start = (page - 1) * page_size
            return {
                "data": {
                    "conversations": conversations[start : start + page_size],
                    "total": len(conversations),
                    "page": page,
                    "page_size": page_size,
                }
            }

        @app.post("/api/conversation/create")
        async def create_conversation(request: Request):
            body = await request.json() if request.method == "POST" else {}
            conv = {
                "id": f"conv_{api.conversation_id_counter}",
                "name": body.get("name", f"对话 {api.conversation_id_counter}"),
                "created_at": int(time.time() * 1000),
                "updated_at": int(time.time() * 1000),
                "message_count": 0,
            }
            api.conversations.append(conv)
            api.conversation_id_counter += 1
            return {"data": conv}

        @app.get("/api/conversation/{conv_id}")
        async def get_conversation(conv_id: str):
            for conv in api.conversations:
                if conv["id"] == conv_id:
                    return {"data": conv}
            return {"data": {}}

        # ==================== 会话管理 ====================
        @app.get("/api/session/list-rule")
        async def session_list_rule(request: Request):
            return {
                "data": {
                    "rules": api.sessions,
                    "total": len(api.sessions),
                }
            }

        @app.get("/api/session/groups")
        async def session_groups():
            return {"data": {"groups": []}}

        @app.get("/api/session/rule/{rule_id}")
        async def session_rule_detail(rule_id: str):
            for session in api.sessions:
                if session.get("id") == rule_id:
                    return {"data": session}
            return {"data": {}}

        # ==================== 插件/Star ====================
        @app.get("/api/plugin/get")
        async def plugins():
            return {"plugins": api._get_plugins()}

        @app.get("/api/plugin/list")
        async def plugin_list():
            return {"data": {"plugins": api._get_plugins()}}

        @app.get("/api/plugin/market_list")
        async def plugin_market():
            return {"plugins": []}

        @app.get("/api/plugin/source/get")
        async def plugin_source():
            return {"sources": []}

        @app.get("/api/plugin/source/get-failed-plugins")
        async def plugin_failed():
            return {"data": {"plugins": []}}

        # ==================== 技能/Skills ====================
        @app.get("/api/skills/list")
        async def skills_list():
            return {"data": {"skills": api._get_skills()}}

        @app.get("/api/skills")
        async def skills():
            return {"data": {"skills": api._get_skills()}}

        # ==================== 提供商/Providers ====================
        @app.get("/api/providers")
        async def providers():
            return {"providers": api._get_providers()}

        @app.get("/api/config/provider/list")
        async def provider_list(request: Request):
            provider_type = request.query_params.get("provider_type", "")
            return {"data": {"providers": api._get_providers()}}

        @app.get("/api/config/provider/template")
        async def provider_template():
            return {
                "data": {
                    "providers": [],
                    "provider_sources": [],
                }
            }

        # ==================== 平台/Platforms ====================
        @app.get("/api/platforms")
        async def platforms():
            return {"platforms": api._get_platforms()}

        @app.get("/api/platform/stats")
        async def platform_stats():
            platforms = api._get_platforms()
            return {
                "data": {
                    "platforms": platforms,
                    "total_users": 0,
                    "total_messages": 0,
                }
            }

        # ==================== 知识库/Knowledge Base ====================
        @app.get("/api/kb/list")
        async def kb_list():
            return {"knowledge_bases": api._get_knowledge_bases()}

        @app.get("/api/kb/{kb_id}")
        async def kb_detail(kb_id: str):
            kbs = api._get_knowledge_bases()
            for kb in kbs:
                if kb.get("id") == kb_id:
                    return {"data": kb}
            return {"data": {}}

        # ==================== 人格/Persona ====================
        @app.get("/api/persona/list")
        async def persona_list():
            return {"personalities": api._get_personas()}

        @app.get("/api/persona/folder/tree")
        async def persona_folder_tree():
            return {"data": {"tree": []}}

        @app.get("/api/persona/folder/list")
        async def persona_folder_list():
            return {"data": {"folders": []}}

        # ==================== 定时任务/Cron ====================
        @app.get("/api/cron/jobs")
        async def cron_jobs():
            return {"data": {"jobs": api._get_cron_jobs()}}

        @app.get("/api/cron/list")
        async def cron_list():
            return {"data": {"jobs": api._get_cron_jobs()}}

        # ==================== MCP 工具 ====================
        @app.get("/api/tools/mcp/servers")
        async def mcp_servers():
            return {"data": {"servers": []}}

        @app.get("/api/mcp/list")
        async def mcp_list():
            return {"data": {"servers": []}}

        @app.get("/api/extension/mcp/list")
        async def mcp_list_alt():
            return {"data": {"servers": []}}

        # ==================== 工具/Tools ====================
        @app.get("/api/tools/list")
        async def tools_list():
            if api.miya and api.miya.tool_registry:
                try:
                    tools = api.miya.tool_registry.list_tools()
                    return {"data": {"tools": tools}}
                except:
                    pass
            return {"data": {"tools": []}}

        # ==================== 命令/Commands ====================
        @app.get("/api/command/list")
        async def command_list():
            return {"commands": []}

        @app.get("/api/commands")
        async def commands():
            return {"commands": []}

        # ==================== SubAgent ====================
        @app.get("/api/subagent/list")
        async def subagent_list():
            return {"data": {"subagents": []}}

        @app.get("/api/subagent/config")
        async def subagent_config():
            return {"data": {"config": {}, "subagents": []}}

        # ==================== 配置 ====================
        @app.get("/api/config")
        async def config():
            return {"data": {"config": {}}}

        @app.get("/api/config/get")
        async def config_get():
            return {"data": {"config": {}}}

        @app.get("/api/config/abconf")
        async def config_abconf(request: Request, id: str = "default"):
            return {"data": {"config": {}}}

        @app.get("/api/config/abconfs")
        async def config_abconfs():
            return {"data": {"confs": []}}

        # ==================== 日志/Trace ====================
        @app.get("/api/log-history")
        async def log_history(request: Request):
            return {"data": {"logs": [], "total": 0}}

        @app.get("/api/trace/settings")
        async def trace_settings():
            return {"data": {"enabled": False}}

        # ==================== Chat ====================
        @app.get("/api/chat/conversations")
        async def chat_conversations():
            return {"conversations": api._get_conversations()}

        @app.get("/api/chat/sessions")
        async def chat_sessions():
            return {"sessions": api.sessions}

        @app.get("/api/chat/new_session")
        async def new_session():
            return {"data": {"session": {"id": "new-session", "name": "新会话"}}}

        # ==================== 启动服务器 ====================
        logger.info("✅ API Server")
        logger.info(f"📡 MIYA Dashboard: http://0.0.0.0:6187")

        if api.miya:
            status = api._get_status()
            logger.info(
                f"🎭 MIYA: {status.get('name', 'MIYA')} v{status.get('version', '1.0.0')}"
            )
            logger.info(f"📦 Plugins: {status.get('plugins', 0)}")
            logger.info(f"💬 Platforms: {status.get('platforms', 0)}")
            logger.info(f"🔌 Providers: {status.get('providers', 0)}")

        config = uvicorn.Config(app, host="0.0.0.0", port=6187, log_level="info")
        server = uvicorn.Server(config)
        await server.serve()

    except Exception as e:
        logger.error(f"失败: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except:
        pass

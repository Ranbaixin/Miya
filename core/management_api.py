"""
弥娅管理 API (REST + WebSocket)

提供平台热插拔的控制面和实时状态推送。

REST 端点:
  GET    /api/v1/health              - 系统健康检查
  GET    /api/v1/platforms            - 获取所有平台状态
  GET    /api/v1/platforms/{id}       - 获取单个平台状态
  POST   /api/v1/platforms/{id}/start    - 启动平台
  POST   /api/v1/platforms/{id}/stop     - 停止平台
  POST   /api/v1/platforms/{id}/restart  - 重启平台
  GET    /api/v1/daemon/status        - 守护进程状态

WebSocket:
  WS /api/v1/ws                      - 实时事件流

Usage:
    from core.management_api import ManagementAPI
    api = ManagementAPI(daemon)
    await api.serve(port=9800)
"""

from __future__ import annotations

import asyncio
import contextlib
import json
import logging
from datetime import datetime
from typing import Dict, Optional, Set

import uvicorn
from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

logger = logging.getLogger("Miya.ManagementAPI")


class ManagementAPI:
    """弥娅管理 API 服务器"""

    def __init__(self, daemon, host: str = "0.0.0.0", port: int = 9800):
        self.daemon = daemon
        self.host = host
        self.port = port
        self.app = FastAPI(title="Miya Management API", version="8.0.0")
        self._ws_clients: Set[WebSocket] = set()
        self._server: Optional[uvicorn.Server] = None
        self._serve_task: Optional[asyncio.Task] = None

        self._setup_middleware()
        self._setup_routes()

    def register_webhook_platforms(self):
        """v7.0: 注册 webhook 平台的 FastAPI 路由"""
        for _pid, inst in self.daemon.registry._instances.items():
            if hasattr(inst, "get_webhook_routes"):
                try:
                    webhook_info = inst.get_webhook_routes()
                    if not webhook_info:
                        continue
                    prefix = webhook_info.get("prefix", "")
                    routes = webhook_info.get("routes", [])
                    if not routes:
                        continue

                    router = APIRouter(prefix=prefix)
                    for method, path, handler in routes:
                        handler.__name__ = f"{_pid}_webhook"
                        router.add_api_route(
                            path if path else "/",
                            endpoint=handler,
                            methods=[method],
                        )
                    self.app.include_router(router)
                    logger.info(f"[Webhook] 注册 {_pid} ({prefix})")
                except Exception as e:  # noqa: BLE001 — Webhook 注册失败，跳过该实例
                    logger.warning(f"[Webhook] {_pid} 注册失败: {e}")

    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=[
                "http://localhost:5173", "http://127.0.0.1:5173",
                "http://localhost:3000", "http://127.0.0.1:3000",
                "http://localhost:9800", "http://127.0.0.1:9800",
            ],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

        # 2026-08 安全加固：管理 API 访问网关
        # - 未设置 MIYA_API_TOKEN：仅允许本机(loopback)访问，远程一律 403
        # - 已设置 MIYA_API_TOKEN：任意来源需 Bearer token（恒时比较）
        import hmac
        import os

        import json as _json
        from fastapi.responses import JSONResponse

        def _token_ok(request: Request, api_token: str) -> bool:
            auth = request.headers.get("Authorization", "")
            if auth.lower().startswith("bearer "):
                provided = auth[7:].strip()
            else:
                provided = request.headers.get("X-Miya-Token", "")
            return bool(provided) and hmac.compare_digest(provided, api_token)

        @self.app.middleware("http")
        async def auth_gate(request: Request, call_next):
            client_host = request.client.host if request.client else ""
            is_loopback = client_host in ("127.0.0.1", "::1", "localhost")
            api_token = os.environ.get("MIYA_API_TOKEN", "").strip()
            path = request.url.path

            # 文档与健康探活：本机或带 token 可访问
            if path in ("/docs", "/openapi.json", "/redoc") or path == "/api/v1/health":
                if is_loopback or (api_token and _token_ok(request, api_token)):
                    return await call_next(request)
                return JSONResponse({"detail": "unauthorized"}, status_code=401)

            if not api_token:
                if is_loopback:
                    return await call_next(request)
                return JSONResponse(
                    {"detail": "管理 API 仅允许本机访问；如需远程请设置 MIYA_API_TOKEN"},
                    status_code=403,
                )

            if _token_ok(request, api_token):
                return await call_next(request)
            return JSONResponse({"detail": "invalid or missing token"}, status_code=401)

    def _setup_routes(self):
        """注册所有路由"""
        app = self.app

        @app.get("/api/v1/health")
        async def health_check():
            daemon_status = self.daemon.get_daemon_status()
            return {
                "status": "ok" if daemon_status["started"] else "starting",
                "timestamp": datetime.now().isoformat(),
                **daemon_status,
            }

        @app.get("/api/v1/platforms")
        async def list_platforms():
            return {
                "platforms": self.daemon.get_platform_status(),
                "total": len(self.daemon.get_platform_status()),
                "online": self.daemon.get_daemon_status()["platforms"]["online"],
            }

        @app.get("/api/v1/platforms/{platform_id}")
        async def get_platform(platform_id: str):
            stats = self.daemon.get_platform_status()
            for p in stats:
                if p["platform_id"] == platform_id:
                    return p
            return {"error": "platform not found", "platform_id": platform_id}

        @app.post("/api/v1/platforms/{platform_id}/start")
        async def start_platform(platform_id: str):
            success = await self.daemon.start_platform(platform_id)
            return {
                "platform_id": platform_id,
                "action": "start",
                "success": success,
            }

        @app.post("/api/v1/platforms/{platform_id}/stop")
        async def stop_platform(platform_id: str):
            success = await self.daemon.stop_platform(platform_id)
            return {
                "platform_id": platform_id,
                "action": "stop",
                "success": success,
            }

        @app.post("/api/v1/platforms/{platform_id}/restart")
        async def restart_platform(platform_id: str):
            success = await self.daemon.restart_platform(platform_id)
            return {
                "platform_id": platform_id,
                "action": "restart",
                "success": success,
            }

        @app.get("/api/v1/daemon/status")
        async def daemon_status():
            return self.daemon.get_daemon_status()

        # ======== 权限管理 (v7.0) ========

        @app.get("/api/v1/auth/status")
        async def auth_status():
            engine = self.daemon.permission_engine
            return engine.get_stats()

        @app.get("/api/v1/auth/roles")
        async def list_roles():
            engine = self.daemon.permission_engine
            return {"roles": engine.list_roles()}

        @app.get("/api/v1/auth/users")
        async def list_users():
            engine = self.daemon.permission_engine
            return {"users": engine.list_users()}

        @app.get("/api/v1/auth/users/{user_id}")
        async def get_user(user_id: str):
            engine = self.daemon.permission_engine
            groups = engine.get_user_groups(user_id)
            perms = engine.get_user_permissions_list(user_id)
            is_super = engine.is_superadmin(user_id)
            return {
                "user_id": user_id,
                "groups": groups,
                "permissions": perms,
                "is_superadmin": is_super,
                "role_level": engine.get_role_level(user_id),
            }

        @app.post("/api/v1/auth/users/{user_id}/grant")
        async def grant_role(user_id: str, request: Request):
            try:
                body = await request.json()
            except (ValueError, OSError):
                return {"error": "需要 JSON body: {platform, groups, username?}"}
            engine = self.daemon.permission_engine
            ok = engine.grant_role(
                user_id=user_id,
                platform=body.get("platform", ""),
                username=body.get("username", user_id),
                groups=body.get("groups", []),
            )
            return {"success": ok, "user_id": user_id}

        @app.post("/api/v1/auth/users/{user_id}/revoke")
        async def revoke_role(user_id: str, request: Request):
            try:
                body = await request.json()
            except (ValueError, OSError):
                body = {}
            engine = self.daemon.permission_engine
            ok = engine.revoke_role(user_id=user_id, groups=body.get("groups"))
            return {"success": ok, "user_id": user_id}

        @app.get("/api/v1/auth/check/{user_id}")
        async def check_permission(user_id: str, permission: str = ""):
            engine = self.daemon.permission_engine
            if not permission:
                return {"error": "需要 ?permission=xxx 参数"}
            return {
                "user_id": user_id,
                "permission": permission,
                "allowed": engine.check(user_id, permission),
            }

        @app.websocket("/api/v1/ws")
        async def websocket_endpoint(ws: WebSocket):
            await ws.accept()
            self._ws_clients.add(ws)
            logger.info(f"WS 客户端连接 (总数: {len(self._ws_clients)})")

            # 发送初始状态
            await ws.send_json(
                {
                    "type": "initial_state",
                    "timestamp": datetime.now().isoformat(),
                    "platforms": self.daemon.get_platform_status(),
                    "daemon": self.daemon.get_daemon_status(),
                }
            )

            try:
                while True:
                    data = await ws.receive_text()
                    try:
                        msg = json.loads(data)
                        await self._handle_ws_message(ws, msg)
                    except json.JSONDecodeError:
                        await ws.send_json({"type": "error", "message": "Invalid JSON"})
            except WebSocketDisconnect:
                pass
            finally:
                self._ws_clients.discard(ws)
                logger.info(f"WS 客户端断开 (剩余: {len(self._ws_clients)})")

    async def _handle_ws_message(self, ws: WebSocket, msg: Dict):
        """处理 WebSocket 客户端消息"""
        action = msg.get("action", "")
        platform_id = msg.get("platform_id", "")

        if action == "start_platform" and platform_id:
            success = await self.daemon.start_platform(platform_id)
            await ws.send_json({"type": "action_result", "action": action, "success": success})
        elif action == "stop_platform" and platform_id:
            success = await self.daemon.stop_platform(platform_id)
            await ws.send_json({"type": "action_result", "action": action, "success": success})
        elif action == "restart_platform" and platform_id:
            success = await self.daemon.restart_platform(platform_id)
            await ws.send_json({"type": "action_result", "action": action, "success": success})
        elif action == "get_status":
            await ws.send_json(
                {
                    "type": "status_update",
                    "platforms": self.daemon.get_platform_status(),
                    "daemon": self.daemon.get_daemon_status(),
                }
            )
        else:
            await ws.send_json({"type": "error", "message": f"Unknown action: {action}"})

    async def broadcast_event(self, event: Dict):
        """向所有 WebSocket 客户端广播事件"""
        payload = {
            "type": "platform_event",
            "timestamp": datetime.now().isoformat(),
            **event,
        }
        dead = set()
        for ws in self._ws_clients:
            try:
                await ws.send_json(payload)
            except Exception:  # noqa: BLE001 — 广播失败，标记连接失效以便清理
                dead.add(ws)
        self._ws_clients -= dead

    async def serve(self, block: bool = True):
        """启动 API 服务器"""
        config = uvicorn.Config(
            self.app,
            host=self.host,
            port=self.port,
            log_level="info",
        )
        self._server = uvicorn.Server(config)

        if block:
            await self._server.serve()
        else:
            self._serve_task = asyncio.create_task(self._server.serve())
            await asyncio.sleep(0.1)

    async def stop(self):
        """停止 API 服务器"""
        if self._server:
            self._server.should_exit = True
        if self._serve_task and not self._serve_task.done():
            self._serve_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._serve_task

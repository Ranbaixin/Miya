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
import asyncio
import json
import logging
import time
from datetime import datetime
from typing import Dict, Optional, Set

import uvicorn
from fastapi import APIRouter, FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, StreamingResponse

logger = logging.getLogger("Miya.ManagementAPI")

_AP_PANEL_HTML = """<!DOCTYPE html>
<html lang="zh"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>弥娅 NT 仪表盘</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0a0a0f;color:#c0c8d0;font:14px monospace;padding:16px}
h1{color:#78d0f0;margin-bottom:12px;font-size:20px}
h2{color:#a0b8c0;font-size:14px;margin:16px 0 6px}
.nt-grid{display:flex;gap:8px;flex-wrap:wrap;margin-bottom:16px}
.nt-card{flex:1;min-width:90px;background:#111;border-radius:6px;padding:8px;text-align:center}
.nt-card .label{font-size:10px;color:#687080;margin-bottom:4px}
.nt-card .val{font-size:16px;font-weight:bold}
.nt-card .bar{height:6px;margin-top:4px;border-radius:3px;transition:width .3s}
.row-label{font-size:10px;color:#687080}
.da{color:#f0a040}.adr{color:#ff6060}.oxy{color:#f060b0}
.ser{color:#60d080}.end{color:#a0d0ff}.cor{color:#ff8040}
.nov{color:#d080ff}.foc{color:#50d0e0}
</style></head><body>
<h1>🫀 弥娅 NT 通道实时监控</h1>
<div class="nt-grid" id="nt"></div>
<h2>♡ 弥娅感受</h2><div id="feels" style="color:#c0a0ff;min-height:20px"></div>
<h2>🧠 认知感受</h2><div id="cog" style="color:#70a0b0;min-height:20px"></div>
<h2>📊 记忆召回</h2><div id="mem" style="color:#80b090;min-height:20px"></div>
<script>
const CHS={DA:{label:"多巴胺",cls:"da"},ADR:{label:"肾上腺素",cls:"adr"},
OXY:{label:"催产素",cls:"oxy"},SER:{label:"血清素",cls:"ser"},
END:{label:"内啡肽",cls:"end"},COR:{label:"皮质醇",cls:"cor"},
NOV:{label:"新奇探索",cls:"nov"},FOC:{label:"专注",cls:"foc"}};
function renderNT(d){
 let h="";
 for(let ch of["DA","ADR","OXY","SER","END","COR","NOV","FOC"]){
  let v=d[ch]||0,p=v*100,c=CHS[ch];
  h+=`<div class="nt-card"><div class="row-label">${c.label}</div>
   <div class="val ${c.cls}">${Math.round(p)}%</div>
   <div class="bar ${c.cls}" style="width:${p}%;background:var(--c,currentColor)"></div></div>`;
 }
 document.getElementById("nt").innerHTML=h;
}
function renderFeels(d){
 let f=Object.entries(d).map(([k,v])=>`${k}:${v.toFixed(1)}`).join(" · ");
 document.getElementById("feels").textContent=f||"平静";
}
function renderCog(d){
 let f=Object.entries(d).map(([k,v])=>`${k}:${v.toFixed(2)}`).join(" · ");
 document.getElementById("cog").textContent=f||"-";
}
const src=new EventSource("/api/v1/ap/stream");
src.onmessage=e=>{
 let d=JSON.parse(e.data);
 renderNT(d.nt);
 renderFeels(d.feels);
 renderCog(d.cog);
};
src.onerror=()=>{document.getElementById("nt").innerHTML+='<span style="color:red">连接中断</span>'};
</script></body></html>"""


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
                except Exception as e:
                    logger.warning(f"[Webhook] {_pid} 注册失败: {e}")

    def _setup_middleware(self):
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

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
            except Exception:
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
            except Exception:
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

        # ======== APV2.1 脑内仪表盘 (v8.1) ========

        @app.get("/api/v1/ap/dashboard")
        async def ap_dashboard():
            """APV2.1 认知引擎实时仪表盘"""
            try:
                from core.miya_psyarch_bridge import get_psyarch_bridge

                bridge = get_psyarch_bridge()
                if not bridge or not bridge._initialized:
                    return {"ready": False, "message": "AP 引擎未就绪"}

                emo = bridge.emotion_snapshot()
                cog = bridge.cognitive_state()
                channels = bridge.channels_state()
                edu = bridge.education_stats()

                return {
                    "ready": True,
                    "timestamp": datetime.now().isoformat(),
                    "nt_channels": emo.get("nt_channels", {}),
                    "miya_feelings": dict(sorted(emo.get("miya_feelings", {}).items(), key=lambda x: -x[1])[:8]),
                    "cognitive_feelings": cog.get("cognitive_feelings", {}),
                    "focus_labels": cog.get("focus_labels", []),
                    "recalled_memories": cog.get("recalled_memories", []),
                    "rhythm": channels.get("rhythm", {}),
                    "task": channels.get("task", {}),
                    "expectation_pressure": channels.get("expectation_pressure", {}),
                    "runtime_load": channels.get("runtime_load", {}),
                    "time": channels.get("time", {}),
                    "education": edu,
                }
            except Exception as e:
                return {"ready": False, "error": str(e)}

        async def _ap_stream():
            """SSE 流：实时推送 AP 8 通道 NT 数据"""
            from core.miya_psyarch_bridge import get_psyarch_bridge

            while True:
                try:
                    bridge = get_psyarch_bridge()
                    if bridge and bridge._initialized:
                        emo = bridge.emotion_snapshot()
                        data = {
                            "ts": time.time(),
                            "nt": {k: round(v, 3) for k, v in emo.get("nt_channels", {}).items()},
                            "feels": dict(sorted(emo.get("miya_feelings", {}).items(), key=lambda x: -x[1])[:4]),
                            "cog": bridge.cognitive_state().get("cognitive_feelings", {}),
                        }
                        yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"
                    await asyncio.sleep(0.5)
                except Exception:
                    await asyncio.sleep(1)

        @app.get("/api/v1/ap/stream")
        async def ap_stream():
            return StreamingResponse(_ap_stream(), media_type="text/event-stream")

        @app.get("/api/v1/ap/panel", response_class=HTMLResponse)
        async def ap_panel():
            return _AP_PANEL_HTML

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
            except Exception:
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

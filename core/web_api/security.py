"""安全相关API路由模块

提供安全扫描、工具调用、计划管理、在线资产搜索、IP封禁等API接口。
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, Depends, Header, HTTPException, Query
    from fastapi.responses import StreamingResponse
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from pydantic import BaseModel, Field

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = object
    HTTPException = Exception
    StreamingResponse = object

    def Depends(x):
        return x

    HTTPBearer = None
    BaseModel = object
    Field = None
    Query = None


class TargetInput(BaseModel):
    target: str
    domain: Optional[str] = None
    url: Optional[str] = None
    keyword: Optional[str] = None
    mode: Optional[str] = None
    service: Optional[str] = None
    limit: Optional[int] = None
    category: Optional[str] = None


class SecurityScanRequest(BaseModel):
    """安全扫描请求"""

    path: str
    body: str = ""
    params: Dict[str, Any] = {}


class SecurityPlanCreateRequest(BaseModel):
    """创建扫描计划请求"""

    target: str
    strategy: str = "quick"


class SecurityPlanExecuteRequest(BaseModel):
    """执行扫描计划请求"""

    plan_id: str


class SecurityToolCallRequest(BaseModel):
    """工具调用请求"""

    tool: str
    target: Optional[str] = None
    domain: Optional[str] = None
    url: Optional[str] = None
    keyword: Optional[str] = None
    mode: Optional[str] = None
    service: Optional[str] = None
    limit: Optional[int] = None
    category: Optional[str] = None
    command: Optional[str] = None


class KaliExecRequest(BaseModel):
    """Kali 命令执行请求"""

    command: str


class KaliLaunchRequest(BaseModel):
    """Kali 桌面启动请求"""

    pass


class IPBlockRequest(BaseModel):
    """IP 封禁请求"""

    ip: str
    duration: int = 3600


def _resolve_args(req: SecurityToolCallRequest) -> Dict[str, Any]:
    """从请求体中提取并清理参数"""
    args: Dict[str, Any] = {}
    for field_name in ("target", "domain", "url", "keyword", "mode", "service", "limit", "category", "command"):
        val = getattr(req, field_name, None)
        if val is not None and val != "":
            if field_name == "limit" and isinstance(val, (int, str)):
                args[field_name] = int(val)
            else:
                args[field_name] = val
    return args


class SecurityRoutes:
    """安全相关路由

    职责:
    - 安全扫描
    - 安全工具调用（14 个工具）
    - 扫描计划管理（创建 / 执行 / 报告 / 列表）
    - 在线资产搜索（FOFA / Shodan / Censys / Quake / ZoomEye）
    - IP封禁管理
    """

    def __init__(self, web_net: Any):
        self.web_net = web_net
        self._orchestrator = None
        self._subnet = None

        if not FASTAPI_AVAILABLE:
            self.router = None
            return

        self.router = APIRouter(prefix="/api/security", tags=["Security"])
        self.security = HTTPBearer()
        self._init_security_components()
        self._setup_routes()
        self._setup_kali_terminal()
        logger.info("[SecurityRoutes] 安全路由已初始化 (14 tools + orchestrator + kali terminal)")

    def _init_security_components(self):
        """初始化安全组件"""
        try:
            from webnet.SecurityNet.orchestrator import get_security_orchestrator

            self._orchestrator = get_security_orchestrator()
            logger.info("[SecurityRoutes] 安全编排引擎已连接")
        except Exception as e:
            logger.warning(f"[SecurityRoutes] 编排引擎初始化跳过: {e}")

        try:
            from webnet.SecurityNet.subnet import SecuritySubnet, SecurityConfig

            self._subnet = SecuritySubnet(SecurityConfig())
            logger.info("[SecurityRoutes] SecuritySubnet 已初始化")
        except Exception as e:
            logger.warning(f"[SecurityRoutes] SecuritySubnet 初始化跳过: {e}")

    def _setup_routes(self):
        """设置路由"""

        # ══════════════════════════════════════════════
        #  基础端点
        # ══════════════════════════════════════════════

        @self.router.post("/scan")
        async def scan_security(request: SecurityScanRequest, client_ip: str = Header(None, alias="X-Forwarded-For")):
            """安全扫描（入侵检测）"""
            try:
                ip = client_ip or "unknown"
                scan_request = {"ip": ip, "path": request.path, "body": request.body, "params": request.params}
                event = self.web_net.scan_security(scan_request)
                if event:
                    logger.warning(f"[SecurityRoutes] 检测到安全事件: {event['type']}")
                    return {"detected": True, "event": event}
                else:
                    return {"detected": False, "event": None}
            except Exception as e:
                logger.error(f"[SecurityRoutes] 安全扫描失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.post("/block-ip")
        async def block_ip(request: IPBlockRequest, token: HTTPAuthorizationCredentials = Depends(self.security)):
            """封禁 IP（需要管理员权限）"""
            try:
                user_info = self.web_net.verify_token(token.credentials)
                if not user_info:
                    raise HTTPException(status_code=401, detail="未授权")
                if user_info.get("level", 0) < 4:
                    raise HTTPException(status_code=403, detail="需要管理员权限")
                self.web_net.block_ip(request.ip, request.duration)
                return {"success": True, "message": f"已封禁 IP: {request.ip}", "duration": request.duration}
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[SecurityRoutes] IP 封禁失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        # ══════════════════════════════════════════════
        #  工具调用 /api/security/tool
        # ══════════════════════════════════════════════

        @self.router.post("/tool")
        async def call_security_tool(request: SecurityToolCallRequest):
            """直接调用安全工具

            支持 14 个工具:
            侦查: security_port_scan, security_nmap_scan, security_subdomain_enum,
                   security_dns_enum, security_online_asset
            分析: security_http_headers, security_ssl_cert, security_dir_brute
            漏洞: security_vuln_lookup, security_sploitus_search, security_web_vuln_scanner
            支撑: security_sandbox_exec, security_tool_index, security_ctf_workflow
            """
            try:
                subnet = self._subnet
                if subnet and request.tool in subnet.tools:
                    args = _resolve_args(request)
                    result = await subnet.execute_tool(request.tool, args)
                    return {"success": True, "tool": request.tool, "result": result}

                # 尝试通过 ToolNet 直接调用
                result = await self._execute_via_tool_registry(request.tool, _resolve_args(request))
                if result is not None:
                    return {"success": True, "tool": request.tool, "result": result}

                return {"success": False, "tool": request.tool, "result": f"工具未找到或未注册: {request.tool}"}
            except Exception as e:
                logger.error(f"[SecurityRoutes] 工具调用失败: {request.tool} — {e}", exc_info=True)
                return {"success": False, "tool": request.tool, "result": f"执行失败: {e}"}

        # ══════════════════════════════════════════════
        #  扫描计划 /api/security/plan/*
        # ══════════════════════════════════════════════

        @self.router.post("/plan/create")
        async def create_security_plan(request: SecurityPlanCreateRequest):
            """创建扫描计划"""
            try:
                orch = self._orchestrator
                if not orch:
                    return {"success": False, "message": "编排引擎不可用"}

                plan = orch.create_plan(request.target, request.strategy)
                if not plan:
                    raise HTTPException(status_code=400, detail=f"未知策略: {request.strategy}")

                # 为计划生成唯一 ID 并在 active_plans 中查找
                plan_id = None
                for pid, p in orch._engine.active_plans.items():
                    if p is plan:
                        plan_id = pid
                        break
                plan_id = plan_id or f"{request.target}-{uuid.uuid4().hex[:8]}"

                # 设置工具执行器
                async def _tool_exec(tool_name: str, args: Dict[str, Any]) -> str:
                    return await self._call_tool_safe(tool_name, args)

                orch.set_tool_executor(_tool_exec)

                return {
                    "success": True,
                    "plan_id": plan_id,
                    "target": request.target,
                    "strategy": request.strategy,
                    "strategy_name": orch._engine.STRATEGIES.get(request.strategy, {}).get("name", request.strategy),
                    "phases": orch._engine.STRATEGIES.get(request.strategy, {}).get("phases", []),
                    "task_count": len(plan.tasks),
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[SecurityRoutes] 创建计划失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.post("/plan/execute")
        async def execute_security_plan(request: SecurityPlanExecuteRequest):
            """执行扫描计划"""
            try:
                orch = self._orchestrator
                if not orch:
                    return {"success": False, "message": "编排引擎不可用"}

                async def _tool_exec(tool_name: str, args: Dict[str, Any]) -> str:
                    return await self._call_tool_safe(tool_name, args)

                orch.set_tool_executor(_tool_exec)

                result = await orch.execute_plan(request.plan_id)
                return {
                    "success": True,
                    "plan_id": request.plan_id,
                    "result": result,
                }
            except Exception as e:
                logger.error(f"[SecurityRoutes] 执行计划失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.get("/plan/report")
        async def get_security_report(plan_id: str = Query(...)):
            """获取扫描报告"""
            try:
                orch = self._orchestrator
                if not orch:
                    return {"success": False, "message": "编排引擎不可用"}

                plan = orch._engine.active_plans.get(plan_id)
                if not plan:
                    return {"success": False, "message": f"计划不存在: {plan_id}"}

                report = orch.generate_report(plan_id)
                return {
                    "success": True,
                    "plan_id": plan_id,
                    "target": plan.target,
                    "strategy": plan.strategy,
                    "status": plan.status.name,
                    "phases_completed": sorted(plan.phases_completed),
                    "services_found": len(plan.services),
                    "tool_recommendations": len(plan.tool_recommendations),
                    "vuln_intel_items": len(plan.vuln_intel),
                    "report": report,
                }
            except Exception as e:
                logger.error(f"[SecurityRoutes] 获取报告失败: {e}", exc_info=True)
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.get("/plans")
        async def get_security_plans():
            """获取所有扫描计划列表"""
            try:
                orch = self._orchestrator
                if not orch:
                    return {"success": True, "plans": []}

                plans = []
                for pid, plan in orch._engine.active_plans.items():
                    plans.append(
                        {
                            "plan_id": pid,
                            "target": plan.target,
                            "strategy": plan.strategy,
                            "status": plan.status.name,
                            "phases_completed": sorted(plan.phases_completed),
                            "task_count": len(plan.tasks),
                            "services_found": len(plan.services),
                            "created_at": plan.created_at,
                        }
                    )
                plans.sort(key=lambda x: x["created_at"], reverse=True)
                return {"success": True, "plans": plans}
            except Exception as e:
                logger.error(f"[SecurityRoutes] 获取计划列表失败: {e}", exc_info=True)
                return {"success": False, "plans": [], "error": str(e)}

        # ══════════════════════════════════════════════
        #  在线资产搜索 /api/security/online
        # ══════════════════════════════════════════════

        @self.router.get("/online")
        async def online_search(
            service: str = Query(...), query: str = Query(...), limit: Optional[int] = Query(default=10)
        ):
            """网络空间搜索引擎查询

            支持: fofa / shodan / censys / quake / zoomEye
            """
            try:
                result = await self._call_tool_safe(
                    "security_online_asset", {"service": service, "query": query, "limit": limit or 10}
                )
                return {
                    "success": True,
                    "service": service,
                    "query": query,
                    "result": result,
                }
            except Exception as e:
                logger.error(f"[SecurityRoutes] 在线搜索失败: {e}", exc_info=True)
                return {"success": False, "service": service, "result": f"搜索失败: {e}"}

        # ══════════════════════════════════════════════
        #  Kali 桌面
        # ══════════════════════════════════════════════

        @self.router.get("/kali/status")
        async def kali_status():
            """检查 Kali Docker 容器状态"""
            try:
                from webnet.SecurityNet.kali_sandbox import (
                    is_docker_available,
                    is_container_running,
                    KALI_CONTAINER,
                )

                docker_ok = is_docker_available()
                container_ok = is_container_running(KALI_CONTAINER) if docker_ok else False
                return {
                    "success": True,
                    "running": docker_ok and container_ok,
                    "docker": docker_ok,
                    "container": container_ok if docker_ok else False,
                    "name": KALI_CONTAINER,
                }
            except Exception as e:
                return {"success": False, "running": False, "error": str(e)}

        @self.router.post("/kali/launch")
        async def kali_launch(
            request: KaliLaunchRequest = None,
            token: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """启动/重启 Kali 桌面环境（需要管理员权限）"""
            try:
                user_info = self.web_net.verify_token(token.credentials)
                if not user_info:
                    raise HTTPException(status_code=401, detail="未授权")
                if user_info.get("level", 0) < 4:
                    raise HTTPException(status_code=403, detail="需要管理员权限")

                from webnet.SecurityNet.kali_sandbox import (
                    ensure_kali_container,
                    docker_exec_sync,
                    KALI_CONTAINER,
                )

                status = ensure_kali_container()
                if not status["success"]:
                    return {"success": False, "error": status.get("error", "无法启动容器")}

                result = docker_exec_sync("pgrep -f 'start-vnc'", timeout=5)
                if not result.get("success") or not result.get("stdout", "").strip():
                    docker_exec_sync("nohup bash /start-vnc.sh > /tmp/vnc.log 2>&1 &", timeout=5)

                return {"success": True, "message": "Kali 桌面已启动", "url": "http://localhost:6080/vnc.html"}
            except HTTPException:
                raise
            except Exception as e:
                return {"success": False, "error": str(e)}

        @self.router.post("/kali/exec")
        async def kali_exec(
            request: KaliExecRequest,
            token: HTTPAuthorizationCredentials = Depends(self.security),
        ):
            """在 Kali 容器中执行命令并返回输出（需要认证）"""
            try:
                user_info = self.web_net.verify_token(token.credentials)
                if not user_info:
                    raise HTTPException(status_code=401, detail="未授权")

                from webnet.SecurityNet.kali_sandbox import (
                    is_container_running,
                    docker_exec_sync,
                    KALI_CONTAINER,
                )

                if not is_container_running(KALI_CONTAINER):
                    return {"success": False, "error": "Kali 容器未运行"}

                command = request.command
                if not command or not command.strip():
                    return {"success": False, "error": "未提供命令"}

                result = docker_exec_sync(command, timeout=30)
                return {
                    "success": result.get("success", False),
                    "stdout": result.get("stdout", ""),
                    "stderr": result.get("stderr", ""),
                    "error": result.get("error", ""),
                }
            except HTTPException:
                raise
            except Exception as e:
                return {"success": False, "error": str(e)}

    def _setup_kali_terminal(self):
        """注册 Kali 终端 WebSocket 路由"""

        @self.router.websocket("/kali/terminal")
        async def kali_terminal(websocket):
            import asyncio as aio, subprocess

            await websocket.accept()
            try:
                from webnet.SecurityNet.kali_sandbox import is_container_running, KALI_CONTAINER

                if not is_container_running(KALI_CONTAINER):
                    await websocket.send_text("\x1b[31mKali 容器未运行\x1b[0m\r\n")
                    await websocket.close()
                    return
            except Exception as e:
                await websocket.send_text(f"\x1b[31m{e}\x1b[0m\r\n")
                await websocket.close()
                return

            proc = await aio.create_subprocess_exec(
                "docker",
                "exec",
                "-i",
                KALI_CONTAINER,
                "bash",
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
            )

            async def read_out():
                try:
                    while True:
                        chunk = await proc.stdout.read(4096)
                        if not chunk:
                            break
                        try:
                            await websocket.send_bytes(chunk)
                        except Exception:
                            break
                except Exception:
                    pass

            async def write_in():
                try:
                    while True:
                        data = await websocket.receive_bytes()
                        proc.stdin.write(data)
                        await proc.stdin.drain()
                except Exception:
                    pass

            r = aio.create_task(read_out())
            try:
                await write_in()
            finally:
                r.cancel()
                try:
                    proc.terminate()
                except ProcessLookupError:
                    pass
                except Exception:
                    pass

    async def _call_tool_safe(self, tool_name: str, args: Dict[str, Any]) -> str:
        """安全地调用工具，优先使用 SecuritySubnet，fallback 到 ToolRegistry"""
        # 优先通过 SecuritySubnet
        if self._subnet and tool_name in self._subnet.tools:
            return await self._subnet.execute_tool(tool_name, args)

        # Fallback: 直接通过 ToolRegistry
        result = await self._execute_via_tool_registry(tool_name, args)
        if result is not None:
            return result

        return f"工具不可用: {tool_name}"

    async def _execute_via_tool_registry(self, tool_name: str, args: Dict[str, Any]) -> Optional[str]:
        """通过 ToolRegistry 直接执行工具（fallback）"""
        try:
            from webnet.ToolNet.base import ToolContext

            ctx = ToolContext()

            # 已知工具的显式映射（14 个安全工具）
            tool_map = {
                "security_port_scan": "webnet.ToolNet.tools.security.port_scanner",
                "security_nmap_scan": "webnet.ToolNet.tools.security.nmap_scan",
                "security_subdomain_enum": "webnet.ToolNet.tools.security.subdomain_enum",
                "security_dns_enum": "webnet.ToolNet.tools.security.dns_enum",
                "security_http_headers": "webnet.ToolNet.tools.security.http_headers",
                "security_ssl_cert": "webnet.ToolNet.tools.security.ssl_cert",
                "security_vuln_lookup": "webnet.ToolNet.tools.security.vuln_lookup",
                "security_sploitus_search": "webnet.ToolNet.tools.security.sploitus_search",
                "security_online_asset": "webnet.ToolNet.tools.security.online_asset",
                "security_dir_brute": "webnet.ToolNet.tools.security.dir_brute",
                "security_web_vuln_scanner": "webnet.ToolNet.tools.security.web_vuln_scanner",
                "security_sandbox_exec": "webnet.ToolNet.tools.security.sandbox_exec",
                "security_ctf_workflow": "webnet.ToolNet.tools.security.ctf_workflow",
                "security_tool_index": "webnet.ToolNet.tools.security.tool_index",
            }

            if tool_name not in tool_map:
                return None

            module_path = tool_map[tool_name]
            getter_name = f"get_{tool_name}_tool"

            import importlib

            mod = importlib.import_module(module_path)
            getter = getattr(mod, getter_name, None)
            if not getter:
                return None

            tool = getter()
            result = await tool.execute(args, ctx)
            return result
        except Exception as e:
            logger.warning(f"[SecurityRoutes] ToolRegistry fallback 失败: {tool_name} — {e}")
            return None

    def get_router(self):
        """获取路由器"""
        return self.router

"""安全相关API路由模块

提供安全扫描、IP封禁等API接口。
"""

import logging
from typing import Any, Dict

logger = logging.getLogger(__name__)

try:
    from fastapi import APIRouter, Depends, Header, HTTPException
    from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
    from pydantic import BaseModel
    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = object
    HTTPException = Exception
    def Depends(x):
        return x
    HTTPBearer = None


class SecurityScanRequest(BaseModel):
    """安全扫描请求"""
    path: str
    body: str = ""
    params: Dict[str, Any] = {}


class IPBlockRequest(BaseModel):
    """IP 封禁请求"""
    ip: str
    duration: int = 3600


class SecurityRoutes:
    """安全相关路由
    
    职责:
    - 安全扫描
    - IP封禁管理
    """

    def __init__(self, web_net: Any):
        """初始化安全路由
        
        Args:
            web_net: WebNet实例
        """
        self.web_net = web_net
        
        if not FASTAPI_AVAILABLE:
            self.router = None
            return
        
        self.router = APIRouter(prefix="/api/security", tags=["Security"])
        self.security = HTTPBearer()
        self._setup_routes()
        logger.info("[SecurityRoutes] 安全路由已初始化")

    def _setup_routes(self):
        """设置路由"""
        
        @self.router.post("/scan")
        async def scan_security(
            request: SecurityScanRequest,
            client_ip: str = Header(None, alias="X-Forwarded-For")
        ):
            """安全扫描"""
            try:
                ip = client_ip or "unknown"
                
                scan_request = {
                    "ip": ip,
                    "path": request.path,
                    "body": request.body,
                    "params": request.params
                }
                
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
        async def block_ip(
            request: IPBlockRequest,
            token: HTTPAuthorizationCredentials = Depends(self.security)
        ):
            """封禁 IP（需要管理员权限）"""
            try:
                # 验证 Token
                user_info = self.web_net.verify_token(token.credentials)
                if not user_info:
                    raise HTTPException(status_code=401, detail="未授权")
                
                # 检查管理员权限
                if user_info.get("level", 0) < 4:
                    raise HTTPException(status_code=403, detail="需要管理员权限")
                
                # 封禁 IP
                self.web_net.block_ip(request.ip, request.duration)
                
                return {
                    "success": True,
                    "message": f"已封禁 IP: {request.ip}",
                    "duration": request.duration
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[SecurityRoutes] IP 封禁失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def get_router(self):
        """获取路由器"""
        return self.router

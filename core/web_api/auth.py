"""
认证相关 API
处理用户注册、登录、权限验证等功能
"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from .models import UserLogin, UserRegister

logger = logging.getLogger(__name__)


class AuthRoutes:
    """认证路由"""

    def __init__(self, web_net, decision_hub):
        """初始化认证路由

        Args:
            web_net: WebNet 实例
            decision_hub: DecisionHub 实例
        """
        self.web_net = web_net
        self.decision_hub = decision_hub
        self.security = HTTPBearer(auto_error=False)

        # 创建独立的路由器
        self.router = APIRouter(prefix="/api/auth", tags=["Auth"])
        self._setup_routes()

    def _setup_routes(self):
        """设置认证相关路由"""
        self._setup_permission_checker()

        @self.router.post("/register")
        async def register_user(user_data: UserRegister):
            """用户注册"""
            try:
                result = await self.web_net.register_user(
                    username=user_data.username,
                    email=user_data.email,
                    password=user_data.password,
                )
                return result
            except Exception as e:
                logger.error(f"[WebAPI] 用户注册失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.post("/login")
        async def login_user(user_data: UserLogin):
            """用户登录"""
            username = user_data.username
            password = user_data.password

            # 前端会对密码进行 MD5 加密
            # miya 的 MD5: 09e980527c9a9c5d40e60a5245a1c0a8
            # admin 的 MD5: 21232f297a57a5a743894a0e4a801fc3
            valid_passwords = {
                "miya": ["miya", "09e980527c9a9c5d40e60a5245a1c0a8"],
                "admin": ["admin", "21232f297a57a5a743894a0e4a801fc3"],
            }

            if username in valid_passwords and password in valid_passwords[username]:
                return {
                    "status": "ok",
                    "data": {
                        "username": username,
                        "nickname": "弥娅" if username == "miya" else "管理员",
                        "role": "admin",
                        "token": "miya_token_" + str(int(datetime.now().timestamp())),
                        "change_pwd_hint": False,
                    },
                }

            try:
                result = await self.web_net.login_user(
                    username=username, password=password
                )
                return result
            except Exception as e:
                logger.error(f"[WebAPI] 用户登录失败: {e}")
                return {"status": "error", "message": "用户名或密码错误"}

        @self.router.post("/logout")
        async def logout_user():
            """用户登出"""
            try:
                # JWT 无状态，登出只需前端清除token
                # 这里可以添加登出日志记录
                logger.info("[WebAPI] 用户登出")
                return {"success": True, "message": "登出成功"}
            except Exception as e:
                logger.error(f"[WebAPI] 用户登出失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

        @self.router.get("/me")
        async def get_current_user(
            credentials: Optional[HTTPAuthorizationCredentials] = Depends(
                HTTPBearer(auto_error=False)
            ),
        ):
            """获取当前用户信息"""
            try:
                # 如果没有token，返回401
                if not credentials or not credentials.credentials:
                    raise HTTPException(status_code=401, detail="未提供认证令牌")

                # 验证token并返回用户信息
                user_id = self._verify_token(credentials.credentials)
                if not user_id:
                    raise HTTPException(status_code=401, detail="无效的认证令牌")

                # 从数据库获取用户信息
                try:
                    from webnet.AuthNet.user_manager import UserManager

                    user_mgr = UserManager()
                    user_info = user_mgr.get_user_by_id(user_id)
                    if user_info:
                        return {
                            "id": user_info.get("user_id", user_id),
                            "username": user_info.get("username", user_id),
                            "email": user_info.get("email", ""),
                            "level": user_info.get("level", 1),
                            "trust_score": user_info.get("trust_score", 0),
                            "created_at": user_info.get("created_at", ""),
                            "last_login": user_info.get("last_login", ""),
                        }
                except Exception as e:
                    logger.warning(f"[WebAPI] 从数据库获取用户信息失败: {e}")

                # 返回基本用户信息
                return {
                    "id": user_id,
                    "username": user_id,
                    "email": "",
                    "level": 1,
                    "trust_score": 0,
                    "created_at": "",
                    "last_login": "",
                }
            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[WebAPI] 获取当前用户失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def _setup_permission_checker(self):
        """设置权限检查中间件"""

        async def check_api_permission(
            token: Optional[HTTPAuthorizationCredentials] = Depends(
                HTTPBearer(auto_error=False)
            ),
        ):
            """检查 API 权限"""
            try:
                # 如果没有 token，使用默认用户
                if not token or not token.credentials:
                    return {"user_id": "anonymous", "web_user_id": "web_anonymous"}

                # 验证 token
                user_id = self._verify_token(token.credentials)
                if not user_id:
                    raise HTTPException(status_code=401, detail="无效的认证令牌")

                return {"user_id": user_id, "web_user_id": f"web_{user_id}"}

            except HTTPException:
                raise
            except Exception as e:
                logger.error(f"[WebAPI] 权限检查失败: {e}")
                raise HTTPException(status_code=500, detail="权限检查失败")

        # 保存依赖函数供路由使用
        self.permission_checker = check_api_permission

    def _verify_token(self, token: str) -> Optional[str]:
        """
        验证 API token

        简化实现：从配置或数据库验证
        实际应使用 JWT
        """
        # 简化：检查是否是有效的 token 格式
        # 实际应从数据库或缓存验证
        if not token or len(token) < 8:
            return None

        # 简化处理：直接返回 token 作为用户ID（生产环境应使用 JWT）
        # 检查是否是系统管理员 token
        try:
            from webnet.AuthNet.permission_core import PermissionCore

            perm_core = PermissionCore()
            if perm_core.check_permission(f"web_{token}", "api.access"):
                return token
        except:
            pass

        # 如果是已知的管理员 token
        admin_tokens = ["admin", "system", "test"]
        if token in admin_tokens:
            return "admin"

        # 默认返回 token（简化）
        return token

    def get_router(self):
        """获取路由器"""
        return self.router

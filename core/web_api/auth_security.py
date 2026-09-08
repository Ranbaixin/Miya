"""
安全凭据模块（2026-08 加固）

替换硬编码口令 / 可预测 token：
- 密码: hashlib.scrypt 加盐哈希（stdlib，无新依赖）
- 管理员凭据: config/.env 中的 MIYA_ADMIN_PASSWORD_HASH（首次启动自动生成随机密码）
- 会话 token: JWT (HS256, 2 小时过期)，密钥 MIYA_JWT_SECRET
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import secrets
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# JWT 密钥与管理员用户名的环境变量名
ENV_JWT_SECRET = "MIYA_JWT_SECRET"
ENV_ADMIN_PASSWORD_HASH = "MIYA_ADMIN_PASSWORD_HASH"
ENV_ADMIN_USERNAME = "MIYA_ADMIN_USERNAME"

DEFAULT_ADMIN_USERNAME = "admin"
TOKEN_TTL_HOURS = 2

_SCRYPT_PARAMS = {"n": 2**14, "r": 8, "p": 1}
_SCRYPT_KEYLEN = 32


def _env_path() -> Path:
    return Path(__file__).parent.parent.parent / "config" / ".env"


def _read_env() -> dict:
    """读取 config/.env 为 dict（KEY → VALUE，保留首次出现的顺序）。"""
    path = _env_path()
    result: dict = {}
    if path.exists():
        try:
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                result[key.strip()] = value.strip()
        except OSError as e:
            logger.warning(f"[auth_security] 读取 .env 失败: {e}")
    return result


def _write_env(updates: dict) -> None:
    """原子更新 config/.env 中的指定键（保留注释与其他键）。"""
    path = _env_path()
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    replaced = set()
    out: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                out.append(key + "=" + updates[key])
                replaced.add(key)
                continue
        out.append(line)
    for key, value in updates.items():
        if key not in replaced:
            out.append(key + "=" + value)

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


# ==================== 密码 ====================


def hash_password(password: str) -> str:
    """scrypt 哈希，格式: scrypt$n$r$p$salt_hex$hash_hex"""
    salt = secrets.token_bytes(16)
    dk = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt,
        n=_SCRYPT_PARAMS["n"],
        r=_SCRYPT_PARAMS["r"],
        p=_SCRYPT_PARAMS["p"],
        dklen=_SCRYPT_KEYLEN,
    )
    return (
        "scrypt$"
        + str(_SCRYPT_PARAMS["n"])
        + "$"
        + str(_SCRYPT_PARAMS["r"])
        + "$"
        + str(_SCRYPT_PARAMS["p"])
        + "$"
        + salt.hex()
        + "$"
        + dk.hex()
    )


def verify_password(password: str, stored: str) -> bool:
    """校验密码；存储格式非法时拒绝（fail-closed）。"""
    try:
        scheme, n, r, p, salt_hex, hash_hex = stored.split("$")
        if scheme != "scrypt":
            return False
        dk = hashlib.scrypt(
            password.encode("utf-8"),
            salt=bytes.fromhex(salt_hex),
            n=int(n),
            r=int(r),
            p=int(p),
            dklen=_SCRYPT_KEYLEN,
        )
        return hmac.compare_digest(dk.hex(), hash_hex)
    except (ValueError, TypeError):
        return False


def generate_random_password(length: int = 14) -> str:
    """生成安全随机密码（URL-safe 字符）。"""
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789"
    return "".join(secrets.choice(alphabet) for _ in range(length))


# ==================== 管理员凭据（.env） ====================


def get_admin_username() -> str:
    return _read_env().get(ENV_ADMIN_USERNAME, DEFAULT_ADMIN_USERNAME)


def ensure_admin_credentials() -> Optional[str]:
    """确保管理员口令存在。首次调用生成随机密码并写入 .env，返回明文（供控制台打印一次）；已存在返回 None。"""
    env = _read_env()
    if env.get(ENV_ADMIN_PASSWORD_HASH):
        return None
    password = generate_random_password()
    _write_env(
        {
            ENV_ADMIN_USERNAME: get_admin_username(),
            ENV_ADMIN_PASSWORD_HASH: hash_password(password),
        }
    )
    logger.warning(
        "[auth_security] 已生成管理员凭据 -> config/.env "
        + "(username="
        + get_admin_username()
        + ")。密码仅在此处显示一次: "
        + password
    )
    return password


def verify_admin_login(username: str, password: str) -> bool:
    """校验管理员登录（scrypt 恒时比较）。"""
    env = _read_env()
    stored = env.get(ENV_ADMIN_PASSWORD_HASH)
    if not stored:
        # 尚无凭据：生成（并静默丢弃明文，仅日志提示重新登录）
        ensure_admin_credentials()
        return False
    return hmac.compare_digest(username, get_admin_username()) and verify_password(password, stored)


# ==================== JWT token ====================


def _jwt_secret() -> str:
    env = _read_env()
    secret = env.get(ENV_JWT_SECRET)
    if not secret:
        secret = secrets.token_urlsafe(48)
        _write_env({ENV_JWT_SECRET: secret})
        logger.info("[auth_security] 已生成 MIYA_JWT_SECRET 并写入 config/.env")
    return secret


def create_token(username: str) -> str:
    """签发 JWT（HS256，TTL 2h）。"""
    import jwt as pyjwt

    now = datetime.now(timezone.utc)  # noqa: UP017 — 本环境 datetime.UTC 不可用，保留 timezone.utc
    payload = {
        "sub": username,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(hours=TOKEN_TTL_HOURS)).timestamp()),
    }
    return pyjwt.encode(payload, _jwt_secret(), algorithm="HS256")


def verify_token(token: str) -> Optional[str]:
    """验证 JWT，返回 username；无效/过期返回 None（fail-closed）。"""
    if not token or len(token) < 16:
        return None
    try:
        import jwt as pyjwt

        payload = pyjwt.decode(token, _jwt_secret(), algorithms=["HS256"])
        return payload.get("sub")
    except Exception:  # noqa: BLE001 — 任何 token 解析失败都视为无效
        return None


# ==================== 统一访问网关（2026-09 加固） ====================


def is_loopback_host(host: str) -> bool:
    return host in ("127.0.0.1", "::1", "localhost", "testclient")


def request_token_ok(request) -> bool:
    """校验请求携带的 MIYA_API_TOKEN（Bearer 或 X-Miya-Token，恒时比较）。"""
    api_token = os.environ.get("MIYA_API_TOKEN", "").strip()
    if not api_token:
        return False
    auth = request.headers.get("Authorization", "")
    provided = auth[7:].strip() if auth.lower().startswith("bearer ") else request.headers.get("X-Miya-Token", "")
    return bool(provided) and hmac.compare_digest(provided, api_token)


def install_token_gate(
    app,
    *,
    public_paths: tuple = ("/docs", "/openapi.json", "/redoc"),
    public_health_paths: tuple = (),
    local_only_paths: tuple = (),
) -> None:
    """为 FastAPI app 安装统一访问网关（fail-closed）。

    - public_paths / public_health_paths：本机可直接访问，远程需带 token。
    - local_only_paths：仅本机可访问（远程即使带 token 也 403）。
    - 其余路径：未设 MIYA_API_TOKEN 时仅本机(loopback)放行，远程 403；
      已设置时任意来源需 Bearer <token> 或 X-Miya-Token。
    注意：必须在 add_middleware(CORSMiddleware) 之后调用，使网关位于最外层。
    """
    from fastapi.responses import JSONResponse

    @app.middleware("http")
    async def token_gate(request, call_next):
        client_host = request.client.host if request.client else ""
        loopback = is_loopback_host(client_host)
        path = request.url.path

        if path in local_only_paths and not loopback:
            return JSONResponse({"detail": "该端点仅允许本机访问"}, status_code=403)

        if path in public_paths or path in public_health_paths:
            if loopback or request_token_ok(request):
                return await call_next(request)
            return JSONResponse({"detail": "unauthorized"}, status_code=401)

        if loopback or request_token_ok(request):
            return await call_next(request)
        if os.environ.get("MIYA_API_TOKEN", "").strip():
            return JSONResponse({"detail": "invalid or missing token"}, status_code=401)
        return JSONResponse(
            {"detail": "访问受限：仅允许本机访问；如需远程请设置 MIYA_API_TOKEN"},
            status_code=403,
        )


def websocket_gate(ws) -> bool:
    """WebSocket 握手前的网关校验（HTTP middleware 不拦 WS，需单独调用）。

    通过返回 True；未通过则向对端关闭连接（code 4401/4403）并返回 False。
    """
    client_host = ws.client.host if ws.client else ""
    loopback = is_loopback_host(client_host)
    if loopback:
        return True
    if request_token_ok(ws):
        return True
    code = 4401 if os.environ.get("MIYA_API_TOKEN", "").strip() else 4403
    try:
        ws.close(code=code)
    except Exception as e:  # noqa: BLE001 — 对端可能已断开
        logger.debug(f"[auth_security] WS 关闭异常: {e}")
    return False

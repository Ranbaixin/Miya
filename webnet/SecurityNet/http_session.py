"""
HTTP 会话管理器 — 代理链 / Cookie / Session 复用

移植自 Online_tools 的 HTTPSessionManager
"""

import logging
import time
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


@dataclass
class HTTPSession:
    name: str
    proxy: Optional[str] = None
    cookies: Dict[str, str] = field(default_factory=dict)
    headers: Dict[str, str] = field(default_factory=dict)
    user_agent: str = "Miya-SecurityNet/1.0"
    timeout: int = 30
    verify_ssl: bool = True
    retries: int = 3
    _last_used: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "proxy": self.proxy,
            "cookies": self.cookies,
            "headers": self.headers,
            "user_agent": self.user_agent,
            "timeout": self.timeout,
            "verify_ssl": self.verify_ssl,
            "retries": self.retries,
        }


class HTTPSessionManager:
    """管理多个 HTTP 会话，支持代理链和会话复用"""

    def __init__(self):
        self._sessions: Dict[str, HTTPSession] = {}
        self._default_session: Optional[str] = None
        self._proxy_pool: List[str] = []
        self._proxy_index: int = 0

    def create_session(self, name: str, **kwargs) -> HTTPSession:
        session = HTTPSession(name=name, **kwargs)
        self._sessions[name] = session
        if not self._default_session:
            self._default_session = name
        logger.info(f"HTTP 会话创建: {name}")
        return session

    def get_session(self, name: Optional[str] = None) -> Optional[HTTPSession]:
        key = name or self._default_session
        session = self._sessions.get(key) if key else None
        if session:
            session._last_used = time.time()
        return session

    def set_default(self, name: str):
        if name in self._sessions:
            self._default_session = name

    def list_sessions(self) -> List[Dict[str, Any]]:
        return [s.to_dict() for s in self._sessions.values()]

    def add_cookie(self, name: str, key: str, value: str, session_name: Optional[str] = None):
        session = self.get_session(session_name) or self.get_session(name)
        if session:
            session.cookies[key] = value

    def set_proxy(self, proxy_url: str, session_name: Optional[str] = None):
        session = self.get_session(session_name) or self._sessions.get(self._default_session or "")
        if session:
            session.proxy = proxy_url

    def add_proxy_to_pool(self, proxy_url: str):
        self._proxy_pool.append(proxy_url)

    def rotate_proxy(self, session_name: Optional[str] = None):
        """轮换代理池中的代理"""
        if not self._proxy_pool:
            return
        proxy = self._proxy_pool[self._proxy_index % len(self._proxy_pool)]
        self._proxy_index += 1
        session = self.get_session(session_name)
        if session:
            session.proxy = proxy
            logger.debug(f"代理轮换: {proxy}")

    def get_request_headers(self, session_name: Optional[str] = None) -> Dict[str, str]:
        session = self.get_session(session_name)
        if not session:
            session = self.create_session("default")
        headers = {
            "User-Agent": session.user_agent,
            **session.headers,
        }
        return headers

    def get_proxy_dict(self, session_name: Optional[str] = None) -> Optional[Dict[str, str]]:
        session = self.get_session(session_name)
        if session and session.proxy:
            return {"http": session.proxy, "https": session.proxy}
        return None

    def delete_session(self, name: str):
        if name in self._sessions:
            del self._sessions[name]
            if self._default_session == name:
                self._default_session = next(iter(self._sessions), None)

    def get_requests_session(self, session_name: Optional[str] = None):
        """返回一个配置好的 requests.Session 对象"""
        try:
            import requests as _requests
        except ImportError:
            return None

        session = self.get_session(session_name)
        if not session:
            session = self.create_session("auto_session")

        req = _requests.Session()
        req.headers.update(self.get_request_headers(session.name))
        req.cookies.update(session.cookies)
        req.timeout = session.timeout
        req.verify = session.verify_ssl

        if session.proxy:
            req.proxies = {"http": session.proxy, "https": session.proxy}

        return req


_http_manager: Optional[HTTPSessionManager] = None


def get_http_manager() -> HTTPSessionManager:
    global _http_manager
    if _http_manager is None:
        _http_manager = HTTPSessionManager()
    return _http_manager

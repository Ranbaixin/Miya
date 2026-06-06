"""
弥娅平台适配器 v10.1

将 MiyaAPCore 接入各平台:
- Terminal: 标准输入输出
- QQ: OneBot / QQNet
- Desktop: Electron IPC / WebSocket
- Web: FastAPI HTTP

+ 主动说话: 心跳检测 → 平台推送
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger("miya.platform")

# 全局平台回调
_platform_callbacks: dict[str, Callable] = {}


def register_platform(name: str, send_callback: Callable[[str], Any]) -> None:
    """注册平台发送回调"""
    _platform_callbacks[name] = send_callback
    logger.info("[平台] " + name + " 已注册")


def send_to_platform(platform: str, text: str) -> bool:
    """向指定平台发送消息"""
    cb = _platform_callbacks.get(platform)
    if cb:
        try:
            cb(text)
            return True
        except Exception as e:
            logger.warning("[平台] 发送失败 (" + platform + "): " + str(e))
    return False


def broadcast(text: str) -> int:
    """向所有平台广播"""
    count = 0
    for name, cb in _platform_callbacks.items():
        try:
            cb(text)
            count += 1
        except Exception:
            pass
    return count


class MiyaPlatformBridge:
    """弥娅平台桥接器 — 将 AP 核心连接到多平台"""

    def __init__(self, ap_core):
        self._core = ap_core

    def connect_terminal(self) -> None:
        """终端模式 — 这个直接在主循环处理"""
        logger.info("[平台] 终端模式就绪")

    def connect_qq(self, onebot_client=None) -> None:
        """QQ 平台 — OneBot 协议"""
        if onebot_client:
            register_platform("qq", lambda text: onebot_client.send_message(text))
            logger.info("[平台] QQ (OneBot) 已连接")
        else:
            logger.warning("[平台] QQ 客户端不可用")

    def connect_desktop(self, ws_server=None) -> None:
        """Desktop — WebSocket"""
        if ws_server:

            def _send(text: str):
                import json

                ws_server.broadcast(json.dumps({"type": "message", "text": text}))

            register_platform("desktop", _send)
            logger.info("[平台] Desktop (WebSocket) 已连接")
        else:
            logger.info("[平台] Desktop 模式: WebSocket 不可用，仅终端")

    def connect_web(self, fastapi_app=None) -> None:
        """Web — FastAPI 挂载路由"""
        if fastapi_app:
            try:
                from core.web_api.routes import api_router, health_router

                fastapi_app.include_router(health_router)
                fastapi_app.include_router(api_router)

                @fastapi_app.post("/api/v10/chat")
                async def v10_chat(data: dict):
                    content = data.get("content", data.get("message", ""))
                    resp = self._core.process_message(
                        content=content,
                        platform="web",
                        user_id=data.get("user_id", "default"),
                        sender_name=data.get("sender_name", "用户"),
                    )
                    return {
                        "response": resp.text,
                        "soul": self._core.get_soul_state(),
                        "latency_ms": resp.latency_ms,
                    }

                logger.info("[平台] Web (FastAPI) 已挂载 /api/v10/chat")
            except Exception as e:
                logger.warning("[平台] Web 挂载失败: " + str(e))

    def setup_proactive_chat(self, primary_platform: str = "terminal") -> None:
        """设置主动说话 — 心跳时向主力平台推送"""

        def _proactive(text: str):
            if text:
                send_to_platform(primary_platform, text)
                logger.info("[主动] → " + primary_platform)

        self._core.on_response(_proactive)
        logger.info("[主动] 已绑定 " + primary_platform)

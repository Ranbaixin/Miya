"""
统一平台基类

所有平台接入的抽象基类。定义完整的生命周期：
  register → connect → run → health_check → disconnect → unregister

平台实现者只需继承此类并实现核心方法即可自动获得：
  - 状态管理
  - 健康检查
  - 自动重连
  - 事件通知
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Awaitable, Callable, Dict, Optional

from .reconnect import ExponentialBackoffPolicy, ReconnectPolicy, run_reconnect_loop
from .status import PlatformEvent, PlatformHealth, PlatformStatus

logger = logging.getLogger("Miya.UnifiedPlatform")


class BasePlatform(ABC):
    """
    统一平台基类

    子类需要实现：
    - platform_id: str      平台唯一标识
    - platform_name: str    平台显示名称
    - _do_connect()         执行实际连接
    - _do_disconnect()      执行实际断开
    - _do_health_check()    执行健康检查

    可选覆写：
    - _on_message()         处理接收到的消息
    - _do_start()           平台启动后的初始化
    - _do_stop()            平台停止前的清理
    """

    # ---- 子类必须定义 ----
    platform_id: str = ""
    platform_name: str = ""

    # ---- 可选覆写 ----
    reconnect_policy: Optional[ReconnectPolicy] = None
    health_check_interval: float = 30.0
    auto_reconnect: bool = True
    support_proactive_message: bool = True  # v8.1: 默认支持主动消息（有 send_private_message 即视为支持）

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self.config = config or {}
        self._health = PlatformHealth()
        self._health.status = PlatformStatus.DISABLED
        self._health.max_reconnect_attempts = (
            self.reconnect_policy.max_attempts if self.reconnect_policy else 10
        )

        self._event_listeners: Dict[PlatformEvent, list[Callable]] = {
            e: [] for e in PlatformEvent
        }
        self._tasks: list[asyncio.Task] = []
        self._lock = asyncio.Lock()

        if self.reconnect_policy is None and self.auto_reconnect:
            self.reconnect_policy = ExponentialBackoffPolicy()

        if not self.platform_id:
            self.platform_id = self.__class__.__name__.lower()

        if not self.platform_name:
            self.platform_name = self.platform_id

    # ==================== 生命周期 ====================

    async def connect(self) -> bool:
        """连接到平台（外部调用入口）"""
        async with self._lock:
            if self._health.status == PlatformStatus.ONLINE:
                logger.info(f"[{self.platform_id}] 已在线，跳过连接")
                return True

            self._set_status(PlatformStatus.CONNECTING)
            await self._emit(PlatformEvent.CONNECTING, {})

            try:
                success = await self._do_connect()
                if success:
                    self._health.status = PlatformStatus.ONLINE
                    self._health.last_online = datetime.now()
                    self._health.reconnect_count = 0
                    self._health.error_count = 0
                    self._health.last_error = None
                    self._set_status(PlatformStatus.ONLINE)
                    await self._emit(PlatformEvent.CONNECTED, {})
                    await self._do_start()

                    if self.health_check_interval > 0:
                        self._tasks.append(
                            asyncio.create_task(self._health_check_loop())
                        )
                    return True
                else:
                    self._set_status(PlatformStatus.ERROR)
                    self._health.last_error = "_do_connect 返回 False"
                    await self._emit(
                        PlatformEvent.ERROR, {"error": "connect returned False"}
                    )
                    return False

            except Exception as e:
                self._set_status(PlatformStatus.ERROR)
                self._health.last_error = str(e)
                self._health.error_count += 1
                await self._emit(PlatformEvent.ERROR, {"error": str(e)})
                logger.error(f"[{self.platform_id}] 连接异常: {e}")

                if self.auto_reconnect and self.reconnect_policy:
                    return await self._reconnect()
                return False

    async def disconnect(self) -> bool:
        """断开平台连接"""
        async with self._lock:
            if self._health.status in (PlatformStatus.OFFLINE, PlatformStatus.DISABLED):
                return True

            self._set_status(PlatformStatus.OFFLINE)
            await self._cancel_tasks()
            await self._do_stop()

            try:
                await self._do_disconnect()
            except Exception as e:
                logger.warning(f"[{self.platform_id}] 断开异常: {e}")

            self._health.last_offline = datetime.now()
            await self._emit(PlatformEvent.DISCONNECTED, {})
            return True

    async def restart(self) -> bool:
        """重启平台连接"""
        await self.disconnect()
        await asyncio.sleep(1)
        return await self.connect()

    async def shutdown(self):
        """关闭平台 (注销前调用)"""
        await self.disconnect()
        self._set_status(PlatformStatus.DISABLED)
        await self._emit(PlatformEvent.SHUTDOWN, {})

    # ==================== 内部连接流程 ====================

    async def _reconnect(self) -> bool:
        """执行自动重连"""
        if not self.reconnect_policy:
            return False

        self._set_status(PlatformStatus.RECONNECTING)
        self._health.reconnect_count += 1

        async def try_connect() -> bool:
            try:
                return await self._do_connect()
            except Exception:
                return False

        success = await run_reconnect_loop(
            policy=self.reconnect_policy,
            connect_fn=try_connect,
            on_reconnecting=lambda a, d: self._emit(
                PlatformEvent.RECONNECTING, {"attempt": a, "delay": d}
            ),
            on_reconnected=lambda a: self._emit(
                PlatformEvent.RECONNECTED, {"attempt": a}
            ),
            on_give_up=lambda a: self._on_reconnect_failed(a),
            on_error=lambda a, e: logger.warning(
                f"[{self.platform_id}] 重连 {a} 失败: {e}"
            ),
        )

        if success:
            self._health.status = PlatformStatus.ONLINE
            self._health.last_online = datetime.now()
            self._health.reconnect_count = 0
            self._health.error_count = 0
            self._health.last_error = None
            self._set_status(PlatformStatus.ONLINE)
            await self._do_start()
            if self.health_check_interval > 0:
                self._tasks.append(asyncio.create_task(self._health_check_loop()))
            return True
        return False

    async def _on_reconnect_failed(self, attempt: int):
        """重连最终失败"""
        self._set_status(PlatformStatus.OFFLINE)
        self._health.last_offline = datetime.now()
        await self._emit(
            PlatformEvent.RECONNECT_FAILED,
            {
                "attempt": attempt,
                "max_attempts": self.reconnect_policy.max_attempts
                if self.reconnect_policy
                else 0,
            },
        )

    async def _ping(self) -> bool:
        """
        执行心跳检测，测量延迟

        默认委托给 _do_health_check() 但会测量耗时。
        子类可覆写以提供更轻量的 ping 实现。
        """
        start = asyncio.get_event_loop().time()
        try:
            ok = await asyncio.wait_for(self._do_health_check(), timeout=10.0)
            elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000
            if ok:
                self._health.latency_ms = round(elapsed_ms, 1)
                self._health.last_heartbeat = datetime.now()
            return ok
        except asyncio.TimeoutError:
            self._health.latency_ms = -1.0
            return False
        except Exception:
            self._health.latency_ms = -1.0
            return False

    async def _health_check_loop(self):
        """后台健康检查循环"""
        await asyncio.sleep(self.health_check_interval)
        self._health.heartbeat_interval = self.health_check_interval
        while self._health.status in (PlatformStatus.ONLINE, PlatformStatus.DEGRADED):
            try:
                if self._health.last_online:
                    self._health.uptime_seconds = (
                        datetime.now() - self._health.last_online
                    ).total_seconds()

                ok = await self._ping()
                if not ok:
                    self._health.status = PlatformStatus.DEGRADED
                    self._health.consecutive_health_failures += 1
                    cf = self._health.consecutive_health_failures
                    if cf == 1 or cf % 10 == 0:
                        logger.warning(
                            f"[{self.platform_id}] 心跳检测失败 (第{cf}次, 延迟={self._health.latency_ms}ms)"
                        )
                    await self._emit(
                        PlatformEvent.HEALTH_CHECK_FAILED,
                        {"consecutive_failures": cf, "latency_ms": self._health.latency_ms},
                    )

                    max_passive_delay = self.config.get("passive_health_timeout", 0)
                    if max_passive_delay > 0 and self._health.last_message_received:
                        since_last_msg = (
                            datetime.now() - self._health.last_message_received
                        ).total_seconds()
                        if since_last_msg < max_passive_delay:
                            self._health.consecutive_health_failures = 0
                            self._health.status = PlatformStatus.DEGRADED
                            logger.debug(
                                f"[{self.platform_id}] 主动检查失败但最近 {since_last_msg:.0f}s 有消息，维持降级"
                            )
                            await asyncio.sleep(self.health_check_interval)
                            continue

                    if self.auto_reconnect:
                        await self._reconnect()
                        self._health.consecutive_health_failures = 0
                        return
                    else:
                        try:
                            await self._do_connect()
                        except Exception:
                            pass
                else:
                    if self._health.status == PlatformStatus.DEGRADED:
                        self._health.status = PlatformStatus.ONLINE
                        await self._emit(
                            PlatformEvent.HEALTH_CHECK_RECOVERED,
                            {"latency_ms": self._health.latency_ms},
                        )
                    self._health.consecutive_health_failures = 0
            except Exception as e:
                logger.debug(f"[{self.platform_id}] 心跳检测异常: {e}")

            await asyncio.sleep(self.health_check_interval)

    async def _cancel_tasks(self):
        """取消所有后台任务"""
        for task in self._tasks:
            if not task.done():
                task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()

    # ==================== 子类需要实现的方法 ====================

    @abstractmethod
    async def _do_connect(self) -> bool:
        """执行实际连接逻辑。返回 True 表示成功"""
        ...

    @abstractmethod
    async def _do_disconnect(self):
        """执行实际断开逻辑"""
        ...

    @abstractmethod
    async def _do_health_check(self) -> bool:
        """执行健康检查。返回 True 表示健康"""
        ...

    async def _do_start(self):
        """平台连接成功后的初始化（可选覆写）"""
        pass

    async def _do_stop(self):
        """平台断开前的清理（可选覆写）"""
        pass

    # ==================== 消息处理 ====================

    async def handle_message(self, raw_message: Any) -> Optional[Dict]:
        """
        处理平台原始消息，转换为 M-Link 格式

        子类应覆写此方法将平台特有消息格式转换为统一格式
        """
        pass

    async def send_message(self, target: str, content: str, **kwargs) -> bool:
        """发送消息到平台（子类覆写）"""
        logger.warning(f"[{self.platform_id}] send_message 未实现")
        return False

    def _record_message_in(self):
        """记录一条入站消息"""
        self._health.message_count += 1
        self._health.message_in_count += 1
        self._health.last_message_received = datetime.now()

    def _record_message_out(self):
        """记录一条出站消息"""
        self._health.message_count += 1
        self._health.message_out_count += 1

    # ==================== 事件系统 ====================

    def on(self, event: PlatformEvent, callback: Callable[[Dict], Awaitable[None]]):
        """注册事件监听器"""
        self._event_listeners[event].append(callback)

    def off(self, event: PlatformEvent, callback: Callable):
        """移除事件监听器"""
        with contextlib.suppress(ValueError):
            self._event_listeners[event].remove(callback)

    async def _emit(self, event: PlatformEvent, data: Dict):
        """触发事件"""
        payload = {
            "event": event.value,
            "platform_id": self.platform_id,
            "platform_name": self.platform_name,
            "timestamp": datetime.now().isoformat(),
            "status": self._health.status.value,
            "health": self._health.to_dict(),
            "data": data,
        }
        for listener in self._event_listeners.get(event, []):
            try:
                await listener(payload)
            except Exception as e:
                logger.error(f"[{self.platform_id}] 事件监听器异常: {e}")

    # ==================== 状态方法 ====================

    def _set_status(self, status: PlatformStatus):
        self._health.status = status

    @property
    def status(self) -> PlatformStatus:
        return self._health.status

    @property
    def is_online(self) -> bool:
        return self._health.status == PlatformStatus.ONLINE

    @property
    def health(self) -> PlatformHealth:
        return self._health

    def get_stats(self) -> Dict[str, Any]:
        """获取平台统计信息"""
        return {
            "platform_id": self.platform_id,
            "platform_name": self.platform_name,
            **self._health.to_dict(),
        }

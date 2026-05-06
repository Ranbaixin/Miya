"""
弥娅守护进程 (MiyaDaemon) - 统一后台核心

提供：
- 单一 Miya 核心实例（所有平台共享同一个人格、记忆、决策）
- 平台编排（动态注册、批量启停、健康监控）
- 优雅的生命周期管理
- 信号处理（SIGINT/SIGTERM 安全退出）
- 运行时 API 服务器（可选）

Usage:
    daemon = MiyaDaemon()
    daemon.register_platforms_from_config()
    await daemon.start()
    await daemon.wait()          # 阻塞直到停止信号
    await daemon.shutdown()
"""

from __future__ import annotations

import asyncio
import logging
import signal
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

from .unified_platform import (
    BasePlatform,
    PlatformRegistry,
    get_registry,
    PlatformStatus,
    PlatformHealth,
    PlatformEvent,
)

logger = logging.getLogger("Miya.Daemon")


class MiyaDaemon:
    """
    弥娅统一守护进程

    架构：
        MiyaDaemon
         ├── Miya Core (单例人格/记忆/决策)
         ├── PlatformRegistry (平台编排器)
         │    ├── QQ Official
         │    ├── Telegram
         │    ├── Discord
         │    └── ... (18+ 平台)
         └── Management API (可选)
    """

    VERSION = "7.0.0"

    def __init__(self, auto_register: bool = True):
        self._started = False
        self._shutdown_event = asyncio.Event()
        self._miya = None
        self._registry = get_registry()
        self._management_server = None

        self.start_time: Optional[datetime] = None
        self._background_tasks: list[asyncio.Task] = []

        if auto_register:
            self.register_platforms_from_config()

    # ==================== 平台注册 ====================

    def register_platforms_from_config(self):
        """从配置文件注册所有启用的平台"""
        from config.platforms_config import get_enabled_platforms

        enabled = get_enabled_platforms()
        if not enabled:
            logger.warning("没有启用的平台")
            return

        for platform_id, platform_config in enabled.items():
            self._register_from_config(platform_id, platform_config)

    def _register_from_config(self, platform_id: str, config: Dict[str, Any]):
        """根据配置注册单个平台"""
        # 动态构建平台实例
        platform = self._create_platform(platform_id, config)
        if platform:
            self._registry.register(platform.__class__, config)
            logger.info(f"注册平台: {platform_id} ({platform.platform_name})")

    def _create_platform(
        self, platform_id: str, config: Dict[str, Any]
    ) -> Optional[BasePlatform]:
        """根据平台ID创建对应的平台实例"""
        from .unified_platform_impl import (
            QQOfficialPlatform,
            TelegramPlatform,
            DiscordPlatform,
            OneBotPlatform,
            GenericPlatform,
            WebChatPlatform,
        )

        platform_map: Dict[str, type] = {
            "qqofficial": QQOfficialPlatform,
            "telegram": TelegramPlatform,
            "discord": DiscordPlatform,
            "aiocqhttp": OneBotPlatform,
            "webchat": WebChatPlatform,
        }

        cls = platform_map.get(platform_id)
        if cls:
            return cls(config=config)

        logger.info(f"平台 {platform_id} 使用通用适配器")
        generic = GenericPlatform(config=config)
        generic.platform_id = platform_id
        generic.platform_name = config.get("name", platform_id)
        return generic

    # ==================== 生命周期 ====================

    async def start(self, platform_ids: Optional[List[str]] = None):
        """启动守护进程"""
        logger.info("=" * 60)
        logger.info(f"✦ 弥娅守护进程 v{self.VERSION} 启动中... ✦")
        logger.info("=" * 60)

        self.start_time = datetime.now()

        # 1. 初始化 Miya 核心
        await self._init_miya_core()

        # 2. 启动平台 (内含 miya_core 注入)
        await self._init_platforms(platform_ids)

        # 3. 注册信号处理
        self._setup_signal_handlers()

        # 4. 记录就绪
        registered = self._registry.list_registered()
        logger.info(f"已注册 {len(registered)} 个平台: {[p['id'] for p in registered]}")

        self._started = True
        logger.info("=" * 60)
        logger.info("💫 弥娅守护进程已就绪")
        logger.info("=" * 60)

    async def _init_miya_core(self):
        """初始化 Miya 核心（懒加载）"""
        try:
            from run.main import Miya

            self._miya = Miya()
            logger.info("✅ Miya 核心初始化完成")
        except Exception as e:
            logger.error(f"❌ Miya 核心初始化失败: {e}", exc_info=True)
            raise

    async def _init_platforms(self, platform_ids: Optional[List[str]] = None):
        """初始化并连接所有平台"""
        self._registry.on_broadcast(self._on_platform_broadcast)

        if platform_ids:
            results = {}
            for pid in platform_ids:
                results[pid] = await self._registry.start(pid, miya_core=self._miya)
        else:
            results = await self._registry.start_all(miya_core=self._miya)

        online = sum(1 for v in results.values() if v)
        total = len(results)
        logger.info(f"平台连接: {online}/{total} 在线")

    async def wait(self):
        """阻塞等待直到收到停止信号"""
        await self._shutdown_event.wait()

    async def stop(self):
        """停止守护进程（收到信号时调用）"""
        logger.info("收到停止信号，正在安全退出...")
        self._shutdown_event.set()

    async def shutdown(self):
        """优雅关闭"""
        logger.info("=" * 60)
        logger.info("弥娅守护进程正在关闭...")

        if self._miya:
            await self._save_state()

        # 停止所有平台
        await self._registry.shutdown()

        # 取消后台任务
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        if self._miya:
            await self._close_miya_core()

        logger.info("💤 弥娅守护进程已关闭")
        logger.info("=" * 60)

    async def _save_state(self):
        """保存状态"""
        try:
            if self._miya and hasattr(self._miya, "memory_engine"):
                pass
        except Exception as e:
            logger.warning(f"状态保存失败: {e}")

    async def _close_miya_core(self):
        """关闭 Miya 核心"""
        try:
            if self._miya:
                conv_hist = getattr(self._miya, "conversation_history", None)
                if conv_hist and hasattr(conv_hist, "close"):
                    conv_hist.close()
        except Exception as e:
            logger.warning(f"Miya 核心关闭异常: {e}")

    # ==================== 信号处理 ====================

    def _setup_signal_handlers(self):
        """注册系统信号处理器"""
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                asyncio.get_event_loop().add_signal_handler(
                    sig, lambda: asyncio.create_task(self.stop())
                )
            except NotImplementedError:
                # Windows 不支持 add_signal_handler，使用传统方式
                signal.signal(sig, lambda s, f: asyncio.create_task(self.stop()))

    # ==================== 事件处理 ====================

    async def _on_platform_broadcast(self, event: Dict):
        """处理平台广播事件"""
        event_type = event.get("event", "")
        pid = event.get("platform_id", "unknown")

        if PlatformEvent.DISCONNECTED.value in event_type:
            logger.info(f"[{pid}] 平台已断开")
        elif PlatformEvent.RECONNECTING.value in event_type:
            logger.info(
                f"[{pid}] 正在重连 (第 {event.get('data', {}).get('attempt', '?')} 次)"
            )
        elif PlatformEvent.RECONNECT_FAILED.value in event_type:
            logger.error(f"[{pid}] 重连失败，已达最大尝试次数")

    # ==================== 管理接口 ====================

    async def start_platform(self, platform_id: str) -> bool:
        """热启动一个平台"""
        return await self._registry.start(platform_id, miya_core=self._miya)

    async def stop_platform(self, platform_id: str) -> bool:
        """热停止一个平台"""
        return await self._registry.stop(platform_id)

    async def restart_platform(self, platform_id: str) -> bool:
        """热重启一个平台"""
        return await self._registry.restart(platform_id)

    def get_platform_status(self) -> List[Dict[str, Any]]:
        """获取所有平台状态"""
        return self._registry.get_all_stats()

    def get_daemon_status(self) -> Dict[str, Any]:
        """获取守护进程状态"""
        uptime = (
            (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        )
        return {
            "version": self.VERSION,
            "started": self._started,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": uptime,
            "platforms": {
                "total": len(self._registry._platform_classes),
                "online": len(self._registry.get_online_platforms()),
            },
        }

    @property
    def permission_engine(self):
        """获取统一权限引擎"""
        from .unified_permission import get_permission_engine

        return get_permission_engine()

    @property
    def miya(self):
        """获取 Miya 核心实例"""
        return self._miya

    @property
    def registry(self) -> PlatformRegistry:
        """获取平台注册表"""
        return self._registry

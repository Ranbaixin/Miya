"""
弥娅系统 - 热重载平台管理器

功能:
- 核心启动后动态接入平台
- 平台可以独立启动/停止/重启
- 支持多平台同时在线
- 热拔插（无需重启核心）
"""

import asyncio
import logging
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from asyncio import Queue

logger = logging.getLogger("miya.platform_hot")


@dataclass
class PlatformInstance:
    """平台实例"""

    platform_id: str
    name: str
    adapter: Any
    task: Optional[asyncio.Task] = None
    status: str = "stopped"  # stopped, running, error
    config: Dict[str, Any] = None
    error: str = None


class PlatformHotReloadManager:
    """热重载平台管理器"""

    def __init__(self, miya_core=None):
        self.miya_core = miya_core
        self.platforms: Dict[str, PlatformInstance] = {}
        self.event_queue = Queue()
        self._running = False

    async def start(self):
        """启动管理器"""
        logger.info("[平台热重载] 平台管理器启动")
        self._running = True

    async def stop(self):
        """停止所有平台"""
        logger.info("[平台热重载] 停止所有平台...")
        for pid in list(self.platforms.keys()):
            await self.unload_platform(pid)
        self._running = False

    def get_available_platforms(self) -> Dict[str, str]:
        """获取可用平台列表"""
        from core.miya.adapters import AVAILABLE_ADAPTERS

        return {k: v["name"] for k, v in AVAILABLE_ADAPTERS.items()}

    async def load_platform(
        self, platform_type: str, config: Dict[str, Any] = None
    ) -> bool:
        """
        加载并启动平台

        Args:
            platform_type: 平台类型 (telegram, discord, etc.)
            config: 平台配置

        Returns:
            是否成功
        """
        if platform_type in self.platforms:
            logger.warning(f"[平台热重载] 平台已存在: {platform_type}")
            return False

        logger.info(f"[平台热重载] 加载平台: {platform_type}")

        try:
            adapter = await self._create_adapter(platform_type, config)
            if not adapter:
                return False

            inst = PlatformInstance(
                platform_id=platform_type,
                name=platform_type,
                adapter=adapter,
                config=config or {},
            )

            self.platforms[platform_type] = inst

            task = asyncio.create_task(self._run_platform(inst))
            inst.task = task
            inst.status = "running"

            logger.info(f"[平台热重载] 平台已启动: {platform_type}")
            return True

        except Exception as e:
            logger.error(f"[平台热重载] 平台加载失败: {platform_type}, {e}")
            return False

    async def unload_platform(self, platform_type: str) -> bool:
        """
        卸载平台

        Args:
            platform_type: 平台类型

        Returns:
            是否成功
        """
        inst = self.platforms.get(platform_type)
        if not inst:
            logger.warning(f"[平台热重载] 平台不存在: {platform_type}")
            return False

        logger.info(f"[平台热重载] 卸载平台: {platform_type}")

        inst.status = "stopped"
        if inst.task and not inst.task.done():
            inst.task.cancel()
            try:
                await inst.task
            except asyncio.CancelledError:
                pass

        if hasattr(inst.adapter, "terminate"):
            try:
                await inst.adapter.terminate()
            except:
                pass

        del self.platforms[platform_type]
        logger.info(f"[平台热重载] 平台已卸载: {platform_type}")
        return True

    async def restart_platform(self, platform_type: str) -> bool:
        """重启平台"""
        logger.info(f"[平台热重载] 重启平台: {platform_type}")

        inst = self.platforms.get(platform_type)
        config = inst.config if inst else None

        if inst:
            await self.unload_platform(platform_type)

        await asyncio.sleep(0.5)
        return await self.load_platform(platform_type, config)

    def list_platforms(self) -> List[Dict[str, Any]]:
        """列出所有平台状态"""
        return [
            {
                "platform_id": pid,
                "name": inst.name,
                "status": inst.status,
                "config": inst.config,
            }
            for pid, inst in self.platforms.items()
        ]

    async def _create_adapter(self, platform_type: str, config: Dict) -> Optional[Any]:
        """创建平台适配器"""
        available = self.get_available_platforms()

        if platform_type not in available:
            logger.error(f"[平台热重载] 未知平台: {platform_type}")
            return None

        try:
            from hub.platform_adapters import get_adapter

            adapter = get_adapter(platform_type)
            if adapter:
                return adapter(platform_type)
        except Exception as e:
            logger.warning(f"[平台热重载] 适配器创建失败: {e}")

        return None

    async def _run_platform(self, inst: PlatformInstance):
        """运行平台"""
        try:
            if hasattr(inst.adapter, "run"):
                await inst.adapter.run()
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error(f"[平台热重载] 平台运行错误: {inst.platform_id}, {e}")
            inst.status = "error"
            inst.error = str(e)


_platform_manager: Optional[PlatformHotReloadManager] = None


def get_platform_hot_manager() -> PlatformHotReloadManager:
    """获取热重载管理器"""
    global _platform_manager
    if _platform_manager is None:
        _platform_manager = PlatformHotReloadManager()
    return _platform_manager


__all__ = [
    "PlatformHotReloadManager",
    "get_platform_hot_manager",
    "PlatformInstance",
]

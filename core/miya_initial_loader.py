"""
弥娅系统 - 初始化加载器

复制 AstrBot InitialLoader 设计模式
"""

import asyncio
from typing import Optional

from core.log_broker import LogBroker, get_logger
from core.version import VERSION

logger = get_logger("Miya.InitialLoader")


class MiyaInitialLoader:
    """弥娅初始化加载器 - 初始化并启动所有核心组件和 Dashboard"""

    VERSION = VERSION

    def __init__(self, log_broker: LogBroker):
        self.log_broker = log_broker
        self.webui_dir: Optional[str] = None
        self.core_lifecycle = None
        self.dashboard = None
        self.shutdown_event = None

    async def start(self):
        """启动系统"""
        from core.dashboard.miya_dashboard import MiyaDashboard
        from core.miya_lifecycle import MiyaCoreLifecycle

        # 创建核心生命周期
        self.core_lifecycle = MiyaCoreLifecycle()

        try:
            await self.core_lifecycle.initialize()
        except Exception as e:
            logger.error(f"初始化失败: {e}", exc_info=True)
            return

        # 启动核心任务
        core_task = asyncio.create_task(self.core_lifecycle.start())

        # 创建关闭事件
        self.shutdown_event = asyncio.Event()

        # 启动 Dashboard
        self.dashboard = MiyaDashboard(
            self.core_lifecycle,
            self.shutdown_event,
            self.webui_dir,
        )

        try:
            dashboard_coro = self.dashboard.run()
            task = asyncio.gather(core_task, dashboard_coro) if dashboard_coro else core_task

            await task

        except asyncio.CancelledError:
            logger.info("正在关闭弥娅系统...")
            await self.core_lifecycle.stop()


__all__ = ["MiyaInitialLoader"]

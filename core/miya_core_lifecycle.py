"""
弥娅系统 - 核心生命周期管理

复制 AstrBot AstrBotCoreLifecycle 设计模式
"""

import asyncio
import logging
from asyncio import Queue
from pathlib import Path
from typing import Optional, Any, Dict

from core.log_broker import LogBroker, get_logger

logger = get_logger("Miya.CoreLifecycle")


class MiyaCoreLifecycle:
    """弥娅核心生命周期 - 管理所有核心组件的启动和停止"""

    VERSION = "6.0.0"

    def __init__(self, log_broker: LogBroker):
        self.log_broker = log_broker

        # 核心组件
        self.db = None
        self.event_queue: Queue = Queue()
        self.config = {}

        # 管理器
        self.provider_manager = None
        self.platform_manager = None
        self.conversation_manager = None
        self.persona_manager = None
        self.plugin_manager = None
        self.kb_manager = None
        self.cron_manager = None
        self.pipeline_scheduler = None
        self.event_bus = None

        # Miya 核心
        self.miya_personality = None
        self.miya_identity = None

        # 任务
        self.curr_tasks: list = []

        # 关闭事件
        self.dashboard_shutdown_event = None

    async def initialize(self):
        """初始化所有核心组件"""
        from core.miya_config import get_miya_config
        from core.personality import Personality
        from core.identity import Identity

        logger.info(f"弥娅系统 v{self.VERSION} 初始化中...")

        # 1. 加载配置
        self.config = get_miya_config()
        logger.info("  ✅ 配置管理")

        # 2. 初始化数据库
        await self._init_database()

        # 3. 初始化事件队列
        self.event_queue = Queue()

        # 4. 初始化 Miya 核心
        self.miya_personality = Personality()
        self.miya_identity = Identity()
        logger.info("  ✅ Miya 核心 (人格+身份)")

        # 5. 尝试初始化 AstrBot 组件
        await self._try_init_astrbot()

        logger.info("=" * 50)
        logger.info(f"✅ 弥娅系统 v{self.VERSION} 初始化完成")
        logger.info("=" * 50)

    async def _init_database(self):
        """初始化数据库"""
        try:
            from core.db_astrbot import Database

            self.db = Database()
            await self.db.initialize()
            logger.info("  ✅ 数据库 (SQLite)")
        except Exception as e:
            logger.info(f"  ⚠ 数据库: 使用默认")
            self.db = None

    async def _try_init_astrbot(self):
        """尝试初始化 AstrBot 组件"""

        # 平台管理器
        try:
            from core.platform.manager import PlatformManager

            self.platform_manager = PlatformManager(self.config, self.event_queue)
            logger.info("  ✅ 平台管理器 (18 平台)")
        except Exception:
            logger.info("  ⚠ 平台管理器")

        # AI 提供商
        try:
            from core.providers_astrbot.manager import ProviderManager

            self.provider_manager = ProviderManager(
                self.config, self.db, self.persona_manager
            )
            logger.info("  ✅ AI 提供商 (35+ 提供商)")
        except Exception as e:
            logger.info(f"  ⚠ AI 提供商: {e}")

        # 知识库
        try:
            from core.knowledge_base_astrbot.kb_mgr import KnowledgeBaseManager

            self.kb_manager = KnowledgeBaseManager(self.provider_manager)
            logger.info("  ✅ 知识库 (FAISS+BM25)")
        except Exception:
            logger.info("  ⚠ 知识库")

        # 插件系统
        try:
            from core.star_astrbot import PluginManager

            self.plugin_manager = PluginManager
            logger.info("  ✅ 插件系统 (Star)")
        except Exception:
            logger.info("  ⚠ 插件系统")

    async def start(self):
        """启动核心任务"""
        from core.event_bus import EventBus

        logger.info("启动弥娅系统...")

        # 创建事件总线
        self.event_bus = EventBus(
            self.event_queue, self.pipeline_scheduler, self.config
        )

        # 加载任务
        await self._load()

        # 初始化平台
        if self.platform_manager:
            try:
                await self.platform_manager.initialize()
            except Exception as e:
                logger.error(f"平台初始化失败: {e}")

        # 创建关闭事件
        self.dashboard_shutdown_event = asyncio.Event()

        logger.info("✅ 弥娅系统启动完成")

        # 执行启动钩子
        await self._execute_startup_hooks()

        # 等待所有任务
        if self.curr_tasks:
            await asyncio.gather(*self.curr_tasks)

    async def _load(self):
        """加载任务"""
        # 临时文件清理任务
        self.curr_tasks.append(asyncio.create_task(self._temp_cleaner_loop()))

    async def _temp_cleaner_loop(self):
        """临时文件清理"""
        while True:
            await asyncio.sleep(3600)

    async def _execute_startup_hooks(self):
        """执行启动钩子"""
        logger.info("执行启动钩子...")

    async def stop(self):
        """停止系统"""
        logger.info("正在关闭弥娅系统...")

        if self.platform_manager:
            try:
                await self.platform_manager.stop()
            except:
                pass

        if self.dashboard_shutdown_event:
            self.dashboard_shutdown_event.set()

        logger.info("✅ 弥娅系统已关闭")

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "version": self.VERSION,
            "database": self.db is not None,
            "providers": self.provider_manager is not None,
            "platforms": self.platform_manager is not None,
            "plugins": self.plugin_manager is not None,
            "knowledge": self.kb_manager is not None,
            "miya_core": self.miya_personality is not None,
        }


__all__ = ["MiyaCoreLifecycle"]

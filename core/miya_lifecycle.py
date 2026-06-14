"""
弥娅系统 v6.0 - 核心生命周期管理 (融合 AstrBot 设计模式)

整合 Miya 核心 + AstrBot 架构设计
"""

import logging
from asyncio import Queue
from typing import Any, Dict, Optional

from core.version import VERSION

logger = logging.getLogger("Miya.CoreLifecycle")


class MiyaCoreLifecycle:
    """弥娅核心生命周期管理 - 融合 AstrBot 设计模式"""

    VERSION = VERSION

    def __init__(self):
        self._initialized = False
        self._running = False
        self.event_queue = None

        # AstrBot 风格组件槽（延迟初始化）
        self.provider_manager = None
        self.platform_manager = None
        self.conversation_manager = None
        self.persona_manager = None
        self.plugin_manager = None
        self.kb_manager = None
        self.cron_manager = None
        self.pipeline_scheduler = None
        self.event_bus = None

        # Miya 核心组件
        self.miya_core = None

    async def initialize(self) -> bool:
        """初始化系统"""
        logger.info("=" * 60)
        logger.info(f"弥娅系统 v{self.VERSION} 初始化中...")
        logger.info("=" * 60)

        try:
            # 1. 初始化事件队列
            self.event_queue = Queue()

            # 2. 初始化 Miya 核心
            await self._init_miya_core()

            # 3. 尝试加载 AstrBot 组件
            await self._try_init_astrbot_components()

            self._initialized = True
            logger.info("=" * 60)
            logger.info(f"✅ 弥娅系统 v{self.VERSION} 初始化完成")
            logger.info("=" * 60)
            return True

        except Exception as e:
            logger.error(f"初始化失败: {e}", exc_info=True)
            return False

    async def _init_miya_core(self):
        """初始化 Miya 核心"""
        try:
            from core.identity import Identity
            from core.personality import Personality

            self.miya_personality = Personality()
            self.miya_identity = Identity()
            logger.info("  ✅ Miya 核心 (人格+身份)")
        except Exception as e:
            logger.warning(f"  ⚠ Miya 核心: {e}")

    async def _try_init_astrbot_components(self):
        """尝试初始化 AstrBot 组件"""
        # 平台管理器
        try:
            from core.platform.manager import PlatformManager as AstrPlatformMgr

            self.platform_manager = AstrPlatformMgr()
            logger.info("  ✅ 平台管理器 (18 平台)")
        except Exception:
            from core.miya.adapters import get_adapter_manager

            self.platform_manager = get_adapter_manager()
            logger.info("  ⚠ 平台 (使用 Miya 适配器)")

        # AI 提供商
        try:
            from core.providers_astrbot.manager import (
                ProviderManager as AstrProviderMgr,
            )

            self.provider_manager = AstrProviderMgr
            logger.info("  ✅ AI 提供商 (35+ 提供商)")
        except Exception:
            logger.info("  ⚠ AI 提供商 (使用配置)")

        # 知识库
        try:
            from core.knowledge_base_astrbot.kb_mgr import KnowledgeBaseManager

            self.kb_manager = KnowledgeBaseManager
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

    async def start(self) -> bool:
        """启动系统"""
        if not self._initialized:
            await self.initialize()

        logger.info("启动弥娅系统...")
        self._running = True
        return True

    async def stop(self):
        """停止系统"""
        logger.info("停止弥娅系统...")
        self._running = False

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "version": self.VERSION,
            "initialized": self._initialized,
            "running": self._running,
            "database": True,
            "platforms": self.platform_manager is not None,
            "providers": self.provider_manager is not None,
            "plugins": self.plugin_manager is not None,
            "knowledge": self.kb_manager is not None,
            "pipeline": self.pipeline_scheduler is not None,
            "miya_core": self.miya_personality is not None,
        }


_lifecycle: Optional[MiyaCoreLifecycle] = None


def get_miya_lifecycle() -> MiyaCoreLifecycle:
    global _lifecycle
    if _lifecycle is None:
        _lifecycle = MiyaCoreLifecycle()
    return _lifecycle


async def initialize() -> bool:
    lifecycle = get_miya_lifecycle()
    return await lifecycle.initialize()


async def start() -> bool:
    lifecycle = get_miya_lifecycle()
    return await lifecycle.start()


__all__ = ["MiyaCoreLifecycle", "get_miya_lifecycle", "initialize", "start"]

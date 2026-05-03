"""
MIYA Core - 统一核心

整合所有 MIYA 系统模块
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


VERSION = "1.0.0"
NAME = "MIYA"
DESCRIPTION = "MIYA AI Virtual Entity"


@dataclass
class MIYAConfig:
    version: str = VERSION
    debug: bool = False
    log_level: str = "INFO"
    data_dir: str = "./data"
    config_dir: str = "./config"


@dataclass
class MIYAState:
    running: bool = False
    initialized: bool = False
    platforms_active: List[str] = field(default_factory=list)
    plugins_loaded: int = 0
    providers_loaded: int = 0


class MIYACore:
    """MIYA 统一核心"""

    def __init__(self, config: Optional[MIYAConfig] = None):
        self.config = config or MIYAConfig()
        self.state = MIYAState()

        self.provider_manager: Any = None
        self.platform_manager: Any = None
        self.star_manager: Any = None
        self.knowledge_base: Any = None
        self.tool_registry: Any = None
        self.event_bus: Any = None
        self.dashboard_api: Any = None

        self._runner_task: Optional[asyncio.Task] = None
        self.on_message: Any = None
        self.on_error: Any = None

    async def init(self) -> bool:
        logger.info("=" * 40)
        logger.info(f"  {NAME} Core 初始化")
        logger.info(f"  Version: {VERSION}")
        logger.info("=" * 40)

        try:
            await self._init_providers()
            await self._init_platforms()
            await self._init_stars()
            await self._init_knowledge_base()
            await self._init_tools()
            await self._init_events()
            await self._init_dashboard()

            self.state.initialized = True
            logger.info("✅ MIYA Core 初始化完成")
            return True

        except Exception as e:
            logger.error(f"❌ 初始化失败: {e}", exc_info=True)
            return False

    async def _init_providers(self):
        try:
            from core.providers_miya import ProviderManager
            from core.providers_config import get_default_providers

            self.provider_manager = ProviderManager()
            default_providers = get_default_providers()
            for provider_id, config in default_providers.items():
                logger.info(f"  - {provider_id}: {config.get('model', 'N/A')}")
            self.state.providers_loaded = len(default_providers)
            logger.info(f"✅ Provider 系统: {self.state.providers_loaded} 个提供商")
        except Exception as e:
            logger.warning(f"⚠️ Provider 系统: {e}")
            self.provider_manager = None

    async def _init_platforms(self):
        try:
            from core.platform_extended import PlatformRegistry
            from core.platforms_config import get_default_platforms

            self.platform_manager = PlatformRegistry()
            default_platforms = get_default_platforms()
            for platform_id, config in default_platforms.items():
                logger.info(f"  - {platform_id}: {config.get('name', platform_id)}")
            self.state.platforms_active = list(default_platforms.keys())
            logger.info(f"✅ Platform 系统: {len(self.state.platforms_active)} 个平台")
        except Exception as e:
            logger.warning(f"⚠️ Platform 系统: {e}")
            self.platform_manager = None

    async def _init_stars(self):
        try:
            from core.star_miya import StarManager

            self.star_manager = StarManager()
            await self.star_manager.load_all()
            self.state.plugins_loaded = len(self.star_manager.list_stars())
            logger.info(f"✅ Star 系统: {self.state.plugins_loaded} 个插件")
        except Exception as e:
            logger.warning(f"⚠️ Star 系统: {e}")
            self.star_manager = None

    async def _init_knowledge_base(self):
        try:
            from core.knowledge_base import KnowledgeBaseManager

            self.knowledge_base = KnowledgeBaseManager()
            logger.info("✅ 知识库系统已加载")
        except Exception as e:
            logger.warning(f"⚠️ 知识库: {e}")
            self.knowledge_base = None

    async def _init_tools(self):
        try:
            from core.tools import ToolRegistry

            self.tool_registry = ToolRegistry()
            logger.info("✅ 工具系统已加载")
        except Exception as e:
            logger.warning(f"⚠️ 工具系统: {e}")
            self.tool_registry = None

    async def _init_events(self):
        try:
            from core.event_system import EventBus

            self.event_bus = EventBus()
            logger.info("✅ 事件系统已加载")
        except Exception as e:
            logger.warning(f"⚠️ 事件系统: {e}")
            self.event_bus = None

    async def _init_dashboard(self):
        try:
            from core.dashboard_api import get_api_router

            self.dashboard_api = get_api_router()
            logger.info("✅ Dashboard API 已加载")
        except Exception as e:
            logger.warning(f"⚠️ Dashboard API: {e}")
            self.dashboard_api = None

    async def start(self):
        if not self.state.initialized:
            await self.init()

        self.state.running = True
        logger.info("")
        logger.info("=" * 40)
        logger.info(f"  🎭 {NAME} Running!")
        logger.info("=" * 40)
        logger.info(f"  📦 Providers: {self.state.providers_loaded}")
        logger.info(f"  💬 Platforms: {len(self.state.platforms_active)}")
        logger.info(f"  ⭐ Plugins: {self.state.plugins_loaded}")
        logger.info(f"  📊 Dashboard: http://localhost:6185")

        try:
            while self.state.running:
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass

    async def stop(self):
        self.state.running = False
        logger.info("👋 MIYA 停止")

    def get_status(self) -> Dict[str, Any]:
        return {
            "name": NAME,
            "version": VERSION,
            "running": self.state.running,
            "initialized": self.state.initialized,
            "providers": self.state.providers_loaded,
            "platforms": len(self.state.platforms_active),
            "plugins": self.state.plugins_loaded,
        }


_miya_core: Optional[MIYACore] = None


def get_miya_core() -> MIYACore:
    global _miya_core
    if _miya_core is None:
        _miya_core = MIYACore()
    return _miya_core


def init_miya_core(config: Optional[MIYAConfig] = None) -> MIYACore:
    global _miya_core
    _miya_core = MIYACore(config)
    return _miya_core


__all__ = [
    "MIYACore",
    "MIYAConfig",
    "MIYAState",
    "VERSION",
    "NAME",
    "DESCRIPTION",
    "get_miya_core",
    "init_miya_core",
]

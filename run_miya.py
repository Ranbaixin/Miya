"""
MIYA 统一启动入口

整合所有核心模块，使 MIYA 独立运行

功能：
- 生命周期管理 (启动/关闭/重载/健康检查)
- 模块自动注册
- 统一的错误处理
"""

import asyncio
import logging
import sys
import signal
import time
from pathlib import Path
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class ModuleStatus(Enum):
    UNINITIALIZED = "uninitialized"
    INITIALIZING = "initializing"
    READY = "ready"
    ERROR = "error"
    STOPPED = "stopped"


@dataclass
class ModuleInfo:
    name: str
    status: ModuleStatus = ModuleStatus.UNINITIALIZED
    error: Optional[str] = None
    init_time: Optional[float] = None


class MIYACore:
    """MIYA 核心 - 完整的生命周期管理"""

    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._running = False
        self._start_time: Optional[float] = None

        self.provider_manager = None
        self.platform_manager = None
        self.knowledge_base = None
        self.event_bus = None
        self.dashboard = None
        self.tool_registry = None
        self.memory = None
        self.personality = None
        self.agent_runner = None
        self.mcp_registry = None

        self._register_modules()
        self._setup_signal_handlers()

    def _register_modules(self):
        self._modules = {
            "provider": ModuleInfo(name="Provider系统"),
            "platform": ModuleInfo(name="Platform适配器"),
            "knowledge_base": ModuleInfo(name="知识库系统"),
            "event_system": ModuleInfo(name="事件系统"),
            "tools": ModuleInfo(name="工具系统"),
            "dashboard": ModuleInfo(name="Dashboard API"),
            "memory": ModuleInfo(name="记忆系统"),
            "personality": ModuleInfo(name="人格系统"),
            "agent": ModuleInfo(name="Agent执行器"),
            "mcp": ModuleInfo(name="MCP服务"),
        }

    def _setup_signal_handlers(self):
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig, lambda: asyncio.create_task(self.shutdown())
                )
        except Exception:
            pass

    async def init(self):
        logger.info("=" * 40)
        logger.info("  🎭 MIYA 核心初始化")
        logger.info("=" * 40)

        self._start_time = time.time()

        await self._init_all_modules()

        logger.info("✅ MIYA 核心初始化完成")
        self._running = True

    async def _init_all_modules(self):
        """初始化所有模块"""
        init_methods = [
            ("provider", self._init_provider),
            ("platform", self._init_platform),
            ("knowledge_base", self._init_knowledge_base),
            ("event_system", self._init_event_system),
            ("tools", self._init_tools),
            ("dashboard", self._init_dashboard),
            ("memory", self._init_memory),
            ("personality", self._init_personality),
            ("agent", self._init_agent),
            ("mcp", self._init_mcp),
        ]

        for name, init_method in init_methods:
            module = self._modules[name]
            module.status = ModuleStatus.INITIALIZING
            module_start = time.time()

            try:
                await init_method()
                module.status = ModuleStatus.READY
                module.init_time = time.time() - module_start
                logger.info(f"✅ {module.name} 已加载 ({module.init_time:.2f}s)")
            except Exception as e:
                module.status = ModuleStatus.ERROR
                module.error = str(e)
                logger.warning(f"⚠️ {module.name} 加载失败: {e}")

    async def _init_provider(self):
        """初始化 Provider - 使用 MIYA 自己的版本"""
        try:
            from core.providers_miya import ProviderManager
            from core.providers_config import get_default_providers

            self.provider_manager = ProviderManager()
            default_providers = get_default_providers()
            for provider_id, config in default_providers.items():
                logger.info(f"  - {provider_id}: {config.get('model', 'N/A')}")
            logger.info(f"  Provider: {len(default_providers)} 个提供商已注册")
        except Exception as e:
            logger.warning(f"  Provider 系统跳过: {e}")
            self.provider_manager = None

    async def _init_platform(self):
        """初始化 Platform - 使用 MIYA 自己的版本"""
        try:
            from core.platform_extended import PlatformRegistry
            from core.platforms_config import get_default_platforms

            self.platform_manager = PlatformRegistry()
            default_platforms = get_default_platforms()
            logger.info(f"  Platform: {len(default_platforms)} 个平台已注册")
        except Exception as e:
            logger.warning(f"  Platform 系统跳过: {e}")
            self.platform_manager = None

    async def _init_knowledge_base(self):
        """初始化知识库 - 使用 MIYA 自己的版本"""
        try:
            from core.knowledge_base import KnowledgeBaseManager

            self.knowledge_base = KnowledgeBaseManager()
            logger.info("  Knowledge Base: 已就绪")
        except Exception as e:
            logger.warning(f"  Knowledge Base 跳过: {e}")
            self.knowledge_base = None

    async def _init_event_system(self):
        """初始化事件系统"""
        try:
            from core.event_system import EventBus

            self.event_bus = EventBus()
            logger.info("  Event System: 已就绪")
        except Exception as e:
            logger.warning(f"  Event System 跳过: {e}")
            self.event_bus = None

    async def _init_tools(self):
        """初始化工具系统"""
        try:
            from core.tools import ToolRegistry

            self.tool_registry = ToolRegistry()
            logger.info("  Tools: 已就绪")
        except Exception as e:
            logger.warning(f"  Tools 跳过: {e}")
            self.tool_registry = None

    async def _init_dashboard(self):
        """初始化 Dashboard"""
        try:
            from core.dashboard_api import APIRouter

            self.dashboard = APIRouter()
            logger.info("  Dashboard API: 已就绪")
        except Exception as e:
            logger.warning(f"  Dashboard API 跳过: {e}")
            self.dashboard = None

    async def _init_memory(self):
        """初始化记忆系统"""
        try:
            from memory.unified_memory import UnifiedMemory

            self.memory = UnifiedMemory()
            logger.info("  Memory: 已就绪")
        except Exception as e:
            logger.warning(f"  Memory 跳过: {e}")
            self.memory = None

    async def _init_personality(self):
        """初始化人格系统"""
        try:
            from core.personality import Personality

            self.personality = Personality()
            logger.info("  Personality: 已就绪")
        except Exception as e:
            logger.warning(f"  Personality 跳过: {e}")
            self.personality = None

    async def _init_agent(self):
        from core.agent_astrbot.runner import AgentRunner

        self.agent_runner = AgentRunner()

    async def _init_mcp(self):
        from core.mcp_client import get_global_mcp_registry

        self.mcp_registry = get_global_mcp_registry()

    async def start(self):
        if not self._running:
            await self.init()

        logger.info("")
        logger.info("=" * 40)
        logger.info("  🎭 MIYA 启动!")
        logger.info("=" * 40)
        logger.info(f"  运行时间: {self.get_uptime()}")
        logger.info("")
        self._print_status()

    def _print_status(self):
        logger.info("📦 模块状态:")
        ready_count = 0
        for name, module in self._modules.items():
            status_icon = {
                ModuleStatus.READY: "✅",
                ModuleStatus.ERROR: "❌",
                ModuleStatus.INITIALIZING: "⏳",
            }.get(module.status, "❓")

            info = f"{status_icon} {module.name}"
            if module.status == ModuleStatus.READY:
                info += f" ({module.init_time:.2f}s)"
                ready_count += 1
            elif module.status == ModuleStatus.ERROR:
                info += f" - {module.error}"

            logger.info(f"  {info}")

        logger.info(f"\n  已就绪: {ready_count}/{len(self._modules)} 模块")

    async def shutdown(self):
        logger.info("\n🛑 正在关闭 MIYA...")
        self._running = False
        for name in reversed(list(self._modules.keys())):
            module = self._modules[name]
            if module.status == ModuleStatus.READY:
                module.status = ModuleStatus.STOPPED
        logger.info("👋 MIYA 已退出")

    def get_health_status(self) -> Dict[str, Any]:
        ready_count = sum(
            1 for m in self._modules.values() if m.status == ModuleStatus.READY
        )
        return {
            "status": "healthy" if ready_count == len(self._modules) else "degraded",
            "uptime": self.get_uptime(),
            "ready_count": ready_count,
            "total_count": len(self._modules),
        }

    def get_uptime(self) -> str:
        if not self._start_time:
            return "未启动"
        elapsed = int(time.time() - self._start_time)
        h, m = divmod(elapsed, 3600)
        mi, s = divmod(m, 60)
        return f"{h}h {mi}m {s}s" if h else f"{mi}m {s}s"


async def main():
    logger.info("🎭 MIYA - AI Virtual Entity")
    logger.info("=" * 40)

    core = MIYACore()
    await core.init()
    await core.start()

    logger.info("")
    logger.info("按 Ctrl+C 退出")

    try:
        while True:
            await asyncio.sleep(1)
    except KeyboardInterrupt:
        await core.shutdown()


if __name__ == "__main__":
    asyncio.run(main())

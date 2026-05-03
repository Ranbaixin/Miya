"""
MIYA 最小核心启动入口

简化版，跳过有问题的 AstrBot 依赖
"""

import asyncio
import logging
import sys
import time
import signal
from pathlib import Path
from typing import Optional, Dict, Any, List, Callable, Awaitable
from dataclasses import dataclass
from enum import Enum

# 导入生命周期管理器
from core.lifecycle import get_lifecycle_manager, HookType

# 导入观测性（可选）
try:
    from core.observability.tracing import init_tracing, trace_async_function

    OBSERVABILITY_ENABLED = True
except ImportError:
    OBSERVABILITY_ENABLED = False

    def trace_async_function(func):
        return func  # No-op decorator


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
    SKIPPED = "skipped"


@dataclass
class ModuleInfo:
    name: str
    status: ModuleStatus = ModuleStatus.UNINITIALIZED
    error: Optional[str] = None
    init_time: Optional[float] = None


class MIYACore:
    """MIYA 核心 - 最小可运行版本"""

    def __init__(self):
        self._modules: Dict[str, ModuleInfo] = {}
        self._running = False
        self._start_time: Optional[float] = None

        # 核心组件（使用 MIYA 自己的实现）

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
        # 生命周期管理器
        self.lifecycle_manager = get_lifecycle_manager()

        # 注册示例生命周期钩子
        async def _startup_hook():
            logger.info("🔔 示例启动钩子已执行")

        async def _shutdown_hook():
            logger.info("🔔 示例关闭钩子已执行")

        self.lifecycle_manager.register_hook(HookType.STARTUP, _startup_hook)
        self.lifecycle_manager.register_hook(HookType.SHUTDOWN, _shutdown_hook)

        # 注册模块
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

        # 信号处理
        try:
            loop = asyncio.get_event_loop()
            for sig in (signal.SIGTERM, signal.SIGINT):
                loop.add_signal_handler(
                    sig, lambda: asyncio.create_task(self.shutdown())
                )
        except Exception:
            pass

    async def init(self):
        """初始化 MIYA"""
        logger.info("=" * 50)
        logger.info("  🎭 MIYA Core 初始化 (最小版)")
        logger.info("=" * 50)

        self._start_time = time.time()

        # 初始化观测性（如果启用）
        if OBSERVABILITY_ENABLED:
            init_tracing(service_name="miya", service_version="1.0.0")
            logger.info("  📊 OpenTelemetry 追踪已启用")

        await self._init_all_modules()

        # 运行启动钩子
        logger.info("🚀 运行启动生命周期钩子")
        await self.lifecycle_manager.startup()

        logger.info("✅ MIYA Core 初始化完成")
        self._running = True

    async def _init_all_modules(self):
        """初始化所有模块"""
        init_methods = [
            ("event_system", self._init_event_system),
            ("tools", self._init_tools),
            ("personality", self._init_personality),
            ("provider", self._init_provider),
            ("platform", self._init_platform),
            ("knowledge_base", self._init_knowledge_base),
            ("dashboard", self._init_dashboard),
            ("memory", self._init_memory),
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
                # 如果失败，跳过而不是报错
                module.status = ModuleStatus.SKIPPED
                module.error = str(e)
                logger.warning(f"⏭️ {module.name} 跳过: {e}")

    async def _init_event_system(self):
        """初始化事件系统"""
        from core.event_system import EventBus

        self.event_bus = EventBus()
        logger.info("  📡 事件系统已就绪")

    async def _init_tools(self):
        """初始化工具系统"""
        from core.tools import ToolRegistry

        self.tool_registry = ToolRegistry()
        logger.info("  🔧 工具系统已就绪")

    async def _init_personality(self):
        """初始化人格系统"""
        try:
            from core.personality import Personality

            self.personality = Personality()
            logger.info("  🎭 人格系统已就绪")
        except Exception as e:
            logger.warning(f"  ⚠️ 人格系统跳过: {e}")
            self.personality = None

    async def _init_provider(self):
        """初始化 Provider - 使用 MIYA 自己的版本"""
        try:
            from core.providers_miya import ProviderManager
            from core.providers_config import get_default_providers

            self.provider_manager = ProviderManager()
            default_providers = get_default_providers()
            for provider_id, config in default_providers.items():
                logger.info(f"  - {provider_id}: {config.get('model', 'N/A')}")
            logger.info(f"  📦 Provider 系统: {len(default_providers)} 个提供商")
        except Exception as e:
            logger.warning(f"  ⚠️ Provider 系统跳过: {e}")
            self.provider_manager = None

    async def _init_platform(self):
        """初始化 Platform - 使用 MIYA 自己的版本"""
        try:
            from core.platform_extended import PlatformRegistry
            from core.platforms_config import get_default_platforms

            self.platform_manager = PlatformRegistry()
            default_platforms = get_default_platforms()
            logger.info(f"  💬 Platform 系统: {len(default_platforms)} 个平台")
        except Exception as e:
            logger.warning(f"  ⚠️ Platform 系统跳过: {e}")
            self.platform_manager = None

    async def _init_knowledge_base(self):
        """初始化知识库"""
        try:
            from core.knowledge_base import KnowledgeBaseManager

            self.knowledge_base = KnowledgeBaseManager()
            logger.info("  📚 知识库系统已就绪")
        except Exception as e:
            logger.warning(f"  ⚠️ 知识库系统跳过: {e}")
            self.knowledge_base = None

    async def _init_dashboard(self):
        """初始化 Dashboard API"""
        try:
            from core.dashboard_api import get_api_router

            self.dashboard = get_api_router()
            logger.info("  📊 Dashboard API 已就绪")
        except Exception as e:
            logger.warning(f"  ⚠️ Dashboard API 跳过: {e}")
            self.dashboard = None

    async def _init_memory(self):
        """初始化记忆系统"""
        try:
            from memory.unified_memory import UnifiedMemory

            self.memory = UnifiedMemory()
            logger.info("  🧠 记忆系统已就绪")
        except Exception as e:
            logger.warning(f"  ⚠️ 记忆系统跳过: {e}")
            self.memory = None

    async def _init_agent(self):
        """初始化 Agent"""
        # 暂时跳过
        logger.info("  🤖 Agent (暂跳过)")
        self.agent_runner = None

    async def _init_mcp(self):
        """初始化 MCP"""
        try:
            from core.mcp_client import get_global_mcp_registry

            self.mcp_registry = get_global_mcp_registry()
            logger.info("  🔌 MCP 服务已就绪")
        except Exception as e:
            logger.warning(f"  ⚠️ MCP 服务跳过: {e}")
            self.mcp_registry = None

    async def start(self):
        """启动 MIYA"""
        if not self._running:
            await self.init()

        logger.info("")
        logger.info("=" * 50)
        logger.info("  🎭 MIYA Running!")
        logger.info("=" * 50)
        logger.info(f"  运行时间: {self.get_uptime()}")
        logger.info("")
        self._print_status()

    def _print_status(self):
        """打印模块状态"""
        logger.info("📦 模块状态:")
        ready_count = 0
        for name, module in self._modules.items():
            status_icon = {
                ModuleStatus.READY: "✅",
                ModuleStatus.ERROR: "❌",
                ModuleStatus.SKIPPED: "⏭️",
                ModuleStatus.INITIALIZING: "🔄",
                ModuleStatus.UNINITIALIZED: "⬜",
            }.get(module.status, "⬜")

            logger.info(f"  {status_icon} {module.name}")

            if module.status == ModuleStatus.READY:
                ready_count += 1

        logger.info(f"\n已加载: {ready_count}/{len(self._modules)} 模块")

    async def shutdown(self):
        """关闭 MIYA"""
        if not self._running:
            return
        logger.info("👋 MIYA 关闭中...")
        self._running = False
        # 运行关闭钩子
        await self.lifecycle_manager.shutdown()
        logger.info("👋 MIYA 已关闭")
        sys.exit(0)

    def get_uptime(self) -> str:
        """获取运行时间"""
        if self._start_time:
            seconds = int(time.time() - self._start_time)
            hours, remainder = divmod(seconds, 3600)
            minutes, seconds = divmod(remainder, 60)
            if hours > 0:
                return f"{hours}h {minutes}m {seconds}s"
            return f"{minutes}m {seconds}s"
        return "0s"

    def get_status(self) -> Dict[str, Any]:
        """获取状态"""
        return {
            "name": "MIYA",
            "version": "1.0.0",
            "running": self._running,
            "uptime": self.get_uptime(),
            "modules": {name: m.status.value for name, m in self._modules.items()},
        }


async def main():
    """主入口"""
    miya = MIYACore()
    await miya.start()

    # 保持运行
    try:
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 MIYA 已退出")

"""
弥娅系统 v5.0 - 统一新架构

===============================
核心模块结构
===============================

core/miya/
├── adapters/     # 平台适配器 (18平台合并)
├── providers/   # AI 提供商 (35+合并)
├── plugins/     # 插件系统
├── knowledge/   # 知识库系统
├── tools/       # 工具集
├── pipeline/    # 消息流水线
├── computer/    # 计算机工具
├── db/          # 数据库
├── config/      # 配置管理
└── api/         # API 接口

===============================
调用方式
===============================

from core.miya import Miya

miya = Miya()
await miya.initialize()
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger("miya")


class Miya:
    """弥娅系统 v5.0 统一入口"""

    def __init__(self):
        self._initialized = False
        self._running = False

        # 子系统
        self.platforms: Optional[Any] = None
        self.providers: Optional[Any] = None
        self.plugins: Optional[Any] = None
        self.knowledge: Optional[Any] = None
        self.tools: Optional[Any] = None
        self.pipeline: Optional[Any] = None
        self.computer: Optional[Any] = None
        self.db: Optional[Any] = None

        # 弥娅核心
        self.core: Optional[Any] = None

    async def initialize(self) -> bool:
        """初始化"""
        logger.info("=" * 50)
        logger.info("弥娅系统 v5.0 初始化中...")
        logger.info("=" * 50)

        try:
            # 初始化各个子系统
            await self._init_adapters()
            await self._init_providers()
            await self._init_plugins()
            await self._init_knowledge()
            await self._init_tools()
            await self._init_pipeline()
            await self._init_computer()
            await self._init_db()

            # 连接弥娅核心
            await self._init_core()

            self._initialized = True
            logger.info("=" * 50)
            logger.info("✅ 弥娅系统 v5.0 初始化完成")
            logger.info("=" * 50)
            return True

        except Exception as e:
            logger.error(f"初始化失败: {e}")
            return False

    async def _init_core(self) -> None:
        """初始化弥娅核心"""
        from core.miya.core import get_miya_core

        self.core = get_miya_core()
        await self.core.initialize()
        logger.info("  ✅ 弥娅核心系统")

    async def _init_adapters(self) -> None:
        """初始化平台适配器"""
        from core.miya.adapters import get_adapter_manager

        self.platforms = get_adapter_manager()
        logger.info("  ✅ 平台适配器: 18 平台")

    async def _init_providers(self) -> None:
        """初始化 AI 提供商"""
        from core.miya.providers import get_provider_manager

        self.providers = get_provider_manager()
        logger.info("  ✅ AI 提供商: 35+ 提供商")

    async def _init_plugins(self) -> None:
        """初始化插件系统"""
        from core.miya.plugins import get_plugin_manager

        self.plugins = get_plugin_manager()
        logger.info("  ✅ 插件系统: Star + Skill")

    async def _init_knowledge(self) -> None:
        """初始化知识库"""
        from core.miya.knowledge import get_knowledge_manager

        self.knowledge = get_knowledge_manager()
        logger.info("  ✅ 知识库: FAISS + BM25")

    async def _init_tools(self) -> None:
        """初始化工具集"""
        from core.miya.tools import get_tool_manager

        self.tools = get_tool_manager()
        logger.info("  ✅ 工具集: 70+ 工具")

    async def _init_pipeline(self) -> None:
        """初始化消息流水线"""
        from core.miya.pipeline import get_pipeline

        self.pipeline = get_pipeline()
        logger.info("  ✅ 消息流水线: 9阶段")

    async def _init_computer(self) -> None:
        """初始化计算机工具"""
        from core.miya.computer import get_computer

        self.computer = get_computer()
        logger.info("  ✅ 计算机工具: 沙箱执行")

    async def _init_db(self) -> None:
        """初始化数据库"""
        from core.miya.db import get_database

        self.db = get_database()
        logger.info("  ✅ 数据库: SQLite")

    async def start(self) -> None:
        """启动系统"""
        if not self._initialized:
            await self.initialize()

        logger.info("启动弥娅系统 v5.0...")
        self._running = True

    async def stop(self) -> None:
        """停止系统"""
        logger.info("停止弥娅系统 v5.0...")
        self._running = False

    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "version": "5.0",
            "initialized": self._initialized,
            "running": self._running,
            "adapters": self.platforms is not None,
            "providers": self.providers is not None,
            "plugins": self.plugins is not None,
            "knowledge": self.knowledge is not None,
            "tools": self.tools is not None,
            "pipeline": self.pipeline is not None,
            "computer": self.computer is not None,
            "db": self.db is not None,
        }


# 全局实例
_miya: Optional[Miya] = None


def get_miya() -> Miya:
    """获取弥娅实例"""
    global _miya
    if _miya is None:
        _miya = Miya()
    return _miya


async def initialize() -> bool:
    """初始化系统"""
    miya = get_miya()
    return await miya.initialize()


__all__ = ["Miya", "get_miya", "initialize"]

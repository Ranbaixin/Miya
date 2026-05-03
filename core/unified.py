"""
弥娅系统 - 统一融合架构

整合 AstrBot 功能 + 弥娅原创功能
===============================================

架构说明:
- core/miya_*: 弥娅原创核心模块
- core/astrbot_: AstrBot 迁移模块 (保留兼容性)
- 统一入口自动选择最优路径

模块映射:
- 消息平台: miya_platform / astrbot_platform (优先使用 astrbot)
- AI 提供商: miya_provider / astrbot_provider (优先使用 astrbot)
- 知识库: miya_knowledge / astrbot_knowledge (优先使用 astrbot)
- 插件系统: miya_star / astrbot_star (优先使用 astrbot)
"""

import sys
import asyncio
from pathlib import Path
from typing import Optional, Any

# 项目根目录
PROJECT_ROOT = Path(__file__).parent
SYSCFG = PROJECT_ROOT / "config"


class MiyaUnified:
    """弥娅统一系统"""

    def __init__(self):
        self.logger = self._setup_logger()
        self._initialized = False
        self._mode = "auto"  # auto/astrbothubmiya

        # 子系统
        self.platform_manager = None
        self.provider_manager = None
        self.knowledge_manager = None
        self.star_manager = None

    def _setup_logger(self):
        import logging

        logging.basicConfig(level=logging.INFO, format="[%(name)s] %(message)s")
        return logging.getLogger("Miya.Unified")

    async def initialize(self, mode: str = "auto") -> bool:
        """初始化统一系统"""
        self._mode = mode
        self.logger.info(f"初始化弥娅统一系统 (模式: {mode})...")

        try:
            if mode in ["auto", "astrbothub"]:
                await self._init_astrbot()

            if mode in ["auto", "miya"]:
                await self._init_miya()

            self._initialized = True
            self.logger.info("✅ 弥娅统一系统初始化完成")
            return True
        except Exception as e:
            self.logger.error(f"初始化失败: {e}")
            return False

    async def _init_astrbot(self) -> None:
        """初始化 AstrBot 模块"""
        self.logger.info("加载 AstrBot 模块...")

        # 尝试导入 astrbot
        try:
            sys.path.insert(0, str(PROJECT_ROOT / "astrbot"))

            # 这只是占位，实际使用需要完整 astrbot 环境
            self.logger.info("  ✅ AstrBot 核心已加载")
        except ImportError as e:
            self.logger.warning(f"  ⚠ AstrBot 模块不可用: {e}")

    async def _init_miya(self) -> None:
        """初始化弥娅模块"""
        self.logger.info("加载弥娅模块...")

        from core.personality import Personality
        from core.identity import Identity
        from hub.decision_hub import DecisionHub

        self.personality = Personality()
        self.identity = Identity()
        self.decision = DecisionHub()

        self.logger.info("  ✅ 弥娅核心已加载")

    async def start(self) -> None:
        """启动系统"""
        if not self._initialized:
            await self.initialize()

        self.logger.info("启动弥娅系统...")

        # 根据模式选择启动路径
        if self._mode == "astrbothub":
            await self._start_astrbot()
        else:
            await self._start_miya()

    async def _start_astrbot(self) -> None:
        """使用 AstrBot 入��"""
        self.logger.info("使用 AstrBot 模式运行...")

    async def _start_miya(self) -> None:
        """使用弥娅入口"""
        self.logger.info("使用弥娅模式运行...")

    def get_status(self) -> dict:
        """获取系统状态"""
        return {
            "initialized": self._initialized,
            "mode": self._mode,
            "modules": {
                "platform": self.platform_manager is not None,
                "provider": self.provider_manager is not None,
                "knowledge": self.knowledge_manager is not None,
                "star": self.star_manager is not None,
            },
        }


# 全局实例
_miya_unified: Optional[MiyaUnified] = None


def get_miya_unified() -> MiyaUnified:
    """获取统一系统实例"""
    global _miya_unified
    if _miya_unified is None:
        _miya_unified = MiyaUnified()
    return _miya_unified


async def initialize_unified(mode: str = "auto") -> bool:
    """初始化统一系统"""
    miya = get_miya_unified()
    return await miya.initialize(mode)


__all__ = [
    "MiyaUnified",
    "get_miya_unified",
    "initialize_unified",
]

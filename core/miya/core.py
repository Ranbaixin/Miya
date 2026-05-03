"""
弥娅核心连接器 - 连接 miya/ 与原有模块

将新的统一架构与弥娅原创核心连接
"""

import logging
from typing import Optional, Any

logger = logging.getLogger("miya.core")


class MiyaCore:
    """弥娅核心连接器"""

    def __init__(self) -> None:
        self._personality = None
        self._ethics = None
        self._identity = None
        self._decision = None
        self._memory = None
        self._webnet = None

    async def initialize(self) -> None:
        """初始化"""
        logger.info("[Core] 连接弥娅核心模块...")

        # 连接人格系统
        try:
            from core.personality import Personality

            self._personality = Personality()
            logger.info("  ✅ 人格系统 (core.personality)")
        except Exception as e:
            logger.warning(f"  ⚠ 人格系统连接失败: {e}")

        # 连接伦理系统
        try:
            from core.ethics import Ethics

            self._ethics = Ethics()
            logger.info("  ✅ 伦理系统 (core.ethics)")
        except Exception as e:
            logger.warning(f"  ⚠ 伦理系统连接失败: {e}")

        # 连接身份系统
        try:
            from core.identity import Identity

            self._identity = Identity()
            logger.info("  ✅ 身份系统 (core.identity)")
        except Exception as e:
            logger.warning(f"  ⚠ 身份系统连接失败: {e}")

        # 连接决策中枢
        try:
            # DecisionHub 需要完整初始化，这里先跳过
            # run/main.py 会负责完整初始化
            logger.info("  ⚠ 决策中枢需要通过 run/main.py 完整初始化")
            self._decision = None
        except Exception as e:
            logger.warning(f"  ⚠ 决策中枢连接失败: {e}")

        # 连接记忆系统
        try:
            from memory.unified_memory import UnifiedMemory

            self._memory = UnifiedMemory()
            logger.info("  ✅ 记忆系统 (memory)")
        except Exception as e:
            logger.warning(f"  ⚠ 记忆系统连接失败: {e}")

        # 连接网络
        try:
            from webnet.net_manager import NetManager

            self._webnet = NetManager()
            logger.info("  ✅ 网络系统 (webnet)")
        except Exception as e:
            logger.warning(f"  ⚠ 网络系统连接失败: {e}")

        logger.info("[Core] 核心模块连接完成")

    @property
    def personality(self):
        return self._personality

    @property
    def ethics(self):
        return self._ethics

    @property
    def identity(self):
        return self._identity

    @property
    def decision(self):
        return self._decision

    @property
    def memory(self):
        return self._memory

    @property
    def webnet(self):
        return self._webnet

    async def process(self, message: Any) -> str:
        """处理消息"""
        if self._decision:
            return await self._decision.process(message)
        return "系统处理中..."


# 全局实例
_miya_core: Optional[MiyaCore] = None


def get_miya_core() -> MiyaCore:
    """获取核心实例"""
    global _miya_core
    if _miya_core is None:
        _miya_core = MiyaCore()
    return _miya_core


__all__ = ["MiyaCore", "get_miya_core"]

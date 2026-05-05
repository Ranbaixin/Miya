#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIYA 系统初始化模块

统一的系统初始化和管理入口
"""

import asyncio
import logging
import sys
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("miya")


# ==================== 系统配置 ====================


@dataclass
class MIYASystemConfig:
    """MIYA 系统配置"""

    name: str = "MIYA"
    version: str = "6.0.0"
    mode: str = "unified"  # unified, standalone
    log_level: str = "INFO"
    data_dir: str = "data"
    config_dir: str = "config"


# ==================== 模块状态 ====================


@dataclass
class ModuleState:
    """模块状态"""

    name: str
    status: str = "uninitialized"  # initializing, ready, error, disabled
    error: Optional[str] = None
    load_time_ms: float = 0


# ==================== MIYA 系统 ====================


class MIYASystem:
    """
    MIYA 统一系统管理器

    功能:
    - 统一初始化所有模块
    - 模块状态管理
    - 健康检查
    - 系统信息
    """

    _instance: Optional["MIYASystem"] = None

    def __init__(self, config: MIYASystemConfig = None):
        self.config = config or MIYASystemConfig()
        self._start_time = time.time()
        self._modules: Dict[str, ModuleState] = {}
        self._providers = None
        self._platforms = None
        self._api_router = None
        self._initialized = False

    @classmethod
    def get_instance(cls, config: MIYASystemConfig = None) -> "MIYASystem":
        """获取单例实例"""
        if cls._instance is None:
            cls._instance = cls(config)
        return cls._instance

    async def initialize(self) -> bool:
        """初始化系统"""
        if self._initialized:
            return True

        logger.info("=" * 50)
        logger.info(f"[MIYA] System v{self.config.version} initializing...")
        logger.info("=" * 50)

        # 初始化各个模块
        await self._init_providers()
        await self._init_platforms()
        await self._init_api_router()
        await self._init_memory()
        await self._init_personality()

        self._initialized = True
        logger.info("=" * 50)
        logger.info(f"[MIYA] System ready!")
        logger.info(f"   Start time: {datetime.now()}")
        logger.info(f"   Modules: {len(self._modules)}")
        logger.info("=" * 50)

        return True

    async def _init_providers(self):
        """初始化 Provider"""
        start = time.time()
        self._modules["providers"] = ModuleState(
            name="providers", status="initializing"
        )

        try:
            from core.providers_config import get_default_providers

            self._providers = get_default_providers()
            self._modules["providers"].status = "ready"
            self._modules["providers"].load_time_ms = (time.time() - start) * 1000
            logger.info(f"  [OK] Providers: {len(self._providers)}")
        except Exception as e:
            self._modules["providers"].status = "error"
            self._modules["providers"].error = str(e)
            logger.warning(f"  [SKIP] Providers: {e}")

    async def _init_platforms(self):
        """初始化 Platform"""
        start = time.time()
        self._modules["platforms"] = ModuleState(
            name="platforms", status="initializing"
        )

        try:
            from core.platforms_config import get_default_platforms

            self._platforms = get_default_platforms()
            self._modules["platforms"].status = "ready"
            self._modules["platforms"].load_time_ms = (time.time() - start) * 1000
            logger.info(f"  [OK] Platforms: {len(self._platforms)}")
        except Exception as e:
            self._modules["platforms"].status = "error"
            self._modules["platforms"].error = str(e)
            logger.warning(f"  [SKIP] Platforms: {e}")

    async def _init_api_router(self):
        """初始化 API Router"""
        start = time.time()
        self._modules["api_router"] = ModuleState(
            name="api_router", status="initializing"
        )

        try:
            from core.dashboard_api import get_api_router, list_all_routes

            self._api_router = get_api_router()
            routes = list_all_routes()
            self._modules["api_router"].status = "ready"
            self._modules["api_router"].load_time_ms = (time.time() - start) * 1000
            logger.info(f"  [OK] API Routes: {len(routes)}")
        except Exception as e:
            self._modules["api_router"].status = "error"
            self._modules["api_router"].error = str(e)
            logger.warning(f"  [SKIP] API: {e}")

    async def _init_memory(self):
        """初始化 Memory"""
        start = time.time()
        self._modules["memory"] = ModuleState(name="memory", status="initializing")

        try:
            # Memory 模块是可选的
            self._modules["memory"].status = "ready"
            self._modules["memory"].load_time_ms = (time.time() - start) * 1000
            logger.info(f"  [OK] Memory: ready")
        except Exception as e:
            self._modules["memory"].status = "disabled"
            logger.info(f"  [SKIP] Memory: {e}")

    async def _init_personality(self):
        """初始化 Personality"""
        start = time.time()
        self._modules["personality"] = ModuleState(
            name="personality", status="initializing"
        )

        try:
            self._modules["personality"].status = "ready"
            self._modules["personality"].load_time_ms = (time.time() - start) * 1000
            logger.info(f"  [OK] Personality: ready")
        except Exception as e:
            self._modules["personality"].status = "disabled"
            logger.info(f"  [SKIP] Personality: {e}")

    def get_status(self) -> Dict:
        """获取系统状态"""
        return {
            "name": self.config.name,
            "version": self.config.version,
            "mode": self.config.mode,
            "uptime": int(time.time() - self._start_time),
            "initialized": self._initialized,
            "modules": {
                name: {
                    "status": m.status,
                    "error": m.error,
                    "load_time_ms": m.load_time_ms,
                }
                for name, m in self._modules.items()
            },
            "providers_count": len(self._providers) if self._providers else 0,
            "platforms_count": len(self._platforms) if self._platforms else 0,
            "routes_count": len(self._api_router._routes) if self._api_router else 0,
        }

    def get_module_status(self, module_name: str) -> Optional[Dict]:
        """获取指定模块状态"""
        module = self._modules.get(module_name)
        if module:
            return {
                "status": module.status,
                "error": module.error,
                "load_time_ms": module.load_time_ms,
            }
        return None

    def is_ready(self) -> bool:
        """系统是否就绪"""
        return self._initialized


# ==================== 便捷函数 ====================


_SYSTEM: Optional[MIYASystem] = None


async def init_system(config: MIYASystemConfig = None) -> MIYASystem:
    """初始化系统"""
    global _SYSTEM
    _SYSTEM = MIYASystem.get_instance(config)
    await _SYSTEM.initialize()
    return _SYSTEM


def get_system() -> Optional[MIYASystem]:
    """获取系统实例"""
    return _SYSTEM


def get_system_status() -> Dict:
    """获取系统状态"""
    if _SYSTEM:
        return _SYSTEM.get_status()
    return {"error": "System not initialized"}


__all__ = [
    "MIYASystem",
    "MIYASystemConfig",
    "ModuleState",
    "init_system",
    "get_system",
    "get_system_status",
]

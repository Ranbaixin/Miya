"""
弥娅统一平台抽象层 (Miya Unified Platform Layer)

提供：
- PlatformStatus: 平台状态枚举
- BasePlatform: 平台基类 (生命周期: connect/disconnect/health/reconnect)
- PlatformRegistry: 动态平台注册表 (无 if-elif 链)
- ReconnectPolicy: 重连策略 (指数退避)
"""

from .status import PlatformStatus, PlatformHealth, PlatformEvent
from .base import BasePlatform
from .registry import PlatformRegistry, register_platform, get_registry
from .reconnect import ReconnectPolicy, ExponentialBackoffPolicy

__all__ = [
    "PlatformStatus",
    "PlatformHealth",
    "PlatformEvent",
    "BasePlatform",
    "PlatformRegistry",
    "register_platform",
    "get_registry",
    "ReconnectPolicy",
    "ExponentialBackoffPolicy",
]

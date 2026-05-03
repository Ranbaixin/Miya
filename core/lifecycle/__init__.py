"""
MIYA 生命周期钩子系统
提供启动、关闭、重载、错误等生命周期事件的钩子机制
"""

from typing import Callable, List, Any, Awaitable, Optional
from enum import Enum
import asyncio
import inspect
import logging

logger = logging.getLogger(__name__)


class HookType(Enum):
    """生命周期钩子类型"""

    STARTUP = "startup"
    SHUTDOWN = "shutdown"
    RELOAD = "reload"
    ERROR = "error"


class LifecycleHook:
    """生命周期钩子"""

    def __init__(
        self, hook_type: HookType, callback: Callable[..., Any], priority: int = 0
    ):
        self.hook_type = hook_type
        self.callback = callback
        self.priority = priority  # 越小越先执行

    async def execute(self, *args, **kwargs) -> Any:
        """执行钩子"""
        if inspect.iscoroutinefunction(self.callback):
            return await self.callback(*args, **kwargs)
        else:
            return self.callback(*args, **kwargs)


class LifecycleManager:
    """生命周期管理器"""

    def __init__(self):
        self._hooks: dict[HookType, List[LifecycleHook]] = {
            hook_type: [] for hook_type in HookType
        }
        self._initialized = False

    def register_hook(
        self,
        hook_type: HookType,
        callback: Callable[..., Any],
        priority: int = 0,
    ):
        """注册生命周期钩子"""
        hook = LifecycleHook(hook_type, callback, priority)
        self._hooks[hook_type].append(hook)
        # 按优先级排序（数字越小优先级越高）
        self._hooks[hook_type].sort(key=lambda h: h.priority)
        logger.debug(f"注册 {hook_type.value} 钩子，优先级: {priority}")

    def unregister_hook(self, hook_type: HookType, callback: Callable[..., Any]):
        """注销生命周期钩子"""
        self._hooks[hook_type] = [
            hook for hook in self._hooks[hook_type] if hook.callback != callback
        ]
        logger.debug(f"注销 {hook_type.value} 钩子")

    async def execute_hooks(self, hook_type: HookType, *args, **kwargs) -> List[Any]:
        """执行指定类型的所有钩子"""
        if hook_type not in self._hooks:
            logger.warning(f"未知的钩子类型: {hook_type}")
            return []

        results = []
        hooks = self._hooks[hook_type]

        if not hooks:
            logger.debug(f"没有注册 {hook_type.value} 钩子")
            return results

        logger.info(f"执行 {len(hooks)} 个 {hook_type.value} 钩子")

        for hook in hooks:
            try:
                logger.info(f"执行钩子: {hook.callback.__name__}")
                result = await hook.execute(*args, **kwargs)
                results.append(result)
            except Exception as e:
                logger.error(
                    f"钩子 {hook.callback.__name__} 执行失败: {e}", exc_info=True
                )
                # 根据钩子类型决定是否继续执行
                if hook_type == HookType.STARTUP:
                    # 启动钩子失败可能影响后续流程
                    raise
                # 其他类型继续执行剩余钩子

        return results

    async def startup(self, *args, **kwargs) -> List[Any]:
        """执行启动钩子"""
        logger.info("🚀 执行启动生命周期钩子")
        return await self.execute_hooks(HookType.STARTUP, *args, **kwargs)

    async def shutdown(self, *args, **kwargs) -> List[Any]:
        """执行关闭钩子"""
        logger.info("🛑 执行关闭生命周期钩子")
        return await self.execute_hooks(HookType.SHUTDOWN, *args, **kwargs)

    async def reload(self, *args, **kwargs) -> List[Any]:
        """执行重载钩子"""
        logger.info("🔄 执行重载生命周期钩子")
        return await self.execute_hooks(HookType.RELOAD, *args, **kwargs)

    async def error(self, *args, **kwargs) -> List[Any]:
        """执行错误钩子"""
        logger.info("❌ 执行错误生命周期钩子")
        return await self.execute_hooks(HookType.ERROR, *args, **kwargs)

    def get_hook_count(self, hook_type: HookType) -> int:
        """获取指定类型的钩子数量"""
        return len(self._hooks.get(hook_type, []))

    def get_all_hooks_info(self) -> dict:
        """获取所有钩子的信息"""
        return {hook_type.value: len(hooks) for hook_type, hooks in self._hooks.items()}


# 全局生命周期管理器实例
_lifecycle_manager: Optional[LifecycleManager] = None


def get_lifecycle_manager() -> LifecycleManager:
    """获取全局生命周期管理器实例"""
    global _lifecycle_manager
    if _lifecycle_manager is None:
        _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager


def init_lifecycle_manager() -> LifecycleManager:
    """初始化全局生命周期管理器"""
    global _lifecycle_manager
    _lifecycle_manager = LifecycleManager()
    return _lifecycle_manager

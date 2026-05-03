"""
Star Filter 系统

提供消息过滤和匹配功能。
"""

import re
import logging
from typing import Dict, List, Optional, Any, Callable, Pattern
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class FilterType(str, Enum):
    """过滤器类型"""

    REGEX = "regex"
    COMMAND = "command"
    COMMAND_GROUP = "command_group"
    PERMISSION = "permission"
    PLATFORM = "platform"
    MESSAGE_TYPE = "message_type"
    CUSTOM = "custom"


@dataclass
class FilterResult:
    """过滤器结果"""

    matched: bool = False
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[str] = None


class BaseFilter:
    """过滤器基类"""

    def __init__(self, filter_type: FilterType, **kwargs):
        self.filter_type = filter_type
        self.config = kwargs

    async def check(self, context: Any) -> FilterResult:
        """检查是否匹配"""
        raise NotImplementedError


class RegexFilter(BaseFilter):
    """正则表达式过滤器"""

    def __init__(self, pattern: str, **kwargs):
        super().__init__(FilterType.REGEX, **kwargs)
        self.pattern = re.compile(pattern)

    async def check(self, context: Any) -> FilterResult:
        """检查消息是否匹配正则表达式"""
        content = getattr(context, "content", "")
        if not content:
            return FilterResult(matched=False)

        match = self.pattern.search(content)
        if match:
            return FilterResult(
                matched=True, data={"match": match.group(0), "groups": match.groups()}
            )
        return FilterResult(matched=False)


class CommandFilter(BaseFilter):
    """命令过滤器"""

    def __init__(self, command: str, aliases: Optional[List[str]] = None, **kwargs):
        super().__init__(FilterType.COMMAND, **kwargs)
        self.command = command
        self.aliases = aliases or []

    async def check(self, context: Any) -> FilterResult:
        """检查消息是否是命令"""
        content = getattr(context, "content", "")
        if not content:
            return FilterResult(matched=False)

        # 提取命令和参数
        parts = content.strip().split()
        if not parts:
            return FilterResult(matched=False)

        cmd = parts[0].lstrip("/")

        # 检查命令或别名
        if cmd == self.command or cmd in self.aliases:
            return FilterResult(matched=True, data={"command": cmd, "args": parts[1:]})
        return FilterResult(matched=False)


class CommandGroupFilter(BaseFilter):
    """命令组过滤器"""

    def __init__(self, group: str, **kwargs):
        super().__init__(FilterType.COMMAND_GROUP, **kwargs)
        self.group = group

    async def check(self, context: Any) -> FilterResult:
        """检查消息是否属于命令组"""
        content = getattr(context, "content", "")
        if not content:
            return FilterResult(matched=False)

        # 提取命令
        parts = content.strip().split()
        if not parts:
            return FilterResult(matched=False)

        cmd = parts[0].lstrip("/")

        # 检查命令组
        if cmd.startswith(self.group):
            return FilterResult(
                matched=True, data={"command": cmd, "group": self.group}
            )
        return FilterResult(matched=False)


class PermissionFilter(BaseFilter):
    """权限过滤器"""

    def __init__(self, permission: str, **kwargs):
        super().__init__(FilterType.PERMISSION, **kwargs)
        self.permission = permission

    async def check(self, context: Any) -> FilterResult:
        """检查用户是否有权限"""
        # 获取用户权限
        user_permissions = getattr(context, "permissions", [])

        if self.permission in user_permissions:
            return FilterResult(matched=True)
        return FilterResult(matched=False, error="权限不足")


class PlatformFilter(BaseFilter):
    """平台过滤器"""

    def __init__(self, platform: str, **kwargs):
        super().__init__(FilterType.PLATFORM, **kwargs)
        self.platform = platform

    async def check(self, context: Any) -> FilterResult:
        """检查消息是否来自指定平台"""
        platform = getattr(context, "platform", "")

        if platform == self.platform:
            return FilterResult(matched=True)
        return FilterResult(matched=False)


class MessageTypeFilter(BaseFilter):
    """消息类型过滤器"""

    def __init__(self, message_type: str, **kwargs):
        super().__init__(FilterType.MESSAGE_TYPE, **kwargs)
        self.message_type = message_type

    async def check(self, context: Any) -> FilterResult:
        """检查消息类型"""
        message_type = getattr(context, "message_type", "")

        if message_type == self.message_type:
            return FilterResult(matched=True)
        return FilterResult(matched=False)


class CustomFilter(BaseFilter):
    """自定义过滤器"""

    def __init__(self, func: Callable, **kwargs):
        super().__init__(FilterType.CUSTOM, **kwargs)
        self.func = func

    async def check(self, context: Any) -> FilterResult:
        """执行自定义过滤器"""
        try:
            result = await self.func(context)
            if isinstance(result, bool):
                return FilterResult(matched=result)
            elif isinstance(result, FilterResult):
                return result
            else:
                return FilterResult(matched=bool(result))
        except Exception as e:
            return FilterResult(matched=False, error=str(e))


class FilterChain:
    """过滤器链"""

    def __init__(self, filters: Optional[List[BaseFilter]] = None):
        self.filters = filters or []

    def add_filter(self, filter_instance: BaseFilter):
        """添加过滤器"""
        self.filters.append(filter_instance)

    async def check_all(self, context: Any) -> FilterResult:
        """检查所有过滤器"""
        for filter_instance in self.filters:
            result = await filter_instance.check(context)
            if not result.matched:
                return result
        return FilterResult(matched=True)

    async def check_any(self, context: Any) -> FilterResult:
        """检查任意过滤器"""
        for filter_instance in self.filters:
            result = await filter_instance.check(context)
            if result.matched:
                return result
        return FilterResult(matched=False)


class FilterManager:
    """过滤器管理器"""

    def __init__(self):
        self._filters: Dict[str, BaseFilter] = {}
        self._chains: Dict[str, FilterChain] = {}

    def register_filter(self, name: str, filter_instance: BaseFilter):
        """注册过滤器"""
        self._filters[name] = filter_instance
        logger.debug(f"Registered filter: {name}")

    def get_filter(self, name: str) -> Optional[BaseFilter]:
        """获取过滤器"""
        return self._filters.get(name)

    def create_chain(self, name: str, filter_names: List[str]) -> FilterChain:
        """创建过滤器链"""
        chain = FilterChain()
        for filter_name in filter_names:
            filter_instance = self.get_filter(filter_name)
            if filter_instance:
                chain.add_filter(filter_instance)

        self._chains[name] = chain
        return chain

    def get_chain(self, name: str) -> Optional[FilterChain]:
        """获取过滤器链"""
        return self._chains.get(name)


# 全局实例
_filter_manager: Optional[FilterManager] = None


def get_filter_manager() -> FilterManager:
    """获取全局过滤器管理器"""
    global _filter_manager
    if _filter_manager is None:
        _filter_manager = FilterManager()
    return _filter_manager


# 便捷函数
def create_regex_filter(pattern: str) -> RegexFilter:
    """创建正则表达式过滤器"""
    return RegexFilter(pattern)


def create_command_filter(
    command: str, aliases: Optional[List[str]] = None
) -> CommandFilter:
    """创建命令过滤器"""
    return CommandFilter(command, aliases)


def create_permission_filter(permission: str) -> PermissionFilter:
    """创建权限过滤器"""
    return PermissionFilter(permission)


def create_platform_filter(platform: str) -> PlatformFilter:
    """创建平台过滤器"""
    return PlatformFilter(platform)


# 导出
__all__ = [
    "FilterType",
    "FilterResult",
    "BaseFilter",
    "RegexFilter",
    "CommandFilter",
    "CommandGroupFilter",
    "PermissionFilter",
    "PlatformFilter",
    "MessageTypeFilter",
    "CustomFilter",
    "FilterChain",
    "FilterManager",
    "get_filter_manager",
    "create_regex_filter",
    "create_command_filter",
    "create_permission_filter",
    "create_platform_filter",
]

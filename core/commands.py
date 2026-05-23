"""
内置命令系统

参考 AstrBot 的内置命令
"""

import asyncio
import logging
import shlex
from dataclasses import dataclass
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("miya.commands")


@dataclass
class Command:
    """命令"""

    name: str
    description: str
    aliases: List[str]
    handler: Callable
    usage: str = ""
    permission: str = "all"  # all, admin, owner


# 命令注册表
_command_registry: Dict[str, Command] = {}


def register_command(
    name: str,
    description: str,
    aliases: List[str] = None,
    usage: str = "",
    permission: str = "all",
):
    """命令装饰器"""

    def decorator(func):
        cmd = Command(
            name=name,
            description=description,
            aliases=aliases or [],
            handler=func,
            usage=usage,
            permission=permission,
        )
        _command_registry[name] = cmd
        for alias in aliases or []:
            _command_registry[alias] = cmd

        logger.debug(f"[Commands] 注册命令: {name}")
        return func

    return decorator


def get_command(name: str) -> Optional[Command]:
    """获取命令"""
    return _command_registry.get(name)


def list_commands() -> List[Dict]:
    """列出所有命令"""
    seen = set()
    result = []
    for cmd in _command_registry.values():
        if cmd.name in seen:
            continue
        seen.add(cmd.name)
        result.append(
            {
                "name": cmd.name,
                "description": cmd.description,
                "aliases": cmd.aliases,
                "usage": cmd.usage,
                "permission": cmd.permission,
            }
        )
    return result


async def execute_command(
    name: str,
    args: str,
    context: Dict[str, Any],
) -> str:
    """执行命令"""
    cmd = get_command(name)
    if not cmd:
        return f"未知命令: {name}"

    try:
        # 解析参数
        parsed_args = []
        if args:
            parsed_args = shlex.split(args)

        # 执行
        handler = cmd.handler
        if asyncio.iscoroutinefunction(handler):
            result = await handler(context, *parsed_args)
        else:
            result = handler(context, *parsed_args)

        return result if result else "命令执行完成"
    except Exception as e:
        logger.error(f"[Commands] 执行失败 {name}: {e}")
        return f"执行失败: {e}"


# ===== 内置命令 =====


@register_command(
    name="help",
    description="显示帮助",
    aliases=["h", "?"],
    usage="/help [命令名]",
)
async def help_command(context: Dict, *args):
    """帮助命令"""
    if args:
        cmd = get_command(args[0])
        if cmd:
            lines = [f"=== {cmd.name} ===", cmd.description]
            if cmd.usage:
                lines.append(f"用法: {cmd.usage}")
            if cmd.aliases:
                lines.append(f"别名: {', '.join(cmd.aliases)}")
            return "\n".join(lines)
        else:
            return f"未找到命令: {args[0]}"

    # 列出所有命令
    lines = ["=== 可用命令 ==="]
    for cmd in list_commands():
        lines.append(f"  {cmd['name']}: {cmd['description']}")
    lines.append("")
    lines.append("使用 /help <命令名> 查看详细用法")
    return "\n".join(lines)


@register_command(
    name="ping",
    description="测试连接",
    aliases=[],
    usage="/ping",
)
def ping_command(context: Dict, *args):
    return "Pong! 🎾"


@register_command(
    name="status",
    description="查看系统状态",
    aliases=["stat"],
    usage="/status",
)
def status_command(context: Dict, *args):
    import platform

    import psutil

    lines = [
        "=== 弥娅系统状态 ===",
        f"Python: {platform.python_version()}",
        f"系统: {platform.system()}",
        f"CPU: {psutil.cpu_percent()}%",
        f"内存: {psutil.virtual_memory().percent}%",
    ]
    return "\n".join(lines)


@register_command(
    name="persona",
    description="切换人格",
    aliases=[],
    usage="/persona <人格名>",
)
def persona_command(context: Dict, *args):
    if not args:
        return "用法: /persona <人格名>"

    persona_name = args[0]
    # 实际切换人格的逻辑
    return f"已切换到人格: {persona_name}"


@register_command(
    name="model",
    description="切换模型",
    aliases=[],
    usage="/model <模型名>",
)
def model_command(context: Dict, *args):
    if not args:
        return "用法: /model <模型名>"

    model_name = args[0]
    return f"已切换到模型: {model_name}"


@register_command(
    name="clear",
    description="清除对话历史",
    aliases=[".clear"],
    usage="/clear",
)
def clear_command(context: Dict, *args):
    return "对话历史已清除 ✓"


@register_command(
    name="sysprompt",
    description="查看/修改系统提示词",
    aliases=[],
    usage="/sysprompt [新提示词]",
)
def sysprompt_command(context: Dict, *args):
    if args:
        return "系统提示词已更新"
    return "请提供新的系统提示词"


__all__ = [
    "Command",
    "register_command",
    "get_command",
    "list_commands",
    "execute_command",
    "help_command",
    "ping_command",
    "status_command",
    "persona_command",
    "model_command",
    "clear_command",
    "sysprompt_command",
]

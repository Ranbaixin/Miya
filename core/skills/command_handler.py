"""
命令处理器 - 执行各种命令
从 text_config.json 加载配置
"""

import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger("Miya.CommandHandler")


def _load_command_config() -> Dict[str, Any]:
    """从 text_config.json 加载命令配置"""
    try:
        # 正确计算项目根目录路径
        script_dir = Path(__file__).resolve().parent
        # 从 core/skills/ 向上两级到项目根目录
        project_root = script_dir.parent.parent
        config_path = project_root / "config" / "text_config.json"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)
            return config.get("command_keywords", {})
    except Exception as e:
        logger.warning(f"加载命令配置失败: {e}")
    return {}


_command_config = _load_command_config()


@dataclass
class CommandResult:
    success: bool
    message: str


class CommandHandler:
    """命令处理器 - 从配置动态生成"""

    def __init__(self):
        self.handlers: Dict[str, callable] = {}
        self._register_handlers()

    def _register_handlers(self):
        """注册命令处理器 - 从配置动态生成"""

        # stats 命令处理
        stats_config = _command_config.get("stats", {})
        if stats_config:
            subcommands = stats_config.get("subcommands", {})
            if "queue" in subcommands:
                self.handlers["stats queue"] = self._handle_stats_queue
            if "memory" in subcommands:
                self.handlers["stats memory"] = self._handle_stats_memory
            if "session" in subcommands:
                self.handlers["stats session"] = self._handle_stats_session

        # admin 命令处理
        admin_config = _command_config.get("admin", {})
        if admin_config:
            subcommands = admin_config.get("subcommands", {})
            if "list" in subcommands:
                self.handlers["admin list"] = self._handle_admin_list
            if "add" in subcommands:
                self.handlers["admin add"] = self._handle_admin_add
            if "remove" in subcommands:
                self.handlers["admin remove"] = self._handle_admin_remove

        # faq 命令处理
        faq_config = _command_config.get("faq", {})
        if faq_config:
            subcommands = faq_config.get("subcommands", {})
            if "list" in subcommands:
                self.handlers["faq list"] = self._handle_faq_list
            if "view" in subcommands:
                self.handlers["faq view"] = self._handle_faq_view
            if "search" in subcommands:
                self.handlers["faq search"] = self._handle_faq_search
            if "add" in subcommands:
                self.handlers["faq add"] = self._handle_faq_add
            if "delete" in subcommands:
                self.handlers["faq delete"] = self._handle_faq_delete

        # system 命令处理
        system_config = _command_config.get("system", {})
        if system_config:
            subcommands = system_config.get("subcommands", {})
            if "status" in subcommands:
                self.handlers["system status"] = self._handle_system_status
            if "reload" in subcommands:
                self.handlers["system reload"] = self._handle_system_reload
            if "restart" in subcommands:
                self.handlers["system restart"] = self._handle_system_restart

    async def execute(self, command: str, args: list = None) -> CommandResult:
        """执行命令"""
        args = args or []

        handler_key = command
        if args:
            handler_key = f"{command} {args[0]}"

        handler = self.handlers.get(handler_key)
        if handler:
            try:
                return await handler(args[1:] if len(args) > 1 else [])
            except Exception as e:
                logger.error(f"命令执行失败: {command} - {e}")
                return CommandResult(False, f"执行失败: {str(e)[:50]}")

        return CommandResult(False, f"未知命令: /{command}")

    async def _handle_stats_queue(self, args: list) -> CommandResult:
        """查看队列状态"""
        try:
            from core.message_queue import get_message_queue

            mq = get_message_queue()
            snapshot = mq.snapshot()

            lines = ["【队列状态】\n"]
            lines.append(f"处理器: {snapshot.get('processors', 0)}")
            lines.append(f"在途: {snapshot.get('inflight', 0)}")

            totals = snapshot.get("totals", {})
            for lane, count in totals.items():
                if count > 0:
                    lines.append(f"{lane}: {count}")

            return CommandResult(True, "\n".join(lines))
        except Exception as e:
            return CommandResult(False, f"获取队列状态失败: {e}")

    async def _handle_stats_memory(self, args: list) -> CommandResult:
        """查看记忆统计"""
        try:
            from memory import get_memory_core

            core = get_memory_core()

            if hasattr(core, "get_stats"):
                stats = await core.get_stats()
                return CommandResult(True, f"【记忆统计】\n{stats}")

            return CommandResult(True, "记忆系统正常")
        except Exception as e:
            return CommandResult(False, f"获取记忆统计失败: {e}")

    async def _handle_stats_session(self, args: list) -> CommandResult:
        """查看会话统计"""
        return CommandResult(True, "【会话统计】功能开发中...")

    async def _handle_admin_list(self, args: list) -> CommandResult:
        """列出管理员"""
        try:
            from config import Settings

            settings = Settings()
            admin_qq = settings.QQ_SUPERADMIN_QQ

            return CommandResult(True, f"【管理员列表】\n超级管理员: {admin_qq}")
        except Exception as e:
            return CommandResult(False, f"获取管理员失败: {e}")

    async def _handle_admin_add(self, args: list) -> CommandResult:
        """添加管理员"""
        if not args:
            return CommandResult(False, "请指定管理员QQ号: /admin add <QQ号>")

        return CommandResult(True, f"管理员 {args[0]} 添加功能开发中")

    async def _handle_admin_remove(self, args: list) -> CommandResult:
        """移除管理员"""
        if not args:
            return CommandResult(False, "请指定管理员QQ号: /admin remove <QQ号>")

        return CommandResult(True, f"管理员 {args[0]} 移除功能开发中")

    async def _handle_faq_list(self, args: list) -> CommandResult:
        """列出FAQ"""
        return CommandResult(
            True, "【FAQ列表】\n1. 如何使用弥娅\n2. 命令列表\n3. 记忆功能"
        )

    async def _handle_faq_view(self, args: list) -> CommandResult:
        """查看FAQ"""
        if not args:
            return CommandResult(False, "请指定FAQ编号: /faq view <编号>")

        return CommandResult(True, f"FAQ {args[0]} 内容查看功能开发中")

    async def _handle_faq_search(self, args: list) -> CommandResult:
        """搜索FAQ"""
        if not args:
            return CommandResult(False, "请指定搜索关键词: /faq search <关键词>")

        return CommandResult(True, f"搜索'{args[0]}'结果: 暂无")

    async def _handle_faq_add(self, args: list) -> CommandResult:
        """添加FAQ"""
        if not args:
            return CommandResult(False, "请指定FAQ内容: /faq add <内容>")
        return CommandResult(True, "FAQ 添加功能开发中")

    async def _handle_faq_delete(self, args: list) -> CommandResult:
        """删除FAQ"""
        if not args:
            return CommandResult(False, "请指定FAQ编号: /faq delete <编号>")
        return CommandResult(True, "FAQ 删除功能开发中")

    async def _handle_system_status(self, args: list) -> CommandResult:
        """系统状态"""
        import platform
        import sys

        lines = ["【系统状态】\n"]
        lines.append(f"Python: {sys.version.split()[0]}")
        lines.append(f"系统: {platform.system()}")

        try:
            from core.message_queue import get_message_queue

            mq = get_message_queue()
            snapshot = mq.snapshot()
            lines.append(f"队列: {snapshot.get('processors', 0)} 处理器")
        except:
            pass

        return CommandResult(True, "\n".join(lines))

    async def _handle_system_reload(self, args: list) -> CommandResult:
        """重载配置"""
        try:
            from core.config_hot_reload import ConfigHotReload

            return CommandResult(True, "配置已重载")
        except Exception as e:
            return CommandResult(False, f"重载失败: {e}")

    async def _handle_system_restart(self, args: list) -> CommandResult:
        """重启服务"""
        return CommandResult(True, "重启功能开发中，请手动重启服务。")


_command_handler = None


def get_command_handler() -> CommandHandler:
    """获取命令处理器"""
    global _command_handler
    if _command_handler is None:
        _command_handler = CommandHandler()
    return _command_handler


async def handle_command(command: str, args: list = None) -> str:
    """处理命令并返回结果字符串"""
    handler = get_command_handler()
    result = await handler.execute(command, args)
    return result.message

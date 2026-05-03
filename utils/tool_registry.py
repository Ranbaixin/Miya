"""
统一工具注册表
管理弥娅系统中所有可用工具的列表
避免在多个文件中重复定义工具列表
"""

import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ToolRegistry:
    """工具注册表 - 统一管理工具列表"""

    # 核心工具列表
    CORE_TOOLS = [
        "web_search",
        "get_weather",
        "get_current_time",
        "send_like",
        "search_memory",
        "get_group_info",
        "react_emoji",
    ]

    # QQ平台扩展工具
    QQ_EXTENDED_TOOLS = [
        # 基础信息查询
        "get_user_info",
        "get_group_list",
        "get_group_member_list",
        "get_group_member_info",
        # 群聊管理
        "set_group_kick",
        "set_group_ban",
        "set_group_whole_ban",
        "set_group_card",
        "set_group_name",
        # 消息操作
        "delete_msg",
        "set_msg_emoji_like",
        # 资源获取
        "get_image",
        "get_record",
        # 搜索工具
        "baiduhot",
        "weibohot",
        "douyinhot",
        "grok_search",
        "tavily_search",
        "web_research",
        "crawl_webpage",
        # 群文件工具
        "group_file_downloader",
        "local_file_finder",
        "qq_file_reader",
        # 其他工具
        "qq_like",
        "send_poke",
        "horoscope",
        "wenchang_dijun",
        "terminal_command",
        "multi_terminal",
        "python_interpreter",
    ]

    # Desktop平台工具
    DESKTOP_TOOLS = [
        # 系统控制
        "open_app",
        "close_app",
        "get_running_apps",
        "get_system_info",
        # 文件操作
        "read_file",
        "write_file",
        "list_directory",
        "search_files",
        # 终端命令
        "terminal_command",
        "multi_terminal",
        # 屏幕操作
        "screenshot",
        "get_screen_text",
        # 其他
        "web_search",
        "get_weather",
        "get_current_time",
    ]

    # Web平台工具
    WEB_TOOLS = [
        "web_search",
        "get_weather",
        "get_current_time",
        "search_memory",
    ]

    # 直接返回工具列表（不需要AI润色）
    DIRECT_RETURN_TOOLS = [
        "horoscope",
        "wenchang_dijun",
        "terminal_command",
        "multi_terminal",
        "douyinhot",
        "weibohot",
        "baiduhot",
        "grok_search",
        "web_search",
        "crawl_webpage",
        "qq_level_query",
        "tavily_search",
        "group_file_downloader",
        "local_file_finder",
        "qq_file_reader",
        "python_interpreter",
    ]

    # 并发执行工具列表
    CONCURRENT_TOOLS = [
        "get_recent_messages",
        "get_user_info",
        "get_current_time",
        "search_knowledge",
        "search_memory",
        "get_profile",
        "bilibili_video",
        "web_search",
        "web_research",
    ]

    @classmethod
    def get_tools_for_platform(cls, platform: str) -> List[str]:
        """
        获取指定平台的工具列表

        Args:
            platform: 平台名称 (qq, desktop, web, terminal)

        Returns:
            工具名称列表
        """
        if platform == "qq":
            return cls.CORE_TOOLS + cls.QQ_EXTENDED_TOOLS
        elif platform == "desktop":
            return cls.DESKTOP_TOOLS
        elif platform == "web":
            return cls.WEB_TOOLS
        elif platform == "terminal":
            return cls.CORE_TOOLS + ["terminal_command", "multi_terminal"]
        else:
            return cls.CORE_TOOLS

    @classmethod
    def is_direct_return_tool(cls, tool_name: str) -> bool:
        """
        检查工具是否应该直接返回结果

        Args:
            tool_name: 工具名称

        Returns:
            是否直接返回
        """
        return tool_name in cls.DIRECT_RETURN_TOOLS

    @classmethod
    def is_concurrent_tool(cls, tool_name: str) -> bool:
        """
        检查工具是否可以并发执行

        Args:
            tool_name: 工具名称

        Returns:
            是否可以并发执行
        """
        return tool_name in cls.CONCURRENT_TOOLS

    @classmethod
    def get_all_tools(cls) -> List[str]:
        """获取所有工具列表"""
        all_tools = set()
        all_tools.update(cls.CORE_TOOLS)
        all_tools.update(cls.QQ_EXTENDED_TOOLS)
        all_tools.update(cls.DESKTOP_TOOLS)
        all_tools.update(cls.WEB_TOOLS)
        return list(all_tools)


# 便捷函数
def get_tools_for_platform(platform: str) -> List[str]:
    """获取指定平台的工具列表"""
    return ToolRegistry.get_tools_for_platform(platform)


def is_direct_return_tool(tool_name: str) -> bool:
    """检查工具是否应该直接返回结果"""
    return ToolRegistry.is_direct_return_tool(tool_name)


def is_concurrent_tool(tool_name: str) -> bool:
    """检查工具是否可以并发执行"""
    return ToolRegistry.is_concurrent_tool(tool_name)

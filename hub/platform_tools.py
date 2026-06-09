"""平台工具管理器

负责根据不同平台选择合适的工具集
"""

import logging
from typing import Dict, List

logger = logging.getLogger(__name__)


class PlatformToolsManager:
    """平台工具管理器

    职责：
    - 根据平台类型选择合适的工具
    - 避免传递过多工具导致API超限
    - 管理平台特定的工具配置
    """

    # 核心工具 - 所有平台都需要
    CORE_TOOLS = [
        "get_current_time",
        "web_search",
        "tavily_search",
        "douyinhot",
        "weibohot",
        "baiduhot",
        "grok_search",
        # MusicNet — MIDI 作曲/编曲
        "midi_write",
        "midi_diff",
        "midi_batch_edit",
        "midi_query",
        "midi_inspect",
        "midi_play",
        "midi_render",
        # MCPNet — 全平台电脑操控
        "mcp_openclaw_send_message",
        "mcp_openclaw_start_gateway",
        "mcp_openclaw_stop_gateway",
        "mcp_openclaw_get_status",
        "mcp_openclaw_get_history",
        "mcp_code_executor_execute",
        "mcp_web_search_search",
        "mcp_web_search_fetch",
        "mcp_screen_vision_look_screen",
        "mcp_screen_vision_screenshot",
        "mcp_filesystem_read_file",
        "mcp_filesystem_write_file",
        "mcp_filesystem_list_files",
        "mcp_filesystem_search_files",
    ]

    # 平台特定工具映射
    PLATFORM_TOOL_MAP = {
        "qq": [
            "send_message",
            "get_user_info",
            "qq_like",
            "send_poke",
            "react_emoji",
            "get_member_list",
            "get_member_info",
            "find_member",
            "memory_add",
            "memory_list",
            # 搜索工具
            "web_search",
            "tavily_search",
            "douyinhot",
            "weibohot",
            "baiduhot",
            "grok_search",
            "crawl_webpage",
            # 信息查询
            "qq_level_query",
            "weather_query",
            # 跨端工具（从QQ控制终端）
            "execute_on_desktop",
            "send_to_desktop",
            "send_to_terminal",
            "terminal_command",
            "terminal_exec",
            "multi_terminal",
            # Terminal Ultra 工具
            "file_read",
            "file_write",
            "file_edit",
            "file_delete",
            "directory_tree",
            "code_execute",
            "project_analyze",
            # Git 工具
            "git_status",
            "git_diff",
            "git_log",
            "git_branch",
            "git_commit",
            "git_push",
            "git_pull",
            "git_checkout",
            "git_stash",
            # 搜索工具
            "file_grep",
            "file_glob",
            # 智能工具
            "project_context",
            "task_plan",
            "suggestions",
            # Skills 工具
            "list_skills",
            # 【格式塔】Agent 工具
            "group_file_downloader",
            "local_file_finder",
            "qq_file_reader",
            "qq_image_analyzer",
            "python_interpreter",
            "horoscope",
            "qq_like",
            "send_poke",
            "react_emoji",
            "wenchang_dijun",
            "baiduhot",
            "douyinhot",
            "qq_level_query",
            "weibohot",
            "crawl_webpage",
            "grok_search",
            "web_search",
        ],
        # 飞书平台工具
        "lark": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # 钉钉平台工具
        "dingtalk": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # 企业微信工具
        "wecom": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # LINE平台工具
        "line": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # Discord平台工具
        "discord": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # Telegram平台工具
        "telegram": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # Slack平台工具
        "slack": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # KOOK平台工具
        "kook": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # 网页聊天工具 - 最完整
        "webchat": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "tavily_search",
            "douyinhot",
            "weibohot",
            "baiduhot",
            "grok_search",
            "crawl_webpage",
            "weather_query",
            "python_interpreter",
            "horoscope",
            "wenchang_dijun",
            "file_read",
            "file_write",
            "file_edit",
            "file_delete",
            "directory_tree",
            "code_execute",
            "project_analyze",
            # Git 工具
            "git_status",
            "git_diff",
            "git_log",
            "git_branch",
            "git_commit",
            "git_push",
            "git_pull",
            "git_checkout",
            "git_stash",
            # 搜索工具
            "file_grep",
            "file_glob",
            # 智能工具
            "project_context",
            "task_plan",
            "suggestions",
            "list_skills",
            "group_file_downloader",
            "local_file_finder",
            "qq_file_reader",
            "qq_image_analyzer",
        ],
        # Satori协议工具
        "satori": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # 微信开放平台
        "weixin_oc": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        # 微信公众号
        "weixin_official_account": [
            "send_message",
            "get_user_info",
            "memory_add",
            "memory_list",
            "web_search",
            "grok_search",
            "crawl_webpage",
            "baiduhot",
            "douyinhot",
            "weibohot",
            "weather_query",
            "python_interpreter",
        ],
        "terminal": [
            # 核心终端工具
            "terminal_command",
            "terminal_exec",
            "multi_terminal",
            "system_info",
            "environment_detector",
            # 跨端工具
            "send_to_qq",
            "send_to_desktop",
            "send_to_terminal",
            "execute_on_desktop",
            "sync_state",
            "qq_like",
            # 文件操作
            "file_read",
            "file_write",
            "file_edit",
            "file_delete",
            "directory_tree",
            "code_execute",
            "project_analyze",
            # Git 工具
            "git_status",
            "git_diff",
            "git_log",
            "git_branch",
            "git_commit",
            "git_push",
            "git_pull",
            "git_checkout",
            "git_stash",
            # 搜索工具
            "file_grep",
            "file_glob",
            # 代码理解
            "code_explain",
            "code_search_symbol",
            # 智能工具
            "project_context",
            "task_plan",
            "suggestions",
            # Agent 工具
            "code_explorer_agent",
            "code_reviewer_agent",
            "code_architect_agent",
            "terminal_agent",
            # Skills 工具
            "list_skills",
        ],
        # Desktop 平台使用与 QQ 相同的工具集（桌面端=超级管理员）
        # 复制 QQ 的工具列表，确保完全一致
        "desktop": [
            # 消息发送
            "send_message",
            "get_user_info",
            "qq_like",
            "send_poke",
            "react_emoji",
            "get_member_list",
            "get_member_info",
            "find_member",
            "memory_add",
            "memory_list",
            # 搜索工具
            "web_search",
            "tavily_search",
            "douyinhot",
            "weibohot",
            "baiduhot",
            "grok_search",
            "crawl_webpage",
            # 信息查询
            "qq_level_query",
            "weather_query",
            # 跨端工具
            "execute_on_desktop",
            "send_to_desktop",
            "send_to_terminal",
            "terminal_command",
            "terminal_exec",
            "multi_terminal",
            # 文件操作
            "file_read",
            "file_write",
            "file_edit",
            "file_delete",
            "directory_tree",
            "code_execute",
            "project_analyze",
            # Git 工具
            "git_status",
            "git_diff",
            "git_log",
            "git_branch",
            "git_commit",
            "git_push",
            "git_pull",
            "git_checkout",
            "git_stash",
            # 搜索工具
            "file_grep",
            "file_glob",
            # 智能工具
            "project_context",
            "task_plan",
            "suggestions",
            # Skills 工具
            "list_skills",
            # Agent 工具
            "group_file_downloader",
            "local_file_finder",
            "qq_file_reader",
            "qq_image_analyzer",
            "python_interpreter",
            "ai_sing",
            "horoscope",
            "wenchang_dijun",
            "code_explorer_agent",
            "code_reviewer_agent",
            "code_architect_agent",
            "terminal_agent",
        ],
        "web": [
            "send_to_qq",
            "send_to_desktop",
            "send_to_terminal",
            "terminal_command",
            "terminal_exec",
            "file_read",
            "file_write",
            "file_edit",
            "file_delete",
            "directory_tree",
            "code_execute",
            "project_analyze",
            # Git 工具
            "git_status",
            "git_diff",
            "git_log",
            "git_branch",
            "git_commit",
            "git_push",
            "git_pull",
            "git_checkout",
            "git_stash",
            # 搜索工具
            "file_grep",
            "file_glob",
            # 智能工具
            "project_context",
            "task_plan",
            "suggestions",
            # Agent 工具
            "code_explorer_agent",
            "code_reviewer_agent",
            "code_architect_agent",
            "terminal_agent",
            # Skills 工具
            "list_skills",
        ],
    }

    # QQ平台扩展工具
    QQ_EXTENDED_TOOLS = [
        "send_message",
        "get_user_info",
        "qq_like",
        "send_poke",
        "react_emoji",
        "get_member_list",
        "get_member_info",
        "find_member",
        "memory_add",
        "memory_list",
        "knowledge_text_search",
        "knowledge_semantic_search",
        "start_trpg",
        "roll_dice",
        "search_tavern_characters",
        # 跨端工具
        "execute_on_desktop",
        "send_to_desktop",
        "send_to_terminal",
        "terminal_command",
        # 搜索工具（新增）
        "web_search",
        "tavily_search",
        "douyinhot",
        "weibohot",
        "baiduhot",
        "grok_search",
        "crawl_webpage",
        # 信息查询
        "qq_level_query",
        "weather_query",
        # 【格式塔】Agent 工具
        "group_file_downloader",
        "local_file_finder",
        "qq_file_reader",
        "qq_image_analyzer",
        "python_interpreter",
        "horoscope",
        "wenchang_dijun",
        # 定时任务工具（交由 LLM 自行判断调用时机）
        "create_schedule_task",
        "list_schedule_tasks",
        "delete_schedule_task",
        "update_schedule_task",
        "get_schedule_stats",
    ]

    def __init__(self, tool_subnet):
        """
        初始化平台工具管理器

        Args:
            tool_subnet: ToolNet子网实例
        """
        self.tool_subnet = tool_subnet

    def get_platform_tools(self, platform: str) -> List[str]:
        """
        获取平台可用工具列表

        Args:
            platform: 平台类型

        Returns:
            工具名称列表
        """
        from hub.platform_adapters import get_adapter

        try:
            adapter = get_adapter(platform)
            return adapter._get_available_tools()
        except Exception as e:
            logger.error(f"[平台工具] 获取平台工具失败: {e}")
            return []

    def get_platform_specific_tools(self, platform: str) -> List[Dict]:
        """
        获取当前平台的工具 schema（优化版）

        只返回当前平台最常用的核心工具，避免过多工具导致API错误

        Args:
            platform: 平台类型 ('qq', 'terminal', 'desktop', 'web')

        Returns:
            工具 schema 列表
        """
        # 获取当前平台的工具
        selected_tools = self.PLATFORM_TOOL_MAP.get(platform, self.CORE_TOOLS)

        # 如果是 QQ 平台（含 aiocqhttp OneBot），添加更多常用工具
        if platform in ("qq", "aiocqhttp"):
            selected_tools = self.CORE_TOOLS + self.QQ_EXTENDED_TOOLS
            # QQ 聊天场景不需要屏幕视觉工具，移除避免 AI 混淆
            selected_tools = [
                t for t in selected_tools if t not in ("mcp_screen_vision_look_screen", "mcp_screen_vision_screenshot")
            ]

        # 从 tool_subnet 获取工具 schema
        try:
            all_schemas = self.tool_subnet.get_tools_schema()
            # 只返回在 selected_tools 列表中的工具
            platform_schemas = [s for s in all_schemas if s.get("function", {}).get("name") in selected_tools]

            logger.info(f"[平台工具] 平台 {platform} 使用 {len(platform_schemas)} 个工具")
            return platform_schemas

        except Exception as e:
            logger.warning(f"[平台工具] 获取平台工具失败: {e}，使用全部工具")
            return self.tool_subnet.get_tools_schema()

    def is_creator(self, user_id: int, onebot_client) -> bool:
        """
        判断用户是否为造物主（超级管理员）

        Args:
            user_id: 用户ID
            onebot_client: OneBot客户端

        Returns:
            是否为造物主
        """
        if onebot_client and hasattr(onebot_client, "superadmin"):
            return user_id == onebot_client.superadmin
        return False

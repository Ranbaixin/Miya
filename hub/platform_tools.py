"""平台工具管理器

负责根据不同平台选择合适的工具集
"""

import logging
import re
from typing import Dict, List

logger = logging.getLogger(__name__)


# ==================== 工具 schema 瘦身（Step 2） ====================

# 语义关键句保留词：触发时机 / 禁止 / 风险 / 区分 / 参数语义
_KEEP_SENTENCE = (
    "当",
    "如果",
    "仅当",
    "调用时机",
    "用于",
    "必须",
    "不要",
    "请勿",
    "禁止",
    "只能",
    "区别于",
    "不要与",
    "重要",
    "危险",
    "谨慎",
    "权限",
    "敏感",
    "注意",
)
# 示例/场景段标记：其后内容一律裁剪
_DROP_SECTIONS = ("适用场景", "使用场景", "示例", "例子", "比如:", "例如:")
_MAX_DESC_CHARS = 120
_MAX_PROP_CHARS = 80


def _split_keep_sentences(text: str, keep_keywords: tuple) -> list:
    """按句子拆分，首句必留，其余仅保留含关键语义的句子"""
    parts = re.split(r"[。！？\n]+", text)
    kept = []
    for p in parts:
        p = p.strip(" \t-·、，,;；")
        if not p:
            continue
        if kept and not any(k in p for k in keep_keywords):
            continue
        kept.append(p)
    return kept


def trim_tool_description(desc: str) -> str:
    """裁剪工具描述：保留核心语义 + 触发时机/禁止/风险/区分，去掉示例与冗长列举。

    保持约束（用户批准）：触发时机、禁止项、参数语义、工具区分、风险限制不可丢。
    """
    if not desc:
        return ""
    text = desc.strip()
    # 1) 截断到示例段之前
    for marker in _DROP_SECTIONS:
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]
    # 2) 句子级保留
    kept = _split_keep_sentences(text, _KEEP_SENTENCE)
    result = "。".join(kept)
    # 3) 超长时按句子边界截断（不切半句话）
    if len(result) > _MAX_DESC_CHARS:
        acc = ""
        for s in kept:
            if acc and len(acc) + len(s) + 1 > _MAX_DESC_CHARS:
                break
            acc = acc + "。" + s if acc else s
        result = acc
    return result + "。" if result else ""


def trim_property_description(desc: str) -> str:
    """裁剪参数描述：保留主规则与补充规则，去掉示例与冗长解释。"""
    if not desc:
        return ""
    text = desc.strip()
    # 1) 去掉示例
    for marker in ("例如", "比如", "示例"):
        idx = text.find(marker)
        if idx > 0:
            text = text[:idx]
    # 2) 保留前两句（主规则 + 补充规则）
    idx = text.find("。")
    if idx >= 0:
        second = text.find("。", idx + 1)
        if second >= 0:
            text = text[: second + 1]
    text = text.strip(" \t，,；;")
    return text[:_MAX_PROP_CHARS]


def trim_tool_schemas(schemas: List[Dict]) -> List[Dict]:
    """对工具 schema 列表做描述瘦身（不改变结构，只裁剪文本字段）。

    - 工具 description：trim_tool_description
    - 参数 property description：trim_property_description
    - 枚举/默认值/必填等结构字段保留（本身紧凑且承载语义）
    """
    out = []
    for schema in schemas:
        func = schema.get("function") or {}
        trimmed = dict(schema)
        tfunc = dict(func)
        tool_name = func.get("name", "")
        # 策展描述优先；未收录的工具走启发式裁剪
        tfunc["description"] = QQ_DESC_OVERRIDES.get(tool_name, trim_tool_description(func.get("description", "")))
        params = func.get("parameters")
        if isinstance(params, dict):
            tparams = dict(params)
            props = params.get("properties")
            if isinstance(props, dict):
                prop_overrides = QQ_PROP_OVERRIDES.get(tool_name, {})
                tprops = {}
                for pname, pdef in props.items():
                    if isinstance(pdef, dict) and pdef.get("description"):
                        pd = dict(pdef)
                        if pname in prop_overrides:
                            pd["description"] = prop_overrides[pname]
                        else:
                            pd["description"] = trim_property_description(pd["description"])
                        tprops[pname] = pd
                    else:
                        tprops[pname] = pdef
                tparams["properties"] = tprops
            tfunc["parameters"] = tparams
        trimmed["function"] = tfunc
        out.append(trimmed)
    return out


# ==================== 工具包路由（Step 3） ====================

# 7 个工具包：qq_core 恒在，扩展包按消息场景 0-2 个
QQ_CORE_PACK = [
    "send_message",  # 发消息（必带）
    "get_user_info",  # 查用户信息
    "memory_add",  # 主动记忆
    "memory_list",  # 记忆查询
    "get_current_time",  # 时间
    "react_emoji",  # 表情回应
    "send_poke",  # 拍一拍
    "qq_like",  # 点赞
]

TOOL_PACKS = {
    "qq_core": QQ_CORE_PACK,
    "search": [
        "web_search",
        "tavily_search",
        "crawl_webpage",
        "baiduhot",
        "weibohot",
        "douyinhot",
        "grok_search",
    ],
    "qq_social": [
        "get_member_list",
        "get_member_info",
        "find_member",
        "qq_level_query",
        "weather_query",
    ],
    "media": [
        "qq_file_reader",
        "qq_image_analyzer",
        "group_file_downloader",
        "local_file_finder",
    ],
    "desktop": [
        "execute_on_desktop",
        "send_to_desktop",
        "send_to_terminal",
        "terminal_command",
    ],
    "game": [
        "start_trpg",
        "roll_dice",
        "search_tavern_characters",
    ],
    "entertainment": [
        "horoscope",
        "wenchang_dijun",
        "python_interpreter",
    ],
}

# 扩展包关键词（消息命中即加入；同一关键词可命中多包，取命中数前 2）
PACK_KEYWORDS = {
    "search": (
        "搜索",
        "搜一下",
        "新闻",
        "热搜",
        "资讯",
        "实时",
        "最新消息",
        "网页",
        "链接",
        "网址",
        "资料",
        "查找资料",
        "帮我查",
    ),
    "qq_social": (
        "群成员",
        "成员列表",
        "群友",
        "成员信息",
        "等级",
        "天气",
        "气温",
    ),
    "media": (
        "图片",
        "照片",
        "看图",
        "分析图片",
        "文件",
        "读文件",
        "群文件",
        "下载群文件",
        "找文件",
        "pdf",
        "文档",
    ),
    "desktop": (
        "终端",
        "桌面",
        "电脑",
        "执行",
        "命令",
        "控制",
        "程序",
    ),
    "game": (
        "骰子",
        "跑团",
        "trpg",
        "掷骰",
        "roll",
        "角色卡",
        "酒馆",
        "tavern",
    ),
    "entertainment": (
        "星座",
        "运势",
        "抽签",
        "抽个签",
        "求签",
        "求个签",
        "占卜",
        "灵签",
        "文昌",
        "算命",
        "代码",
        "计算",
        "python",
        "数据分析",
    ),
}

# ==================== QQ 工具描述策展（Step 2/3） ====================
# 人工压缩版描述：保留触发时机/禁止项/参数语义/工具区分/风险限制，
# 去掉示例列举与冗长解释。未收录的工具走 trim_tool_description 启发式。
QQ_DESC_OVERRIDES = {
    "get_current_time": "获取当前系统时间。当用户问'现在几点/几点了/什么时间/今天日期'时必须调用，不要用文字回复。",
    "get_user_info": "获取QQ用户详细信息。当用户明确请求时调用。",
    "send_message": "发送消息到指定群或私聊。当用户需要发送消息时调用。",
    "memory_add": "添加手动长期记忆。当用户明确要求记住/添加记忆/保存重要内容时必须调用，不要用文字回复。",
    "memory_list": "列出记忆。当用户问过去的事/记忆/昨天前天上周时调用，可按时间范围查询。用自己的话回答，不要直接复制工具输出。",
    "qq_like": "给指定QQ号点赞。当用户说'点赞/点个赞'时使用。",
    "send_poke": "拍一拍。当用户说'拍一拍/戳一戳'时使用。",
    "react_emoji": "给消息回复emoji表情。当用户说'回复表情/加个emoji'时使用。",
    "horoscope": "查询星座运势。当用户问'运势/星座'时使用。",
    "wenchang_dijun": "文昌帝君灵签抽签。当用户说'抽签/求签/算一卦'时使用。",
    "qq_file_reader": "读取QQ文件内容。当用户说'读文件/查看文件/分析文件/读取PDF'时使用。",
    "qq_image_analyzer": "分析QQ图片内容。当用户发送带图片的引用消息并要求分析时必须调用。",
    "crawl_webpage": "爬取指定URL网页内容。当用户发链接想获取页面内容时使用。",
    "tavily_search": "Tavily AI 搜索引擎。当用户询问实时信息/新闻/事实或你不知道答案时使用。",
    "weather_query": "查询指定城市天气（温度/湿度/风力等）。当用户问'天气/气温/下雨'时使用。",
    "group_file_downloader": "查看或下载QQ群文件。当用户说'看看群文件/下载群文件'时使用；未指定群号则用当前对话群。",
    "local_file_finder": "在本地电脑搜索文件。当用户说'找不到文件/帮我找文件'时使用。",
    "baiduhot": "获取百度热搜榜单。当用户问'百度热搜/baidu热榜'时使用。",
    "douyinhot": "获取抖音热搜榜单。当用户问'抖音热搜/douyin热榜'时使用。",
    "qq_level_query": "查询QQ号等级、活跃天数及升级进度。当用户问'QQ等级'时使用。",
    "weibohot": "获取微博热搜榜单。当用户问'微博热搜/微博热门/有什么新闻'时使用。",
    "web_search": "网络搜索（Bing/Google）。当用户需要搜索信息、查找资料时使用。",
    "python_interpreter": "执行Python代码。当用户说'运行代码/计算/数据分析'时使用。",
}

# 参数描述压缩（仅收录冗长项；未收录的走 trim_property_description）
QQ_PROP_OVERRIDES = {
    "get_current_time": {"format": "时间格式：iso/text/json"},
    "memory_list": {"time_range": "时间范围：今天/昨天/前天/上周/上月"},
    "react_emoji": {"emoji": "emoji名称：心/赞/哈哈等"},
    "memory_add": {"priority": "优先级0-1，越高越重要"},
    "group_file_downloader": {"group_id": "群号；未指定则用当前对话群"},
}

MAX_EXTRA_PACKS = 2


def classify_packs(user_input: str, max_extra: int = MAX_EXTRA_PACKS) -> List[str]:
    """按消息关键词把场景归类到 0-2 个扩展工具包（qq_core 恒在，不计入）。

    Args:
        user_input: 用户消息原文
        max_extra: 最多附加的扩展包数量（用户约束 0-2）

    Returns:
        扩展包名列表（按命中数降序，最多 max_extra 个）
    """
    if not user_input:
        return []
    text = str(user_input).lower()
    scored = []
    for pack, kws in PACK_KEYWORDS.items():
        hits = sum(1 for kw in kws if kw in text)
        if hits:
            scored.append((hits, pack))
    scored.sort(key=lambda item: -item[0])
    return [p for _, p in scored[:max_extra]]


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
    ]

    def __init__(self, tool_subnet):
        """
        初始化平台工具管理器

        Args:
            tool_subnet: ToolNet子网实例
        """
        self.tool_subnet = tool_subnet

    # ==================== Step 3：按场景选包 ====================

    def _schemas_for_names(self, names: List[str]) -> List[Dict]:
        """从注册表取指定工具名的 schema（不存在则跳过）"""
        try:
            all_schemas = self.tool_subnet.get_tools_schema()
            name_set = set(names)
            return [s for s in all_schemas if s.get("function", {}).get("name") in name_set]
        except Exception as e:  # noqa: BLE001 — 注册表异常时降级空集
            logger.warning(f"[平台工具] 获取 schema 失败: {e}")
            return []

    def _qq_available_names(self) -> List[str]:
        """QQ 平台可用工具名（核心 + 扩展，去重，排除屏幕视觉）"""
        seen = set()
        names = []
        for name in self.CORE_TOOLS + self.QQ_EXTENDED_TOOLS:
            if name in seen:
                continue
            seen.add(name)
            if name in ("mcp_screen_vision_look_screen", "mcp_screen_vision_screenshot"):
                continue
            names.append(name)
        return names

    def select_tools_for_message(self, platform: str, user_input: str = "") -> List[Dict]:
        """Step 3：按消息场景选择工具包（调用前分类，而非全量 68 工具）。

        - QQ 平台：qq_core + 0-2 个扩展包（按关键词分类），描述瘦身
        - 其他平台：维持原平台全集（不引入分类复杂度）
        - 任何失败降级为 qq_core，绝不回退全量 68
        """
        if platform not in ("qq", "aiocqhttp"):
            return self.get_platform_specific_tools(platform)

        packs = ["qq_core"] + classify_packs(user_input or "")
        names = []
        seen = set()
        for pack in packs:
            for name in TOOL_PACKS.get(pack, []):
                if name not in seen:
                    seen.add(name)
                    names.append(name)

        available = set(self._qq_available_names())
        names = [n for n in names if n in available]
        if not names:
            names = list(QQ_CORE_PACK)

        schemas = self._schemas_for_names(names)
        if not schemas:
            # 降级：仅 qq_core（双重保险，绝不回退全量）
            schemas = self._schemas_for_names(QQ_CORE_PACK)
        return trim_tool_schemas(schemas)

    def get_qq_core_schemas(self) -> List[Dict]:
        """仅 qq_core 包（兜底/降级用），描述瘦身。"""
        schemas = self._schemas_for_names(QQ_CORE_PACK)
        return trim_tool_schemas(schemas)

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
        except Exception as e:  # noqa: BLE001 — 平台工具读取失败降级返回空
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

            # Step 2：QQ 聊天场景对工具描述瘦身（保留触发/禁止/参数语义/区分/风险）
            if platform in ("qq", "aiocqhttp"):
                platform_schemas = trim_tool_schemas(platform_schemas)

            logger.info(f"[平台工具] 平台 {platform} 使用 {len(platform_schemas)} 个工具")
            return platform_schemas

        except Exception as e:  # noqa: BLE001 — 工具过滤失败降级为平台集，绝不回退全量 68
            logger.warning(f"[平台工具] 获取平台工具失败: {e}，降级平台核心集")
            if platform in ("qq", "aiocqhttp"):
                return self.get_qq_core_schemas()
            return self._schemas_for_names(selected_tools)

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

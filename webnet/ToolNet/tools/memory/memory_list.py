"""
列出记忆（统一接口层）

支持查询：
- 长期记忆（用户记忆 + 弥娅自记忆）
- 弥娅自记忆（承诺、观点、建议等）
- 按标签/角色/用户筛选

本工具优先使用新版 MiyaMemoryCore 记忆系统
"""

import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


def _load_config() -> Dict[str, Any]:
    """从 text_config.json 加载记忆列表工具配置"""
    try:
        config_path = (
            Path(__file__).parent.parent.parent.parent.parent
            / "config"
            / "text_config.json"
        )
        if config_path.exists():
            import json

            with open(config_path, "r", encoding="utf-8") as f:
                full_config = json.load(f)

            tool_config = full_config.get("memory_list_tool", {})
            self_config = full_config.get("assistant_self", {})

            return {
                "description": tool_config.get("description", ""),
                "time_range_options": tool_config.get("time_range_options", {}),
                "defaults": tool_config.get("defaults", {}),
                "self_memory_tags": self_config.get("self_memory_tags", []),
            }
    except Exception as e:
        logger.warning(f"[MemoryList] 加载配置失败: {e}")

    return {}


def _parse_time_range(
    time_range: Optional[str], keywords: Dict[str, List[str]]
) -> tuple:
    """解析时间范围，返回 (start_time, end_time)"""
    if not time_range:
        return None, None

    now = datetime.now()
    start_time = None
    end_time = None

    if time_range == "today":
        start_time = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif time_range == "yesterday":
        yesterday = now - timedelta(days=1)
        start_time = yesterday.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = yesterday.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_range == "day_before_yesterday":
        dby = now - timedelta(days=2)
        start_time = dby.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = dby.replace(hour=23, minute=59, second=59, microsecond=999999)
    elif time_range == "last_week":
        start_time = now - timedelta(days=7)
    elif time_range == "last_month":
        start_time = now - timedelta(days=30)

    return start_time, end_time


class MemoryList(BaseTool):
    """MemoryList - 统一记忆接口层"""

    @property
    def config(self) -> Dict[str, Any]:
        cfg = _load_config()

        time_range_desc = ", ".join(
            f"'{k}'({v})"
            for k, v in cfg.get(
                "time_range_options",
                {
                    "today": "今天",
                    "yesterday": "昨天",
                    "day_before_yesterday": "前天",
                    "last_week": "上周",
                    "last_month": "上月",
                },
            ).items()
        )

        defaults = cfg.get("defaults", {"limit": 15, "include_dialogue": True})

        return {
            "name": "memory_list",
            "description": cfg.get("description", "列出记忆"),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": f"返回的最大数量，默认{defaults.get('limit', 15)}",
                        "default": defaults.get("limit", 15),
                        "minimum": 1,
                        "maximum": 50,
                    },
                    "tag": {"type": "string", "description": "按标签筛选记忆"},
                    "role": {
                        "type": "string",
                        "description": "按角色筛选：'user'（用户说的）、'assistant'（弥娅说的）、不填则全部",
                        "enum": ["user", "assistant"],
                    },
                    "include_dialogue": {
                        "type": "boolean",
                        "description": f"是否包含对话历史（dialogue层），默认{defaults.get('include_dialogue', True)}",
                        "default": defaults.get("include_dialogue", True),
                    },
                    "time_range": {
                        "type": "string",
                        "description": f"时间范围筛选: {time_range_desc}",
                        "enum": list(
                            cfg.get(
                                "time_range_options",
                                {
                                    "today": "今天",
                                    "yesterday": "昨天",
                                    "day_before_yesterday": "前天",
                                    "last_week": "上周",
                                    "last_month": "上月",
                                },
                            ).keys()
                        ),
                    },
                },
                "required": [],
            },
        }

    async def execute(self, context: ToolContext, **kwargs) -> str:
        """执行工具 - 优先使用 MiyaMemoryCore"""
        cfg = _load_config()
        defaults = cfg.get("defaults", {})

        args = kwargs
        limit = args.get("limit", defaults.get("limit", 15))
        tag = args.get("tag")
        role_filter = args.get("role")
        include_dialogue = args.get(
            "include_dialogue", defaults.get("include_dialogue", True)
        )
        time_range = args.get("time_range")
        user_id = str(context.user_id) if context.user_id else None

        self_memory_tags = cfg.get("self_memory_tags", [])
        preview_length = defaults.get("content_preview_length", 120)

        start_time, end_time = _parse_time_range(time_range, {})

        try:
            from memory import get_memory_core

            core = await get_memory_core()

            if tag:
                results = await core.search_by_tag(
                    tag,
                    user_id=user_id,
                    limit=limit,
                    start_time=start_time,
                    end_time=end_time,
                )
            elif role_filter == "assistant":
                from memory.core import MemoryQuery

                q = MemoryQuery(
                    query="",
                    limit=limit * 3,
                    start_time=start_time,
                    end_time=end_time,
                )
                all_results = await core.retrieve(q)
                results = []
                for m in all_results:
                    level_val = (
                        m.level.value if hasattr(m.level, "value") else str(m.level)
                    )
                    source_val = (
                        m.source.value if hasattr(m.source, "value") else str(m.source)
                    )
                    if (
                        source_val == "assistant_self"
                        or any(t in (m.tags or []) for t in self_memory_tags)
                        or (
                            getattr(m, "role", "") == "assistant"
                            and level_val in ("long_term", "semantic")
                        )
                    ):
                        results.append(m)
                    if len(results) >= limit:
                        break
            elif user_id and user_id != "global":
                results = await core.search_by_user(
                    user_id, limit=limit, start_time=start_time, end_time=end_time
                )
            else:
                from memory.core import MemoryQuery

                q = MemoryQuery(
                    query="",
                    limit=limit * 3,
                    start_time=start_time,
                    end_time=end_time,
                )
                results = await core.retrieve(q)
                filtered = []
                for m in results:
                    level_val = (
                        m.level.value if hasattr(m.level, "value") else str(m.level)
                    )
                    source_val = (
                        m.source.value if hasattr(m.source, "value") else str(m.source)
                    )
                    meta = getattr(m, "metadata", {}) or {}
                    if level_val in ("long_term", "semantic", "knowledge"):
                        filtered.append(m)
                    elif level_val == "short_term":
                        priority = getattr(m, "priority", 0)
                        importance = meta.get("importance", "")
                        if (
                            priority >= 0.7
                            or importance == "high"
                            or source_val == "assistant_self"
                            or source_val == "manual"
                            or meta.get("pinned", False)
                        ):
                            filtered.append(m)
                    elif level_val == "dialogue" and include_dialogue:
                        if role_filter is None or getattr(m, "role", "") == role_filter:
                            filtered.append(m)
                results = filtered[:limit]

            if not results:
                if role_filter == "assistant":
                    return "[INFO] 弥娅暂无自记忆记录。弥娅的承诺、观点、建议等会在对话中自动提取并存储。"
                return "[INFO] No memories found"

            result_lines = [
                f"[INFO] Memory list (total {len(results)} memories)",
                "-" * 40,
            ]
            for i, mem in enumerate(results, 1):
                content_preview = (
                    mem.content[:preview_length] + "..."
                    if len(mem.content) > preview_length
                    else mem.content
                )
                tags_str = ", ".join(mem.tags) if mem.tags else "none"
                level_label = {
                    "long_term": "long_term",
                    "short_term": "short_term",
                    "dialogue": "dialogue",
                    "semantic": "semantic",
                    "knowledge": "knowledge",
                }.get(
                    mem.level.value if hasattr(mem.level, "value") else str(mem.level),
                    mem.level.value if hasattr(mem.level, "value") else "unknown",
                )

                role_label = getattr(mem, "role", "")
                source_label = ""
                if hasattr(mem.source, "value"):
                    source_label = mem.source.value
                elif hasattr(mem.source, "__str__"):
                    source_label = str(mem.source)

                line_parts = [f"{i}. [{level_label}]"]
                if role_label:
                    line_parts.append(f"[{role_label}]")
                if source_label == "assistant_self":
                    line_parts.append("[自记忆]")
                line_parts.append(content_preview)

                result_lines.append(" ".join(line_parts))
                result_lines.append(f"   tags: {tags_str}")
                result_lines.append(f"   user_id: {mem.user_id}")
                result_lines.append(
                    f"   created_at: {mem.created_at[:16] if mem.created_at else 'unknown'}"
                )
                if source_label:
                    result_lines.append(f"   source: {source_label}")
                result_lines.append("")

            return "\n".join(result_lines)

        except Exception as e:
            logger.error(f"[MemoryList] MiyaMemoryCore 查询失败: {e}", exc_info=True)

        try:
            from memory.undefined_memory import get_undefined_memory_adapter

            adapter = get_undefined_memory_adapter()

            if tag:
                memories = await adapter.get_by_tag(tag, limit)
            else:
                memories = await adapter.get_all(limit)

            if not memories:
                return "[INFO] No memories found in Undefined lightweight memory system"

            result = f"[INFO] Memory list (Undefined lightweight memory system)\nTotal {len(memories)} memories\n\n"
            for i, mem in enumerate(memories, 1):
                if isinstance(mem, dict):
                    content = mem.get("content", "")
                    tags = mem.get("tags", [])
                    mem_id = mem.get("id", mem.get("uuid", "unknown"))
                    created_at = mem.get("created_at", "未知时间")
                else:
                    content = getattr(mem, "fact", getattr(mem, "content", ""))
                    tags = getattr(mem, "tags", [])
                    mem_id = getattr(mem, "uuid", getattr(mem, "id", "unknown"))
                    created_at = getattr(mem, "created_at", "未知时间")

                content_preview = (
                    content[: int(preview_length * 0.83)] + "..."
                    if len(content) > int(preview_length * 0.83)
                    else content
                )
                tags_str = ", ".join(tags) if tags else "none"
                result += f"{i}. **{mem_id}**\n"
                result += f"   created_at: {created_at}\n"
                result += f"   content: {content_preview}\n"
                result += f"   tags: {tags_str}\n\n"

            return result
        except Exception as e:
            logger.error(f"[MemoryList] Undefined 记忆系统失败: {e}", exc_info=True)

        cognitive_memory = getattr(context, "cognitive_memory", None)
        if cognitive_memory:
            try:
                results = await cognitive_memory.search(
                    query=tag if tag else "", top_k=limit
                )

                if not results:
                    return "[INFO] No memories found in cognitive memory system"

                result = f"[INFO] Memory list (cognitive memory system)\nTotal {len(results)} memories\n\n"
                for i, mem in enumerate(results, 1):
                    content_preview = (
                        mem.get("content", "")[:100] + "..."
                        if len(mem.get("content", "")) > 100
                        else mem.get("content", "")
                    )
                    result += f"{i}. **{mem.get('id', 'unknown')}**\n"
                    result += f"   content: {content_preview}\n"
                    tags = mem.get("tags", [])
                    tag_str = ", ".join(tags) if tags else "none"
                    result += f"   tags: {tag_str}\n\n"

                return result
            except Exception as e:
                logger.error(f"[MemoryList] 认知记忆系统失败: {e}", exc_info=True)

        return "[INFO] Memory system not initialized, unable to list memories"

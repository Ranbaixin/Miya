"""
/profile 命令 — 从 config 读取消息，使用认知侧写存储
"""
from __future__ import annotations

import logging
from typing import Any, List

from config.config_utils import get_text_message

logger = logging.getLogger(__name__)


async def execute(args: List[str], context: Any) -> str:
    is_group = False
    target_id = ""
    for arg in args:
        if arg.lower().strip() in ("g", "group", "群"):
            is_group = True
        elif arg.strip().isdigit():
            if context.check_permission("superadmin"):
                target_id = arg.strip()

    if is_group:
        entity_type = "group"
        entity_id = target_id or str(context.group_id)
        if not entity_id or entity_id == "0":
            return get_text_message("cognitive_memory", "group_profile_private")
    else:
        entity_type = "user"
        entity_id = target_id or str(context.sender_id)

    try:
        from webnet.ToolNet.tools.cognitive.profile_storage import get_profile_storage
        storage = get_profile_storage()
        profile = await storage.read_profile(entity_type, entity_id)
        if profile:
            type_label = "用户" if entity_type == "user" else "群聊"
            return f"【{type_label}侧写】ID: {entity_id}\n{profile}"

        observations = await storage.get_observations(entity_type, entity_id, limit=5)
        if observations:
            type_label = "用户" if entity_type == "user" else "群聊"
            header = get_text_message("cognitive_memory", "preliminary_header", type=type_label)
            obs_text = "\n".join(f"- {o['observation']}" for o in observations)
            footer = get_text_message("cognitive_memory", "preliminary_footer")
            return f"{header}\n{obs_text}\n\n{footer}"
    except Exception as e:
        logger.debug(f"获取侧写失败: {e}")

    type_label = "用户" if entity_type == "user" else "群聊"
    return get_text_message("cognitive_memory", "profile_empty", type=type_label)

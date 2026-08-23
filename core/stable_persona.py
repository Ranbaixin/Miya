"""稳定画像（stable persona）构建器 —— 2026-08 修订计划 Step 6

从长期记忆中挑选白名单标签（喜好/信息/identity/重要）的条目：
- 结构化合并去重：MemoryItem ID 优先，缺失时用归一化文本
- 冲突（同 ID/同文本）取时间戳最新者
- 用户隔离：条目显式归属其他用户时剔除（群聊不跨用户泄漏）
- 最多 3 条；失败/无结果返回空段
- 日志只含条数，不含记忆正文
"""

import logging
import re
from datetime import datetime
from typing import List, Optional

logger = logging.getLogger(__name__)

# 稳定画像白名单标签（命中任一即可，见记忆白名单统计）
STABLE_TAGS = ("喜好", "信息", "identity", "重要")
MAX_STABLE_ITEMS = 3

_WS_RE = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """归一化文本：去全部空白 + 小写，用于去重键"""
    if not text:
        return ""
    return _WS_RE.sub("", str(text)).strip().lower()


def _item_time(item) -> str:
    """取条目时间戳（created_at 优先，回退 updated_at）"""
    ts = getattr(item, "created_at", None) or getattr(item, "updated_at", None) or ""
    return str(ts)


def _item_id(item) -> str:
    return str(getattr(item, "id", "") or "")


def merge_and_dedupe(
    items: List,
    target_user_id: Optional[str] = None,
    max_items: int = MAX_STABLE_ITEMS,
) -> List:
    """按 ID/归一化文本去重，时间戳最新者胜，用户隔离，最多 max_items 条。"""
    if not items:
        return []
    ordered = sorted(items, key=_item_time, reverse=True)
    seen = set()
    out = []
    for item in ordered:
        # 用户隔离：条目显式归属他人则剔除（默认 global 不设限）
        item_uid = str(getattr(item, "user_id", "") or "")
        if target_user_id is not None and item_uid and item_uid != "global":
            if item_uid != str(target_user_id):
                continue
        mid = _item_id(item)
        content = str(getattr(item, "content", "") or "")
        key = mid if mid else normalize_text(content)
        if not key:
            continue
        if key in seen:
            continue
        seen.add(key)
        out.append(item)
        if len(out) >= max_items:
            break
    return out


def format_stable_persona(items: List) -> str:
    """格式化为提示词段；空列表返回空串。"""
    if not items:
        return ""
    lines = ["【关于TA的稳定印象（长期记忆）】"]
    for item in items:
        content = str(getattr(item, "content", "") or "").strip()
        if not content:
            continue
        ts = _item_time(item)
        ts_str = ""
        if ts:
            try:
                ts_str = datetime.fromisoformat(ts).strftime("%m-%d %H:%M")
            except (ValueError, TypeError):
                ts_str = ""
        prefix = f"[{ts_str}] " if ts_str else ""
        lines.append(f"- {prefix}{content}")
    if len(lines) == 1:
        return ""
    return "\n".join(lines)


async def fetch_stable_persona(
    memory_core,
    user_id: Optional[str] = None,
    group_id: Optional[str] = None,
) -> str:
    """从长期记忆构建稳定画像段。

    Args:
        memory_core: MiyaMemoryCore 实例（或 None → 空段）
        user_id: 当前用户 ID（None → 不限定用户）
        group_id: 当前群 ID（仅群聊传入，用于进一步收敛）

    Returns:
        稳定画像提示段；任何失败返回空串（不阻断主流程）。
    """
    if memory_core is None:
        return ""
    try:
        from memory.core import MemoryLevel, MemoryQuery

        q = MemoryQuery(
            level=MemoryLevel.LONG_TERM,
            tags=list(STABLE_TAGS),
            any_tag=True,
            user_id=str(user_id) if user_id is not None else None,
            group_id=str(group_id) if group_id else None,
            limit=20,
            sort_by="priority",
            sort_order="desc",
        )
        items = await memory_core.retrieve(q)
        merged = merge_and_dedupe(
            items,
            target_user_id=str(user_id) if user_id is not None else None,
        )
        segment = format_stable_persona(merged)
        logger.info(f"[稳定画像] 白名单命中 {len(items)} 条，去重后 {len(merged)} 条")
        return segment
    except Exception as e:  # noqa: BLE001 — 稳定画像为增强上下文，失败降级空段
        logger.warning(f"[稳定画像] 构建失败: {e}")
        return ""

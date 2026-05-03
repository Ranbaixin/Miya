"""
弥娅思考记录查询工具

用于查询弥娅的思考过程、情绪分析、内心独白等认知记忆
"""

from typing import Dict, Any, Optional, List
import logging
from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class ThinkingQueryTool(BaseTool):
    """思考记录查询工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "thinking_query",
            "description": """弥娅思考记录查询工具，用于查看弥娅的思考过程、情绪分析、内心独白等。

可查询内容：
1. 最近思考 - 查看最近的思考记录
2. 内心独白 - 查看内心独白历史
3. 情绪历史 - 查看情绪变化
4. 归因分析 - 查看归因历史
5. 完整记录 - 查看完整认知记录

使用方式：
- 思考最近 [数量]
- 思考内心 [数量]
- 思考情绪 [数量]
- 思考归因 [数量]
- 思考完整 [数量]""",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {
                        "type": "string",
                        "description": "操作类型: recent/inner/emotion/attribution/full",
                        "enum": ["recent", "inner", "emotion", "attribution", "full"],
                    },
                    "limit": {
                        "type": "integer",
                        "description": "返回数量限制",
                        "default": 5,
                    },
                },
                "required": ["action"],
            },
        }

    async def execute(self, context: ToolContext, **kwargs) -> str:
        """执行思考记录查询"""
        args = kwargs.get("args", {}) if kwargs else {}
        action = args.get("action", "recent") if args else "recent"
        limit = args.get("limit", 5) if args else 5

        user_id = str(context.user_id) if context.user_id else None
        if not user_id:
            return "无法确定用户身份"

        try:
            if action == "recent":
                return await self._get_recent(limit, user_id)
            elif action == "inner":
                return await self._get_inner_thought(limit, user_id)
            elif action == "emotion":
                return await self._get_emotions(limit, user_id)
            elif action == "attribution":
                return await self._get_attributions(limit, user_id)
            elif action == "full":
                return await self._get_full(limit, user_id)
            else:
                return "未知操作类型"
        except Exception as e:
            logger.error(f"思考记录查询失败: {e}")
            return f"查询失败: {str(e)[:100]}"

    async def _get_recent(self, limit: int, user_id: str) -> str:
        """获取最近思考记录"""
        try:
            from memory.cognition_cache import get_cognition_cache

            cache = get_cognition_cache()
            records = await cache.get_recent(user_id, limit)

            if not records:
                from memory import retrieve_cognition

                results = await retrieve_cognition(user_id, limit)
                if not results:
                    return "暂无思考记录"

                lines = [f"🧠 最近的思考记录 ({len(results)}条)", "=" * 50]
                for i, rec in enumerate(results, 1):
                    inner = rec.get("inner_thought", "")[:40]
                    thinking = rec.get("thinking", "")[:60]
                    lines.append(f"\n{i}. 内心: {inner}")
                    if thinking:
                        lines.append(f"   思考: {thinking}")
                return "\n".join(lines)

            lines = [f"🧠 最近的思考记录 ({len(records)}条)", "=" * 50]
            for i, rec in enumerate(records, 1):
                inner = rec.inner_thought[:40]
                thinking = rec.thinking[:60]
                emotions = rec.emotions
                emotions_str = (
                    ", ".join([f"{k}({v})" for k, v in list(emotions.items())[:3]])
                    if emotions
                    else "无"
                )
                lines.append(f"\n{i}. 内心: {inner}")
                lines.append(f"   情绪: {emotions_str}")
                if thinking:
                    lines.append(f"   思考: {thinking}")
            return "\n".join(lines)

        except Exception as e:
            return f"查询失败: {str(e)}"

    async def _get_inner_thought(self, limit: int, user_id: str) -> str:
        """获取内心独白历史"""
        try:
            from memory.cognition_cache import get_cognition_cache

            cache = get_cognition_cache()
            records = await cache.get_recent(user_id, limit)

            if not records:
                from memory import retrieve_cognition

                results = await retrieve_cognition(user_id, limit)
                if not results:
                    return "暂无内心独白记录"

                lines = [f"💭 内心独白历史 ({len(results)}条)", "=" * 50]
                for i, rec in enumerate(results, 1):
                    inner = rec.get("inner_thought", "")
                    if inner:
                        lines.append(f"{i}. {inner}")
                return "\n".join(lines)

            lines = [f"💭 内心独白历史 ({len(records)}条)", "=" * 50]
            for i, rec in enumerate(records, 1):
                if rec.inner_thought:
                    lines.append(f"{i}. {rec.inner_thought}")
            return "\n".join(lines)

        except Exception as e:
            return f"查询失败: {str(e)}"

    async def _get_emotions(self, limit: int, user_id: str) -> str:
        """获取情绪历史"""
        try:
            from memory.cognition_cache import get_cognition_cache

            cache = get_cognition_cache()
            records = await cache.get_recent(user_id, limit)

            if not records:
                from memory import retrieve_cognition

                results = await retrieve_cognition(user_id, limit)
                if not results:
                    return "暂无情绪记录"

                lines = [f"💗 情绪历史 ({len(results)}条)", "=" * 50]
                for i, rec in enumerate(results, 1):
                    emotions = rec.get("emotions", {})
                    if emotions:
                        emotions_str = ", ".join(
                            [f"{k}({v})" for k, v in emotions.items()]
                        )
                        lines.append(f"{i}. {emotions_str}")
                return "\n".join(lines)

            lines = [f"💗 情绪历史 ({len(records)}条)", "=" * 50]
            for i, rec in enumerate(records, 1):
                emotions = rec.emotions
                if emotions:
                    emotions_str = ", ".join([f"{k}({v})" for k, v in emotions.items()])
                    lines.append(f"{i}. {emotions_str}")
            return "\n".join(lines)

        except Exception as e:
            return f"查询失败: {str(e)}"

    async def _get_attributions(self, limit: int, user_id: str) -> str:
        """获取归因分析历史"""
        try:
            from memory.cognition_cache import get_cognition_cache

            cache = get_cognition_cache()
            records = await cache.get_recent(user_id, limit)

            if not records:
                from memory import retrieve_cognition

                results = await retrieve_cognition(user_id, limit)
                if not results:
                    return "暂无归因记录"

                lines = [f"🎯 归因分析历史 ({len(results)}条)", "=" * 50]
                for i, rec in enumerate(results, 1):
                    attr = rec.get("attribution", "")
                    if attr:
                        lines.append(f"{i}. {attr}")
                return "\n".join(lines)

            lines = [f"🎯 归因分析历史 ({len(records)}条)", "=" * 50]
            for i, rec in enumerate(records, 1):
                if rec.attribution:
                    lines.append(f"{i}. {rec.attribution}")
            return "\n".join(lines)

        except Exception as e:
            return f"查询失败: {str(e)}"

    async def _get_full(self, limit: int, user_id: str) -> str:
        """获取完整认知记录"""
        try:
            from memory.cognition_cache import get_cognition_cache

            cache = get_cognition_cache()
            records = await cache.get_recent(user_id, limit)

            if not records:
                from memory import retrieve_cognition

                results = await retrieve_cognition(user_id, limit)
                if not results:
                    return "暂无认知记录"

                lines = [f"📝 完整认知记录 ({len(results)}条)", "=" * 60]
                for i, rec in enumerate(results, 1):
                    inner = rec.get("inner_thought", "")
                    attr = rec.get("attribution", "")
                    refl = rec.get("reflection", "")
                    emotions = rec.get("emotions", {})

                    lines.append(f"\n--- 第{i}条 ---")
                    if inner:
                        lines.append(f"内心: {inner}")
                    if emotions:
                        emotions_str = ", ".join(
                            [f"{k}({v})" for k, v in emotions.items()]
                        )
                        lines.append(f"情绪: {emotions_str}")
                    if attr:
                        lines.append(f"归因: {attr}")
                    if refl:
                        lines.append(f"反思: {refl}")
                return "\n".join(lines)

            lines = [f"📝 完整认知记录 ({len(records)}条)", "=" * 60]
            for i, rec in enumerate(records, 1):
                lines.append(f"\n--- 第{i}条 ---")
                if rec.inner_thought:
                    lines.append(f"内心: {rec.inner_thought}")
                if rec.emotions:
                    emotions_str = ", ".join(
                        [f"{k}({v})" for k, v in rec.emotions.items()]
                    )
                    lines.append(f"情绪: {emotions_str}")
                if rec.attribution:
                    lines.append(f"归因: {rec.attribution}")
                if rec.reflection:
                    lines.append(f"反思: {rec.reflection}")
                if rec.thinking:
                    lines.append(f"思考: {rec.thinking[:80]}")
            return "\n".join(lines)

        except Exception as e:
            return f"查询失败: {str(e)}"


TOOL_CLASS = ThinkingQueryTool

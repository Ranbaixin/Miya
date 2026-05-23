"""
热搜查询工具 - 微博热搜
"""

import logging
from typing import Any, Dict

import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class WeiboHotTool(BaseTool):
    """微博热搜工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "weibohot",
            "description": "获取微博实时热搜榜。当用户问'热搜'、'微博热搜'、'有什么新闻'时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "返回条数，默认为10",
                        "default": 10,
                    }
                },
            },
        }

    async def execute(self, context: ToolContext, **kwargs) -> str:
        args = kwargs.get("args", {}) if kwargs else {}
        limit = args.get("limit", 10)

        return await self._get_hot_list(limit)

    async def _get_hot_list(self, limit: int) -> str:
        """获取热搜列表"""
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Referer": "https://weibo.com/",
                "Accept": "application/json, text/plain, */*",
            }
            async with httpx.AsyncClient(timeout=10, headers=headers) as client:
                resp = await client.get("https://weibo.com/ajax/side/hotSearch")

                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("ok") == 1:
                        realtime = data.get("data", {}).get("realtime", [])

                        if not realtime:
                            return "暂无热搜数据"

                        lines = ["【微博热搜榜】"]
                        for i, item in enumerate(realtime[:limit]):
                            word = item.get("word", "")
                            item.get("num", 0)
                            if word:
                                lines.append(f"{i + 1}. {word}")

                        return "\n".join(lines)

            return "获取热搜失败，请稍后再试"

        except Exception as e:
            logger.error(f"获取微博热搜失败: {e}")
            return f"获取热搜失败: {str(e)[:50]}"


def get_weibohot_tool():
    return WeiboHotTool()

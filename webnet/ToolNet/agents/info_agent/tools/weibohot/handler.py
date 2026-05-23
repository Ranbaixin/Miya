"""
微博热搜工具 - info_agent专用
"""

import logging
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)


async def execute(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    """获取微博热搜榜单"""
    limit = args.get("limit", 10)

    if limit < 1 or limit > 50:
        return "热搜数量必须在1-50之间"

    try:
        # 使用免费API
        async with httpx.AsyncClient(timeout=15) as client:
            resp = await client.get("https://weibo.com/ajax/side/hotSearch")

            if resp.status_code != 200:
                return f"获取热搜失败: HTTP {resp.status_code}"

            data = resp.json()
            if data.get("ok") != 1:
                return f"获取热搜失败: {data.get('msg', '未知错误')}"

            hot_list = data.get("data", {}).get("realtime", [])
            if not hot_list:
                return "暂无热搜数据"

            result = f"【微博热搜 TOP {min(limit, len(hot_list))}】\n\n"

            for idx, item in enumerate(hot_list[:limit], 1):
                title = item.get("word", "")
                hot = item.get("num", 0)
                if title:
                    result += f"{idx}. {title}\n"
                    if hot:
                        result += f"   热度: {hot}\n"

            return result

    except Exception as e:
        logger.error(f"获取微博热搜失败: {e}")
        return f"获取热搜失败: {str(e)[:50]}"

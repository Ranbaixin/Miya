"""
Grok搜索工具 - web_agent专用
"""

import logging
import os
from typing import Any, Dict

import httpx

logger = logging.getLogger(__name__)

GROK_API_URL = os.environ.get("GROK_API_URL", "https://api.xai.ai/v1/chat/completions")
GROK_API_KEY = os.environ.get("GROK_API_KEY", "")
GROK_MODEL = os.environ.get("GROK_MODEL", "grok-2-1212")


async def execute(args: Dict[str, Any], context: Dict[str, Any]) -> str:
    """执行Grok搜索"""
    query = args.get("query", "").strip()

    if not query:
        return "请提供搜索内容"

    if not GROK_API_KEY:
        return "Grok搜索功能未配置（缺少GROK_API_KEY环境变量）\n请在config/.env中设置GROK_API_KEY"

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {
                "Authorization": f"Bearer {GROK_API_KEY}",
                "Content-Type": "application/json",
            }
            data = {
                "model": GROK_MODEL,
                "messages": [
                    {
                        "role": "user",
                        "content": f"请搜索以下内容并提供详细信息：{query}\n\n请提供搜索结果摘要和相关信息来源。",
                    }
                ],
                "max_tokens": 4096,
            }

            response = await client.post(GROK_API_URL, headers=headers, json=data)
            response.raise_for_status()

            result = response.json()
            content = (
                result.get("choices", [{}])[0].get("message", {}).get("content", "")
            )

            if content:
                return f"【Grok搜索结果】\n\n{content}"
            else:
                return "未获取到搜索结果"

    except httpx.TimeoutException:
        logger.error("Grok搜索超时")
        return "搜索超时，请稍后重试"
    except httpx.HTTPStatusError as e:
        logger.error(f"Grok搜索HTTP错误: {e}")
        return f"搜索失败：HTTP {e.response.status_code}"
    except Exception as e:
        logger.exception(f"Grok搜索失败: {e}")
        return f"搜索失败：{str(e)}"

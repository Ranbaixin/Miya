"""
网络搜索工具 - web_agent专用
"""

from typing import Dict, Any
import logging
import httpx
import os

logger = logging.getLogger(__name__)


def _search_duckduckgo(query: str, count: int = 5) -> str:
    """使用DuckDuckGo免费搜索"""
    try:
        url = "https://html.duckduckgo.com/html/"
        params = {"q": query, "b": count}

        import requests

        resp = requests.get(url, params=params, timeout=10)

        if resp.status_code == 200:
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(resp.text, "html.parser")

            results = []
            for result in soup.select(".result")[:count]:
                title_elem = result.select_one(".result__title")
                snippet_elem = result.select_one(".result__snippet")
                link_elem = result.select_one("a.result__a")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    url = link_elem.get("href", "") if link_elem else ""

                    results.append(
                        f"{len(results) + 1}. {title}\n   {snippet[:100]}...\n   链接: {url}\n"
                    )

            if results:
                return "\n".join(results)
            else:
                return f"未找到与'{query}'相关的搜索结果"
        else:
            return f"DuckDuckGo搜索失败: HTTP {resp.status_code}"
    except Exception as e:
        return f"DuckDuckGo搜索失败: {str(e)[:50]}"


async def execute(context, **kwargs) -> str:
    """执行网络搜索"""
    query = kwargs.get("query", "")
    count = kwargs.get("count", 5)

    if not query:
        return "请提供搜索关键词"

    try:
        # 优先使用配置的API
        from core.system_config import get_api_url

        bing_key = os.getenv("BING_API_KEY", "")
        search_url = (
            get_api_url("bing_search") or "https://api.bing.microsoft.com/v7.0/search"
        )

        if bing_key:
            headers = {"Ocp-Apim-Subscription-Key": bing_key}
            params = {"q": query, "count": count, "mkt": "zh-CN"}

            async with httpx.AsyncClient(timeout=15, headers=headers) as client:
                resp = await client.get(search_url, params=params)

                if resp.status_code == 200:
                    data = resp.json()
                    web_pages = data.get("webPages", {}).get("value", [])

                    if not web_pages:
                        return f"未找到与'{query}'相关的搜索结果"

                    result = f"【搜索结果: {query}】\n\n"

                    for i, item in enumerate(web_pages[:count], 1):
                        title = item.get("name", "")
                        snippet = item.get("snippet", "")
                        url = item.get("url", "")

                        if title:
                            result += f"{i}. {title}\n"
                            if snippet:
                                result += f"   {snippet[:100]}...\n"
                            result += f"   链接: {url}\n\n"

                    return result
                else:
                    return f"Bing搜索失败，尝试DuckDuckGo...\n\n{_search_duckduckgo(query, count)}"
        else:
            # 无API key时使用DuckDuckGo备用方案
            return f"【搜索结果: {query}】\n\n{_search_duckduckgo(query, count)}"

    except Exception as e:
        logger.error(f"网络搜索失败: {e}")
        return f"搜索失败: {str(e)[:50]}"

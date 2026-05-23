"""
arXiv论文搜索工具
"""

import logging
from typing import Any, Dict
from urllib.parse import quote

import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)


class ArxivSearchTool(BaseTool):
    """arXiv论文搜索工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "arxiv_search",
            "description": "搜索arXiv学术论文库，查找相关学术文献。当用户问'论文'、'查找paper'、'搜索arxiv'时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "搜索关键词或论文标题"},
                    "max_results": {
                        "type": "integer",
                        "description": "返回结果数量，默认为5",
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        }

    async def execute(self, context: ToolContext, **kwargs) -> str:
        args = kwargs.get("args", {}) if kwargs else {}
        query = args.get("query", "")
        max_results = args.get("max_results", 5)

        if not query:
            return "请提供搜索关键词"

        return await self._search_arxiv(query, max_results)

    async def _search_arxiv(self, query: str, max_results: int) -> str:
        """搜索arXiv"""
        try:
            async with httpx.AsyncClient(timeout=30) as client:
                url = "http://export.arxiv.org/api/query"
                params = {
                    "search_query": f"all:{quote(query)}",
                    "start": 0,
                    "max_results": max_results,
                    "sortBy": "relevance",
                    "sortOrder": "descending",
                }

                resp = await client.get(url, params=params)

                if resp.status_code == 200:
                    import xml.etree.ElementTree as ET

                    root = ET.fromstring(resp.text)
                    ns = {"atom": "http://www.w3.org/2005/Atom"}

                    entries = root.findall(".//atom:entry", ns)

                    if not entries:
                        return f"未找到与'{query}'相关的论文"

                    lines = [f"【arXiv论文搜索结果: {query}】\n"]

                    for i, entry in enumerate(entries):
                        title = entry.find("atom:title", ns)
                        summary = entry.find("atom:summary", ns)
                        link = entry.find("atom:id", ns)
                        published = entry.find("atom:published", ns)

                        title_text = (
                            title.text.strip().replace("\n", " ")
                            if title is not None
                            else "无标题"
                        )
                        summary_text = (
                            summary.text.strip()[:200] if summary is not None else ""
                        )
                        link_text = link.text if link is not None else ""
                        date = published.text[:10] if published is not None else ""

                        lines.append(f"\n{i + 1}. {title_text}")
                        lines.append(f"   日期: {date}")
                        lines.append(f"   摘要: {summary_text}...")
                        lines.append(f"   链接: {link_text}")

                    return "\n".join(lines)

            return "搜索失败，请稍后再试"

        except Exception as e:
            logger.error(f"arXiv搜索失败: {e}")
            return f"搜索失败: {str(e)[:50]}"


def get_arxiv_search_tool():
    return ArxivSearchTool()

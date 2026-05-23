"""
网页爬取工具

抓取网页内容并提取文本，支持Markdown格式输出。
"""

import logging
import os
from typing import Any, Dict

import httpx
from bs4 import BeautifulSoup

from core.system_config import get_api_url
from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)

XXAPI_BASE_URL = os.environ.get(
    "XXAPI_BASE_URL", get_api_url("xxapi") or "https://v2.xxapi.cn"
)


class CrawlWebpageTool(BaseTool):
    """网页爬取工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "crawl_webpage",
            "description": """网页内容抓取工具。

当用户需要获取特定网页的内容时使用此工具。
可以抓取网页并提取文本、标题等信息。

示例:
- 抓取: 获取百度首页的内容
- 爬取: https://example.com 的内容""",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "要抓取的网页URL",
                    },
                    "max_chars": {
                        "type": "integer",
                        "description": "最大字符数，默认4096",
                        "default": 4096,
                    },
                },
                "required": ["url"],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        url = args.get("url", "").strip()
        if not url:
            return "请提供要抓取的URL"

        if not url.startswith(("http://", "https://")):
            return "URL必须以http://或https://开头"

        max_chars = args.get("max_chars", 4096)

        try:
            async with httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True,
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
            ) as client:
                response = await client.get(url)
                response.raise_for_status()

                html = response.text

                soup = BeautifulSoup(html, "html.parser")

                for script in soup(["script", "style"]):
                    script.decompose()

                title = soup.title.string if soup.title else ""
                description = ""
                meta_desc = soup.find("meta", {"name": "description"})
                if meta_desc:
                    description = meta_desc.get("content", "")

                text = soup.get_text()

                lines = (line.strip() for line in text.splitlines())
                chunks = (
                    phrase.strip() for line in lines for phrase in line.split("  ")
                )
                text = "\n".join(chunk for chunk in chunks if chunk)

                if max_chars > 0 and len(text) > max_chars:
                    text = text[:max_chars] + "\n\n...（内容已截断）"

                result = "# 网页抓取结果\n\n"
                result += f"**URL**: {url}\n\n"

                if title:
                    result += f"**标题**: {title}\n\n"

                if description:
                    result += f"**描述**: {description}\n\n"

                result += "---\n\n## 内容\n\n"
                result += text

                return result

        except httpx.TimeoutException:
            logger.error(f"网页抓取超时: {url}")
            return "网页抓取超时，请稍后重试"
        except httpx.HTTPStatusError as e:
            logger.error(f"网页抓取HTTP错误: {e}")
            return f"网页抓取失败：HTTP {e.response.status_code}"
        except Exception as e:
            logger.exception(f"网页抓取失败: {e}")
            return f"网页抓取失败：{str(e)}"


def get_crawl_webpage_tool():
    return CrawlWebpageTool()

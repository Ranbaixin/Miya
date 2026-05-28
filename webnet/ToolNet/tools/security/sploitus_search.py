"""
Sploitus 漏洞利用搜索工具

搜索 Sploitus 的 Exploit-DB、Packet Storm 等漏洞利用数据库。
支持按关键词、CVE 编号、产品名称搜索。
"""

import asyncio
import logging
from typing import Any, Dict, List, Optional

import httpx
from bs4 import BeautifulSoup

from webnet.ToolNet.base import BaseTool, ToolContext

logger = logging.getLogger(__name__)

SPLOITUS_API = "https://sploitus.com"
EXPLOIT_DB_SEARCH = "https://www.exploit-db.com/search"


class SecuritySploitusSearchTool(BaseTool):
    """Sploitus 漏洞利用搜索工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_sploitus_search",
            "description": (
                "漏洞利用搜索工具。\n"
                "搜索 Exploit-DB、Sploitus 等数据库中的漏洞利用代码和 PoC。\n"
                "支持按 CVE 编号、产品名称、漏洞类型搜索。\n"
                "用于验证漏洞的实际可利用性和获取 PoC 参考。\n"
                "注意：仅用于授权安全研究。\n\n"
                "示例:\n"
                "- CVE搜索: security_sploitus_search cve=CVE-2024-1234\n"
                "- 产品搜索: security_sploitus_search keyword='Apache Struts'\n"
                "- 类型搜索: security_sploitus_search keyword='Remote Code Execution'"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cve": {
                        "type": "string",
                        "description": "CVE 编号",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词（产品名/漏洞类型）",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "结果数量上限，默认10",
                    },
                },
                "required": [],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        cve = args.get("cve", "").strip().upper()
        keyword = args.get("keyword", "").strip()
        limit = args.get("limit", 10)

        if not cve and not keyword:
            return "请提供 CVE 编号或搜索关键词"

        query = cve or keyword

        lines = [
            f"Sploitus 漏洞利用搜索",
            f"查询: {query}",
            "",
        ]

        try:
            results = await self._search_exploitdb(query, limit)
            if results:
                lines.append(f"### Exploit-DB 结果 ({len(results)})")
                for i, r in enumerate(results[:limit], 1):
                    lines.append(f"**{i}. {r['title']}**")
                    lines.append(f"   - 类型: {r.get('type', 'N/A')}")
                    lines.append(f"   - 平台: {r.get('platform', 'N/A')}")
                    if r.get("verified"):
                        lines.append(f"   - 已验证: 是")
                    lines.append(f"   - 链接: {r.get('url', '')}")
                    lines.append("")
            else:
                lines.append("Exploit-DB: 未找到相关漏洞利用")

            # 尝试 Sploitus API
            sploitus_results = await self._search_sploitus(query, limit)
            if sploitus_results:
                lines.append(f"### Sploitus 结果 ({len(sploitus_results)})")
                for i, r in enumerate(sploitus_results[:limit], 1):
                    lines.append(f"**{i}. {r['title']}**")
                    lines.append(f"   - 来源: {r.get('source', 'N/A')}")
                    lines.append(f"   - 类型: {r.get('type', 'N/A')}")
                    lines.append(f"   - 链接: {r.get('url', '')}")
                    if r.get("description", ""):
                        lines.append(f"   - 描述: {r['description'][:200]}")
                    lines.append("")

            if not results and not sploitus_results:
                lines.append(f"未找到相关漏洞利用。\n建议: 手动访问 https://www.exploit-db.com/search?q={query}")

        except Exception as e:
            logger.error(f"Sploitus 搜索失败: {e}")
            lines.append(f"搜索过程中发生错误。请手动访问:")
            lines.append(f"  - https://www.exploit-db.com/search?q={query}")
            lines.append(f"  - https://sploitus.com/?query={query}")

        return "\n".join(lines)

    async def _search_exploitdb(self, query: str, limit: int) -> List[Dict]:
        """搜索 Exploit-DB"""
        results = []
        try:
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                response = await client.get(
                    EXPLOIT_DB_SEARCH,
                    params={"q": query},
                    headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"},
                )
                if response.status_code != 200:
                    return results

                soup = BeautifulSoup(response.text, "html.parser")
                for row in soup.select("table.exploit_list tbody tr")[:limit]:
                    cols = row.find_all("td")
                    if len(cols) < 5:
                        continue
                    link = row.find("a", href=True)
                    if not link:
                        continue
                    results.append(
                        {
                            "title": link.get_text(strip=True),
                            "url": f"https://www.exploit-db.com{link['href']}",
                            "type": cols[3].get_text(strip=True) if len(cols) > 3 else "N/A",
                            "platform": cols[4].get_text(strip=True) if len(cols) > 4 else "N/A",
                            "verified": "check" in row.get("class", ""),
                        }
                    )
        except Exception as e:
            logger.debug(f"Exploit-DB 搜索异常: {e}")
        return results

    async def _search_sploitus(self, query: str, limit: int) -> List[Dict]:
        """搜索 Sploitus API"""
        results = []
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                response = await client.get(
                    f"{SPLOITUS_API}/search",
                    params={"q": query, "type": "exploits"},
                    headers={"User-Agent": "Miya-SecurityNet/1.0"},
                )
                if response.status_code == 200:
                    data = response.json()
                    exploits = data.get("exploits", [])[:limit]
                    for exp in exploits:
                        results.append(
                            {
                                "title": exp.get("title", ""),
                                "url": f"{SPLOITUS_API}{exp.get('href', '')}",
                                "source": exp.get("source", "Sploitus"),
                                "type": exp.get("type", "exploit"),
                                "description": exp.get("description", ""),
                            }
                        )
        except Exception as e:
            logger.debug(f"Sploitus API 搜索异常: {e}")
        return results


def get_security_sploitus_search_tool():
    return SecuritySploitusSearchTool()

"""
Tavily AI 搜索引擎 - 弥娅核心模块

Tavily 是专为 AI 设计的搜索引擎，返回结构化、干净、可直接用于 LLM 的结果。
相比传统搜索引擎，Tavily 的优势：
1. 结果已过滤广告和垃圾内容
2. 返回正文摘要，无需额外抓取
3. 支持上下文感知搜索
4. 低延迟，高准确率

API: https://tavily.com/
"""

import logging
import os
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


class TavilyAISearch:
    """Tavily AI 搜索引擎"""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("TAVILY_API_KEY", "")
        self.base_url = "https://api.tavily.com/search"
        self.timeout = 15.0

        if not self.api_key:
            logger.warning("[Tavily] API Key 未配置，搜索功能将不可用")
            logger.warning("[Tavily] 请在 .env 中添加: TAVILY_API_KEY=tvly-xxx")

    def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "basic",
        include_answer: bool = True,
        include_raw_content: bool = False,
        include_domains: Optional[List[str]] = None,
        exclude_domains: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        执行 AI 搜索

        Args:
            query: 搜索查询
            max_results: 返回结果数 (1-20)
            search_depth: 搜索深度 ("basic" 或 "advanced")
            include_answer: 是否包含 AI 生成的直接答案
            include_raw_content: 是否包含完整正文内容
            include_domains: 限定搜索特定域名
            exclude_domains: 排除特定域名

        Returns:
            结构化搜索结果
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "Tavily API Key 未配置",
                "results": [],
            }

        payload = {
            "query": query,
            "api_key": self.api_key,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": include_answer,
            "include_raw_content": include_raw_content,
        }

        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains

        try:
            import ssl

            context = ssl.create_default_context()
            context.check_hostname = False
            context.verify_mode = ssl.CERT_NONE

            with httpx.Client(verify=context) as client:
                response = client.post(
                    self.base_url,
                    json=payload,
                    timeout=self.timeout,
                    headers={"Content-Type": "application/json"},
                )
                response.raise_for_status()
                data = response.json()

            # 解析结果
            results = []
            for item in data.get("results", []):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "content": item.get("content", ""),
                        "score": item.get("score", 0),
                        "raw_content": item.get("raw_content", ""),
                    }
                )

            return {
                "success": True,
                "query": query,
                "answer": data.get("answer", ""),
                "results": results,
                "result_count": len(results),
                "search_depth": search_depth,
            }

        except httpx.TimeoutException:
            logger.error(f"[Tavily] 搜索请求超时: {query}")
            return {
                "success": False,
                "error": "搜索请求超时",
                "results": [],
            }
        except httpx.HTTPStatusError as e:
            logger.error(
                f"[Tavily] HTTP 错误: {e.response.status_code} - {e.response.text}"
            )
            return {
                "success": False,
                "error": f"HTTP {e.response.status_code}",
                "results": [],
            }
        except Exception as e:
            logger.error(f"[Tavily] 搜索失败: {e}")
            return {
                "success": False,
                "error": str(e),
                "results": [],
            }

    def search_news(
        self,
        query: str,
        max_results: int = 5,
        days: int = 3,
    ) -> Dict[str, Any]:
        """
        搜索新闻

        Args:
            query: 搜索查询
            max_results: 返回结果数
            days: 搜索最近几天的新闻

        Returns:
            新闻搜索结果
        """
        return self.search(
            query=query,
            max_results=max_results,
            search_depth="advanced",
            include_answer=True,
            include_domains=[
                "news.sina.com.cn",
                "www.thepaper.cn",
                "www.163.com",
                "news.qq.com",
            ],
        )

    def format_for_ai(self, search_result: Dict[str, Any]) -> str:
        """
        将搜索结果格式化为 AI 友好的文本

        Args:
            search_result: search() 返回的结果

        Returns:
            格式化的文本
        """
        if not search_result.get("success"):
            return f"搜索失败: {search_result.get('error', '未知错误')}"

        parts = []

        # AI 直接答案
        if search_result.get("answer"):
            parts.append(f"💡 AI 摘要: {search_result['answer']}")

        # 详细结果
        if search_result.get("results"):
            parts.append(f"\n📚 详细来源 ({search_result['result_count']} 条):")
            for i, r in enumerate(search_result["results"], 1):
                parts.append(f"{i}. {r['title']}")
                parts.append(f"   链接: {r['url']}")
                if r.get("content"):
                    content = r["content"][:200]
                    parts.append(f"   摘要: {content}...")

        return "\n".join(parts)


def tavily_search_command(
    query: str,
    max_results: int = 5,
    search_depth: str = "basic",
    include_answer: bool = True,
) -> Dict[str, Any]:
    """
    Tavily 搜索命令统一接口

    Args:
        query: 搜索查询
        max_results: 返回结果数
        search_depth: 搜索深度 ("basic" 或 "advanced")
        include_answer: 是否包含 AI 生成的直接答案

    Returns:
        搜索结果
    """
    searcher = TavilyAISearch()
    result = searcher.search(
        query=query,
        max_results=max_results,
        search_depth=search_depth,
        include_answer=include_answer,
    )

    if result.get("success"):
        return {
            "status": "success",
            "query": result["query"],
            "answer": result.get("answer", ""),
            "results": [
                {
                    "title": r["title"],
                    "url": r["url"],
                    "content": r["content"],
                }
                for r in result["results"]
            ],
            "result_count": result["result_count"],
            "formatted": searcher.format_for_ai(result),
        }
    else:
        return {
            "status": "error",
            "error": result.get("error", "未知错误"),
            "query": query,
        }

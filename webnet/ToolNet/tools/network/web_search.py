"""
网络搜索增强工具 - 弥娅核心模块
支持多引擎搜索、结果去重、智能摘要
"""

import logging
import re
from typing import Any, Dict, List

import requests
from bs4 import BeautifulSoup

from core.system_config import get_api_url

logger = logging.getLogger(__name__)


class EnhancedWebSearch:
    """增强版网络搜索工具"""

    def __init__(self):
        # 搜索引擎配置（优先免费无密钥引擎）
        self.search_engines = {
            "baidu": {
                "name": "百度",
                "url": "https://www.baidu.com/s",
                "params": {"wd": "", "rn": 10},
                "key_required": False,
                "parser": "_parse_baidu_response",
                "method": "GET",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                },
            },
            "bing_cn": {
                "name": "必应中国",
                "url": "https://cn.bing.com/search",
                "params": {"q": "", "count": 10},
                "key_required": False,
                "parser": "_parse_bing_cn_response",
                "method": "GET",
                "headers": {
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                },
            },
            "duckduckgo_html": {
                "name": "DuckDuckGo HTML",
                "url": "https://html.duckduckgo.com/html/",
                "params": {"q": ""},
                "key_required": False,
                "parser": "_parse_duckduckgo_html_response",
                "method": "POST",
            },
            "duckduckgo_api": {
                "name": "DuckDuckGo API",
                "url": get_api_url("duckduckgo") or "https://api.duckduckgo.com/",
                "params": {"q": "", "format": "json"},
                "key_required": False,
                "parser": "_parse_duckduckgo_response",
                "method": "GET",
            },
            "serpapi": {
                "name": "SerpAPI",
                "url": get_api_url("serpapi") or "https://serpapi.com/search",
                "params": {"q": "", "engine": "google", "num": 10},
                "key_required": True,
                "api_key_env": "SERPAPI_API_KEY",
                "parser": "_parse_serpapi_response",
                "method": "GET",
            },
            "tavily": {
                "name": "Tavily AI",
                "url": "https://api.tavily.com/search",
                "params": {
                    "query": "",
                    "search_depth": "basic",
                    "include_answer": True,
                    "max_results": 5,
                },
                "key_required": True,
                "api_key_env": "TAVILY_API_KEY",
                "parser": "_parse_tavily_response",
                "method": "POST",
                "json_body": True,
            },
        }
        self._free_engines = ["baidu", "bing_cn", "duckduckgo_html", "duckduckgo_api"]

        # 如果配置了 TAVILY_API_KEY，优先使用 Tavily
        if self._has_tavily_key():
            self._free_engines.insert(0, "tavily")

    def search(
        self, query: str, engines: List[str] = None, num_results: int = 10
    ) -> List[Dict[str, Any]]:
        if engines is None:
            engines = self._free_engines
        all_results = []
        for engine in engines:
            try:
                engine_results = self._search_engine(query, engine, num_results)
                all_results.extend(engine_results)
                logger.info(f"{engine}引擎返回 {len(engine_results)} 个结果")
            except Exception as e:
                logger.error(f"{engine}引擎搜索失败: {e}")
        deduplicated = self._deduplicate_results(all_results)
        ranked = self._rank_results(deduplicated, query)
        logger.info(f"搜索完成，去重后 {len(ranked)} 个结果")
        return ranked

    def _has_tavily_key(self) -> bool:
        try:
            import os

            if os.getenv("TAVILY_API_KEY"):
                return True
            from dotenv import load_dotenv

            for rel_path in [
                os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "..", "config", ".env"
                ),
                os.path.join(os.getcwd(), "config", ".env"),
                os.path.join(os.getcwd(), ".env"),
            ]:
                if os.path.exists(rel_path):
                    load_dotenv(rel_path, override=True)
            return bool(os.getenv("TAVILY_API_KEY", ""))
        except Exception:
            return False

    def _search_engine(
        self, query: str, engine: str, num_results: int
    ) -> List[Dict[str, Any]]:
        if engine not in self.search_engines:
            logger.error(f"不支持的搜索引擎: {engine}")
            return []

        config = self.search_engines[engine]

        # 构建请求
        params = config["params"].copy()
        headers = config.get("headers", {}).copy()
        json_body = config.get("json_body", False)

        # 设置查询参数（兼容不同引擎的 query key）
        query_key = "query" if json_body else ("wd" if "wd" in params else "q")
        params[query_key] = query
        if "count" in params:
            params["count"] = num_results
        if "num" in params:
            params["num"] = num_results
        if "max_results" in params:
            params["max_results"] = min(num_results, 10)

        # 检查是否需要 API 密钥
        if config["key_required"]:
            import os

            api_key = os.environ.get(config["api_key_env"], "")
            if not api_key:
                from dotenv import load_dotenv

                config_env = os.path.join(
                    os.path.dirname(__file__), "..", "..", "..", "..", "config", ".env"
                )
                if os.path.exists(config_env):
                    load_dotenv(config_env)
                    api_key = os.environ.get(config["api_key_env"], "")
            if not api_key:
                logger.warning(f"{engine}引擎需要API密钥: {config['api_key_env']}")
                return []
            headers["Authorization"] = f"Bearer {api_key}"

        try:
            method = config.get("method", "GET")
            if method == "POST":
                if json_body:
                    response = requests.post(
                        config["url"], json=params, timeout=15, headers=headers
                    )
                else:
                    response = requests.post(
                        config["url"], data=params, timeout=10, headers=headers
                    )
            else:
                response = requests.get(
                    config["url"], params=params, timeout=10, headers=headers
                )
            response.raise_for_status()

            # 使用配置指定的解析器
            parser_name = config.get("parser")
            if parser_name and hasattr(self, parser_name):
                parser_fn = getattr(self, parser_name)
                results = parser_fn(
                    response.text
                    if method == "POST"
                    else response.json()
                    if response.headers.get("content-type", "").startswith(
                        "application/json"
                    )
                    else response.text
                )
            else:
                # 旧的硬编码解析逻辑（向后兼容）
                data = response.json()
                if engine == "duckduckgo_api":
                    results = self._parse_duckduckgo_response(data)
                elif engine == "serpapi":
                    results = self._parse_serpapi_response(data)
                else:
                    results = []

            return results

        except requests.exceptions.Timeout:
            logger.error(f"{engine}引擎请求超时")
            return []
        except Exception as e:
            logger.error(f"{engine}引擎请求失败: {e}")
            return []

    def _parse_duckduckgo_html_response(self, html: str) -> List[Dict[str, Any]]:
        """解析 DuckDuckGo HTML 搜索结果（免费，无需 API）"""
        results = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            for item in soup.select(".result"):
                title_el = item.select_one(".result__title a")
                snippet_el = item.select_one(".result__snippet")
                item.select_one(".result__url")
                if title_el:
                    results.append(
                        {
                            "title": title_el.get_text(strip=True),
                            "url": title_el.get("href", ""),
                            "snippet": snippet_el.get_text(strip=True)
                            if snippet_el
                            else "",
                            "source": "duckduckgo_html",
                        }
                    )
        except Exception as e:
            logger.error(f"DuckDuckGo HTML 解析失败: {e}")
        return results

    def _parse_duckduckgo_response(self, data) -> List[Dict[str, Any]]:
        """解析 DuckDuckGo API JSON 响应"""
        results = []
        try:
            if isinstance(data, str):
                import json

                data = json.loads(data)
            if isinstance(data, dict) and "RelatedTopics" in data:
                for item in data["RelatedTopics"][:10]:
                    if isinstance(item, dict):
                        results.append(
                            {
                                "title": item.get("Text", item.get("Result", "")),
                                "url": item.get("FirstURL", ""),
                                "snippet": item.get("Text", item.get("Result", ""))[
                                    :200
                                ],
                                "source": "duckduckgo_api",
                            }
                        )
        except Exception:
            pass
        return results

    def _parse_tavily_response(self, data: Dict) -> List[Dict[str, Any]]:
        """解析 Tavily AI 搜索响应"""
        results = []
        try:
            if isinstance(data, str):
                import json

                data = json.loads(data)
            for item in data.get("results", []):
                results.append(
                    {
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", item.get("snippet", ""))[:300],
                        "source": "tavily",
                    }
                )
            # 添加 AI 生成的答案
            if data.get("answer"):
                results.insert(
                    0,
                    {
                        "title": "AI 摘要",
                        "url": "",
                        "snippet": data["answer"][:500],
                        "source": "tavily_ai",
                    },
                )
        except Exception as e:
            logger.error(f"Tavily 解析失败: {e}")
        return results

    def _parse_baidu_response(self, html: str) -> List[Dict[str, Any]]:
        """解析百度 HTML 搜索结果（免费，无需 API，国内可用）"""
        results = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            for item in soup.select(".result, .c-container"):
                title_el = item.select_one("h3 a") or item.select_one(".t a")
                snippet_el = item.select_one(".c-abstract") or item.select_one(
                    ".c-span-last p"
                )
                if title_el:
                    url = str(title_el.get("href", ""))
                    if url and not url.startswith("http"):
                        url = "https://www.baidu.com" + url
                    results.append(
                        {
                            "title": title_el.get_text(strip=True),
                            "url": url,
                            "snippet": snippet_el.get_text(strip=True)[:200]
                            if snippet_el
                            else "",
                            "source": "baidu",
                        }
                    )
        except Exception as e:
            logger.error(f"百度解析失败: {e}")
        return results

    def _parse_bing_cn_response(self, html: str) -> List[Dict[str, Any]]:
        """解析必应中国 HTML 搜索结果（免费，国内可用）"""
        results = []
        try:
            soup = BeautifulSoup(html, "html.parser")
            for item in soup.select("li.b_algo"):
                title_el = item.select_one("h2 a")
                snippet_el = item.select_one(".b_caption p") or item.select_one("p")
                if title_el:
                    results.append(
                        {
                            "title": title_el.get_text(strip=True),
                            "url": title_el.get("href", ""),
                            "snippet": snippet_el.get_text(strip=True)[:200]
                            if snippet_el
                            else "",
                            "source": "bing_cn",
                        }
                    )
        except Exception as e:
            logger.error(f"必应中国解析失败: {e}")
        return results
        """解析DuckDuckGo API响应"""
        results = []

        if "Results" not in data or "MainResults" not in data:
            return results

        # 使用RelatedTopics作为备选
        results_list = data.get("Results", data.get("MainResults", []))

        for item in results_list[:10]:
            results.append(
                {
                    "title": item.get("Text", ""),
                    "url": item.get("FirstURL", ""),
                    "snippet": item.get("Text", ""),
                    "source": "duckduckgo_api",
                }
            )

        return results

    def _parse_serpapi_response(self, data: Dict) -> List[Dict[str, Any]]:
        """解析SerpAPI响应"""
        results = []

        if "organic_results" not in data:
            return results

        for item in data["organic_results"]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("link", ""),
                    "snippet": item.get("snippet", ""),
                    "displayUrl": item.get("link", ""),
                    "source": "serpapi",
                }
            )

        return results

    def _deduplicate_results(
        self, results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """搜索结果去重"""
        seen = set()
        deduplicated = []

        for result in results:
            # 使用URL作为唯一标识
            url = result.get("url", "")

            # 简化URL（去掉查询参数）
            clean_url = re.sub(r"\?.*", "", url)
            clean_url = clean_url.rstrip("/")

            if clean_url not in seen:
                seen.add(clean_url)
                deduplicated.append(result)

        return deduplicated

    def _rank_results(
        self, results: List[Dict[str, Any]], query: str
    ) -> List[Dict[str, Any]]:
        """搜索结果排序和评分"""
        query_keywords = set(query.lower().split())

        for result in results:
            title = result.get("title", "").lower()
            snippet = result.get("snippet", "").lower()
            url = result.get("url", "")

            # 计算相关性分数
            score = 0

            # 标题匹配
            title_match = sum(1 for kw in query_keywords if kw in title)
            score += title_match * 3

            # 摘要匹配
            snippet_match = sum(1 for kw in query_keywords if kw in snippet)
            score += snippet_match * 1

            # URL权威性加分
            if ".gov" in url or ".edu" in url:
                score += 2
            elif "wikipedia.org" in url:
                score += 1.5

            result["relevance_score"] = score

        # 按分数排序
        ranked = sorted(
            results, key=lambda x: x.get("relevance_score", 0), reverse=True
        )

        return ranked

    def generate_summary(
        self, results: List[Dict[str, Any]], max_length: int = 500
    ) -> str:
        """
        生成搜索结果摘要

        Args:
            results: 搜索结果列表
            max_length: 最大摘要长度

        Returns:
            摘要文本
        """
        if not results:
            return "未找到相关结果"

        # 提取关键信息
        top_results = results[:5]  # 只总结前5个

        summary_parts = []

        for i, result in enumerate(top_results, 1):
            title = result.get("title", "未知标题")
            snippet = result.get("snippet", "")

            # 截断长摘要
            if len(snippet) > 100:
                snippet = snippet[:97] + "..."

            summary_parts.append(f"{i}. {title}: {snippet}")

        # 组合摘要
        summary_text = "搜索结果摘要：\n" + "\n".join(summary_parts)

        # 如果超过最大长度，截断
        if len(summary_text) > max_length:
            summary_text = summary_text[: max_length - 3] + "..."

        return summary_text

    def search_with_ai_context(
        self, query: str, context: str, engines: List[str] = None
    ) -> Dict[str, Any]:
        """
        带AI上下文的搜索

        Args:
            query: 搜索查询
            context: 上下文信息（来自之前的对话）
            engines: 搜索引擎列表

        Returns:
            搜索结果和上下文相关性分析
        """
        # 执行搜索
        results = self.search(query, engines)

        # 分析结果与上下文的相关性
        context_keywords = set(re.findall(r"[\u4e00-\u9fff]{2,}", context))

        relevant_results = []
        for result in results:
            title = result.get("title", "")
            snippet = result.get("snippet", "")

            # 检查标题和摘要中是否包含上下文关键词
            relevance = 0
            for kw in context_keywords:
                if kw in title or kw in snippet:
                    relevance += 1

            result["context_relevance"] = relevance

            if relevance > 0:
                relevant_results.append(result)

        return {
            "搜索结果": relevant_results if relevant_results else results,
            "上下文关键词": list(context_keywords),
            "相关结果数": len(relevant_results),
        }


def search_command(
    query: str, engines: List[str] = None, options: Dict[str, Any] = None
) -> Dict[str, Any]:
    """
    搜索命令统一接口

    Args:
        query: 搜索查询
        engines: 搜索引擎列表
        options:
            {
                "num_results": 10,
                "deduplicate": True,
                "generate_summary": True,
                "with_context": "",
                "max_summary_length": 500
            }

    Returns:
        搜索结果
    """
    if options is None:
        options = {}

    searcher = EnhancedWebSearch()

    # 执行搜索
    if "with_context" in options:
        results = searcher.search_with_ai_context(
            query, options["with_context"], engines
        )
    else:
        results_list = searcher.search(query, engines, options.get("num_results", 10))

        # 去重
        if options.get("deduplicate", True):
            results_list = searcher._deduplicate_results(results_list)

        results = {"搜索结果": results_list}

    # 生成摘要
    if options.get("generate_summary", False):
        results["摘要"] = searcher.generate_summary(
            results_list, options.get("max_summary_length", 500)
        )

    # 添加元数据
    results["查询"] = query
    results["结果数"] = len(results_list)
    results["使用的引擎"] = engines or "全部"

    return results


# 别名，用于向后兼容
WebSearch = EnhancedWebSearch

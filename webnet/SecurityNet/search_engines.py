"""安全搜索引擎集成模块

从 PentAGI 移植，独立实现以下搜索引擎：
- DuckDuckGo Instant Answer API
- Google Custom Search (需 GOOGLE_API_KEY + GOOGLE_CX)
- Sploitus Exploit 搜索
- NVD / CVE 搜索 (NVD API v2.0)
- SearXNG 自托管搜索
- Tavily AI 搜索 (需 TAVILY_API_KEY)

所有引擎默认 graceful fallback：无需 API Key 即可使用的引擎（DuckDuckGo、Sploitus、NVD）
自动回退到可用的引擎。
"""

import asyncio
import json
import logging
import os
import re
import time
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from urllib.parse import quote_plus, urlencode

logger = logging.getLogger(__name__)

try:
    import aiohttp

    HAS_AIOHTTP = True
except ImportError:
    import requests

    HAS_AIOHTTP = False


# ─── 配置 ────────────────────────────────────────────
GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY", "")
GOOGLE_CX = os.environ.get("GOOGLE_CX", "")
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "")
SEARXNG_URL = os.environ.get("SEARXNG_URL", "http://localhost:8888")
REQUEST_TIMEOUT = int(os.environ.get("SEARCH_TIMEOUT", "15"))

# Rate limiting: minimum seconds between requests per engine
RATE_LIMITS: Dict[str, float] = {
    "google": 2.0,
    "duckduckgo": 1.0,
    "sploitus": 1.5,
    "nvd": 1.0,
    "searxng": 0.5,
    "tavily": 1.5,
}

_last_request: Dict[str, float] = {}


def _rate_limit(engine: str):
    """Apply rate limiting between requests"""
    now = time.time()
    last = _last_request.get(engine, 0)
    delay = RATE_LIMITS.get(engine, 1.0)
    if now - last < delay:
        time.sleep(delay - (now - last))
    _last_request[engine] = time.time()


# ─── DuckDuckGo ──────────────────────────────────────
async def search_duckduckgo(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """DuckDuckGo 匿名搜索 (Instant Answer API)

    无需 API Key，始终可用。
    """
    _rate_limit("duckduckgo")
    results: List[Dict[str, str]] = []

    try:
        url = "https://api.duckduckgo.com/"
        params = {
            "q": query,
            "format": "json",
            "no_html": 1,
            "skip_disambig": 1,
            "t": "miya_securitynet",
        }

        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=REQUEST_TIMEOUT) as resp:
                    if resp.status == 200:
                        data = await resp.json()
        else:
            import requests as req

            resp = req.get(url, params=params, timeout=REQUEST_TIMEOUT)
            data = resp.json() if resp.status_code == 200 else {}

        # Parse Abstract
        abstract = data.get("Abstract", "")
        if abstract:
            results.append(
                {
                    "title": data.get("Heading", query),
                    "snippet": abstract,
                    "url": data.get("AbstractURL", ""),
                    "source": "duckduckgo",
                }
            )

        # Parse RelatedTopics
        for topic in data.get("RelatedTopics", [])[: max_results - 1]:
            if isinstance(topic, dict) and "Text" in topic:
                results.append(
                    {
                        "title": topic.get("FirstURL", "").split("/")[-1].replace("_", " "),
                        "snippet": topic.get("Text", ""),
                        "url": topic.get("FirstURL", ""),
                        "source": "duckduckgo",
                    }
                )

        # Results via HTML scraping fallback
        if len(results) < 3:
            results.extend(await _duckduckgo_html_fallback(query, max_results - len(results)))

    except Exception as e:
        logger.debug(f"DuckDuckGo search failed: {e}")
        try:
            results.extend(await _duckduckgo_html_fallback(query, max_results))
        except Exception:
            pass

    return results[:max_results]


async def _duckduckgo_html_fallback(query: str, max_results: int) -> List[Dict[str, str]]:
    """DuckDuckGo HTML 搜索回退"""
    results = []
    try:
        url = "https://html.duckduckgo.com/html/"

        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, data={"q": query, "kl": "us-en"}, timeout=REQUEST_TIMEOUT) as resp:
                    html = await resp.text()
        else:
            import requests as req

            resp = req.post(url, data={"q": query, "kl": "us-en"}, timeout=REQUEST_TIMEOUT)
            html = resp.text

        # Simple HTML extraction
        link_pattern = re.compile(
            r'<a[^>]*class="result__a"[^>]*href="([^"]*)"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )
        snippet_pattern = re.compile(
            r'<a[^>]*class="result__snippet"[^>]*>(.*?)</a>',
            re.DOTALL | re.IGNORECASE,
        )

        links = link_pattern.findall(html)
        snippets = snippet_pattern.findall(html)

        for i, (url, title) in enumerate(links[:max_results]):
            snippet = snippets[i] if i < len(snippets) else ""
            snippet = re.sub(r"<[^>]+>", "", snippet).strip()
            results.append(
                {
                    "title": re.sub(r"<[^>]+>", "", title).strip(),
                    "snippet": snippet,
                    "url": url,
                    "source": "duckduckgo",
                }
            )
    except Exception as e:
        logger.debug(f"DuckDuckGo HTML fallback failed: {e}")

    return results


# ─── Google Custom Search ───────────────────────────
async def search_google(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Google Custom Search

    需要环境变量 GOOGLE_API_KEY 和 GOOGLE_CX。
    """
    if not GOOGLE_API_KEY or not GOOGLE_CX:
        logger.debug("Google Search: GOOGLE_API_KEY or GOOGLE_CX not set, falling back to DuckDuckGo")
        return await search_duckduckgo(query, max_results)

    _rate_limit("google")
    results = []

    try:
        url = "https://www.googleapis.com/customsearch/v1"
        params = {
            "key": GOOGLE_API_KEY,
            "cx": GOOGLE_CX,
            "q": query,
            "num": min(max_results, 10),
            "safe": "off",
        }

        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=REQUEST_TIMEOUT) as resp:
                    data = await resp.json()
        else:
            import requests as req

            resp = req.get(url, params=params, timeout=REQUEST_TIMEOUT)
            data = resp.json()

        for item in data.get("items", []):
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("snippet", ""),
                    "url": item.get("link", ""),
                    "source": "google",
                }
            )

    except Exception as e:
        logger.debug(f"Google search failed: {e}, falling back to DuckDuckGo")
        return await search_duckduckgo(query, max_results)

    return results[:max_results]


# ─── Sploitus ───────────────────────────────────────
async def search_sploitus(query: str, max_results: int = 15) -> List[Dict[str, str]]:
    """Sploitus Exploit 聚合搜索

    聚合 ExploitDB、Packet Storm、GitHub Security Advisories、CVE 等。
    """
    _rate_limit("sploitus")
    results = []

    try:
        url = "https://sploitus.com/api/search"
        params = {"query": query, "limit": max_results}

        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=REQUEST_TIMEOUT) as resp:
                    data = await resp.json()
        else:
            import requests as req

            resp = req.get(url, params=params, timeout=REQUEST_TIMEOUT)
            data = resp.json()

        for exploit in data.get("exploits", [])[:max_results]:
            results.append(
                {
                    "title": exploit.get("title", ""),
                    "snippet": exploit.get("cve", ""),
                    "url": exploit.get("href", ""),
                    "source": "sploitus",
                    "type": exploit.get("type", "exploit"),
                    "published": exploit.get("published", ""),
                }
            )

    except Exception as e:
        logger.debug(f"Sploitus search failed: {e}")

    return results


# ─── NVD / CVE ──────────────────────────────────────
async def search_cve(keyword: str, max_results: int = 20) -> List[Dict[str, str]]:
    """NVD (National Vulnerability Database) API v2.0 搜索"""
    _rate_limit("nvd")
    results = []

    try:
        # Check if keyword is already a CVE ID
        cve_pattern = re.compile(r"CVE-\d{4}-\d{4,}", re.IGNORECASE)
        cve_id = cve_pattern.search(keyword)
        if cve_id:
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={cve_id.group()}"
        else:
            encoded = quote_plus(keyword)
            url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={encoded}&resultsPerPage={min(max_results, 20)}"

        headers = {"User-Agent": "Miya-SecurityNet/1.0"}

        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers, timeout=REQUEST_TIMEOUT) as resp:
                    data = await resp.json()
        else:
            import requests as req

            resp = req.get(url, headers=headers, timeout=REQUEST_TIMEOUT)
            data = resp.json()

        for vuln in data.get("vulnerabilities", [])[:max_results]:
            cve_data = vuln.get("cve", {})
            cve_id_full = cve_data.get("id", "")
            descriptions = cve_data.get("descriptions", [])
            desc = next((d["value"] for d in descriptions if d.get("lang") == "en"), "")

            metrics = cve_data.get("metrics", {})
            cvss_v31 = metrics.get("cvssMetricV31", [{}])[0].get("cvssData", {})
            cvss_v30 = metrics.get("cvssMetricV30", [{}])[0].get("cvssData", {})
            cvss = cvss_v31.get("baseScore") or cvss_v30.get("baseScore") or "N/A"

            severity = cvss_v31.get("baseSeverity") or cvss_v30.get("baseSeverity") or "N/A"

            published = cve_data.get("published", "")
            results.append(
                {
                    "title": cve_id_full,
                    "snippet": desc[:500] if desc else "",
                    "url": f"https://nvd.nist.gov/vuln/detail/{cve_id_full}",
                    "source": "nvd",
                    "cvss": str(cvss),
                    "severity": severity,
                    "published": published,
                }
            )

    except Exception as e:
        logger.debug(f"NVD search failed: {e}")

    return results


# ─── SearXNG ────────────────────────────────────────
async def search_searxng(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """SearXNG 自托管元搜索引擎"""
    _rate_limit("searxng")
    results = []

    try:
        url = f"{SEARXNG_URL}/search"
        params = {
            "q": query,
            "format": "json",
            "categories": "general,it,security",
            "language": "auto",
        }

        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=REQUEST_TIMEOUT) as resp:
                    data = await resp.json()
        else:
            import requests as req

            resp = req.get(url, params=params, timeout=REQUEST_TIMEOUT)
            data = resp.json()

        for item in data.get("results", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("content", "")[:500],
                    "url": item.get("url", ""),
                    "source": "searxng",
                    "engine": item.get("engine", ""),
                }
            )

    except Exception as e:
        logger.debug(f"SearXNG search failed: {e}")

    return results


# ─── Tavily ─────────────────────────────────────────
async def search_tavily(query: str, max_results: int = 10) -> List[Dict[str, str]]:
    """Tavily AI 搜索（需 TAVILY_API_KEY）"""
    if not TAVILY_API_KEY:
        logger.debug("Tavily: TAVILY_API_KEY not set")
        return []

    _rate_limit("tavily")
    results = []

    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "max_results": max_results,
            "search_depth": "advanced",
            "include_domains": [],
            "exclude_domains": [],
        }

        if HAS_AIOHTTP:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, timeout=REQUEST_TIMEOUT) as resp:
                    data = await resp.json()
        else:
            import requests as req

            resp = req.post(url, json=payload, timeout=REQUEST_TIMEOUT)
            data = resp.json()

        for item in data.get("results", [])[:max_results]:
            results.append(
                {
                    "title": item.get("title", ""),
                    "snippet": item.get("content", "")[:500],
                    "url": item.get("url", ""),
                    "source": "tavily",
                    "score": item.get("score", 0),
                }
            )

    except Exception as e:
        logger.debug(f"Tavily search failed: {e}")

    return results


# ─── 统一搜索接口 ───────────────────────────────────
SEARCH_ENGINES = {
    "duckduckgo": search_duckduckgo,
    "google": search_google,
    "sploitus": search_sploitus,
    "nvd": search_cve,
    "cve": search_cve,
    "searxng": search_searxng,
    "tavily": search_tavily,
}


async def search(
    query: str,
    engines: Optional[List[str]] = None,
    max_results: int = 10,
) -> Dict[str, Any]:
    """统一搜索引擎接口

    Args:
        query: 搜索关键词
        engines: 搜索引擎列表，默认 ["duckduckgo", "sploitus", "nvd"]
        max_results: 每个引擎的最大结果数

    Returns:
        {"results": [...], "engines": {"duckduckgo": 10, ...}, "query": "...", "timestamp": "..."}
    """
    if engines is None:
        engines = ["duckduckgo", "sploitus", "nvd"]

    all_results = []
    engine_counts = {}

    for engine in engines:
        func = SEARCH_ENGINES.get(engine)
        if not func:
            continue
        try:
            results = await func(query, max_results)
            all_results.extend(results)
            engine_counts[engine] = len(results)
        except Exception as e:
            logger.debug(f"Search engine {engine} failed: {e}")
            engine_counts[engine] = 0

    return {
        "results": all_results,
        "engines": engine_counts,
        "query": query,
        "total": len(all_results),
        "timestamp": datetime.now().isoformat(),
    }


async def security_search(query: str, max_results: int = 15) -> List[Dict[str, str]]:
    """安全专用搜索：自动查询 Sploitus + NVD + DuckDuckGo"""
    results = []
    # Sploitus (exploits)
    sploitus_results = await search_sploitus(query, max_results)
    results.extend(sploitus_results)
    # NVD (vulnerabilities)
    cve_results = await search_cve(query, max_results)
    results.extend(cve_results)
    # DuckDuckGo (general)
    if len(results) < 5:
        ddg_results = await search_duckduckgo(query, max_results)
        results.extend(ddg_results)
    return results


def search_sync(query: str, engines: Optional[List[str]] = None, max_results: int = 10) -> Dict[str, Any]:
    """同步搜索接口（内部使用 asyncio）"""
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # 在已有事件循环中，创建新任务
            import concurrent.futures

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(lambda: asyncio.run(search(query, engines, max_results)))
                return future.result()
        return asyncio.run(search(query, engines, max_results))
    except RuntimeError:
        return asyncio.run(search(query, engines, max_results))

"""
CVE / NVD 漏洞情报引擎

查询 NVD + EPSS + 多源漏洞情报。
所有静态数据从 config/security_net.yaml 读取。
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

import httpx

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_vuln_lookup_config
except ImportError:
    get_vuln_lookup_config = lambda: {}

_CFG = get_vuln_lookup_config()
_API_BASE = _CFG.get("nvd_api_base", "https://services.nvd.nist.gov/rest/json/cves/2.0")
_REQ_TIMEOUT = _CFG.get("request_timeout", 30.0)
_MAX_LIMIT = _CFG.get("max_limit", 20)
_DESC_LEN = _CFG.get("description_max_length", 300)
_OFFLINE_DB = _CFG.get("offline_knowledge", {})
_OFFLINE_MSG = _CFG.get("offline_fallback_message", "")

logger = logging.getLogger(__name__)

CVSS_VECTOR_LABELS = {
    "AV": "攻击向量",
    "AC": "复杂度",
    "PR": "权限要求",
    "UI": "用户交互",
    "S": "作用域",
    "C": "机密性",
    "I": "完整性",
    "A": "可用性",
}
CVSS_VALUES = {
    "AV": {"N": ("网络", 4), "A": ("相邻", 3), "L": ("本地", 2), "P": ("物理", 1)},
    "AC": {"L": ("低", 1), "H": ("高", 2)},
    "PR": {"N": ("无", 0), "L": ("低", 1), "H": ("高", 2)},
    "UI": {"N": ("无", 0), "R": ("需要", 1)},
    "S": {"U": ("不变", 0), "C": ("变化", 1)},
    "C": {"N": ("无", 0), "L": ("低", 1), "H": ("高", 2)},
    "I": {"N": ("无", 0), "L": ("低", 1), "H": ("高", 2)},
    "A": {"N": ("无", 0), "L": ("低", 1), "H": ("高", 2)},
}
SEV_LABEL = {"CRITICAL": "严重", "HIGH": "高危", "MEDIUM": "中危", "LOW": "低危"}


class SecurityVulnLookupTool(BaseTool):
    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_vuln_lookup",
            "description": (
                "漏洞情报引擎。搜索 CVE 详情，含 CVSS 评分、EPSS 预测、影响版本、补丁链接。\n"
                "示例: security_vuln_lookup cve=CVE-2024-1234\n"
                "或 security_vuln_lookup keyword=Apache severity=critical"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "cve": {"type": "string", "description": "CVE 编号"},
                    "keyword": {"type": "string", "description": "产品/版本关键词"},
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low"]},
                    "limit": {"type": "integer", "description": "结果数上限"},
                },
                "required": [],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        cve = args.get("cve", "").strip().upper()
        keyword = args.get("keyword", "").strip()
        severity = args.get("severity", "").strip().lower()
        limit = min(args.get("limit", 10), _MAX_LIMIT)

        if not cve and not keyword:
            return "请提供 CVE 编号或搜索关键词"

        try:
            if cve:
                items = await self._fetch_by_cve(cve, limit)
            else:
                result = await self._fetch_by_keyword(keyword, limit)
                total = result.get("total", 0)
                items = result.get("items", [])
        except httpx.TimeoutException:
            return self._fallback(cve or keyword, "API 超时")
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                return f"未找到: {cve or keyword}"
            return self._fallback(cve or keyword, f"API {e.response.status_code}")
        except Exception as e:
            logger.warning(f"NVD 请求失败: {e}")
            return self._fallback(cve or keyword, "网络不可用")

        if severity:
            items = [v for v in items if self._match_sev(v, severity)]

        if not items:
            return f"未找到相关漏洞: {cve or keyword}"

        # 批量获取 EPSS
        epss_map = await self._fetch_epss_batch([self._extract_cve_id(v) for v in items[:limit]])

        return self._render(items[:limit], cve or keyword, epss_map, total if not cve else 1)

    async def _fetch_by_cve(self, cve_id: str, limit: int) -> List[Dict]:
        async with httpx.AsyncClient(timeout=_REQ_TIMEOUT) as cli:
            resp = await cli.get(
                _API_BASE,
                params={"cveId": cve_id},
                headers={"User-Agent": "Miya-SecurityNet/1.0"},
            )
            resp.raise_for_status()
            return resp.json().get("vulnerabilities", [])

    async def _fetch_by_keyword(self, kw: str, limit: int) -> Dict[str, Any]:
        async with httpx.AsyncClient(timeout=_REQ_TIMEOUT) as cli:
            resp = await cli.get(
                _API_BASE,
                params={"keywordSearch": kw, "resultsPerPage": limit},
                headers={"User-Agent": "Miya-SecurityNet/1.0"},
            )
            resp.raise_for_status()
            data = resp.json()
            return {"items": data.get("vulnerabilities", []), "total": data.get("totalResults", 0)}

    async def _fetch_epss_batch(self, cve_ids: List[str]) -> Dict[str, Dict]:
        """批量获取 EPSS 评分 (FIRST.org API)"""
        if not cve_ids:
            return {}
        clean_ids = [cid for cid in cve_ids if cid and cid != "UNKNOWN"]
        if not clean_ids:
            return {}
        try:
            async with httpx.AsyncClient(timeout=15.0) as cli:
                resp = await cli.get(
                    "https://api.first.org/data/v1/epss",
                    params={"cve": ",".join(clean_ids)},
                )
                if resp.status_code == 200:
                    data = resp.json()
                    results = {}
                    for item in data.get("data", []):
                        results[item.get("cve", "")] = {
                            "epss": float(item.get("epss", "0")),
                            "percentile": float(item.get("percentile", "0")),
                        }
                    return results
        except Exception as e:
            logger.debug(f"EPSS 获取失败: {e}")
        return {}

    def _extract_cve_id(self, vuln: Dict) -> str:
        return vuln.get("cve", {}).get("id", "")

    def _match_sev(self, vuln: Dict, target: str) -> bool:
        data = vuln.get("cve", vuln)
        for mt in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            for item in data.get("metrics", {}).get(mt, []):
                sev = item.get("cvssData", {}).get("baseSeverity", "").lower()
                if sev == target:
                    return True
        return False

    def _parse_cvss(self, metrics: Dict) -> Tuple[Dict, float, str]:
        """解析 CVSS 数据，返回 (vector_dict, base_score, severity)"""
        for mt in ("cvssMetricV31", "cvssMetricV30", "cvssMetricV2"):
            for item in metrics.get(mt, []):
                cvss = item.get("cvssData", {})
                vector = cvss.get("vectorString", "")
                score = cvss.get("baseScore", 0)
                sev = cvss.get("baseSeverity", "?")
                parsed = {}
                if vector:
                    for part in vector.split("/"):
                        if ":" in part:
                            k, v = part.split(":", 1)
                            parsed[k] = v
                return parsed, score, sev
        return {}, 0, "?"

    def _render(self, items: List[Dict], query: str, epss_map: Dict, total: int) -> str:
        lines = [
            "漏洞情报报告",
            f"查询: {query}",
            f"匹配: {len(items)} / {total} 条",
            f"时间: {datetime.now():%Y-%m-%d %H:%M:%S}",
            "",
            "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━",
            "",
        ]
        for i, vuln in enumerate(items, 1):
            data = vuln.get("cve", vuln)
            cve_id = data.get("id", "UNKNOWN")
            desc = ""
            for d in data.get("descriptions", []):
                if d.get("lang") == "en":
                    desc = d.get("value", "")
                    break
            if len(desc) > _DESC_LEN:
                desc = desc[: _DESC_LEN - 3] + "..."

            published = data.get("published", "")[:10]
            last_modified = data.get("lastModified", "")[:10]

            # ── CVSS 评分 ─────────────────────────
            vector, score, sev = self._parse_cvss(data.get("metrics", {}))
            sev_cn = SEV_LABEL.get(sev.upper(), sev)
            risk_bar = self._risk_bar(score)

            lines.append(f"## {i}. {cve_id}")
            lines.append(f"  评分: {score} / 10  ({sev_cn})")
            lines.append(f"  风险: {risk_bar}")

            # ── EPSS ──────────────────────────────
            epss_data = epss_map.get(cve_id, {})
            if epss_data:
                epss_val = epss_data.get("epss", 0)
                epss_pct = epss_data.get("percentile", 0)
                lines.append(f"  EPSS: {epss_val:.4f} (超越 {epss_pct * 100:.1f}% 的漏洞)")
            else:
                lines.append(f"  EPSS: 暂无数据")

            lines.append(f"  发布: {published}  更新: {last_modified}")
            lines.append(f"  描述: {desc}")
            lines.append("")

            # ── CVSS 向量拆解 ────────────────────
            if vector:
                lines.append(f"  CVSS 向量分解:")
                for key in ("AV", "AC", "PR", "UI", "S", "C", "I", "A"):
                    val = vector.get(key, "?")
                    label = CVSS_VECTOR_LABELS.get(key, key)
                    val_info = CVSS_VALUES.get(key, {}).get(val, (val, 0))
                    val_cn = val_info[0] if isinstance(val_info, tuple) else val_info
                    impact = val_info[1] if isinstance(val_info, tuple) else 0
                    bar = "█" * impact if impact > 0 else "—"
                    lines.append(f"    {label:6s} = {val} ({val_cn:4s})  {bar}")
                lines.append("")

            # ── 影响版本 (CPE) ────────────────────
            configs = data.get("configurations", data.get("cveTags", []))
            if configs:
                cpes = self._extract_cpes(configs)
                if cpes:
                    lines.append(f"  影响产品/版本:")
                    for cpe in cpes[:5]:
                        lines.append(f"    · {cpe}")
                    if len(cpes) > 5:
                        lines.append(f"    共 {len(cpes)} 个")
                    lines.append("")

            # ── References + 补丁 ──────────────────
            refs = data.get("references", [])
            if refs:
                urls = []
                patches = []
                advisories = []
                for r in refs:
                    url = r.get("url", "")
                    tags = r.get("tags", [])
                    if not url:
                        continue
                    if any(t in ("Patch", "Vendor Advisory") for t in tags):
                        patches.append((url, tags))
                    elif any(t in ("Third Party Advisory",) for t in tags):
                        advisories.append(url)
                    else:
                        urls.append(url)

                if patches:
                    lines.append(f"  补丁/官方公告:")
                    for p, tags in patches[:3]:
                        tag_str = ", ".join(tags) if tags else "补丁"
                        lines.append(f"    · [{tag_str}] {p[:80]}")
                    lines.append("")

                if urls:
                    lines.append(f"  参考资料:")
                    for u in urls[:3]:
                        lines.append(f"    · {u[:80]}")
                    lines.append("")

            lines.append("━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
            lines.append("")

            if i >= _MAX_LIMIT:
                break

        lines.append("*NVD + FIRST.org EPSS  |  nvd.nist.gov*")
        return "\n".join(lines)

    def _risk_bar(self, score: float) -> str:
        if not score:
            return "暂无评分"
        n = min(10, max(1, int(score)))
        if score >= 9:
            return f"[严重] {'█' * n}{'░' * (10 - n)}"
        elif score >= 7:
            return f"[高危] {'█' * n}{'░' * (10 - n)}"
        elif score >= 4:
            return f"[中危] {'█' * n}{'░' * (10 - n)}"
        else:
            return f"[低危] {'█' * n}{'░' * (10 - n)}"

    def _extract_cpes(self, configurations: List) -> List[str]:
        """从 config 块中提取 CPE 字符串"""
        results = []
        try:
            for node in configurations:
                if "nodes" in node:
                    for sub in node["nodes"]:
                        for match in sub.get("cpeMatch", []):
                            criteria = match.get("criteria", "")
                            if criteria:
                                ver_start = match.get("versionStartIncluding", "")
                                ver_end = match.get("versionEndExcluding", "")
                                info = criteria.replace("cpe:2.3:", "")
                                if ver_start:
                                    info += f" (>= {ver_start})"
                                if ver_end:
                                    info += f" (< {ver_end})"
                                results.append(info)
                elif "cpeMatch" in node:
                    for match in node.get("cpeMatch", []):
                        results.append(match.get("criteria", ""))
        except Exception:
            pass
        return results[:10]

    def _fallback(self, query: str, reason: str = "") -> str:
        if not _OFFLINE_DB:
            return _OFFLINE_MSG or f"无法查询: {query}  |  nvd.nist.gov"
        ql = query.lower()
        for key, info in _OFFLINE_DB.items():
            if key in ql:
                return (
                    f"离线知识库 (API: {reason})\n查询: {query}\n\n{info}\n\n实时数据: nvd.nist.gov  |  FIRST.org/epss"
                )
        return _OFFLINE_MSG or f"无法查询: {query}"


def get_security_vuln_lookup_tool():
    return SecurityVulnLookupTool()

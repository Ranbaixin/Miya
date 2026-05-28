"""
SecurityNet 配置加载器

所有安全工具从此模块读取配置。
支持 YAML 文件加载和缓存。
"""

from __future__ import annotations

import yaml
from pathlib import Path
from typing import Any, Dict, List, Optional

_CONF: Optional[Dict[str, Any]] = None
_CONFIG_PATH = Path(__file__).parent / "security_net.yaml"


def _load() -> Dict[str, Any]:
    global _CONF
    if _CONF is not None:
        return _CONF
    try:
        if _CONFIG_PATH.exists():
            _CONF = yaml.safe_load(_CONFIG_PATH.read_text(encoding="utf-8")) or {}
        else:
            _CONF = {}
    except Exception:
        _CONF = {}
    return _CONF


def reload() -> Dict[str, Any]:
    global _CONF
    _CONF = None
    return _load()


def get_section(section: str, default: Any = None) -> Any:
    cfg = _load()
    return cfg.get(section, default)


def get_value(key: str, default: Any = None) -> Any:
    """支持点号分隔的嵌套键，如 'port_scanner.common_ports'"""
    cfg = _load()
    for k in key.split("."):
        if isinstance(cfg, dict):
            cfg = cfg.get(k)
        else:
            return default
    return cfg if cfg is not None else default


# ─── 便捷访问接口 ────────────────────────────


def get_orchestrator_config() -> Dict[str, Any]:
    return get_section("orchestrator", {})


def get_port_scanner_config() -> Dict[str, Any]:
    return get_section("port_scanner", {})


def get_common_ports() -> Dict[int, str]:
    return get_value("port_scanner.common_ports", {})


def get_subdomain_enum_config() -> Dict[str, Any]:
    return get_section("subdomain_enum", {})


def get_default_subdomains() -> List[str]:
    return get_value("subdomain_enum.default_subdomains", [])


def get_deep_subdomains() -> List[str]:
    return get_value("subdomain_enum.deep_subdomains", [])


def get_http_headers_config() -> Dict[str, Any]:
    return get_section("http_headers", {})


def get_vuln_lookup_config() -> Dict[str, Any]:
    return get_section("vuln_lookup", {})


def get_offline_knowledge() -> Dict[str, str]:
    return get_value("vuln_lookup.offline_knowledge", {})


def get_web_vuln_scanner_config() -> Dict[str, Any]:
    return get_section("web_vuln_scanner", {})


def get_dir_brute_config() -> Dict[str, Any]:
    return get_section("dir_brute", {})


def get_nmap_scan_config() -> Dict[str, Any]:
    return get_section("nmap_scan", {})


def get_online_asset_config() -> Dict[str, Any]:
    return get_section("online_asset", {})


def get_ctf_workflow_config() -> Dict[str, Any]:
    return get_section("ctf_workflow", {})


def get_tool_index_config() -> Dict[str, Any]:
    return get_section("tool_index", {})


def get_sandbox_config() -> Dict[str, Any]:
    return get_section("sandbox", {})


def get_sploitus_config() -> Dict[str, Any]:
    return get_section("sploitus", {})


def get_dns_enum_config() -> Dict[str, Any]:
    return get_section("dns_enum", {})


def get_ssl_cert_config() -> Dict[str, Any]:
    return get_section("ssl_cert", {})

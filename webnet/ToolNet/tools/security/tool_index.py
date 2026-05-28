"""
安全工具知识库查询工具

集成 Online_tools 的 308+ 安全工具目录。
支持按类别、名称、用途搜索推荐的安全工具。
"""

import json
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_tool_index_config
except ImportError:
    get_tool_index_config = lambda: {}

_CFG = get_tool_index_config()
CATEGORY_TOOLS = _CFG.get("tools", {})
TOOL_CATEGORIES = {cat: [t["name"] for t in CATEGORY_TOOLS.get(cat, [])] for cat in CATEGORY_TOOLS}
MAX_PREVIEW = _CFG.get("max_preview", 3)

CATEGORY_TOOLS: Dict[str, List[Dict[str, str]]] = {
    "信息收集": [
        {"name": "OneForAll", "desc": "功能强大的子域名收集工具，支持多种数据源"},
        {"name": "EHole", "desc": "红队重点攻击系统指纹探测工具"},
        {"name": "gogo", "desc": "面向红队的自动化引擎扫描工具"},
        {"name": "naabu", "desc": "快速的端口扫描工具 (Go)"},
        {"name": "nmap", "desc": "经典网络扫描器和安全审计工具"},
        {"name": "masscan", "desc": "超快速互联网级端口扫描器"},
        {"name": "fscan", "desc": "内网综合扫描工具,适合内网渗透"},
        {"name": "kscan", "desc": "轻量级资产探测和漏洞扫描"},
        {"name": "goby", "desc": "自动化网络空间测绘和安全评估平台"},
        {"name": "dirsearch", "desc": "Web目录爆破工具 (Python)"},
        {"name": "DnsX", "desc": "快速多用途DNS工具包"},
        {"name": "Search_Viewer", "desc": "Fofa/Shodan 可视化搜索工具"},
        {"name": "appshunter", "desc": "APP资产信息收集工具"},
    ],
    "漏洞扫描": [
        {"name": "nuclei", "desc": "基于模板的快速漏洞扫描器,社区6000+模板"},
        {"name": "xray", "desc": "Web漏洞检测代理,支持POC自定义"},
        {"name": "afrog", "desc": "高性能漏洞扫描器,支持POC编排"},
        {"name": "poc-bomber", "desc": "POC/EXP批量检测工具"},
        {"name": "scaninfo", "desc": "开源、轻量、快速、跨平台的红队扫描工具"},
        {"name": "Full-Scanner", "desc": "全面信息收集+漏洞扫描一体工具"},
    ],
    "漏洞利用": [
        {"name": "sqlmap", "desc": "自动化SQL注入检测和利用工具"},
        {"name": "ShiroAttack2", "desc": "Shiro反序列化漏洞综合利用工具"},
        {"name": "JNDIExploit", "desc": "JNDI注入利用工具,支持多种协议"},
        {"name": "FastjsonScan", "desc": "Fastjson漏洞检测利用工具"},
        {"name": "Struts2", "desc": "Struts2系列漏洞检测利用工具"},
        {"name": "WeblogicTool", "desc": "Weblogic漏洞综合利用工具"},
        {"name": "LiqunKit", "desc": "Java代码审计+自动化审计和漏洞利用"},
        {"name": "dalfox", "desc": "快速XSS参数分析和扫描工具"},
        {"name": "XSStrike", "desc": "高级XSS检测套件"},
        {"name": "POC-bomber", "desc": "基于POC的漏洞批量验证工具"},
        {"name": "MYExploit", "desc": "综合漏洞利用框架"},
    ],
    "Webshell": [
        {"name": "冰蝎", "desc": "动态二进制加密Webshell管理工具"},
        {"name": "哥斯拉 Godzilla", "desc": "JavaWebshell管理,支持冰蝎/哥斯拉内存马"},
        {"name": "蚁剑 AntSword", "desc": "开源跨平台Webshell管理工具"},
        {"name": "天蝎", "desc": "新一代Webshell管理器"},
    ],
    "密码破解": [
        {"name": "hashcat", "desc": "最快最先进密码恢复工具 (GPU加速)"},
        {"name": "hydra", "desc": "网络登录暴力破解工具,支持50+协议"},
        {"name": "john", "desc": "John the Ripper 离线密码破解"},
        {"name": "pydictor", "desc": "强大实用的黑客暴力破解字典生成工具"},
        {"name": "jwt_tool", "desc": "JSON Web Token 测试工具包"},
    ],
    "安全防御": [
        {"name": "D盾", "desc": "Webshell查杀+安全防护一体化工具"},
        {"name": "河马", "desc": "内存马专杀和Webshell查杀工具"},
        {"name": "火绒剑", "desc": "安全分析工具利器(进程/网络/注册表)"},
        {"name": "BlueTeamTools", "desc": "蓝队工具箱:日志清洗/溯源/攻击IP分析"},
        {"name": "Sysmon", "desc": "Windows系统监控服务"},
        {"name": "FindAll", "desc": "内网资产发现工具"},
        {"name": "TrafficEye", "desc": "开源流量分析监控系统"},
    ],
    "取证分析": [
        {"name": "Volatility", "desc": "高级内存取证框架"},
        {"name": "volatility3", "desc": "Volatility 3 新版内存取证框架"},
        {"name": "Wireshark", "desc": "网络协议分析器"},
        {"name": "tshark", "desc": "Wireshark命令行版本"},
        {"name": "binwalk", "desc": "固件分析工具"},
        {"name": "foremost", "desc": "文件恢复和分离工具"},
        {"name": "exiftool", "desc": "元数据读写工具"},
        {"name": "Steghide", "desc": "图片/音频隐写工具"},
    ],
    "代理抓包": [
        {"name": "BurpSuite", "desc": "Web应用安全测试平台"},
        {"name": "Fiddler", "desc": "Web调试代理,支持HTTPS解密"},
        {"name": "Charles", "desc": "HTTP代理/监视器/反向代理"},
        {"name": "mitmproxy", "desc": "交互式TLS拦截代理"},
        {"name": "Wireshark", "desc": "网络协议分析器"},
    ],
    "逆向工程": [
        {"name": "Ghidra", "desc": "NSA开源的软件逆向工程框架"},
        {"name": "IDA Free", "desc": "交互式反汇编器(免费版)"},
        {"name": "x64dbg", "desc": "Windows开源x64/x32调试器"},
        {"name": "dnSpy", "desc": ".NET调试器和汇编编辑器"},
        {"name": "jadx", "desc": "Dex to Java反编译器"},
        {"name": "jd-gui", "desc": "Java反编译图形工具"},
        {"name": "GDA", "desc": "Android APK/DEX 分析工具"},
    ],
    "CTF专项": [
        {"name": "CyberChef", "desc": "数据编码/解码/加密/解密在线工具"},
        {"name": "pwntools", "desc": "CTF和漏洞利用开发框架 (Python)"},
        {"name": "zsteg", "desc": "PNG/BMP隐写检测工具"},
        {"name": "RsaCtfTool", "desc": "RSA攻击工具,支持多种攻击方式"},
        {"name": "yafu", "desc": "大整数分解工具"},
        {"name": "checksec", "desc": "二进制保护机制检查工具"},
        {"name": "ROPgadget", "desc": "ROP链搜索工具"},
        {"name": "libc-database", "desc": "libc版本离线识别工具"},
    ],
}


class SecurityToolIndexTool(BaseTool):
    """安全工具知识库查询工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_tool_index",
            "description": (
                "安全工具知识库查询工具。\n"
                "当用户需要推荐安全工具、了解特定工具用途、\n"
                "或按类别浏览 308+ 安全工具时使用此工具。\n"
                "覆盖信息收集、漏洞扫描/利用、Webshell、密码破解、\n"
                "取证分析、逆向工程、安全防御等 15 个类别。\n\n"
                "示例:\n"
                "- 按类别浏览: security_tool_index category=信息收集\n"
                "- 搜索工具: security_tool_index keyword=nmap\n"
                "- 列出类别: security_tool_index"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "工具类别，如 '信息收集'/'漏洞扫描'/'密码破解' 等，不填则列出所有类别",
                    },
                    "keyword": {
                        "type": "string",
                        "description": "搜索关键词，在工具名称和描述中搜索",
                    },
                },
                "required": [],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        category = args.get("category", "").strip()
        keyword = args.get("keyword", "").strip().lower()

        if keyword:
            return self._search_tools(keyword)

        if category:
            return self._show_category(category)

        return self._list_categories()

    def _list_categories(self) -> str:
        lines = ["安全工具知识库 — 类别总览", ""]
        for cat, tools in CATEGORY_TOOLS.items():
            lines.append(f"### {cat} ({len(tools)} 个工具)")
            for t in tools[:MAX_PREVIEW]:
                lines.append(f"  - {t.get('name', '')}: {t.get('desc', '')[:60]}")
            if len(tools) > MAX_PREVIEW:
                lines.append(f"  ... 共 {len(tools)} 个工具，使用 security_tool_index category={cat} 查看全部")
            lines.append("")
        lines.append("使用方式:")
        lines.append("  - 按类别: security_tool_index category=信息收集")
        lines.append("  - 搜索: security_tool_index keyword=nmap")
        return "\n".join(lines)

    def _show_category(self, category: str) -> str:
        tools = CATEGORY_TOOLS.get(category)
        if not tools:
            for cat, ts in CATEGORY_TOOLS.items():
                if category in cat or cat in category:
                    tools = ts
                    category = cat
                    break
        if not tools:
            return f"未找到类别 '{category}'。可用类别: {', '.join(CATEGORY_TOOLS.keys())}"
        lines = [f"安全工具 — {category}", ""]
        lines.append("| 工具 | 描述 |")
        lines.append("|------|------|")
        for t in tools:
            lines.append(f"| {t.get('name', '')} | {t.get('desc', '')} |")
        lines.append("")
        lines.append(f"共 {len(tools)} 个工具")
        lines.append(f"*数据来源: Online_tools 安全工具目录 (308+) + 社区推荐*")
        return "\n".join(lines)

    def _search_tools(self, keyword: str) -> str:
        results = []
        for cat, tools in CATEGORY_TOOLS.items():
            for t in tools:
                name = t.get("name", "").lower()
                desc = t.get("desc", "").lower()
                if keyword in name or keyword in desc:
                    results.append({**t, "category": cat})
        if not results:
            return f"未找到与 '{keyword}' 相关的工具\n\n试试搜索: nmap, burp, sqlmap, 子域名, 扫描"
        lines = [f"工具搜索: {keyword} — 找到 {len(results)} 个结果", ""]
        for r in results:
            lines.append(f"**[{r.get('category', '')}] {r.get('name', '')}**")
            lines.append(f"  {r.get('desc', '')}")
            lines.append("")
        lines.append("*更多工具请访问: security_tool_index category=<类别>*")
        return "\n".join(lines)


def get_security_tool_index_tool():
    return SecurityToolIndexTool()

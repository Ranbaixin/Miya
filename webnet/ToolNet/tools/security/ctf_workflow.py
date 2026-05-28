"""
CTF 解题 + BugBounty 工作流工具

支持：
- CTF 比赛辅助（Web/Crypto/Pwn/Forensics/Rev/Misc/OSINT 指引）
- BugBounty 漏洞赏金工作流指引
- 常见靶场题目模式识别
"""

import logging
from typing import Any, Dict, List

from webnet.ToolNet.base import BaseTool, ToolContext

try:
    from config.security_net_loader import get_ctf_workflow_config
except ImportError:
    get_ctf_workflow_config = lambda: {}

_CFG = get_ctf_workflow_config()
CTF_CATEGORIES = _CFG.get("categories", {})
BUGBOUNTY_FLOW = _CFG.get("bugbounty_flow", {})
CATEGORY_ADVICE = _CFG.get("category_specific_advice", {})
    "web": {
        "name": "Web安全",
        "tools": ["BurpSuite", "sqlmap", "dirsearch", "nuclei"],
        "common_techniques": [
            "SQL注入 (联合查询/盲注/时间盲注/)",
            "XSS (反射型/存储型/DOM型)",
            "SSRF (内网探测/云元数据/Redis攻击)",
            "文件上传 (前端绕过/Content-Type/文件头/条件竞争)",
            "反序列化 (Java/PHP/Python Pickle)",
            "SSTI (Jinja2/Twig/FreeMarker)",
            "命令注入 (管道符/反引号/$IFS绕过)",
            "XXE (外带数据/内网探测)",
            "认证绕过 (JWT伪造/Session劫持)",
        ],
    },
    "crypto": {
        "name": "密码学",
        "tools": ["CyberChef", "RsaCtfTool", "yafu", "hashcat"],
        "common_techniques": [
            "古典密码 (凯撒/维吉尼亚/栅栏/培根)",
            "RSA攻击 (共模/小指数/维纳攻击)",
            "分组密码 (CBC字节翻转/Padding Oracle)",
            "哈希长度扩展攻击",
            "格密码 (LLL算法)",
        ],
    },
    "pwn": {
        "name": "二进制漏洞",
        "tools": ["pwntools", "ghidra", "gdb", "checksec", "ROPgadget"],
        "common_techniques": [
            "栈溢出 (ret2text/ret2libc/ret2syscall)",
            "格式化字符串 (任意读写/GOT覆写)",
            "堆利用 (UAF/Fastbin/Tcache)",
            "整数溢出 (符号/宽度溢出)",
            "ROP链构造",
        ],
    },
    "forensics": {
        "name": "数字取证",
        "tools": ["Volatility", "binwalk", "foremost", "exiftool", "Steghide"],
        "common_techniques": [
            "内存取证 (进程列表/注册表/网络连接)",
            "磁盘取证 (文件恢复/MFT分析)",
            "流量分析 (Wireshark/tshark 过滤)",
            "隐写分析 (LSB/频域/元数据)",
            "日志分析 (Web/系统/安全日志)",
        ],
    },
    "rev": {
        "name": "逆向工程",
        "tools": ["Ghidra", "IDA Free", "jadx", "x64dbg", "dnSpy"],
        "common_techniques": [
            "静态分析 (反汇编/反编译)",
            "动态调试 (断点/内存修改)",
            "脱壳去花 (反反调试/反虚拟机)",
            "算法逆向 (加密/压缩/校验)",
        ],
    },
    "misc": {
        "name": "杂项",
        "tools": ["CyberChef", "zsteg", "foremost", "checklist"],
        "common_techniques": [
            "编码解码 (Base64/Hex/Unicode/Morse)",
            "协议分析 (自定义协议/PCAP)",
            "Python沙箱逃逸",
            "游戏逆向 (Unity/IL2CPP)",
        ],
    },
    "osint": {
        "name": "开源情报",
        "tools": ["Sherlock", "theHarvester", "Maltego CE"],
        "common_techniques": [
            "社交账号搜索",
            "域名/WHOIS 反查",
            "图片EXIF/GPS分析",
            "证书透明度日志",
            "Google Dork",
        ],
    },
}

BUGBOUNTY_FLOW = {
    "title": "BugBounty 漏洞赏金工作流",
    "phases": [
        {
            "phase": 1,
            "name": "侦察",
            "actions": [
                "子域名枚举 → subfinder/amass/OneForAll",
                "端口扫描 → nmap/masscan/naabu",
                "技术指纹 → Wappalyzer/WhatWeb/BuiltWith",
                "URL采集 → waybackurls/gau/katana",
            ],
        },
        {
            "phase": 2,
            "name": "映射与分析",
            "actions": [
                "目录枚举 → dirsearch/ffuf/gobuster",
                "参数发现 → paramspider/arjun",
                "JS分析 → LinkFinder/SecretFinder",
                "API端点收集 → Swagger/GraphQL",
            ],
        },
        {
            "phase": 3,
            "name": "漏洞发现",
            "actions": [
                "自动化扫描 → nuclei/xray/yakit (注意流量)",
                "手动测试 → SQL注入/XSS/SSRF/任意文件读取",
                "业务逻辑 → IDOR/竞态条件/支付绕过",
                "配置错误 → CORS/Cloud Storage/.git泄露",
            ],
        },
        {
            "phase": 4,
            "name": "利用验证",
            "actions": [
                "概念证明 → 最小化PoC，不破坏数据",
                "影响评估 → 确定漏洞实际危害范围",
                "截图留证 → 清晰展示漏洞利用过程",
            ],
        },
        {
            "phase": 5,
            "name": "报告撰写",
            "actions": [
                "标题 + 严重程度 (CVSS评分)",
                "复现步骤 (清晰、可操作)",
                "影响说明 (业务/数据/合规)",
                "修复建议 (具体、可行)",
            ],
        },
    ],
}


class SecurityCTFWorkflowTool(BaseTool):
    """CTF + BugBounty 工作流工具"""

    @property
    def config(self) -> Dict[str, Any]:
        return {
            "name": "security_ctf_workflow",
            "description": (
                "CTF 解题辅助 + BugBounty 漏洞赏金工作流工具。\n"
                "当用户需要 CTF 比赛解题指引、特定类型题目的攻略，\n"
                "或需要 BugBounty 渗透测试方法论时使用此工具。\n"
                "支持 7 种 CTF 类别和 5 阶段 BugBounty 流程。\n"
                "注意：仅提供方法论指引，不提供自动化解题。\n\n"
                "示例:\n"
                "- CTF攻略: security_ctf_workflow type=ctf category=web\n"
                "- 赏金流程: security_ctf_workflow type=bugbounty\n"
                "- 列出类别: security_ctf_workflow type=list"
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "type": {
                        "type": "string",
                        "enum": ["ctf", "bugbounty", "list"],
                        "description": "工作流类型: ctf/BugBounty攻略 或 list 查看所有类别",
                    },
                    "category": {
                        "type": "string",
                        "description": "CTF 类别 (type=ctf 时必填): web/crypto/pwn/forensics/rev/misc/osint",
                    },
                    "challenge": {
                        "type": "string",
                        "description": "具体的题目描述或遇到的具体问题",
                    },
                },
                "required": [],
            },
        }

    async def execute(self, args: Dict[str, Any], context: ToolContext) -> str:
        workflow_type = args.get("type", "list")
        category = args.get("category", "").strip().lower()
        challenge = args.get("challenge", "").strip()

        if workflow_type == "list":
            return self._list_categories()

        if workflow_type == "bugbounty":
            return self._bugbounty_workflow()

        if workflow_type == "ctf":
            if not category or category not in CTF_CATEGORIES:
                return f"请选择有效的 CTF 类别:\n{self._list_categories()}"
            return self._ctf_guide(category, challenge)

        return f"未知工作流类型: {workflow_type}"

    def _list_categories(self) -> str:
        lines = ["CTF 题目类别 + BugBounty 工作流:", ""]
        for key, cat in CTF_CATEGORIES.items():
            lines.append(f"  **{key}** - {cat['name']}")
            lines.append(f"    推荐工具: {', '.join(cat['tools'])}")
        lines.append("")
        lines.append(f"  **bugbounty** - {BUGBOUNTY_FLOW['title']}")
        lines.append("")
        lines.append("使用方式:")
        lines.append("  - CTF攻略: security_ctf_workflow type=ctf category=web")
        lines.append("  - 赏金流程: security_ctf_workflow type=bugbounty")
        return "\n".join(lines)

    def _ctf_guide(self, category: str, challenge: str) -> str:
        cat = CTF_CATEGORIES.get(category, {})
        tools_list = cat.get("tools", [])
        techniques = cat.get("techniques", [])
        lines = [
            f"CTF {cat.get('name', category)} 解题指引",
            "",
            f"### 推荐工具",
            ", ".join(tools_list) if tools_list else "查看 CTF 专项工具列表",
            "",
            f"### 常见考点与技术",
            "",
        ]
        for tech in techniques:
            lines.append(f"- {tech}")
        lines.append("")
        lines.append("### 解题思路")
        lines.append("")
        lines.append("1. **信息收集** — 查看题目描述、源码、附件，确定考点方向")
        lines.append("2. **环境搭建** — 部署本地环境，安装必要工具")
        lines.append("3. **逐步分析** — 从最简单的角度开始尝试，逐步深化")
        lines.append("4. **记录过程** — 记录尝试的每个步骤和结果")
        lines.append("5. **反思总结** — 解题后复盘，理解原理")
        if challenge:
            lines.append("")
            lines.append(f"### 关于你的题目: {challenge[:100]}")
            lines.append("")
            advice = CATEGORY_ADVICE.get(category, "请尝试上述常见技术，从最简单的开始。")
            lines.append(advice)
        lines.append("")
        if tools_list:
            lines.append(f"*提示：弥娅可通过 Docker 沙箱执行 {', '.join(tools_list[:3])} 等进行实际解题*")
        return "\n".join(lines)

    def _bugbounty_workflow(self) -> str:
        title = BUGBOUNTY_FLOW.get("title", "BugBounty 工作流")
        phases = BUGBOUNTY_FLOW.get("phases", [])
        principles = BUGBOUNTY_FLOW.get("principles", [])
        lines = [f"# {title}", ""]
        for phase in phases:
            lines.append(f"## Phase {phase.get('phase', '?')}: {phase.get('name', '')}")
            lines.append("")
            for action in phase.get("actions", []):
                lines.append(f"- {action}")
            lines.append("")
        lines.append("---")
        lines.append("### 重要原则")
        lines.append("")
        for p in principles:
            lines.append(f"{principles.index(p) + 1}. **{p.split('—')[0].strip()}** — {p.split('—')[1].strip() if '—' in p else p}")
        lines.append("")
        lines.append("*弥娅 SecurityNet 的全面扫描、端口扫描、目录爆破等工具可用于自动化部分侦察过程*")
        return "\n".join(lines)


CATEGORY_SPECIFIC_ADVICE = {
    "web": "优先检查：1) 页面源代码和JS文件中的注释/API端点\n2) URL 参数和 Cookie 中的特殊值\n3) HTTP 响应头是否有异常\n4) 尝试常见的弱口令和默认凭据\n5) 检查 robots.txt 和 sitemap.xml",
    "crypto": "优先检查：1) 题目提供的加密算法和参数\n2) 是否有已知的数学攻击方法\n3) 密文是否有模式（重复、长度）\n4) 尝试用 CyberChef 进行快速编码解码\n5) 考虑侧信道信息（时间、文件名）",
    "pwn": "优先检查：1) checksec 查看保护机制\n2) 分析程序逻辑找溢出点\n3) 用 gdb/pwndbg 调试确认偏移\n4) 检查 libc 版本（libc database查找）\n5) 注意 one_gadget 条件",
    "forensics": "优先检查：1) file 命令确认文件类型\n2) strings 提取可读字符串\n3) binwalk 提取嵌套文件\n4) exiftool 查看元数据\n5) 搜索常见隐藏数据特征（PK头/Zip头/PNG尾）",
    "rev": "优先检查：1) file 确认文件类型和架构\n2) strings 查找关键字符串（flag/密码/提示）\n3) 搜索硬编码常量和密钥\n4) 用反编译器查看主逻辑\n5) 识别常见加密算法（AES/RSA/自定义）",
    "misc": "优先检查：1) 从最简单的方法开始（不是所有题目都是复杂加密）\n2) 检查所有附件中的隐藏信息\n3) 尝试不同的编码解码工具\n4) 搜索题目名称和描述中的提示\n5) 查看比赛平台的历史 writeup",
    "osint": "优先检查：1) Google Image Search 搜索图片\n2) 查看图片 EXIF/GPS 数据\n3) 社交媒体平台搜索用户名\n4) Wayback Machine 查看历史版本\n5) 证书透明度日志 (crt.sh)",
}


def get_security_ctf_workflow_tool():
    return SecurityCTFWorkflowTool()

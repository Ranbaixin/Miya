"""
CTF 工具智能匹配器 — 根据题目类型和描述自动推荐最佳工具链

移植自 Online_tools 的 CTFToolManager（200+ 工具按 25 类别智能匹配）
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# 25 个 CTF 工具类别 + 关键词映射
CATEGORY_TOOLS: Dict[str, List[str]] = {
    "web_recon": ["nmap", "httpx", "katana", "gau", "waybackurls", "whatweb", "wapiti"],
    "web_fuzz": ["ffuf", "dirsearch", "gobuster", "feroxbuster", "wfuzz", "arjun"],
    "sql_injection": ["sqlmap", "nosqlmap", "sqlninja", "bbqsql"],
    "xss": ["dalfox", "xsstrike", "xsser", "knoxss"],
    "ssrf": ["ssrfmap", "gopherus", "ssrfuzz"],
    "command_injection": ["commix", "crlfuzz", "tplmap"],
    "file_upload": ["fuxploider", "uploadscanner", "burp_collaborator"],
    "deserialization": ["ysoserial", "phpggc", "jexboss", "marshalsec"],
    "crypto_classic": ["cyberchef", "dcode", "quipqiup", "rsactftool", "xortool"],
    "crypto_aes": ["aes-keyschedule", "padding_oracle_tool", "trivium_crack"],
    "crypto_rsa": ["rsactftool", "rsa-wiener-attack", "boneh_durfee", "coppersmith"],
    "crypto_hash": ["hashcat", "john", "hashid", "name-that-hash"],
    "crypto_ecc": ["ecctool", "pohlig-hellman", "sage_ecc"],
    "reverse_elf": ["ghidra", "ida_free", "radare2", "binary_ninja", "rizin", "angr", "pwntools"],
    "reverse_pe": ["x64dbg", "dnspy", "ilspy", "pebear", "pestudio", "detectiteasy"],
    "reverse_android": ["jadx", "apktool", "dex2jar", "frida", "objection"],
    "reverse_firmware": ["binwalk", "firmadyne", "firmwalker", "qemu-user"],
    "pwn_stack": ["pwntools", "ropper", "ROPgadget", "checksec", "pwndbg", "gef"],
    "pwn_heap": ["heapviewer", "heapinspect", "pwntools_heap", "angr"],
    "pwn_fmt": ["fmtstr_pwn", "pwntools_fmt", "fmt_fuzz"],
    "pwn_kernel": ["pwnkernel", "linux_exploit_suggester", "kernel_exploit_framework"],
    "forensics_disk": ["sleuthkit", "autopsy", "volatility3", "bulk_extractor", "photorec"],
    "forensics_memory": ["volatility3", "rekall", "winpmem", "avml", "lime"],
    "steganography": ["steghide", "zsteg", "binwalk", "exiftool", "stegsolve", "foremost", "outguess"],
    "misc_osint": ["theharvester", "sherlock", "maigret", "holehe", "phoneinfoga"],
}

# 关键词 → 类别映射
KEYWORD_CATEGORY: Dict[str, str] = {
    # Web
    "sql": "sql_injection",
    "注入": "sql_injection",
    "injection": "sql_injection",
    "xss": "xss",
    "跨站": "xss",
    "script": "xss",
    "ssrf": "ssrf",
    "服务端请求": "ssrf",
    "命令注入": "command_injection",
    "command": "command_injection",
    "rce": "command_injection",
    "上传": "file_upload",
    "upload": "file_upload",
    "文件": "file_upload",
    "反序列化": "deserialization",
    "deserialize": "deserialization",
    "serialize": "deserialization",
    "http": "web_recon",
    "web": "web_recon",
    "网页": "web_recon",
    "目录": "web_fuzz",
    "fuzz": "web_fuzz",
    "爆破": "web_fuzz",
    # Crypto
    "rsa": "crypto_rsa",
    "aes": "crypto_aes",
    "des": "crypto_classic",
    "sha": "crypto_hash",
    "md5": "crypto_hash",
    "hash": "crypto_hash",
    "哈希": "crypto_hash",
    "ecc": "crypto_ecc",
    "椭圆": "crypto_ecc",
    "曲线": "crypto_ecc",
    "古典": "crypto_classic",
    "凯撒": "crypto_classic",
    "维吉尼亚": "crypto_classic",
    "密码": "crypto_classic",
    "加密": "crypto_classic",
    "crypto": "crypto_classic",
    # Reverse
    "elf": "reverse_elf",
    "linux": "reverse_elf",
    "so": "reverse_elf",
    "pe": "reverse_pe",
    "exe": "reverse_pe",
    "dll": "reverse_pe",
    "windows": "reverse_pe",
    "apk": "reverse_android",
    "android": "reverse_android",
    "安卓": "reverse_android",
    "固件": "reverse_firmware",
    "firmware": "reverse_firmware",
    "bin": "reverse_firmware",
    "ida": "reverse_elf",
    "ghidra": "reverse_elf",
    "逆向": "reverse_elf",
    "reverse": "reverse_elf",
    # Pwn
    "栈": "pwn_stack",
    "overflow": "pwn_stack",
    "rop": "pwn_stack",
    "ret2": "pwn_stack",
    "堆": "pwn_heap",
    "heap": "pwn_heap",
    "free": "pwn_heap",
    "格式化字符串": "pwn_fmt",
    "fmt": "pwn_fmt",
    "printf": "pwn_fmt",
    "内核": "pwn_kernel",
    "kernel": "pwn_kernel",
    "驱动": "pwn_kernel",
    "pwn": "pwn_stack",
    "二进制": "pwn_stack",
    # Forensics
    "取证": "forensics_disk",
    "forensics": "forensics_disk",
    "磁盘": "forensics_disk",
    "内存": "forensics_memory",
    "memory": "forensics_memory",
    "dump": "forensics_memory",
    "流量": "forensics_disk",
    "pcap": "forensics_disk",
    "wireshark": "forensics_disk",
    # Stegano
    "隐写": "steganography",
    "steg": "steganography",
    "图片": "steganography",
    "音频": "steganography",
    "mp3": "steganography",
    "png": "steganography",
    # Misc
    "osint": "misc_osint",
    "情报": "misc_osint",
    "社工": "misc_osint",
}


class CTFToolMatcher:
    """根据题目类型/描述智能推荐 CTF 工具链"""

    def __init__(self):
        self._cache: Dict[str, List[str]] = {}

    def match_by_category(self, category: str) -> List[str]:
        """按 CTF 类别直接返回工具列表"""
        cat = category.lower().replace("-", "_")
        for key in CATEGORY_TOOLS:
            if key == cat or cat in key:
                return CATEGORY_TOOLS[key]
        # 模糊匹配
        for key in CATEGORY_TOOLS:
            if cat.startswith(key.split("_")[0]):
                return CATEGORY_TOOLS[key]
        return CATEGORY_TOOLS.get("web_recon", [])

    def match_by_description(self, description: str) -> Dict[str, List[str]]:
        """根据题目描述智能匹配工具类别和工具

        Returns:
            {category: [tool1, tool2, ...]}
        """
        text = description.lower()
        if text in self._cache:
            return self._cache[text]

        matched_categories: Dict[str, int] = {}
        for keyword, category in KEYWORD_CATEGORY.items():
            if keyword in text:
                matched_categories[category] = matched_categories.get(category, 0) + 1

        if not matched_categories:
            return {"web_recon": CATEGORY_TOOLS["web_recon"]}

        # 按匹配次数排序
        result = {}
        for category, count in sorted(matched_categories.items(), key=lambda x: -x[1]):
            if category in CATEGORY_TOOLS:
                result[category] = CATEGORY_TOOLS[category]

        self._cache[text] = result
        return result

    def get_tool_chain(self, description: str) -> List[str]:
        """获取推荐的工具链（有序列表）"""
        matched = self.match_by_description(description)
        chain = []
        for tools in matched.values():
            chain.extend(tools[:3])  # 每类取前 3 个
        return list(dict.fromkeys(chain))[:8]  # 去重，最多 8 个

    def get_all_categories(self) -> List[str]:
        return sorted(CATEGORY_TOOLS.keys())

    def search_tools(self, keyword: str) -> List[str]:
        """按关键词搜索工具"""
        results = []
        for category, tools in CATEGORY_TOOLS.items():
            if keyword.lower() in category.lower():
                results.extend(tools)
            else:
                results.extend(t for t in tools if keyword.lower() in t.lower())
        return list(dict.fromkeys(results))


_ctf_matcher: Optional[CTFToolMatcher] = None


def get_ctf_matcher() -> CTFToolMatcher:
    global _ctf_matcher
    if _ctf_matcher is None:
        _ctf_matcher = CTFToolMatcher()
    return _ctf_matcher

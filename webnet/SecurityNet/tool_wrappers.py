"""安全工具命令行包装器 — MCP 风格工具注册

将 100+ 安全工具注册为可直接调用的命令行包装器。
弥娅原生，不依赖 HexStrike 服务器。

每个工具就是一个 command builder + subprocess 执行器。
AI Agent 通过 terminal 工具间接调用这些工具。
"""

import asyncio
import json
import logging
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

# 默认超时
DEFAULT_TIMEOUT = int(os.environ.get("SECURITY_TOOL_TIMEOUT", "300"))

# ─── Tool Definition ─────────────────────────────────


@dataclass
class ToolCommand:
    """单个安全工具命令定义"""

    name: str
    description: str
    category: str
    command_template: str  # 例如: "nmap -sV -p {ports} {target}"
    required_params: List[str] = field(default_factory=list)
    optional_params: Dict[str, str] = field(default_factory=dict)  # param → default_value
    timeout: int = DEFAULT_TIMEOUT
    dependencies: List[str] = field(default_factory=list)  # 需要安装的工具

    def build_command(self, params: Dict[str, Any]) -> Tuple[str, Optional[str]]:
        """构建最终命令

        Returns:
            (command_string, error_message_or_none)
        """
        # 检查必需参数
        missing = [p for p in self.required_params if p not in params or not params[p]]
        if missing:
            return "", f"缺少必需参数: {', '.join(missing)}"

        # 合并默认参数
        full_params = {**self.optional_params, **params}

        # 替换模板中的参数
        cmd = self.command_template
        for key, value in full_params.items():
            cmd = cmd.replace(f"{{{key}}}", str(value) if value is not None else "")

        # 清理未替换的占位符（可选参数未提供时）
        cmd = re.sub(r"\{[^}]+\}", "", cmd)
        # 清理多余空格
        cmd = re.sub(r"\s+", " ", cmd).strip()

        return cmd, None


# ─── 检查工具是否安装 ───────────────────────────────


def is_tool_installed(tool_name: str) -> bool:
    """检查命令行工具是否在 PATH 中"""
    return shutil.which(tool_name) is not None


async def execute_tool(
    tool: ToolCommand,
    params: Dict[str, Any],
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """执行安全工具命令

    Returns:
        {"success": bool, "stdout": str, "stderr": str, "command": str, "timeout": int, "elapsed": float}
    """
    cmd, error = tool.build_command(params)
    if error:
        return {"success": False, "error": error, "command": ""}

    if tool.dependencies:
        for dep in tool.dependencies:
            if not is_tool_installed(dep):
                return {
                    "success": False,
                    "error": f"依赖工具未安装: {dep}。请先安装 {dep} 后再试。",
                    "command": cmd,
                }

    timeout = timeout or tool.timeout
    start = datetime.now()

    try:
        proc = await asyncio.create_subprocess_shell(
            cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd or ".",
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        elapsed = (datetime.now() - start).total_seconds()

        stdout_str = stdout.decode("utf-8", errors="replace").strip()
        stderr_str = stderr.decode("utf-8", errors="replace").strip()

        return {
            "success": proc.returncode == 0 or bool(stdout_str),
            "stdout": stdout_str[:50000],
            "stderr": stderr_str[:10000],
            "returncode": proc.returncode,
            "command": cmd,
            "timeout": timeout,
            "elapsed": round(elapsed, 2),
        }
    except asyncio.TimeoutError:
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "success": False,
            "error": f"命令超时 ({timeout}s)",
            "command": cmd,
            "timeout": timeout,
            "elapsed": round(elapsed, 2),
        }
    except Exception as e:
        return {
            "success": False,
            "error": f"执行失败: {e}",
            "command": cmd,
        }


def execute_tool_sync(
    tool: ToolCommand,
    params: Dict[str, Any],
    cwd: Optional[str] = None,
    timeout: Optional[int] = None,
) -> Dict[str, Any]:
    """同步执行工具"""
    cmd, error = tool.build_command(params)
    if error:
        return {"success": False, "error": error, "command": ""}

    timeout = timeout or tool.timeout
    start = datetime.now()

    try:
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=timeout,
            cwd=cwd or ".",
        )
        elapsed = (datetime.now() - start).total_seconds()
        return {
            "success": result.returncode == 0 or bool(result.stdout.strip()),
            "stdout": result.stdout[:50000],
            "stderr": result.stderr[:10000],
            "returncode": result.returncode,
            "command": cmd,
            "timeout": timeout,
            "elapsed": round(elapsed, 2),
        }
    except subprocess.TimeoutExpired:
        return {
            "success": False,
            "error": f"命令超时 ({timeout}s)",
            "command": cmd,
        }
    except Exception as e:
        return {"success": False, "error": f"执行失败: {e}", "command": cmd}


# ─── 100+ Tool Registry ─────────────────────────────

TOOLS: Dict[str, ToolCommand] = {}


def _register(tool: ToolCommand):
    TOOLS[tool.name] = tool
    return tool


# ── Phase 1: Network Reconnaissance ─────────────────

_register(
    ToolCommand(
        name="nmap",
        description="经典网络扫描器 — 端口 + 服务版本 + OS 检测",
        category="network_recon",
        command_template="nmap -sV -sC -T4 {target} {extra_args}",
        required_params=["target"],
        optional_params={"extra_args": ""},
        timeout=300,
        dependencies=["nmap"],
    )
)

_register(
    ToolCommand(
        name="nmap-advanced",
        description="高级 Nmap — NSE 脚本 + 全端口 + 激进模式",
        category="network_recon",
        command_template="nmap -sV -sC -O -p- -T4 -A --script=vuln,exploit,auth,default {target} {extra_args}",
        required_params=["target"],
        optional_params={"extra_args": ""},
        timeout=600,
        dependencies=["nmap"],
    )
)

_register(
    ToolCommand(
        name="nmap-quick",
        description="快速 nmap — 仅 TOP 1000 端口",
        category="network_recon",
        command_template="nmap -sV --top-ports 1000 -T4 {target}",
        required_params=["target"],
        timeout=120,
        dependencies=["nmap"],
    )
)

_register(
    ToolCommand(
        name="masscan",
        description="超高速端口扫描器 — 互联网级",
        category="network_recon",
        command_template="masscan {target} -p{ports} --rate={rate} {extra_args}",
        required_params=["target"],
        optional_params={"ports": "1-65535", "rate": "1000", "extra_args": ""},
        timeout=180,
        dependencies=["masscan"],
    )
)

_register(
    ToolCommand(
        name="rustscan",
        description="超快端口扫描器 (Rust 实现)",
        category="network_recon",
        command_template="rustscan -a {target} --ulimit 5000 -- -sV -sC {extra_args}",
        required_params=["target"],
        optional_params={"extra_args": ""},
        timeout=120,
        dependencies=["rustscan"],
    )
)

_register(
    ToolCommand(
        name="autorecon",
        description="自动化侦察 — 多工具联动",
        category="network_recon",
        command_template="autorecon {target} --only-scans-dir {output_dir} {extra_args}",
        required_params=["target"],
        optional_params={"output_dir": os.path.join(tempfile.gettempdir(), "autorecon"), "extra_args": ""},
        timeout=600,
        dependencies=["autorecon"],
    )
)

_register(
    ToolCommand(
        name="enum4linux-ng",
        description="Windows/Samba 枚举 (增强版)",
        category="network_recon",
        command_template="enum4linux-ng -A {target} {extra_args}",
        required_params=["target"],
        optional_params={"extra_args": ""},
        timeout=120,
        dependencies=["enum4linux-ng"],
    )
)

_register(
    ToolCommand(
        name="smbmap",
        description="SMB 共享枚举",
        category="network_recon",
        command_template="smbmap -H {target} {extra_args}",
        required_params=["target"],
        optional_params={"extra_args": "-u guest"},
        timeout=60,
        dependencies=["smbmap"],
    )
)

_register(
    ToolCommand(
        name="netexec",
        description="网络执行/喷射框架",
        category="network_recon",
        command_template="netexec smb {target} {extra_args}",
        required_params=["target"],
        optional_params={"extra_args": "--shares"},
        timeout=120,
        dependencies=["netexec"],
    )
)

_register(
    ToolCommand(
        name="responder",
        description="LLMNR/NBT-NS/mDNS 投毒",
        category="network_recon",
        command_template="responder -I {interface} {extra_args}",
        required_params=["interface"],
        optional_params={"extra_args": "-wrf"},
        timeout=300,
        dependencies=["responder"],
    )
)


# ── Phase 2: Web / Subdomain Recon ──────────────────

_register(
    ToolCommand(
        name="subfinder",
        description="子域名发现",
        category="subdomain",
        command_template="subfinder -d {domain} -o {output_file} {extra_args}",
        required_params=["domain"],
        optional_params={"output_file": os.path.join(tempfile.gettempdir(), "subfinder.txt"), "extra_args": ""},
        timeout=300,
        dependencies=["subfinder"],
    )
)

_register(
    ToolCommand(
        name="amass",
        description="深度子域名枚举",
        category="subdomain",
        command_template="amass enum -d {domain} -o {output_file} {extra_args}",
        required_params=["domain"],
        optional_params={"output_file": os.path.join(tempfile.gettempdir(), "amass.txt"), "extra_args": "-passive"},
        timeout=600,
        dependencies=["amass"],
    )
)

_register(
    ToolCommand(
        name="httpx",
        description="HTTP 服务探测",
        category="web_recon",
        command_template="httpx -l {input_file} -title -tech-detect -status-code -follow-redirects -o {output_file} {extra_args}",
        required_params=["input_file"],
        optional_params={"output_file": os.path.join(tempfile.gettempdir(), "httpx_output.txt"), "extra_args": ""},
        timeout=120,
        dependencies=["httpx"],
    )
)

_register(
    ToolCommand(
        name="httpx-url",
        description="HTTP 服务探测（单 URL）",
        category="web_recon",
        command_template="httpx -u {url} -title -tech-detect -status-code -follow-redirects {extra_args}",
        required_params=["url"],
        optional_params={"extra_args": ""},
        timeout=60,
        dependencies=["httpx"],
    )
)

_register(
    ToolCommand(
        name="katana",
        description="JS 爬虫 — 端点发现",
        category="web_recon",
        command_template="katana -u {url} -d {depth} -jc -kf all -o {output_file} {extra_args}",
        required_params=["url"],
        optional_params={
            "depth": "3",
            "output_file": os.path.join(tempfile.gettempdir(), "katana.txt"),
            "extra_args": "",
        },
        timeout=300,
        dependencies=["katana"],
    )
)

_register(
    ToolCommand(
        name="gau",
        description="获取已知 URL（Wayback/AlienVault/CommonCrawl）",
        category="web_recon",
        command_template="gau {domain} --o {output_file} {extra_args}",
        required_params=["domain"],
        optional_params={"output_file": os.path.join(tempfile.gettempdir(), "gau.txt"), "extra_args": ""},
        timeout=180,
        dependencies=["gau"],
    )
)

_register(
    ToolCommand(
        name="waybackurls",
        description="Wayback Machine URL 收集",
        category="web_recon",
        command_template="waybackurls {domain} {extra_args}",
        required_params=["domain"],
        optional_params={"extra_args": ""},
        timeout=120,
        dependencies=["waybackurls"],
    )
)


# ── Phase 3: Directory & Parameter Discovery ────────

_register(
    ToolCommand(
        name="gobuster",
        description="目录/文件扫描",
        category="dir_enum",
        command_template="gobuster dir -u {url} -w {wordlist} -t {threads} -o {output_file} {extra_args}",
        required_params=["url"],
        optional_params={
            "wordlist": "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
            "threads": "50",
            "output_file": os.path.join(tempfile.gettempdir(), "gobuster.txt"),
            "extra_args": "-x php,html,txt,js,json,asp,aspx,jsp,do,action",
        },
        timeout=300,
        dependencies=["gobuster"],
    )
)

_register(
    ToolCommand(
        name="gobuster-dns",
        description="DNS 子域扫描",
        category="dir_enum",
        command_template="gobuster dns -d {domain} -w {wordlist} -t {threads} -o {output_file} {extra_args}",
        required_params=["domain"],
        optional_params={
            "wordlist": "/usr/share/wordlists/seclists/Discovery/DNS/subdomains-top1million-5000.txt",
            "threads": "50",
            "output_file": os.path.join(tempfile.gettempdir(), "gobuster_dns.txt"),
            "extra_args": "",
        },
        timeout=300,
        dependencies=["gobuster"],
    )
)

_register(
    ToolCommand(
        name="dirsearch",
        description="Web 目录爆破",
        category="dir_enum",
        command_template="dirsearch -u {url} -e {extensions} -t {threads} --format=json -o {output_file} {extra_args}",
        required_params=["url"],
        optional_params={
            "extensions": "php,html,js,txt,bak,zip,tar.gz,conf",
            "threads": "30",
            "output_file": os.path.join(tempfile.gettempdir(), "dirsearch.json"),
            "extra_args": "",
        },
        timeout=300,
        dependencies=["dirsearch"],
    )
)

_register(
    ToolCommand(
        name="ffuf",
        description="Web Fuzzer",
        category="dir_enum",
        command_template="ffuf -u {url}/FUZZ -w {wordlist} -t {threads} -o {output_file} {extra_args}",
        required_params=["url"],
        optional_params={
            "wordlist": "/usr/share/wordlists/dirbuster/directory-list-2.3-medium.txt",
            "threads": "50",
            "output_file": os.path.join(tempfile.gettempdir(), "ffuf.json"),
            "extra_args": "-of json",
        },
        timeout=300,
        dependencies=["ffuf"],
    )
)

_register(
    ToolCommand(
        name="feroxbuster",
        description="目录递归扫描",
        category="dir_enum",
        command_template="feroxbuster -u {url} -t {threads} -o {output_file} --json {extra_args}",
        required_params=["url"],
        optional_params={
            "threads": "50",
            "output_file": os.path.join(tempfile.gettempdir(), "feroxbuster.json"),
            "extra_args": "",
        },
        timeout=300,
        dependencies=["feroxbuster"],
    )
)

_register(
    ToolCommand(
        name="arjun",
        description="HTTP 参数发现",
        category="dir_enum",
        command_template="arjun -u {url} -t {threads} -oJ {output_file} {extra_args}",
        required_params=["url"],
        optional_params={
            "threads": "10",
            "output_file": os.path.join(tempfile.gettempdir(), "arjun.json"),
            "extra_args": "",
        },
        timeout=120,
        dependencies=["arjun"],
    )
)


# ── Phase 4: Vulnerability Scanning ─────────────────

_register(
    ToolCommand(
        name="nuclei",
        description="基于模板的漏洞扫描器（6000+ 模板）",
        category="vuln_scan",
        command_template="nuclei -u {url} -t {templates} -severity {severity} -o {output_file} {extra_args}",
        required_params=["url"],
        optional_params={
            "templates": "",
            "severity": "critical,high,medium",
            "output_file": os.path.join(tempfile.gettempdir(), "nuclei.txt"),
            "extra_args": "-stats -silent",
        },
        timeout=300,
        dependencies=["nuclei"],
    )
)

_register(
    ToolCommand(
        name="nuclei-batch",
        description="批量漏洞扫描（从文件读取 URL 列表）",
        category="vuln_scan",
        command_template="nuclei -l {targets_file} -severity {severity} -o {output_file} -stats -silent {extra_args}",
        required_params=["targets_file"],
        optional_params={
            "severity": "critical,high,medium",
            "output_file": os.path.join(tempfile.gettempdir(), "nuclei_batch.txt"),
            "extra_args": "",
        },
        timeout=600,
        dependencies=["nuclei"],
    )
)

_register(
    ToolCommand(
        name="nikto",
        description="Web 服务器扫描器",
        category="vuln_scan",
        command_template="nikto -h {url} -o {output_file} -Format txt {extra_args}",
        required_params=["url"],
        optional_params={
            "output_file": os.path.join(tempfile.gettempdir(), "nikto.txt"),
            "extra_args": "-Tuning 123456789",
        },
        timeout=300,
        dependencies=["nikto"],
    )
)

_register(
    ToolCommand(
        name="wpscan",
        description="WordPress 安全扫描器",
        category="vuln_scan",
        command_template="wpscan --url {url} --enumerate p,t,u,vp,vt --format json -o {output_file} {extra_args}",
        required_params=["url"],
        optional_params={
            "output_file": os.path.join(tempfile.gettempdir(), "wpscan.json"),
            "extra_args": "",
        },
        timeout=300,
        dependencies=["wpscan"],
    )
)


# ── Phase 5: SQL Injection ──────────────────────────

_register(
    ToolCommand(
        name="sqlmap",
        description="自动化 SQL 注入检测和利用",
        category="exploitation",
        command_template="sqlmap -u {url} --batch --level={level} --risk={risk} --random-agent --output-dir={output_dir} {extra_args}",
        required_params=["url"],
        optional_params={
            "level": "3",
            "risk": "2",
            "output_dir": os.path.join(tempfile.gettempdir(), "sqlmap"),
            "extra_args": "",
        },
        timeout=600,
        dependencies=["sqlmap"],
    )
)

_register(
    ToolCommand(
        name="sqlmap-dbs",
        description="SQLMap — 枚举数据库",
        category="exploitation",
        command_template="sqlmap -u {url} --dbs --batch --random-agent {extra_args}",
        required_params=["url"],
        optional_params={"extra_args": ""},
        timeout=300,
        dependencies=["sqlmap"],
    )
)

_register(
    ToolCommand(
        name="sqlmap-tables",
        description="SQLMap — 枚举表",
        category="exploitation",
        command_template="sqlmap -u {url} -D {database} --tables --batch --random-agent {extra_args}",
        required_params=["url", "database"],
        optional_params={"extra_args": ""},
        timeout=300,
        dependencies=["sqlmap"],
    )
)

_register(
    ToolCommand(
        name="sqlmap-dump",
        description="SQLMap — 导出表数据",
        category="exploitation",
        command_template="sqlmap -u {url} -D {database} -T {table} --dump --batch --random-agent {extra_args}",
        required_params=["url", "database", "table"],
        optional_params={"extra_args": ""},
        timeout=600,
        dependencies=["sqlmap"],
    )
)


# ── Phase 6: XSS / Web Vulnerabilities ──────────────

_register(
    ToolCommand(
        name="dalfox",
        description="XSS 扫描和验证",
        category="exploitation",
        command_template="dalfox url {url} -o {output_file} --silence {extra_args}",
        required_params=["url"],
        optional_params={
            "output_file": os.path.join(tempfile.gettempdir(), "dalfox.txt"),
            "extra_args": "",
        },
        timeout=180,
        dependencies=["dalfox"],
    )
)

_register(
    ToolCommand(
        name="wafw00f",
        description="WAF 检测与指纹识别",
        category="vuln_scan",
        command_template="wafw00f {target} {extra_args}",
        required_params=["target"],
        optional_params={"extra_args": ""},
        timeout=60,
        dependencies=["wafw00f"],
    )
)


# ── Phase 7: Password Attacks ───────────────────────

_register(
    ToolCommand(
        name="hydra",
        description="在线密码爆破",
        category="password",
        command_template="hydra -l {username} -P {wordlist} {target} {service} -o {output_file} {extra_args}",
        required_params=["username", "target", "service"],
        optional_params={
            "wordlist": "/usr/share/wordlists/rockyou.txt",
            "output_file": os.path.join(tempfile.gettempdir(), "hydra.txt"),
            "extra_args": "-t 4 -V",
        },
        timeout=600,
        dependencies=["hydra"],
    )
)

_register(
    ToolCommand(
        name="john",
        description="John the Ripper 密码破解",
        category="password",
        command_template="john {hash_file} --wordlist={wordlist} {extra_args}",
        required_params=["hash_file"],
        optional_params={
            "wordlist": "/usr/share/wordlists/rockyou.txt",
            "extra_args": "--format=auto",
        },
        timeout=600,
        dependencies=["john"],
    )
)

_register(
    ToolCommand(
        name="hashcat",
        description="GPU 加速密码破解",
        category="password",
        command_template="hashcat -m {hash_mode} {hash_file} {wordlist} -o {output_file} {extra_args}",
        required_params=["hash_file"],
        optional_params={
            "hash_mode": "0",
            "wordlist": "/usr/share/wordlists/rockyou.txt",
            "output_file": os.path.join(tempfile.gettempdir(), "hashcat.txt"),
            "extra_args": "--force",
        },
        timeout=1200,
        dependencies=["hashcat"],
    )
)


# ── Phase 8: Exploitation Frameworks ────────────────

_register(
    ToolCommand(
        name="msfvenom",
        description="Metasploit Payload 生成器",
        category="exploitation",
        command_template="msfvenom -p {payload} LHOST={lhost} LPORT={lport} -f {format} -o {output_file} {extra_args}",
        required_params=["payload", "lhost"],
        optional_params={
            "lport": "4444",
            "format": "exe",
            "output_file": os.path.join(tempfile.gettempdir(), "payload"),
            "extra_args": "",
        },
        timeout=30,
        dependencies=["msfvenom"],
    )
)

_register(
    ToolCommand(
        name="msfconsole",
        description="Metasploit 控制台（交互式）",
        category="exploitation",
        command_template="msfconsole -q -x '{commands}' {extra_args}",
        required_params=["commands"],
        optional_params={"extra_args": ""},
        timeout=300,
        dependencies=["msfconsole"],
    )
)


# ── Phase 9: Reverse Engineering ────────────────────

_register(
    ToolCommand(
        name="binwalk",
        description="固件分析",
        category="reverse_eng",
        command_template="binwalk {file_path} {extra_args}",
        required_params=["file_path"],
        optional_params={"extra_args": "-e"},
        timeout=120,
        dependencies=["binwalk"],
    )
)

_register(
    ToolCommand(
        name="checksec",
        description="二进制安全检测",
        category="reverse_eng",
        command_template="checksec --file={file_path} {extra_args}",
        required_params=["file_path"],
        optional_params={"extra_args": ""},
        timeout=10,
        dependencies=["checksec"],
    )
)

_register(
    ToolCommand(
        name="exiftool",
        description="元数据提取",
        category="forensics",
        command_template="exiftool {file_path} {extra_args}",
        required_params=["file_path"],
        optional_params={"extra_args": ""},
        timeout=30,
        dependencies=["exiftool"],
    )
)

_register(
    ToolCommand(
        name="steghide",
        description="隐写术检测和提取",
        category="forensics",
        command_template="steghide extract -sf {file_path} -p {password} -f {extra_args}",
        required_params=["file_path"],
        optional_params={"password": "", "extra_args": ""},
        timeout=60,
        dependencies=["steghide"],
    )
)


# ── Phase 10: Cloud / Container Security ────────────

_register(
    ToolCommand(
        name="trivy",
        description="容器/Docker 镜像漏洞扫描",
        category="cloud",
        command_template="trivy image {image} -o {output_file} {extra_args}",
        required_params=["image"],
        optional_params={
            "output_file": os.path.join(tempfile.gettempdir(), "trivy.json"),
            "extra_args": "--format json --severity CRITICAL,HIGH",
        },
        timeout=300,
        dependencies=["trivy"],
    )
)

_register(
    ToolCommand(
        name="prowler",
        description="AWS 安全评估",
        category="cloud",
        command_template="prowler aws {extra_args}",
        required_params=[],
        optional_params={
            "extra_args": "--output json --output-directory " + os.path.join(tempfile.gettempdir(), "prowler")
        },
        timeout=600,
        dependencies=["prowler"],
    )
)

_register(
    ToolCommand(
        name="scout-suite",
        description="多云安全评估",
        category="cloud",
        command_template="scout aws {extra_args}",
        required_params=[],
        optional_params={"extra_args": "--report-dir " + os.path.join(tempfile.gettempdir(), "scout")},
        timeout=600,
        dependencies=["scout"],
    )
)

_register(
    ToolCommand(
        name="kube-hunter",
        description="Kubernetes 渗透测试",
        category="cloud",
        command_template="kube-hunter --pod {extra_args}",
        required_params=[],
        optional_params={"extra_args": "--report json"},
        timeout=300,
        dependencies=["kube-hunter"],
    )
)


# ── Utility ─────────────────────────────────────────


def get_tool(tool_name: str) -> Optional[ToolCommand]:
    """获取工具定义"""
    return TOOLS.get(tool_name)


def list_tools(category: Optional[str] = None) -> List[ToolCommand]:
    """列出所有工具，可选按类别过滤"""
    tools = list(TOOLS.values())
    if category:
        tools = [t for t in tools if t.category == category]
    return sorted(tools, key=lambda t: t.name)


def get_categories() -> List[str]:
    """获取所有工具类别"""
    return sorted(set(t.category for t in TOOLS.values()))


def check_installed_tools() -> Dict[str, bool]:
    """检查所有工具的安装状态"""
    return {name: is_tool_installed(name) for name in sorted(TOOLS.keys())}


def get_tools_status() -> Dict[str, Any]:
    """获取工具状态概览"""
    installed = check_installed_tools()
    categories = {}
    for name, tool in TOOLS.items():
        if tool.category not in categories:
            categories[tool.category] = {"total": 0, "installed": 0, "tools": []}
        categories[tool.category]["total"] += 1
        if installed.get(name):
            categories[tool.category]["installed"] += 1
        categories[tool.category]["tools"].append(name)

    return {
        "total": len(TOOLS),
        "installed": sum(1 for v in installed.values() if v),
        "categories": categories,
        "installed_map": installed,
    }

#!/usr/bin/env python3
"""仓库密钥泄露扫描（2026-08 安全加固）

检查项：
1. git 跟踪的根目录或前端 data/ 运行时数据（应全部忽略）
2. git 跟踪的私有配置和 config/.env（应忽略）
3. git 跟踪文件中的疑似密钥模式（sk-*、AWS AKIA*、私钥块、JWT）

用法: python scripts/scan_secrets.py
退出码: 0 = 通过, 1 = 发现风险
"""

import re
import subprocess
import sys

# Windows 兼容：默认 CP936/GBK 控制台打印 ✅/❌ 会 UnicodeEncodeError（exit 1）
if sys.platform == "win32":
    for _stream in (sys.stdout, sys.stderr):
        try:
            _stream.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001,S110 — 重配置失败仅跳过
            pass

SUSPICIOUS_PATTERNS = [
    (r"sk-[A-Za-z0-9]{20,}", "OpenAI 风格 API Key"),
    (r"AKIA[0-9A-Z]{16}", "AWS Access Key"),
    (r"-----BEGIN (RSA |EC |OPENSSH )?PRIVATE KEY-----", "私钥块"),
    (r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}", "JWT"),
    (r"(?i)(api[_-]?key|secret|token)\s*[:=]\s*['\"][A-Za-z0-9_\-]{16,}['\"]", "内联密钥赋值"),
]


def git(files: list[str]) -> list[str]:
    return subprocess.run(
        ["git", "ls-files", *files], capture_output=True, text=True, check=True
    ).stdout.splitlines()


def main() -> int:
    problems = []

    tracked_data = [f for f in git(["data/", "miya_frontend/data/"]) if f != "data/.gitkeep"]
    if tracked_data:
        problems.append(f"git 跟踪了 {len(tracked_data)} 个 data/ 运行时文件（应忽略）: "
                        + ", ".join(tracked_data[:5]) + " ...")

    tracked_env = git(["config/.env"])
    if tracked_env:
        problems.append("git 跟踪了 config/.env（含凭据，应忽略）")

    tracked_private_config = git(["config/permissions.json", "config/qq_config.yaml"])
    if tracked_private_config:
        problems.append("git 跟踪了账号配置文件: " + ", ".join(tracked_private_config))

    # 扫描所有被跟踪的文本文件
    all_files = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True
    ).stdout.splitlines()
    for path in all_files:
        if path.startswith("data/") or path.endswith((".png", ".jpg", ".jpeg", ".gif", ".ico", ".db", ".sqlite", ".lock", ".pyc")):
            continue
        try:
            content = open(path, encoding="utf-8", errors="ignore").read()
        except OSError:
            continue
        for pat, desc in SUSPICIOUS_PATTERNS:
            m = re.search(pat, content)
            if not m:
                continue
            matched = m.group(0)
            # 排除常见占位符示例（your-*/example/xxx/<...>）
            if re.search(r"(?i)(your[-_ ]|example|placeholder|\bxxx\b|<[^>]+>|change[_ ]me)", matched):
                continue
            line_no = content[: m.start()].count("\n") + 1
            problems.append(f"{path}:{line_no} 疑似 {desc}: {matched[:40]}")

    if problems:
        print("❌ 发现安全风险:")
        for p in problems:
            print("  -", p)
        return 1

    print("✅ 密钥扫描通过：无 data/ 跟踪、无 .env 跟踪、无疑似密钥模式")
    return 0


if __name__ == "__main__":
    sys.exit(main())

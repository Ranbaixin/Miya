#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查代码 import 与依赖清单的一致性。

用法:
  python scripts/check_imports_vs_requirements.py

扫描 core/hub/memory/webnet/mlink/run 下的所有 .py 文件，
对比 setup/dependencies/*.txt 中声明的包，报告差异。
"""

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCAN_DIRS = ["core", "hub", "memory", "webnet", "mlink", "run"]

# 标准库 (Python 3.11+)
STDLIB = {
    "abc",
    "argparse",
    "ast",
    "asyncio",
    "base64",
    "collections",
    "concurrent",
    "contextlib",
    "copy",
    "csv",
    "ctypes",
    "dataclasses",
    "datetime",
    "decimal",
    "difflib",
    "enum",
    "fractions",
    "functools",
    "glob",
    "hashlib",
    "hmac",
    "importlib",
    "inspect",
    "io",
    "itertools",
    "json",
    "logging",
    "math",
    "multiprocessing",
    "operator",
    "os",
    "pathlib",
    "pickle",
    "platform",
    "pprint",
    "queue",
    "random",
    "re",
    "secrets",
    "shlex",
    "shutil",
    "signal",
    "socketserver",
    "sqlite3",
    "statistics",
    "string",
    "struct",
    "subprocess",
    "sys",
    "tarfile",
    "tempfile",
    "textwrap",
    "threading",
    "time",
    "tracemalloc",
    "traceback",
    "types",
    "typing",
    "unittest",
    "urllib",
    "uuid",
    "wave",
    "warnings",
    "weakref",
    "xml",
    "zipfile",
    "zoneinfo",
    # 补充遗漏的标准库
    "__future__",
    "array",
    "builtins",
    "calendar",
    "colorsys",
    "contextvars",
    "fnmatch",
    "email",
    "fcntl",
    "gc",
    "getpass",
    "gettext",
    "gzip",
    "heapq",
    "html",
    "http",
    "imp",
    "linecache",
    "locale",
    "mimetypes",
    "mmap",
    "msvcrt",
    "netrc",
    "nis",
    "nntplib",
    "numbers",
    "opcode",
    "pdb",
    "poplib",
    "posix",
    "profile",
    "pstats",
    "pty",
    "pwd",
    "py_compile",
    "pyclbr",
    "readline",
    "reprlib",
    "resource",
    "rlcompleter",
    "runpy",
    "sched",
    "selectors",
    "site",
    "sndhdr",
    "socket",
    "ssl",
    "stat",
    "stringprep",
    "sunau",
    "symbol",
    "symtable",
    "sysconfig",
    "syslog",
    "tabnanny",
    "telnetlib",
    "termios",
    "test",
    "timeit",
    "tkinter",
    "token",
    "shelve",
    "smtplib",
    "tokenize",
    "trace",
    "tty",
    "turtle",
    "unicodedata",
    "uu",
    "venv",
    "wsgiref",
    "xdrlib",
    "xmlrpc",
}

# 本地包（仓库内顶层目录，不是 PyPI 依赖）
LOCAL_PACKAGES = {"core", "hub", "memory", "webnet", "mlink", "run", "config", "utils", "mcpserver", "plugins"}

# 已知的 import → PyPI 包名映射
IMPORT_TO_PYPI = {
    "PIL": "pillow",
    "yaml": "pyyaml",
    "dotenv": "python-dotenv",
    "pydantic": "pydantic",
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "starlette": "starlette",
    "aiohttp": "aiohttp",
    "aiofiles": "aiofiles",
    "httpx": "httpx",
    "jwt": "pyjwt",
    "cryptography": "cryptography",
    "psutil": "psutil",
    "watchdog": "watchdog",
    "requests": "requests",
    "websockets": "websockets",
    "websocket": "websocket-client",
    "sqlalchemy": "sqlalchemy",
    "sklearn": "scikit-learn",
    "cv2": "opencv-python",
    "numpy": "numpy",
    "pandas": "pandas",
    "faiss": "faiss-cpu",
    "matplotlib": "matplotlib",
    "scipy": "scipy",
    "magic": "python-magic",
    "pymongo": "pymongo",
    "Crypto": "pycryptodome",
    "google": "google-auth",
    "bs4": "beautifulsoup4",
    "markdown": "markdown",
    "jinja2": "jinja2",
    "pytest": "pytest",
    "chardet": "chardet",
    "tenacity": "tenacity",
    "jieba": "jieba",
    "loguru": "loguru",
    "qrcode": "qrcode",
    "pyserial": "serial",
    "playwright": "playwright",
    "comtypes": "comtypes",
    "pywinauto": "pywinauto",
    "win32com": "pywin32",
    "aiocqhttp": "aiocqhttp",
    "pedalboard": "pedalboard",
    "pydub": "pydub",
    "soundfile": "soundfile",
    "croniter": "croniter",
    "docstring_parser": "docstring-parser",
    "fastmcp": "fastmcp",
    "mcp": "mcp",
    "dingtalk_stream": "dingtalk-stream-sdk",
    "wechatpy": "wechatpy",
    "slack_sdk": "slack-sdk",
    "linebot": "line-bot-sdk",
    "lark_oapi": "lark-oapi",
    "markitdown": "markitdown",
    "markitdown_no_magika": "markitdown",  # 代码写错包名
    "genie_tts": None,  # 私有/不存在
    "epub_parser": None,
    "chromadb": "chromadb",
    "neo4j": "neo4j",
    "redis": "redis",
    "pymilvus": "pymilvus",
    # 2026-09 补充：import 名与 PyPI 名（连字符）差异映射
    "edge_tts": "edge-tts",
    "pydantic_settings": "pydantic-settings",
    "sentence_transformers": "sentence-transformers",
    "docx": "python-docx",
    "botpy": "qq-botpy",
    "telegram": "python-telegram-bot",
    "opentelemetry": "opentelemetry-api",
    # 软依赖（try/except 可选导入，缺失时功能降级，不算缺声明）：
    "pedalboard": None,
    "pydub": None,
    "soundfile": None,
    # 外部工具仓库的顶层包（UVR5 等，非 PyPI 依赖）
    "tools": None,
}


def collect_imports() -> dict:
    """返回 {root_package_name: [file_paths]}"""
    imports = {}
    for d in SCAN_DIRS:
        for pyfile in (ROOT / d).rglob("*.py"):
            if any(s in pyfile.parts for s in ("venv", "node_modules", ".git", "__pycache__", "_astrbot")):
                continue
            try:
                tree = ast.parse(pyfile.read_text("utf-8"))
            except (SyntaxError, UnicodeDecodeError):
                continue
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        top = alias.name.split(".")[0]
                        imports.setdefault(top, set()).add(str(pyfile.relative_to(ROOT)))
                elif isinstance(node, ast.ImportFrom):
                    if node.module and node.level == 0:
                        top = node.module.split(".")[0]
                        imports.setdefault(top, set()).add(str(pyfile.relative_to(ROOT)))
    return imports


def load_declared() -> set:
    """返回 setup/dependencies/*.txt 与 pyproject.toml 中声明的 PyPI 包名。

    2026-09 修复：此前只读 setup/dependencies/*.txt，漏掉 pyproject.toml
    （uv 管理的实际依赖真源），导致 apscheduler/pyjwt/edge-tts 等已声明
    依赖被误报为缺失。
    """
    deps_dir = ROOT / "setup" / "dependencies"
    declared = set()
    for req_file in deps_dir.glob("*.txt"):
        for line in req_file.read_text("utf-8").splitlines():
            line = line.strip().split("#")[0].strip()
            if not line:
                continue
            m = re.match(r"^([a-zA-Z0-9_-]+)", line)
            if m:
                declared.add(m.group(1))

    pyproject = ROOT / "pyproject.toml"
    if pyproject.exists():
        # 解析 pyproject 中所有 `key = [` 数组（主依赖 + 可选依赖组）
        lines = pyproject.read_text("utf-8").splitlines()
        in_deps = False
        for line in lines:
            s = line.strip()
            if not in_deps and re.match(r"^[A-Za-z0-9_\-]+\s*=\s*\[", s):
                in_deps = True
                s_after = s[s.index("[") + 1 :]
                if s_after.strip().endswith("]"):
                    in_deps = False  # 单行数组
                continue
            if in_deps:
                if s.startswith("]"):
                    in_deps = False
                    continue
                for m in re.finditer(r'"([a-zA-Z0-9_.\-]+)', s):
                    name = m.group(1).lower().split("[")[0]
                    declared.add(name)
    return declared


def main():
    imports = collect_imports()
    declared = load_declared()
    missing = []

    for mod, files in sorted(imports.items()):
        pkg = IMPORT_TO_PYPI.get(mod, mod)
        if pkg is None:
            continue  # known-nonexistent package
        if mod in STDLIB or mod in LOCAL_PACKAGES or f"F:\\PY" in str(files):
            continue
        if pkg not in declared:
            # check if directly in declared
            if mod not in declared:
                missing.append((mod, pkg, sorted(files)[:3]))

    if missing:
        print(f"缺失依赖 ({len(missing)} 个):")
        for mod, pkg, files in missing:
            print(f"  {mod} -> pip install {pkg}")
            for f in files:
                print(f"    {f}")
        return 1
    else:
        print("所有 import 对应的依赖均已声明。")
        return 0


if __name__ == "__main__":
    sys.exit(main())

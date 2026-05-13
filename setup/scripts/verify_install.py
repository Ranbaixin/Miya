#!/usr/bin/env python3
"""
Miya 安装验证脚本
动态解析 setup/dependencies/*.txt，验证依赖是否可正确导入
"""

import sys
import importlib
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent
DEPS_DIR = ROOT / "setup" / "dependencies"

CORE_CATEGORIES = {"base"}

PIP_TO_IMPORT: dict[str, str] = {
    "python-telegram-bot": "telegram",
    "python-multipart": "multipart",
    "python-dotenv": "dotenv",
    "python-docx": "docx",
    "python-magic": "magic",
    "pyyaml": "yaml",
    "pyjwt": "jwt",
    "pillow": "PIL",
    "edge-tts": "edge_tts",
    "sentence-transformers": "sentence_transformers",
    "scikit-learn": "sklearn",
    "opencv-python": "cv2",
    "discord.py": "discord",
    "lark-oapi": "lark_oapi",
    "line-bot-sdk": "linebot",
    "slack-bolt": "slack_bolt",
    "slack-sdk": "slack_sdk",
    "qq-botpy": "botpy",
    "typing-extensions": "typing_extensions",
    "google-generativeai": "google.generativeai",
    "pydantic-settings": "pydantic_settings",
    "sphinx-rtd-theme": "sphinx_rtd_theme",
    "pytest-asyncio": "pytest_asyncio",
    "pytest-cov": "pytest_cov",
    "rank-bm25": "rank_bm25",
    "faiss-cpu": "faiss",
    "funasr-onnx": "funasr_onnx",
    "beautifulsoup4": "bs4",
    "mattermostdriver": "mattermostdriver",
    "python-ripgrep": "ripgrep",
    "pycryptodome": "Crypto",
    "pyserial": "serial",
    "pyffmpeg": "pyffmpeg",
    "sqlmodel": "sqlmodel",
}


def parse_requirements_file(filepath: Path) -> list[str]:
    packages = []
    if not filepath.exists():
        return packages
    for line in filepath.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if (
            not line
            or line.startswith("#")
            or line.startswith("-r")
            or line.startswith("-e")
        ):
            continue
        match = re.match(r"^([a-zA-Z0-9][\w\-.]*)", line)
        if match:
            packages.append(match.group(1))
    return packages


def resolve_import(pip_name: str) -> str:
    if pip_name in PIP_TO_IMPORT:
        return PIP_TO_IMPORT[pip_name]
    return pip_name.replace("-", "_").lower()


def try_import(import_name: str) -> bool:
    try:
        importlib.import_module(import_name)
        return True
    except ImportError:
        return False


def collect_core() -> list[str]:
    return parse_requirements_file(DEPS_DIR / "base.txt")


def collect_optional() -> list[str]:
    optional = []
    for deps_file in sorted(DEPS_DIR.glob("*.txt")):
        if deps_file.stem in CORE_CATEGORIES:
            continue
        optional.extend(parse_requirements_file(deps_file))
    return optional


def dedup(items: list[str]) -> list[str]:
    seen = set()
    result = []
    for item in items:
        if item not in seen:
            seen.add(item)
            result.append(item)
    return result


def run() -> int:
    print("\n" + "=" * 60)
    print("Miya Install Verification")
    print(f"Config dir: {DEPS_DIR}")
    print("=" * 60)

    core = dedup(collect_core())
    optional = dedup(collect_optional())
    core_set = set(core)
    optional = [d for d in optional if d not in core_set]

    success = []
    failed = []
    opt_success = []
    opt_missing = []

    for dep in core:
        name = resolve_import(dep)
        if try_import(name):
            success.append(dep)
        else:
            failed.append(dep)

    for dep in optional:
        name = resolve_import(dep)
        if try_import(name):
            opt_success.append(dep)
        else:
            opt_missing.append(dep)

    if success:
        print("\n[OK] Core modules:")
        for mod in success:
            print(f"  + {mod}")

    if opt_success:
        print("\n[OK] Optional modules:")
        for mod in opt_success:
            print(f"  + {mod}")

    if failed:
        print("\n[FAIL] Core modules missing:")
        for mod in failed:
            print(f"  - {mod}")

    if opt_missing:
        print("\n[WARN] Optional modules not installed:")
        for mod in opt_missing:
            print(f"  - {mod}")

    total_ok = len(success) + len(opt_success)
    print("\n" + "-" * 60)
    print(
        f"Result: {total_ok} OK | {len(failed)} failed | {len(opt_missing)} optional missing"
    )
    print("-" * 60)

    if failed:
        print("\n[FAIL] Core verification failed!")
        print("  Run: pip install -r setup/dependencies/base.txt")
        return 1

    print("\n[OK] Core verification passed!")
    if opt_missing:
        print(
            f"\nNote: {len(opt_missing)} optional modules missing, some features may be unavailable."
        )
        print("  Run: pip install -r setup/requirements/full.txt")

    print("=" * 60 + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(run())

#!/usr/bin/env python3
"""
Miya 依赖检查脚本
动态解析 setup/dependencies/*.txt 文件，检查所有依赖是否已安装
"""

import re
import subprocess
import sys
from pathlib import Path
from typing import Dict

ROOT = Path(__file__).resolve().parent.parent.parent
DEPS_DIR = ROOT / "setup" / "dependencies"


def parse_requirements_file(filepath: Path) -> Dict[str, str]:
    packages = {}
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
        match = re.match(r"^([a-zA-Z0-9][\w\-.]*)(\[[^\]]*\])?\s*([><=!~].*)?", line)
        if match:
            name = match.group(1).strip().lower()
            spec = match.group(3).strip() if match.group(3) else ""
            packages[name] = spec
    return packages


def parse_all_dependencies() -> Dict[str, Dict[str, str]]:
    categorized = {}
    if not DEPS_DIR.exists():
        print(f"ERROR: deps dir not found {DEPS_DIR}")
        return categorized
    for deps_file in sorted(DEPS_DIR.glob("*.txt")):
        category = deps_file.stem
        packages = parse_requirements_file(deps_file)
        if packages:
            categorized[category] = packages
    return categorized


def collect_unique(categorized: Dict[str, Dict[str, str]]) -> Dict[str, str]:
    all_pkgs = {}
    for cat_data in categorized.values():
        for name, spec in cat_data.items():
            if name not in all_pkgs:
                all_pkgs[name] = spec
    return all_pkgs


def get_installed_version(package_name: str) -> str | None:
    try:
        result = subprocess.run(
            [sys.executable, "-m", "pip", "show", package_name],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            return None
        for line in result.stdout.splitlines():
            if line.startswith("Version:"):
                return line.split(":", 1)[1].strip()
    except Exception:
        pass
    return None


def parse_ver(v: str) -> tuple:
    clean = re.sub(r"[^0-9.]", "", v.strip().split("+")[0].split("-")[0])
    parts = clean.split(".")
    result = []
    for p in parts:
        try:
            result.append(int(p))
        except ValueError:
            result.append(0)
    return tuple(result) if result else (0,)


def check_constraint(installed: str, spec: str) -> bool:
    if not spec:
        return True
    iv = parse_ver(installed)
    ok = True
    parts = [p.strip() for p in re.split(r",", spec) if p.strip()]
    for constraint in parts:
        m = re.match(r"([><=!~]+)\s*(\S.*)", constraint)
        if not m:
            continue
        op, target = m.group(1), m.group(2).strip()
        tv = parse_ver(target)
        if op == ">=" and not (iv >= tv) or op == ">" and not (iv > tv) or op == "<=" and not (iv <= tv) or op == "<" and not (iv < tv) or op == "==" and iv != tv or op == "!=" and iv == tv:
            ok = False
        elif op == "~=":
            if not (iv >= tv):
                ok = False
            if len(tv) >= 2:
                upper = list(tv)
                upper[-2] += 1
                for i in range(-1, -len(upper), -1):
                    if i == -2:
                        continue
                    upper[i] = 0
                if iv >= tuple(upper):
                    ok = False
    return ok


def run() -> int:
    categorized = parse_all_dependencies()
    if not categorized:
        print("\nERROR: no dependency config files found")
        return 1

    all_packages = collect_unique(categorized)

    print("\n" + "=" * 60)
    print("Miya Dependencies Check")
    print(f"Config dir: {DEPS_DIR}")
    print(f"Categories: {len(categorized)}")
    print(f"Total:      {len(all_packages)}")
    print("=" * 60)

    installed_list = []
    missing_list = []
    mismatch_list = []

    for name, spec in sorted(all_packages.items()):
        version = get_installed_version(name)
        if version is None:
            missing_list.append(f"{name} {spec}".strip())
        else:
            if spec and not check_constraint(version, spec):
                mismatch_list.append(f"{name}=={version} (need {spec})")
            else:
                installed_list.append(f"{name}=={version}")

    if missing_list:
        print("\n[MISSING]")
        for pkg in missing_list:
            print(f"  - {pkg}")

    if mismatch_list:
        print("\n[VERSION MISMATCH]")
        for pkg in mismatch_list:
            print(f"  - {pkg}")

    if missing_list or mismatch_list:
        print(f"\n  Installed: {len(installed_list)}")

    print("\n" + "-" * 60)
    print(
        f"Result: {len(installed_list)} OK | {len(missing_list)} missing | {len(mismatch_list)} mismatch"
    )
    print("-" * 60)

    if missing_list or mismatch_list:
        print("\nRecommend:")
        print("  pip install -r setup/requirements/full.txt")
    else:
        print("\n[OK] All dependencies verified!")

    print("=" * 60 + "\n")
    return 0 if not missing_list and not mismatch_list else 1


if __name__ == "__main__":
    sys.exit(run())

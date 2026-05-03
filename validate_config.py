#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIYA 配置验证器

验证系统配置是否正确
"""

import os
import sys
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==================== 验证结果 ====================


@dataclass
class ValidationResult:
    """验证结果"""

    name: str
    passed: bool
    message: str = ""
    severity: str = "error"  # error, warning, info


def check_env_vars() -> List[ValidationResult]:
    """检查环境变量"""
    results = []

    # 检查 .env 文件
    env_file = PROJECT_ROOT / "config" / ".env"
    if env_file.exists():
        results.append(ValidationResult(".env file", True, "Exists"))
    else:
        results.append(
            ValidationResult(".env file", False, "Not found (optional)", "warning")
        )

    return results


def check_config_files() -> List[ValidationResult]:
    """检查配置文件"""
    results = []

    config_dir = PROJECT_ROOT / "config"
    required_configs = [
        "providers_config.py",
        "platforms_config.py",
    ]

    for config_file in required_configs:
        path = PROJECT_ROOT / "core" / config_file
        if path.exists():
            results.append(ValidationResult(config_file, True, "Exists"))
        else:
            results.append(ValidationResult(config_file, False, "Missing", "error"))

    return results


def check_dependencies() -> List[ValidationResult]:
    """检查依赖"""
    results = []
    required = ["openai", "anthropic", "httpx", "fastapi"]

    for pkg in required:
        try:
            __import__(pkg)
            results.append(ValidationResult(f"package:{pkg}", True, "Installed"))
        except ImportError:
            results.append(
                ValidationResult(f"package:{pkg}", False, "Not installed", "warning")
            )

    return results


def check_python_version() -> List[ValidationResult]:
    """检查 Python 版本"""
    results = []

    version = sys.version_info
    if version.major >= 3 and version.minor >= 8:
        results.append(
            ValidationResult(
                "python",
                True,
                f"v{version.major}.{version.minor}.{version.micro}",
            )
        )
    else:
        results.append(
            ValidationResult(
                "python",
                False,
                f"v{version.major}.{version.minor} (need 3.8+)",
                "error",
            )
        )

    return results


def check_data_dir() -> List[ValidationResult]:
    """检查数据目录"""
    results = []

    data_dir = PROJECT_ROOT / "data"
    if data_dir.exists():
        results.append(ValidationResult("data directory", True, "Exists"))
    else:
        data_dir.mkdir(exist_ok=True)
        results.append(ValidationResult("data directory", True, "Created"))

    return results


def run_validation() -> Dict:
    """运行所有验证"""
    all_results = []

    all_results.extend(check_python_version())
    all_results.extend(check_config_files())
    all_results.extend(check_dependencies())
    all_results.extend(check_env_vars())
    all_results.extend(check_data_dir())

    # 统计
    passed = sum(1 for r in all_results if r.passed)
    failed = len(all_results) - passed

    errors = sum(1 for r in all_results if not r.passed and r.severity == "error")
    warnings = sum(1 for r in all_results if not r.passed and r.severity == "warning")

    return {
        "results": all_results,
        "passed": passed,
        "failed": failed,
        "errors": errors,
        "warnings": warnings,
    }


def print_report():
    """打印验证报告"""
    print("=" * 50)
    print("[MIYA] Configuration Validator v6.0")
    print("=" * 50)
    print()

    result = run_validation()

    for r in result["results"]:
        status = "[OK]" if r.passed else f"[{r.severity.upper()}]"
        print(f"  {status} {r.name}: {r.message}")

    print()
    print("=" * 50)
    print(f"Summary:")
    print(f"  Total: {len(result['results'])}")
    print(f"  Passed: {result['passed']}")
    if result["errors"] > 0:
        print(f"  Errors: {result['errors']}")
    if result["warnings"] > 0:
        print(f"  Warnings: {result['warnings']}")
    print("=" * 50)

    return result["errors"] == 0


if __name__ == "__main__":
    success = print_report()
    sys.exit(0 if success else 1)

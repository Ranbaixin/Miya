#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIYA 系统自测脚本

测试 MIYA 核心模块是否正常工作
"""

import asyncio
import sys
import time
from pathlib import Path
from dataclasses import dataclass

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


# ==================== 测试结果 ====================


@dataclass
class TestResult:
    """测试结果"""

    name: str
    passed: bool
    message: str = ""
    time_ms: float = 0


# ==================== 测试用例 ====================


async def test_system_init() -> TestResult:
    """测试系统初始化"""
    try:
        from core.miya_system import init_system

        await init_system()
        return TestResult("System Init", True, "v6.0 ready")
    except Exception as e:
        return TestResult("System Init", False, str(e))


async def test_system_info() -> TestResult:
    """测试系统信息"""
    try:
        from core.system_info import get_system_info, get_modules_info

        info = get_system_info()
        modules = get_modules_info()

        if info.get("version") == "6.0":
            return TestResult(
                "System Info",
                True,
                f"v{info['version']}, {len(modules)} modules",
            )
        else:
            return TestResult("System Info", False, "version mismatch")
    except Exception as e:
        return TestResult("System Info", False, str(e))


async def test_providers() -> TestResult:
    """测试 Provider 列表"""
    try:
        from core.dashboard_api import APIRouter

        router = APIRouter()
        result = await router._routes["GET /api/providers"](None)

        total = result.get("total", 0)
        if total >= 5:  # 新系统更严格，有些没密钥的不会启用
            return TestResult("Providers", True, f"{total} providers")
        else:
            return TestResult("Providers", False, f"only {total}")
    except Exception as e:
        return TestResult("Providers", False, str(e))


async def test_platforms() -> TestResult:
    """测试 Platform 列表"""
    try:
        from core.dashboard_api import APIRouter

        router = APIRouter()
        result = await router._routes["GET /api/platforms"](None)

        total = result.get("total", 0)
        if total >= 10:
            return TestResult("Platforms", True, f"{total} platforms")
        else:
            return TestResult("Platforms", False, f"only {total}")
    except Exception as e:
        return TestResult("Platforms", False, str(e))


async def test_dashboard_api() -> TestResult:
    """测试 Dashboard API"""
    try:
        from core.dashboard_api import APIRouter

        router = APIRouter()
        health = await router._routes["GET /health"](None)

        if health.get("status") == "ok":
            return TestResult(
                "Dashboard API",
                True,
                f"v{health.get('version')}, {len(router._routes)} routes",
            )
        else:
            return TestResult("Dashboard API", False, "health check failed")
    except Exception as e:
        return TestResult("Dashboard API", False, str(e))


async def test_status() -> TestResult:
    """测试状态API"""
    try:
        from core.dashboard_api import APIRouter

        router = APIRouter()
        result = await router._routes["GET /api/stats"](None)

        if "uptime" in result and result.get("providers_count", 0) >= 5:
            return TestResult(
                "Status API",
                True,
                f"uptime: {result.get('uptime')}s, providers: {result.get('providers_count')}",
            )
        else:
            return TestResult("Status API", False, "missing fields")
    except Exception as e:
        return TestResult("Status API", False, str(e))


# ==================== 主测试函数 ====================


async def run_tests() -> list[TestResult]:
    """运行所有测试"""
    tests = [
        test_system_init,
        test_system_info,
        test_providers,
        test_platforms,
        test_dashboard_api,
        test_status,
    ]

    results = []
    for test_func in tests:
        start = time.time()
        result = await test_func()
        result.time_ms = (time.time() - start) * 1000
        results.append(result)
        status = "[OK]" if result.passed else "[FAIL]"
        print(f"  {status} {result.name}: {result.message} ({result.time_ms:.1f}ms)")

    return results


# ==================== 主函数 ====================


def main():
    """主函数"""
    print("=" * 60)
    print("[MIYA] System Self-Test v6.0")
    print("=" * 60)

    results = asyncio.run(run_tests())

    # 统计
    passed = sum(1 for r in results if r.passed)
    failed = len(results) - passed

    print()
    print("=" * 60)
    print(f"[RESULT] {passed}/{len(results)} passed")
    if failed > 0:
        print(f"[FAIL] {failed}")
    print("=" * 60)

    # 返回码
    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIYA 系统报告生成器

生成完整的系统状态报告
"""

import asyncio
import json
import sys
import time
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def get_system_report() -> dict:
    """获取系统报告"""
    import core.miya_system
    import core.system_info

    # 初始化系统
    asyncio.run(core.miya_system.init_system())

    # 获取状态
    status = core.miya_system.get_system_status()
    info = core.system_info.get_system_info()
    modules = core.system_info.get_modules_info()

    report = {
        "timestamp": datetime.now().isoformat(),
        "system": {
            "name": "MIYA",
            "version": "6.0",
            "mode": status.get("mode", "unified"),
            "uptime": status.get("uptime", 0),
        },
        "modules": {
            m["name"]: {
                "status": m["status"],
                "load_time_ms": m.get("load_time_ms", 0),
            }
            for m in modules
        },
        "counts": {
            "providers": status.get("providers_count", 0),
            "platforms": status.get("platforms_count", 0),
            "routes": status.get("routes_count", 0),
        },
        "runtime": {
            "python_version": info.get("python", "unknown"),
            "platform": info.get("platform", "unknown"),
        },
    }

    return report


def print_report(report: dict):
    """打印报告"""
    print("=" * 60)
    print("           MIYA System Report v6.0")
    print("=" * 60)
    print()
    print(f"Generated: {report['timestamp']}")
    print()
    print("-" * 60)
    print("System:")
    print(f"  Name:    {report['system']['name']}")
    print(f"  Version: {report['system']['version']}")
    print(f"  Mode:    {report['system']['mode']}")
    print(f"  Uptime:  {report['system']['uptime']}s")
    print("-" * 60)
    print("Counts:")
    print(f"  Providers: {report['counts']['providers']}")
    print(f"  Platforms: {report['counts']['platforms']}")
    print(f"  Routes:    {report['counts']['routes']}")
    print("-" * 60)
    print("Modules:")
    for name, info in report["modules"].items():
        status = info["status"]
        load_time = info.get("load_time_ms", 0)
        print(f"  - {name}: {status} ({load_time:.1f}ms)")
    print("-" * 60)
    print("Runtime:")
    print(f"  Python: {report['runtime']['python_version']}")
    print(f"  OS:     {report['runtime']['platform']}")
    print("=" * 60)


def save_report(filename: str = "miya_report.json"):
    """保存报告到文件"""
    report = get_system_report()

    with open(filename, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2, ensure_ascii=False)

    print(f"Report saved to: {filename}")
    return report


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        save_report()
    else:
        report = get_system_report()
        print_report(report)


if __name__ == "__main__":
    main()

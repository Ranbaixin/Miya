#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MIYA CLI 入口

用法:
    python miya.py                    # 显示帮助
    python miya.py init                   # 初始化系统
    python miya.py status             # 显示状态
    python miya.py server           # 启动 API 服务器
    python miya.py test              # 运行自测
    python miya.py providers         # 列出提供商
    python miya.py platforms         # 列出平台
    python miya.py routes            # 列出路由
    python miya.py modules            # 列出模块
"""

import argparse
import asyncio
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))


def cmd_init(args):
    """初始化系统"""
    from core.miya_system import init_system

    print("[MIYA] Initializing...")
    asyncio.run(init_system())
    print("[OK] System ready!")


def cmd_status(args):
    """显示状态"""
    from core.miya_system import init_system, get_system_status

    asyncio.run(init_system())
    status = get_system_status()

    print("=" * 50)
    print(f"  MIYA v{status['version']}")
    print(f"  Mode: {status['mode']}")
    print(f"  Uptime: {status['uptime']}s")
    print("-" * 50)
    print(f"  Providers: {status['providers_count']}")
    print(f"  Platforms: {status['platforms_count']}")
    print(f"  Routes: {status['routes_count']}")
    print("-" * 50)
    print("  Modules:")
    for name, m in status.get("modules", {}).items():
        print(f"    - {name}: {m['status']}")
    print("=" * 50)


def cmd_server(args):
    """启动服务器"""
    import miya_server

    miya_server.main()


def cmd_test(args):
    """运行测试"""
    import test_miya

    test_miya.main()


def cmd_providers(args):
    """列出提供商和模型"""
    from core.model_pool_manager import get_model_pool

    pool = get_model_pool()
    stats = pool.get_stats()

    print("=" * 50)
    print("MIYA 模型池状态")
    print("=" * 50)
    print(f"总模型数: {stats['total']}")
    print(f"启用数: {stats['enabled']}")
    print()
    print("按类型:")
    for t, s in stats["by_type"].items():
        enabled = s["enabled"]
        total = s["total"]
        print(f"  {t}: {enabled}/{total} 启用")
    print()


def cmd_models(args):
    """列出 AI 模型（与 providers 相同）"""
    cmd_providers(args)


def cmd_platforms(args):
    """列出平台"""
    from core.dashboard_api import APIRouter

    async def run():
        router = APIRouter()
        result = await router._routes["GET /api/platforms"](None)
        print("=" * 50)
        print(f"Platforms ({result['total']}):")
        for p in result.get("platforms", []):
            print(f"  - {p['id']}: {p.get('type', 'N/A')}")
        print("=" * 50)

    asyncio.run(run())


def cmd_routes(args):
    """列出路由"""
    from core.dashboard_api import list_all_routes

    routes = list_all_routes()
    print("=" * 50)
    print(f"Routes ({len(routes)}):")
    for r in routes:
        print(f"  {r['method']:6} {r['path']}")
    print("=" * 50)


def cmd_modules(args):
    """列出模块"""
    from core.miya_system import init_system, get_system_status
    from core.system_info import get_modules_info

    asyncio.run(init_system())
    modules = get_modules_info()

    print("=" * 50)
    print(f"Modules ({len(modules)}):")
    for m in modules:
        status = m["status"]
        print(f"  - {m['name']}: {status}")
    print("=" * 50)


def cmd_models(args):
    """列出 AI 模型"""
    from core.model_pool_manager import get_model_pool

    pool = get_model_pool()
    models = pool.list_all()

    print("=" * 50)
    print(f"Models ({len(models)}):")
    for m in models:
        status = "[OK]" if m["enabled"] else "[X]"
        print(f"  {m['id']}: {m['type']} - {m['provider']} - {status}")

    enabled = sum(1 for m in models if m["enabled"])
    print(f"Total: {len(models)}, {enabled} enabled")
    print("=" * 50)


# ==================== 主函数 ====================


def main():
    parser = argparse.ArgumentParser(description="MIYA CLI")
    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # init
    subparsers.add_parser("init", help="Initialize system")

    # status
    subparsers.add_parser("status", help="Show system status")

    # server
    subparsers.add_parser("server", help="Start API server")

    # test
    subparsers.add_parser("test", help="Run self-test")

    # providers
    subparsers.add_parser("providers", help="List providers")

    # platforms
    subparsers.add_parser("platforms", help="List platforms")

    # routes
    subparsers.add_parser("routes", help="List API routes")

    # modules
    subparsers.add_parser("modules", help="List modules")

    # models (使用 providers 命令的别名)
    # subparsers.add_parser("models", help="List AI models")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        return

    # 执行命令
    commands = {
        "init": cmd_init,
        "status": cmd_status,
        "server": cmd_server,
        "test": cmd_test,
        "providers": cmd_providers,
        "platforms": cmd_platforms,
        "routes": cmd_routes,
        "modules": cmd_modules,
        "models": cmd_models,
    }

    cmd = commands.get(args.command)
    if cmd:
        cmd(args)


if __name__ == "__main__":
    main()

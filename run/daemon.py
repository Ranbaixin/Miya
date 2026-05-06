"""
弥娅系统 v7.0 - 统一守护进程入口

启动方式:
  python run/daemon.py                  # 启动守护进程 + API
  python run/daemon.py --no-api         # 仅守护进程，不启动 API
  python run/daemon.py --api-port 9800  # 指定 API 端口
  python run/daemon.py --platforms qqofficial,webchat  # 仅启动指定平台

环境变量:
  MIYA_API_PORT=9800   API 端口 (默认 9800)
  MIYA_API_HOST=0.0.0.0  API 监听地址

这是弥娅系统自 v7.0 起的唯一启动入口。
守护进程启动后会：
  1. 初始化弥娅核心（人格、记忆、决策引擎）
  2. 自动连接所有启用的平台
  3. 启动管理 API 服务器 (REST + WebSocket)
  4. 平台自动重连、健康检查
  5. 接收 Ctrl+C 优雅退出
"""

from __future__ import annotations

import asyncio
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["MIYA_DAEMON_MODE"] = "1"  # v7.0: 标记 daemon 模式，避免重复日志 handler


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
        ],
        force=True,  # v7.0: 清除其他模块添加的重复 handler
    )
    # 抑制启动时过于啰嗦的日志
    for noisy in [
        "webnet.ToolNet.registry",
        "hub.platform_adapters",
        "Miya.Gestalt",
        "Miya.AgentHub",
        "botpy",
        "httpx",
        "memory.core",
        "memory.sqlite_backend",
        "core.embedding_client",
        "memory.working_memory",
        "memory.historian",
        "memory.diteng_listener",
        "core.user_persona",
        "core.awareness",
        "core.autonomy_manager",
        "core.autonomous_engine",
        "core.web_api",
        "core.problem_scanner",
    ]:
        logging.getLogger(noisy).setLevel(logging.WARNING)


async def run_daemon(
    api_enabled: bool = True,
    api_port: int = 9800,
    api_host: str = "0.0.0.0",
    platform_ids: list[str] | None = None,
):
    """启动弥娅守护进程"""
    from core.miya_daemon import MiyaDaemon
    from core.management_api import ManagementAPI

    logger = logging.getLogger("Miya.Bootstrap")

    print("""
╔══════════════════════════════════════════════════════════════╗
║                                                              ║
║        ✦ 弥娅 (MIYA) v7.0 - 统一守护进程 ✦                  ║
║                                                              ║
║        所有平台已就绪 · 热插拔 · 自动重连                    ║
║                                                              ║
╚══════════════════════════════════════════════════════════════╝
    """)

    # 1. 初始化守护进程
    daemon = MiyaDaemon()
    logger.info("弥娅守护进程已创建")

    # 2. 启动守护进程
    await daemon.start(platform_ids=platform_ids)

    # 3. 启动管理 API
    if api_enabled:
        api = ManagementAPI(daemon, host=api_host, port=api_port)
        await api.serve(block=False)
        logger.info(f"管理 API 已启动: http://{api_host}:{api_port}")

        # 将 API 广播链接到 daemon 的平台事件
        daemon.registry.on_broadcast(api.broadcast_event)
        # v7.0: 注册 webhook 平台路由
        api.register_webhook_platforms()

        print(f"""
╔══════════════════════════════════════════════════════════════╗
║  ✦ 管理 API 就绪                                            ║
║━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━  ║
║  REST:  http://{api_host}:{api_port}/api/v1/health              ║
║  WS:    ws://{api_host}:{api_port}/api/v1/ws                    ║
║  Docs:  http://{api_host}:{api_port}/docs                       ║
╚══════════════════════════════════════════════════════════════╝
        """)
    else:
        api = None
        print()
        print("  ◆ 管理 API 已禁用")
        print()

    # 显示平台状态
    _print_platform_status(daemon)

    print("\n  💫 弥娅已就绪，按 Ctrl+C 退出...\n")

    # 4. 等待退出信号
    try:
        await daemon.wait()
    except KeyboardInterrupt:
        pass

    # 5. 优雅关闭
    print("\n正在关闭...")
    if api:
        await api.stop()
    await daemon.shutdown()
    print("\n💤 弥娅已退出\n")


def _print_platform_status(daemon):
    """打印平台状态表格"""
    stats = daemon.get_platform_status()
    if not stats:
        print("  ⚠ 没有启用的平台")
        return

    print("  ◆ 平台状态 ────────────────────────────")
    print(f"  {'平台':<20} {'状态':<12}")
    print(f"  {'─' * 20} {'─' * 12}")
    for s in stats:
        status_icon = "✓" if s["status"] == "online" else "✗"
        print(f"  {s['platform_name']:<20} {status_icon} {s['status']}")
    print()


def main():
    import argparse

    parser = argparse.ArgumentParser(description="弥娅系统 v7.0 统一守护进程")
    parser.add_argument("--no-api", action="store_true", help="不启动管理 API")
    parser.add_argument(
        "--api-port",
        type=int,
        default=int(os.environ.get("MIYA_API_PORT", 9800)),
        help="管理 API 端口 (默认 9800)",
    )
    parser.add_argument(
        "--api-host",
        type=str,
        default=os.environ.get("MIYA_API_HOST", "0.0.0.0"),
        help="管理 API 监听地址",
    )
    parser.add_argument(
        "--platforms",
        type=str,
        help="仅启动指定平台（逗号分隔），如 qqofficial,webchat",
    )
    parser.add_argument(
        "--list-platforms",
        action="store_true",
        help="列出所有可用平台",
    )

    args = parser.parse_args()

    # 列出平台
    if args.list_platforms:
        from config.platforms_config import get_enabled_platforms

        enabled = get_enabled_platforms()
        print("\n✦ 可用平台:\n")
        for pid, cfg in enabled.items():
            name = cfg.get("name", pid)
            print(f"  - {pid}: {name}")
        print()
        return 0

    # 解析平台列表
    platform_ids = None
    if args.platforms:
        platform_ids = [p.strip() for p in args.platforms.split(",") if p.strip()]

    # 启动
    setup_logging()
    log_dir = PROJECT_ROOT / "logs"
    log_dir.mkdir(exist_ok=True)

    try:
        asyncio.run(
            run_daemon(
                api_enabled=not args.no_api,
                api_port=args.api_port,
                api_host=args.api_host,
                platform_ids=platform_ids,
            )
        )
    except KeyboardInterrupt:
        pass
    except Exception as e:
        logging.getLogger("Miya.Bootstrap").error(f"守护进程异常: {e}", exc_info=True)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())

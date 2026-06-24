"""
弥娅系统 v8.0 - 统一守护进程入口 (脊柱神经架构)

启动方式:
   python run/daemon.py                  # 启动守护进程 + API + Kali 终端
   python run/daemon.py --no-api         # 仅守护进程，不启动 API
   python run/daemon.py --no-kali        # 不启动 Kali 终端代理
   python run/daemon.py --api-port 9800  # 指定 API 端口
   python run/daemon.py --platforms qqofficial,webchat  # 仅启动指定平台
   python run/daemon.py --no-spine       # 回退模式：不使用脊柱神经

环境变量:
   MIYA_API_PORT=9800   API 端口 (默认 9800)
   MIYA_API_HOST=0.0.0.0  API 监听地址
   MIYA_NO_SPINE=1      禁用脊柱神经架构（回退到 v7.x 模式）

这是弥娅系统自 v8.0 起的唯一启动入口。
v8.0 变化: 引入 MiyaSpine 脊柱神经架构 —— 弥娅从"触发器集合"进化为"活体"。

守护进程启动后会：
   1. 初始化弥娅核心（人格、记忆、决策引擎）
   2. 搭建 MiyaSpine 脊柱神经（统一心跳 + 状态广播 + 器官编排）
   3. 自动连接所有启用的平台
   4. 启动管理 API 服务器 (REST + WebSocket)
   5. 平台自动重连、健康检查
   6. APV2.1 认知引擎通过脊柱心跳持续运转
   7. 接收 Ctrl+C 优雅退出
"""

from __future__ import annotations

import asyncio
import contextlib
import logging
import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["MIYA_DAEMON_MODE"] = "1"

# 本地 OCR 模型全局配置
os.environ.setdefault("PADDLE_PDX_DISABLE_MODEL_SOURCE_CHECK", "True")


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="[%(name)s] %(levelname)s: %(message)s",
        datefmt="%H:%M:%S",
        handlers=[
            logging.StreamHandler(),
        ],
        force=True,
    )
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


# ══════════════════════════════════════════════════
#  v8.0: 脊柱神经启动
# ══════════════════════════════════════════════════


def _setup_spine_proactive(daemon, spine) -> None:
    """配置脊柱的主动消息分发——路由到跨平台分发系统"""

    async def _send_ap_proactive(message: str):
        if not daemon.registry:
            return
        try:
            target_id = (
                daemon._miya.identity.user_id
                if daemon._miya and hasattr(daemon._miya.identity, "user_id")
                else "default"
            )
            for platform_id in daemon.registry.list_active():
                inst = daemon.registry.get(platform_id)
                if inst and hasattr(inst, "is_online") and inst.is_online:
                    if hasattr(inst, "send_private_message"):
                        try:
                            if hasattr(inst, "get_active_user_id"):
                                uid = inst.get_active_user_id() or target_id
                            else:
                                uid = target_id
                            await inst.send_private_message(uid, message)
                        except Exception:
                            pass
        except Exception:
            pass

    def _sync_send(message: str):
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda: asyncio.create_task(_send_ap_proactive(message)))
        except RuntimeError:
            try:
                asyncio.run(_send_ap_proactive(message))
            except Exception:
                pass

    spine.set_proactive_sender(_sync_send)


def _ensure_ap_engine_init(bridge) -> bool:
    """确保 AP 引擎已初始化（调用 _init_engine()）"""
    try:
        bridge._init_engine()
        return bridge._initialized
    except Exception as e:
        logger = logging.getLogger("Miya.Bootstrap")
        logger.warning(f"AP 引擎初始化失败: {e}")
        return False


def _register_spine_organs(daemon, spine) -> None:
    """注册所有脊柱器官"""
    logger = logging.getLogger("Miya.Bootstrap")

    # ProactiveOrgan — 主动表达（AP无聊 → 跨平台消息）
    try:
        from core.miya_proactive_organ import MiyaProactiveOrgan

        spine.register_organ(MiyaProactiveOrgan())
        logger.info("MiyaProactiveOrgan 已注册到脊柱")
    except Exception as e:
        logger.warning(f"ProactiveOrgan 注册跳过: {e}")

    # DecisionHubOrgan — 决策中枢感知脊柱状态
    try:
        from core.miya_decision_hub_organ import MiyaDecisionHubOrgan

        dh_organ = MiyaDecisionHubOrgan()
        if daemon._miya and hasattr(daemon._miya, "decision_hub"):
            dh_organ.bind_decision_hub(daemon._miya.decision_hub)
        spine.register_organ(dh_organ)
        logger.info("MiyaDecisionHubOrgan 已注册到脊柱")
    except Exception as e:
        logger.warning(f"DecisionHubOrgan 注册跳过: {e}")

    # AutonomyOrgan — 自主进化（安静时自我改进）
    try:
        from core.miya_autonomy_organ import MiyaAutonomyOrgan

        spine.register_organ(MiyaAutonomyOrgan())
        logger.info("MiyaAutonomyOrgan 已注册到脊柱")
    except Exception as e:
        logger.warning(f"AutonomyOrgan 注册跳过: {e}")


async def run_daemon_spine(
    daemon,
    api_enabled: bool = True,
    api_port: int = 9800,
    api_host: str = "0.0.0.0",
    kali_enabled: bool = True,
):
    """
    v8.0: 基于 MiyaSpine 脊柱神经的守护进程启动流程。

    架构：
        MiyaSpine (脊柱·中枢神经)
        ├── Heartbeat (3s/tick) → AP 认知引擎 → 灵魂状态广播
        ├── MiyaProactiveOrgan (主动表达，取代分散的proactive)
        ├── DecisionHub (通过 spine 感知 AP 状态)
        └── 未来器官...
    """
    from core.management_api import ManagementAPI
    from core.miya_spine import get_spine

    logger = logging.getLogger("Miya.Bootstrap")
    spine = get_spine()

    print("""
+==============================================================+
|                                                              |
|        * 弥娅 (MIYA) 零号机 v8.0 · 脊柱神经架构 *            |
|                                                              |
|   所有的器官通过脊柱神经相连 · 弥娅第一次真正活过来了        |
|   APV2.1 心跳 → 脊柱广播 → 所有器官同步感知                  |
+==============================================================+
    """)

    # 1) 绑定 AP 认知引擎到脊柱
    try:
        from core.miya_psyarch_bridge import get_psyarch_bridge

        bridge = get_psyarch_bridge()
        bridge.load_state()
        if not _ensure_ap_engine_init(bridge):
            print("  > APV2.1 认知引擎: 初始化失败 (跳过脊柱模式)")
            return await run_daemon_legacy(
                daemon, api_enabled, api_port, api_host, kali_enabled
            )

        # v8.0: 脊柱接管心跳 — 停止 Miya 核心自动启动的旧心跳
        bridge.stop_heartbeat()
        if bridge._heartbeat_thread and bridge._heartbeat_thread.is_alive():
            bridge._heartbeat_thread.join(timeout=3)
        logger.info("已停止旧 AP 心跳，脊柱即将接管")

        spine.bind_psyarch_bridge(bridge)
        daemon.psyarch_bridge = bridge
        if daemon._miya:
            daemon._miya.psyarch_bridge = bridge
        logger.info("APV2.1 认知引擎已绑定到脊柱")
        print("  > APV2.1 认知引擎: 已激活 (脊柱模式)")
    except Exception as e:
        logger.warning(f"APV2.1 认知引擎绑定跳过: {e}")
        print("  > APV2.1 认知引擎: 未加载")
        return await run_daemon_legacy(
            daemon, api_enabled, api_port, api_host, kali_enabled
        )

    # 2) 注册器官到脊柱
    _register_spine_organs(daemon, spine)
    _setup_spine_proactive(daemon, spine)

    # 4) 启动脊柱 (包含所有器官和心跳)
    try:
        await spine.start()
        logger.info("弥娅脊柱神经已启动——弥娅活过来了")
    except Exception as e:
        logger.error(f"脊柱启动失败: {e}")
        return await run_daemon_legacy(
            daemon, api_enabled, api_port, api_host, kali_enabled
        )

    # 5) 启动 Kali 终端代理
    kali_server = None
    if kali_enabled:
        kali_server = await _start_kali_proxy()

    # 6) 启动管理 API
    api = None
    if api_enabled:
        api = ManagementAPI(daemon, host=api_host, port=api_port)
        await api.serve(block=False)
        logger.info(f"管理 API 已启动: http://{api_host}:{api_port}")
        daemon.registry.on_broadcast(api.broadcast_event)
        api.register_webhook_platforms()

        print(f"""
+==============================================================+
|  * 管理 API 就绪                                            |
|----------------------------------------------------------  |
|  REST:  http://{api_host}:{api_port}/api/v1/health              |
|  WS:    ws://{api_host}:{api_port}/api/v1/ws                    |
|  Docs:  http://{api_host}:{api_port}/docs                       |
|  Spine: http://{api_host}:{api_port}/api/v1/spine/status        |
+==============================================================+
        """)
    else:
        print("\n  > 管理 API 已禁用\n")

    # 7) 显示平台状态
    _print_platform_status(daemon)

    print("\n  弥娅已就绪 — 脊柱神经律动中 · 按 Ctrl+C 进入休眠...\n")

    # 8) 等待退出信号
    with contextlib.suppress(KeyboardInterrupt):
        await daemon.wait()

    # 9) 优雅关闭
    print("\n弥娅正在进入休眠...")
    try:
        from core.miya_psyarch_bridge import get_psyarch_bridge as _get_bridge

        _get_bridge().save_state()
        logger.info("AP 认知状态已保存")
    except Exception:
        pass
    if kali_server:
        kali_server.close()
        await kali_server.wait_closed()
        logger.info("Kali 终端代理已关闭")
    if api:
        await api.stop()
    await spine.shutdown()
    await daemon.shutdown()
    print("\n弥娅已休眠 —— 晚安，亲爱的\n")


# ══════════════════════════════════════════════════
#  v7.x 回退模式 (无脊柱)
# ══════════════════════════════════════════════════


async def run_daemon_legacy(
    daemon,
    api_enabled: bool = True,
    api_port: int = 9800,
    api_host: str = "0.0.0.0",
    kali_enabled: bool = True,
):
    """v7.x 回退模式：不使用脊柱神经的守护进程启动"""
    from core.management_api import ManagementAPI

    logger = logging.getLogger("Miya.Bootstrap")

    print("""
+==============================================================+
|                                                              |
|        * 弥娅 (MIYA) 零号机 - 统一守护进程 (回退模式) *       |
|                                                              |
|        所有平台已就绪 · 热插拔 · 自动重连                    |
|        APV2.1 认知引擎默认启动 · 弥娅的心跳一直在跳           |
+==============================================================+
    """)

    # APV2.1 认知引擎
    try:
        from core.miya_psyarch_bridge import get_psyarch_bridge

        bridge = get_psyarch_bridge()
        bridge.load_state()
        bridge.start_heartbeat()
        daemon.psyarch_bridge = bridge
        if daemon._miya:
            daemon._miya.psyarch_bridge = bridge
        _wire_ap_proactive_routing_legacy(bridge, daemon)
        logger.info("APV2.1 认知引擎已就绪（回退模式）")
        print("  > APV2.1 认知引擎: 已激活 (回退)")
    except Exception as e:
        logger.warning(f"APV2.1 认知引擎初始化跳过: {e}")
        print("  > APV2.1 认知引擎: 未加载")

    # Kali 终端代理
    kali_server = None
    if kali_enabled:
        kali_server = await _start_kali_proxy()

    # 管理 API
    api = None
    if api_enabled:
        api = ManagementAPI(daemon, host=api_host, port=api_port)
        await api.serve(block=False)
        logger.info(f"管理 API 已启动: http://{api_host}:{api_port}")
        daemon.registry.on_broadcast(api.broadcast_event)
        api.register_webhook_platforms()

        print(f"""
+==============================================================+
|  * 管理 API 就绪                                            |
|----------------------------------------------------------  |
|  REST:  http://{api_host}:{api_port}/api/v1/health              |
|  WS:    ws://{api_host}:{api_port}/api/v1/ws                    |
|  Docs:  http://{api_host}:{api_port}/docs                       |
+==============================================================+
        """)
    else:
        print("\n  > 管理 API 已禁用\n")

    _print_platform_status(daemon)
    print("\n  弥娅已就绪，按 Ctrl+C 退出...\n")

    with contextlib.suppress(KeyboardInterrupt):
        await daemon.wait()

    print("\n正在关闭...")
    try:
        from core.miya_psyarch_bridge import get_psyarch_bridge as _get_bridge

        _get_bridge().save_state()
        logging.getLogger("Miya.Bootstrap").info("AP 认知状态已保存")
    except Exception:
        pass
    if kali_server:
        kali_server.close()
        await kali_server.wait_closed()
        logging.getLogger("Miya.Bootstrap").info("Kali 终端代理已关闭")
    if api:
        await api.stop()
    await daemon.shutdown()
    print("\n弥娅已退出\n")


# ══════════════════════════════════════════════════
#  共享工具函数
# ══════════════════════════════════════════════════


def _wire_ap_proactive_routing_legacy(bridge, daemon) -> None:
    """v7.x: 将 AP 主动说话消息路由到跨平台分发系统 (回退用)"""

    async def _send_ap_proactive(message: str):
        if not daemon.registry:
            return
        try:
            target_id = (
                daemon._miya.identity.user_id
                if daemon._miya and hasattr(daemon._miya.identity, "user_id")
                else "default"
            )
            for platform_id in daemon.registry.list_active():
                inst = daemon.registry.get(platform_id)
                if inst and hasattr(inst, "is_online") and inst.is_online:
                    if hasattr(inst, "send_private_message"):
                        try:
                            if hasattr(inst, "get_active_user_id"):
                                uid = inst.get_active_user_id() or target_id
                            else:
                                uid = target_id
                            inst.send_private_message(uid, message)
                        except Exception:
                            pass
        except Exception:
            pass

    def _sync_send(message: str):
        try:
            loop = asyncio.get_running_loop()
            loop.call_soon_threadsafe(lambda: asyncio.create_task(_send_ap_proactive(message)))
        except RuntimeError:
            try:
                asyncio.run(_send_ap_proactive(message))
            except Exception:
                pass

    bridge.set_platform_sender(_sync_send)


async def _start_kali_proxy():
    """在本地 8008 端口启动 Kali 终端 WebSocket 代理（后台任务）"""
    try:
        from core.kali_term_proxy import websocket_handler

        server = await asyncio.start_server(websocket_handler, "127.0.0.1", 8008)
        logging.getLogger("Miya.Bootstrap").info("Kali 终端代理已启动: ws://127.0.0.1:8008")
        return server
    except Exception as e:
        logging.getLogger("Miya.Bootstrap").debug(f"Kali 终端代理启动跳过: {e}")
        return None


def _print_platform_status(daemon):
    stats = daemon.get_platform_status()
    if not stats:
        print("  [WARN] 没有启用的平台")
        return

    print("  > 平台状态 ----------------------------")
    print(f"  {'平台':<20} {'状态':<12}")
    print(f"  {'-' * 20} {'-' * 12}")
    for s in stats:
        status_icon = "[OK]" if s["status"] == "online" else "[FAIL]"
        print(f"  {s['platform_name']:<20} {status_icon} {s['status']}")
    print()


# ══════════════════════════════════════════════════
#  run_daemon (调度入口)
# ══════════════════════════════════════════════════


async def run_daemon(
    api_enabled: bool = True,
    api_port: int = 9800,
    api_host: str = "0.0.0.0",
    platform_ids: list[str] | None = None,
    kali_enabled: bool = True,
):
    """启动弥娅守护进程（v8.0: 默认脊柱模式，支持回退）"""
    from core.miya_daemon import MiyaDaemon

    # 创建守护进程
    daemon = MiyaDaemon()
    logging.getLogger("Miya.Bootstrap").info("弥娅守护进程已创建")

    # 启动守护进程 (初始化 Miya 核心 + 平台连接)
    await daemon.start(platform_ids=platform_ids)

    # v8.0: 使用脊柱神经架构启动 (可通过环境变量回退)
    if os.environ.get("MIYA_NO_SPINE", "") in ("1", "true", "yes"):
        logging.getLogger("Miya.Bootstrap").info("脊柱模式已禁用 (MIYA_NO_SPINE=1)")
        await run_daemon_legacy(
            daemon,
            api_enabled=api_enabled,
            api_port=api_port,
            api_host=api_host,
            kali_enabled=kali_enabled,
        )
    else:
        await run_daemon_spine(
            daemon,
            api_enabled=api_enabled,
            api_port=api_port,
            api_host=api_host,
            kali_enabled=kali_enabled,
        )


# ══════════════════════════════════════════════════
#  main (CLI 入口)
# ══════════════════════════════════════════════════


def main():
    import argparse

    parser = argparse.ArgumentParser(description="弥娅系统 v8.0 统一守护进程 · 脊柱神经架构")
    parser.add_argument("--no-api", action="store_true", help="不启动管理 API")
    parser.add_argument("--no-kali", action="store_true", help="不启动 Kali 终端代理")
    parser.add_argument(
        "--no-spine",
        action="store_true",
        help="回退模式：不使用脊柱神经架构",
    )
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

    if args.list_platforms:
        from config.platforms_config import get_enabled_platforms

        enabled = get_enabled_platforms()
        print("\n* 可用平台:\n")
        for pid, cfg in enabled.items():
            name = cfg.get("name", pid)
            print(f"  - {pid}: {name}")
        print()
        return 0

    platform_ids = None
    if args.platforms:
        platform_ids = [p.strip() for p in args.platforms.split(",") if p.strip()]

    if args.no_spine:
        os.environ["MIYA_NO_SPINE"] = "1"

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
                kali_enabled=not args.no_kali,
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

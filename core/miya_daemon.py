"""
弥娅守护进程 (MiyaDaemon) - 统一后台核心

提供：
- 单一 Miya 核心实例（所有平台共享同一个人格、记忆、决策）
- 平台编排（动态注册、批量启停、健康监控）
- 优雅的生命周期管理
- 信号处理（SIGINT/SIGTERM 安全退出）
- 运行时 API 服务器（可选）

Usage:
    daemon = MiyaDaemon()
    daemon.register_platforms_from_config()
    await daemon.start()
    await daemon.wait()          # 阻塞直到停止信号
    await daemon.shutdown()
"""

from __future__ import annotations

import asyncio
import logging
import signal
from datetime import datetime
from typing import Any, Dict, List, Optional

from .unified_platform import (
    BasePlatform,
    PlatformEvent,
    PlatformRegistry,
    get_registry,
)
from .version import VERSION

logger = logging.getLogger("Miya.Daemon")


class MiyaDaemon:
    """
    弥娅统一守护进程

    架构：
        MiyaDaemon
         ├── Miya Core (单例人格/记忆/决策)
         ├── PlatformRegistry (平台编排器)
         │    ├── QQ Official
         │    ├── Telegram
         │    ├── Discord
         │    └── ... (18+ 平台)
         └── Management API (可选)
    """

    VERSION = VERSION

    def __init__(self, auto_register: bool = True):
        self._started = False
        self._shutdown_event = asyncio.Event()
        self._miya = None
        self._registry = get_registry()
        self._management_server = None

        self.start_time: Optional[datetime] = None
        self._background_tasks: list[asyncio.Task] = []

        if auto_register:
            self.register_platforms_from_config()

    # ==================== 平台注册 ====================

    def register_platforms_from_config(self):
        """从配置文件注册所有启用的平台"""
        from config.platforms_config import get_enabled_platforms

        enabled = get_enabled_platforms()
        if not enabled:
            logger.warning("没有启用的平台")
            return

        for platform_id, platform_config in enabled.items():
            self._register_from_config(platform_id, platform_config)

    def _register_from_config(self, platform_id: str, config: Dict[str, Any]):
        """根据配置注册单个平台"""
        # 动态构建平台实例
        platform = self._create_platform(platform_id, config)
        if platform:
            self._registry.register(platform.__class__, config)
            logger.info(f"注册平台: {platform_id} ({platform.platform_name})")

    def _create_platform(self, platform_id: str, config: Dict[str, Any]) -> Optional[BasePlatform]:
        """根据平台ID创建对应的平台实例"""
        from .unified_platform_impl import (
            DiscordPlatform,
            GenericPlatform,
            LarkPlatform,
            OneBotPlatform,
            QQOfficialPlatform,
            TelegramPlatform,
            WebChatPlatform,
        )

        platform_map: Dict[str, type] = {
            "qqofficial": QQOfficialPlatform,
            "telegram": TelegramPlatform,
            "discord": DiscordPlatform,
            "aiocqhttp": OneBotPlatform,
            "webchat": WebChatPlatform,
            "lark": LarkPlatform,
        }

        cls = platform_map.get(platform_id)
        if cls:
            return cls(config=config)

        logger.info(f"平台 {platform_id} 使用通用适配器")
        generic = GenericPlatform(config=config)
        generic.platform_id = platform_id
        generic.platform_name = config.get("name", platform_id)
        return generic

    # ==================== 生命周期 ====================

    async def start(self, platform_ids: Optional[List[str]] = None):
        """启动守护进程"""
        logger.info("=" * 60)
        logger.info(f"✦ 弥娅守护进程 v{self.VERSION} 启动中... ✦")
        logger.info("=" * 60)

        self.start_time = datetime.now()

        # 0. 启动预检（告警不阻断）：配置语法/模型配置语义/环境变量，
        #    防"带病不自知"上线（依赖缺失、视觉模型配错、API key 缺失等静默降级）
        self._run_startup_preflight()

        # 1. 初始化 Miya 核心
        await self._init_miya_core()

        # 2. 启动平台 (内含 miya_core 注入)
        await self._init_platforms(platform_ids)

        await self._scheduler_lifecycle("start")

        # 3. 注册信号处理
        self._setup_signal_handlers()

        # 4. 记录就绪
        registered = self._registry.list_registered()
        logger.info(f"已注册 {len(registered)} 个平台: {[p['id'] for p in registered]}")

        self._started = True
        logger.info("=" * 60)
        logger.info("💫 弥娅守护进程已就绪")
        logger.info("=" * 60)

    async def _init_miya_core(self):
        """初始化 Miya 核心（懒加载，优雅降级）"""
        from run.main import Miya

        self._miya = Miya()
        logger.info("✅ Miya 核心初始化完成")

        # MemoryNet 初始化失败不阻止启动
        if self._miya.memory_net:
            try:
                await self._miya.memory_net.initialize()
                logger.info("✅ MemoryNet 全局记忆系统初始化成功")
            except Exception as e:  # noqa: BLE001 — MemoryNet 失败不影响核心，已记录日志
                logger.warning(f"⚠️ MemoryNet 初始化失败（不影响核心服务）: {e}")

        # 2026-08 修复：初始化 GRAG 任务管理器（此前从未调用，实时五元组提取静默失效）
        grag = getattr(self._miya, "grag_memory", None)
        if grag:
            try:
                await grag.initialize()
                logger.info("✅ GRAG 任务管理器初始化成功（实时知识提取启用）")
            except Exception as e:  # noqa: BLE001 — GRAG 初始化失败不影响核心，同步兜底仍可用
                logger.warning(f"⚠️ GRAG 任务管理器初始化失败（将走同步提取）: {e}")

        # 2026-09：接线定时遗忘循环（start_cleanup_task 此前零调用方，
        # 过期删除/90天归档/低优先级衰减从未执行，短期记忆积压无人清理）
        try:
            from memory.core import get_memory_core

            mem_core = await get_memory_core()
            await mem_core.start_cleanup_task()
            logger.info("✅ 记忆清理循环已启动（过期删除 + 90天归档 + 低优先级衰减）")
        except Exception as e:  # noqa: BLE001 — 清理循环失败不影响核心服务
            logger.warning(f"⚠️ 记忆清理循环启动失败: {e}")

        # 主动聊天后台轮询（可选，失败不影响核心服务）
        try:
            dh = getattr(self._miya, "decision_hub", None)
            if dh and dh.proactive_chat and dh.proactive_chat.is_enabled():
                await dh.start_proactive_background()
                logger.info("✅ 主动聊天后台轮询已启动")
        except Exception as e:  # noqa: BLE001 — 主动聊天失败不影响核心，已记录日志
            logger.warning(f"⚠️ 主动聊天启动失败（不影响核心服务）: {e}")

        # PC 使用作息每日沉淀（可选：经 pc_tracker 桥拉当日摘要入长期记忆）
        try:
            from core.pc_usage_digest import start_daily_digest

            if start_daily_digest():
                logger.info("✅ PC 作息每日沉淀任务已排期")
            else:
                logger.info("PC 作息沉淀已通过 PC_DIGEST_ENABLED 停用")
        except Exception as e:  # noqa: BLE001 — 沉淀任务失败不影响核心服务
            logger.warning(f"⚠️ PC 作息沉淀任务启动失败（不影响核心服务）: {e}")

    def _run_startup_preflight(self):
        """启动预检（core/doctor.run_preflight）：只告警不阻断，防止带病不自知上线"""
        try:
            from core.doctor import WARN, has_failures, run_preflight, summarize

            findings = run_preflight()
            counts = summarize(findings)
            if not findings or (not has_failures(findings) and counts.get(WARN, 0) == 0):
                logger.info("✅ 启动预检通过（配置/模型/环境变量）")
                return
            logger.warning("=" * 60)
            logger.warning("⚠️ 启动预检发现问题（不阻断启动，建议尽快修复）：")
            for f in findings:
                for detail in f.details:
                    if detail.startswith("["):
                        logger.warning(f"  [{f.check_id}] {detail}")
                for hint in f.fix_hints:
                    logger.warning(f"      ↳ 修复: {hint}")
            logger.warning("=" * 60)
            if has_failures(findings):
                logger.error(f"⚠️ 启动预检存在 FAIL 级问题 {counts}，完整诊断请运行: python scripts/doctor.py")
        except Exception as e:  # noqa: BLE001 — 预检失败不影响核心启动
            logger.warning(f"启动预检执行失败（不影响核心服务）: {e}")

        # 2026-09：启动辅助子进程（健康检查 + 可选 Neo4j 迁移补课）延后 60s 执行，
        # 削峰启动内存/IO；Neo4j 迁移默认关闭（图谱已改用 SQLite graph_store），
        # 显式设置 MIYA_ENABLE_NEO4J_MIGRATE=1 才会执行。
        try:
            import os
            import subprocess
            import sys

            from pathlib import Path as _Path

            health_script = _Path(__file__).parent.parent / "scripts" / "memory_health_check.py"
            migrate_script = _Path(__file__).parent.parent / "scripts" / "migrate_memory_to_neo4j.py"
            enable_migrate = os.getenv("MIYA_ENABLE_NEO4J_MIGRATE", "").lower() in ("1", "true", "yes")

            async def _delayed_startup_checks():
                await asyncio.sleep(60)
                if health_script.exists():
                    await asyncio.to_thread(
                        subprocess.run,
                        [sys.executable, str(health_script)],
                        capture_output=True,
                        text=True,
                        timeout=120,
                    )
                    logger.info("记忆健康检查已完成（延后启动）")
                if enable_migrate and migrate_script.exists():
                    await asyncio.to_thread(
                        subprocess.run,
                        [sys.executable, str(migrate_script)],
                        capture_output=True,
                        text=True,
                        timeout=600,
                    )
                    logger.info("记忆图迁移增量补课已完成（延后启动）")

            self._background_tasks.append(asyncio.create_task(_delayed_startup_checks()))
            extra = " + Neo4j 迁移补课" if enable_migrate else ""
            logger.info(f"启动辅助检查已排期（60s 后执行健康检查{extra}）")
        except Exception as e:  # noqa: BLE001 — 辅助检查失败不影响核心
            logger.warning(f"⚠️ 启动辅助检查排期失败（不影响核心服务）: {e}")

    async def _init_platforms(self, platform_ids: Optional[List[str]] = None):
        """初始化并连接所有平台

        2026-09 修复：显式校验 platform_ids，未知 id 立即报错并列出可用值，
        不再静默"平台连接: 0/1 在线"（此前 --platforms webchat 报未知平台）。
        """
        self._registry.on_broadcast(self._on_platform_broadcast)

        if platform_ids:
            registered = {p["id"] for p in self._registry.list_registered()}
            unknown = [pid for pid in platform_ids if pid not in registered]
            if unknown:
                raise ValueError(
                    f"未知平台: {', '.join(unknown)}；可用平台: {', '.join(sorted(registered))}"
                    "（注意：仅已启用的平台可指定，可在 config/platforms_config.py 中启用）"
                )
            results = {}
            for pid in platform_ids:
                results[pid] = await self._registry.start(pid, miya_core=self._miya)
        else:
            results = await self._registry.start_all(miya_core=self._miya)

        online = sum(1 for v in results.values() if v)
        total = len(results)
        logger.info(f"平台连接: {online}/{total} 在线")

    async def wait(self):
        """阻塞等待直到收到停止信号"""
        await self._shutdown_event.wait()

    async def stop(self):
        """停止守护进程（收到信号时调用）"""
        logger.info("收到停止信号，正在安全退出...")
        self._shutdown_event.set()

    async def shutdown(self):
        """优雅关闭"""
        logger.info("=" * 60)
        logger.info("弥娅守护进程正在关闭...")

        if self._miya:
            await self._save_state()

        await self._scheduler_lifecycle("stop")

        # 停止所有平台
        await self._registry.shutdown()

        # 取消后台任务
        for task in self._background_tasks:
            if not task.done():
                task.cancel()
        if self._background_tasks:
            await asyncio.gather(*self._background_tasks, return_exceptions=True)
        self._background_tasks.clear()

        if self._miya:
            await self._close_miya_core()

        logger.info("💤 弥娅守护进程已关闭")
        logger.info("=" * 60)

    async def _save_state(self):
        """保存状态（关闭前持久化工作记忆、谛听、话题追踪）"""
        try:
            from memory.diteng_listener import get_diting
            from memory.working_memory import get_working_memory

            try:
                wm = get_working_memory()
                wm.save(force=True)  # 强制刷新防抖缓冲区
                logger.debug("[关闭] 工作记忆已保存")
            except Exception as e:  # noqa: BLE001 — 工作记忆保存失败已记录日志
                logger.debug(f"[关闭] 工作记忆保存失败: {e}")

            try:
                diting = get_diting()
                diting.save()
                logger.debug("[关闭] 谛听状态已保存")
            except Exception as e:  # noqa: BLE001 — 谛听保存失败已记录日志
                logger.debug(f"[关闭] 谛听保存失败: {e}")

        except Exception as e:  # noqa: BLE001 — 状态保存失败已记录日志
            logger.warning(f"状态保存失败: {e}")

    async def _close_miya_core(self):
        """关闭 Miya 核心

        2026-09 修复（P1 关闭链）：此前 daemon 退出从不调用 Miya.ashutdown()，
        导致 8000 Web API 的非 daemon uvicorn 线程永不停止（进程悬挂），
        且 ai_client/记忆后端/GRAG/Neo4j 等均绕过关闭链。ashutdown 内部
        每步有 _safe_close 超时保护，可安全幂等调用。
        """
        try:
            if self._miya:
                # 与终端模式(run/main.py amain finally)相同的关闭顺序：
                # 先落盘会话历史，再走 ashutdown 完整关闭链
                conv_hist = getattr(self._miya, "conversation_history", None)
                if conv_hist and hasattr(conv_hist, "flush"):
                    await conv_hist.flush()
                if conv_hist and hasattr(conv_hist, "close"):
                    await conv_hist.close()

                ashutdown = getattr(self._miya, "ashutdown", None)
                if ashutdown:
                    await ashutdown()
        except Exception as e:  # noqa: BLE001 — 核心关闭异常已记录日志
            logger.warning(f"Miya 核心关闭异常: {e}")

    async def _scheduler_lifecycle(self, action: str) -> None:
        """启动或停止定时任务调度器（统一生命周期入口）

        2026-09 修复（P2 调度器双实例）：daemon 启动前先把 Miya.scheduler
        （DecisionHub/ToolNet 经 tool_context 持有的实例）登记为全局单例，
        避免 tool_context 注册的定时任务落在从未 start 的孤立实例上。
        """
        try:
            from hub.scheduler import get_global_scheduler, set_global_scheduler

            if self._miya:
                miya_scheduler = getattr(self._miya, "scheduler", None)
                if miya_scheduler is not None:
                    set_global_scheduler(miya_scheduler)

            scheduler = get_global_scheduler()
            if action == "start":
                await scheduler.start()
                logger.info("✅ 定时任务调度器已启动")
            else:
                await scheduler.stop()
                logger.info("定时任务调度器已停止")
        except Exception as e:  # noqa: BLE001 — 调度器操作失败已记录日志
            logger.warning(f"⚠️ 定时任务调度器{action}失败: {e}")

    # ==================== 信号处理 ====================

    def _setup_signal_handlers(self):
        """注册系统信号处理器"""
        for sig in (signal.SIGINT, signal.SIGTERM):
            try:
                asyncio.get_event_loop().add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
            except NotImplementedError:
                # Windows: 直接设置 shutdown_event 而非 asyncio.create_task
                signal.signal(sig, lambda s, f: self._shutdown_event.set())

    # ==================== 事件处理 ====================

    async def _on_platform_broadcast(self, event: Dict):
        """处理平台广播事件"""
        event_type = event.get("event", "")
        pid = event.get("platform_id", "unknown")

        if PlatformEvent.DISCONNECTED.value in event_type:
            logger.info(f"[{pid}] 平台已断开")
        elif PlatformEvent.RECONNECTING.value in event_type:
            logger.info(f"[{pid}] 正在重连 (第 {event.get('data', {}).get('attempt', '?')} 次)")
        elif PlatformEvent.RECONNECT_FAILED.value in event_type:
            logger.error(f"[{pid}] 重连失败，已达最大尝试次数")

    # ==================== 管理接口 ====================

    async def start_platform(self, platform_id: str) -> bool:
        """热启动一个平台"""
        return await self._registry.start(platform_id, miya_core=self._miya)

    async def stop_platform(self, platform_id: str) -> bool:
        """热停止一个平台"""
        return await self._registry.stop(platform_id)

    async def restart_platform(self, platform_id: str) -> bool:
        """热重启一个平台"""
        return await self._registry.restart(platform_id)

    def get_platform_status(self) -> List[Dict[str, Any]]:
        """获取所有平台状态"""
        return self._registry.get_all_stats()

    def get_daemon_status(self) -> Dict[str, Any]:
        """获取守护进程状态"""
        uptime = (datetime.now() - self.start_time).total_seconds() if self.start_time else 0
        # 2026-09 加固：暴露 AI 降级状态，避免 AI 不可用时健康检查显示"假活"
        ai_degraded = not (self._miya and getattr(self._miya, "ai_client", None))
        return {
            "version": self.VERSION,
            "started": self._started,
            "start_time": self.start_time.isoformat() if self.start_time else None,
            "uptime_seconds": uptime,
            "degraded": {
                "ai_client": ai_degraded,
            },
            "platforms": {
                "total": len(self._registry._platform_classes),
                "online": len(self._registry.get_online_platforms()),
            },
        }

    @property
    def permission_engine(self):
        """获取统一权限引擎"""
        from .unified_permission import get_permission_engine

        return get_permission_engine()

    @property
    def miya(self):
        """获取 Miya 核心实例"""
        return self._miya

    @property
    def registry(self) -> PlatformRegistry:
        """获取平台注册表"""
        return self._registry

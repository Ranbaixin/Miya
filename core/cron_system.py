"""
弥娅定时任务系统 (Cron System)

功能：
1. 定时任务执行
2. 延迟消息发送
3. 任务调度管理
4. 任务历史记录

参考 AstrBot Cron 实现

作者: MIYA
日期: 2026-04-28
"""

import asyncio
import contextlib
import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

from croniter import croniter

logger = logging.getLogger(__name__)


# ==================== 枚举定义 ====================


class TaskStatus(str, Enum):
    """任务状态"""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class TaskType(str, Enum):
    """任务类型"""

    CRON = "cron"  # Cron表达式定时
    DELAYED = "delayed"  # 延迟执行
    ONCE = "once"  # 单次执行
    INTERVAL = "interval"  # 间隔执行


# ==================== 数据结构 ====================


@dataclass
class CronTask:
    """定时任务"""

    task_id: str
    name: str
    task_type: TaskType
    cron_expression: Optional[str] = None  # Cron表达式
    interval_seconds: Optional[int] = None  # 间隔秒数
    delay_seconds: Optional[int] = None  # 延迟秒数
    run_at: Optional[str] = None  # 执行时间 (ISO格式)

    handler: Optional[Callable] = None  # 处理函数
    handler_module: str = ""  # 处理函数模块
    handler_name: str = ""  # 处理函数名

    args: tuple = field(default_factory=tuple)
    kwargs: Dict = field(default_factory=dict)

    enabled: bool = True
    max_retries: int = 3
    timeout: int = 300  # 超时秒数

    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_run: Optional[str] = None
    next_run: Optional[str] = None
    run_count: int = 0

    metadata: Dict = field(default_factory=dict)


@dataclass
class TaskResult:
    """任务执行结果"""

    task_id: str
    status: TaskStatus
    result: Any = None
    error: Optional[str] = None
    duration: float = 0.0
    executed_at: str = field(default_factory=lambda: datetime.now().isoformat())


# ==================== Cron 调度器 ====================


class CronScheduler:
    """
    Cron 调度器

    功能：
    - Cron表达式解析
    - 任务调度
    - 延迟消息
    - 任务历史
    """

    def __init__(self):
        self._tasks: Dict[str, CronTask] = {}
        self._running_tasks: Dict[str, asyncio.Task] = {}
        self._history: List[TaskResult] = []
        self._initialized = False
        self._scheduler_task: Optional[asyncio.Task] = None

        # 检查间隔
        self._check_interval = 1.0  # 1秒检查一次

    async def initialize(self):
        """初始化调度器"""
        logger.info("[CronScheduler] 初始化...")

        # 加载保存的任务
        await self._load_tasks()

        # 启动调度循环
        self._scheduler_task = asyncio.create_task(self._run_scheduler())

        self._initialized = True
        logger.info(f"[CronScheduler] 已初始化，共 {len(self._tasks)} 个任务")

    async def _run_scheduler(self):
        """调度循环"""
        while True:
            try:
                await self._check_and_run_tasks()
                await asyncio.sleep(self._check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"[CronScheduler] 调度异常: {e}")
                await asyncio.sleep(5)

    async def _check_and_run_tasks(self):
        """检查并执行到期任务"""
        now = datetime.now()

        for task_id, task in self._tasks.items():
            if not task.enabled:
                continue

            if task_id in self._running_tasks:
                continue

            # 计算下次执行时间
            if task.task_type == TaskType.CRON and task.cron_expression:
                next_run = self._get_next_run(task.cron_expression, task.last_run)
                task.next_run = next_run.isoformat() if next_run else None

                if next_run and now >= next_run:
                    asyncio.create_task(self._execute_task(task_id))

            elif task.task_type == TaskType.DELAYED and task.delay_seconds:
                if not task.last_run:
                    # 首次执行
                    run_at = datetime.fromisoformat(task.created_at) + timedelta(
                        seconds=task.delay_seconds
                    )
                    task.next_run = run_at.isoformat()

                    if now >= run_at:
                        asyncio.create_task(self._execute_task(task_id))

            elif task.task_type == TaskType.INTERVAL and task.interval_seconds:
                if not task.next_run:
                    task.next_run = (
                        datetime.fromisoformat(task.created_at)
                        + timedelta(seconds=task.interval_seconds)
                    ).isoformat()
                else:
                    next_run = datetime.fromisoformat(task.next_run)
                    if now >= next_run:
                        task.next_run = (
                            next_run + timedelta(seconds=task.interval_seconds)
                        ).isoformat()
                        asyncio.create_task(self._execute_task(task_id))

    def _get_next_run(
        self, cron_expr: str, last_run: Optional[str]
    ) -> Optional[datetime]:
        """获取下次执行时间"""
        try:
            base_time = datetime.now()
            if last_run:
                base_time = datetime.fromisoformat(last_run)

            cron = croniter(cron_expr, base_time)
            return cron.get_next(datetime)
        except Exception as e:
            logger.warning(f"[CronScheduler] Cron解析失败: {e}")
            return None

    async def _execute_task(self, task_id: str):
        """执行任务"""
        task = self._tasks.get(task_id)
        if not task:
            return

        # 标记为运行中
        self._running_tasks[task_id] = asyncio.current_task()
        task.status = TaskStatus.RUNNING

        start_time = datetime.now()
        logger.info(f"[CronScheduler] 执行任务: {task.name} ({task_id})")

        result = None
        error = None
        status = TaskStatus.COMPLETED

        try:
            # 执行任务
            if task.handler:
                if asyncio.iscoroutinefunction(task.handler):
                    result = await asyncio.wait_for(
                        task.handler(*task.args, **task.kwargs), timeout=task.timeout
                    )
                else:
                    result = task.handler(*task.args, **task.kwargs)

            # 处理延迟消息
            elif task.handler_module and task.handler_name:
                result = await self._execute_external_handler(task)

        except asyncio.TimeoutError:
            error = f"任务执行超时 ({task.timeout}秒)"
            status = TaskStatus.FAILED
            logger.error(f"[CronScheduler] {error}")

        except Exception as e:
            error = str(e)
            status = TaskStatus.FAILED
            logger.error(f"[CronScheduler] 任务执行失败: {e}")

        finally:
            # 记录结果
            duration = (datetime.now() - start_time).total_seconds()
            task_result = TaskResult(
                task_id=task_id,
                status=status,
                result=str(result)[:500] if result else None,
                error=error,
                duration=duration,
            )
            self._history.append(task_result)

            # 更新任务状态
            task.last_run = datetime.now().isoformat()
            task.run_count += 1

            # 移除运行中标记
            self._running_tasks.pop(task_id, None)

            # 如果是单次任务，标记完成
            if task.task_type == TaskType.ONCE:
                task.enabled = False

    async def _execute_external_handler(self, task: CronTask) -> Any:
        """执行外部处理器"""
        # 可以通过消息系统发送延迟消息
        logger.info(
            f"[CronScheduler] 外部处理器: {task.handler_module}.{task.handler_name}"
        )
        return f"任务执行: {task.name}"

    async def _load_tasks(self):
        """加载任务"""
        # 从数据库或配置文件加载
        pass

    async def _save_tasks(self):
        """保存任务"""
        # 保存到数据库或配置文件
        pass

    # ==================== 公共 API ====================

    def add_cron_task(
        self,
        name: str,
        cron_expression: str,
        handler: Callable = None,
        handler_module: str = "",
        handler_name: str = "",
        args: tuple = (),
        kwargs: Dict = None,
        enabled: bool = True,
        max_retries: int = 3,
        timeout: int = 300,
    ) -> str:
        """添加Cron任务"""
        task_id = str(uuid.uuid4())[:8]

        task = CronTask(
            task_id=task_id,
            name=name,
            task_type=TaskType.CRON,
            cron_expression=cron_expression,
            handler=handler,
            handler_module=handler_module,
            handler_name=handler_name,
            args=args,
            kwargs=kwargs or {},
            enabled=enabled,
            max_retries=max_retries,
            timeout=timeout,
        )

        self._tasks[task_id] = task
        logger.info(f"[CronScheduler] 添加Cron任务: {name} ({task_id})")

        return task_id

    def add_delayed_task(
        self,
        name: str,
        delay_seconds: int,
        handler: Callable = None,
        handler_module: str = "",
        handler_name: str = "",
        args: tuple = (),
        kwargs: Dict = None,
    ) -> str:
        """添加延迟任务"""
        task_id = str(uuid.uuid4())[:8]

        task = CronTask(
            task_id=task_id,
            name=name,
            task_type=TaskType.DELAYED,
            delay_seconds=delay_seconds,
            handler=handler,
            handler_module=handler_module,
            handler_name=handler_name,
            args=args,
            kwargs=kwargs or {},
        )

        self._tasks[task_id] = task
        logger.info(f"[CronScheduler] 添加延迟任务: {name} ({delay_seconds}秒)")

        return task_id

    def add_interval_task(
        self,
        name: str,
        interval_seconds: int,
        handler: Callable = None,
        handler_module: str = "",
        handler_name: str = "",
        args: tuple = (),
        kwargs: Dict = None,
    ) -> str:
        """添加间隔任务"""
        task_id = str(uuid.uuid4())[:8]

        task = CronTask(
            task_id=task_id,
            name=name,
            task_type=TaskType.INTERVAL,
            interval_seconds=interval_seconds,
            handler=handler,
            handler_module=handler_module,
            handler_name=handler_name,
            args=args,
            kwargs=kwargs or {},
        )

        self._tasks[task_id] = task
        logger.info(f"[CronScheduler] 添加间隔任务: {name} ({interval_seconds}秒)")

        return task_id

    def enable_task(self, task_id: str) -> bool:
        """启用任务"""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = True
            return True
        return False

    def disable_task(self, task_id: str) -> bool:
        """禁用任务"""
        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            return True
        return False

    def cancel_task(self, task_id: str) -> bool:
        """取消任务"""
        if task_id in self._running_tasks:
            self._running_tasks[task_id].cancel()
            del self._running_tasks[task_id]

        if task_id in self._tasks:
            self._tasks[task_id].enabled = False
            return True
        return False

    def delete_task(self, task_id: str) -> bool:
        """删除任务"""
        self.cancel_task(task_id)
        if task_id in self._tasks:
            del self._tasks[task_id]
            return True
        return False

    def get_task(self, task_id: str) -> Optional[CronTask]:
        """获取任务"""
        return self._tasks.get(task_id)

    def list_tasks(self, enabled_only: bool = False) -> List[Dict]:
        """列出任务"""
        result = []
        for task in self._tasks.values():
            if enabled_only and not task.enabled:
                continue
            result.append(
                {
                    "task_id": task.task_id,
                    "name": task.name,
                    "type": task.task_type.value,
                    "enabled": task.enabled,
                    "cron": task.cron_expression,
                    "interval": task.interval_seconds,
                    "delay": task.delay_seconds,
                    "next_run": task.next_run,
                    "last_run": task.last_run,
                    "run_count": task.run_count,
                }
            )
        return result

    def get_history(self, limit: int = 50) -> List[Dict]:
        """获取任务历史"""
        return [
            {
                "task_id": r.task_id,
                "status": r.status.value,
                "result": r.result,
                "error": r.error,
                "duration": f"{r.duration:.2f}s",
                "executed_at": r.executed_at,
            }
            for r in self._history[-limit:]
        ]

    def get_stats(self) -> Dict:
        """获取统计"""
        total = len(self._tasks)
        enabled = sum(1 for t in self._tasks.values() if t.enabled)
        running = len(self._running_tasks)

        history_total = len(self._history)
        history_success = sum(
            1 for r in self._history if r.status == TaskStatus.COMPLETED
        )

        return {
            "total_tasks": total,
            "enabled_tasks": enabled,
            "disabled_tasks": total - enabled,
            "running_tasks": running,
            "history_total": history_total,
            "history_success": history_success,
            "history_failed": history_total - history_success,
        }

    async def shutdown(self):
        """关闭调度器"""
        logger.info("[CronScheduler] 关闭中...")

        # 取消所有运行中的任务
        for task in self._running_tasks.values():
            task.cancel()

        # 停止调度循环
        if self._scheduler_task:
            self._scheduler_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._scheduler_task

        # 保存任务状态
        await self._save_tasks()

        logger.info("[CronScheduler] 已关闭")


# ==================== 全局实例 ====================


_cron_scheduler: Optional[CronScheduler] = None


def get_cron_scheduler() -> CronScheduler:
    """获取Cron调度器"""
    global _cron_scheduler
    if _cron_scheduler is None:
        _cron_scheduler = CronScheduler()
    return _cron_scheduler


async def initialize_cron_scheduler() -> CronScheduler:
    """初始化Cron调度器"""
    scheduler = get_cron_scheduler()
    await scheduler.initialize()
    return scheduler


# ==================== 便捷函数 ====================


async def schedule_cron(
    name: str,
    cron_expression: str,
    handler: Callable = None,
    **kwargs,
) -> str:
    """便捷函数：添加Cron任务"""
    scheduler = get_cron_scheduler()
    return scheduler.add_cron_task(name, cron_expression, handler, **kwargs)


async def schedule_delayed(
    name: str,
    delay_seconds: int,
    handler: Callable = None,
    **kwargs,
) -> str:
    """便捷函数：添加延迟任务"""
    scheduler = get_cron_scheduler()
    return scheduler.add_delayed_task(name, delay_seconds, handler, **kwargs)


async def schedule_interval(
    name: str,
    interval_seconds: int,
    handler: Callable = None,
    **kwargs,
) -> str:
    """便捷函数：添加间隔任务"""
    scheduler = get_cron_scheduler()
    return scheduler.add_interval_task(name, interval_seconds, handler, **kwargs)


__all__ = [
    "TaskStatus",
    "TaskType",
    "CronTask",
    "TaskResult",
    "CronScheduler",
    "get_cron_scheduler",
    "initialize_cron_scheduler",
    "schedule_cron",
    "schedule_delayed",
    "schedule_interval",
]

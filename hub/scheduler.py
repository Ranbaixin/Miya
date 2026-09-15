"""
任务调度
管理和调度系统任务
"""

import asyncio
import contextlib
import heapq
import json
import logging
import sys
import threading
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class Task:
    """任务类"""

    def __init__(
        self,
        task_id: str,
        task_type: str,
        priority: int,
        data: Dict,
        execute_at: Optional[datetime] = None,
        repeat_daily_time: Optional[str] = None,
    ):
        self.task_id = task_id
        self.task_type = task_type
        self.priority = priority
        self.data = data
        self.created_at = datetime.now()
        self.scheduled_at = None
        self.execute_at = execute_at or datetime.now()
        self.completed_at = None
        self.status = "pending"
        # 2026-08：每日重复时间（HH:MM），执行后自动重排到次日同一时刻
        self.repeat_daily_time = repeat_daily_time

    def __lt__(self, other):
        # 按执行时间排序，如果时间相同则按优先级
        if self.execute_at != other.execute_at:
            return self.execute_at < other.execute_at
        return self.priority < other.priority


class Scheduler:
    """任务调度器"""

    def __init__(self, tool_registry=None, onebot_client=None):
        import threading

        self.task_queue = []
        self._queue_lock = threading.Lock()  # 跨线程安全锁
        self.running_tasks = {}
        self.completed_tasks = {}
        self.task_history = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._thread: Optional[threading.Thread] = None
        self.tool_registry = tool_registry
        self.onebot_client = onebot_client
        self.terminal_callback: Optional[Callable[[str], Any]] = None  # 终端模式回调
        # 2026-09：pending 任务持久化（此前重启全丢；data/ 已在 .gitignore）
        self._persist_path = Path("data/scheduler_tasks.json")

    # ==================== 持久化 ====================

    def _save_persist(self) -> None:
        """把 pending 任务全量落盘（任务量小，全量写可接受）"""
        try:
            self._persist_path.parent.mkdir(parents=True, exist_ok=True)
            with self._queue_lock:
                pending = [
                    {
                        "task_id": t.task_id,
                        "task_type": t.task_type,
                        "priority": t.priority,
                        "data": t.data,
                        "execute_at": t.execute_at.isoformat(),
                        "repeat_daily_time": t.repeat_daily_time,
                    }
                    for t in self.task_queue
                ]
            self._persist_path.write_text(
                json.dumps(pending, ensure_ascii=False, indent=2), encoding="utf-8"
            )
        except Exception as e:  # noqa: BLE001 — 持久化失败不影响调度
            logger.warning(f"调度任务落盘失败: {e}")

    def _load_persist(self) -> None:
        """启动时恢复 pending 任务：未来的入队；过期的 10 分钟宽限内照常执行，超出丢弃"""
        if not self._persist_path.exists():
            return
        try:
            pending = json.loads(self._persist_path.read_text(encoding="utf-8"))
        except (OSError, ValueError) as e:
            logger.warning(f"调度任务持久化文件损坏，忽略: {e}")
            return
        now = datetime.now()
        grace = timedelta(minutes=10)
        restored, dropped = 0, 0
        for item in pending if isinstance(pending, list) else []:
            try:
                execute_at = datetime.fromisoformat(item["execute_at"])
            except (KeyError, ValueError, TypeError):
                dropped += 1
                continue
            if execute_at < now - grace:
                dropped += 1
                continue
            task = Task(
                task_id=item["task_id"],
                task_type=item["task_type"],
                priority=item.get("priority", 5),
                data=item.get("data", {}),
                execute_at=execute_at,
                repeat_daily_time=item.get("repeat_daily_time"),
            )
            with self._queue_lock:
                heapq.heappush(self.task_queue, task)
            restored += 1
        if restored or dropped:
            logger.info(f"调度任务恢复: 入队 {restored} 个，丢弃过期 {dropped} 个")

    async def start(self):
        """启动调度器"""
        if self._running:
            logger.warning("调度器已经在运行")
            return

        self._running = True
        self._load_persist()
        self._task = asyncio.create_task(self._run_loop())
        logger.info("任务调度器已启动")

    def start_background(self):
        """在后台线程中启动调度器"""
        if self._running:
            logger.warning("调度器已经在运行")
            return

        def run_in_thread():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self.start())
                loop.run_forever()
            except Exception as e:  # noqa: BLE001 — 线程边界异常仅记录防止崩溃
                logger.error(f"调度器线程错误: {e}")
            finally:
                loop.close()

        self._thread = threading.Thread(target=run_in_thread, daemon=True)
        self._thread.start()
        logger.info("任务调度器已在后台线程中启动")

    async def stop(self):
        """停止调度器"""
        self._running = False
        if self._task:
            self._task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await self._task
        logger.info("任务调度器已停止")

    async def _run_loop(self):
        """调度循环"""
        while self._running:
            try:
                # 检查是否有待执行的任务
                with self._queue_lock:
                    has_tasks = bool(self.task_queue)
                    if has_tasks:
                        now = datetime.now()
                        next_task = self.task_queue[0]  # peek under lock
                if has_tasks:
                    print(
                        f"[SCHEDULER] Queue has {len(self.task_queue)} tasks, next: {next_task.execute_at}",
                        file=sys.stderr,
                    )
                    if next_task.execute_at <= now:
                        with self._queue_lock:
                            heapq.heappop(self.task_queue)
                        logger.info(f"执行定时任务: {next_task.task_id}, 类型: {next_task.task_type}")
                        print(
                            f"[SCHEDULER] Executing task {next_task.task_id}",
                            file=sys.stderr,
                        )
                        await self._execute_task(next_task)

                # 等待一段时间再检查
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"调度循环错误: {e}", exc_info=True)

    async def _execute_task(self, task: Task):
        """执行任务"""
        task.status = "running"
        self.running_tasks[task.task_id] = task

        try:
            # 构建工具上下文
            tool_context = {
                "onebot_client": self.onebot_client,
                "send_like_callback": getattr(self.onebot_client, "send_like", None) if self.onebot_client else None,
                "user_id": task.data.get("target_id"),
                "group_id": task.data.get("target_id") if task.data.get("target_type") == "group" else None,
                "message_type": task.data.get("target_type", "private"),
                "sender_name": "scheduled_task",
            }

            # 根据任务类型执行不同的操作
            if task.task_type == "scheduled_reminder":
                # 定时提醒任务 - 发送消息提醒
                data = task.data
                target_type = data.get("target_type", "private")
                target_id = data.get("target_id")
                message = data.get("message", "")

                logger.info(f"执行提醒任务: 目标={target_type}_{target_id}, 消息={message}")

                # 终端模式或没有 onebot_client 时，记录日志提醒
                if not self.onebot_client:
                    logger.info(f"【定时提醒】{message}")
                    # 可以通过回调通知终端
                    if hasattr(self, "terminal_callback") and self.terminal_callback:
                        try:
                            await self.terminal_callback(message)
                        except Exception as e:  # noqa: BLE001 — 终端回调失败仅记录
                            logger.error(f"终端回调失败: {e}")
                else:
                    # 使用 onebot_client 发送消息
                    try:
                        if target_type == "group":
                            await self.onebot_client.send_group_message(target_id, message)
                            logger.info(f"提醒消息已发送到群 {target_id}")
                        else:
                            await self.onebot_client.send_private_message(target_id, message)
                            logger.info(f"提醒消息已发送到用户 {target_id}")
                    except Exception as e:
                        logger.error(f"发送提醒消息失败: {e}", exc_info=True)

            elif task.task_type == "scheduled_message":
                # 定时发送消息任务
                data = task.data
                target_type = data.get("target_type", "private")
                target_id = data.get("target_id")
                message = data.get("message", "")

                logger.info(f"发送定时消息: 目标={target_type}_{target_id}, 消息={message}")

                # 直接使用 onebot_client 发送消息
                if self.onebot_client:
                    try:
                        if target_type == "group":
                            await self.onebot_client.send_group_message(target_id, message)
                            logger.info(f"定时消息已发送到群 {target_id}")
                        else:
                            await self.onebot_client.send_private_message(target_id, message)
                            logger.info(f"定时消息已发送到用户 {target_id}")
                    except Exception as e:
                        logger.error(f"发送定时消息失败: {e}", exc_info=True)

            elif task.task_type == "scheduled_action":
                # 定时执行动作（如点赞等）
                data = task.data
                action_type = data.get("action_type", "")
                target_id = data.get("target_id")
                message = data.get("message", "")

                logger.info(f"执行定时动作: 类型={action_type}, 目标={target_id}")

                # 根据动作类型调用相应工具
                if self.tool_registry and action_type:
                    from core.tool_adapter import ToolAdapter

                    adapter = ToolAdapter()
                    adapter.set_tool_registry(self.tool_registry)

                    if action_type == "qq_like":
                        args = {
                            "target_user_id": target_id,
                            "times": data.get("times", 1),
                        }
                        result = await adapter.execute_tool("qq_like", args, tool_context)
                        logger.info(f"点赞动作已执行: {result}")

                    elif action_type == "send_poke":
                        args = {
                            "target_user_id": target_id,
                            "group_id": target_id if task.data.get("target_type") == "group" else None,
                        }
                        result = await adapter.execute_tool("send_poke", args, tool_context)
                        logger.info(f"拍一拍动作已执行: {result}")

            # 2026-08：每日重复任务自动重排到次日同一时刻
            if task.repeat_daily_time:
                try:
                    hour, minute = (int(x) for x in task.repeat_daily_time.split(":"))
                    tomorrow = datetime.now() + timedelta(days=1)
                    next_run = tomorrow.replace(hour=hour, minute=minute, second=0, microsecond=0)
                    repeat_task = Task(
                        task_id=f"{task.task_id}_repeat",
                        task_type=task.task_type,
                        priority=task.priority,
                        data=dict(task.data),
                        execute_at=next_run,
                        repeat_daily_time=task.repeat_daily_time,
                    )
                    self.schedule(repeat_task)
                    logger.info(f"每日任务已重排: {task.task_id} → {next_run.isoformat()}")
                except (ValueError, TypeError) as e:
                    logger.warning(f"每日任务重排失败: {e}")

            # 标记任务完成（一次性任务已出队，重写落盘防止重启后重执行；每日任务由 schedule() 落盘）
            self.complete_task(task.task_id, {"result": "success"})
            self._save_persist()

        except Exception as e:
            logger.error(f"任务执行失败 {task.task_id}: {e}", exc_info=True)
            self.fail_task(task.task_id, str(e))
            self._save_persist()

    def schedule(self, task: Task) -> None:
        """添加任务到调度队列"""
        with self._queue_lock:
            heapq.heappush(self.task_queue, task)
        task.scheduled_at = datetime.now()
        self._save_persist()
        logger.info(f"任务已添加到调度队列: {task.task_id}, 执行时间: {task.execute_at}")

    def get_next_task(self) -> Optional[Task]:
        """获取下一个待执行任务"""
        with self._queue_lock:
            if not self.task_queue:
                return None
            task = heapq.heappop(self.task_queue)
        task.status = "running"
        self.running_tasks[task.task_id] = task
        return task

    def complete_task(self, task_id: str, result: Dict = None) -> None:
        """完成任务"""
        if task_id in self.running_tasks:
            task = self.running_tasks.pop(task_id)
            task.status = "completed"
            task.completed_at = datetime.now()
            task.result = result
            self.completed_tasks[task_id] = task
            self.task_history.append(task)

            # 只保留最近100条历史
            if len(self.task_history) > 100:
                self.task_history = self.task_history[-100:]

    def fail_task(self, task_id: str, error: str) -> None:
        """任务失败"""
        if task_id in self.running_tasks:
            task = self.running_tasks.pop(task_id)
            task.status = "failed"
            task.error = error
            task.completed_at = datetime.now()
            self.task_history.append(task)

    def get_task_status(self, task_id: str) -> Optional[Dict]:
        """获取任务状态"""
        # 检查运行中的任务
        if task_id in self.running_tasks:
            task = self.running_tasks[task_id]
            return {
                "status": task.status,
                "type": task.task_type,
                "created_at": task.created_at.isoformat(),
                "running_time": (datetime.now() - task.created_at).total_seconds(),
            }

        # 检查已完成的任务
        if task_id in self.completed_tasks:
            task = self.completed_tasks[task_id]
            return {
                "status": task.status,
                "type": task.task_type,
                "created_at": task.created_at.isoformat(),
                "completed_at": task.completed_at.isoformat(),
            }

        return None

    def get_queue_info(self) -> Dict:
        """获取队列信息"""
        return {
            "pending": len(self.task_queue),
            "running": len(self.running_tasks),
            "completed": len(self.completed_tasks),
            "total": len(self.task_history),
        }

    def cleanup_completed(self, older_than_hours: int = 24) -> int:
        """清理旧任务"""
        cutoff = datetime.now() - timedelta(hours=older_than_hours)

        to_remove = [tid for tid, task in self.completed_tasks.items() if task.completed_at < cutoff]

        for tid in to_remove:
            del self.completed_tasks[tid]

        return len(to_remove)


# ==================== 全局单例 ====================

_global_scheduler: Optional["Scheduler"] = None


def get_global_scheduler() -> "Scheduler":
    """获取全局调度器实例"""
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = Scheduler()
    return _global_scheduler


def set_global_scheduler(scheduler: "Scheduler"):
    """设置全局调度器实例"""
    global _global_scheduler
    _global_scheduler = scheduler

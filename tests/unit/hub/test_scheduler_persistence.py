"""调度器持久化 + 定时任务检测回归测试（定时提醒时间解析修复）。

覆盖：pending 任务落盘/恢复/过期宽限与丢弃、decision_hub 定时检测的
解析成功建任务与无法解析放行 LLM 的关键行为变更。
"""

import json
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from hub.scheduler import Scheduler
from core.reminder_time_parser import parse_reminder_time


@pytest.fixture
def scheduler(tmp_path, monkeypatch):
    """独立持久化路径的调度器（不真正启动 run_loop）"""
    s = Scheduler()
    s._persist_path = tmp_path / "scheduler_tasks.json"
    return s


def _make_task(task_id, execute_at, task_type="scheduled_reminder"):
    from hub.scheduler import Task

    return Task(
        task_id=task_id,
        task_type=task_type,
        priority=5,
        data={"message": "测试提醒"},
        execute_at=execute_at,
    )


class TestSchedulerPersistence:
    def test_schedule_persists_to_disk(self, scheduler, tmp_path):
        future = datetime.now() + timedelta(hours=1)
        scheduler.schedule(_make_task("t1", future))

        data = json.loads(scheduler._persist_path.read_text(encoding="utf-8"))
        assert len(data) == 1
        assert data[0]["task_id"] == "t1"

    def test_completion_updates_persist(self, scheduler):
        """一次性任务执行后应从落盘文件移除（防重启重执行）。

        模拟真实流程：schedule 落盘 → 出队执行 → complete → 重写落盘为空。
        """
        scheduler.schedule(_make_task("t1", datetime.now() + timedelta(hours=1)))
        assert len(json.loads(scheduler._persist_path.read_text(encoding="utf-8"))) == 1

        popped = scheduler.get_next_task()  # 出队（对应 _run_loop 的 heappop）
        assert popped.task_id == "t1"
        scheduler.complete_task("t1", {"result": "success"})
        scheduler._save_persist()

        data = json.loads(scheduler._persist_path.read_text(encoding="utf-8"))
        assert data == []

    def test_reload_restores_future_task(self, scheduler, tmp_path):
        future = datetime.now() + timedelta(hours=1)
        scheduler.schedule(_make_task("t1", future))

        fresh = Scheduler()
        fresh._persist_path = scheduler._persist_path
        fresh._load_persist()

        assert len(fresh.task_queue) == 1
        assert fresh.task_queue[0].task_id == "t1"

    def test_reload_drops_expired_beyond_grace(self, scheduler):
        long_past = datetime.now() - timedelta(hours=2)
        scheduler.schedule(_make_task("old", long_past))

        fresh = Scheduler()
        fresh._persist_path = scheduler._persist_path
        fresh._load_persist()

        assert len(fresh.task_queue) == 0

    def test_reload_executes_recently_expired_within_grace(self, scheduler):
        """过期 5 分钟（<10 分钟宽限）→ 恢复入队照常执行。"""
        recent_past = datetime.now() - timedelta(minutes=5)
        scheduler.schedule(_make_task("recent", recent_past))

        fresh = Scheduler()
        fresh._persist_path = scheduler._persist_path
        fresh._load_persist()

        assert len(fresh.task_queue) == 1

    def test_corrupt_file_soft_loads(self, scheduler, tmp_path):
        scheduler._persist_path.write_text("{broken json", encoding="utf-8")
        fresh = Scheduler()
        fresh._persist_path = scheduler._persist_path
        fresh._load_persist()  # 不抛异常
        assert fresh.task_queue == []


# ==================== decision_hub 定时检测 ====================


def _make_hub(capture):
    """构造仅含检测所需依赖的 DecisionHub 实例（绕过重量级 __init__）"""
    from hub.decision_hub import DecisionHub

    hub = DecisionHub.__new__(DecisionHub)

    async def fake_execute_tool(**kwargs):
        capture.update(kwargs)
        return "✅ 定时任务已创建\n任务ID: test123"

    hub.tool_subnet = SimpleNamespace(execute_tool=fake_execute_tool)
    return hub


class TestDetectAndProcessTimerTask:
    async def test_arabic_minutes_creates_task(self):
        """历史能力回归：30分钟后 → 建任务且时间为解析后的绝对时刻。"""
        capture = {}
        hub = _make_hub(capture)
        result = await hub._detect_and_process_timer_task(
            {"group_id": 0}, "qq", "30分钟后提醒我喝水", "12345", "tester"
        )
        assert result is not None
        assert capture["args"]["schedule_time"] != "1分钟后"
        assert capture["args"]["target_type"] == "private"

    async def test_chinese_numeral_time(self):
        """历史缺陷回归：十分钟后 → 正确解析（此前退化为 1 分钟后）。"""
        capture = {}
        hub = _make_hub(capture)
        result = await hub._detect_and_process_timer_task(
            {"group_id": 0}, "qq", "十分钟后提醒我起立", "12345", "tester"
        )
        assert result is not None
        parsed = parse_reminder_time("十分钟后")
        assert capture["args"]["schedule_time"] == parsed.scheduled_at.strftime("%Y-%m-%d %H:%M")

    async def test_unparseable_falls_through_to_llm(self):
        """核心行为变更：关键词命中但时间无法解析 → 返回 None 放行 AI，
        不再错误地创建 1 分钟后的任务。"""
        capture = {}
        hub = _make_hub(capture)
        result = await hub._detect_and_process_timer_task(
            {"group_id": 0}, "qq", "提醒我一件重要的事", "12345", "tester"
        )
        assert result is None
        assert capture == {}  # 未调用 create_schedule_task

    async def test_no_keyword_returns_none(self):
        hub = _make_hub({})
        result = await hub._detect_and_process_timer_task(
            {"group_id": 0}, "qq", "随便聊聊天", "12345", "tester"
        )
        assert result is None

"""统一时间解析器回归测试（定时提醒时间解析修复）。

基准时点 2026-09-15 20:00:00（周一）。
"""

from datetime import datetime

import pytest

from core.reminder_time_parser import parse_reminder_time

NOW = datetime(2026, 9, 15, 20, 0, 0)  # 周一 20:00


def _at(text: str, now: datetime = NOW):
    result = parse_reminder_time(text, now=now)
    return result.scheduled_at if result else None


class TestRelativeTime:
    def test_arabic_minutes(self):
        assert _at("30分钟后提醒我喝水") == NOW.replace(minute=30)

    def test_chinese_numeral_ten(self):
        """历史缺陷回归：十分钟后 → 20:10（此前错误地 1 分钟后）。"""
        assert _at("十分钟后提醒我") == NOW.replace(minute=10)

    def test_chinese_numeral_twenty(self):
        assert _at("二十分钟后叫我") == NOW.replace(minute=20)

    def test_chinese_numeral_fifteen(self):
        assert _at("十五分钟后提醒我") == NOW.replace(minute=15)

    def test_liang_hours(self):
        assert _at("两小时后提醒我") == NOW.replace(hour=22)

    def test_arabic_hours(self):
        """历史缺陷回归：2小时后 → 22:00（此前错误地 1 分钟后）。"""
        assert _at("2小时后提醒我") == NOW.replace(hour=22)

    def test_half_hour(self):
        assert _at("半小时后提醒我") == NOW.replace(minute=30)

    def test_days_later(self):
        result = _at("3天后提醒我复查")
        assert (result - NOW).days == 3


class TestAbsoluteClock:
    def test_tomorrow_morning(self):
        """历史缺陷回归：明天早上8点 → 明天 08:00（此前错误地 1 分钟后）。"""
        assert _at("明天早上8点叫我起床") == datetime(2026, 9, 16, 8, 0)

    def test_tomorrow_evening_chinese(self):
        """明晚九点半 = 明天 21:30（晚语义 +12 小时）。"""
        assert _at("明晚九点半提醒我") == datetime(2026, 9, 16, 21, 30)

    def test_tonight_late(self):
        """今晚11点（20:00 时）= 当天 23:00。"""
        assert _at("今晚11点提醒我") == datetime(2026, 9, 15, 23, 0)

    def test_weekday_evening(self):
        """周五晚上9点：周一 → 本周五 21:00。"""
        assert _at("周五晚上9点提醒我") == datetime(2026, 9, 18, 21, 0)

    def test_afternoon_passed_goes_next_day(self):
        """下午3点（20:00 时已过）→ 明天 15:00。"""
        assert _at("下午3点开会提醒我") == datetime(2026, 9, 16, 15, 0)

    def test_bare_hhmm_next_day_when_passed(self):
        assert _at("15:30提醒我") == datetime(2026, 9, 16, 15, 30)

    def test_full_datetime(self):
        assert _at("2026-09-20 10:00提醒我交报告") == datetime(2026, 9, 20, 10, 0)


class TestDailyRepeat:
    def test_daily_evening(self):
        result = parse_reminder_time("每天21点提醒我写日记", now=NOW)
        assert result is not None
        assert result.repeat_daily_time == "21:00"
        assert result.scheduled_at == datetime(2026, 9, 15, 21, 0)

    def test_daily_morning_passed_goes_tomorrow(self):
        result = parse_reminder_time("每天早上7点提醒我吃早饭", now=NOW)
        assert result.repeat_daily_time == "07:00"
        assert result.scheduled_at == datetime(2026, 9, 16, 7, 0)


class TestNoGuessFallback:
    def test_unparseable_returns_none(self):
        """历史缺陷回归：无法解析必须返回 None（放行 LLM），禁止错误兜底 1 分钟。"""
        for text in ("随便聊聊天", "你好呀", "今天天气怎么样"):
            assert parse_reminder_time(text, now=NOW) is None, text

    def test_bare_number_without_context_rejected(self):
        """裸数字无日期/时段信息不猜。"""
        assert parse_reminder_time("8", now=NOW) is None

    def test_empty(self):
        assert parse_reminder_time("", now=NOW) is None

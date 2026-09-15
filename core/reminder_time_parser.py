"""
定时提醒统一时间解析器（纯函数，无项目内依赖）

修复目标（2026-09）：
  旧逻辑只认"阿拉伯数字+分钟后"，中文数字分支是不可达死代码，小时/绝对时间
  完全不解析，全部错误地退化成"1分钟后"。

支持的语法（从高到低优先）：
  1. 每日重复句式："每天(的)?(21:00|晚上9点|X点Y分)提醒…" → repeat_daily_time
  2. 相对时间：N分钟后/N分钟内、N小时后、N天后、N秒后、半小时后
  3. 中文数字相对：十分钟后/二十分钟后/两小时后/半小时（中文数字合成：十/十五/二十…）
  4. 绝对时钟：[今天|明天|后天|大后天|周X|星期X|下周X][早上|上午|中午|下午|晚上|凌晨]X[点[半|Y分]|HH:MM]
  5. 绝对日期：YYYY-MM-DD HH:MM、MM-DD HH:MM、HH:MM（当日已过自动+1天）

全部失败返回 None——由调用方决定放行 LLM 工具路径，不再错误兜底"1分钟后"。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional

# 中文数字 → 数值（合成规则：十=X0/十X/XX十X）
_CN_DIGIT = {
    "零": 0, "一": 1, "二": 2, "两": 2, "三": 3, "四": 4,
    "五": 5, "六": 6, "七": 7, "八": 8, "九": 9,
}
_CN_UNIT_HOUR = {"小时": 1, "个小时": 1}
_PERIOD_OFFSET = {"凌晨": 0, "早上": 0, "上午": 0, "中午": 0, "下午": 12, "晚上": 12, "傍晚": 12}
_WEEKDAY = {"一": 0, "二": 1, "三": 2, "四": 3, "五": 4, "六": 5, "日": 6, "天": 6}
_DAY_WORD_OFFSET = {
    "今天": 0, "今日": 0, "今晚": 0, "今早": 0,
    "明天": 1, "明日": 1, "明早": 1, "明晚": 1,
    "后天": 2, "大后天": 3,
}


@dataclass
class ReminderTime:
    """解析结果：具体执行时刻 + 可选每日重复时间（HH:MM）"""

    scheduled_at: datetime
    repeat_daily_time: Optional[str] = None
    matched_text: str = ""  # 命中的时间表达片段（日志/回显用）


# ==================== 中文数字合成 ====================

def _cn_to_int(segment: str) -> Optional[int]:
    """中文数字段转数值：支持 一~九、十、十X、X十、X十X、两（0-99）"""
    segment = (segment or "").strip()
    if not segment:
        return None
    if segment.isdigit():
        return int(segment)
    if "十" not in segment:
        # 纯个位
        if len(segment) == 1 and segment in _CN_DIGIT:
            return _CN_DIGIT[segment]
        return None
    tens_part, _, ones_part = segment.partition("十")
    tens = _CN_DIGIT.get(tens_part, 1) if tens_part else 1
    ones = _CN_DIGIT.get(ones_part, 0) if ones_part else 0
    if (tens_part and tens_part not in _CN_DIGIT) or (ones_part and ones_part not in _CN_DIGIT):
        return None
    return tens * 10 + ones


# ==================== 绝对时钟短语 ====================

def _parse_clock_phrase(content: str, now: datetime) -> Optional[tuple]:
    """解析 [日期词][时段]X[点[半|Y分]|HH:MM] 或裸 HH:MM，返回 (datetime, matched)"""
    content = content.strip()

    # 裸 HH:MM 或 日期+HH:MM
    m = re.search(r"(\d{4}-\d{2}-\d{2}\s+)?(\d{1,2}):(\d{2})", content)
    if m:
        date_part = m.group(1)
        hour, minute = int(m.group(2)), int(m.group(3))
        if hour > 23 or minute > 59:
            return None
        if date_part:
            try:
                base = datetime.strptime(date_part.strip(), "%Y-%m-%d")
            except ValueError:
                return None
            target = base.replace(hour=hour, minute=minute)
        else:
            target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if target <= now:
                target += timedelta(days=1)  # 当日已过自动+1天
        return target, m.group(0).strip()

    # [日期词][时段]X点[半|Y分]
    day_word = r"(?:(大后天|后天|明晚|明早|明天|明日|今晚|今早|今天|今日|下周[一二三四五六日天]|本周[一二三四五六日天]|星期[一二三四五六日天]|周[一二三四五六日天])?)?"
    period_word = r"(凌晨|早上|上午|中午|下午|晚上|傍晚)?"
    m = re.search(
        day_word + period_word + r"(\d{1,2}|[零一二两三四五六七八九十]+)点(半|([一二两三四五六七八九十\d]{1,3}))?分?",
        content,
    )
    if not m:
        return None

    day = m.group(1)
    period = m.group(2)
    hour_seg = m.group(3)
    half = m.group(4)
    minute_seg = m.group(5)

    hour = int(hour_seg) if hour_seg.isdigit() else _cn_to_int(hour_seg)
    if hour is None or hour > 24:
        return None
    minute = 30 if half else 0
    if not half and minute_seg:
        minute = int(minute_seg) if minute_seg.isdigit() else _cn_to_int(minute_seg) or 0
    if minute > 59:
        return None

    # 时段偏移：下午/晚上 12 小时制（12 点本身不加，凌晨不加）
    if period in ("下午", "晚上", "傍晚") and hour < 12:
        hour += 12
    # "明晚/今晚"这类日期词自带夜间语义：九点半=21:30 而非 09:30
    if not period and day and day.endswith("晚") and hour < 12:
        hour += 12
    if period == "中午" and hour == 12:
        pass

    target = now.replace(hour=hour % 24, minute=minute, second=0, microsecond=0)

    # 日期词偏移
    day = day or ""
    if day in _DAY_WORD_OFFSET:
        target += timedelta(days=_DAY_WORD_OFFSET[day])
    elif day.startswith(("周", "星期")):
        name = day[-1]
        if name in _WEEKDAY:
            days_ahead = (_WEEKDAY[name] - now.weekday()) % 7
            if days_ahead == 0:
                days_ahead = 7  # 周X 且今天就是周X → 指下周
            target += timedelta(days=days_ahead)
    elif day.startswith("下周"):
        name = day[-1]
        if name in _WEEKDAY:
            days_ahead = (_WEEKDAY[name] - now.weekday()) % 7 + 7
            target += timedelta(days=days_ahead)

    # 时段已指明但时刻早于现在且无日期词 → +1 天（"下午3点"在凌晨执行场景）
    if not day and target <= now and period:
        target += timedelta(days=1)
    if target <= now and not day and not period:
        return None  # 无任何日期/时段信息的裸数字不猜

    return target, m.group(0).strip()


# ==================== 主入口 ====================

def parse_reminder_time(content: str, now: Optional[datetime] = None) -> Optional[ReminderTime]:
    """解析自然语言提醒时间。返回 None 表示无法解析（调用方自行降级，勿猜测兜底）。"""
    if not content:
        return None
    now = now or datetime.now()

    # 1) 每日重复句式（最高优先）：每天(的)?<时刻>
    daily_m = re.search(r"每天(?:的)?(.{1,12}?)(?:提醒|叫我|通知|发送)", content)
    if daily_m:
        clock = _parse_clock_phrase(daily_m.group(1), now.replace(hour=0, minute=0, second=0, microsecond=0))
        if clock:
            target = clock[0]
            if target <= now:
                target += timedelta(days=1)  # 今日该时刻已过 → 明日起
            hhmm = f"{target.hour:02d}:{target.minute:02d}"
            return ReminderTime(
                scheduled_at=target,
                repeat_daily_time=hhmm,
                matched_text=daily_m.group(0),
            )

    # 2) 相对时间：秒/分钟（含"内"）/小时/天/半小时
    relative_seconds = None
    matched_text = ""
    if re.search(r"半\s*小时", content):
        relative_seconds = 30 * 60
        matched_text = "半小时"
    else:
        units = (("秒", 1), ("分钟", 60), ("小时", 3600), ("天", 86400))
        for unit, seconds in units:
            # 阿拉伯数字（含"个"：N个小时后）
            m = re.search(rf"(\d+)\s*个?{re.escape(unit)}[后内]?", content)
            if m and re.search(rf"{re.escape(unit)}\s*[后内]|{re.escape(unit)}$", content):
                relative_seconds = int(m.group(1)) * seconds
                matched_text = m.group(0)
                break
        if relative_seconds is None:
            # 中文数字相对（十分钟后/两小时后/三天后）
            for unit, seconds in units:
                m = re.search(rf"([零一二两三四五六七八九十]+)\s*个?{re.escape(unit)}\s*[后内]", content)
                if m:
                    value = _cn_to_int(m.group(1))
                    if value is not None:
                        relative_seconds = value * seconds
                        matched_text = m.group(0)
                        break

    if relative_seconds is not None and relative_seconds > 0:
        return ReminderTime(
            scheduled_at=now + timedelta(seconds=relative_seconds),
            repeat_daily_time=None,
            matched_text=matched_text,
        )

    # 3) 绝对时钟 / 日期
    clock = _parse_clock_phrase(content, now)
    if clock:
        return ReminderTime(scheduled_at=clock[0], repeat_daily_time=None, matched_text=clock[1])

    return None

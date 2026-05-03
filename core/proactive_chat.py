"""
弥娅主动聊天系统 v2.1 (完整版)
==========
支持：
- 关键词触发
- 时间触发（多时段问候）
- 上下文触发（行为期望跟进）
- 情绪感知触发
- 主动关怀
- AI触发

配置驱动，所有内容可自定义
"""

import asyncio
import hashlib
import logging
import random
import re
from datetime import datetime
from typing import Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


def load_config() -> dict:
    """从 config/proactive_chat.yaml 加载主动聊天配置"""
    try:
        import yaml
        from pathlib import Path

        config_path = Path(__file__).parent.parent / "config" / "proactive_chat.yaml"

        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as f:
                raw_config = yaml.safe_load(f)

            if raw_config and "proactive_chat" in raw_config:
                logger.info("[主动聊天] 从 config/proactive_chat.yaml 加载配置成功")
                return _normalize_config(raw_config["proactive_chat"])
            else:
                logger.warning(
                    "[主动聊天] config/proactive_chat.yaml 中无 proactive_chat 配置，使用默认配置"
                )
                return get_default_config()
        else:
            logger.warning("[主动聊天] config/proactive_chat.yaml 不存在，使用默认配置")
            return get_default_config()
    except ImportError:
        logger.warning("[主动聊天] PyYAML 未安装，尝试从 _base.yaml 加载")
        try:
            from core.personality_loader import get_personality_loader

            loader = get_personality_loader()
            base_config = loader._load_base_config()
            raw_config = loader.get_proactive_chat_config(base_config)

            if raw_config:
                logger.info("[主动聊天] 从 _base.yaml 加载配置成功")
                return _normalize_config(raw_config)
            else:
                return get_default_config()
        except Exception as e:
            logger.warning(f"[主动聊天] 配置加载失败: {e}，使用默认配置")
            return get_default_config()
    except Exception as e:
        logger.warning(f"[主动聊天] 配置加载失败: {e}，使用默认配置")
        return get_default_config()


def _normalize_config(raw: dict) -> dict:
    """将 _base.yaml 的配置格式转换为代码期望的格式"""
    default = get_default_config()

    enabled = raw.get("enabled", default["enabled"])
    quiet_hours = raw.get("quiet_hours", default["limits"]["quiet_hours"])
    max_daily = raw.get("max_daily_messages", default["limits"]["max_daily_per_target"])

    # 上下文触发
    ctx_trigger = raw.get("context_trigger", {})
    expectations = {}
    raw_expectations = ctx_trigger.get("expectations", {})
    if raw_expectations:
        expectations["enabled"] = True
        follow_responses = {}
        for key, responses in raw_expectations.items():
            follow_responses[key] = responses
        expectations["follow_responses"] = follow_responses
    else:
        expectations = default["triggers"]["context"]

    # 情绪感知
    emotion_perc = raw.get("emotion_perception", {})
    emotion_cfg = {
        "enabled": emotion_perc.get(
            "enabled", default["triggers"]["emotion"]["enabled"]
        ),
        "emotion_keywords": emotion_perc.get("emotion_keywords", {}),
        "emotion_responses": emotion_perc.get("emotion_responses", {}),
    }

    # 关键词触发
    kw_trigger = raw.get("keyword_trigger", {})
    keyword_cfg = {
        "enabled": kw_trigger.get("enabled", default["triggers"]["keyword"]["enabled"]),
        "keywords": kw_trigger.get("keywords", []),
        "responses": kw_trigger.get("responses", []),
    }

    # 主动关怀
    check_in = raw.get("check_in", {})
    check_in_cfg = {
        "enabled": check_in.get("enabled", default["triggers"]["check_in"]["enabled"]),
        "check_interval": check_in.get("check_interval", 3600),
        "messages": check_in.get("messages", []),
    }

    # AI触发
    ai_trigger = raw.get("ai_trigger", {})
    ai_cfg = {
        "enabled": ai_trigger.get("enabled", default["triggers"]["ai"]["enabled"]),
        "cooldown": ai_trigger.get("cooldown", 300),
        "check_interval": ai_trigger.get("check_interval", 60),
        "max_per_hour": ai_trigger.get("max_per_hour", 3),
        "system_prompt": ai_trigger.get("system_prompt", ""),
    }

    # 时间感知
    time_aware = raw.get("time_awareness", {})
    greetings = {}
    if time_aware.get("enabled", True):
        time_slots = time_aware.get("time_slots", {})
        for slot_name, slot_data in time_slots.items():
            greetings[slot_name] = {
                "messages": [
                    t
                    for topic in slot_data.get("topics", [])
                    for t in topic.get("templates", [])
                ]
            }
    time_cfg = {
        "enabled": time_aware.get("enabled", default["triggers"]["time"]["enabled"]),
        "check_interval": raw.get("check_interval", 60),
        "greetings": greetings,
    }

    return {
        "enabled": enabled,
        "triggers": {
            "keyword": keyword_cfg,
            "time": time_cfg,
            "context": expectations,
            "emotion": emotion_cfg,
            "check_in": check_in_cfg,
            "ai": ai_cfg,
        },
        "limits": {
            "global_cooldown": 300,
            "max_daily_per_target": max_daily,
            "max_hourly_per_target": raw.get(
                "max_hourly_messages", default["limits"]["max_hourly_per_target"]
            ),
            "duplicate_window": 60,
            "quiet_hours": quiet_hours,
            "quiet_hours_enabled": True,
        },
        "trigger_type_cooldown": raw.get("trigger_type_cooldown", {}),
        "user_message_cooldown": raw.get("user_message_cooldown", 5),
    }


def get_default_config() -> dict:
    """默认配置（简化版）"""
    return {
        "enabled": True,
        "triggers": {
            "keyword": {"enabled": True, "keywords": [], "responses": []},
            "time": {"enabled": True, "check_interval": 60, "greetings": {}},
            "context": {"enabled": True, "check_interval": 300, "expectations": {}},
            "emotion": {"enabled": True},
            "check_in": {"enabled": False},
            "ai": {"enabled": False},
        },
        "limits": {
            "global_cooldown": 300,
            "max_daily_per_target": 10,
            "max_hourly_per_target": 3,
            "duplicate_window": 60,
            "quiet_hours": [23, 0, 1, 2, 3, 4, 5, 6],
            "quiet_hours_enabled": True,
        },
        "trigger_type_cooldown": {
            "context": 60,
            "emotion": 120,
            "keyword": 30,
            "time": 300,
            "check_in": 1800,
            "ai": 180,
        },
        "user_message_cooldown": 5,
    }


@dataclass
class ChatContext:
    """聊天上下文"""

    chat_type: str
    target_id: int
    group_name: Optional[str] = None
    member_count: int = 0
    last_active: Optional[str] = None
    recent_topics: list = field(default_factory=list)
    message_count_today: int = 0
    # 用户行为状态
    user_expectation: Optional[str] = None  # 用户说"吃完"、"下班"等
    detected_emotion: Optional[str] = None  # 检测到的情绪


@dataclass
class ProactiveResult:
    """主动消息结果"""

    should_respond: bool
    message: Optional[str]
    trigger_type: str
    context: Optional[ChatContext] = None


class ProactiveChatSystem:
    """弥娅主动聊天系统 v2.1"""

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._config = load_config()

        # 核心开关
        self._enabled = self._config.get("enabled", True)

        # 触发器配置
        triggers = self._config.get("triggers", {})
        self._keyword_config = triggers.get("keyword", {})
        self._time_config = triggers.get("time", {})
        self._context_config = triggers.get("context", {})
        self._emotion_config = triggers.get("emotion", {})
        self._check_in_config = triggers.get("check_in", {})
        self._ai_config = triggers.get("ai", {})

        # 限制配置
        limits = self._config.get("limits", {})
        self._global_cooldown = limits.get("global_cooldown", 300)
        self._max_daily = limits.get("max_daily_per_target", 10)
        self._max_hourly = limits.get("max_hourly_per_target", 3)
        self._duplicate_window = limits.get("duplicate_window", 60)
        self._quiet_hours = limits.get("quiet_hours", [23, 0, 1, 2, 3, 4, 5, 6])
        self._quiet_hours_enabled = limits.get("quiet_hours_enabled", True)

        # 调试设置
        debug = self._config.get("debug", {})
        self._verbose = debug.get("verbose", False)
        self._log_triggers = debug.get("log_triggers", True)

        # 运行状态
        self._last_trigger_time: dict[int, datetime] = {}
        self._context_cache: dict[int, ChatContext] = {}
        self._user_last_interaction: dict[int, datetime] = {}
        self._message_cache: dict[str, datetime] = {}
        self._daily_count: dict[int, dict] = {}
        self._hourly_count: dict[int, list] = {}

        # 最后检测的期望行为（用于上下文跟进）
        self._last_expectation: dict[int, str] = {}

        # 追踪每种触发类型的最后发送时间
        self._last_trigger_by_type: dict[int, dict[str, datetime]] = {}

        # 追踪已发送消息的内容，避免重复
        self._sent_messages_history: dict[int, list[tuple[str, datetime]]] = {}

        # 从配置加载触发类型冷却时间
        cooldown_config = self._config.get("trigger_type_cooldown", {})
        self._trigger_type_cooldown = (
            cooldown_config
            if cooldown_config
            else {
                "context": 60,
                "emotion": 120,
                "keyword": 30,
                "time": 300,
                "check_in": 1800,
                "ai": 180,
            }
        )

        # 用户发消息后的冷却时间
        self._user_message_cooldown = self._config.get("user_message_cooldown", 5)

    def _check_trigger_type_cooldown(self, target_id: int, trigger_type: str) -> bool:
        """检查同类型触发是否在冷却时间内"""
        min_interval = self._trigger_type_cooldown.get(trigger_type, 60)

        if target_id not in self._last_trigger_by_type:
            return True  # 没有记录，可以触发

        last_time = self._last_trigger_by_type[target_id].get(trigger_type)
        if not last_time:
            return True

        elapsed = (datetime.now() - last_time).total_seconds()
        return elapsed >= min_interval

    def _record_trigger_by_type(self, target_id: int, trigger_type: str):
        """记录某类型的触发时间"""
        if target_id not in self._last_trigger_by_type:
            self._last_trigger_by_type[target_id] = {}
        self._last_trigger_by_type[target_id][trigger_type] = datetime.now()

    def _check_message_content_duplicate(self, target_id: int, message: str) -> bool:
        """检查消息内容是否与最近发送的过于相似"""
        if target_id not in self._sent_messages_history:
            return False

        now = datetime.now()
        # 清理过期记录（保留30分钟内的）
        self._sent_messages_history[target_id] = [
            (msg, t)
            for msg, t in self._sent_messages_history[target_id]
            if (now - t).total_seconds() < 1800
        ]

        # 简化比对：检查前20个字符
        msg_prefix = message[:20] if len(message) > 20 else message

        for prev_msg, _ in self._sent_messages_history[target_id]:
            prev_prefix = prev_msg[:20] if len(prev_msg) > 20 else prev_msg
            # 如果前缀相同，认为是重复
            if msg_prefix == prev_prefix:
                return True

        return False

    def _record_sent_message(self, target_id: int, message: str):
        """记录已发送的消息"""
        if target_id not in self._sent_messages_history:
            self._sent_messages_history[target_id] = []
        self._sent_messages_history[target_id].append((message, datetime.now()))

    def set_ai_client(self, ai_client):
        self.ai_client = ai_client

    def set_personality(self, personality):
        self.personality = personality

    def is_enabled(self) -> bool:
        return self._enabled

    def is_trigger_enabled(self, trigger_type: str) -> bool:
        if trigger_type == "keyword":
            return self._keyword_config.get("enabled", True)
        elif trigger_type == "time":
            return self._time_config.get("enabled", True)
        elif trigger_type == "context":
            return self._context_config.get("enabled", True)
        elif trigger_type == "emotion":
            return self._emotion_config.get("enabled", True)
        elif trigger_type == "check_in":
            return self._check_in_config.get("enabled", False)
        elif trigger_type == "ai":
            return self._ai_config.get("enabled", False)
        return False

    def update_context(self, target_id: int, context: ChatContext):
        self._context_cache[target_id] = context
        self._user_last_interaction[target_id] = datetime.now()

    def record_message(self, target_id: int, chat_type: str, content: str = ""):
        now = datetime.now()
        self._user_last_interaction[target_id] = now

        # 创建或更新上下文
        if target_id not in self._context_cache:
            self._context_cache[target_id] = ChatContext(
                chat_type=chat_type,
                target_id=target_id,
            )

        ctx = self._context_cache[target_id]
        ctx.chat_type = chat_type
        ctx.last_active = now.isoformat()
        ctx.message_count_today += 1

        # 提取话题关键词
        if content:
            keywords = self._extract_keywords(content)
            if keywords:
                ctx.recent_topics = (ctx.recent_topics + keywords)[-5:]

        # 检测期望行为（用户说要做什么）
        expectation = self._detect_expectation(content)
        if expectation:
            ctx.user_expectation = expectation
            self._last_expectation[target_id] = expectation
            logger.info(f"[主动聊天] 检测到期望行为: {expectation}")

        # 检测情绪
        emotion = self._detect_emotion(content)
        if emotion:
            ctx.detected_emotion = emotion
            logger.info(f"[主动聊天] 检测到情绪: {emotion}")

        # 重置每日计数
        if target_id not in self._daily_count:
            self._daily_count[target_id] = {"date": now.date(), "count": 0}
        elif self._daily_count[target_id]["date"] != now.date():
            self._daily_count[target_id] = {"date": now.date(), "count": 0}

    def _extract_keywords(self, text: str) -> list:
        """提取话题关键词"""
        keyword_list = [
            "学习",
            "工作",
            "吃饭",
            "睡觉",
            "游戏",
            "电影",
            "音乐",
            "运动",
            "考试",
        ]
        return [kw for kw in keyword_list if kw in text]

    def _detect_expectation(self, text: str) -> Optional[str]:
        """检测用户的期望行为（说完某事后需要跟进）"""
        expectation_patterns = {
            "吃完": ["吃完", "吃好了", "吃饱", "吃饭"],
            "睡完": ["睡完", "睡醒了", "起床了", "醒来"],
            "锻炼完": ["锻炼完", "运动完", "健身完"],
            "看完": ["看完", "看完啦", "看完了"],
            "看完医生": ["看完医生", "看完病", "检查完"],
            "下班": ["下班", "下班了", "下班啦"],
            "放学": ["放学", "放学了", "下课"],
            "回来": ["回来", "回到家", "回来了"],
            "泡面好了": ["泡面好了", "泡面好了"],
        }

        for expectation, patterns in expectation_patterns.items():
            for pattern in patterns:
                if pattern in text:
                    return expectation
        return None

    def _detect_emotion(self, text: str) -> Optional[str]:
        """检测用户情绪"""
        emotion_keywords = self._emotion_config.get("emotion_keywords", {})

        for emotion, keywords in emotion_keywords.items():
            for keyword in keywords:
                if keyword in text:
                    return emotion
        return None

    def _is_in_quiet_hours(self) -> bool:
        """检查静默时段"""
        if not self._quiet_hours_enabled:
            return False
        return datetime.now().hour in self._quiet_hours

    def _check_cooldown(self, target_id: int) -> bool:
        """检查冷却时间"""
        last_time = self._last_trigger_time.get(target_id)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < self._global_cooldown:
                return False
        return True

    def _check_rate_limits(self, target_id: int) -> bool:
        """检查速率限制"""
        now = datetime.now()
        today = now.date()

        # 每日限制
        if target_id in self._daily_count:
            if self._daily_count[target_id]["date"] == today:
                if self._daily_count[target_id]["count"] >= self._max_daily:
                    return False

        # 每小时限制
        if target_id in self._hourly_count:
            self._hourly_count[target_id] = [
                t
                for t in self._hourly_count[target_id]
                if (now - t).total_seconds() < 3600
            ]
            if len(self._hourly_count[target_id]) >= self._max_hourly:
                return False

        return True

    def _is_duplicate(self, target_id: int, message: str) -> bool:
        """检查重复消息"""
        if not message:
            return True

        msg_hash = hashlib.md5(f"{target_id}:{message[:50]}".encode()).hexdigest()

        if msg_hash in self._message_cache:
            last_time = self._message_cache[msg_hash]
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < self._duplicate_window:
                logger.info(f"[主动聊天] 消息去重: {message[:30]}...")
                return True
            del self._message_cache[msg_hash]

        self._message_cache[msg_hash] = datetime.now()

        # 清理过期缓存
        now = datetime.now()
        self._message_cache = {
            k: v
            for k, v in self._message_cache.items()
            if (now - v).total_seconds() < self._duplicate_window * 2
        }

        return False

    def _record_trigger(self, target_id: int):
        """记录触发"""
        now = datetime.now()
        today = now.date()

        self._last_trigger_time[target_id] = now

        if target_id not in self._daily_count:
            self._daily_count[target_id] = {"date": today, "count": 0}
        self._daily_count[target_id]["count"] += 1

        if target_id not in self._hourly_count:
            self._hourly_count[target_id] = []
        self._hourly_count[target_id].append(now)

    async def check_and_respond(
        self, target_id: int, user_message: Optional[str] = None
    ) -> Optional[ProactiveResult]:
        """检查是否需要主动发言"""
        if not self._enabled:
            return None

        # 检查用户是否刚发送了消息
        last_user_msg_time = self._user_last_interaction.get(target_id)
        if last_user_msg_time:
            elapsed = (datetime.now() - last_user_msg_time).total_seconds()
            if elapsed < self._user_message_cooldown:
                return None

        if self._is_in_quiet_hours():
            return None

        if not self._check_cooldown(target_id):
            return None

        if not self._check_rate_limits(target_id):
            return None

        context = self._context_cache.get(target_id)
        if not context:
            return None

        # 1. 上下文触发（行为期望跟进）- 优先级最高
        if self.is_trigger_enabled("context"):
            result = await self._check_context_trigger(target_id, context)
            if result:
                return result

        # 2. 情绪感知触发
        if self.is_trigger_enabled("emotion") and context.detected_emotion:
            result = await self._check_emotion_trigger(
                target_id, context, user_message or ""
            )
            if result:
                return result

        # 3. 关键词触发
        if self.is_trigger_enabled("keyword") and user_message:
            result = await self._check_keyword_trigger(target_id, context, user_message)
            if result:
                return result

        # 4. 时间触发
        if self.is_trigger_enabled("time"):
            result = await self._check_time_trigger(target_id, context)
            if result:
                return result

        # 5. 主动关怀
        if self.is_trigger_enabled("check_in"):
            result = await self._check_check_in_trigger(target_id, context)
            if result:
                return result

        # 6. AI触发
        if self.is_trigger_enabled("ai"):
            result = await self._check_ai_trigger(target_id, context)
            if result:
                return result

        return None

    async def _check_context_trigger(
        self, target_id: int, context: ChatContext
    ) -> Optional[ProactiveResult]:
        """上下文触发 - 行为期望跟进"""
        expectations_config = self._context_config.get("expectations", {})
        if not expectations_config.get("enabled", True):
            return None

        # 检查用户是否有未跟进的期望行为
        user_expectation = context.user_expectation or self._last_expectation.get(
            target_id
        )

        if not user_expectation:
            return None

        # 获取期望跟进回复
        follow_responses = expectations_config.get("follow_responses", {})
        responses = follow_responses.get(
            user_expectation, follow_responses.get("default", [])
        )

        if not responses:
            return None

        # 检查同类型触发冷却
        if not self._check_trigger_type_cooldown(target_id, "context"):
            return None

        message = random.choice(responses)

        # 检查消息内容是否重复
        if self._check_message_content_duplicate(target_id, message):
            return None

        if not self._is_duplicate(target_id, message):
            self._record_trigger(target_id)
            self._record_trigger_by_type(target_id, "context")
            self._record_sent_message(target_id, message)

            # 跟进后清除期望状态
            if target_id in self._last_expectation:
                del self._last_expectation[target_id]
            context.user_expectation = None

            if self._log_triggers:
                logger.info(f"[主动聊天] [上下文触发] target={target_id}: {message}")

            return ProactiveResult(
                should_respond=True,
                message=message,
                trigger_type="context",
                context=context,
            )

        return None

    async def _check_emotion_trigger(
        self, target_id: int, context: ChatContext, user_message: str
    ) -> Optional[ProactiveResult]:
        """情绪感知触发"""
        emotion = context.detected_emotion
        if not emotion:
            return None

        emotion_responses = self._emotion_config.get("emotion_responses", {})
        responses = emotion_responses.get(emotion, [])

        if not responses:
            return None

        # 只有情绪强烈时才回复（这里简单处理，随机触发）
        if random.random() > 0.3:  # 30%概率触发，避免太频繁
            return None

        # 检查同类型触发冷却
        if not self._check_trigger_type_cooldown(target_id, "emotion"):
            return None

        message = random.choice(responses)

        # 检查消息内容是否重复
        if self._check_message_content_duplicate(target_id, message):
            return None

        if not self._is_duplicate(target_id, message):
            self._record_trigger(target_id)
            self._record_trigger_by_type(target_id, "emotion")
            self._record_sent_message(target_id, message)

            # 清除情绪状态
            context.detected_emotion = None

            if self._log_triggers:
                logger.info(
                    f"[主动聊天] [情绪触发] target={target_id}, emotion={emotion}: {message}"
                )

            return ProactiveResult(
                should_respond=True,
                message=message,
                trigger_type="emotion",
                context=context,
            )

        return None

    async def _check_keyword_trigger(
        self, target_id: int, context: ChatContext, user_message: str
    ) -> Optional[ProactiveResult]:
        """关键词触发"""
        keywords = self._keyword_config.get("keywords", [])
        matched = [kw for kw in keywords if kw in user_message]

        if not matched:
            return None

        if self._log_triggers:
            logger.info(
                f"[主动聊天] [关键词触发] target={target_id}, matched={matched}"
            )

        responses = self._keyword_config.get("responses", [])
        if responses:
            message = random.choice(responses)
        else:
            message = "嗯呢，收到啦~"

        # 检查同类型触发冷却
        if not self._check_trigger_type_cooldown(target_id, "keyword"):
            return None

        # 检查消息内容是否重复
        if self._check_message_content_duplicate(target_id, message):
            return None

        if not self._is_duplicate(target_id, message):
            self._record_trigger(target_id)
            self._record_trigger_by_type(target_id, "keyword")
            self._record_sent_message(target_id, message)
            return ProactiveResult(
                should_respond=True,
                message=message,
                trigger_type="keyword",
                context=context,
            )

        return None

    async def _check_time_trigger(
        self, target_id: int, context: ChatContext
    ) -> Optional[ProactiveResult]:
        """时间触发 - 多时段问候"""
        now = datetime.now()
        hour = now.hour

        greetings = self._time_config.get("greetings", {})

        # 判断时段并获取消息
        messages = []

        # 早上 6-12
        if 6 <= hour < 12:
            messages = greetings.get("morning", {}).get("messages", [])
        # 中午 12-14
        elif 12 <= hour < 14:
            messages = greetings.get("noon", {}).get("messages", [])
            if not messages:
                messages = greetings.get("afternoon", {}).get("messages", [])
        # 下午 14-18
        elif 14 <= hour < 18:
            messages = greetings.get("afternoon", {}).get("messages", [])
        # 傍晚 18-22
        elif 18 <= hour < 22:
            messages = greetings.get("evening", {}).get("messages", [])
        # 深夜 22-6
        else:
            messages = greetings.get("night", {}).get("messages", [])

        if not messages:
            return None

        # 检查同类型触发冷却
        if not self._check_trigger_type_cooldown(target_id, "time"):
            return None

        message = random.choice(messages)

        # 检查消息内容是否重复
        if self._check_message_content_duplicate(target_id, message):
            return None

        if not self._is_duplicate(target_id, message):
            self._record_trigger(target_id)
            self._record_trigger_by_type(target_id, "time")
            self._record_sent_message(target_id, message)

            if self._log_triggers:
                logger.info(f"[主动聊天] [时间触发] target={target_id}: {message}")

            return ProactiveResult(
                should_respond=True,
                message=message,
                trigger_type="time",
                context=context,
            )

        return None

    async def _check_check_in_trigger(
        self, target_id: int, context: ChatContext
    ) -> Optional[ProactiveResult]:
        """主动关怀触发"""
        check_in_config = self._check_in_config
        check_interval = check_in_config.get("check_interval", 3600)

        # 检查上次互动时间
        last_interaction = self._user_last_interaction.get(target_id)
        if last_interaction:
            elapsed = (datetime.now() - last_interaction).total_seconds()
            if elapsed < check_interval:
                return None

        # 检查是否应该触发关怀
        if random.random() > 0.2:  # 20%概率触发
            return None

        messages = check_in_config.get("messages", [])
        if not messages:
            return None

        # 检查同类型触发冷却
        if not self._check_trigger_type_cooldown(target_id, "check_in"):
            return None

        message = random.choice(messages)

        # 检查消息内容是否重复
        if self._check_message_content_duplicate(target_id, message):
            return None

        if not self._is_duplicate(target_id, message):
            self._record_trigger(target_id)
            self._record_trigger_by_type(target_id, "check_in")
            self._record_sent_message(target_id, message)

            if self._log_triggers:
                logger.info(f"[主动聊天] [关怀触发] target={target_id}: {message}")

            return ProactiveResult(
                should_respond=True,
                message=message,
                trigger_type="check_in",
                context=context,
            )

        return None

    async def _check_ai_trigger(
        self, target_id: int, context: ChatContext
    ) -> Optional[ProactiveResult]:
        """AI触发"""
        if not self.ai_client:
            return None

        ai_config = self._ai_config
        cooldown = ai_config.get("cooldown", 300)

        last_time = self._last_trigger_time.get(target_id)
        if last_time:
            elapsed = (datetime.now() - last_time).total_seconds()
            if elapsed < cooldown:
                return None

        try:
            chat_type = "群聊" if context.chat_type == "group" else "私聊"
            group_name = context.group_name or "未知群"
            member_count = context.member_count
            last_active = context.last_active or "未知"
            recent_topics = (
                ", ".join(context.recent_topics) if context.recent_topics else "无"
            )

            prompt = f"""判断是否应该主动和用户聊天。
聊天信息：
- 类型: {chat_type}
- 群名称: {group_name}
- 成员数: {member_count}
- 用户最后活跃: {last_active}
- 最近话题: {recent_topics}

如果需要回复，请生成一句简短温暖的话（不超过20字）。
如果不需要回复，请回复"SKIP"。"""

            response = await self.ai_client.chat(
                messages=[{"role": "user", "content": prompt}],
                max_tokens=self._config.get("max_tokens", 50),
                temperature=self._config.get("temperature", 0.7),
            )

            # response 直接是字符串，不需要 .get() 解析
            message = (
                response.strip() if isinstance(response, str) else str(response).strip()
            )

            if message.upper() == "SKIP" or not message:
                return None

            # 检查同类型触发冷却
            if not self._check_trigger_type_cooldown(target_id, "ai"):
                return None

            # 检查消息内容是否重复
            if self._check_message_content_duplicate(target_id, message):
                return None

            if not self._is_duplicate(target_id, message):
                self._record_trigger(target_id)
                self._record_trigger_by_type(target_id, "ai")
                self._record_sent_message(target_id, message)

                if self._log_triggers:
                    logger.info(f"[主动聊天] [AI触发] target={target_id}: {message}")

                return ProactiveResult(
                    should_respond=True,
                    message=message,
                    trigger_type="ai",
                    context=context,
                )

        except Exception as e:
            logger.warning(f"[主动聊天] AI触发失败: {e}")

        return None


# 全局实例
_proactive_system: Optional[ProactiveChatSystem] = None


def get_proactive_chat_system() -> ProactiveChatSystem:
    """获取主动聊天系统实例"""
    global _proactive_system
    if _proactive_system is None:
        _proactive_system = ProactiveChatSystem()
    return _proactive_system

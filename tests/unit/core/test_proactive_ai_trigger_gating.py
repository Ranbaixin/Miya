"""主动聊天 AI 判断评估节流回归测试（主动聊天降频与 token 优化）。

此前实际行为：300s 全局冷却驱动的"每 5 分钟一次 AI 判断调用"（带全量人设 prompt 覆盖）。
优化后：独立 eval_interval_seconds 评估节流（默认 2 小时）+ 类型冷却前置（不先生成再丢弃）
+ use_miya_prompt=False（保留构建好的 system prompt）+ 上下文截断 + 无互动会话 TTL 清理。
"""

from datetime import datetime, timedelta

import pytest

from core.proactive_chat import ChatContext, ProactiveChatSystem, _normalize_config


class FakeAIClient:
    """记录调用参数的假 AI 客户端"""

    def __init__(self, response="SKIP"):
        self.response = response
        self.calls = []

    async def chat(self, **kwargs):
        self.calls.append(kwargs)
        return self.response


@pytest.fixture
def system():
    """每次测试用全新单例（构造后按场景覆盖属性，保证确定性）"""
    ProactiveChatSystem._instance = None
    s = ProactiveChatSystem()
    s._ai_eval_interval = 7200
    yield s
    ProactiveChatSystem._instance = None


def _ctx(target_id=42):
    return ChatContext(
        chat_type="private",
        target_id=target_id,
        last_active=datetime.now().isoformat(),
    )


def _setup(system, fake):
    system.ai_client = fake
    system.personality = None
    system._scene_enabled = False
    system._context_cache[42] = _ctx()


class TestAiEvalThrottle:
    async def test_eval_interval_blocks_ai_call(self, system):
        """距上次评估不足 eval_interval_seconds → 不调 AI（此前每 5 分钟烧一次）。"""
        fake = FakeAIClient()
        _setup(system, fake)
        system._last_ai_eval[42] = datetime.now() - timedelta(minutes=30)

        result = await system._check_ai_trigger(42, system._context_cache[42])

        assert result is None
        assert fake.calls == []

    async def test_skip_still_records_eval(self, system):
        """AI 判 SKIP → 不发言，但评估时间已记录（SKIP 也是一次评估）。"""
        fake = FakeAIClient(response="SKIP")
        _setup(system, fake)

        result = await system._check_ai_trigger(42, system._context_cache[42])

        assert result is None
        assert len(fake.calls) == 1
        assert 42 in system._last_ai_eval

    async def test_sent_message_records_eval_and_throttles(self, system):
        """AI 生成消息 → 发送并记录；立即再查不会二次调用（评估节流生效）。"""
        fake = FakeAIClient(response="在忙什么呀~")
        _setup(system, fake)

        result = await system._check_ai_trigger(42, system._context_cache[42])
        assert result is not None
        assert result.message == "在忙什么呀~"
        assert result.trigger_type == "ai"

        await system._check_ai_trigger(42, system._context_cache[42])
        assert len(fake.calls) == 1


class TestGateOrdering:
    async def test_type_cooldown_blocks_before_call(self, system):
        """同类型发送冷却期内 → 不调 AI（冷却检查已前置，不再先生成再丢弃）。"""
        fake = FakeAIClient()
        _setup(system, fake)
        system._last_trigger_by_type[42] = {"ai": datetime.now() - timedelta(minutes=10)}

        result = await system._check_ai_trigger(42, system._context_cache[42])

        assert result is None
        assert fake.calls == []

    async def test_use_miya_prompt_false_and_tools_empty(self, system):
        """判断调用必须 use_miya_prompt=False（否则构建好的 system prompt 被全量人设覆盖）+ tools=[]。"""
        fake = FakeAIClient(response="SKIP")
        _setup(system, fake)

        await system._check_ai_trigger(42, system._context_cache[42])

        kwargs = fake.calls[0]
        assert kwargs["use_miya_prompt"] is False
        assert kwargs["tools"] == []
        assert kwargs["tool_choice"] == "none"

    async def test_context_truncated(self, system):
        """深度上下文注入前截断到 600 字。"""
        fake = FakeAIClient(response="SKIP")
        _setup(system, fake)

        async def big_rich(_target_id):
            return "记" * 5000

        system._rich_context_provider = big_rich

        await system._check_ai_trigger(42, system._context_cache[42])

        user_msg = fake.calls[0]["messages"][-1].content
        assert "记" * 600 in user_msg
        assert "记" * 601 not in user_msg


class TestTargetTtlPrune:
    def test_stale_target_pruned_fresh_kept(self, system):
        """超过 TTL 无互动的会话被清理（含各状态字典），近期会话保留。"""
        system._target_ttl_seconds = 168 * 3600
        old_ctx = ChatContext(
            chat_type="private",
            target_id=1,
            last_active=(datetime.now() - timedelta(days=8)).isoformat(),
        )
        fresh_ctx = _ctx(target_id=2)
        system._context_cache = {1: old_ctx, 2: fresh_ctx}
        system._user_last_interaction[1] = datetime.now() - timedelta(days=8)
        system._last_trigger_time[1] = datetime.now()
        system._last_ai_eval[1] = datetime.now()

        system._prune_stale_targets()

        assert 1 not in system._context_cache
        assert 1 not in system._last_trigger_time
        assert 1 not in system._last_ai_eval
        assert 1 not in system._user_last_interaction
        assert 2 in system._context_cache

    def test_ttl_zero_disables_prune(self, system):
        system._target_ttl_seconds = 0
        system._context_cache = {
            1: ChatContext(
                chat_type="private",
                target_id=1,
                last_active=(datetime.now() - timedelta(days=365)).isoformat(),
            )
        }
        system._prune_stale_targets()
        assert 1 in system._context_cache


class TestNormalizeConfig:
    def test_new_keys_consumed(self):
        raw = {
            "enabled": True,
            "check_interval": 30,
            "target_ttl_hours": 72,
            "global_cooldown": 600,
            "ai_trigger": {"enabled": True, "eval_interval_seconds": 3600, "cooldown": 300, "system_prompt": "x"},
            "trigger_type_cooldown": {"ai": 3600},
        }
        cfg = _normalize_config(raw)
        assert cfg["check_interval"] == 30
        assert cfg["target_ttl_hours"] == 72
        assert cfg["global_cooldown"] == 600
        assert cfg["limits"]["global_cooldown"] == 600
        assert cfg["triggers"]["ai"]["eval_interval_seconds"] == 3600
        # 死配置不再透传
        assert "check_interval" not in cfg["triggers"]["ai"]
        assert "max_per_hour" not in cfg["triggers"]["ai"]

    def test_defaults_without_raw_keys(self):
        cfg = _normalize_config({"enabled": True})
        assert cfg["check_interval"] == 45
        assert cfg["target_ttl_hours"] == 168
        assert cfg["limits"]["global_cooldown"] == 300
        assert cfg["triggers"]["ai"]["eval_interval_seconds"] == 7200

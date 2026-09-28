"""mixin ingest 通道测试：感知构建与 route 完全一致；ingest 不触发回复侧事件。"""
import types

import pytest

import core.unified_permission as perm_mod
from core.unified_platform_impl.message_mixin import MessageMixin


class _Host(MessageMixin):
    platform_id = "aiocqhttp"

    def __init__(self):
        self._miya_core = types.SimpleNamespace()
        self.spawned = []
        self.events = []

    def _spawn(self, coro):
        self.spawned.append(coro)
        coro.close()  # 不真正运行，防泄漏

    def _emit_realtime_events(self, content, reply, sender_name):
        self.events.append((content, reply))

    def _after_route(self, content, reply, user_id):
        return _noop_after(content)


async def _noop_after(content):
    return None


@pytest.fixture
def host(monkeypatch):
    h = _Host()
    engine = types.SimpleNamespace(
        is_superadmin=lambda uid, platform: uid == "888",
        is_staff=lambda uid, platform: False,
        _config={"superadmins": {"q": {"name": "然鑫", "ids": {"qq": ["888"]}}}},
    )
    monkeypatch.setattr(perm_mod, "get_permission_engine", lambda: engine)
    return h


@pytest.mark.asyncio
async def test_build_perception_matches_route_shape(host):
    msg, perception = await host._build_perception_message(
        content="你好", user_id="888", user_name="然鑫", message_type="private",
        group_id="", group_name="", sender_role="member", is_at_bot=True, extra=None,
    )
    assert perception["is_owner"] is True
    assert perception["user_id"] == "888"  # 规范 ID 回填
    assert perception["unified_user_id"] == "aiocqhttp_888"
    assert msg.content is perception


@pytest.mark.asyncio
async def test_ingest_channel_calls_decision_hub_ingest_and_emits_user_event(host):
    captured = {}

    async def ingest(message):
        captured["msg"] = message
        return ("CTX", None)

    host._miya_core = types.SimpleNamespace(
        decision_hub=types.SimpleNamespace(ingest_cross_platform=ingest)
    )
    ctx, direct = await host.ingest_to_decision_hub(
        content="在吗", user_id="u1", user_name="小明", message_type="private",
        group_id="", group_name="", sender_role="member", is_at_bot=True, extra=None,
    )
    assert ctx == "CTX" and direct is None
    assert host.events == [("在吗", "")]  # 只发用户消息侧事件，无助手回复事件
    assert len(host.spawned) == 1  # _after_route 已安排
    assert captured["msg"].content["user_id"] == "u1"


@pytest.mark.asyncio
async def test_ingest_channel_not_ready_returns_error_text(host):
    host._miya_core = None
    ctx, direct = await host.ingest_to_decision_hub(
        content="hi", user_id="u1", user_name="", message_type="private",
        group_id="", group_name="", sender_role="member", is_at_bot=True, extra=None,
    )
    assert ctx == "弥娅系统未就绪" and direct is None


@pytest.mark.asyncio
async def test_ingest_channel_exception_returns_error_text(host, monkeypatch):
    async def boom(message):
        raise RuntimeError("db down")

    host._miya_core = types.SimpleNamespace(
        decision_hub=types.SimpleNamespace(ingest_cross_platform=boom)
    )
    ctx, direct = await host.ingest_to_decision_hub(
        content="hi", user_id="u1", user_name="", message_type="private",
        group_id="", group_name="", sender_role="member", is_at_bot=True, extra=None,
    )
    assert "处理消息时出错了" in ctx and direct is None

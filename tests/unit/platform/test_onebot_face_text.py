"""face 表情文本化回归测试（链路修复 Fix 5）。

修复前：字符串分支把 [CQ:face,...] 整体删除（faceText 丢失），array 分支只计数不取文本
→ 纯表情消息空内容被丢弃，弥娅"看不见"小表情。
修复后：face 文本提取（raw.faceText，CQ 实体还原）注入 content，注入点位于
群聊纯表情预过滤之后、空内容丢弃之前。
"""

import pytest

from core.unified_platform_impl.onebot_platform import OneBotPlatform


class TestParseCqFaceText:
    def test_raw_facetext_extracted(self):
        attrs = 'id=222,type=sticker,raw={"faceText":"大怨种","description":"商城表情","faceId":"222"}'
        assert OneBotPlatform._parse_cq_face_text(attrs) == "大怨种"

    def test_cq_entity_comma_restored(self):
        attrs = 'id=1,raw={"faceText":"a&#44;b"}'
        assert OneBotPlatform._parse_cq_face_text(attrs) == "a,b"

    def test_cq_entity_brackets_restored(self):
        attrs = 'id=1,raw={"faceText":"x&#91;y&#93;"}'
        assert OneBotPlatform._parse_cq_face_text(attrs) == "x[y]"

    def test_cq_entity_amp_restored_last(self):
        attrs = 'id=1,raw={"faceText":"m&amp;n"}'
        assert OneBotPlatform._parse_cq_face_text(attrs) == "m&n"

    def test_no_raw_falls_back_to_face_id(self):
        assert OneBotPlatform._parse_cq_face_text("id=123") == "#123"

    def test_malformed_raw_falls_back_to_face_id(self):
        attrs = "id=123,raw={bad json}"
        assert OneBotPlatform._parse_cq_face_text(attrs) == "#123"

    def test_raw_without_facetext_falls_back(self):
        attrs = 'id=5,raw={"description":"x"}'
        assert OneBotPlatform._parse_cq_face_text(attrs) == "#5"


def _make_platform(monkeypatch, captured):
    """构造 mock 边界内的平台实例：捕获 route_to_decision_hub 收到的 content。"""

    async def fake_route(content, **kwargs):
        captured["content"] = content
        captured["kwargs"] = kwargs
        return None

    async def fake_resolve_group_name(group_id):
        return "测试群"

    # DM 合并关闭：本文件专测表情文本注入（route 捕获），与合并器无关
    platform = OneBotPlatform({"bot_qq": "10000", "dm_merge_enabled": False})
    platform.route_to_decision_hub = fake_route
    monkeypatch.setattr(platform, "_is_group_allowed", lambda gid: True)
    monkeypatch.setattr(platform, "_is_user_allowed", lambda uid: True)
    monkeypatch.setattr(platform, "_is_at_bot", lambda raw, qq: False)
    monkeypatch.setattr(platform, "_extract_at_list", lambda raw: [])
    monkeypatch.setattr(platform, "_spawn", lambda coro: None)
    monkeypatch.setattr(platform, "_ensure_decision_hub_refs", lambda: None)
    monkeypatch.setattr(platform, "_resolve_group_name", fake_resolve_group_name)
    return platform


def _private_msg(raw):
    return {
        "message_type": "private",
        "raw_message": raw,
        "sender": {"user_id": 99999, "nickname": "tester"},
        "self_id": 10000,
    }


def _group_msg(raw):
    return {
        "message_type": "group",
        "raw_message": raw,
        "sender": {"user_id": 99999, "nickname": "tester", "role": "member"},
        "group_id": 88888,
        "self_id": 10000,
    }


class TestFaceTextInjection:
    async def test_private_pure_face_string_gets_text(self, monkeypatch):
        """私聊纯表情（CQ 字符串）→ content 注入 [表情:大怨种]，不再被空内容丢弃。"""
        captured = {}
        platform = _make_platform(monkeypatch, captured)
        raw = '[CQ:face,id=222,raw={"faceText":"大怨种"}]'
        await platform._handle_chat_message(_private_msg(raw))
        assert captured.get("content") == "[表情:大怨种]"

    async def test_private_mixed_text_and_face(self, monkeypatch):
        """私聊混合消息 → 文字保留、表情附在后面。"""
        captured = {}
        platform = _make_platform(monkeypatch, captured)
        raw = '哈哈[CQ:face,id=222,raw={"faceText":"大怨种"}]'
        await platform._handle_chat_message(_private_msg(raw))
        assert captured.get("content") == "哈哈 [表情:大怨种]"

    async def test_private_pure_face_array_with_raw_dict(self, monkeypatch):
        """私聊纯表情（array 格式，raw 为 dict）→ faceText 生效。"""
        captured = {}
        platform = _make_platform(monkeypatch, captured)
        raw = [{"type": "face", "data": {"id": "222", "raw": {"faceText": "大怨种"}}}]
        await platform._handle_chat_message(_private_msg(raw))
        assert captured.get("content") == "[表情:大怨种]"

    async def test_private_pure_face_array_with_raw_json_string(self, monkeypatch):
        """私聊纯表情（array 格式，raw 为 JSON 字符串，Lagrange 风格）→ faceText 生效。"""
        captured = {}
        platform = _make_platform(monkeypatch, captured)
        raw = [{"type": "face", "data": {"id": "222", "raw": '{"faceText": "哼"}'}}]
        await platform._handle_chat_message(_private_msg(raw))
        assert captured.get("content") == "[表情:哼]"

    async def test_private_pure_face_without_raw_falls_back_to_id(self, monkeypatch):
        """无私商城信息（普通 QQ 基础表情）→ 兜底 #id 文本，消息不再被丢。"""
        captured = {}
        platform = _make_platform(monkeypatch, captured)
        raw = [{"type": "face", "data": {"id": "18"}}]
        await platform._handle_chat_message(_private_msg(raw))
        assert captured.get("content") == "[表情:#18]"

    async def test_group_pure_face_prefilter_preserved(self, monkeypatch):
        """群聊非主人未@纯表情 → 照旧预过滤，不进决策层（注入点位于预过滤之后的回归保障）。"""
        captured = {}
        platform = _make_platform(monkeypatch, captured)
        raw = [{"type": "face", "data": {"id": "222", "raw": {"faceText": "大怨种"}}}]
        await platform._handle_chat_message(_group_msg(raw))
        assert "content" not in captured

    async def test_group_face_with_text_passes_prefilter(self, monkeypatch):
        """群聊带文字的表情消息 → 通过预过滤且表情文本注入 content。"""
        captured = {}
        platform = _make_platform(monkeypatch, captured)
        raw = [
            {"type": "text", "data": {"text": "这个好用"}},
            {"type": "face", "data": {"id": "222", "raw": {"faceText": "大怨种"}}},
        ]
        await platform._handle_chat_message(_group_msg(raw))
        assert captured.get("content") == "这个好用 [表情:大怨种]"

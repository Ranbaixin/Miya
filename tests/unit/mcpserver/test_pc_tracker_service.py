"""pc_tracker MCP 服务回归测试（PC 使用数据接入弥娅）。

覆盖：base_url 可配置化（SSH 隧道端点 9443）/ 健康检查 / text_summary 提取 /
不可达时的友好降级。
"""

from types import SimpleNamespace

import httpx
import pytest

from mcpserver.pc_tracker.service import PcTrackerService


class _FakeResponse:
    def __init__(self, payload, status_code=200):
        self._payload = payload
        self.status_code = status_code

    def raise_for_status(self):
        if self.status_code >= 400:
            raise httpx.HTTPStatusError(f"HTTP {self.status_code}", request=None, response=None)

    def json(self):
        return self._payload


class _FakeAsyncClient:
    payload = {}
    status_code = 200
    fail = False

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, **kwargs):
        PcTrackerService.last_url = url
        if _FakeAsyncClient.fail:
            raise httpx.ConnectError("unreachable")
        return _FakeResponse(_FakeAsyncClient.payload, _FakeAsyncClient.status_code)


@pytest.fixture
def fake_http(monkeypatch):
    monkeypatch.setattr("mcpserver.pc_tracker.service.httpx.AsyncClient", _FakeAsyncClient)
    PcTrackerService.last_url = ""

    def set_payload(payload=None, status_code=200, fail=False):
        _FakeAsyncClient.payload = payload or {}
        _FakeAsyncClient.status_code = status_code
        _FakeAsyncClient.fail = fail

    return set_payload


class TestBaseUrlConfig:
    def test_default_tunnel_endpoint(self, monkeypatch):
        """默认走 SSH 反向隧道端点 127.0.0.1:9443（修复原 8080 笔误+拓扑不通）。"""
        monkeypatch.delenv("PC_TRACKER_API_BASE", raising=False)
        service = PcTrackerService()
        assert service.base_url == "http://127.0.0.1:9443/api/v1"

    def test_env_override(self, monkeypatch):
        monkeypatch.setenv("PC_TRACKER_API_BASE", "http://127.0.0.1:8088/api/v1")
        assert PcTrackerService().base_url == "http://127.0.0.1:8088/api/v1"

    def test_request_url_composes_base_and_path(self, fake_http):
        fake_http({"data": {}})
        service = PcTrackerService()
        import asyncio

        asyncio.run(service._get("/agent/context"))
        assert PcTrackerService.last_url.endswith("/api/v1/agent/context")


class TestHealthAndSummary:
    async def test_health_check_true_when_context_ok(self, fake_http):
        fake_http({"data": {"text_summary": "今日活跃 2.5 小时"}})
        service = PcTrackerService()
        assert await service.health_check() is True

    async def test_health_check_false_when_unreachable(self, fake_http):
        fake_http(fail=True)
        service = PcTrackerService()
        assert await service.health_check() is False

    async def test_get_text_summary(self, fake_http):
        fake_http({"data": {"text_summary": "2026-09-21，电脑活跃使用总计2小时33分钟"}})
        service = PcTrackerService()
        summary = await service.get_text_summary()
        assert "2小时33分钟" in summary

    async def test_get_text_summary_none_when_absent(self, fake_http):
        fake_http({"data": {}})
        service = PcTrackerService()
        assert await service.get_text_summary() is None

    async def test_tool_unreachable_friendly_message(self, fake_http):
        """桥不可达 → 友好提示（含隧道端点），不抛异常。"""
        fake_http(fail=True)
        service = PcTrackerService()
        result = await service.handle_handoff({"tool_name": "pc_context", "parameters": {}})
        assert "不可用" in result
        assert "9443" in result

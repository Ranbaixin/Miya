"""余额查询模块测试（core/balance_query.py）。"""

import pytest

from core import balance_query
from core.balance_query import fetch_balance, format_balance


# ---------- format_balance 纯函数 ----------

class TestFormatBalance:
    def test_normal_cny(self):
        data = {
            "is_available": True,
            "balance_infos": [
                {"currency": "CNY", "total_balance": "110.00", "granted_balance": "10.00", "topped_up_balance": "100.00"}
            ],
        }
        text = format_balance(data)
        assert "【DeepSeek 账户余额】" in text
        assert "¥110.00" in text
        assert "¥10.00" in text
        assert "¥100.00" in text
        assert "✅ 可用" in text

    def test_unavailable_flag(self):
        data = {"is_available": False, "balance_infos": [{"currency": "CNY", "total_balance": "5.00"}]}
        assert "⚠️ 账户不可用" in format_balance(data)

    def test_empty_infos(self):
        assert "无余额信息" in format_balance({"is_available": True, "balance_infos": []})

    def test_non_cny_currency_symbol(self):
        data = {"is_available": True, "balance_infos": [{"currency": "USD", "total_balance": "9.99"}]}
        assert "USD 9.99" in format_balance(data)


# ---------- fetch_balance 网络路径（mock httpx） ----------

class _FakeResponse:
    def __init__(self, status_code=200, payload=None):
        self.status_code = status_code
        self._payload = payload or {}

    def json(self):
        return self._payload


class _FakeClient:
    payload = {}
    status_code = 200
    raise_exc = None

    def __init__(self, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def get(self, url, headers=None):
        if _FakeClient.raise_exc:
            raise _FakeClient.raise_exc
        return _FakeResponse(_FakeClient.status_code, _FakeClient.payload)


@pytest.fixture
def fake_http(monkeypatch):
    monkeypatch.setattr(balance_query.httpx, "AsyncClient", _FakeClient)
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")

    def set_response(status_code=200, payload=None, raise_exc=None):
        _FakeClient.status_code = status_code
        _FakeClient.payload = payload or {}
        _FakeClient.raise_exc = raise_exc

    return set_response


class TestFetchBalance:
    async def test_success(self, fake_http):
        fake_http(200, {"is_available": True, "balance_infos": [{"currency": "CNY", "total_balance": "88.00"}]})
        ok, text = await fetch_balance()
        assert ok is True
        assert "¥88.00" in text

    async def test_401_invalid_key(self, fake_http):
        fake_http(401)
        ok, text = await fetch_balance()
        assert ok is False
        assert "API Key 无效" in text

    async def test_timeout_returns_friendly_text(self, fake_http):
        import httpx

        fake_http(raise_exc=httpx.TimeoutException("timeout"))
        ok, text = await fetch_balance()
        assert ok is False
        assert "网络异常" in text

    async def test_missing_key(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        ok, text = await fetch_balance(api_key="")
        assert ok is False
        assert "未配置 DEEPSEEK_API_KEY" in text

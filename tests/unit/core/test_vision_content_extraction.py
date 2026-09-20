"""视觉调用空描述修复回归测试（core/multi_vision_analyzer._call_vision_api）。

事故：DeepSeek V4.1 思考型模型对表情包图片返回空 content（输出落在
reasoning_content 或思考耗尽 max_tokens），分析器把空描述当成功返回，
弥娅回复"图片内容我看不到"。
"""

from types import SimpleNamespace

import httpx
import pytest

from core.multi_vision_analyzer import MultiVisionAnalyzer


class _FakeResponse:
    def __init__(self, payload=None, status_code=200, text=""):
        self._payload = payload or {}
        self.status_code = status_code
        self.text = text

    def json(self):
        return self._payload


class _FakeAsyncClient:
    """按序返回预设响应，记录请求"""

    def __init__(self, responses):
        self.responses = list(responses)
        self.requests = []

    async def post(self, url, json=None, headers=None, timeout=None):
        self.requests.append(json)
        item = self.responses.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


def _resp(content="", reasoning_content=None, finish_reason="stop"):
    message = {"role": "assistant", "content": content, "reasoning_content": reasoning_content}
    return _FakeResponse({"choices": [{"message": message, "finish_reason": finish_reason}]})


def _model_config(provider="openai", max_tokens=4000):
    return SimpleNamespace(
        name="deepseek-flash",
        provider=provider,
        api_base="https://api.deepseek.com/v1",
        api_key="sk-test",
        max_tokens=max_tokens,
        timeout=0,
    )


def _make_analyzer(responses):
    """跳过 __init__（避免加载模型池/网络客户端），只注入被测依赖"""
    analyzer = MultiVisionAnalyzer.__new__(MultiVisionAnalyzer)
    analyzer.http_client = _FakeAsyncClient(responses)
    return analyzer


def _call(analyzer, model_config=None):
    import asyncio

    return asyncio.run(
        analyzer._call_vision_api(
            model_config or _model_config(), "aGVsbG8=", "jpeg"
        )
    )


class TestVisionContentExtraction:
    def test_normal_content_returned(self):
        analyzer = _make_analyzer([_resp(content="这是一张黑白卡通表情包，写着猫猫无聊。")])
        result = _call(analyzer)
        assert "表情包" in result["description"]
        assert result["confidence"] == 0.8

    def test_empty_content_falls_back_to_reasoning(self, caplog):
        """content 为空但 reasoning_content 有内容 → 兜底取 reasoning（带告警日志）。"""
        analyzer = _make_analyzer(
            [_resp(content="", reasoning_content="用户发了一张黑白表情包，画着一只无精打采的猫。")]
        )
        result = _call(analyzer)
        assert "黑白表情包" in result["description"]
        assert any("reasoning_content 兜底" in r.message for r in caplog.records)

    def test_two_empty_attempts_raise_with_diagnostics(self):
        """连续两次空描述 → ValueError，带 finish_reason/max_tokens 诊断。"""
        analyzer = _make_analyzer([_resp(content="", finish_reason="length")] * 2)
        with pytest.raises(ValueError) as exc:
            _call(analyzer)
        msg = str(exc.value)
        assert "连续返回空描述" in msg
        assert "finish_reason=length" in msg
        assert "max_tokens=4000" in msg
        # 确认确实重试了 2 次
        assert len(analyzer.http_client.requests) == 2

    def test_first_empty_then_success(self):
        """第一次空（偶发）、第二次成功 → 返回成功描述。"""
        analyzer = _make_analyzer(
            [_resp(content="", finish_reason="length"), _resp(content="一只橘猫躺在键盘上。")]
        )
        result = _call(analyzer)
        assert "橘猫" in result["description"]

    def test_timeout_raises_valueerror(self):
        analyzer = _make_analyzer([httpx.TimeoutException("timeout")])
        with pytest.raises(ValueError) as exc:
            _call(analyzer)
        assert "超时" in str(exc.value)

    def test_http_401_raises(self):
        analyzer = _make_analyzer([_FakeResponse({"error": {"message": "auth"}}, status_code=401, text="auth")])
        with pytest.raises(ValueError) as exc:
            _call(analyzer)
        assert "HTTP 401" in str(exc.value)

    def test_max_tokens_sent_in_payload(self):
        """token 预算加倍后 payload 应带 max_tokens=4000。"""
        analyzer = _make_analyzer([_resp(content="描述")])
        _call(analyzer)
        payload = analyzer.http_client.requests[0]
        assert payload["max_tokens"] == 4000

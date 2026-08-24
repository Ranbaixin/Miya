"""AI 客户端 usage 校准闭环测试（2026-08 验收补充）。

覆盖：
- 响应含 usage → record_calibration 被调用（估算/实际写入校准文件）
- 响应无 usage → 不崩溃、不写校准
- 校准只记录最大值（不降低预算，与 token_budget 约束一致）
"""

import json
from types import SimpleNamespace

import pytest

from core.ai_client import DeepSeekClient


def _client(model="deepseek-chat"):
    # 避免完整初始化（不需要真实 client 即可测校准助手）
    client = object.__new__(DeepSeekClient)
    client.model = model
    return client


def test_record_usage_calibration_writes_file(tmp_path, monkeypatch):
    import utils.token_budget as tb

    monkeypatch.setattr(tb, "_CALIBRATION_FILE", tmp_path / "cal.json")

    c = _client()
    params = {"model": "deepseek-chat", "messages": [{"role": "user", "content": "你好"}]}
    resp = SimpleNamespace(usage=SimpleNamespace(prompt_tokens=200, completion_tokens=50))
    c._record_usage_calibration(params, resp, provider="deepseek")

    data = json.loads((tmp_path / "cal.json").read_text(encoding="utf-8"))
    assert "deepseek" in data
    assert "deepseek-chat" in data["deepseek"]
    assert data["deepseek"]["deepseek-chat"]["ratio"] > 0


def test_record_usage_calibration_no_usage_no_crash(tmp_path, monkeypatch):
    import utils.token_budget as tb

    monkeypatch.setattr(tb, "_CALIBRATION_FILE", tmp_path / "cal.json")

    c = _client()
    # 响应无 usage 属性
    resp = SimpleNamespace(choices=[], usage=None)
    c._record_usage_calibration({}, resp, provider="deepseek")  # 不应抛异常
    resp2 = SimpleNamespace()  # 连 usage 都没有
    c._record_usage_calibration({}, resp2, provider="deepseek")
    assert not (tmp_path / "cal.json").exists()


def test_record_usage_calibration_never_lowers_budget(tmp_path, monkeypatch):
    import utils.token_budget as tb

    monkeypatch.setattr(tb, "_CALIBRATION_FILE", tmp_path / "cal.json")

    c = _client()
    params = {"model": "deepseek-chat", "messages": [{"role": "user", "content": "中" * 50}]}
    base_est = tb.estimate_tokens(json.dumps(params, ensure_ascii=False), provider="deepseek", model="deepseek-chat")

    # 实际 < 估算 → 校准比例 <1，预算不降
    c._record_usage_calibration(params, SimpleNamespace(usage=SimpleNamespace(prompt_tokens=10)), provider="deepseek")
    est_after = tb.estimate_tokens(json.dumps(params, ensure_ascii=False), provider="deepseek", model="deepseek-chat")
    assert est_after == base_est

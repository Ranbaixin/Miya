"""token 预算器测试（2026-08 修订计划 Step 1 验收）。

覆盖：
- 未知 provider/model → 保守估算（中文 2 token/字）
- OpenAI 系模型 → tiktoken 精确计量（model_encoding_name 映射）
- 分段计量：total_input == 各段之和，空段为 0
- usage 校准：校准系数只记录最大值；校准不得降低预算
- 预算日志不包含记忆正文/隐私内容
- context_limit = min(13K, window - output_reserve - safety_margin)
- 裁剪优先级：tool_results 最先裁，history 最后裁
"""

import json

import pytest

from utils import token_budget as tb


# ==================== 保守估算 / 未知模型 ====================

def test_conservative_estimate_cjk_and_ascii():
    # 中文：2 token/字 + 1 余量
    assert tb.conservative_estimate("你好世界") == 4 * 2 + 1
    # 纯 ASCII：1 token/3 字符（向上取整余量 1）
    assert tb.conservative_estimate("hello") == int(5 / 3.0) + 1
    # 空串
    assert tb.conservative_estimate("") == 0


def test_unknown_model_falls_back_to_conservative():
    """未知 provider/model → 无 tiktoken、无校准 → 保守估算"""
    text = "你好世界，这是中文测试文本。"
    assert tb.estimate_tokens(text, provider="", model="") == tb.conservative_estimate(text)
    # deepseek 属于无 tokenizer 提供方
    assert tb.estimate_tokens(text, provider="deepseek", model="deepseek-chat") == tb.conservative_estimate(text)


def test_model_encoding_name_mapping():
    assert tb.model_encoding_name("gpt-4o-mini") == "o200k_base"
    assert tb.model_encoding_name("gpt-4") == "cl100k_base"
    assert tb.model_encoding_name("gpt-4o") == "o200k_base"
    assert tb.model_encoding_name("deepseek-chat") is None
    assert tb.model_encoding_name("") is None
    assert tb.model_encoding_name(None) is None


def test_openai_uses_tiktoken_when_available():
    """OpenAI 系模型有 tiktoken → 精确计量（结果 <= 保守估算）"""
    text = "The quick brown fox jumps over the lazy dog."
    est = tb.estimate_tokens(text, provider="openai", model="gpt-4o")
    assert est > 0
    assert est <= tb.conservative_estimate(text)


# ==================== 分段计量 ====================

def test_count_segments_total_is_sum():
    segments = {
        "system": "你好世界",
        "history": "hi there",
        "stable_memory": "喜欢读书、听音乐",
        "user": "",
    }
    counted = tb.count_segments(segments, provider="deepseek", model="deepseek-chat")
    assert counted["user"] == 0  # 空段为 0
    total = sum(v for k, v in counted.items() if k != "total_input")
    assert counted["total_input"] == total


# ==================== usage 校准 ====================

def test_calibration_never_lowers_budget(tmp_path, monkeypatch):
    monkeypatch.setattr(tb, "_CALIBRATION_FILE", tmp_path / "cal.json")
    text = "中" * 50  # 保守估算 = 101
    base = tb.estimate_tokens(text, provider="deepseek", model="deepseek-chat")

    # 校准系数 < 1（真实 usage 低于估算）→ 预算不得降低
    tb.record_calibration("deepseek", "deepseek-chat", estimated=100, actual=50)
    assert tb.estimate_tokens(text, provider="deepseek", model="deepseek-chat") == base

    # 校准系数 > 1 → 预算提升
    tb.record_calibration("deepseek", "deepseek-chat", estimated=100, actual=200)
    raised = tb.estimate_tokens(text, provider="deepseek", model="deepseek-chat")
    assert raised > base

    # 之后更小的校准系数不能把预算拉低（只记录最大值）
    tb.record_calibration("deepseek", "deepseek-chat", estimated=100, actual=120)
    assert tb.estimate_tokens(text, provider="deepseek", model="deepseek-chat") == raised


def test_calibration_invalid_input_ignored(tmp_path, monkeypatch):
    monkeypatch.setattr(tb, "_CALIBRATION_FILE", tmp_path / "cal.json")
    tb.record_calibration("", "m", estimated=10, actual=20)   # 无 provider
    tb.record_calibration("deepseek", "m", estimated=0, actual=20)  # 非法 estimated
    assert not (tmp_path / "cal.json").exists()


def test_calibration_file_isolation(tmp_path, monkeypatch):
    """provider+model 隔离：互不影响"""
    monkeypatch.setattr(tb, "_CALIBRATION_FILE", tmp_path / "cal.json")
    tb.record_calibration("deepseek", "deepseek-chat", estimated=100, actual=300)
    # 同 provider 不同 model 不受影响
    assert tb._get_calibration("deepseek", "other-model") is None
    # 不同 provider 不受影响
    assert tb._get_calibration("anthropic", "claude-3-5-sonnet") is None
    data = json.loads((tmp_path / "cal.json").read_text(encoding="utf-8"))
    assert data["deepseek"]["deepseek-chat"]["ratio"] == 3.0


# ==================== 预算日志（无隐私） ====================

def test_budget_log_has_no_privacy_content():
    raw = {
        "system": "你是弥娅，一个虚拟化身",
        "history": "用户: 我今天去看了电影\\n弥娅: 好看吗",
        "stable_memory": "用户的真实姓名是张三",
    }
    segments = tb.count_segments(raw, provider="deepseek", model="deepseek-chat")
    segments["total_input"] = 999
    log = tb.budget_log(segments)
    assert "prompt.system=" in log
    assert "prompt.history=" in log
    assert "total_input=999" in log
    # 不含任何正文内容
    for secret in ("弥娅", "电影", "张三", "虚拟化身"):
        assert secret not in log


# ==================== 上下文上限 ====================

def test_context_limit_formula():
    # 默认：min(13K, 64000-4000-1000) = 13K
    assert tb.context_limit() == 13000
    # 小窗口：min(13K, 8000-4000-1000) = 3000
    assert tb.context_limit(context_window=8000) == 3000
    # 自定义预留
    assert tb.context_limit(context_window=10000, output_reserve=2000, safety_margin=500) == 7500


# ==================== 裁剪优先级 ====================

def test_crop_priority_tool_results_first():
    text = "中" * 30  # 61 tokens（保守）
    segments = {"tool_results": text, "knowledge": text, "history": text}
    cropped = tb.crop_segments(segments, limit=130, provider="deepseek", model="deepseek-chat")
    # tool_results 被裁短，knowledge/history 保持不变
    assert len(cropped["tool_results"]) < 30
    assert cropped["knowledge"] == text
    assert cropped["history"] == text
    total = sum(tb.estimate_tokens(v, "deepseek", "deepseek-chat") for v in cropped.values())
    assert total <= 130


def test_crop_drops_history_last():
    """预算只能容纳一个段时：tool_results 先被丢弃，history 最后裁"""
    text = "中" * 30  # 61 tokens
    segments = {"tool_results": text, "knowledge": text, "history": text}
    cropped = tb.crop_segments(segments, limit=61, provider="deepseek", model="deepseek-chat")
    assert "tool_results" not in cropped
    assert "knowledge" not in cropped
    assert "history" in cropped


def test_crop_zero_limit_empties_all():
    text = "中" * 30
    segments = {"tool_results": text, "history": text}
    cropped = tb.crop_segments(segments, limit=0, provider="deepseek", model="deepseek-chat")
    assert cropped == {}

"""统一 token 预算器（2026-08 修订计划 Step 1）

设计约束（用户批准）：
- tiktoken 仅对 OpenAI 系编码准确；DeepSeek/Anthropic/Gemini 等走保守估算，
  不假装是真实 tokenizer
- provider usage 校准：按 provider+model+encoding 保存系数；校准不得降低预算，
  准入判断取 max(保守估算, 校准估算)
- 分段计量：system/history/stable_memory/cognitive_memory/knowledge/tools.schema/
  tool_results/user → total_input
- S1 工具 schema 计量：序列化实际发送的完整工具 JSON
- S4 上限：min(13K, context_window - output_reserve - safety_margin)，默认保留 1K 余量
- 预算日志不包含记忆正文/隐私内容
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)

# ==================== 编码映射 ====================

# OpenAI 系模型 → tiktoken 编码
_OPENAI_MODEL_ENCODINGS = {
    # 顺序敏感：先匹配最具体（"gpt-4" 是 "gpt-4o" 的子串）
    "gpt-4o-mini": "o200k_base",
    "gpt-4o": "o200k_base",
    "gpt-4": "cl100k_base",
    "gpt-3.5": "cl100k_base",
    "text-embedding": "cl100k_base",
}

# 无真实 tokenizer 的提供方（走保守估算）
_NON_TOKENIZER_PROVIDERS = {"deepseek", "anthropic", "gemini", "zhipu", "dashscope", "siliconflow", "ollama"}

# 校准文件（不提交，gitignore 的 data/ 下）
_CALIBRATION_FILE = Path("data/.token_calibration.json")

# 默认窗口与预留
DEFAULT_CONTEXT_WINDOW = 64000
DEFAULT_OUTPUT_RESERVE = 4000
DEFAULT_SAFETY_MARGIN = 1000

# ==================== 保守估算 ====================

_CJK_RE = re.compile(r"[\u4e00-\u9fff\u3400-\u4dbf]")
_CJK_PUNCT_RE = re.compile(r"[\u3000-\u303f\uff00-\uffef]")


def conservative_estimate(text: str) -> int:
    """保守 token 估算：中文按 2 token/字，英文按 1 token/3 字符，标点另计。
    取偏大值，宁可高估不可低估。
    """
    if not text:
        return 0
    text = str(text)
    cjk_chars = len(_CJK_RE.findall(text)) + len(_CJK_PUNCT_RE.findall(text))
    non_cjk = len(text) - cjk_chars
    # 中文：2 token/字（保守）；英文/符号：1 token/3 字符（偏保守）
    est = cjk_chars * 2 + non_cjk / 3.0
    return int(est) + 1  # 留 1 token 余量


# ==================== tiktoken 封装 ====================

_enc_cache: Dict[str, object] = {}


def _get_encoding(name: str):
    if name in _enc_cache:
        return _enc_cache[name]
    try:
        import tiktoken

        enc = tiktoken.get_encoding(name)
        _enc_cache[name] = enc
        return enc
    except Exception:  # noqa: BLE001 - tokenizer 缺失降级保守估算
        return None


def model_encoding_name(model: str) -> Optional[str]:
    """根据模型名映射 tiktoken 编码（仅 OpenAI 系）"""
    if not model:
        return None
    m = model.lower()
    for key, enc in _OPENAI_MODEL_ENCODINGS.items():
        if key in m:
            return enc
    # 默认：OpenAI 系未知名 → cl100k（近似）
    if "openai" in m or "gpt" in m:
        return "cl100k_base"
    return None


# ==================== 估算主入口 ====================

def estimate_tokens(text: str, provider: str = "", model: str = "") -> int:
    """估算文本 token：
    1. OpenAI 系模型有 tiktoken 编码 → 用 tokenizer
    2. 其他（DeepSeek/Anthropic/Gemini/未知）→ 保守估算
    3. provider usage 校准后取 max(保守, 校准)
    """
    if not text:
        return 0
    enc_name = model_encoding_name(model) if provider in ("openai", "openai_compatible") or "openai" in provider.lower() else None
    enc = _get_encoding(enc_name) if enc_name else None
    base = (
        len(enc.encode(str(text)))
        if enc
        else conservative_estimate(text)
    )

    cal = _get_calibration(provider, model)
    if cal:
        # 校准系数 = 真实 usage / 估算；校准后预算 = 估算 * 系数（取大者）
        calibrated = int(base * cal)
        return max(base, calibrated)
    return base


def _get_calibration(provider: str, model: str) -> Optional[float]:
    """读取校准系数（provider+model 隔离）"""
    if not provider:
        return None
    data = _load_calibration()
    entry = data.get(provider, {}).get(model or "*", {})
    return entry.get("ratio")


def record_calibration(provider: str, model: str, estimated: int, actual: int) -> None:
    """provider 返回真实 usage 后记录校准系数。系数只保存，不用于降低预算。"""
    if not provider or estimated <= 0 or actual <= 0:
        return
    ratio = actual / estimated
    data = _load_calibration()
    data.setdefault(provider, {}).setdefault(model or "*", {})
    # 只记录最大值（保守方向）：校准系数取历史最大，避免被低估拖低
    old = data[provider][model or "*"].get("ratio", 0.0)
    data[provider][model or "*"]["ratio"] = max(old, ratio)
    data[provider][model or "*"]["samples"] = data[provider][model or "*"].get("samples", 0) + 1
    _save_calibration(data)


def _load_calibration() -> dict:
    if _CALIBRATION_FILE.exists():
        try:
            return json.loads(_CALIBRATION_FILE.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            pass
    return {}


def _save_calibration(data: dict) -> None:
    try:
        _CALIBRATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        _CALIBRATION_FILE.write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
        )
    except OSError as e:
        logger.debug("[token_budget] 校准保存失败: %s", e)


# ==================== 分段计量 ====================

def count_segments(segments: Dict[str, str], provider: str = "", model: str = "") -> Dict[str, int]:
    """分段计量：返回每段 token + total_input（不含隐私日志）"""
    result = {}
    total = 0
    for name, text in segments.items():
        n = estimate_tokens(text, provider=provider, model=model)
        result[name] = n
        total += n
    result["total_input"] = total
    return result


def budget_log(segments: Dict[str, int]) -> str:
    """预算日志（只含段名与数字，不含记忆正文）"""
    parts = []
    for k, v in segments.items():
        if k == "total_input":
            continue
        parts.append(f"prompt.{k}={v}")
    parts.append(f"total_input={segments.get('total_input', 0)}")
    return " ".join(parts)


# ==================== 上下文上限 ====================

def context_limit(
    context_window: int = DEFAULT_CONTEXT_WINDOW,
    output_reserve: int = DEFAULT_OUTPUT_RESERVE,
    safety_margin: int = DEFAULT_SAFETY_MARGIN,
) -> int:
    """输入预算上限：min(13K, window - output_reserve - safety_margin)"""
    return min(13000, context_window - output_reserve - safety_margin)


# ==================== 裁剪优先级 ====================

# 超预算时裁剪顺序（先裁的优先被裁）：工具结果最先，历史最后
CROP_PRIORITY = [
    "tool_results",    # 1. 工具返回（最大且最易重复）
    "knowledge",       # 2. 知识图谱
    "cognitive_memory",  # 3. 认知记忆
    "stable_memory",   # 4. 稳定画像
    "history",         # 5. 对话历史（最后裁）
]


def crop_segments(segments: Dict[str, str], limit: int, provider: str = "", model: str = "") -> Dict[str, str]:
    """超预算按优先级裁剪段（返回裁剪后的段 dict）"""
    result = dict(segments)
    total = sum(estimate_tokens(v, provider, model) for v in result.values())
    if total <= limit:
        return result
    for name in CROP_PRIORITY:
        if name not in result:
            continue
        text = result[name]
        est = estimate_tokens(text, provider, model)
        if total - est <= limit:
            # 只裁到剩余可容纳比例
            remain = limit - (total - est)
            if remain <= 0:
                del result[name]
            else:
                # 按比例截断文本（保守：保留前 remain/est 部分）
                ratio = remain / est
                cut_len = max(1, int(len(text) * ratio))
                result[name] = text[:cut_len]
            total = sum(estimate_tokens(v, provider, model) for v in result.values())
            break
        else:
            del result[name]
            total = sum(estimate_tokens(v, provider, model) for v in result.values())
        if total <= limit:
            break
    return result

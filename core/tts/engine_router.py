"""
弥娅 TTS 引擎路由 — 跨平台共享模块
供 OneBot / QQOfficial / 其他平台复用
"""

import logging
import tempfile
import os

logger = logging.getLogger(__name__)


def _load_config():
    import json

    config_path = "config/tts_config.json"
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


async def synthesize(text: str, engine: str = None) -> str | None:
    """合成语音 → 返回临时文件路径，失败返回 None"""
    config = _load_config()
    if not engine:
        engine = config.get("preferred_engine", "edge_tts")
    try:
        if engine == "gpt_sovits":
            return await _synthesize_gpt_sovits(config, text)
        elif engine == "api_tts":
            return await _synthesize_api_tts(config, text)
        else:
            return await _synthesize_edge_tts(config, text)
    except Exception as e:
        logger.warning(f"TTS {engine} 失败: {e}，回退 edge-tts")
        if engine != "edge_tts":
            try:
                return await _synthesize_edge_tts(config, text)
            except Exception:
                pass
        return None


async def _synthesize_edge_tts(config: dict, text: str) -> str:
    import edge_tts

    engine_cfg = config.get("engines", {}).get("edge_tts", {})
    voice = engine_cfg.get("voice", "zh-CN-XiaoxiaoNeural")
    speed = engine_cfg.get("speed", 1.0)
    rate_str = f"+{int((speed - 1) * 100)}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    tmp = tempfile.NamedTemporaryFile(suffix=".mp3", delete=False)
    tmp_path = tmp.name
    tmp.close()
    await communicate.save(tmp_path)
    return tmp_path


async def _synthesize_gpt_sovits(config: dict, text: str) -> str:
    import aiohttp, re

    sovits = config.get("engines", {}).get("gpt_sovits", {})
    api_url = sovits.get("api_url", "http://127.0.0.1:9880")
    timeout = sovits.get("timeout", 30)

    filtered = text
    if sovits.get("filter_brackets", True):
        filtered = re.sub(r"【.*?】", "", filtered)
        filtered = re.sub(r"\[.*?\]", "", filtered)
    if sovits.get("filter_special_chars", True):
        filtered = re.sub(r"[\U00010000-\U0010FFFF]", "", filtered)

    payload = {
        "text": filtered,
        "text_lang": sovits.get("language", "zh"),
        "ref_audio_path": sovits.get("reference_audio", ""),
        "prompt_text": sovits.get("reference_text", ""),
        "prompt_lang": sovits.get("language", "zh"),
        "top_k": sovits.get("top_k", 15),
        "top_p": sovits.get("top_p", 1.0),
        "temperature": sovits.get("temperature", 1.0),
        "speed_factor": sovits.get("speed", 1.0),
        "ref_free": sovits.get("ref_free", False),
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=timeout)) as s:
        async with s.post(f"{api_url.rstrip('/')}/tts", json=payload) as r:
            if r.status != 200:
                raise RuntimeError(f"GPT-SoVITS {r.status}")
            data = await r.read()
    tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    tmp_path = tmp.name
    tmp.close()
    with open(tmp_path, "wb") as f:
        f.write(data)
    return tmp_path


async def _synthesize_api_tts(config: dict, text: str) -> str:
    import aiohttp

    api_conf = config.get("engines", {}).get("api_tts", {})
    api_url = api_conf.get("api_url", "https://api.openai.com/v1/audio/speech")
    api_key = api_conf.get("api_key", "")
    if not api_key:
        raise RuntimeError("API Key 未配置")
    fmt = api_conf.get("format", "mp3")
    payload = {
        "model": "tts-1",
        "input": text,
        "voice": api_conf.get("voice", "alloy"),
        "response_format": fmt,
        "speed": api_conf.get("speed", 1.0),
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=30)) as s:
        async with s.post(
            api_url, json=payload, headers={"Authorization": f"Bearer {api_key}"}
        ) as r:
            if r.status != 200:
                raise RuntimeError(f"API TTS {r.status}")
            data = await r.read()
    tmp = tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False)
    tmp_path = tmp.name
    tmp.close()
    with open(tmp_path, "wb") as f:
        f.write(data)
    return tmp_path

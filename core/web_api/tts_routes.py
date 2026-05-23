"""
弥娅 TTS API 路由
提供 /tts/speech 端点，连接前端 TTS 播放到后端多引擎
"""

import contextlib
import json
import logging
import os
import tempfile
from typing import Optional

from starlette.responses import Response

try:
    from fastapi import APIRouter, HTTPException

    FASTAPI_AVAILABLE = True
except ImportError:
    FASTAPI_AVAILABLE = False
    APIRouter = object
    HTTPException = Exception

logger = logging.getLogger(__name__)


def _load_tts_config():
    try:
        with open("config/tts_config.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


async def _synthesize_edge_tts(text, voice, speed, fmt):
    import edge_tts

    rate_str = f"+{int((speed - 1) * 100)}%"
    communicate = edge_tts.Communicate(text, voice, rate=rate_str)
    tmp = tempfile.NamedTemporaryFile(suffix=f".{fmt}", delete=False)
    tmp_path = tmp.name
    tmp.close()
    await communicate.save(tmp_path)
    with open(tmp_path, "rb") as f:
        data = f.read()
    with contextlib.suppress(OSError):
        os.unlink(tmp_path)
    return data


async def _synthesize_gpt_sovits(config, text):
    import re

    import aiohttp

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

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=timeout)
    ) as session, session.post(f"{api_url.rstrip('/')}/tts", json=payload) as resp:
        if resp.status != 200:
            text_err = await resp.text()
            raise RuntimeError(f"GPT-SoVITS {resp.status}: {text_err[:200]}")
        return await resp.read()


async def _synthesize_api_tts(config, text):
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

    async with aiohttp.ClientSession(
        timeout=aiohttp.ClientTimeout(total=30)
    ) as session, session.post(
        api_url,
        json=payload,
        headers={"Authorization": f"Bearer {api_key}"},
    ) as resp:
        if resp.status != 200:
            text_err = await resp.text()
            raise RuntimeError(f"API TTS {resp.status}: {text_err[:200]}")
        return await resp.read()


class TTSRoutes:
    """TTS API 路由"""

    def __init__(self):
        self.router: Optional[APIRouter] = None
        if not FASTAPI_AVAILABLE:
            logger.warning("[TTSRoutes] FastAPI 不可用")
            return

        self.router = APIRouter(prefix="/tts", tags=["TTS"])
        self._setup_routes()

    def _setup_routes(self):
        router = self.router

        @router.post("/speech")
        async def tts_speech(request: dict):
            """TTS 语音合成，支持多引擎"""
            input_text = request.get("input") or request.get("text", "")
            voice = request.get("voice", "zh-CN-XiaoxiaoNeural")
            speed = request.get("speed", 1.0)
            response_format = request.get("response_format") or request.get(
                "format", "mp3"
            )
            engine = request.get("engine") or request.get("model", "")

            if not input_text:
                raise HTTPException(status_code=400, detail="input text is required")

            config = _load_tts_config()
            if not engine or engine in ("default", "tts-1"):
                engine = config.get("preferred_engine", "edge_tts")

            logger.info(
                f"[TTS] {engine} request: voice={voice}, speed={speed}, len={len(input_text)}"
            )

            try:
                if engine == "gpt_sovits":
                    audio_data = await _synthesize_gpt_sovits(config, input_text)
                    content_type = "audio/wav"
                elif engine == "api_tts":
                    audio_data = await _synthesize_api_tts(config, input_text)
                    (
                        api_conf.get("format", "mp3")
                        if (api_conf := config.get("engines", {}).get("api_tts", {}))
                        else "mp3"
                    )
                    content_type = "audio/mpeg"
                else:
                    engine_cfg = config.get("engines", {}).get("edge_tts", {})
                    actual_voice = (
                        voice
                        if voice != "zh-CN-XiaoxiaoNeural"
                        else engine_cfg.get("voice", voice)
                    )
                    audio_data = await _synthesize_edge_tts(
                        input_text, actual_voice, speed, response_format
                    )
                    content_type_map = {
                        "mp3": "audio/mpeg",
                        "wav": "audio/wav",
                        "ogg": "audio/ogg",
                        "aac": "audio/aac",
                        "flac": "audio/flac",
                    }
                    content_type = content_type_map.get(response_format, "audio/mpeg")

                logger.info(f"[TTS] {engine} 合成成功: {len(audio_data)} bytes")
                return Response(
                    content=audio_data,
                    media_type=content_type,
                    headers={
                        "Content-Length": str(len(audio_data)),
                        "Cache-Control": "no-cache",
                    },
                )

            except ImportError:
                logger.error(f"[TTS] {engine} 依赖未安装")
                raise HTTPException(
                    status_code=500, detail=f"{engine} dependencies missing"
                )
            except Exception as e:
                logger.error(f"[TTS] {engine} 合成失败: {e}")
                raise HTTPException(status_code=500, detail=str(e))

    def get_router(self) -> Optional[APIRouter]:
        return self.router

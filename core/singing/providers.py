"""
唱歌引擎提供商实现

当前支持:
- AutoConvertMusicEngine: 对接 Auto-Convert-Music 翻唱服务 (So-VITS-SVC)
- RVCEngine: 对接 RVC WebUI 翻唱服务 (Retrieval-based Voice Conversion)
- (未来可扩展: GPTSovitsSinger, etc.)
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

from .base import LearnStatus, LearnTask, SingingEngine, SongInfo

logger = logging.getLogger(__name__)


class AutoConvertMusicEngine(SingingEngine):
    """Auto-Convert-Music 翻唱引擎

    对接 REST API — 搜索歌曲 → AI学唱 → 下载人声/伴奏 → 播放
    """

    def __init__(self):
        super().__init__("auto_convert_music")
        self.api_url: str = ""
        self.timeout: int = 30
        self.learn_timeout: int = 500
        self.skip_convert_pattern: str = ""
        self.output_base_dir: str = "data/singing"
        self.volume_vocal: int = 70
        self.volume_accompany: int = 70
        self.speaker: str = ""

    def initialize(self, config: Dict[str, Any]) -> bool:
        try:
            self.api_url = config.get("api_url", "").rstrip("/")
            self.timeout = config.get("timeout", 30)
            self.learn_timeout = config.get("learn_timeout", 500)
            self.skip_convert_pattern = config.get("skip_convert_pattern", "")
            self.output_base_dir = config.get("output_dir", "data/singing")
            self.volume_vocal = config.get("volume_vocal", 70)
            self.volume_accompany = config.get("volume_accompany", 70)
            self.speaker = config.get("speaker", "")

            if not self.api_url:
                logger.error("Auto-Convert-Music api_url is required")
                return False

            os.makedirs(self.output_base_dir, exist_ok=True)
            self.is_initialized = True
            logger.info(
                f"Auto-Convert-Music engine initialized: {self.api_url} speaker={self.speaker}"
            )
            return True
        except Exception as e:
            logger.error(f"Auto-Convert-Music initialization failed: {e}")
            return False

    def _speaker_param(self) -> str:
        """返回 speaker 查询参数，无 speaker 时返回空字符串"""
        if not self.speaker:
            return ""
        from urllib.parse import quote

        return f"?speaker={quote(self.speaker, safe='')}"

    def _get(self, path: str, timeout: int = None) -> Optional[Any]:
        import requests

        url = f"{self.api_url}{path}"
        t = timeout or self.timeout
        try:
            resp = requests.get(url, timeout=(5, t))
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.error(f"Auto-Convert-Music request failed: {url} — {e}")
            return None

    async def search_song(self, query: str) -> Optional[SongInfo]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/musicInfo/{query}")
        )
        if resp is None:
            return None
        try:
            data = resp.json()
            return SongInfo(
                song_id=str(data.get("id", "")),
                song_name=data.get("songName", query),
                source="netease",
            )
        except Exception as e:
            logger.error(f"Failed to parse song search result: {e}")
            return None

    async def get_available_songs(self) -> List[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/accompany_vocal_status{self._speaker_param()}")
        )
        if resp is None:
            return []
        try:
            data = resp.json()
            return data.get("converted_file", [])
        except Exception:
            return []

    async def request_learn(self, song_name: str) -> LearnTask:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/append_song/{song_name}{self._speaker_param()}")
        )
        if resp is None:
            return LearnTask(song_name=song_name, status=LearnStatus.FAILED)
        try:
            data = resp.json()
            status = LearnStatus(data.get("status", "waiting"))
            actual_name = data.get("songName", song_name)
            return LearnTask(song_name=actual_name, status=status)
        except Exception as e:
            logger.error(f"Failed to request learn: {e}")
            return LearnTask(song_name=song_name, status=LearnStatus.FAILED)

    async def get_learn_status(self, song_name: str) -> LearnStatus:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/accompany_vocal_status{self._speaker_param()}")
        )
        if resp is None:
            return LearnStatus.FAILED
        try:
            data = resp.json()
            converted = data.get("converted_file", [])
            failed = data.get("convertfail", [])
            if song_name in failed:
                return LearnStatus.FAILED
            if song_name in converted:
                return LearnStatus.PROCESSED
            return LearnStatus.PROCESSING
        except Exception:
            return LearnStatus.FAILED

    async def download_vocal(self, song_name: str, output_dir: str) -> Optional[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._get(
                f"/get_vocal/{song_name}{self._speaker_param()}", timeout=120
            ),
        )
        if resp is None or resp.status_code != 200:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "vocal.wav")
        with open(path, "wb") as f:
            f.write(resp.content)
        logger.info(f"Vocal downloaded: {path}")
        return path

    async def download_accompany(
        self, song_name: str, output_dir: str
    ) -> Optional[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/get_accompany/{song_name}", timeout=120)
        )
        if resp is None or resp.status_code != 200:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "accompany.wav")
        with open(path, "wb") as f:
            f.write(resp.content)
        logger.info(f"Accompany downloaded: {path}")
        return path

    async def download_origin(self, song_name: str, output_dir: str) -> Optional[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/download_origin_song/{song_name}", timeout=120)
        )
        if resp is None or resp.status_code != 200:
            return None
        data = resp.json()
        actual_name = data.get("songName", song_name)
        audio_resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/get_audio/{actual_name}", timeout=120)
        )
        if audio_resp is None:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "vocal.wav")
        with open(path, "wb") as f:
            f.write(audio_resp.content)
        logger.info(f"Origin song downloaded: {path}")
        return path

    async def get_failed_songs(self) -> List[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/accompany_vocal_status{self._speaker_param()}")
        )
        if resp is None:
            return []
        try:
            return resp.json().get("convertfail", [])
        except Exception:
            return []

    async def download_mix(self, song_name: str, output_dir: str) -> Optional[str]:
        """下载混音成品（人声+伴奏已混合）"""
        resp = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: self._get(
                f"/get_mix/{song_name}{self._speaker_param()}", timeout=120
            ),
        )
        if resp is None or resp.status_code != 200:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{song_name}_mix.wav")
        with open(path, "wb") as f:
            f.write(resp.content)
        logger.info(f"Mix downloaded: {path}")
        return path


class RVCEngine(SingingEngine):
    """RVC (Retrieval-based Voice Conversion) 翻唱引擎

    对接 RVC WebUI API 模式 — 搜索歌曲 → 人声分离 → RVC换声 → 播放

    RVC API 端点：
      GET  /speakers                   → 列出已加载模型
      POST /set_model?model_name=xxx   → 切换模型
      POST /vc                         → 声线转换 (form: audio=file.wav)
    """

    def __init__(self):
        super().__init__("rvc")
        self.api_url: str = ""
        self.timeout: int = 30
        self.learn_timeout: int = 500
        self.output_base_dir: str = "data/singing_rvc"
        self.volume_vocal: int = 70
        self.volume_accompany: int = 70
        self.model_name: str = ""
        self.f0_up_key: int = 0
        self.f0_method: str = "rmvpe"
        self.index_rate: float = 0.3
        self.filter_radius: int = 3
        self.resample_sr: int = 0
        self.rms_mix_rate: float = 0.6
        self.protect: float = 0.25

    def initialize(self, config: Dict[str, Any]) -> bool:
        try:
            self.api_url = config.get("api_url", "http://127.0.0.1:7897").rstrip("/")
            self.timeout = config.get("timeout", 60)
            self.learn_timeout = config.get("learn_timeout", 500)
            self.output_base_dir = config.get("output_dir", "data/singing_rvc")
            self.volume_vocal = config.get("volume_vocal", 70)
            self.volume_accompany = config.get("volume_accompany", 70)
            self.model_name = config.get("model_name", "")
            self.f0_up_key = config.get("f0_up_key", 0)
            self.f0_method = config.get("f0_method", "rmvpe")
            self.index_rate = config.get("index_rate", 0.3)
            self.filter_radius = config.get("filter_radius", 3)
            self.resample_sr = config.get("resample_sr", 0)
            self.rms_mix_rate = config.get("rms_mix_rate", 0.6)
            self.protect = config.get("protect", 0.25)

            if not self.api_url:
                logger.error("RVC api_url is required")
                return False
            if not self.model_name:
                logger.warning("RVC model_name not configured, will use default")

            os.makedirs(self.output_base_dir, exist_ok=True)
            self.is_initialized = True
            logger.info(
                f"RVC engine initialized: {self.api_url} model={self.model_name}"
            )
            return True
        except Exception as e:
            logger.error(f"RVC initialization failed: {e}")
            return False

    def _get(self, path: str, timeout: int = None) -> Optional[Any]:
        import requests

        url = f"{self.api_url}{path}"
        t = timeout or self.timeout
        try:
            resp = requests.get(url, timeout=(5, t))
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.debug(f"RVC GET failed: {url} — {e}")
            return None

    def _post(
        self, path: str, data: dict = None, files: dict = None, timeout: int = None
    ) -> Optional[Any]:
        import requests

        url = f"{self.api_url}{path}"
        t = timeout or self.timeout
        try:
            resp = requests.post(url, data=data, files=files, timeout=(5, t))
            resp.raise_for_status()
            return resp
        except Exception as e:
            logger.error(f"RVC POST failed: {url} — {e}")
            return None

    async def list_models(self) -> List[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get("/speakers")
        )
        if resp is None:
            return []
        try:
            return resp.json()
        except Exception:
            return []

    async def set_model(self, model_name: str) -> bool:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._post("/set_model", data={"model_name": model_name})
        )
        if resp is not None:
            self.model_name = model_name
            logger.info(f"RVC model switched: {model_name}")
            return True
        return False

    async def convert_voice(self, audio_path: str, output_path: str) -> bool:
        """单次声线转换：输入音频 → RVC换声 → 输出"""
        try:
            filename = os.path.basename(audio_path)
            with open(audio_path, "rb") as f:
                files = {"audio": (filename, f, "audio/wav")}
                data = {
                    "model_name": self.model_name,
                    "f0_up_key": str(self.f0_up_key),
                    "f0_method": self.f0_method,
                    "index_rate": str(self.index_rate),
                    "filter_radius": str(self.filter_radius),
                    "resample_sr": str(self.resample_sr),
                    "rms_mix_rate": str(self.rms_mix_rate),
                    "protect": str(self.protect),
                }
                resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda d=data, f=files: self._post(
                        "/vc", data=d, files=f, timeout=120
                    ),
                )
            if resp is None or resp.status_code != 200:
                return False
            with open(output_path, "wb") as out_f:
                out_f.write(resp.content)
            logger.info(f"RVC conversion complete: {output_path}")
            return True
        except Exception as e:
            logger.error(f"RVC voice conversion failed: {e}")
            return False

    async def search_song(self, query: str) -> Optional[SongInfo]:
        """搜索歌曲 — 调用 ACM 的 musicInfo 或直接查 NetEase"""
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/musicInfo/{query}")
        )
        if resp is None:
            return None
        try:
            data = resp.json()
            sid = data.get("id", "")
            if not sid or str(sid) == "0":
                return None
            return SongInfo(
                song_id=str(sid),
                song_name=data.get("songName", query),
                source="netease",
            )
        except Exception:
            return None

    async def get_available_songs(self) -> List[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get("/accompany_vocal_status")
        )
        if resp is None:
            return []
        try:
            return resp.json().get("converted_file", [])
        except Exception:
            return []

    async def request_learn(self, song_name: str) -> LearnTask:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/append_song/{song_name}")
        )
        if resp is None:
            return LearnTask(song_name=song_name, status=LearnStatus.FAILED)
        try:
            data = resp.json()
            status = LearnStatus(data.get("status", "waiting"))
            actual_name = data.get("songName", song_name)
            return LearnTask(song_name=actual_name, status=status)
        except Exception:
            return LearnTask(song_name=song_name, status=LearnStatus.FAILED)

    async def get_learn_status(self, song_name: str) -> LearnStatus:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get("/accompany_vocal_status")
        )
        if resp is None:
            return LearnStatus.FAILED
        try:
            data = resp.json()
            converted = data.get("converted_file", [])
            failed = data.get("convertfail", [])
            if song_name in failed:
                return LearnStatus.FAILED
            if song_name in converted:
                return LearnStatus.PROCESSED
            return LearnStatus.PROCESSING
        except Exception:
            return LearnStatus.FAILED

    async def download_vocal(self, song_name: str, output_dir: str) -> Optional[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/get_vocal/{song_name}", timeout=120)
        )
        if resp is None or resp.status_code != 200:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "vocal.wav")
        with open(path, "wb") as f:
            f.write(resp.content)
        logger.info(f"[RVC] Vocal downloaded: {path}")
        return path

    async def download_accompany(
        self, song_name: str, output_dir: str
    ) -> Optional[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/get_accompany/{song_name}", timeout=120)
        )
        if resp is None or resp.status_code != 200:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "accompany.wav")
        with open(path, "wb") as f:
            f.write(resp.content)
        logger.info(f"[RVC] Accompany downloaded: {path}")
        return path

    async def download_origin(self, song_name: str, output_dir: str) -> Optional[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/download_origin_song/{song_name}", timeout=120)
        )
        if resp is None or resp.status_code != 200:
            return None
        try:
            data = resp.json()
            actual_name = data.get("songName", song_name)
        except Exception:
            actual_name = song_name
        audio_resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda an=actual_name: self._get(f"/get_audio/{an}", timeout=120)
        )
        if audio_resp is None or audio_resp.status_code != 200:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, "vocal.wav")
        with open(path, "wb") as f:
            f.write(audio_resp.content)
        logger.info(f"Origin downloaded: {path}")
        return path

    async def download_mix(self, song_name: str, output_dir: str) -> Optional[str]:
        """下载混音成品（人声+伴奏已混合）"""
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get(f"/get_mix/{song_name}", timeout=120)
        )
        if resp is None or resp.status_code != 200:
            return None
        os.makedirs(output_dir, exist_ok=True)
        path = os.path.join(output_dir, f"{song_name}_mix.wav")
        with open(path, "wb") as f:
            f.write(resp.content)
        logger.info(f"Mix downloaded: {path}")
        return path

    async def get_failed_songs(self) -> List[str]:
        resp = await asyncio.get_event_loop().run_in_executor(
            None, lambda: self._get("/accompany_vocal_status")
        )
        if resp is None:
            return []
        try:
            return resp.json().get("convertfail", [])
        except Exception:
            return []

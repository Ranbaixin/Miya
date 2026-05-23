"""
弥娅内置唱歌引擎 — BuiltinSingingEngine

自包含的本地唱歌管线：
  音乐源 → 下载 → 多轮人声分离(BS-Roformer → VR和声 → VR去混响)
           → 归一化 → RVC换声 → 人声后处理效果 → 多轨混音 → 播放
"""

import asyncio
import logging
import os
import shutil
from typing import Any, Dict, List, Optional

import numpy as np

from .base import LearnStatus, LearnTask, SingingEngine, SongInfo
from .music_source import MusicSource
from .separator import VocalSeparator

logger = logging.getLogger(__name__)


class BuiltinSingingEngine(SingingEngine):
    """内置唱歌引擎 — 本地全流程管线"""

    def __init__(self):
        super().__init__("builtin")
        self.output_base_dir: str = "data/singing"
        self.volume_vocal: int = 70
        self.volume_accompany: int = 70
        self.learn_timeout: int = 300

        self.music_source: Optional[MusicSource] = None
        self.source_type: str = "local"

        self.separator: Optional[VocalSeparator] = None
        self._demucs_separator: Optional[VocalSeparator] = None

        self.separation_stages: List[Dict[str, str]] = []
        self.separation_stages_enabled: bool = False

        self.effects_enabled: bool = True
        self.effects_compressor_threshold: float = 3.0
        self.effects_compressor_ratio: float = 3.0
        self.effects_highpass_hz: float = 110.0
        self.effects_gain_db: float = 3.0
        self.effects_reverb_room: float = 0.22
        self.effects_reverb_wet: float = 0.22

        self.mix_chord_enabled: bool = True
        self.mix_chord_volume: int = 50

        self.uvr5_python: str = "python"
        self.uvr5_cli: str = ""
        self.uvr5_device: str = "cuda"
        self.uvr5_timeout: int = 600

        self.rvc_api_url: str = "http://127.0.0.1:7898"
        self.rvc_model: str = "遐蝶"
        self.rvc_f0_up_key: int = 0
        self.rvc_f0_method: str = "rmvpe"
        self.rvc_index_rate: float = 0.3
        self.rvc_filter_radius: int = 3
        self.rvc_resample_sr: int = 0
        self.rvc_rms_mix_rate: float = 0.6
        self.rvc_protect: float = 0.25

        self._current_song: Optional[str] = None
        self._available_songs: List[str] = []

    def initialize(self, config: Dict[str, Any]) -> bool:
        try:
            self.output_base_dir = config.get("output_dir", "data/singing")
            self.volume_vocal = config.get("volume_vocal", 70)
            self.volume_accompany = config.get("volume_accompany", 70)
            self.learn_timeout = config.get("learn_timeout", 300)

            self.rvc_api_url = config.get("rvc_api_url", "http://127.0.0.1:7898").rstrip("/")
            self.rvc_model = config.get("rvc_model", "遐蝶")
            self.rvc_f0_up_key = config.get("rvc_f0_up_key", 0)
            self.rvc_f0_method = config.get("rvc_f0_method", "rmvpe")
            self.rvc_index_rate = config.get("rvc_index_rate", 0.3)
            self.rvc_filter_radius = config.get("rvc_filter_radius", 3)
            self.rvc_resample_sr = config.get("rvc_resample_sr", 0)
            self.rvc_rms_mix_rate = config.get("rvc_rms_mix_rate", 0.6)
            self.rvc_protect = config.get("rvc_protect", 0.25)

            self.separation_stages_enabled = config.get("separation_stages_enabled", False)
            self.separation_stages = config.get("separation_stages", [])

            eff = config.get("vocal_effects", {})
            self.effects_enabled = eff.get("enabled", True)
            self.effects_compressor_threshold = eff.get("compressor_threshold_db", 3.0)
            self.effects_compressor_ratio = eff.get("compressor_ratio", 3.0)
            self.effects_highpass_hz = eff.get("highpass_hz", 110.0)
            self.effects_gain_db = eff.get("gain_db", 3.0)
            self.effects_reverb_room = eff.get("reverb_room_size", 0.22)
            self.effects_reverb_wet = eff.get("reverb_wet_level", 0.22)

            self.mix_chord_enabled = config.get("mix_chord_enabled", True)
            self.mix_chord_volume = config.get("mix_chord_volume", 50)

            self.uvr5_python = config.get(
                "uvr5_python",
                r"D:\AIvoice\GPT-SoVITS-v2pro-20250604-nvidia50\GPT-SoVITS-v2pro-20250604-nvidia50\runtime\python.exe",
            )
            self.uvr5_cli = config.get(
                "uvr5_cli",
                os.path.join(os.path.dirname(os.path.abspath(__file__)), "uvr5_cli.py"),
            )
            self.uvr5_device = config.get("uvr5_device", "cuda")
            self.uvr5_timeout = config.get("uvr5_timeout", 600)

            self.source_type = config.get("music_source", "auto")
            source_cfg = config.get("source_config", {})

            if self.source_type == "auto":
                from .music_source import AutoMusicSource

                self.music_source = AutoMusicSource()
            elif self.source_type == "netease":
                from .music_source import NeteaseMusicSource

                self.music_source = NeteaseMusicSource()
            elif self.source_type == "bilibili":
                from .music_source import BilibiliMusicSource

                self.music_source = BilibiliMusicSource()
            else:
                from .music_source import LocalFileSource

                self.music_source = LocalFileSource()

            if not self.music_source.initialize(source_cfg):
                logger.error("Builtin: music source init failed")
                return False

            if self.separation_stages_enabled and self.separation_stages:
                self.separator = None
                logger.info(f"Builtin: 多轮分离模式 ({len(self.separation_stages)} stages)")
            else:
                uvr5_cfg = {
                    k: config.get(k)
                    for k in (
                        "uvr5_python",
                        "uvr5_cli",
                        "uvr5_models",
                        "uvr5_device",
                        "uvr5_timeout",
                    )
                    if config.get(k) is not None
                }
                demucs_cfg = {
                    "demucs_python": config.get(
                        "demucs_python",
                        r"D:\AIvoice\RVC20240604Nvidia50x0\RVC20240604Nvidia50x0\runtime\python.exe",
                    ),
                    "demucs_models": config.get("demucs_models", ["htdemucs_ft", "htdemucs"]),
                    "demucs_timeout": config.get("demucs_timeout", 300),
                }

                from .separator import DemucsSeparator, FFmpegSeparator, UVR5Separator

                self.separator = FFmpegSeparator()
                self.separator.initialize({})
                self._demucs_separator = None

                uvr5 = UVR5Separator()
                if uvr5.initialize(uvr5_cfg):
                    self.separator = uvr5
                    logger.info("Builtin: UVR5 分离器就绪 (BS-Roformer, SDR 12.97)")
                else:
                    logger.info("Builtin: UVR5 不可用，回退 Demucs")

                demucs = DemucsSeparator()
                if demucs.initialize(demucs_cfg):
                    if self.separator.name == "ffmpeg":
                        self.separator = demucs
                    self._demucs_separator = demucs
                    logger.info("Builtin: Demucs 备用分离器就绪")

            os.makedirs(self.output_base_dir, exist_ok=True)
            self.is_initialized = True
            logger.info(
                f"BuiltinSingingEngine initialized: source={self.source_type} "
                f"rvc={self.rvc_api_url} model={self.rvc_model} "
                f"multi_stage={self.separation_stages_enabled} "
                f"effects={self.effects_enabled} chord_mix={self.mix_chord_enabled}"
            )
            return True
        except Exception as e:
            logger.error(f"BuiltinSingingEngine init failed: {e}")
            return False

    async def search_song(self, query: str) -> Optional[SongInfo]:
        if not self.music_source:
            return None
        result = await self.music_source.search(query)
        if result is None:
            return None
        return SongInfo(
            song_id=result.song_id,
            song_name=result.song_name,
            source=result.source,
        )

    async def get_available_songs(self) -> List[str]:
        return self._available_songs

    async def download_song_audio(self, song_name: str, output_dir: str) -> Optional[str]:
        """下载歌曲音频（给 workflow 用）"""
        if not self.music_source:
            return None
        result = await self.music_source.search(song_name)
        if result is None:
            return None
        return await self.music_source.download(result, output_dir)

    async def separate_vocals(self, audio_path: str, output_dir: str):
        """人声分离 → (vocal_path, instrumental_path)"""
        if not self.separator:
            return None, None
        return await self.separator.separate(audio_path, output_dir)

    async def _run_uvr5_stage(
        self, audio_path: str, output_dir: str, model_type: str, model_path: str
    ) -> Optional[dict]:
        """运行单个 UVR5 分离阶段，返回 {vocal_path, inst_path} 或 None"""
        import subprocess as _sp

        src_abs = os.path.abspath(audio_path)
        out_abs = os.path.abspath(output_dir)
        os.makedirs(out_abs, exist_ok=True)

        wav_input = os.path.join(out_abs, "_uvr5_input.wav")
        try:
            _sp.run(
                [
                    shutil.which("ffmpeg") or r"D:\AIvoice\RVC20240604Nvidia50x0\RVC20240604Nvidia50x0\ffmpeg.exe",
                    "-y",
                    "-i",
                    src_abs,
                    "-ar",
                    "44100",
                    "-ac",
                    "2",
                    "-sample_fmt",
                    "s16",
                    wav_input,
                ],
                capture_output=True,
                timeout=120,
            )
            if os.path.exists(wav_input) and os.path.getsize(wav_input) > 0:
                src_abs = wav_input
                logger.info(f"[UVR5 stage] WAV 预转换: {os.path.getsize(wav_input)}B")
        except Exception as e:
            logger.warning(f"[UVR5 stage] WAV 预转换跳过: {e}")

        if not os.path.exists(model_path):
            logger.warning(f"[UVR5 stage] 模型不存在: {model_path}")
            return None

        logger.info(f"[UVR5 stage] {model_type}: {os.path.basename(src_abs)}")
        try:
            result = await asyncio.get_event_loop().run_in_executor(
                None,
                lambda: _sp.run(
                    [
                        self.uvr5_python,
                        self.uvr5_cli,
                        src_abs,
                        out_abs,
                        "--model-type",
                        model_type,
                        "--model-path",
                        model_path,
                        "--device",
                        self.uvr5_device,
                    ],
                    capture_output=True,
                    timeout=self.uvr5_timeout,
                    encoding="utf-8",
                    errors="replace",
                ),
            )
        except (_sp.TimeoutExpired, Exception) as e:
            logger.warning(f"[UVR5 stage] error: {e}")
            return None

        if result.returncode != 0:
            logger.warning(f"[UVR5 stage] rc={result.returncode} stderr={result.stderr[-500:]}")
            return None

        vocal_out = os.path.join(out_abs, "Vocals.wav")
        inst_out = os.path.join(out_abs, "Instrumental.wav")

        if os.path.exists(vocal_out):
            logger.info(f"[UVR5 stage] OK [{model_type}]")
            return {"vocal_path": vocal_out, "inst_path": inst_out}

        logger.warning(f"[UVR5 stage] no output: {model_type}")
        return None

    async def _multi_stage_separate(self, audio_path: str, output_dir: str) -> Optional[dict]:
        """多轮人声分离流水线：
        Stage 0: BS-Roformer → Vocals + Instrumental(backing)
        Stage 1: VR 和声提取 → Clean Vocals + Chord(harmony)
        Stage 2: VR 去混响  → Final Vocals + Echo(reverb)
        返回 {vocal_path, accompany_path, chord_path, echo_path} 或 None
        """
        stages_output = []
        current_input = audio_path

        for idx, stage in enumerate(self.separation_stages):
            stage_dir = os.path.join(output_dir, f"_stage{idx}")
            stage_type = stage.get("model_type", "bs_roformer")
            stage_path = stage.get("model_path", "")

            result = await self._run_uvr5_stage(current_input, stage_dir, stage_type, stage_path)
            if result is None:
                logger.error(f"[多轮分离] Stage {idx} ({stage_type}) 失败")
                return None

            stages_output.append(result)
            current_input = result["vocal_path"]
            logger.info(f"[多轮分离] Stage {idx} ({stage_type}) 完成: vocal={os.path.getsize(result['vocal_path'])}B")

        final_idx = len(stages_output) - 1

        final_vocal = os.path.join(output_dir, "Vocals.wav")
        shutil.move(stages_output[final_idx]["vocal_path"], final_vocal)

        accompany_path = os.path.join(output_dir, "Instrumental.wav")
        shutil.move(stages_output[0]["inst_path"], accompany_path)

        chord_path = None
        if final_idx >= 1:
            chord_path = os.path.join(output_dir, "Chord.wav")
            shutil.move(stages_output[final_idx - 1]["inst_path"], chord_path)
            logger.info(f"[多轮分离] 和声轨: Chord.wav ({os.path.getsize(chord_path)}B)")

        echo_path = None
        if final_idx >= 2:
            echo_path = os.path.join(output_dir, "Echo.wav")
            shutil.move(stages_output[final_idx]["inst_path"], echo_path)
            logger.info(f"[多轮分离] 混响轨: Echo.wav ({os.path.getsize(echo_path)}B)")

        for idx in range(len(self.separation_stages)):
            stage_dir = os.path.join(output_dir, f"_stage{idx}")
            shutil.rmtree(stage_dir, ignore_errors=True)

        return {
            "vocal_path": final_vocal,
            "accompany_path": accompany_path,
            "chord_path": chord_path,
            "echo_path": echo_path,
        }

    def _apply_vocal_effects(self, vocal_path: str, output_dir: str) -> Optional[str]:
        """人声后处理效果链：Compressor → HPF → Gain → Reverb

        优先使用 pedalboard，回退到 numpy + scipy 实现
        """
        import numpy as np

        if not os.path.exists(vocal_path):
            return None

        out_path = os.path.join(output_dir, "Vocals_processed.wav")

        try:
            import soundfile as sf

            data, sr = sf.read(vocal_path, dtype="float32")
            if data.ndim == 1:
                data = data.reshape(-1, 1)
        except Exception as e:
            logger.warning(f"[效果] 读取失败: {e}")
            return vocal_path

        try:
            import pedalboard
            from pedalboard import Compressor, Gain, HighpassFilter, Reverb

            board = pedalboard.Pedalboard(
                [
                    Compressor(
                        threshold_db=self.effects_compressor_threshold,
                        ratio=self.effects_compressor_ratio,
                        attack_ms=5,
                        release_ms=150,
                    ),
                    HighpassFilter(cutoff_frequency_hz=self.effects_highpass_hz),
                    Gain(gain_db=self.effects_gain_db),
                    Reverb(
                        room_size=self.effects_reverb_room,
                        damping=0.5,
                        wet_level=self.effects_reverb_wet,
                        dry_level=1.0 - self.effects_reverb_wet,
                        width=0.66,
                    ),
                ]
            )
            data = data.T if data.ndim > 1 and data.shape[1] > 1 else data.flatten()
            effected = board(data, sr)
            effected = effected.reshape(-1, 1) if effected.ndim == 1 else effected.T

            peak = np.max(np.abs(effected))
            if peak > 0.95:
                effected = np.clip(effected / peak * 0.95, -1.0, 1.0)

            sf.write(out_path, effected, sr, subtype="PCM_16")
            logger.info(
                f"[效果] pedalboard: Comp→HPF({self.effects_highpass_hz}Hz)"
                f"→Gain(+{self.effects_gain_db}dB)→Reverb(wet={self.effects_reverb_wet})"
            )
            return out_path

        except ImportError:
            logger.info("[效果] pedalboard 不可用，使用 numpy/scipy 回退")

        try:
            data, sr = sf.read(vocal_path, dtype="float32")
            if data.ndim == 1:
                data = data.reshape(-1, 1)

            _numpy_compressor(data, self.effects_compressor_threshold, self.effects_compressor_ratio)

            try:
                from scipy.signal import butter, sosfilt

                nyq = sr / 2
                cutoff = self.effects_highpass_hz / nyq
                if 0 < cutoff < 1:
                    sos = butter(4, cutoff, btype="high", output="sos")
                    data = sosfilt(sos, data, axis=0)
                    logger.info(f"[效果] HPF {self.effects_highpass_hz}Hz (scipy)")
            except ImportError:
                logger.warning("[效果] scipy 不可用，跳过 HPF")

            gain_linear = 10 ** (self.effects_gain_db / 20)
            data = data * gain_linear

            if self.effects_reverb_wet > 0:
                data = _numpy_reverb(data, sr, self.effects_reverb_room, self.effects_reverb_wet)

            peak = np.max(np.abs(data))
            if peak > 1.0:
                data = data / peak * 0.95

            sf.write(out_path, data, sr, subtype="PCM_16")
            logger.info(
                f"[效果] numpy: Comp→HPF({self.effects_highpass_hz}Hz)"
                f"→Gain(+{self.effects_gain_db}dB)→Reverb(wet={self.effects_reverb_wet})"
            )
            return out_path
        except Exception as e:
            logger.warning(f"[效果] numpy 回退失败: {e}")
            return vocal_path

    async def _normalize_vocal(self, vocal_path: str) -> Optional[str]:
        """人声归一化到 -6dB + 立体声→单声道，输出 16-bit PCM WAV

        Demucs 输出的立体声两通道存在微小时延差，不能用 np.mean() 取均值
        (会导致相位抵消/梳状滤波)，而应取左通道。RVC HuBERT 只需单声道输入。
        """
        import numpy as np

        if not os.path.exists(vocal_path):
            return None

        try:
            import soundfile as sf

            data, sr = sf.read(vocal_path, dtype="float32")
            orig_channels = 1
            if data.ndim > 1 and data.shape[1] > 1:
                orig_channels = data.shape[1]
                data = data[:, 0:1]
                logger.info(f"[归一化] 立体声→单声道: 取左通道 ({orig_channels}ch→1ch)")

            data = data.reshape(-1, 1) if data.ndim == 1 else data

            peak = float(np.max(np.abs(data)))
            if peak <= 0:
                return vocal_path

            target_peak = 0.5
            out_path = vocal_path.replace(".wav", "_norm.wav")

            if peak > target_peak:
                gain = target_peak / peak
                data = np.clip(data * gain, -1.0, 1.0)
                logger.info(f"[归一化] 衰减 peak {peak:.4f} → {target_peak:.4f} (x{gain:.2f})")
            elif peak > target_peak * 0.9:
                logger.info(f"[归一化] 已够响亮 peak={peak:.4f}")
            else:
                gain = target_peak / peak
                data = np.clip(data * gain, -1.0, 1.0)
                logger.info(f"[归一化] 提升 peak {peak:.4f} → {target_peak:.4f} (x{gain:.1f})")

            sf.write(out_path, data, sr, subtype="PCM_16")
            return out_path
        except Exception as e:
            logger.warning(f"[归一化] 失败: {e}")
            return vocal_path

    def _check_vocal_quality(self, vocal_path: str, source_path: str, inst_path: Optional[str]) -> Optional[str]:
        """检测人声分离质量，太弱时用原始音频替代"""
        import numpy as np

        try:
            import soundfile as sf

            data, _sr = sf.read(vocal_path, frames=48000 * 5, dtype="float32")
            peak = float(np.max(np.abs(data)))

            if peak >= 0.03:
                return vocal_path

            logger.warning(f"[质量] demucs 人声过弱 peak={peak:.4f}, 回退全曲模式")

            full_vocal = os.path.join(os.path.dirname(vocal_path), "Vocals_full.wav")
            if not os.path.exists(full_vocal):
                import subprocess

                from .separator import _find_ffmpeg

                subprocess.run(
                    [_find_ffmpeg(), "-y", "-i", source_path, "-ac", "1", full_vocal],
                    capture_output=True,
                    timeout=60,
                )

            if os.path.exists(full_vocal) and os.path.getsize(full_vocal) > 0:
                logger.info(f"[质量] 全曲 WAV 已生成: {full_vocal}")
                return full_vocal

            logger.warning("[质量] ffmpeg 转换失败，用原始人声")
            return vocal_path
        except Exception as e:
            logger.warning(f"[质量] 检测失败: {e}")
            return vocal_path

    async def convert_voice(self, vocal_path: str, output_dir: str) -> Optional[str]:
        """RVC 语音转换 — 带模型切换验证"""
        import requests

        if not os.path.exists(vocal_path):
            return None

        output_path = os.path.join(output_dir, f"Vocals_{self.rvc_model}.wav")
        if os.path.exists(output_path):
            logger.info(f"[RVC] cached: {output_path}")
            return output_path

        def _rvc_post(path, data=None, files=None, timeout=300):
            return requests.post(
                f"{self.rvc_api_url}{path}",
                data=data,
                files=files,
                timeout=timeout,
            )

        model_ok = False
        try:
            resp = _rvc_post("/set_model", data={"model_name": self.rvc_model}, timeout=10)
            if resp.status_code == 200:
                result = resp.json() if resp.text else {}
                loaded = result.get("model", result.get("status", ""))
                logger.info(f"[RVC] set_model: {self.rvc_model} → response={loaded}")
                model_ok = True
            else:
                logger.warning(f"[RVC] set_model HTTP {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            logger.warning(f"[RVC] set_model failed: {e}")

        if not model_ok:
            try:
                models_resp = requests.get(f"{self.rvc_api_url}/speakers", timeout=5)
                models = models_resp.json() if models_resp.text else []
                logger.warning(f"[RVC] 可用模型: {models}, 目标: {self.rvc_model}")
            except Exception:
                pass

        try:
            filename = os.path.basename(vocal_path)
            with open(vocal_path, "rb") as f:
                rvc_files = {"audio": (filename, f, "audio/wav")}
                rvc_data = {
                    "model_name": self.rvc_model,
                    "f0_up_key": str(self.rvc_f0_up_key),
                    "f0_method": self.rvc_f0_method,
                    "index_rate": str(self.rvc_index_rate),
                    "filter_radius": str(self.rvc_filter_radius),
                    "resample_sr": str(self.rvc_resample_sr),
                    "rms_mix_rate": str(self.rvc_rms_mix_rate),
                    "protect": str(self.rvc_protect),
                }
                resp = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: _rvc_post("/vc", data=rvc_data, files=rvc_files, timeout=300),
                )
            resp.raise_for_status()
            with open(output_path, "wb") as f:
                f.write(resp.content)
            logger.info(f"[RVC] OK: {output_path} ({len(resp.content)} bytes)")
            return output_path
        except Exception as e:
            logger.error(f"[RVC] failed: {e}")
            return None

    async def _clean_vocal_for_rvc(self, vocal_path: str) -> Optional[str]:
        """RVC 前人声净化

        RVC 的 HuBERT 特征提取器需要单声道。demucs 输出立体声，
        若用 np.mean() 取均值会导致相位抵消（L/R 通道存在微小时延差）。
        此处取左声道作为单声道源，而非对两通道求均值。
        然后使用保守的频谱门降噪（只去除低于噪声基底 6dB 的信号）。
        """
        import numpy as np

        if not os.path.exists(vocal_path):
            return None

        out_path = vocal_path.replace(".wav", "_clean.wav")

        try:
            import soundfile as sf

            data, sr = sf.read(vocal_path, dtype="float32")
            if data.ndim == 1:
                data = data.reshape(-1, 1)

            if data.shape[1] > 1:
                orig_ch = data.shape[1]
                data = data[:, 0:1]
                logger.info(f"[净化] 立体声→单声道: 取左通道 ({orig_ch}→1ch)")
        except Exception as e:
            logger.warning(f"[净化] 读取失败: {e}")
            return vocal_path

        try:
            from scipy.signal import istft, stft

            channel = data[:, 0]

            nperseg = 2048
            noverlap = nperseg * 3 // 4
            f, t_seg, Zxx = stft(channel, fs=sr, nperseg=nperseg, noverlap=noverlap)
            mag = np.abs(Zxx)

            noise_floor = np.mean(
                np.sort(mag, axis=1)[:, : max(1, mag.shape[1] // 20)],
                axis=1,
                keepdims=True,
            )
            threshold = np.broadcast_to(noise_floor * 2.0, mag.shape)
            mask_below = mag <= threshold

            gain = np.ones_like(mag)
            gain[mask_below] = np.clip(mag[mask_below] / (threshold[mask_below] + 1e-8), 0.0, 1.0)
            gain = np.clip(gain, 0.05, 1.0)

            Zxx_clean = Zxx * gain

            _t, cleaned_ch = istft(Zxx_clean, fs=sr, nperseg=nperseg, noverlap=noverlap)
            cleaned = cleaned_ch[: len(channel)]

            rms_before = np.sqrt(np.mean(channel**2))
            rms_after = np.sqrt(np.mean(cleaned**2))
            reduction = 1 - rms_after / rms_before if rms_before > 0 else 0.0
            logger.info(f"[净化] RMS {rms_before:.4f} → {rms_after:.4f} (reduction={reduction:.1%})")

            sf.write(out_path, cleaned, sr, subtype="PCM_16")
            return out_path
        except ImportError:
            logger.warning("[净化] scipy 不可用，跳过降噪")
            sf.write(out_path, data, sr, subtype="PCM_16")
            return out_path
        except Exception as e:
            logger.warning(f"[净化] 失败: {e}")
            sf.write(out_path, data, sr, subtype="PCM_16")
            return out_path

        try:
            from scipy.signal import istft, stft

            cleaned = np.zeros_like(data)
            for ch in range(data.shape[1]):
                channel = data[:, ch]
                f, t_seg, Zxx = stft(channel, fs=sr, nperseg=2048, noverlap=1536)
                mag = np.abs(Zxx)

                noise_floor = np.mean(
                    np.sort(mag, axis=1)[:, : max(1, mag.shape[1] // 10)],
                    axis=1,
                    keepdims=True,
                )
                gain = np.clip(1.0 - noise_floor / (mag + 1e-8), 0.0, 1.0)
                Zxx_clean = Zxx * gain

                _t, cleaned_ch = istft(Zxx_clean, fs=sr, nperseg=2048, noverlap=1536)
                cleaned[: len(cleaned_ch), ch] = cleaned_ch[: len(cleaned)]

            peak = np.max(np.abs(cleaned))
            if peak > 0:
                rms_before = np.sqrt(np.mean(data**2))
                rms_after = np.sqrt(np.mean(cleaned**2))
                logger.info(
                    f"[净化] RMS {rms_before:.4f} → {rms_after:.4f} "
                    f"(reduction={1 - rms_after / max(rms_before, 1e-8):.1%})"
                )

            sf.write(out_path, cleaned, sr, subtype="PCM_16")
            return out_path
        except ImportError:
            logger.warning("[净化] scipy 不可用，跳过降噪")
            return vocal_path
        except Exception as e:
            logger.warning(f"[净化] 失败: {e}")
            return vocal_path

    async def request_learn(self, song_name: str) -> LearnTask:
        """发起学唱 — 实际由 workflow 的 _learn_and_download 处理"""
        return LearnTask(song_name=song_name, status=LearnStatus.WAITING)

    async def get_learn_status(self, song_name: str) -> LearnStatus:
        output_dir = os.path.join(self.output_base_dir, song_name)
        vocal = os.path.join(output_dir, "Vocals.wav")
        inst = os.path.join(output_dir, "Instrumental.wav")
        if os.path.exists(vocal) or os.path.exists(inst):
            return LearnStatus.PROCESSED
        return LearnStatus.PROCESSING

    async def download_vocal(self, song_name: str, output_dir: str) -> Optional[str]:
        path = os.path.join(output_dir, f"Vocals_{self.rvc_model}.wav")
        return path if os.path.exists(path) else None

    async def download_accompany(self, song_name: str, output_dir: str) -> Optional[str]:
        path = os.path.join(output_dir, "Instrumental.wav")
        return path if os.path.exists(path) else None

    async def download_origin(self, song_name: str, output_dir: str) -> Optional[str]:
        return None

    async def download_mix(self, song_name: str, output_dir: str) -> Optional[str]:
        return None

    async def process_full_pipeline(self, song_name: str, output_dir: str) -> Optional[dict]:
        """完整唱歌管线：下载 → 多轮分离 → 归一化 → 换声 → 效果 → 返回路径

        Returns dict with vocal_path, accompany_path, chord_path, output_dir or None
        """
        logger.info(f"[Builtin] 全流程开始: {song_name}")

        os.makedirs(output_dir, exist_ok=True)

        audio_path = await self.download_song_audio(song_name, output_dir)
        if not audio_path:
            logger.error(f"[Builtin] 下载失败: {song_name}")
            return None
        logger.info(f"[Builtin] 音频下载完成: {audio_path}")

        if self.separation_stages_enabled and self.separation_stages:
            sep_result = await self._multi_stage_separate(audio_path, output_dir)
            if sep_result is None:
                logger.warning("[Builtin] 多轮分离失败，回退到传统分离")
                vocal_path, inst_path = await self.separate_vocals(audio_path, output_dir)
                chord_path = None
            else:
                vocal_path = sep_result["vocal_path"]
                inst_path = sep_result["accompany_path"]
                chord_path = sep_result.get("chord_path")
                logger.info(f"[Builtin] 多轮分离完成: vocal={vocal_path}, inst={inst_path}, chord={chord_path}")
        else:
            vocal_path, inst_path = await self.separate_vocals(audio_path, output_dir)
            chord_path = None

            if not vocal_path and self._demucs_separator:
                logger.info("[Builtin] UVR5 分离失败，回退 Demucs...")
                vocal_path, inst_path = await self._demucs_separator.separate(audio_path, output_dir)

            if not vocal_path:
                from .separator import _ffmpeg_fallback

                vocal_path, inst_path = await _ffmpeg_fallback(audio_path, output_dir)
                if not vocal_path:
                    logger.error(f"[Builtin] 分离失败: {song_name}")
                    return None
            logger.info(f"[Builtin] 人声分离完成: vocal={vocal_path}, inst={inst_path}")

        fallback_marker = os.path.join(output_dir, "_fallback.marker")
        if os.path.exists(fallback_marker):
            logger.warning("[Builtin] 分离降级，跳过 RVC 直接播放原曲")
            vocal_path = self._check_vocal_quality(vocal_path, audio_path, inst_path)
            if not vocal_path:
                return None
            return {
                "vocal_path": vocal_path,
                "accompany_path": inst_path or "",
                "output_dir": output_dir,
                "skip_rvc": True,
            }

        vocal_path = await self._normalize_vocal(vocal_path)
        if not vocal_path:
            logger.error(f"[Builtin] 人声归一化失败: {song_name}")
            return None

        converted = await self.convert_voice(vocal_path, output_dir)
        if not converted:
            logger.error(f"[Builtin] RVC 换声失败: {song_name}")
            return None
        logger.info(f"[Builtin] 换声完成: {converted}")

        if self.effects_enabled:
            processed = self._apply_vocal_effects(converted, output_dir)
            if processed:
                converted = processed
                logger.info(f"[Builtin] 效果处理完成: {converted}")

        result = {
            "vocal_path": converted,
            "accompany_path": inst_path or "",
            "output_dir": output_dir,
        }

        if self.mix_chord_enabled and chord_path and os.path.exists(chord_path):
            result["chord_path"] = chord_path

        return result

    def cleanup(self):
        if self.music_source:
            self.music_source.cleanup()
        if self.separator:
            self.separator.cleanup()
        self.is_initialized = False


def _numpy_compressor(data: "np.ndarray", threshold_db: float, ratio: float):
    """简易下行压缩器 — 对超过阈值的信号按 ratio 衰减"""
    import numpy as np

    threshold_linear = 10 ** (threshold_db / 20) * 0.7
    mask = np.abs(data) > threshold_linear
    if np.any(mask):
        excess = np.abs(data[mask]) - threshold_linear
        attenuated = excess / ratio
        sign = np.sign(data[mask])
        data[mask] = sign * (threshold_linear + attenuated)


def _numpy_reverb(data: "np.ndarray", sr: int, room_size: float, wet_level: float) -> "np.ndarray":
    """简易卷积混响 — 指数衰减噪声脉冲响应 (FFT 加速)"""
    import numpy as np

    ir_duration = room_size * 3.0 + 0.3
    ir_len = int(sr * ir_duration)
    t = np.arange(ir_len) / sr
    decay = np.exp(-t / (room_size * 2.0 + 0.15))
    ir = np.random.randn(ir_len).astype(np.float32) * decay
    ir = ir / (np.max(np.abs(ir)) + 1e-8) * 0.6

    dry_level = 1.0 - wet_level
    output = np.zeros_like(data, dtype=np.float32)

    try:
        from scipy.signal import oaconvolve

        _conv = oaconvolve
    except ImportError:
        try:
            from scipy.signal import fftconvolve

            _conv = fftconvolve
        except ImportError:
            _conv = np.convolve

    if data.ndim == 2:
        for ch in range(data.shape[1]):
            conv = _conv(data[:, ch], ir, mode="full")
            conv = conv[: len(data)]
            output[:, ch] = dry_level * data[:, ch] + wet_level * conv
    else:
        conv = _conv(data, ir, mode="full")
        conv = conv[: len(data)]
        output = dry_level * data + wet_level * conv

    peak = np.max(np.abs(output))
    if peak > 0.0:
        output = output / peak * 0.95

    return output

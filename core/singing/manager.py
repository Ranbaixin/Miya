"""
唱歌注册管理器 + 唱歌工作流

管理多个唱歌引擎的注册、切换，以及从点歌→搜索→学唱→播放的完整异步流水线。
"""

import asyncio
import logging
import os
import re
import time
import threading
from typing import Dict, List, Optional, Any
from pathlib import Path

from .base import SingingEngine, SongInfo, LearnTask, LearnStatus, SongOutput

logger = logging.getLogger(__name__)


class SingingWorkflow:
    """唱歌异步工作流 — 点歌→搜索→学唱→下载→播放 完整流水线"""

    def __init__(self, registry: "SingingRegistry"):
        self.registry = registry
        self.is_learning: bool = False
        self.is_singing: bool = False
        self.current_song: Optional[SongOutput] = None
        self.play_queue: List[SongOutput] = []
        self._learn_lock = threading.Lock()
        self._play_lock = threading.Lock()
        self._playback_active = False

    def _save_speaker_marker(self, output_dir: str, engine):
        """保存 speaker 标记，用于缓存版本校验"""
        speaker = getattr(engine, "speaker", "")
        if speaker and output_dir:
            os.makedirs(output_dir, exist_ok=True)
            marker = os.path.join(output_dir, "_speaker.txt")
            with open(marker, "w", encoding="utf-8") as f:
                f.write(speaker)

    async def process_song_request(self, query: str, username: str = "") -> str:
        """处理唱歌请求，返回给用户的文本回复"""
        from core.text_loader import get_singing_text

        engine = self.registry.get_engine()
        if engine is None:
            return get_singing_text("not_configured")

        logger.info(f"[唱歌] {username} 点播: {query}")

        song_info = await engine.search_song(query)
        if song_info is None or not song_info.song_id or song_info.song_id == "0":
            return get_singing_text("no_song_found", song_name=query)

        song_name = song_info.song_name
        font_text = ""
        if query.strip().lower() != song_name.strip().lower():
            font_text = f'根据"{query}"的信息，'

        output_dir = os.path.join(engine.output_base_dir, song_name)
        vocal_path = os.path.join(output_dir, "vocal.wav")
        accompany_path = os.path.join(output_dir, "accompany.wav")

        # builtin 引擎走全流程管线
        if engine.engine_name == "builtin":
            from core.singing.provider_builtin import BuiltinSingingEngine

            builtin: "BuiltinSingingEngine" = engine  # type: ignore
            converted = os.path.join(output_dir, f"Vocals_{builtin.rvc_model}.wav")
            inst = os.path.join(output_dir, "Instrumental.wav")

            if os.path.exists(converted) and os.path.exists(inst):
                logger.info(f"[唱歌] builtin 缓存命中: {song_name}")
                self._enqueue_play(
                    SongOutput(
                        song_name=song_name,
                        vocal_path=converted,
                        accompany_path=inst,
                        output_dir=output_dir,
                    )
                )
                asyncio.create_task(self._background_play())
                return f"{font_text}{get_singing_text('learned_and_queued', song_name=song_name)}"

            logger.info(f"[唱歌] builtin 全流程: {song_name}")
            asyncio.create_task(
                self._builtin_pipeline(song_name, output_dir, font_text)
            )
            return f"{font_text}{get_singing_text('learning', song_name=song_name)}"

        # ACM / RVC 引擎走原有路径

        if os.path.exists(vocal_path) or os.path.exists(accompany_path):
            import shutil

            speaker_file = os.path.join(output_dir, "_speaker.txt")
            current_speaker = getattr(engine, "speaker", "")
            cached_speaker = ""
            if os.path.exists(speaker_file):
                with open(speaker_file, "r", encoding="utf-8") as f:
                    cached_speaker = f.read().strip()
            if current_speaker and cached_speaker != current_speaker:
                logger.info(
                    f"[唱歌] 缓存 speaker 不匹配 ({cached_speaker or '(空)'} != {current_speaker})，重新学唱"
                )
                shutil.rmtree(output_dir, ignore_errors=True)
            else:
                logger.info(f"[唱歌] 本地已有歌曲: {song_name}")
                mix_path = os.path.join(output_dir, f"{song_name}_mix.wav")
                if not os.path.exists(mix_path):
                    await engine.download_mix(song_name, output_dir)
                self._save_speaker_marker(output_dir, engine)
                self._enqueue_play(
                    SongOutput(
                        song_name=song_name,
                        vocal_path=vocal_path,
                        accompany_path=accompany_path,
                        output_dir=output_dir,
                    )
                )
                asyncio.create_task(self._background_play())
                return f"{font_text}{get_singing_text('learned_and_queued', song_name=song_name)}"

        available = await engine.get_available_songs()
        if song_name in available:
            logger.info(f"[唱歌] 服务端已有歌曲: {song_name}")
            os.makedirs(output_dir, exist_ok=True)
            vocal = await engine.download_vocal(song_name, output_dir)
            accompany = await engine.download_accompany(song_name, output_dir)
            if vocal or accompany:
                self._save_speaker_marker(output_dir, engine)
                self._enqueue_play(
                    SongOutput(
                        song_name=song_name,
                        vocal_path=vocal or "",
                        accompany_path=accompany or "",
                        output_dir=output_dir,
                    )
                )
                asyncio.create_task(self._background_play())
                return f"{font_text}{get_singing_text('learned_and_queued', song_name=song_name)}"
            return get_singing_text("download_failed", song_name=song_name)

        logger.info(f"[唱歌] 需要学唱: {song_name}")
        asyncio.create_task(
            self._learn_and_download(song_name, query, output_dir, username)
        )
        return f"{font_text}{get_singing_text('learning', song_name=song_name)}"

    def _enqueue_play(self, output: SongOutput):
        with self._play_lock:
            self.play_queue.append(output)

    async def _learn_and_download(
        self, song_name: str, query: str, output_dir: str, username: str
    ):
        """后台学唱 + 下载 → 入队 → 播放"""
        engine = self.registry.get_engine()
        if engine is None:
            return

        with self._learn_lock:
            if self.is_learning:
                return
            self.is_learning = True

        try:
            task = await engine.request_learn(song_name)
            if task.status == LearnStatus.FAILED:
                logger.error(f"[唱歌] 学唱请求失败: {song_name}")
                return

            song_name = task.song_name
            output_dir = os.path.join(engine.output_base_dir, song_name)
            os.makedirs(output_dir, exist_ok=True)

            if task.status == LearnStatus.PROCESSED:
                vocal_path = await engine.download_vocal(song_name, output_dir)
                accompany_path = await engine.download_accompany(song_name, output_dir)
                logger.info(f"[唱歌] 学唱完成（秒返）: {song_name}")
            else:
                vocal_path = None
                accompany_path = None
                for i in range(engine.learn_timeout):
                    status = await engine.get_learn_status(song_name)
                    if status == LearnStatus.PROCESSED:
                        vocal_path = await engine.download_vocal(song_name, output_dir)
                        accompany_path = await engine.download_accompany(
                            song_name, output_dir
                        )
                        logger.info(f"[唱歌] 学唱完成（第{i}秒）: {song_name}")
                        break
                    elif status == LearnStatus.FAILED:
                        logger.error(f"[唱歌] 学唱失败: {song_name}")
                        return
                    await asyncio.sleep(1)
                else:
                    logger.error(f"[唱歌] 学唱超时: {song_name}")
                    return

            self._save_speaker_marker(output_dir, engine)
            self._enqueue_play(
                SongOutput(
                    song_name=song_name,
                    vocal_path=vocal_path or "",
                    accompany_path=accompany_path or "",
                    output_dir=output_dir,
                )
            )
            await self._background_play()

        except Exception as e:
            logger.exception(f"[唱歌] 学唱异常: {e}")
        finally:
            self.is_learning = False

    async def _builtin_pipeline(self, song_name: str, output_dir: str, font_text: str):
        """内置引擎全流程：下载 → 分离 → 换声 → 入队 → 播放"""
        from core.text_loader import get_singing_text
        from core.singing.provider_builtin import BuiltinSingingEngine

        engine = self.registry.get_engine()
        if engine is None or engine.engine_name != "builtin":
            return

        builtin: "BuiltinSingingEngine" = engine  # type: ignore
        result = await builtin.process_full_pipeline(song_name, output_dir)
        if result is None:
            logger.error(f"[唱歌] builtin 全流程失败: {song_name}")
            return

        self._save_speaker_marker(output_dir, engine)
        skip_rvc = bool(result.get("skip_rvc", False))
        chord_path = result.get("chord_path", "")
        self._enqueue_play(
            SongOutput(
                song_name=song_name,
                vocal_path=result["vocal_path"],
                accompany_path=result["accompany_path"],
                output_dir=output_dir,
                skip_rvc=skip_rvc,
                chord_path=chord_path,
                vol_chord=getattr(builtin, "mix_chord_volume", 50),
            )
        )
        await self._background_play()
        if skip_rvc:
            logger.info(f"[唱歌] builtin 全流程完成 (降级模式): {song_name}")

    async def _background_play(self):
        """后台异步播放队列中的所有歌曲"""
        if self._playback_active:
            return
        self._playback_active = True
        try:
            while self.play_queue:
                await self.play_next()
        finally:
            self._playback_active = False

    async def play_next(self, engine: Optional[SingingEngine] = None) -> Optional[str]:
        """播放队列中下一首歌，返回歌曲名，无歌返回None"""
        with self._play_lock:
            if not self.play_queue:
                return None
            output = self.play_queue.pop(0)
            self.current_song = output

        if engine is None:
            engine = self.registry.get_engine()
        if engine is None:
            return None

        vocal_path = output.vocal_path
        accompany_path = output.accompany_path

        if not os.path.exists(vocal_path) and not os.path.exists(accompany_path):
            logger.warning(f"[唱歌] 歌曲文件不存在: {output.song_name}")
            return None

        self.is_singing = True
        logger.info(f"[唱歌] 开始播放: {output.song_name}")

        try:
            await self._play_dual_tracks(
                vocal_path,
                accompany_path,
                vol_vocal=engine.volume_vocal,
                vol_accompany=engine.volume_accompany,
                skip_rvc=output.skip_rvc,
                chord_path=output.chord_path,
                vol_chord=output.vol_chord,
            )
        except Exception as e:
            logger.exception(f"[唱歌] 播放异常: {e}")
        finally:
            self.is_singing = False
            self.current_song = None

        return output.song_name

    async def _play_dual_tracks(
        self,
        vocal: str,
        accompany: str,
        vol_vocal: int = 70,
        vol_accompany: int = 70,
        skip_rvc: bool = False,
        chord_path: str = "",
        vol_chord: int = 50,
    ):
        """播放歌曲：优先混音成品 → pydub 多轨混音 → AudioPlayer 播放"""
        output_dir = (
            os.path.dirname(vocal) if vocal else os.path.dirname(accompany or "")
        )
        song_name = os.path.basename(output_dir) if output_dir else "unknown"
        mix_file = (
            os.path.join(output_dir, f"{song_name}_mix.wav") if output_dir else ""
        )

        play_file: Optional[str] = ""

        if skip_rvc and os.path.exists(vocal):
            play_file = vocal
            logger.info(f"[唱歌] 降级播放原曲: {os.path.basename(play_file)}")
        elif mix_file and os.path.exists(mix_file):
            play_file = mix_file
            logger.info(f"[唱歌] 播放混音成品: {os.path.basename(play_file)}")
        elif os.path.exists(vocal) and os.path.exists(accompany):
            play_file = await self._mix_wav_files(
                vocal,
                accompany,
                vol_vocal,
                vol_accompany,
                mix_file,
                chord_path=chord_path,
                vol_chord=vol_chord,
            )
            track_count = 3 if (chord_path and os.path.exists(chord_path)) else 2
            logger.info(
                f"[唱歌] {track_count}轨混音播放: {os.path.basename(play_file or '')}"
            )
        else:
            play_file = (
                vocal
                if os.path.exists(vocal)
                else (accompany if os.path.exists(accompany) else "")
            )
            if play_file:
                logger.info(f"[唱歌] 单轨播放: {os.path.basename(play_file)}")

        if not play_file or not os.path.exists(play_file):
            logger.warning(f"[唱歌] 无可播放文件: {song_name}")
            return

        from core.audio_player import get_audio_player

        player = get_audio_player()
        logger.info(f"[唱歌] 开始播放: {song_name}")
        await player.play(play_file)
        await player.wait_until_finished()
        logger.info(f"[唱歌] 播放完成: {song_name}")

    async def _mix_wav_files(
        self,
        vocal_path: str,
        accompany_path: str,
        vol_vocal: int,
        vol_accompany: int,
        output_path: str,
        chord_path: str = "",
        vol_chord: int = 50,
    ) -> Optional[str]:
        """多轨混音：人声 + 伴奏 + 可选和声 → 单文件，支持独立音量控制"""
        import math

        def do_mix():
            try:
                import os as _os

                _ffmpeg_path = (
                    r"D:\AIvoice\RVC20240604Nvidia50x0\RVC20240604Nvidia50x0\ffmpeg.exe"
                )
                if _os.path.exists(_ffmpeg_path):
                    _os.environ["PATH"] = (
                        _os.path.dirname(_ffmpeg_path)
                        + ";"
                        + _os.environ.get("PATH", "")
                    )

                from pydub import AudioSegment

                track_v = AudioSegment.from_file(vocal_path)
                track_a = AudioSegment.from_file(accompany_path)

                max_len = max(len(track_v), len(track_a))
                has_chord = (
                    chord_path
                    and _os.path.exists(chord_path)
                    and _os.path.getsize(chord_path) > 0
                )

                if has_chord:
                    track_c = AudioSegment.from_file(chord_path)
                    max_len = max(max_len, len(track_c))

                if len(track_v) < max_len:
                    track_v += AudioSegment.silent(duration=max_len - len(track_v))
                if len(track_a) < max_len:
                    track_a += AudioSegment.silent(duration=max_len - len(track_a))
                if has_chord and len(track_c) < max_len:
                    track_c += AudioSegment.silent(duration=max_len - len(track_c))

                ratio_v = vol_vocal / 70.0
                ratio_a = vol_accompany / 70.0
                if ratio_v != 1.0:
                    db_v = 20 * math.log10(max(ratio_v, 0.001))
                    track_v = track_v.apply_gain(db_v)
                if ratio_a != 1.0:
                    db_a = 20 * math.log10(max(ratio_a, 0.001))
                    track_a = track_a.apply_gain(db_a)

                if has_chord:
                    ratio_c = vol_chord / 70.0
                    if ratio_c != 1.0:
                        db_c = 20 * math.log10(max(ratio_c, 0.001))
                        track_c = track_c.apply_gain(db_c)

                mixed = track_a.overlay(track_v)
                if has_chord:
                    mixed = mixed.overlay(track_c)
                    logger.info(f"[混音] 3轨: vocal+accompany+chord(vol={vol_chord})")

                peak_db = mixed.max_dBFS
                if peak_db > -1.0:
                    mixed = mixed.apply_gain(-1.0 - peak_db)
                    logger.info(f"[混音] 防削波: peak={peak_db:.1f}dBFS → -1.0dBFS")

                mixed.export(output_path, format="wav")
                return output_path
            except Exception as e:
                logger.exception(f"[唱歌] 混音失败: {e}")
                return None

        return await asyncio.get_event_loop().run_in_executor(None, do_mix)

    def get_queue_size(self) -> int:
        return len(self.play_queue)

    def get_status(self) -> Dict[str, Any]:
        return {
            "is_learning": self.is_learning,
            "is_singing": self.is_singing,
            "current_song": self.current_song.song_name if self.current_song else None,
            "queue_size": len(self.play_queue),
        }


class SingingRegistry:
    """唱歌引擎注册管理器"""

    def __init__(self):
        self.engines: Dict[str, SingingEngine] = {}
        self.default_engine: Optional[str] = None
        self.current_engine: Optional[str] = None
        self.workflow = SingingWorkflow(self)

    def register_engine(self, engine: SingingEngine, is_default: bool = False):
        engine_name = engine.engine_name
        self.engines[engine_name] = engine
        if is_default or self.default_engine is None:
            self.default_engine = engine_name
        if self.current_engine is None:
            self.current_engine = engine_name
        logger.info(f"Registered singing engine: {engine_name} (default={is_default})")

    def unregister_engine(self, engine_name: str):
        if engine_name in self.engines:
            engine = self.engines[engine_name]
            engine.cleanup()
            del self.engines[engine_name]
            if self.current_engine == engine_name:
                self.current_engine = self.default_engine or (
                    list(self.engines.keys())[0] if self.engines else None
                )
            if self.default_engine == engine_name:
                self.default_engine = (
                    list(self.engines.keys())[0] if self.engines else None
                )

    def get_engine(self, engine_name: Optional[str] = None) -> Optional[SingingEngine]:
        if engine_name is None:
            engine_name = self.current_engine
        return self.engines.get(engine_name)

    def set_current_engine(self, engine_name: str) -> bool:
        if engine_name in self.engines:
            self.current_engine = engine_name
            logger.info(f"Current singing engine: {engine_name}")
            return True
        return False

    def get_available_engines(self) -> List[str]:
        return list(self.engines.keys())

    async def initialize_all(self, config: Dict[str, Any]):
        for engine_name, engine_config in config.items():
            engine = self.engines.get(engine_name)
            if engine:
                success = engine.initialize(engine_config)
                if success:
                    logger.info(f"Singing engine initialized: {engine_name}")
                else:
                    logger.error(f"Singing engine failed: {engine_name}")

    def cleanup_all(self):
        for engine in self.engines.values():
            engine.cleanup()
        logger.info("All singing engines cleaned up")

    def __repr__(self):
        return f"<SingingRegistry: engines={list(self.engines.keys())}, current={self.current_engine}>"


_global_singing_registry: Optional[SingingRegistry] = None


def get_singing_registry() -> SingingRegistry:
    global _global_singing_registry
    if _global_singing_registry is None:
        _global_singing_registry = SingingRegistry()
    return _global_singing_registry
